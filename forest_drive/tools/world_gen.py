#!/usr/bin/env python3
"""Generate the Forest Drive world: road centreline, terrain heightmap (with the road corridor,
shoulders, ditches and cut/fill embankments carved in), material control maps, canopy density,
and the placement of every tree, plant, rock and prop.

Outputs (resources/world/):
  heightmap.f32.gz      (N x N float32 metres, gzip)       N = 2049, 1 m spacing
  terrain_normal.png    RGB world normal (x, z, y)          N x N
  control0.png          R litter  G needles  B moss  A grass   (layer weights)
  control1.png          R soil    G gravel   B canopy A wetness
  road.json             centreline samples (x, y, z) every 1 m, closed loop
  inst_<set>.bin.gz     pre-baked MultiMesh buffers (16 floats / instance) grouped by variant + cell
  world.json            metadata (sizes, files, counts)

Usage: python3 tools/world_gen.py        (after build_assets.py wrote assets/catalog.json)
"""
from __future__ import annotations

import gzip
import json
import math
import os
import struct
import sys
import time

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import texlib as T  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "resources", "world")
SEED = 20261108
N = 2049
SIZE = 2048.0
ORIGIN = -1024.0
ROAD_HALF_ASPHALT = 4.10
ROAD_EDGE = 5.0          # outer edge of the gravel shoulder (road mesh)
rng = np.random.default_rng(SEED)


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


# --------------------------------------------------------------------- road
# Hand-designed control polygon: long north straight, S-bends in the east, a long south
# straight and a chicane in the west. Interpolated with a centripetal Catmull-Rom spline.
CTRL = np.array([
    (-620, 300), (-430, 372), (-140, 402), (160, 400), (320, 372), (418, 292), (438, 180), (376, 64),
    (418, -62), (502, -150), (522, -286), (456, -418), (326, -498), (140, -520), (-90, -500), (-300, -470),
    (-442, -418), (-520, -326), (-498, -206), (-560, -106), (-652, -24), (-668, 92), (-662, 204),
], dtype=np.float64)


def catmull_closed(P, n_per=160, alpha=0.5):
    out = []
    n = len(P)
    for i in range(n):
        p0, p1, p2, p3 = P[(i - 1) % n], P[i], P[(i + 1) % n], P[(i + 2) % n]
        def tj(ti, pi, pj):
            return ti + np.linalg.norm(pj - pi) ** alpha
        t0 = 0.0; t1 = tj(t0, p0, p1); t2 = tj(t1, p1, p2); t3 = tj(t2, p2, p3)
        for t in np.linspace(t1, t2, n_per, endpoint=False):
            A1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            A2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            A3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            B1 = (t2 - t) / (t2 - t0) * A1 + (t - t0) / (t2 - t0) * A2
            B2 = (t3 - t) / (t3 - t1) * A2 + (t - t1) / (t3 - t1) * A3
            out.append((t2 - t) / (t2 - t1) * B1 + (t - t1) / (t2 - t1) * B2)
    return np.array(out)


def smooth_path_closed(xz, sigma):
    return np.stack([smooth_closed(xz[:, 0], sigma), smooth_closed(xz[:, 1], sigma)], 1)


def resample_closed(pts, step):
    d = np.linalg.norm(np.diff(np.vstack([pts, pts[:1]]), axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(d)])
    L = s[-1]
    n = int(round(L / step))
    st = np.linspace(0, L, n, endpoint=False)
    ext = np.vstack([pts, pts[:1]])
    x = np.interp(st, s, ext[:, 0]); z = np.interp(st, s, ext[:, 1])
    return np.stack([x, z], 1), L


# ------------------------------------------------------------------ terrain
def base_terrain():
    big = T.fft_noise(2048, 3.3, SEED + 1, lo=1.2)
    mid = T.fft_noise(2048, 2.2, SEED + 2, lo=14, hi=110)
    hum = T.fft_noise(2048, 1.8, SEED + 3, lo=110, hi=500)
    rough = T.fft_noise(2048, 2.0, SEED + 4, lo=3, hi=40)
    h = (big - 0.5) * 46.0
    h += (mid - 0.5) * 4.5 * (0.6 + 0.8 * rough)
    h += (hum - 0.5) * 0.7
    h = np.pad(h, ((0, 1), (0, 1)), mode="wrap")
    return h.astype(np.float64)


def smooth_closed(v, sigma):
    n = len(v)
    k = np.exp(-0.5 * (np.arange(-4 * sigma, 4 * sigma + 1) / sigma) ** 2); k /= k.sum()
    ext = np.concatenate([v[-len(k):], v, v[:len(k)]])
    return np.convolve(ext, k, mode="same")[len(k):len(k) + n]


def grade_limit(z, step, g):
    z = z.copy()
    for _ in range(6):
        for i in range(len(z)):
            z[i] = np.clip(z[i], z[i - 1] - g * step, z[i - 1] + g * step)
        for i in range(len(z) - 1, -1, -1):
            j = (i + 1) % len(z)
            z[i] = np.clip(z[i], z[j] - g * step, z[j] + g * step)
    return z


def bilinear(h, x, z):
    fx = np.clip(x - ORIGIN, 0, N - 1.001); fz = np.clip(z - ORIGIN, 0, N - 1.001)
    ix = fx.astype(int); iz = fz.astype(int); tx = fx - ix; tz = fz - iz
    a = h[iz, ix]; b = h[iz, ix + 1]; c = h[iz + 1, ix]; d = h[iz + 1, ix + 1]
    return (a * (1 - tx) + b * tx) * (1 - tz) + (c * (1 - tx) + d * tx) * tz


def road_mesh_profile(ad):
    """Height of the road mesh relative to the centreline height at lateral distance ad (>= 0)."""
    y = -0.02 * np.minimum(ad, ROAD_HALF_ASPHALT)
    edge = (ad > ROAD_HALF_ASPHALT) & (ad <= 4.16)
    y = np.where(edge, -0.082 - (ad - ROAD_HALF_ASPHALT) / 0.06 * 0.038, y)
    grav = ad > 4.16
    y = np.where(grav, -0.12 - (np.minimum(ad, ROAD_EDGE) - 4.16) * (0.08 / 0.84), y)
    return y


def carve(h, road_xz, road_z):
    log("carving road corridor")
    tree = cKDTree(road_xz)
    gx = ORIGIN + np.arange(N)
    X, Z = np.meshgrid(gx, gx)
    P = np.stack([X.ravel(), Z.ravel()], 1)
    dist, idx = tree.query(P, k=1, distance_upper_bound=120.0, workers=-1)
    far = ~np.isfinite(dist)
    idx[far] = 0
    n = len(road_xz)
    tang = road_xz[(idx + 1) % n] - road_xz[(idx - 1) % n]
    tang /= np.linalg.norm(tang, axis=1, keepdims=True)
    rel = P - road_xz[idx]
    along = np.sum(rel * tang, axis=1)
    lat = rel[:, 0] * -tang[:, 1] + rel[:, 1] * tang[:, 0]    # signed lateral (left +)
    # interpolate road height along the segment for accuracy
    j = np.where(along >= 0, (idx + 1) % n, (idx - 1) % n)
    zr = road_z[idx] + (road_z[j] - road_z[idx]) * np.minimum(np.abs(along), 1.0)
    ad = np.abs(lat)
    ad[far] = 1e3
    hn = h.ravel()
    t = np.empty_like(hn)
    # under the road mesh: 7 cm below its surface
    under = ad < ROAD_EDGE
    t[under] = zr[under] + road_mesh_profile(ad[under]) - 0.07
    # ditch + berm
    def smooth01(x):
        x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)
    edge_h = -0.22
    ditch_d = -0.42
    berm = -0.30
    m1 = (ad >= ROAD_EDGE) & (ad < 6.4)
    t[m1] = zr[m1] + edge_h + (ditch_d - edge_h) * smooth01((ad[m1] - ROAD_EDGE) / 1.4)
    m2 = (ad >= 6.4) & (ad < 7.8)
    t[m2] = zr[m2] + ditch_d + (berm - ditch_d) * smooth01((ad[m2] - 6.4) / 1.4)
    m3 = ad >= 7.8
    bh = zr[m3] + berm
    diff = hn[m3] - bh
    width = np.clip(np.abs(diff) * 2.2, 4.0, 45.0)
    w = smooth01((ad[m3] - 9.0) / width)
    t[m3] = bh + diff * w
    out = t.reshape(N, N)
    lat_map = lat.reshape(N, N).astype(np.float32); lat_map[far.reshape(N, N)] = 1e3
    return out, lat_map, idx.reshape(N, N), zr.reshape(N, N)


# ----------------------------------------------------------------- placement
CAT = json.load(open(os.path.join(ROOT, "assets", "catalog.json")))["variants"]
VAR = {v["name"]: v for v in CAT}


def instance_rows(x, y, z, yaw, scale, normal=None, align=0.0, tilt=None, custom=None):
    """Build MultiMesh 3D buffer rows (12 floats) + 4 custom floats for arrays of instances."""
    n = len(x)
    cy, sy = np.cos(yaw), np.sin(yaw)
    # rotation about Y
    R = np.zeros((n, 3, 3))
    R[:, 0, 0] = cy; R[:, 0, 2] = sy; R[:, 1, 1] = 1; R[:, 2, 0] = -sy; R[:, 2, 2] = cy
    if normal is not None and np.any(align > 0):
        up = np.zeros((n, 3)); up[:, 1] = 1
        tgt = up * (1 - align[:, None]) + normal * align[:, None]
        tgt /= np.linalg.norm(tgt, axis=1, keepdims=True)
        axis = np.cross(up, tgt)
        s = np.linalg.norm(axis, axis=1)
        c = tgt[:, 1]
        k = np.where(s[:, None] > 1e-6, axis / np.maximum(s[:, None], 1e-9), 0)
        K = np.zeros((n, 3, 3))
        K[:, 0, 1] = -k[:, 2]; K[:, 0, 2] = k[:, 1]; K[:, 1, 0] = k[:, 2]
        K[:, 1, 2] = -k[:, 0]; K[:, 2, 0] = -k[:, 1]; K[:, 2, 1] = k[:, 0]
        I = np.eye(3)[None]
        A = I + K * s[:, None, None] + np.einsum("nij,njk->nik", K, K) * (1 - c)[:, None, None]
        R = np.einsum("nij,njk->nik", A, R)
    if tilt is not None:
        R = np.einsum("nij,njk->nik", tilt, R)
    M = R * scale[:, None, None]
    rows = np.zeros((n, 16), np.float32)
    rows[:, 0:3] = M[:, 0, :]; rows[:, 3] = x
    rows[:, 4:7] = M[:, 1, :]; rows[:, 7] = y
    rows[:, 8:11] = M[:, 2, :]; rows[:, 11] = z
    if custom is not None:
        rows[:, 12:16] = custom
    return rows


class InstanceSet:
    def __init__(self, name, cell):
        self.name, self.cell = name, cell
        self.items = {}   # variant -> list of row arrays

    def add(self, variant, rows):
        if len(rows):
            self.items.setdefault(variant, []).append(rows)

    def write(self):
        gridn = int(SIZE // self.cell)
        header = {"stride": 16, "cell": self.cell, "grid": gridn, "origin": ORIGIN, "variants": []}
        blobs = []
        off = 0
        for v, lst in sorted(self.items.items()):
            rows = np.concatenate(lst)
            cx = np.clip(((rows[:, 3] - ORIGIN) // self.cell).astype(int), 0, gridn - 1)
            cz = np.clip(((rows[:, 11] - ORIGIN) // self.cell).astype(int), 0, gridn - 1)
            cid = cz * gridn + cx
            order = np.lexsort((rng.random(len(cid)), cid))
            rows = rows[order]; cid = cid[order]
            uniq, start, cnt = np.unique(cid, return_index=True, return_counts=True)
            header["variants"].append({"name": v, "offset": off, "count": int(len(rows)),
                                       "cells": np.stack([uniq, start, cnt], 1).astype(int).tolist()})
            blobs.append(rows.astype(np.float32).tobytes())
            off += len(rows)
        js = json.dumps(header, separators=(",", ":")).encode()
        payload = b"FDI1" + struct.pack("<I", len(js)) + js + b"".join(blobs)
        path = os.path.join(OUT, f"inst_{self.name}.bin.gz")
        with gzip.open(path, "wb", compresslevel=6) as f:
            f.write(payload)
        total = sum(v["count"] for v in header["variants"])
        log(f"inst_{self.name}: {total} instances, {len(header['variants'])} variants, {os.path.getsize(path) / 1e6:.1f} MB")
        return total


def jittered(spacing, mask_fn=None, bounds=None):
    x0, x1, z0, z1 = bounds or (ORIGIN + 2, ORIGIN + SIZE - 2, ORIGIN + 2, ORIGIN + SIZE - 2)
    gx = np.arange(x0, x1, spacing); gz = np.arange(z0, z1, spacing)
    X, Z = np.meshgrid(gx, gz)
    X = X.ravel() + rng.uniform(0, spacing, X.size); Z = Z.ravel() + rng.uniform(0, spacing, Z.size)
    return X, Z


def main():
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    # ------------------------------------------------------------ road + terrain
    curve = catmull_closed(CTRL)
    road_xz, L = resample_closed(curve, 1.0)
    road_xz = smooth_path_closed(road_xz, 15.0)
    road_xz, L = resample_closed(road_xz, 1.0)
    log(f"road loop length {L:.0f} m, {len(road_xz)} samples")
    # curvature check
    k = 5
    d1 = (np.roll(road_xz, -k, 0) - np.roll(road_xz, k, 0)) / (2 * k)
    d2 = (np.roll(road_xz, -k, 0) - 2 * road_xz + np.roll(road_xz, k, 0)) / (k * k)
    curv = np.abs(d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]) / np.linalg.norm(d1, axis=1) ** 3
    log(f"min curve radius {1 / max(curv.max(), 1e-9):.0f} m, straight share {np.mean(curv < 1 / 800):.0%}")
    h = base_terrain()
    zr = bilinear(h, road_xz[:, 0], road_xz[:, 1])
    zr = smooth_closed(zr, 70)
    zr = grade_limit(zr, 1.0, 0.065)
    zr = smooth_closed(zr, 12)
    log(f"road elevation {zr.min():.1f} .. {zr.max():.1f} m, max grade {np.abs(np.diff(zr)).max() * 100:.1f}%")
    h, lat, ridx, zroad = carve(h, road_xz, zr)
    ad = np.abs(lat)
    h = h.astype(np.float32)
    # normals
    gz_, gx_ = np.gradient(h.astype(np.float64))
    nrm = np.stack([-gx_, np.ones_like(gx_), -gz_], -1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    slope = 1 - nrm[..., 1]
    with gzip.open(os.path.join(OUT, "heightmap.f32.gz"), "wb", compresslevel=6) as f:
        f.write(h.astype("<f4").tobytes())
    Image.fromarray((np.stack([nrm[..., 0], nrm[..., 2], nrm[..., 1]], -1) * 127.5 + 127.5).clip(0, 255).astype(np.uint8)).save(
        os.path.join(OUT, "terrain_normal.png"), optimize=True)
    log(f"terrain {h.min():.1f} .. {h.max():.1f} m")
    with open(os.path.join(OUT, "road.json"), "w") as f:
        json.dump({"closed": True, "spacing": 1.0, "length": round(L, 2), "half_asphalt": ROAD_HALF_ASPHALT,
                   "edge": ROAD_EDGE, "lane_width": 3.4,
                   "points": np.round(np.stack([road_xz[:, 0], zr, road_xz[:, 1]], 1), 3).tolist()}, f)

    def H(x, z):
        return bilinear(h, x, z)

    def NRM(x, z):
        ix = np.clip(np.round(x - ORIGIN).astype(int), 0, N - 1); iz = np.clip(np.round(z - ORIGIN).astype(int), 0, N - 1)
        return nrm[iz, ix]

    road_kd = cKDTree(road_xz)

    def LAT(x, z):
        """Exact horizontal distance to the road centreline (1 m samples; error < 3 cm beyond the shoulder)."""
        d, _ = road_kd.query(np.stack([np.asarray(x, np.float64), np.asarray(z, np.float64)], 1), workers=-1)
        return d

    # ------------------------------------------------------------ ecological fields (4 m grid)
    def field(beta, lo, seed, hi=None):
        f = T.fft_noise(512, beta, seed, lo=lo, hi=hi)
        return np.asarray(Image.fromarray(np.pad(f, ((0, 1), (0, 1)), mode="wrap").astype(np.float32), "F").resize((N, N), Image.BILINEAR))
    moist = ndimage.gaussian_filter(-h.astype(np.float64), 40)
    moist = (moist - moist.min()) / (moist.max() - moist.min())
    moist = np.clip(moist * 0.7 + field(2.5, 2, SEED + 10) * 0.5 - 0.1, 0, 1).astype(np.float32)
    density = field(2.4, 2, SEED + 11)
    clearing = np.clip((field(2.8, 2, SEED + 12) - 0.72) * 6, 0, 1)   # sparse clearings
    pine_f = np.clip((1 - moist) * 1.3 - 0.3 + (field(2.2, 3, SEED + 13) - 0.5) * 0.8, 0, 1)
    spruce_f = np.clip(moist * 1.2 - 0.15 + (field(2.2, 3, SEED + 14) - 0.5) * 0.8, 0, 1)
    fir_f = np.clip(0.55 + (field(2.2, 3, SEED + 15) - 0.5) * 1.6, 0, 1) * 0.7
    birch_f = np.clip((field(2.0, 4, SEED + 16) - 0.45) * 2.5, 0, 1) * 0.8 + np.clip(1 - ad / 40.0, 0, 1) * 0.5
    south = np.clip(-nrm[..., 2] * 4, 0, 1)
    oak_f = np.clip((field(2.2, 3, SEED + 17) - 0.55) * 3, 0, 1) * (0.4 + 0.6 * south) * 0.55
    decid_f = np.clip(moist * 0.9 + (field(2.2, 4, SEED + 18) - 0.5), 0, 1) * 0.5
    species = {
        "pine": (pine_f, ["pine_a", "pine_b", "pine_c"]),
        "spruce": (spruce_f, ["spruce_a", "spruce_b", "spruce_c"]),
        "fir": (fir_f, ["fir_a", "fir_b"]),
        "birch": (birch_f, ["birch_a", "birch_b"]),
        "oak": (oak_f, ["oak_a", "oak_b"]),
        "decid": (decid_f, ["alder_a", "linden_a"]),
    }

    def sample(f, x, z):
        ix = np.clip(np.round(x - ORIGIN).astype(int), 0, N - 1); iz = np.clip(np.round(z - ORIGIN).astype(int), 0, N - 1)
        return f[iz, ix]

    # ------------------------------------------------------------ rocks first (trees avoid them)
    sets = {k: InstanceSet(k, 32.0) for k in ("trees", "understory", "bushes", "rocks", "props")}
    sets["cover"] = InstanceSet("cover", 32.0)
    occupied = []  # (x, z, r)
    rock_names = [v["name"] for v in CAT if v["category"] == "rock"]
    cx, cz = jittered(36.0)
    keep = (rng.random(cx.size) < 0.33) & (LAT(cx, cz) > 9)
    near = (LAT(cx, cz) > 7.2) & (LAT(cx, cz) < 16) & (rng.random(cx.size) < 0.65)
    keep |= near
    rx, rz, rv, rs = [], [], [], []
    for x, z in zip(cx[keep], cz[keep]):
        k = int(rng.integers(1, 6))
        for j in range(k):
            px, pz = x + rng.normal(0, 3.5), z + rng.normal(0, 3.5)
            if LAT(np.array([px]), np.array([pz]))[0] < 7.0:
                continue
            v = rock_names[int(rng.integers(0, len(rock_names)))]
            s = rng.uniform(0.45, 1.25) * (1.35 if j == 0 else 1.0)
            rx.append(px); rz.append(pz); rv.append(v); rs.append(s)
    rx, rz, rs = np.array(rx), np.array(rz), np.array(rs)
    for v in set(rv):
        m = np.array([r == v for r in rv])
        x, z, s = rx[m], rz[m], rs[m]
        hh = VAR[v]["aabb"][1][1]
        y = H(x, z) - s * hh * rng.uniform(0.0, 0.18, len(x))
        cust = np.stack([rng.random(len(x)), rng.random(len(x)), s, sample(moist, x, z)], 1)
        sets["rocks"].add(v, instance_rows(x, y, z, rng.uniform(0, 2 * np.pi, len(x)), s, NRM(x, z), np.full(len(x), 0.55), custom=cust))
        r = VAR[v]["clearance"] * s
        occupied += list(zip(x, z, r))
    log(f"rocks: {len(rx)}")

    # ------------------------------------------------------------ trees
    X, Z = jittered(3.3)
    lt = LAT(X, Z)
    dens = sample(density, X, Z)
    edge_boost = np.clip(1 - (lt - 7) / 25, 0, 1)
    p_accept = (0.18 + 0.38 * dens + 0.2 * edge_boost) * (1 - 0.85 * sample(clearing, X, Z))
    acc = (rng.random(X.size) < p_accept) & (lt > 6.9)
    X, Z = X[acc], Z[acc]
    # species choice
    weights = np.stack([sample(species[k][0], X, Z) + 0.02 for k in species], 1)
    weights /= weights.sum(1, keepdims=True)
    u = rng.random(len(X))[:, None]
    choice = (np.cumsum(weights, 1) < u).sum(1)
    kinds = list(species)
    # variant + clearance per candidate, then greedy Poisson-style rejection using KD-tree neighbour lists
    names_per_kind = [species[k][1] for k in kinds]
    var_idx = np.array([rng.integers(0, len(names_per_kind[c])) for c in choice])
    cand_v = np.array([names_per_kind[c][j] for c, j in zip(choice, var_idx)])
    cand_s = rng.uniform(0.82, 1.15, len(X))
    clear = np.array([VAR[v]["clearance"] for v in cand_v]) * cand_s
    lt_acc = LAT(X, Z)
    ok_road = lt_acc >= 6.6 + clear
    # rocks occupy space too
    if occupied:
        occ = np.array(occupied)
        rt = cKDTree(occ[:, :2])
        dd, ii = rt.query(np.stack([X, Z], 1), k=1)
        ok_road &= dd > (occ[ii, 2] + clear + 0.6)
    pts = np.stack([X, Z], 1)
    kd = cKDTree(pts)
    max_r = float(clear.max())
    nbrs = kd.query_ball_point(pts, 2 * max_r + 0.9, workers=-1)
    order = rng.permutation(len(X))
    is_oak = choice == kinds.index("oak")
    order = np.concatenate([order[is_oak[order]], order[~is_oak[order]]])
    taken = np.zeros(len(X), bool)
    Xl, Zl, Cl = X.tolist(), Z.tolist(), clear.tolist()
    okl = ok_road.tolist()
    for i in order.tolist():
        if not okl[i]:
            continue
        xi, zi, ri = Xl[i], Zl[i], Cl[i]
        good = True
        for j in nbrs[i]:
            if taken[j] and (Xl[j] - xi) ** 2 + (Zl[j] - zi) ** 2 < (Cl[j] + ri + 0.9) ** 2:
                good = False
                break
        if good:
            taken[i] = True
    tx, tz, tv, ts = X[taken], Z[taken], cand_v[taken], cand_s[taken]
    log(f"trees: {len(tx)} ({len(tx) / (SIZE * SIZE / 1e4):.0f}/ha)")
    # canopy density map at 2 m
    CN = 1024
    canopy_acc = np.zeros((CN, CN)); conif_acc = np.zeros((CN, CN))
    def stamp(x, z, rad, op, conifer):
        cxp = (x - ORIGIN) / 2.0; czp = (z - ORIGIN) / 2.0; rp = rad / 2.0
        r_i = int(np.ceil(np.max(rp))) + 1
        ox, oz = np.meshgrid(np.arange(-r_i, r_i + 1), np.arange(-r_i, r_i + 1))
        for k in range(len(x)):
            ix = int(cxp[k]) + ox; iz = int(czp[k]) + oz
            dd = np.sqrt((ix + 0.5 - cxp[k]) ** 2 + (iz + 0.5 - czp[k]) ** 2) / max(rp[k], 0.5)
            w = np.clip(1.2 - dd, 0, 1) * op[k]
            ok = (ix >= 0) & (ix < CN) & (iz >= 0) & (iz < CN) & (w > 0)
            canopy_acc[iz[ok], ix[ok]] += -np.log(1 - np.minimum(w[ok], 0.95))
            if conifer[k]:
                conif_acc[iz[ok], ix[ok]] += w[ok]
    for v in np.unique(tv):
        m = tv == v
        meta = VAR[v]
        conif = meta["kind"] in ("pine", "spruce", "fir")
        op = {"pine": 0.6, "spruce": 0.92, "fir": 0.9, "birch": 0.55, "oak": 0.9, "decid": 0.8}[meta["kind"]]
        stamp(tx[m], tz[m], meta["crown_radius"] * ts[m] * (0.8 if meta["kind"] == "pine" else 1.0), np.full(m.sum(), op), np.full(m.sum(), conif))
        x, z, s = tx[m], tz[m], ts[m]
        y = H(x, z) - 0.12
        cust = np.stack([rng.random(len(x)), rng.random(len(x)), s, np.zeros(len(x))], 1)
        sets["trees"].add(v, instance_rows(x, y, z, rng.uniform(0, 2 * np.pi, len(x)), s, custom=cust))
    canopy = 1 - np.exp(-ndimage.gaussian_filter(canopy_acc, 1.2))
    conif_frac = ndimage.gaussian_filter(conif_acc, 3.0) / np.maximum(ndimage.gaussian_filter(canopy_acc, 3.0), 1e-3)
    conif_frac = np.clip(conif_frac, 0, 1)
    up = lambda a: np.asarray(Image.fromarray(a.astype(np.float32), "F").resize((N, N), Image.BILINEAR))
    canopy_f = np.clip(up(canopy), 0, 1); conif_f = np.clip(up(conif_frac), 0, 1)
    light = 1 - canopy_f

    # ------------------------------------------------------------ understory, bushes
    X, Z = jittered(4.6)
    lt = LAT(X, Z)
    road_near = np.clip(1 - (lt - 6) / 120, 0.35, 1)
    p = (0.18 + 0.45 * sample(light, X, Z)) * road_near
    acc = (rng.random(X.size) < p) & (lt > 6.4)
    X, Z = X[acc], Z[acc]
    und = [v["name"] for v in CAT if v["category"] == "understory"]
    wts = {"young_spruce_a": sample(spruce_f, X, Z) + 0.2, "young_spruce_b": sample(spruce_f, X, Z) + 0.2,
           "young_fir": sample(fir_f, X, Z) + 0.1, "young_pine": sample(pine_f, X, Z) * sample(light, X, Z) + 0.05,
           "young_birch_a": sample(birch_f, X, Z) * 0.8 + 0.1, "young_birch_b": sample(birch_f, X, Z) * 0.8 + 0.1,
           "hazel": sample(decid_f, X, Z) + 0.15, "snag": np.full(len(X), 0.08),
           "rowan": sample(decid_f, X, Z) * 0.6 + 0.08, "young_alder": sample(moist, X, Z) * 0.5 + 0.05, "young_oak": sample(oak_f, X, Z) + 0.06}
    W = np.stack([wts[n] for n in und], 1); W /= W.sum(1, keepdims=True)
    ch = (np.cumsum(W, 1) < rng.random(len(X))[:, None]).sum(1)
    for k, v in enumerate(und):
        m = ch == k
        x, z = X[m], Z[m]
        s = rng.uniform(0.75, 1.25, len(x))
        y = H(x, z) - 0.08
        cust = np.stack([rng.random(len(x)), rng.random(len(x)), s, sample(canopy_f, x, z)], 1)
        sets["understory"].add(v, instance_rows(x, y, z, rng.uniform(0, 2 * np.pi, len(x)), s, custom=cust))
    log(f"understory: {len(X)}")
    X, Z = jittered(3.4)
    lt = LAT(X, Z)
    edge = np.exp(-((lt - 10) / 7) ** 2)
    p = 0.06 + 0.5 * edge * (0.5 + 0.5 * sample(light, X, Z)) + 0.25 * sample(clearing, X, Z)
    acc = (rng.random(X.size) < p) & (lt > 6.2)
    X, Z = X[acc], Z[acc]
    bn = [v["name"] for v in CAT if v["category"] == "bush"]
    ch = rng.integers(0, len(bn), len(X))
    # low bilberry shrubs belong under the canopy, away from the bright verge
    for k, v in enumerate(bn):
        if v.startswith("bilberry"):
            under = sample(canopy_f, X, Z) > 0.45
            ch = np.where((ch == k) & ~under, rng.integers(0, len(bn), len(X)), ch)
    for k, v in enumerate(bn):
        m = ch == k
        x, z = X[m], Z[m]
        s = rng.uniform(0.7, 1.3, len(x))
        y = H(x, z) - 0.05
        cust = np.stack([rng.random(len(x)), rng.random(len(x)), s, sample(canopy_f, x, z)], 1)
        sets["bushes"].add(v, instance_rows(x, y, z, rng.uniform(0, 2 * np.pi, len(x)), s, NRM(x, z), np.full(len(x), 0.2), custom=cust))
    log(f"bushes: {len(X)}")

    # ------------------------------------------------------------ props: logs, stumps
    X, Z = jittered(17.0)
    lt = LAT(X, Z)
    acc = (rng.random(X.size) < 0.55) & (lt > 9.5)
    X, Z = X[acc], Z[acc]
    pn = [v["name"] for v in CAT if v["category"] in ("prop", "detail")]
    ch = rng.integers(0, len(pn), len(X))
    for k, v in enumerate(pn):
        m = ch == k
        x, z = X[m], Z[m]
        meta = VAR[v]
        yaw = rng.uniform(0, 2 * np.pi, len(x))
        if meta["kind"] == "log":
            # keep logs out of the road corridor along their whole length
            half = meta["crown_radius"]
            ex, ez = np.cos(yaw) * half, -np.sin(yaw) * half
            ok = (LAT(x + ex, z + ez) > 8.0) & (LAT(x - ex, z - ez) > 8.0)
            x, z, yaw = x[ok], z[ok], yaw[ok]
            ex, ez = ex[ok], ez[ok]
            s = rng.uniform(0.85, 1.2, len(x))
            h1, h2 = H(x + ex * s, z + ez * s), H(x - ex * s, z - ez * s)
            # the log must rest on the ground along its whole length: no bridging hollows, no cutting humps
            dev = np.zeros(len(x))
            for t in np.linspace(-1, 1, 9):
                line = h2 + (h1 - h2) * (t + 1) / 2
                dev = np.maximum(dev, np.abs(H(x + ex * s * t, z + ez * s * t) - line))
            ok = dev < 0.16
            x, z, yaw, ex, ez, s, h1, h2 = x[ok], z[ok], yaw[ok], ex[ok], ez[ok], s[ok], h1[ok], h2[ok]
            pitch = np.arctan2(h1 - h2, 2 * half * s)
            # tilt about the log's local Z axis (logs lie along local X)
            n = len(x)
            Rz = np.zeros((n, 3, 3)); c, sn = np.cos(pitch), np.sin(pitch)
            Rz[:, 0, 0] = c; Rz[:, 0, 1] = -sn; Rz[:, 1, 0] = sn; Rz[:, 1, 1] = c; Rz[:, 2, 2] = 1
            cy, sy = np.cos(yaw), np.sin(yaw)
            Ry = np.zeros((n, 3, 3)); Ry[:, 0, 0] = cy; Ry[:, 0, 2] = sy; Ry[:, 1, 1] = 1; Ry[:, 2, 0] = -sy; Ry[:, 2, 2] = cy
            y = (h1 + h2) / 2 - 0.15 * s
            cust = np.stack([rng.random(n), rng.random(n), s, sample(moist, x, z)], 1)
            rows = instance_rows(x, y, z, np.zeros(n), s, tilt=np.einsum("nij,njk->nik", Ry, Rz), custom=cust)
        else:
            s = rng.uniform(0.8, 1.3, len(x))
            y = H(x, z) - 0.06
            cust = np.stack([rng.random(len(x)), rng.random(len(x)), s, sample(moist, x, z)], 1)
            rows = instance_rows(x, y, z, yaw, s, NRM(x, z), np.full(len(x), 0.6), custom=cust)
        sets["props"].add(v, rows)

    # ------------------------------------------------------------ ground cover (road corridor)
    BAND = 90.0
    def corridor(spacing):
        X, Z = jittered(spacing, bounds=(-720, 640, -660, 520))
        lt = LAT(X, Z)
        m = lt < BAND
        return X[m], Z[m], lt[m]
    cover_specs = []
    # grass: light + verge
    X, Z, lt = corridor(0.85)
    verge = np.exp(-((lt - 7.5) / 3.2) ** 2)
    p = (0.5 * sample(light, X, Z) ** 1.5 + 0.85 * verge) * (lt > 5.25) * (0.75 + 0.5 * sample(density, X, Z))
    p *= 1 - 0.7 * np.clip((sample(moist, X, Z) - 0.6) * 3, 0, 1) * (lt > 12)
    cover_specs.append((["grass_a", "grass_b", "grass_c", "grass_d", "grass_e"], X, Z, p, (0.7, 1.35), 0.6))
    X, Z, lt = corridor(1.5)
    shade = sample(canopy_f, X, Z)
    p = (0.18 + 0.4 * sample(moist, X, Z)) * (0.45 + 0.55 * shade) + 0.35 * np.exp(-((lt - 9) / 4) ** 2)
    p *= (lt > 6.0)
    cover_specs.append((["fern_a", "fern_b", "fern_c", "fern_d", "fern_e"], X, Z, p, (0.65, 1.3), 0.3))
    X, Z, lt = corridor(2.1)
    p = (0.08 + 0.25 * np.exp(-((lt - 8.5) / 4) ** 2)) * (lt > 5.6)
    cover_specs.append((["nettle_a", "nettle_b", "cow_parsley"], X, Z, p, (0.7, 1.3), 0.25))
    X, Z, lt = corridor(1.3)
    p = 0.18 * sample(canopy_f, X, Z) * (lt > 6.0)
    cover_specs.append((["sprouts"], X, Z, p, (0.7, 1.5), 0.6))
    X, Z, lt = corridor(1.9)
    p = 0.05 + 0.25 * np.exp(-((lt - 5.6) / 0.6) ** 2)
    p *= (lt > 5.05)
    cover_specs.append((["stone"], X, Z, p, (0.5, 2.0), 0.8))
    X, Z, lt = corridor(3.6)
    p = 0.22 * sample(canopy_f, X, Z) * (lt > 7.0)
    cover_specs.append((["branches_a", "branches_b", "branches_c"], X, Z, p, (0.7, 1.4), 0.9))
    total_cover = 0
    for names, X, Z, p, srange, align in cover_specs:
        acc = rng.random(X.size) < p
        X, Z = X[acc], Z[acc]
        # keep clear of trunks and rocks
        ch = rng.integers(0, len(names), len(X))
        for k, v in enumerate(names):
            m = ch == k
            x, z = X[m], Z[m]
            s = rng.uniform(*srange, len(x))
            y = H(x, z) - (0.02 if VAR[v]["kind"] != "stone" else 0.03 * s)
            cust = np.stack([rng.random(len(x)), rng.random(len(x)), s, sample(canopy_f, x, z)], 1)
            sets["cover"].add(v, instance_rows(x, y, z, rng.uniform(0, 2 * np.pi, len(x)), s, NRM(x, z), np.full(len(x), align), custom=cust))
        total_cover += len(X)
    log(f"ground cover: {total_cover}")

    # ------------------------------------------------------------ control maps
    log("material control maps")
    def nf(beta, lo, seed, hi=None):
        f = T.fft_noise(2048, beta, seed, lo=lo, hi=hi)
        return np.pad(f, ((0, 1), (0, 1)), mode="wrap")
    n1, n2, n3, n4 = nf(1.8, 8, SEED + 21), nf(1.8, 10, SEED + 22), nf(2.0, 6, SEED + 23), nf(1.6, 20, SEED + 24)
    w_litter = (1 - conif_f) * (0.55 + 0.6 * n1) * (0.3 + canopy_f)
    w_needle = conif_f * (0.6 + 0.5 * n2) * (0.3 + canopy_f) + 0.08
    w_moss = np.clip(moist * 1.2 + (n3 - 0.5) * 1.6, 0, 1) ** 1.5 * (0.35 + canopy_f) * (1 + 0.6 * np.clip(nrm[..., 2] * 3, 0, 1))
    verge = np.exp(-((ad - 7.0) / 2.8) ** 2)
    w_grass = (light ** 2) * (0.7 + 0.6 * n4) + verge * 0.9
    ditch = np.exp(-((ad - 6.4) / 0.9) ** 2)
    w_soil = np.clip(slope * 5 - 0.5, 0, 1.2) + ditch * 0.35 + np.clip((n2 - 0.7) * 3, 0, 1) * 0.5
    gnoise = nf(1.5, 60, SEED + 25)
    w_gravel = np.clip(1 - (ad - 5.0 - 0.6 * gnoise) / 0.9, 0, 1) * (ad > 4.6)
    W = np.stack([w_litter, w_needle, w_moss, w_grass, w_soil, w_gravel], -1).astype(np.float32)
    W = np.maximum(W, 0) ** 1.6
    W[..., 5] = np.maximum(W[..., 5], (ad < 5.2).astype(np.float32) * 2)
    W /= np.maximum(W.sum(-1, keepdims=True), 1e-4)
    wet = np.clip(ditch * 0.9 + np.clip((moist - 0.65) * 2, 0, 1) * 0.5, 0, 1)
    c0 = (W[..., :4] * 255 + 0.5).astype(np.uint8)
    c1 = np.stack([W[..., 4], W[..., 5], canopy_f, wet], -1)
    c1 = (np.clip(c1, 0, 1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(c0, "RGBA").save(os.path.join(OUT, "control0.png"), optimize=True)
    Image.fromarray(c1, "RGBA").save(os.path.join(OUT, "control1.png"), optimize=True)
    for fn in ("control0.png", "control1.png", "terrain_normal.png"):
        with open(os.path.join(OUT, fn + ".import"), "w") as f:
            f.write('[remap]\n\nimporter="texture"\ntype="CompressedTexture2D"\n\n[params]\n\ncompress/mode=2\n'
                    'compress/high_quality=true\ncompress/normal_map=2\nmipmaps/generate=true\n'
                    'process/fix_alpha_border=false\ndetect_3d/compress_to=0\n')

    # ------------------------------------------------------------ write instances
    counts = {k: s.write() for k, s in sets.items()}
    meta = {
        "seed": SEED, "size": SIZE, "origin": ORIGIN, "resolution": N,
        "height_min": float(h.min()), "height_max": float(h.max()),
        "heightmap": "res://resources/world/heightmap.f32.gz",
        "normal_map": "res://resources/world/terrain_normal.png",
        "control0": "res://resources/world/control0.png", "control1": "res://resources/world/control1.png",
        "road": "res://resources/world/road.json", "road_length": round(L, 1),
        "instances": {k: f"res://resources/world/inst_{k}.bin.gz" for k in sets}, "counts": counts,
        "spawn": [float(road_xz[0][0]), float(zr[0]), float(road_xz[0][1])],
    }
    with open(os.path.join(OUT, "world.json"), "w") as f:
        json.dump(meta, f, indent=1)
    log(f"done in {time.time() - t0:.0f}s", counts)


if __name__ == "__main__":
    main()
