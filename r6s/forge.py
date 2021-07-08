#!python3
# -*- coding: utf-8 -*-
"""
This submodule is designed to parse ``.forge`` files strictly from
R6:Siege.

Basic structure:
Forge - core object, parses initial file structure of a given forge
|---Entry - structure that maps where each packed file is stored within
|---NameEntry - extra data about each packed file (timestamp, type, etc)
|---Container - empty class, used only for code organization purposes
    |---Descriptor - dict with some metadata, related to the wholeforge
    |                there is always one as the first forge entry
    |---File - class that handles entry unpacking and export
    |   |---Datablock - each packed file is cut into a bunch of size
    |   |   |           limited chunks. this class handles their
    |   |   |           unpacking
    |   |   |---Chunk - struct that maps a chunk
    |   |---Meta - this class fell behind since Y5 and should be
    |              rewritten ignore it for now
    |---Hash - class with some forge archive related data. There is
               always one as the last forge entry

DepGraph - class that is designed to parse ``.depgraphbin`` files
"""
import io
import os
import zstandard as zstd
from binstream import (
    ruint8,
    ruint16,
    rint32,
    ruint32,
    ruint64,
    termstr,
    streamend,
)
import datetime
import typing

# debug section
# from binutils import phex

DEBUG = True
log = print


class Entry(object):
    """
    :param io.ByteIO r: input data stream
    :ivar uint64 offset: [0x0] metadata and file start address
    :ivar uint64 uid: [0x8] entrie's uid
    :ivar uint32 size: [0x10] total entry size (meta + file)
    :ivar int end: data end (not serialized, added for ease of reverse
        engineering)
    
    Entry struct. These represent the data needed to fetch file from a
    ``.forge`` archive.
    """

    def __init__(self, r):
        self.offset = ruint64(r)
        self.uid = ruint64(r)
        self.size = ruint32(r)
        self.end = self.offset + self.size


class NameEntry(object):
    """
    TODO: write doc for Y5 NameEntry
    """

    def __init__(self, r):
        self.x00 = ruint32(r)  # [0x00] 0
        self.x04 = ruint32(r)  # [0x04] 4
        self.x08 = ruint64(r)  # [0x08] 0
        self.x10 = ruint32(r)  # [0x10] 4
        self.meta = r.read(0xFF)  # [0x14] entry metadata
        self.x113 = ruint8(r)  # [0x113] some byte
        # [0x114]
        self.timestamp = datetime.datetime.fromtimestamp(ruint32(r))
        self.x118 = ruint32(r)  # [0x118] 0
        self.prev_entry_idx = rint32(r)  # [0x11c] previous entry index
        self.next_entry_idx = rint32(r)  # [0x120] next entry index
        self.x124 = ruint64(r)  # [0x124] 0
        self.file_type = ruint32(r)  # [0x12c]
        self.x130 = ruint32(r)  # [0x130] 0
        self.x134 = r.read(12)  # [0x134] looks like compressed data


class Container(object):
    """
    Storage class designed to hold container types inside. Each child
    class must have a constructor of type ``(self, stream, entry)``
    where ``stream`` is an infile handle and ``entry`` is
    :class:`Entry` type object.
    
    :cvar dict identifier: maps object's magic (found in
        :attr:`NameEntry.file_type`) to it's constructor::

            Container.identify = {
                1: Descriptor,
                6: Hash,
                0x57fbaa34: File
            }
    
    """

    class Descriptor(dict):
        """Descriptor:
            ``{data id : data value, ...}``

        Basically a dict of stored values. Values are of types:
            uint32, uint62, str"""

        def __init__(self, r, entry):
            super().__init__()
            # start = entry.offset
            end = entry.end
            while r.tell() < end:
                did = ruint32(r)  # data id
                dtype = ruint32(r)  # data type
                if dtype == 0:  # uint32
                    self[did] = ruint32(r)
                elif dtype == 1:  # strlen, str, \x00
                    strlen = ruint32(r)
                    self[did] = r.read(strlen)
                    r.read(1)
                elif dtype == 5:  # uint64
                    self[did] = ruint64(r)
                else:
                    raise Exception(
                        "Unknown data type!\n"
                        "data id: 0x%x, type: 0x%x" % (did, dtype)
                    )

    class Hash(object):
        """
        Hash entry can be found in any forge archive as it's last entry.
        Never actually bothered to interpret those, so no values are
        named properly.
        :param uint64 hash1:  [0x0]
        :param uint32 extra:  [0x8]
        :param uint64 hash2:  [0xC]
        :param uint32 extra2: [0x14]
        :param bytes  name:   [0x18]
        :param uint64 x58:    [0x58]
        :param uint64 x60:    [0x60]
        :param uint32 extra3: [0x68]
        :param uint64 x6C:    [0x6C]
        :param uint64 x74:    [0x74]
        :param uint32 extra4: [0x7C]
        :param uint64 x80:    [0x80]
        """

        def __init__(self, r, entry):
            # init
            self.hash1 = 0
            self.extra = 0
            self.hash2 = 0
            self.extra2 = 0
            self.name = b""
            self.x58 = 0
            self.x60 = 0
            self.extra3 = 0
            self.x6C = 0
            self.x74 = 0
            self.extra4 = 0
            self.x80 = 0
            # read data
            self.hash1 = ruint64(r)  # [0x0]
            self.extra = ruint32(r)  # [0x8]
            if (
                not self.extra
            ):  # switch value, controls wether there is more metadata
                return
            self.hash2 = ruint64(r)  # [0xC]
            self.extra2 = ruint32(r)  # [0x14]
            if not self.extra2:
                return
            self.name = termstr(r.read(0x40))  # [0x18]
            self.x58 = ruint64(r)  # [0x58]
            self.x60 = ruint64(r)  # [0x60]
            self.extra3 = ruint32(r)  # [0x68]
            if not self.extra3:
                return
            self.x6C = ruint64(r)  # [0x6C]
            self.x74 = ruint64(r)  # [0x74]
            self.extra4 = ruint32(r)  # [0x7C]
            if not self.extra4:
                return
            self.x80 = ruint64(r)  # [0x80]

    class File(object):
        """
        Stores all info necessary to uncompress a file.
        
        :ivar Meta meta: metadata container
        :ivar Datablock file: file data container
        """

        class Datablock(object):
            """
            Stores collection of Chunks that comprise a single
            compressed file.
            """

            class Chunk(object):
                """
                Describes where to find particular data chunk, whether
                it is compressed/raw and where to find it within data
                stream. It's serialized form is split in parts. First
                we have ``[unpacked, packed]`` for each chunk, than we
                have ``[hash, data]`` for each chunk. ``offset`` is not
                a serialized variable, it's added merely for reverse
                engineering ease.
                
                :ivar uint32 unpacked: [0x0] unpacked data size
                :ivar uint32 packed: [0x4] packed data size
                :ivar uint64 hash: [0x8] checksum or uid
                :ivar int offset: ``0`` Chunk's position within
                    bytestream. **Must be set by the owner of chunk
                    instance!** (i.e. Datablock that initializes given
                    chunk should explicitly set this value)
                :ivar bool ispacked: tracks whether chunk is compressed
                    or has raw data
                """

                def __init__(self, r):  # Chunk()
                    self.unpacked = ruint32(r)
                    self.packed = ruint32(r)
                    self.hash = 0
                    self.offset = 0
                    self.ispacked = self.unpacked > self.packed

                def finalize(self, r):
                    self.hash = ruint32(r)
                    self.offset = r.tell()

            def __init__(self, r):  # Datablock()
                self.reader = r
                ruint16(r)  # [0x8] = 2 <-- container deserializer type
                # (changed to 3 in Y5)
                ruint16(r)  # [0xA] = 3
                ruint8(r)  # [0xC] = 0
                self.xD = ruint16(r)
                num_chunks = ruint32(r)
                self.chunks = []
                self.packed = 0
                self.unpacked = 0
                self.ispacked = False
                for i in range(num_chunks):
                    chunk = self.Chunk(r)
                    self.packed += chunk.packed
                    self.unpacked += chunk.unpacked
                    self.chunks.append(chunk)
                    if chunk.ispacked:
                        self.ispacked = True
                for chunk in self.chunks:
                    # retrieve chunk's hash\uid
                    chunk.finalize(r)
                    # skip actual data to proceed to next chunk
                    r.seek(chunk.packed, io.SEEK_CUR)

            def __getitem__(self, key):
                return self.chunks[key]

            def getstream(self):
                return getdatastream(self, self.reader)

        class Meta(list):
            """
            Basically a list of link entries. Sole purpose of this
            container is to deserialize and store metadata links.
            
            Structure: ``[Link, Link, ...]``

            .. note::
                seems to be deprecated since Y5
            """

            class Link(object):
                """
                :ivar uint64 uid: [0x0] magic number type uid uint64
                :ivar uint32 value: [0x8] unknown value (type?)
                :ivar bool extra: marks whether link has extra data
                    (not a serialized data, comes from `init`\!
                :ivar uint64 un1: [0xC] (0 if not extra)
                :ivar uint64 un2: [0x14] (0 if not extra)
                """

                def __init__(self, r, extra):
                    """
                    :param io.ByteIO r: data stream
                    :param bool extra: if set to true, than Link grabs
                        2 extra values from stream (each 8 byte long).
                    
                    """
                    self.uid = ruint64(r)
                    self.size = ruint32(r)
                    if extra:
                        self.extra = True
                        self.un1 = ruint64(r)
                        self.un2 = ruint64(r)
                    else:
                        self.extra = False
                        self.un1 = 0
                        self.un2 = 0

                def __repr__(self):
                    result = "Link(%i, %i" % (self.uid, self.size)
                    if self.extra:
                        result += ", 0x%016X, 0x%016X)" % (self.un1, self.un2)
                    else:
                        result += ")"
                    return result

            def __init__(self, r):  # Meta()
                super().__init__()
                # detect if entry has extra length
                r.seek(0, io.SEEK_END)
                length = r.tell()
                r.seek(0)
                # process links
                numlinks = ruint16(r)
                # actual detect
                if ((length - 2) / numlinks) == 12:
                    extra = False
                else:
                    extra = True
                # build links
                for i in range(numlinks):
                    self.append(self.Link(r, extra))

        def __init__(self, r, entry):  # File()
            """
            :param io.ByteIO r: input stream
            :param Entry entry: entry to process
            """
            # basic structures
            self.meta = None
            self.file = None
            # initialize
            assert ruint32(r) == 0x1014FA99, "Not a file container!"
            end = entry.end
            block = self.Datablock(r)
            if r.tell() < end:
                # unpkstreamblock = getdatastream(block, r)
                # self.meta = self.Meta(unpkstreamblock)
                #
                # if DEBUG:
                #     # CASE DIDN'T READ META ENTIRELY
                #     if unpkstreamblock.read(1) != b"":
                #         log(
                #            "0x%X: %s" % (
                #                         entry.offset,
                #                         phex(unpkstreamblock.getvalue())
                #                         )
                #            )
                #
                # unpkstreamblock.close()
                container_magic = ruint64(r)
                # currently only one type of container is 100% parsed
                if container_magic != 0x1014FA9957FBAA34:
                    # print(
                    #     "unexpected container version: "
                    #     f"0x{container_magic:016X}"
                    # )
                    self.meta = block
                    r.seek(end)  # skip unknown containers for now
                else:
                    self.meta = block
                    self.file = self.Datablock(r)
            else:
                self.file = block

        def hasmeta(self):
            return self.meta is not None

    # maps each container's magic number to it's class. It is used to
    # easily get matching constructor for given entry type in .forge
    identify = {1: Descriptor, 6: Hash, 0x57FBAA34: File}


### FORGE CLASS
class Forge(object):
    def __init__(self, r):
        # basic structures
        self.entries = []
        self.names = []  # deprecated name, holds entry's extra info, not name
        self.fpath = ""
        self.reader = None
        # initialize
        self.reader = r
        self.fpath = r.name
        self.parse()

    def ensureopen(self):
        """Allows to reopen the file in case it was closed."""
        if self.reader.closed:
            self.reader = open(self.fpath, "rb")

    def close(self):
        """Shortcut to close the file handle."""
        if not self.reader.closed:
            self.reader.close()

    def __iter__(self):
        return (
            (i, self.entries[i], self.names[i], self.get_container(i))
            for i in range(len(self.entries))
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __getitem__(self, key):
        # case slice
        if isinstance(key, slice):
            indices = range(
                key.start or 0, key.stop or len(self.entries), key.step or 1
            )
            return (
                (i, self.entries[i], self.names[i], self.get_container(i))
                for i in indices
            )
        # case iterable (list/tuple)
        elif hasattr(key, "__iter__"):
            return (
                (i, self.entries[i], self.names[i], self.get_container(i))
                for i in tuple(key)
            )
        # case int
        else:
            # it gets exported as a nested tuple to maintain interface with
            # both upper cases, so there is no need to threat tupled returns
            # and single key return separately
            return (
                (
                    key,
                    self.entries[key],
                    self.names[key],
                    self.get_container(key),
                ),
            )

    def byuid(self, key):
        if isinstance(key, int):
            key = [key]
        ids = (i for i, e in enumerate(self.entries) if e.uid in key)
        return self[ids]

    def bytype(self, tp):
        """
        Returns only entries that match the container type. Makes easier
        to filter out.
        This is a kind of costly operation. It builds each data container
        consecutively.
        """
        return (x for x in self.__iter__() if isinstance(x[3], tp))

    def bymagic(self, magic):
        """
        Returns all containers that contain data with specific magic id.
        
        :param int magic: magic value of a file type.
        """
        names = self.names
        return (
            (i, self.entries[i], names[i], self.get_container(i))
            for i in range(len(names))
            if names[i].file_type == magic
        )

    def files(self):
        """Returns all containers that contain file data."""
        names = self.names
        return (
            (i, self.entries[i], names[i], self.get_container(i))
            for i in range(len(names))
            if names[i].file_type != 0
        )

    def parse(self):
        # consts
        FORMATID = b"scimitar\x00"
        # aliases
        r = self.reader
        # check if appropriate file format
        formatid = r.read(9)
        assert (
            formatid == FORMATID
        ), "Wrong format id (expected %r, got %r)" % (FORMATID, formatid,)
        version = ruint32(r)
        header_offset = ruint32(r)
        self.x11 = ruint32(r)  # [0x11] = 0
        self.x15 = ruint32(r)  # [(0x15] = 0x10
        self.x19 = ruint32(r)  # [0x19] = 0
        self.x1d = ruint8(
            r
        )  # literally no correlation found to any data so far
        #
        self.num_entries = ruint32(r)  # files + hash entry + descriptor entry
        self.x22 = ruint32(r)  # [0x22] = 2
        self.x26 = ruint32(r)  # [0x26] = 0
        self.x2a = ruint32(r)  # [0x2a] = 0
        self.x2e = ruint32(r)  # [0x2e] = 0
        self.x32 = rint32(r)  # [0x32] = -1
        self.x36 = rint32(r)  # [0x36] = -1
        #
        self.num_plus2 = ruint32(r)  # num_entries+2 (what for?..)
        self.x3e = ruint32(r)  # [0x3e] = 1
        self.x4a = ruint32(r)  # [0x42] = 0x4a
        self.x46 = ruint32(r)  # [0x46] = 0
        #
        self.num2 = ruint32(r)  # num_entries again
        self.x4e = ruint32(r)  # [0x4e] = 2
        self.x52 = ruint32(r)  # [0x52] = 0x7a
        self.x56 = ruint32(r)  # [0x56] = 0
        self.x5a = rint32(r)  # [0x5a] = -1
        self.x5e = rint32(r)  # [0x5e] = -1
        self.x62 = ruint32(r)  # [0x62] = 0
        #
        self.num_plus1 = ruint32(r)  # [0x66] num_entries+1 (what for?..)
        self.names_offset = ruint64(r)  # [0x6a]
        self.lostfound = ruint64(r)  # [0x72]

        # entries @0x7A
        for i in range(self.num_entries):
            entry = Entry(r)
            self.entries.append(entry)

        # names
        r.seek(self.names_offset)
        for i in range(self.num_entries):
            nameentry = NameEntry(r)
            self.names.append(nameentry)

        # TODO: LOSTFOUND

    def get_container(self, index):
        """
        Get specific container by it's index.
        :param int index: container's index
        """
        r = self.reader
        entry = self.entries[index]
        start = entry.offset
        end = entry.end
        r.seek(start)
        contmagick = ruint32(r)
        constructor = Container.identify.get(contmagick, None)
        if constructor is None:
            log(
                "No constructor for container %i of style 0x%X (from "
                "0x%X to 0x%X), skipping" % (index, contmagick, start, end)
            )
            container = None
        else:
            container = constructor(r, entry)
        return container


class DepGraph(object):
    """
    Utility class designed to work with depgraphbin files. Contains
    only static functions.
    """

    def __init__(self):
        self.links = []

    def _process_return_(self, result, type="uids"):
        if type == "uids":
            return [result]

    def children_uids(self, uid):
        return [link.dst for link in self.links if link.src == uid]

    def parents_uids(self, uid):
        return [link.src for link in self.links if link.dst == uid]

    def child_in_links(self, uid):
        return [link for link in self.links if link.dst == uid]

    def parent_in_links(self, uid):
        return [link for link in self.links if link.src == uid]

    def are_linked(self, src, dst):
        for link in self.links:
            if link.src == src and link.dst == dst:
                return True
        return False

    @staticmethod
    def get_data_from_io(r, close=True):
        """
        Gets stream and unzips depgraph data from it. Might be useful
        when depgraph format changes again.
        :param r: input stream (assumed .depgraphbin file)
        :param close: whether to close stream after read or not
                      (default True)
        :return: unpacked data stream
        """
        assert ruint64(r) == 0x1014FA9957FBAA34, (
            "Invalid data type descriptor, file"
            "must start with 34 AA FB 57 99 FA 14 10"
        )
        reader = Container.File.Datablock(r).getstream()
        if close:
            r.close()
        return reader

    @staticmethod
    def parse_stream(unpacked, close=True):
        assert (
            ruint8(unpacked) == 0x02
        ), "Expected a 0x02 byte, got else, wrong depgraph type!"
        end = streamend(unpacked)
        links = []
        while unpacked.tell() < end:
            links.append(Link.parse(unpacked))
        return links

    def parse(instance, input):
        """
        Acts both as instance method and class method. If called from
        class, returns new DepGraph instance with links. If called from
        instance, appends new links to it's list.
        :param instance:
            cls or self, depends on caller
        :param typing.Union[str, io.IOBase] input:
            path to .depgraphbin file or io stream with serialized
            links data
        :return: DepGraph
        """
        # process input as file_path/io_stream
        if isinstance(input, (str, os.PathLike)):
            input = open(input, "rb")
        unpacked = DepGraph.get_data_from_io(input, close=True)
        links = DepGraph.parse_stream(unpacked, close=True)
        # process DepGraph as class/instance
        if instance == DepGraph:  # CLASS METHOD
            result = instance()
            result.links = links
        else:  # INSTANCE METHOD
            result = instance
            result.links = list(set(result.links + links))
        return result


class Link(object):
    """Describes link between 2 files."""

    def __init__(
        self, src=None, dst=None, x10=None, x14=None, x16=None, x17=None
    ):
        self.src = src
        self.dst = dst
        self.x10 = x10
        self.x14 = x14
        self.x16 = x16
        self.x17 = x17

    def __eq__(self, other):
        if isinstance(other, Link):
            return vars(self) == vars(other)
        return False

    def __hash__(self) -> int:
        return hash(
            (self.src, self.dst, self.x10, self.x14, self.x16, self.x17)
        )

    @staticmethod
    def parse(r):
        return Link(
            ruint64(r), ruint64(r), rint32(r), ruint16(r), ruint8(r), ruint8(r)
        )

    def __repr__(self):
        return "<Link: {}>".format(
            ", ".join(f"{k}={v}" for k, v in vars(self).items())
        )


# functions
# Forge
def parse(fpath, close=False):
    r = open(fpath, "rb")
    res = Forge(r)
    if close:
        r.close()
    return res


def getdatastream(input, r):
    """
    getdatastream(Datablock, InStream)
    getdatastream([Chunk, Chunk, ...], InStream)
    getdatastream(Chunk, InStream)
    
    Gets compressed chunk as input and returns :class:`io.BytesIO` with
    uncompressed data inside.
    
    Can also accept a  :class:`Container.File.Datablock`  containing a bunch
    of chunks or simply a ``list()`` of chunks.
    """
    result = io.BytesIO()
    if isinstance(input, Container.File.Datablock):  # got datablock as input
        chunks = input.chunks
    elif hasattr(input, "__iter__"):  # got list of chunks as input
        chunks = input
    elif isinstance(input, Container.File.Datablock.Chunk):  # got single chunk
        chunks = [input]
    else:
        raise ValueError(
            "Bad 'input attribute'. Acceptable calls are:\n"
            "            getdatastream(Datablock, InStream)\n"
            "            getdatastream([Chunk, Chunk, ...]], InStream)\n"
            "            getdatastream(Chunk, InStream)"
        )
    for chunk in chunks:
        r.seek(chunk.offset)
        if not chunk.ispacked:
            result.write(r.read(chunk.packed))
        else:
            dctx = zstd.ZstdDecompressor()
            dobj = dctx.decompressobj(write_size=chunk.unpacked)
            result.write(dobj.decompress(r.read(chunk.packed)))
    result.seek(0)
    return result


def getdata(datablock, r):
    handle = getdatastream(datablock, r)
    result = handle.getvalue()
    handle.close()
    return result


# Depgraph
def gather_links(fpaths):
    """
    Gather links from all paths
    :param typing.Union[typing.List[str], str] fpaths:
        path or list of paths to a file
    :return: DepGraph
    """
    if isinstance(fpaths, str):
        fpaths = [fpaths]
    result = DepGraph()
    for fpath in fpaths:
        result.parse(fpath)
    return result
