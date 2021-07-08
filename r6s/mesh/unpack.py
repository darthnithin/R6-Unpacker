#!python3
# -*- coding: utf-8 -*-
import struct

HALFS4 = struct.Struct("4h")
BYTEU4 = struct.Struct("4B")
FLOATH2 = struct.Struct("2e")
FLOAT3 = struct.Struct("3f")


def uint64_to_pos(r):
    x, y, z, s = HALFS4.unpack(r.read(8))
    return (x * s / 0x7FFF, y * s / 0x7FFF, z * s / 0x7FFF)


def uint32_to_vec(r):
    nx, ny, nz, ln = BYTEU4.unpack(r.read(4))
    return (nx / 0x7F - 1, ny / 0x7F - 1, nz / 0x7F - 1)


def uint32_to_color(r):
    r, g, b, a = BYTEU4.unpack(r.read(4))
    return r / 0xFF, g / 0xFF, b / 0xFF, a / 0xFF


def uint32_to_uv(r):
    return FLOATH2.unpack(r.read(4))


def read3floats(r):
    return FLOAT3.unpack(r.read(12))
