"""Mesh building helpers + a minimal glTF 2.0 (.glb) writer.

Vertex attribute conventions shared with the Godot shaders (see shaders/*.gdshader):
  COLOR.r  baked ambient occlusion (0 dark .. 1 open)
  COLOR.g  branch sway weight (0 on the trunk .. 1 at branch tips)
  COLOR.b  leaf flutter weight (0 .. 1)
  COLOR.a  per-branch wind phase (0 .. 1)
  UV2.x    bark: texture-array layer (+0.5 = dead wood); foliage: translucency scale
  UV2.y    normalised height inside the plant (0 at the ground .. 1 at the top)
"""
from __future__ import annotations

import json
import math
import struct

import numpy as np


def normalize(v, axis=-1):
    n = np.linalg.norm(v, axis=axis, keepdims=True)
    return v / np.maximum(n, 1e-9)


class Surface:
    def __init__(self, name: str, alpha: bool = False):
        self.name, self.alpha = name, alpha
        self.pos, self.nrm, self.uv, self.uv2, self.col, self.idx = [], [], [], [], [], []
        self.nv = 0

    def add(self, pos, nrm, uv, uv2, col, idx):
        pos = np.asarray(pos, np.float32).reshape(-1, 3)
        n = len(pos)
        self.pos.append(pos)
        self.nrm.append(np.asarray(nrm, np.float32).reshape(n, 3))
        self.uv.append(np.asarray(uv, np.float32).reshape(n, 2))
        self.uv2.append(np.broadcast_to(np.asarray(uv2, np.float32), (n, 2)).copy())
        self.col.append(np.broadcast_to(np.asarray(col, np.float32), (n, 4)).copy())
        self.idx.append(np.asarray(idx, np.uint32).reshape(-1) + self.nv)
        self.nv += n

    @property
    def tris(self):
        return sum(len(i) for i in self.idx) // 3

    def arrays(self):
        if not self.pos:
            return None
        return dict(pos=np.concatenate(self.pos), nrm=normalize(np.concatenate(self.nrm)),
                    uv=np.concatenate(self.uv), uv2=np.concatenate(self.uv2),
                    col=np.clip(np.concatenate(self.col), 0, 1), idx=np.concatenate(self.idx))


class Mesh:
    """A set of surfaces (one per material)."""

    def __init__(self, *surfaces: tuple[str, bool]):
        self.s = {n: Surface(n, a) for n, a in surfaces}

    def __getitem__(self, k) -> Surface:
        return self.s[k]

    @property
    def tris(self):
        return sum(s.tris for s in self.s.values())

    def bounds(self):
        ps = [np.concatenate(s.pos) for s in self.s.values() if s.pos]
        p = np.concatenate(ps)
        return p.min(0), p.max(0)


# ---------------------------------------------------------------- primitives
def frames_along(points: np.ndarray):
    """Parallel-transport frames (tangent, normal, binormal) along a polyline."""
    n = len(points)
    t = np.zeros((n, 3))
    t[1:-1] = points[2:] - points[:-2]
    t[0] = points[1] - points[0]
    t[-1] = points[-1] - points[-2]
    t = normalize(t)
    ref = np.array([0.0, 0.0, 1.0]) if abs(t[0][1]) > 0.9 or abs(t[0][2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    if abs(np.dot(ref, t[0])) > 0.9:
        ref = np.array([1.0, 0.0, 0.0])
    nrm = np.zeros((n, 3)); bi = np.zeros((n, 3))
    nrm[0] = normalize(np.cross(t[0], ref)); bi[0] = np.cross(t[0], nrm[0])
    for i in range(1, n):
        b = np.cross(t[i - 1], t[i])
        bl = np.linalg.norm(b)
        v = nrm[i - 1]
        if bl > 1e-8:
            b /= bl
            ang = math.acos(max(-1.0, min(1.0, float(np.dot(t[i - 1], t[i])))))
            # Rodrigues rotation of v around b by ang
            v = v * math.cos(ang) + np.cross(b, v) * math.sin(ang) + b * np.dot(b, v) * (1 - math.cos(ang))
        v = normalize(v - t[i] * np.dot(v, t[i]))
        nrm[i] = v; bi[i] = np.cross(t[i], v)
    return t, nrm, bi


def tube(surf: Surface, points, radii, sides: int, layer: float, u_repeat: float, v_scale: float,
         sway, phase: float, hnorm, ao=None, radial_mod=None, cap_end=False, v0: float = 0.0):
    """Generalised cylinder along points with per-point radius.

    sway/hnorm/ao: per-point arrays (or scalars). radial_mod(i, theta) -> radius multiplier.
    Returns the accumulated v at the end (for continuing UVs on children).
    """
    points = np.asarray(points, np.float64)
    k = len(points)
    radii = np.broadcast_to(np.asarray(radii, np.float64), (k,))
    sway = np.broadcast_to(np.asarray(sway, np.float64), (k,))
    hnorm = np.broadcast_to(np.asarray(hnorm, np.float64), (k,))
    ao = np.broadcast_to(np.asarray(1.0 if ao is None else ao, np.float64), (k,))
    t, nr, bi = frames_along(points)
    th = np.linspace(0, 2 * math.pi, sides + 1)
    seg = np.linalg.norm(np.diff(points, axis=0), axis=1)
    vacc = v0 + np.concatenate([[0], np.cumsum(seg)]) * v_scale
    P, N, UV, UV2, C = [], [], [], [], []
    for i in range(k):
        for j, a in enumerate(th):
            d = nr[i] * math.cos(a) + bi[i] * math.sin(a)
            r = radii[i] * (radial_mod(i, a) if radial_mod else 1.0)
            P.append(points[i] + d * r)
            N.append(d)
            UV.append((j / sides * u_repeat, vacc[i]))
            UV2.append((layer, hnorm[i]))
            C.append((ao[i], sway[i], 0.0, phase))
    idx = []
    row = sides + 1
    for i in range(k - 1):
        for j in range(sides):
            a, b = i * row + j, i * row + j + 1
            c, d = (i + 1) * row + j, (i + 1) * row + j + 1
            idx += [a, c, b, b, c, d]
    P = np.array(P); N = np.array(N)
    if radial_mod is not None:
        # recompute normals from the deformed surface (finite differences on the grid)
        G = P.reshape(k, row, 3)
        du = np.roll(G, -1, axis=1) - np.roll(G, 1, axis=1)
        du[:, 0] = G[:, 1] - G[:, -2]; du[:, -1] = du[:, 0]
        dv = np.zeros_like(G); dv[1:-1] = G[2:] - G[:-2]; dv[0] = G[1] - G[0]; dv[-1] = G[-1] - G[-2]
        nn = normalize(np.cross(dv, du)).reshape(-1, 3)
        flip = np.sum(nn * N, axis=1) < 0
        nn[flip] *= -1
        N = nn
    surf.add(P, N, UV, UV2, C, idx)
    if cap_end:  # broken / cut end: a flat cap
        c0 = surf.nv
        cp = points[-1]; tn = t[-1]
        ring = [cp + (nr[-1] * math.cos(a) + bi[-1] * math.sin(a)) * radii[-1] * 0.95 for a in th[:-1]]
        Pc = [cp] + ring
        Nc = [tn] * len(Pc)
        UVc = [(0.5, vacc[-1])] + [(0.5 + 0.3 * math.cos(a), vacc[-1] + 0.3 * math.sin(a)) for a in th[:-1]]
        id2 = []
        for j in range(sides):
            id2 += [0, 1 + j, 1 + (j + 1) % sides]
        surf.add(Pc, Nc, UVc, (layer, hnorm[-1]), (ao[-1] * 0.8, sway[-1], 0.0, phase), id2)
    return float(vacc[-1])


def card(surf: Surface, base, up, right, width, height, rect, anchor=(0.5, 1.0), axis="up",
         normal_hint=None, bend=0.0, segs=1, ao=1.0, sway=1.0, flutter=1.0, phase=0.0, hnorm=0.5,
         translucency=1.0, flip_u=False, bend_dir=None):
    """Alpha-cut foliage card.

    rect: atlas (x, y, w, h) in image space (y down). The sprite's growth axis ('up' = image up,
    'right' = image +x, 'down' = image down) is mapped onto the world 'up' vector; anchor is the
    attachment point in sprite-fraction coordinates (image space).
    bend: droop at the far end (metres) along bend_dir (default world -Y).
    """
    up = normalize(np.asarray(up, np.float64)); right = normalize(np.asarray(right, np.float64))
    base = np.asarray(base, np.float64)
    rx, ry, rw, rh = rect
    # sprite-space axes: s along growth, w across.
    if axis == "up":
        a_s, a_w = 1.0 - anchor[1], anchor[0]
        def uv_of(s, w):  # s: 0..1 along growth (fraction of height), w: 0..1 across
            return (rx + w * rw, ry + (1.0 - s) * rh)
        L, W = height, width
    elif axis == "right":
        a_s, a_w = anchor[0], 1.0 - anchor[1]
        def uv_of(s, w):
            return (rx + s * rw, ry + (1.0 - w) * rh)
        L, W = width, height
    else:  # down (hanging)
        a_s, a_w = anchor[1], 1.0 - anchor[0]
        def uv_of(s, w):
            return (rx + (1.0 - w) * rw, ry + s * rh)
        L, W = height, width
    if flip_u:
        _uv = uv_of
        def uv_of(s, w):  # noqa: F811
            return _uv(s, 1.0 - w)
    n_face = normalize(np.cross(right, up))
    nh = n_face if normal_hint is None else normalize(np.asarray(normal_hint, np.float64))
    bdir = np.array([0.0, -1.0, 0.0]) if bend_dir is None else normalize(np.asarray(bend_dir, np.float64))
    P, N, UV = [], [], []
    for i in range(segs + 1):
        s = i / segs
        along = (s - a_s) * L
        droop = bend * max(s - a_s, 0.0) ** 2 / max(1.0 - a_s, 1e-3) ** 2 if bend else 0.0
        for w in (0.0, 1.0):
            off = (w - a_w) * W
            P.append(base + up * along + right * off + bdir * droop)
            N.append(nh)
            UV.append(uv_of(s, w))
    idx = []
    for i in range(segs):
        a, b, c, d = 2 * i, 2 * i + 1, 2 * i + 2, 2 * i + 3
        idx += [a, b, c, b, d, c]
    # sway: increases toward the free end; flutter on the leaves
    sw = [min(1.0, sway * (0.85 + 0.15 * (i / segs))) for i in range(segs + 1) for _ in (0, 1)]
    C = [(ao, s_, flutter, phase) for s_ in sw]
    surf.add(P, N, UV, (translucency, hnorm), C, idx)


# ------------------------------------------------------------------- glTF out
def write_glb(path: str, nodes: list[tuple[str, "Mesh"]], materials: list[tuple[str, bool]]):
    """nodes: [(node_name, Mesh)], materials: [(name, alpha_mask)] — surfaces map by name."""
    bin_parts: list[bytes] = []
    views, accessors, meshes, gnodes = [], [], [], []
    offset = 0

    def push(arr: np.ndarray, target: int | None, ctype: int, typ: str, minmax=False):
        nonlocal offset
        data = arr.tobytes()
        pad = (-len(data)) % 4
        views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(data), **({"target": target} if target else {})})
        bin_parts.append(data + b"\0" * pad)
        offset += len(data) + pad
        acc = {"bufferView": len(views) - 1, "componentType": ctype, "count": int(arr.shape[0]), "type": typ}
        if minmax:
            acc["min"] = arr.min(axis=0).tolist(); acc["max"] = arr.max(axis=0).tolist()
        accessors.append(acc)
        return len(accessors) - 1

    mat_index = {n: i for i, (n, _) in enumerate(materials)}
    for name, mesh in nodes:
        prims = []
        for sname, surf in mesh.s.items():
            a = surf.arrays()
            if a is None:
                continue
            idx = a["idx"]
            ib = idx.astype(np.uint16) if a["pos"].shape[0] < 65536 else idx.astype(np.uint32)
            prims.append({
                "attributes": {
                    "POSITION": push(a["pos"].astype(np.float32), 34962, 5126, "VEC3", True),
                    "NORMAL": push(a["nrm"].astype(np.float32), 34962, 5126, "VEC3"),
                    "TEXCOORD_0": push(a["uv"].astype(np.float32), 34962, 5126, "VEC2"),
                    "TEXCOORD_1": push(a["uv2"].astype(np.float32), 34962, 5126, "VEC2"),
                    "COLOR_0": push(a["col"].astype(np.float32), 34962, 5126, "VEC4"),
                },
                "indices": push(ib, 34963, 5123 if ib.dtype == np.uint16 else 5125, "SCALAR"),
                "material": mat_index[sname],
            })
        if not prims:
            continue
        meshes.append({"name": name, "primitives": prims})
        gnodes.append({"name": name, "mesh": len(meshes) - 1})
    gl = {
        "asset": {"version": "2.0", "generator": "forest_drive/tools/meshkit.py"},
        "scene": 0, "scenes": [{"nodes": list(range(len(gnodes)))}],
        "nodes": gnodes, "meshes": meshes,
        "materials": [{"name": n, "doubleSided": bool(a), "alphaMode": "MASK" if a else "OPAQUE",
                       **({"alphaCutoff": 0.5} if a else {}),
                       "pbrMetallicRoughness": {"baseColorFactor": [0.4, 0.5, 0.3, 1] if a else [0.4, 0.3, 0.2, 1],
                                                "metallicFactor": 0.0, "roughnessFactor": 0.8}} for n, a in materials],
        "accessors": accessors, "bufferViews": views, "buffers": [{"byteLength": offset}],
    }
    js = json.dumps(gl, separators=(",", ":")).encode()
    js += b" " * ((-len(js)) % 4)
    binb = b"".join(bin_parts)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(binb)))
        f.write(struct.pack("<II", len(js), 0x4E4F534A)); f.write(js)
        f.write(struct.pack("<II", len(binb), 0x004E4942)); f.write(binb)
