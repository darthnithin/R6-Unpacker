#!python3
# -*- coding: utf-8 -*-
"""
Designed to parse and export forge textures.

Note:
Forge's textures in their essence are plain dds with mangled header data
and some extra metadata on top. All this class does is it remaps those
values and dumps it into external utilities to convert.

Basic structure:
Tex - class designed to parse and export forge texture.

Caveats:
Forge textures use some strange width and height values. Thoes get
stored as Tex.w and Tex.h parameters. To get actual dimensions, use
Tex.get_dimensions(), it returns a tuple of (width, height) in pixels.
Also, this module seems to successfully unpack 99% of textures, but
there is 1% of ones that fail to get exported. Of the ones I nave seen
some of them had ``get_dimensions()`` as odd numbers which seems to be
invalid for some dds types and results in Raw Tex failing to convert the
texture. The code in ``get_dimensions()`` is empirical, i.e. a guess. It
migh be wrong which results in those bad dimensions and export failure.
Anyways, this part needs mor work.
"""
from binstream import ruint8, ruint16, ruint32, ruint64
from io import SEEK_SET, SEEK_END
import subprocess as sp
import os
import r6s.settings
import r6s.common
import typing


def bin_path(name):
    return os.path.join(r6s.settings.tex_bin, name)


textypes = {
    0x0: 87,  # b8g8r8a8_unorm
    0x2: 71,  # BC1
    0x3: 71,  # BC1
    0x4: 74,  # BC2
    0x5: 77,  # BC3
    0x6: 83,  # BC5U
    0x7: 61,  # r8_unorm
    0x8: 61,  # r8_unorm
    0x9: 56,  # r16_unorm
    0xB: 42,  # r32_uint
    0xC: 3,  # r32g32b32a32_uint???
    0xE: 80,  # bc4???
    0xF: 95,  # BC6
    0x10: 98,  # BC7
    0x11: 87,  # b8g8r8a8_unorm
}


### TEX CLASS
class Tex(object):
    """
    WIP::
        `tex_type` seems to be the texture type classifier. Research
        shows the following groupings:
        * 0 - diffuse textures (best candidate to search for operators)
        * 1 - normal maps
        * 2 - extra textures (roughness, metallicity, etc.)
        * 3 - menu icons and some cubemaps
        * 4 - LUTs?
        * 5 - strange normal maps. Mostly floor tiles. Seem like another
              extra texture
        * 6 - B/W textures and stencils
        * 7 - RGB masks (material masks?) with rare exceptions
    Caveats::
        Atthibutes `w` and `h` are not actual dimensions in pixels. To
        get actual dimensions, use method `Tex.get_dimensions()`
    """

    def __init__(self, r):
        self.reader = r
        self.fpath = ""
        if hasattr(r, "name"):
            self.fpath = r.name
        else:
            self.fpath = ""
        # header part
        self.header = r6s.common.FileMeta.parse(r)
        assert ruint32(r) == 0x13237FE9  # actual DDS payload header
        self.data_start = r.tell()
        # payload
        self.textype = ruint32(r)  # [0x00]
        self.x04 = ruint32(r)  # 1
        self.x08 = ruint32(r)
        self.tex_type = ruint32(r)  # [0x0C] see docstring for details
        self.x10 = ruint32(r)
        self.x14 = ruint32(r)
        self.x18 = ruint32(r)
        self.x1C = ruint32(r)  # 0
        self.x20 = ruint32(r)  # 0
        self.x24 = ruint32(r)  # 0
        self.container_id = ruint32(r)  # [0x28] container id
        self.x2C = ruint8(r)  # [0x2C]

        self.num_blocks = ruint16(r)  # [0x2D]
        self.x2F = ruint8(r)  # [0x2F] might indicate whether there is alpha
        # channel in texture (not sure, needs more research)

        self.x30 = ruint32(r)  # 7
        self.start = r.tell()
        r.seek(-0x29, SEEK_END)
        self.end = r.tell()
        self.texsize = self.end - self.start

        self.w = ruint32(r)
        self.h = ruint32(r)

        # eN notation is same hex offset, e just means 'end' because those
        # values go after the actual dds blob
        self.e8 = ruint32(r)  # 1
        self.eC = ruint32(r)  # 0
        self.chan = ruint32(r)
        self.e14 = ruint32(r)
        self.mips = ruint32(r)
        self.e1C = ruint32(r)
        self.e20 = ruint32(r)  # 7
        self.e24 = ruint32(r)  # 7
        self.e28 = ruint8(r)  # 1
        self.texstart()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __del__(self):
        self.close()

    def texstart(self):
        self.reader.seek(self.start)

    def close(self):
        if not self.reader.closed:
            self.reader.close()

    def get_dimensions(self):
        chan = 2 ** self.chan
        w = self.w // chan
        h = self.h // chan
        return [w, h]

    def get_width(self):
        return self.w // (2 ** self.chan)

    def dump_blob(self, fdir):
        """
        Dumps dds blob to given folder.
        :param str fdir:
            Folder to dump data in.
        :return: str
            Returns path to exported data. Path is if look
            fdir\\{uid}.file
        """
        fdir = os.path.abspath(fdir)
        filepath = os.path.join(fdir, "%i.file" % self.header.uid)
        touchdir(fdir)
        with open(filepath, "wb") as w:
            self.reader.seek(self.start, SEEK_SET)
            w.write(self.reader.read(self.texsize))
        return filepath

    def buildDds(self, fdir, cleanup=True):
        filepath = self.dump_blob(fdir)
        ddspath = buildDds(filepath, self)
        if cleanup:
            os.remove(filepath)
        return ddspath

    def buildPng(self, fdir, vflip=True, rewrite=True, cleanup=True):
        ddspath = self.buildDds(fdir, cleanup)
        pngpath = buildPng(ddspath, vflip, rewrite)
        if cleanup:
            os.remove(ddspath)
        return pngpath


def buildDds(fpath, tex):
    """
    Builds Dds from dumped texture file.
    
    :param str fpath:
        A path to a dds blob file that was dumped from forge texture
    :param Tex tex:
        A Tex object that holds metadata for that particular blob
    :return: str
        Returns a string (path to written file).
    """
    w, h = tex.get_dimensions()
    tp = textypes.get(tex.textype, None)
    if tp is None:
        raise ValueError("Unknown textype(=%i) for %s" % (tex.textype, fpath))
    exe = bin_path("RawtexCmd.exe")
    command = f"{exe} {fpath} {tp} 0 {w} {h}"
    rawtex = sp.Popen(command, stdout=None, stderr=sp.PIPE)
    stderr = rawtex.communicate()[1]
    if rawtex.returncode == 0:
        fname, _ = os.path.splitext(fpath)
        return fname + ".dds"
    else:
        raise RuntimeError(
            f"Failed while executing command:\n{command}\n"
            f"STDERR:\n{stderr}"
        )


def buildPng(fpath, vflip=True, rewrite=False):
    """
    Builds png from given dds file.
    :param str fpath:
        Path to dds file.
    :param bool vflip:
        Flip image vertically.
    :param bool rewrite:
        Rewrite png if it already exists.
    :return: tuple(int, str)
        Returns tuple with an int (0 means operation completed
        successfully) and a string (path to written file).
    """
    fdir, fname = os.path.split(fpath)
    rewrite = "-y " if rewrite else ""
    vflip = "-vflip " if vflip else ""
    exe = bin_path("texconv.exe")
    command = (
        f"{exe} {rewrite}{vflip}-ft png -srgbi -l -f R8G8B8A8_UNORM_SRGB -o {fdir} {fpath}" # fix gamma + lowercase extension (requires updated texconv.exe)
    )
    texconv = sp.Popen(command, stdout=sp.PIPE)
    stdout = texconv.communicate()[0]
    if b"\nwriting " in stdout:
        outfilepath = stdout.split(b"\nwriting ")[1].strip()
        if b"\nERROR: " in outfilepath:
            errortext = outfilepath.split(b"\nERROR: ")[1].strip()
            raise RuntimeError(
                f"Rawtex failed to write file\nERROR:\n{errortext}"
            )
        return outfilepath.decode("ascii")
    else:
        raise RuntimeError(f"RawTex failed to write file\nSTDOUT:\n{stdout}")


def touchdir(path):
    if not os.path.isdir(path):
        os.makedirs(path)


def is_texture(magic):
    if magic in (
                0xD7B5C478, 0xF9C80707, 0x59CE4D13, 0x9F492D22,
                0x3876CCDF,                                         # textures4 forges
                0x9468B9E2, 0x5A61FAD                               # guitextures forges
                ):
        return True


### TEX PARSE
def parse(fpath, close=False):
    r = open(fpath, "rb")
    res = Tex(r)
    if close:
        r.close()
    return res


def savebyuid(forge, uid, fdir, cleanup=True):
    i = None
    fdir = os.path.abspath(fdir)
    for i, e, n, c in forge.byuid(uid):
        with Tex(c.file.getstream()) as tex:
            pngpath = tex.buildPng(fdir, cleanup=cleanup)
        return pngpath
    if i is None:
        raise ValueError("No child with uid %i found" % uid)


def getbyuid(forge, uid):
    i = None
    for i, e, n, c in forge.byuid(uid):
        return Tex(c.file.getstream())
    if i is None:
        raise ValueError("No child with uid %i found" % uid)


def process(fpath):
    fdir, fname = os.path.split(fpath)
    name, ext = os.path.splitext(fname)
    ddspath = os.path.join(fdir, "%i.dds" % name)
    filepath = os.path.join(fdir, "%i.file" % name)
    tex = parse(fpath, True)
    buildDds(filepath, tex)
    buildPng(ddspath)
    os.remove(filepath)
    os.remove(ddspath)
