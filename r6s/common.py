#!python3
# -*- coding: utf-8 -*-
"""
This class is supposed to hold common structures that get used
frequently all over the place.
"""
from binstream import ruint64, ruint32
import io


class FileMeta(object):
    def __init__(self):
        self.encoded_meta = b""
        self.var1 = 0
        self.magic = 0
        self.uid = 0
        self.var2 = 0
        self.var3 = 0
        # var2 and var3 are almost always 0 (except for some entries in
        # datapc64.forge and maype couple others)

    @classmethod
    def parse(cls, r):
        self = cls()
        meta_len = ruint32(r)
        self.encoded_meta = r.read(meta_len)
        self.var1 = ruint32(r)
        self.magic = ruint32(r)
        self.uid = ruint64(r)
        assert self.magic == ruint32(
            r
        ), f"Second magic mismatch at 0x{r.tell()-4:h}!"
        self.var2 = ruint32(r)
        self.var3 = ruint32(r)
        return self


def read_file_piece(r):
    meta_size = ruint32(r)
    meta = io.BytesIO(r.read(meta_size))
    data_size = ruint32(r)
    magic = ruint32(r)
    data = io.BytesIO(r.read(data_size))
    return magic, meta, data
