"""Binary FBX reader mirroring Blender's io_scene_fbx/parse_fbx.py; validates structure."""
import struct, sys, zlib
from collections import Counter

HEAD = b'Kaydara FBX Binary  \x00'

def read_elem(f, data, off, ver):
    hdr = '<3I' if ver < 7500 else '<3Q'
    hs = struct.calcsize(hdr)
    end, nprops, plen = struct.unpack_from(hdr, data, off)
    off += hs
    if end == 0:
        return None, off
    nl = data[off]; off += 1
    name = data[off:off + nl].decode(); off += nl
    props = []
    pstart = off
    for _ in range(nprops):
        t = chr(data[off]); off += 1
        if t in 'YCIFDL':
            sz = {'Y': 2, 'C': 1, 'I': 4, 'F': 4, 'D': 8, 'L': 8}[t]
            fmt = {'Y': '<h', 'C': '<?', 'I': '<i', 'F': '<f', 'D': '<d', 'L': '<q'}[t]
            props.append(struct.unpack_from(fmt, data, off)[0]); off += sz
        elif t in 'fdlib':
            n, enc, clen = struct.unpack_from('<3I', data, off); off += 12
            raw = data[off:off + clen]; off += clen
            if enc == 1:
                raw = zlib.decompress(raw)
            isz = {'f': 4, 'd': 8, 'l': 8, 'i': 4, 'b': 1}[t]
            assert len(raw) == n * isz, (name, t, n, len(raw))
            props.append(struct.unpack('<%d%s' % (n, {'f': 'f', 'd': 'd', 'l': 'q', 'i': 'i', 'b': '?'}[t]), raw))
        elif t in 'SR':
            n = struct.unpack_from('<I', data, off)[0]; off += 4
            props.append(data[off:off + n]); off += n
        else:
            raise ValueError('bad prop type %r in %s' % (t, name))
    assert off - pstart == plen, ('prop length mismatch', name)
    kids = []
    if off < end:
        null = 13 if ver < 7500 else 25
        while off < end - null:
            k, off = read_elem(f, data, off, ver)
            kids.append(k)
        assert data[off:off + null] == b'\0' * null, ('missing sentinel', name)
        off += null
    assert off == end, ('end offset mismatch', name, off, end)
    return (name, props, kids), off

def main(path):
    data = open(path, 'rb').read()
    assert data[:21] == HEAD, 'bad header'
    ver = struct.unpack_from('<I', data, 23)[0]
    off = 27
    top = []
    while True:
        e, off = read_elem(None, data, off, ver)
        if e is None:
            break
        top.append(e)
    print('version', ver, 'top-level:', [e[0] for e in top])
    objs = next(e for e in top if e[0] == 'Objects')
    c = Counter(k[0] for k in objs[2])
    print('objects:', dict(c))
    tris = 0
    for k in objs[2]:
        if k[0] == 'Geometry':
            d = {g[0]: g for g in k[2]}
            pvi = d['PolygonVertexIndex'][1][0]
            nv = len(d['Vertices'][1][0]) // 3
            assert all((i if i >= 0 else ~i) < nv for i in pvi), 'index out of range'
            npoly = sum(1 for i in pvi if i < 0)
            le = {g[0]: g for g in d['LayerElementNormal'][2]}
            assert len(le['Normals'][1][0]) == 3 * len(pvi), 'normal count'
            lu = {g[0]: g for g in d['LayerElementUV'][2]}
            assert len(lu['UVIndex'][1][0]) == len(pvi), 'uv index count'
            lm = {g[0]: g for g in d['LayerElementMaterial'][2]}
            assert len(lm['Materials'][1][0]) == npoly, 'material count'
            tris += npoly
    conns = next(e for e in top if e[0] == 'Connections')
    print('connections:', len(conns[2]), 'triangles:', tris)
    print('footer bytes after records:', len(data) - off)
    print('OK')

if __name__ == '__main__':
    main(sys.argv[1])
