#!python3
# -*- coding: utf-8 -*-
"""
This submodule parses and exports mesh data to be further imported by a
DCC package (blender in my case). I don't use any standardized formats
simply because I don't want to bother writing those. I dump it as a
json.

Basic terminology:
* meshdata - unpacked data that is ready to be imported to blender
* island - a set of polygons (within same lod) that share the same
           material. They can be unconnected (despite the naming, it is
           deprecated, I didn't bother to refactor)
* tris chunk - a data chunk that desctibes a set of triangles. In mesh
               triangles data is not a continuous dump, it's divided
               into distinct blocks. More on that in IslandDescriptor's
               docstring

Basic structure:
Mesh - class that is responsible for mesh file parsing
|---IslandDescriptor - structure that maps an island and it's metadata
|---IslandSkinMapping - this is a gues, it's not fully reversed. I guess
                        this struct is supposed to map bone id's to
                        skinning data (which for now I'm dumping as 
                        ``colors`` attribute in meshdata for
                        visualization purposes)

Caveats:
Not all parameters are refactored yet. FOr example, Mesh.x2C is
important for mesh type filtering, but not named properly.
IslandSkinMapping is fully deserialized but not completely interpreted.
"""
from functools import reduce
import io
import os
import json
import struct

from r6s.mesh.unpack import *
from binstream import *
from r6s.common import FileMeta

# import revutils as ru
# tohes = ru.bytes.bytes2hes
# import pprint
# pp = pprint.pprint

TRIS_CHUNK_SIZE = 0x180
TRIS_IN_CHUNK = 64


def is_mesh(magic):
    return magic == 0xABEB2DFB


class IslandDescriptor(object):
    """
    Holds data needed to construct a given island.
    What a tris_chunk is:
    triangles are stored in chunks. Each chunk is 0x180 bytes long.
    If given chunk is the last one in island ant is not filled till the
    end, it gets filled with last vert's id, forming invalid triangles.
    Example of an end of such chunk:
    
    
       ...: ...
     0x160: 0F AB 1C AB 1B AB 1A AB 1B AB 1f AB 10 AB 11 AB 
     0x170: 12 AB 11 AB|11 AB 11 AB 11 AB 11 AB 11 AB 11 AB
                  ^    |^
    last valid tri's id|buffer filled with last id
    """

    def __init__(self):
        self.x00 = 0
        self.offset_verts = 0
        self.num_verts = 0
        self.offset_tris_chunks = 0  # tris chunks offset
        self.num_tris_chunks = 0  # tris chunks num per this island
        self.mat_id = 0
        self.x18 = 0
        self.x1C = 0
        self.x20 = 0

    @classmethod
    def parse(cls, r):
        self = cls()
        self.x00 = ruint32(r)
        self.offset_verts = ruint32(r)
        self.num_verts = ruint32(r)
        self.offset_tris_chunks = ruint32(r)
        self.num_tris_chunks = ruint32(r)
        self.mat_id = ruint32(r)
        self.x18 = ruint32(r)
        self.x1C = ruint32(r)
        self.x20 = ruint32(r)
        return self

    def __repr__(self):
        return (
            "<IslandDescriptor: "
            + ", ".join(f"{k}={v}" for k, v in vars(self).items())
            + ">"
        )


class IslandSkinMapping(object):
    """This is just a guess based on structure. It might turn out
    being something else."""

    SIZE = 0x10C

    def __init__(self):
        self.x00 = 0
        self.bones_used = 0  # blind guess
        self.mat_id = 0  # a guess, but seems to be true
        self.x04 = 0
        self.vert_buf_len = 0
        self.indices = []
        self.x108 = 0

    @classmethod
    def parse(cls, r):
        self = cls()
        self.x00 = ruint16(r)
        self.bones_used = ruint8(r)
        self.mat_id = ruint8(r)
        self.x04 = ruint16(r)
        self.vert_buf_len = ruint16(r)
        len_indices = ruint8(r)
        self.indices = list(r.read(len_indices))
        r.seek(
            self.SIZE - 2 - 4 - 2 - 1 - len_indices - 4, io.SEEK_CUR,
        )
        self.x108 = ruint32(r)
        return self


class Mesh(object):
    """Mesh:
            verts   - [(float, float, float), ...]
            normals - [(float, float, float), ...]
            tangs   - [(float, float, float), ...]
            colors  - [(int, int, int, int), ...]
            unar1   - [(int, int, int, int), ...] for now
            uvs     - [(float, float), ...]
            islands - [    [(int, int, int), ...], ...    ]
            verts_data_len      - int
            verts_data_len - int
            tris_data_len - int
            num_verts      - int
            num_islands   - int
            """

    HEADER_SIZE = 0x4C
    BBOX_STRUCT = struct.Struct("8f")

    def __init__(self, r, readmesh=True):
        self.reader = r
        self.header = None
        self.fpath = ""
        if hasattr(r, "name"):
            self.fpath = r.name
        self.verts = []
        self.islands = []
        self.vertmaps = []
        self.trisblock_stats = []
        self.triunknown = []
        self.normals = None
        self.tangs = None
        self.colors = None
        self.unar1 = None  # unknown array 1
        self.uvs = None

        # file header (0x5C - zeroes till verts)
        self.header = FileMeta.parse(r)
        # model header
        assert ruint32(r) == 0xFC9E1595  # [-0x8], inner model struct type
        self.size_till_footer = ruint32(r)  # [-0x4]
        data_start = r.tell()  # inner model zero byte

        self.x00 = ruint32(r)  # [0x0] = 0x14
        self.revision = ruint32(r)  # [0x4] = 0, 1, 2
        self.vert_len = ruint32(r)  # [0x8] how much bytes are allocated
        # per vertex
        if not self.vert_len in (0x18, 0x1C, 0x24, 0x28, 0x2C, 0x5C,):
            print("Unknown vert_len 0x%X" % self.vert_len)
        self.verts_data_len = ruint32(r)  # [0x0C]
        self.tris_data_len = ruint32(r)  # [0x10]

        # these hold lengths of data blocks following immediately after
        # trisblock
        self.vertmaps_data_len = ruint32(r)  # [0x14]  num_verts*12
        self.un2 = ruint32(r)  # [0x18] unreversed data
        self.trisblock_stat_data_len = ruint32(r)  # [0x1C] size of array that
        # contains 11 floats per each tris chunk
        self.triunknown_data_len = ruint32(r)  # [0x20]  size of array that
        # contains packed 4-byte value per each triangle (including invalid
        # tris)
        self.x24 = ruint32(r)  # [0x24] = 0
        self.x28 = ruint32(r)  # [0x28] = 0
        self.x2C = ruint32(r)  # [0x2C] = 1(animated/interactive?),
        # 2(map props?), 8(some bosses, some hands), 9, 10(some weapons)
        self.num_lods = ruint32(r)
        self.mesh_type = rint32(r)  # flags?.. = -1(bboxes???),
        # 2 (assets?), 269 (weapons/gadgets)
        self.num_islands = ruint32(r)  # [0x38]
        self.x3C = ruint32(r)  # [0x3C] = 0
        self.x40 = rfloat(r)  # float
        self.x44 = rfloat(r)  # float
        ### EXAMINE
        self.rng3_len = ruint32(r)  # [0x48] len from vertblock till valuable
        # data end (till end of floats section)

        self.num_verts = self.verts_data_len // self.vert_len
        self.vertblock_start = r.tell()
        self.trisblock_start = self.vertblock_start + self.verts_data_len
        self.extra_data_start = self.trisblock_start + self.tris_data_len

        self.tail_start = (
            self.extra_data_start
            + self.vertmaps_data_len
            + self.un2
            + self.trisblock_stat_data_len
            + self.triunknown_data_len
        )

        # tail data
        r.seek(self.tail_start)
        self.island_metas = [
            IslandDescriptor.parse(r)
            for _ in range(self.num_islands * self.num_lods)
        ]
        self.island_bboxes = [
            self.BBOX_STRUCT.unpack(r.read(0x20))
            for _ in range(self.num_islands)
        ]
        self.island_skin_mapping = [
            IslandSkinMapping.parse(r) for _ in range(self.num_islands)
        ]

        if readmesh:
            self.readmesh()

    def readmesh(self):
        """
        This function reads raw mesh data from file, deserializes it and
        stores it without any processing. It must be invoked before any
        attempts to use export methods (and is invoced in __init__ by
        default).
        """
        r = self.reader
        r.seek(self.vertblock_start, io.SEEK_SET)

        # read verts
        known_format = False
        if self.revision == 0:
            ### =====  CASE 0x1_  =====
            if self.vert_len in (0x18, 0x1C):
                known_format = True
                self.uvs = []
                skip_bytes = self.vert_len - 12
                if skip_bytes:
                    print(
                        f"Will skip {skip_bytes} bytes of unknown data per vertex."
                    )
                for _ in range(self.num_verts):
                    self.verts.append(uint64_to_pos(r))
                    r.read(skip_bytes)  # skip other data for now
                    self.uvs.append(uint32_to_uv(r))
        elif self.revision in (1, 2):
            ### =====  CASE 0x1_  =====
            if self.vert_len in (0x18, 0x1C):
                known_format = True
                # positions
                self.verts = [uint64_to_pos(r) for _ in range(self.num_verts)]
                # normals
                self.normals = [
                    uint32_to_vec(r) for _ in range(self.num_verts)
                ]
                # tangs
                self.tangs = [uint32_to_vec(r) for _ in range(self.num_verts)]
                # binorms
                self.binorms = [
                    uint32_to_vec(r) for _ in range(self.num_verts)
                ]
                # 0x1c specific header_block_ptrn
                if self.vert_len == 0x1C:
                    # colors
                    self.colors = [
                        [uint32_to_color(r) for _ in range(self.num_verts)]
                    ]
                # uvs?
                self.uvs = [uint32_to_uv(r) for _ in range(self.num_verts)]

            ### =====  CASE 0x2_  =====
            elif self.vert_len in [
                0x24,
                0x28,
                0x2C,
            ]:
                known_format = True
                remaining = self.vert_len
                # positions
                self.verts = [read3floats(r) for _ in range(self.num_verts)]
                remaining -= 12
                # normals
                self.normals = [
                    uint32_to_vec(r) for _ in range(self.num_verts)
                ]  # might be tangent
                remaining -= 4
                # tan
                tan = [
                    uint32_to_vec(r) for _ in range(self.num_verts)
                ]  # might be binormal
                remaining -= 4
                # binorm
                bi = [uint32_to_vec(r) for _ in range(self.num_verts)]
                remaining -= 4
                # uvs
                self.uvs = [uint32_to_uv(r) for _ in range(self.num_verts)]
                remaining -= 4

                if remaining != 0:
                    self.colors = []
                while remaining != 0:
                    remaining -= 4
                    self.colors.append(
                        [uint32_to_color(r) for _ in range(self.num_verts)]
                    )

                if remaining:
                    print("remaining", remaining)
            ### =====  CASE 0x5_  =====
            elif self.vert_len == 0x5C:
                for _ in range(self.num_verts):
                    self.verts.append(read3floats(r))
                    self.unar1.append(ras(r, "f" * 20))
        if not known_format:
            raise ValueError(
                "Unknown mesh vertex length: 0x%X, revision: %i"
                % (self.vert_len, self.revision)
            )
        # read tris
        self._parse_tris_blocks_()
        # vert maps
        if self.vertmaps_data_len:
            self._parse_vertmaps_()
        # unknown, yet to find and reverse
        if self.un2:
            pass  # print("Has un2 data!")
        # trisblock statistics
        if self.trisblock_stat_data_len:
            self._parse_trisblock_stat_()
        # per-triangle data
        if self.triunknown_data_len:
            self._parse_triunknown_()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.reader.close()

    def __del__(self):
        if not self.reader.closed:
            self.reader.close()

    def init_meshdata(self, copy: bool = False) -> dict:
        """
        Build new dict, containing data necessary to build mesh.
        :param bool copy:
            whether to link data from Mesh object directly or to copy
            it. If you plan to modify data before building the mesh
            (appending another color list to 'colors' etc) - set it to
            True, otherwise you will append also to Mesh.colors.
        :return dict: meshdata dictionary
        """
        assert len(self.islands), (
            "No island triangles stored! "
            "Run `self.readmesh() to build data buffers first.`"
        )
        meshdata = {"islands": {}}
        meshdata["verts"] = self.verts.copy() if copy else self.verts
        if self.uvs is not None:
            meshdata["uvs"] = self.uvs.copy() if copy else self.uvs
        if self.normals is not None:
            normals = self.normals.copy() if copy else self.normals
            meshdata["normals"] = normals
        if self.colors is not None:
            if copy:
                colors = []
                for col in self.colors:
                    colors.append(col.copy())
                meshdata["colors"] = colors
            else:
                meshdata["colors"] = self.colors
        return meshdata

    def build_island(self, meshdata: dict, index: int) -> dict:
        assert len(self.islands), (
            "No island triangles stored! "
            "Run `self.readmesh() to build data buffers first.`"
        )
        island_tris = self.islands[index]
        island_meta = self.island_metas[index]
        offset_verts = island_meta.offset_verts
        if offset_verts:
            meshdata["islands"][island_meta.mat_id] = [
                tuple(v + offset_verts for v in tri) for tri in island_tris
            ]
        else:
            meshdata["islands"][island_meta.mat_id] = island_tris
        return meshdata

    def remove_isolated_verts(self, meshdata: dict) -> dict:
        """
        Removes vertices that are not connected to any triangle.
        **WARNING! OPERATES ON INPUT DATA INSTEAD OF COPYING IT!**
        """
        # build mappings for used vertices
        used_verts = sorted(
            set(
                v
                for island in meshdata["islands"].values()
                for tri in island
                for v in tri
            )
        )
        vert_mapping = {old: new for new, old in enumerate(used_verts)}
        # clean up verts and mormals
        for key in ["verts", "normals", "uvs"]:
            if key in meshdata:
                meshdata[key] = _filter_by_indices_(meshdata[key], used_verts)
        # clean up colors
        if "colors" in meshdata:
            for i_col, color in enumerate(meshdata["colors"]):
                meshdata["colors"][i_col] = _filter_by_indices_(
                    color, used_verts
                )
        for mat_id in meshdata["islands"]:
            meshdata["islands"][mat_id] = [
                tuple(vert_mapping[x] for x in tri)
                for tri in meshdata["islands"][mat_id]
            ]
        return meshdata

    def build_meshdata(
        self,
        lod: int = 0,
        copy: bool = False,
        clear: bool = True,
        islands=None,
    ) -> dict:
        """
        Build mesh data for blender. Exports it as a dict for ease of
        use and transfer. By default operates on a single LOD (default
        0). If one wants to specify islands, those must have indices
        within that one lod (i.e. less than self.num_islands) If one
        wants to select islands from different lods, he/she must set
        lod=-1. This way islands will now provide indices within all
        self.islands and must be less than
        ``self.num_lods * self.num_islands``.
        :param lod:
        :param copy:
        :param clear:
        :param islands:
        :return:
        """
        # preprocess islands attribute
        if islands is None:  # case DEFAULT
            islands = range(self.num_islands)
        elif isinstance(islands, int):  # case integer
            islands = [islands]
        # check lod
        assert (
            lod < self.num_lods
        ), f"lod must be below self.num_lods={self.num_lods}, got {lod}."
        # build data
        meshdata = self.init_meshdata(copy)
        for isl_index in islands:
            if lod != -1:
                assert isl_index < self.num_islands, (
                    "Expected island index less than self.num_islands="
                    f"{self.num_islands}, got {isl_index}."
                )
                final_index = lod * self.num_islands + isl_index
            else:
                final_index = isl_index
            self.build_island(meshdata, final_index)
        if clear:
            self.remove_isolated_verts(meshdata)
        return meshdata

    def _update_indices_(self, self_lst, tridxs):
        if self_lst is None:
            return None
        result = [None] * len(tridxs)
        for ni, oi in enumerate(tridxs):  # ni, oi -> new index, old index
            result[ni] = self_lst[oi]
        return result

    def dump_meshdata(
        self,
        outdir,
        lod: int = 0,
        copy: bool = False,
        clear: bool = True,
        islands=None,
    ):
        meshdata = self.build_meshdata(lod, copy, clear, islands)
        outfile = os.path.join(outdir, str(self.header.uid) + ".meshjson")
        with open(outfile, "w") as w:
            json.dump(meshdata, w)

    def _parse_tris_blocks_(self):
        """
        Loops through trisblock section, splits it into islands, parses
        and trims invalid endings (read IslandDescriptor's docstring for
        more info). Stores resulting triangle islands in self.islands.
        :return list: list of all processed islands
        """
        r = self.reader
        r.seek(self.trisblock_start)
        # parse each island's data
        for island_meta in self.island_metas:
            tri_indices = [
                ruint16(r)
                for _ in range(island_meta.num_tris_chunks * TRIS_IN_CHUNK * 3)
            ]
            # cleanup invalid ending of tris data
            if len(tri_indices):
                last_id = tri_indices[-1]
                invalid_tri = [
                    last_id,
                    last_id,
                    last_id,
                ]
                last_tri_index = len(tri_indices) - 3
                # run from end to beginning while finding invalid triplets
                while (
                    tri_indices[last_tri_index : last_tri_index + 3]
                    == invalid_tri
                ):
                    last_tri_index -= 3
                # trim till last valid triplet
                tri_indices = tri_indices[: last_tri_index + 3]
                # pack triplets into triangles and store
                i_tris = iter(tri_indices)
                self.islands.append(list(zip(i_tris, i_tris, i_tris)))
            else:  # empty island
                self.islands.append([])
        return self.islands

    def _parse_vertmaps_(self):
        """
        reads vertex mappings for each island
        :return:
        """
        r = self.reader
        r.seek(self.extra_data_start)
        for i in range(self.num_lods):
            mapping = [ruint16(r) for _ in range(self.num_verts)]
            self.vertmaps.append(mapping)
        return self.vertmaps

    def _parse_trisblock_stat_(self):
        r = self.reader
        r.seek(self.extra_data_start + self.vertmaps_data_len + self.un2)
        for i in range(self.tris_data_len // TRIS_CHUNK_SIZE):
            self.trisblock_stats.append(struct.unpack("11f", r.read(11 * 4)))
        return self.trisblock_stats

    def _parse_triunknown_(self):
        r = self.reader
        self.triunknown = [
            tuple(r.read(4)) for _ in range(self.triunknown_data_len // 4)
        ]
        return self.triunknown


def parse(input, readmesh=True, close=False):
    if isinstance(input, io.IOBase):
        r = input
    elif isinstance(input, str):
        r = open(input, "rb")
    else:
        raise (
            AttributeError(
                'Unknown input type of class "%s". '
                "Must be file path or io.stream."
            )
        )
    res = Mesh(r, readmesh)
    if close:
        r.close()
    return res


def _filter_by_indices_(lst: list, indices: list) -> list:
    """
    Example::
        >>> _filter_by_indices_(lst=['a','b','c','d'],indices=[1,3])
        ... ['b','d']
    """
    return [v for i, v in enumerate(lst) if i in indices]

