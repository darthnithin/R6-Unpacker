from binstream import ruint8, ruint16, rint32, ruint32, ruint64, termstr
import r6s.common as rc
import io


def split_asset(r):
    assets = []
    while len(r.read(1)):  # wacky way to test for EOF
        r.seek(-1, io.SEEK_CUR)  # rewind after test
        assets.append(rc.read_file_piece(r))
    return assets


def filter_by_magic(assets, magic):
    result = []
    for asset in assets:
        if asset[0] == magic:
            result.append(asset)
    return result


def parse_shader(r):
    vert_shader_len = ruint32(r)
    vert_shader = r.read(vert_shader_len)
    r.read(1)  # skip terminating x00
    pix_shader_len = ruint32(r)
    pix_shader = r.read(pix_shader_len)
    r.read(1)  # skip terminating x00
    r.read(0x10)  # skip padding or whatever it is
    num_entries = ruint32(r)
    r.read(1)  # skip 1 extra byte
    tail = r.read()
    return vert_shader.decode(), pix_shader.decode(), tail
