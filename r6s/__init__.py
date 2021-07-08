#!python3
# -*- coding: utf-8 -*-
"""
This package is designed to unpack data from Rainbow 6: Siege. It's
main functionality is split into different modules. Main modules of
interest are:

* :mod:`r6s.settings` - holds global settings for this package
* :mod:`r6s.forge` - deals with .forge archives. Unpacks them, reads
  metadata etc. No packing functionality atm, only read.
* :mod:`r6s.mesh` - deserealizes and exports mesh data
* :mod:`r6s.tex` - deserializes and repacks textures to easy to use
  formats (partially implemented)
"""
import r6s.forge as forge
import r6s.tex as tex
import r6s.mesh as mesh
import r6s.settings as settings
import os


def fastdump(fpath, indices, exportpath=None):
    """
    .. function:: fastdump(fpath, indices)
       fastdump(fpath, callable)
    
    :param fpath: path to forge archive
    :param indices: entry number to dump or list of entry numbers or
                    callable
    :return: list of paths to dumped files
        
    Allows to dump contents of file by just package name and entry
    index/indices. Unpacked files are dumped to a
    :data:`settings.EXPORT` folder. Each file gets named as a
    decimal representation of it's uid.
    
    :attr:`indices` can be :class:`int`,
    :class:`iterable` or callable. If callable, it must accept 1 
    positional argument as input. It will recieve a tuple(num,
    :class:`forge.Entry`, :class:`forge.NameEntry`,
    :class:`forge.Container`) and must return :class:`Bool` (``True``
    means container will get exported).
    
    This is designed for more flexibility. Basically, callable gets a
    full context info related to an entry being processed. It can than
    decide wether it wants :func:`fastdump` to return this specific
    entry (by returning ``True``) or to skip it (by returning
    ``False``). Example::
        
        def pick_by_only_even_uids(context):
            entry_num, entry_data, entryname_data, container = context
            is_even = (entry_data.uid % 2) == 0
            return is_even
        
        only_even_uids = fastdump('datapc64_ondemand.forge',
                                   pick_by_only_even_uids)
        # only_even_uids now holds list of 
    
    
    """
    fdir, fname = os.path.split(fpath)
    name, ext = os.path.splitext(fname)
    if exportpath is None:
        DIR = os.path.join(settings.EXPORT, name)
    else:
        DIR = exportpath
    os.makedirs(DIR, exist_ok=True)
    result = []
    with forge.parse(fpath) as frg:
        if callable(indices):
            selected = (t[0] for t in frg if indices(t))
        else:
            selected = indices
        for i, e, n, c in frg[selected]:
            with forge.getdatastream(c.file, frg.reader) as data:
                OUT = os.path.join(DIR, "%s%s" % (e.uid, ".file"))
                with open(OUT, "wb") as w:
                    result.append(OUT)
                    w.write(data.read())
    return result


def dumpstream(fpath, r):
    """
    :param fpath: path to forge archive. Can be str
                  ``\"some/file/path.ext\"`` or a
                  list ``[\"some\", \"file\", \"path.ext\"]``
    :param r: input stream object.
    :return: path to a resulting file (basically a str version of
             :attr:`fpath`)

    Dump stream handle to a file. Supports abs path, relative path as well
    as a list/tuple of folders and target file (with extension already merged!).
    
    .. note::
        I don't even remember why I wrote this function...
    """
    # if list/tuple, than join to a single path
    if isinstance(fpath, (list, tuple)):
        fpath = os.path.join(*fpath)
    # if not an absolute path, prepend storage path
    if not os.path.isabs(fpath):
        fpath = os.path.join(settings.EXPORT, fpath)
    # check if necessary dirs exist
    fdir = os.path.dirname(fpath)
    os.makedirs(fdir, exist_ok=True)
    # write
    print("Writing %s" % fpath)
    cursor = r.tell()
    r.seek(0)
    with open(fpath, "wb") as w:
        w.write(r.read())
    r.seek(cursor)
    return fpath


def dumpbyuids(fpath, uids, exportpath=None):
    """
    :param fpath: path to forge archive
    :param uids: file uid/uids to dump from archive. Can be int or
                 iterable.
    :return: list of paths to dumped files
    
    Fast dump by uid/uids. Returns path/paths to dumped files. It is
    based on :func:`fastdump` so export paths are built with same
    logic.
    """
    if isinstance(uids, int):
        return fastdump(
            fpath, lambda x: x[1].uid == uids, exportpath=exportpath
        )
    else:
        return fastdump(
            fpath, lambda x: x[1].uid in uids, exportpath=exportpath
        )


def dumpall(fpath):
    """
    :param str fpath: path to forge archive

    Dumps all files inside of forge archive. Uses same export path logic
    as :func:`fastdump`.
    """
    fdir, fname = os.path.split(fpath)
    name, ext = os.path.splitext(fname)
    DIR = os.path.join(settings.EXPORT, name)
    with forge.parse(fpath) as frg:
        for _, e, _, c in frg:
            with forge.getdatastream(c.file, frg.reader) as data:
                OUT = os.path.join(DIR, "%s%s" % (e.uid, ".file"))
                with open(OUT, "wb") as w:
                    w.write(data.read())
