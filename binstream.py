from struct import unpack as upk, pack as pk, calcsize as csz

def streamend(s):
    """Hacky way to get a stream contents length. Intended to be used with
    finite length streams."""
    cursor = s.tell()
    s.seek(0, 2)
    end = s.tell()
    s.seek(cursor, 0)
    return end

def termstr(s):
    """Truncate string to terminating \x00"""
    return s[:s.find(b'\x00')]

# read from binary to data
def rint8(r):
    """Read byte from stream r. Returns int."""
    return upk('b', r.read(1))[0]
def ruint8(r):
    """Read unsigned byte from stream r. Returns int."""
    return upk('B', r.read(1))[0]
def rint16(r):
    """Read int16 from stream r. Returns int."""
    return upk('h', r.read(2))[0]
def ruint16(r):
    """Read uint16 from stream r. Returns int."""
    return upk('H', r.read(2))[0]
def rint32(r):
    """Read int32 from stream r. Returns int."""
    return upk('i', r.read(4))[0]
def ruint32(r):
    """Read uint32 from stream r. Returns int."""
    return upk('I', r.read(4))[0]
def rint64(r):
    """Read int64 from stream r. Returns int."""
    return upk('q', r.read(8))[0]
def ruint64(r):
    """Read uint64 from stream r. Returns int."""
    return upk('Q', r.read(8))[0]
def rfloat(r):
    """Read float32 from stream r. Returns float."""
    return upk('f', r.read(4))[0]
def rdouble(r):
    """Read float64 from stream r. Returns float."""
    return upk('d', r.read(8))[0]
def ras(r, fmt):
    """Read data formatted as fmt from stream r. fmt uses format characters from
    struct module. Returns a tuple of values."""
    return upk(fmt, r.read(csz(fmt)))

# write data to binary representation
def wint8(w, d):
    """Write data d as int8 to stream w."""
    w.write(pk('b', d))
def wuint8(w, d):
    """Write data d as uint8 to stream w."""
    w.write(pk('B', d))
def wint16(w, d):
    """Write data d as int16 to stream w."""
    w.write(pk('h', d))
def wuint16(w, d):
    """Write data d as uint16 to stream w."""
    w.write(pk('H', d))
def wint32(w, d):
    """Write data d as int32 to stream w."""
    w.write(pk('i', d))
def wuint32(w, d):
    """Write data d as uint32 to stream w."""
    w.write(pk('I', d))
def wint64(w, d):
    """Write data d as int64 to stream w."""
    w.write(pk('q', d))
def wuint64(w, d):
    """Write data d as uint64 to stream w."""
    w.write(pk('Q', d))
def wfloat(w, d):
    """Write float d to stream w as float."""
    w.write(pk('f', d))
def wdouble(w, d):
    """Write float d to stream w as double."""
    w.write(pk('d', d))
def was(w, fmt, *d):
    """Write args of fmt to stream w. A direct wrapper around pack(fmt, *d)"""
    w.write(pk(fmt, *d))

# convert string or bits to data
def sint8(s):
    """Convert string to byte. Returns int."""
    return upk('b', s)[0]
def suint8(s):
    """Convert string to unsigned byte. Returns int."""
    return upk('B', s)[0]
def sint16(s):
    """Convert string to int16. Returns int."""
    return upk('h', s)[0]
def suint16(s):
    """Convert string to uint16. Returns int."""
    return upk('H', s)[0]
def sint32(s):
    """Convert string to int32. Returns int."""
    return upk('i', s)[0]
def suint32(s):
    """Convert string to uint32. Returns int."""
    return upk('I', s)[0]
def sint64(s):
    """Convert string to int64. Returns int."""
    return upk('q', s)[0]
def suint64(s):
    """Convert string to uint64. Returns int."""
    return upk('Q', s)[0]
def sfloat(s):
    """Convert string to float32. Returns float."""
    return upk('f', s)[0]
def sdouble(s):
    """Convert string to float64. Returns float."""
    return upk('d', s)[0]
def sas(s, fmt):
    """Convert string according to fmt. fmt uses format characters from struct
    module. Returns a tuple of values."""
    return upk(fmt, s)

# convert data to bytes
def uint32s(v):
    """Convert value to uint32. returns bytes string[4]."""
    return pk('I',v)