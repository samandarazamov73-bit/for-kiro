#!/usr/bin/env python3
"""Generate every mesh used by the forest: procedural trees, understory, bushes, ground cover,
plus LOD chains for the CC0 photoscanned rocks / stumps / logs / branches.

Each asset is written as assets/<group>/<name>.glb containing nodes LOD0, LOD1, LOD2 (fewer for
small ground cover). assets/catalog.json lists every variant with its size, clearance radius,
LOD switch distances and triangle counts; tools/world_gen.py and the Godot scripts read it.

Usage: FOREST_SRC=<sources> python3 tools/build_assets.py
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import meshkit as mk  # noqa: E402
from meshkit import normalize  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.environ.get("FOREST_SRC", os.path.join(HERE, ".cache", "src"))
ATLAS = json.load(open(os.path.join(ROOT, "assets", "textures", "foliage", "foliage_atlas.json")))["rects"]
UP = np.array([0.0, 1.0, 0.0])

# sprite anchor (image-space fraction) and growth axis inside its atlas rectangle
SPRITE = {
    "fir_a": ((0.5, 0.98), "up"), "fir_b": ((0.5, 0.98), "up"), "fir_c": ((0.5, 0.98), "up"),
    "fir_d": ((0.5, 0.98), "up"), "fir_e": ((0.5, 0.98), "up"),
    "spruce_branch": ((0.02, 0.51), "right"), "conifer_mass": ((0.5, 0.55), "up"),
    "pine_cluster": ((0.5, 0.95), "up"), "pine_a": ((0.5, 0.99), "up"), "pine_b": ((0.02, 0.62), "right"),
    "birch_twig": ((0.12, 0.08), "down"), "leafy_branch": ((0.5, 0.04), "down"),
    "oak_cluster": ((0.5, 0.97), "up"), "decid_cluster": ((0.5, 0.99), "up"),
    "compound_leaf": ((0.5, 0.98), "up"),
}
for i in range(5):
    SPRITE[f"fern_{i}"] = ((0.5, 0.99), "up"); SPRITE[f"grass_{i}"] = ((0.5, 0.985), "up")
for i in range(3):
    SPRITE[f"moss_{i}"] = ((0.5, 0.97), "up")
for i in range(4):
    SPRITE[f"nettle_{i}"] = ((0.5, 0.5), "up")


def sprite_card(surf, name, base, growth, side, length, **kw):
    """Card for an atlas sprite: `length` is the world size along the sprite's growth axis."""
    rect = ATLAS[name]
    anchor, axis = SPRITE[name]
    aspect = rect[2] / rect[3]  # image w / h
    if axis in ("up", "down"):
        w, h = length * aspect, length
    else:
        w, h = length, length / aspect
    mk.card(surf, base, growth, side, w, h, rect, anchor=anchor, axis=axis, **kw)


def perp(v, rng):
    a = normalize(np.cross(v, UP if abs(v[1]) < 0.95 else np.array([1.0, 0, 0])))
    b = np.cross(v, a)
    t = rng.uniform(0, 2 * math.pi)
    return normalize(a * math.cos(t) + b * math.sin(t))


def grow_path(start, direction, length, nseg, rng, gravity=0.0, wobble=0.08, curl=0.0):
    """Random-walk branch path. gravity>0 bends up, <0 droops (applied progressively)."""
    pts = [np.asarray(start, np.float64)]
    d = normalize(np.asarray(direction, np.float64))
    step = length / nseg
    for i in range(nseg):
        t = (i + 1) / nseg
        d = normalize(d + rng.normal(0, wobble, 3) + UP * (gravity * t) + UP * (curl * t * t))
        pts.append(pts[-1] + d * step)
    return np.array(pts)


def resample(points, max_seg):
    out = [points[0]]
    for i in range(1, len(points)):
        a, b = points[i - 1], points[i]
        n = max(1, int(math.ceil(np.linalg.norm(b - a) / max_seg)))
        for k in range(1, n + 1):
            out.append(a + (b - a) * k / n)
    return np.array(out)


def thin(points, keep_every):
    if len(points) <= 2 or keep_every <= 1:
        return points
    idx = list(range(0, len(points) - 1, keep_every)) + [len(points) - 1]
    return points[idx]


class Skeleton:
    def __init__(self, height, bark_layer, crown_r):
        self.H, self.layer, self.crown_r = height, bark_layer, crown_r
        self.tubes = []    # dict(points, radii, level, phase, sway0, sway1, cap, mod)
        self.leaves = []   # dict(lods, sprite, base, growth, side, length, normal, ao, sway, phase, bend, segs, tr)

    def tube(self, points, r0, r1, level, rng, sway0=0.0, sway1=0.0, cap=False, mod=None, radii=None):
        k = len(points)
        if radii is None:
            t = np.linspace(0, 1, k)
            radii = r0 + (r1 - r0) * t ** 0.9
        self.tubes.append(dict(points=np.asarray(points), radii=np.asarray(radii), level=level,
                               phase=float(rng.random()), sway0=sway0, sway1=sway1, cap=cap, mod=mod))

    def leaf(self, lods, sprite, base, growth, side, length, normal=None, ao=1.0, sway=1.0, phase=0.0,
             bend=0.0, segs=1, tr=1.0, flutter=1.0, flip=False):
        self.leaves.append(dict(lods=lods, sprite=sprite, base=np.asarray(base, np.float64),
                                growth=normalize(np.asarray(growth, np.float64)), side=normalize(np.asarray(side, np.float64)),
                                length=length, normal=normal, ao=ao, sway=sway, phase=phase, bend=bend, segs=segs,
                                tr=tr, flutter=flutter, flip=flip))


def crown_normal(p, center, face, up_bias=0.35, w_face=0.25):
    radial = p - center
    radial = radial / max(np.linalg.norm(radial), 1e-6)
    return normalize(radial + UP * up_bias + normalize(face) * w_face)


# ------------------------------------------------------------------ emitting
LOD_SIDES = {0: {0: 12, 1: 6, 2: 4, 3: 3}, 1: {0: 5, 1: 4, 2: 3, 3: 3}, 2: {0: 4, 1: 3, 2: 3, 3: 3}}
LOD_MINR = {0: 0.006, 1: 0.035, 2: 0.09}


def emit(skel: Skeleton, lod: int, bark_tile=1.1) -> mk.Mesh:
    mesh = mk.Mesh(("bark", False), ("foliage", True))
    H = skel.H
    for tb in skel.tubes:
        lvl = tb["level"]
        if tb["radii"][0] < LOD_MINR[lod] and lvl > 0:
            continue
        if lod == 2 and lvl > 0 and tb["radii"][0] < 0.16:
            continue           # far LOD: trunk (and only massive limbs), no roots or branches
        pts, rad = tb["points"], tb["radii"]
        if lod > 0 and len(pts) > 3:
            step = 3 if lod == 1 else 6
            idx = list(range(0, len(pts) - 1, step)) + [len(pts) - 1]
            pts, rad = pts[idx], rad[idx]
        sides = LOD_SIDES[lod][min(lvl, 3)]
        if lvl > 0:
            r = float(rad[0])
            sides = min(sides, 3 if r < 0.03 else 4 if r < 0.05 else 5 if r < 0.09 else 6)
        circ = 2 * math.pi * float(rad[0])
        rep = max(1.0, round(circ / bark_tile)) if lvl == 0 else max(1.0, round(circ / bark_tile * 2) / 2)
        k = len(pts)
        sway = np.linspace(tb["sway0"], tb["sway1"], k)
        hn = np.clip(pts[:, 1] / H, 0, 1)
        ao = np.clip(0.55 + 0.45 * np.clip((pts[:, 1] + 0.3) / 2.5, 0, 1), 0, 1)
        if lvl > 0:
            ao = ao * 0.85
        mod = tb["mod"] if lod == 0 else (tb["mod"] if (tb["mod"] and lod == 1) else None)
        mk.tube(mesh["bark"], pts, rad, sides, skel.layer, rep, 1.0 / bark_tile, sway, tb["phase"], hn, ao,
                radial_mod=(None if mod is None else (lambda i, a, _m=mod, _p=pts: _m(_p[i][1], a))), cap_end=tb["cap"])
    for lf in skel.leaves:
        if lod not in lf["lods"]:
            continue
        sprite_card(mesh["foliage"], lf["sprite"], lf["base"], lf["growth"], lf["side"], lf["length"],
                    normal_hint=lf["normal"], ao=lf["ao"], sway=lf["sway"], phase=lf["phase"], bend=lf["bend"],
                    segs=lf["segs"] if lod == 0 else 1, hnorm=float(np.clip(lf["base"][1] / H, 0, 1)),
                    translucency=lf["tr"], flutter=lf["flutter"], flip_u=lf["flip"])
    return mesh


# -------------------------------------------------------------- trunk + roots
def make_trunk(skel: Skeleton, rng, H, r0, lean=0.0, bend=0.25, top_frac=1.0, roots=True, flare=1.0):
    n = max(8, int(H / 0.55))
    ys = np.concatenate([[-0.6, -0.2, 0.0, 0.25, 0.55, 0.95], np.linspace(1.5, H * top_frac, n)])
    ph1, ph2 = rng.uniform(0, 6.28, 2)
    lean_dir = normalize(np.array([math.cos(ph1), 0, math.sin(ph1)]))
    pts = []
    for y in ys:
        t = max(y, 0) / H
        off = lean_dir * (lean * y) + np.array([math.sin(t * 5.5 + ph1), 0, math.cos(t * 4.3 + ph2)]) * bend * t
        pts.append(np.array([0, y, 0]) + off)
    pts = np.array(pts)
    taper = np.clip(1 - np.maximum(ys, 0) / (H * 1.02), 0.0, 1) ** 0.85
    rad = r0 * taper + 0.012
    rad *= 1 + flare * 0.55 * np.exp(-np.maximum(ys, 0) / 0.45)
    lobes = int(rng.integers(5, 8)); lph = rng.uniform(0, 6.28)
    def mod(y, a, _l=lobes, _p=lph):
        e = math.exp(-max(y, 0) / 0.55) * flare
        return 1 + 0.16 * e * math.cos(_l * a + _p) + 0.05 * math.sin(3 * a + _p * 2) * math.exp(-max(y, 0) / 2.5)
    skel.tube(pts, 0, 0, 0, rng, radii=rad, mod=mod, cap=top_frac < 1.0)
    if roots:
        for k in range(lobes):
            az = (2 * math.pi * k - lph) / lobes + rng.normal(0, 0.12)
            d = np.array([math.cos(az), 0, math.sin(az)])
            r_trunk = r0 * 1.35
            start = np.array([0, 0.22 + rng.uniform(0, 0.12), 0]) + d * r_trunk * 0.55
            length = r0 * rng.uniform(3.0, 6.0)
            path = [start]
            for i in range(1, 6):
                t = i / 5
                p = start + d * length * t + np.array([0, -0.55 * t ** 0.7 - 0.05, 0]) + perp(d, rng) * 0.04 * i
                path.append(p)
            path = np.array(path)
            rr = r0 * 0.42 * np.linspace(1, 0.25, len(path))
            skel.tube(path, 0, 0, 1, rng, radii=rr)
    return pts, rad


def trunk_point(pts, rad, y):
    ys = pts[:, 1]
    i = int(np.clip(np.searchsorted(ys, y), 1, len(ys) - 1))
    t = (y - ys[i - 1]) / max(ys[i] - ys[i - 1], 1e-6)
    return pts[i - 1] + (pts[i] - pts[i - 1]) * t, rad[i - 1] + (rad[i] - rad[i - 1]) * t


# ------------------------------------------------------------------ conifers
def conifer(seed, kind, H, r0, cb, Rmax, lean=0.02, dead_stubs=True, young=False):
    """kind: spruce | fir. Whorled branches, sprig cards (LOD0), branch cards (LOD1), mass cards (LOD2)."""
    rng = np.random.default_rng(seed)
    skel = Skeleton(H, 1.0, Rmax)
    tp, tr = make_trunk(skel, rng, H, r0, lean=lean, bend=0.15, roots=not young, flare=0.0 if young else 1.0)
    hc = cb * H
    y = hc
    whorl = 0
    sprigs = ["fir_a", "fir_b", "fir_c", "fir_d", "fir_e"]
    droop = -0.35 if kind == "spruce" else -0.08
    while y < H - 0.35:
        rel = (y - hc) / (H - hc)
        n = int(rng.integers(4, 7)) if not young else int(rng.integers(3, 6))
        ph = rng.uniform(0, 2 * math.pi)
        prof = (1 - rel) ** (0.95 if kind == "spruce" else 0.85)
        for j in range(n):
            az = ph + 2 * math.pi * j / n + rng.normal(0, 0.25)
            dh = np.array([math.cos(az), 0, math.sin(az)])
            L = max(0.25, Rmax * prof * rng.uniform(0.78, 1.08) + 0.15)
            pitch = (rng.uniform(-0.45, -0.15) if kind == "spruce" else rng.uniform(-0.15, 0.08)) + rel * 0.35
            base, rt = trunk_point(tp, tr, y)
            start = base + dh * rt * 0.8
            path = grow_path(start, dh + UP * pitch, L, 3, rng, gravity=droop, wobble=0.06,
                             curl=0.45 if kind == "spruce" else 0.15)
            br = 0.012 + 0.03 * L / max(Rmax, 1) * (1.0 if not young else 0.6)
            skel.tube(path, br, 0.006, 1, rng, sway0=0.05, sway1=0.6 + 0.3 * rel)
            pphase = float(rng.random())
            side_v = normalize(np.cross(UP, dh))
            center = np.array([base[0], y, base[2]])
            # LOD0: sprigs along the branch, layered shelves
            m = max(2, int(L / ((0.165 if kind == "spruce" else 0.145) * (0.4 if young else 1.0))))
            for s in range(m):
                t = 0.18 + 0.82 * (s + rng.random() * 0.6) / m
                k = min(int(t * (len(path) - 1)), len(path) - 2)
                f = t * (len(path) - 1) - k
                p = path[k] + (path[k + 1] - path[k]) * f
                bd = normalize(path[k + 1] - path[k])
                sd = 1 if s % 2 == 0 else -1
                g = normalize(bd + side_v * sd * rng.uniform(0.3, 0.9) + UP * rng.uniform(-0.15, 0.15))
                side = normalize(np.cross(g, UP) * math.cos(rng.uniform(-0.6, 0.6)) + UP * rng.uniform(-0.3, 0.3))
                length = rng.uniform(0.38, 0.62) * (1.0 - 0.35 * t) * (0.8 if young else 1.0)
                nh = crown_normal(p, center + UP * 0.6, np.cross(side, g))
                depth = np.linalg.norm((p - center)[[0, 2]]) / max(Rmax * prof + 0.2, 0.3)
                ao = float(np.clip(0.35 + 0.65 * depth, 0.3, 1.0) * (0.75 + 0.25 * rel))
                skel.leaf({0}, sprigs[int(rng.integers(0, 5))], p, g, side, length, nh, ao, sway=0.6 + 0.4 * t,
                          phase=pphase, bend=0.05 * length, segs=2, tr=0.6, flutter=0.3, flip=rng.random() < 0.5)
                if s % 3 == 1:
                    skel.leaf({1}, sprigs[int(rng.integers(0, 2))], p, g, side, length * 1.7, nh, ao,
                              sway=0.6 + 0.4 * t, phase=pphase, tr=0.6, flutter=0.2)
            # hanging secondary shoots for spruce (comb habit)
            if kind == "spruce" and not young:
                for s in range(max(1, int(L / 0.6))):
                    t = 0.35 + 0.6 * rng.random()
                    k = min(int(t * (len(path) - 1)), len(path) - 2)
                    p = path[k] + (path[k + 1] - path[k]) * rng.random()
                    g = normalize(-UP + dh * 0.25 + rng.normal(0, 0.15, 3))
                    side = normalize(np.cross(g, dh))
                    nh = crown_normal(p, center, dh)
                    skel.leaf({0}, sprigs[int(rng.integers(0, 2))], p, g, side, rng.uniform(0.3, 0.5), nh, 0.6,
                              sway=0.9, phase=pphase, tr=0.6, flutter=0.4)
            # LOD1/LOD2: branch-sized cards
            ang = rng.uniform(-0.35, 0.35)
            for c in range(2):
                side = normalize(side_v * math.cos(ang + c * 1.1) + UP * math.sin(ang + c * 1.1))
                p0 = start
                g = normalize(path[-1] - path[0])
                nh = crown_normal(path[len(path) // 2], center + UP * 0.5, np.cross(side, g))
                skel.leaf({1} if c == 0 else {1}, "spruce_branch", p0, g, side,
                          np.linalg.norm(path[-1] - path[0]) * 1.12, nh, float(0.55 + 0.45 * rel), sway=0.7,
                          phase=pphase, tr=0.5, flutter=0.2, flip=c == 1)
        y += rng.uniform(0.45, 0.75) * (0.75 if rel > 0.75 else 1.0) * (0.4 if young else 1.0)
        whorl += 1
    # leader
    for k in range(3):
        g = normalize(UP + rng.normal(0, 0.15, 3))
        sprite_name = sprigs[k % 2]
        skel.leaf({0, 1}, sprite_name, trunk_point(tp, tr, H - 0.9)[0], g, perp(g, rng), 1.0, None, 0.95,
                  sway=1.0, tr=0.6, flutter=0.2)
    # LOD2: crown mass cards forming a cone
    n_rings = max(3, int((H - hc) / 2.2))
    for i in range(n_rings):
        rel = (i + 0.5) / n_rings
        yy = hc + rel * (H - hc) * 0.95
        rad = Rmax * (1 - rel) ** 0.9 + 0.3
        for j in range(3):
            az = rng.uniform(0, math.pi) + j * math.pi / 3
            side = np.array([math.cos(az), 0, math.sin(az)])
            nh = normalize(np.array([math.sin(az), 0.5, -math.cos(az)]))
            skel.leaf({2}, "conifer_mass", np.array([0, yy, 0]), UP, side, rad * 2.0 + (H - hc) / n_rings * 0.6,
                      nh, float(0.5 + 0.5 * rel), sway=0.5, tr=0.4, flutter=0.1, flip=j % 2 == 1)
        # flat skirt card at each ring
        side = np.array([1.0, 0, 0])
        skel.leaf({2}, "conifer_mass", np.array([0, yy, 0]), normalize(np.array([0, 0.25, 1.0])), side, rad * 2.1,
                  UP, float(0.45 + 0.4 * rel), sway=0.5, tr=0.4, flutter=0.1)
    if dead_stubs and not young:
        for i in range(int(hc * 3)):
            yy = rng.uniform(1.8, hc)
            base, rt = trunk_point(tp, tr, yy)
            az = rng.uniform(0, 2 * math.pi)
            d = np.array([math.cos(az), rng.uniform(-0.3, 0.1), math.sin(az)])
            L = rng.uniform(0.15, 0.9) * (0.4 + yy / hc)
            path = grow_path(base + d * rt * 0.8, d, L, 2, rng, wobble=0.1)
            skel.tube(path, 0.018 + 0.01 * L, 0.006, 2, rng, cap=False)
    return skel


def pine(seed, H, r0, cb, lean=0.03, young=False):
    rng = np.random.default_rng(seed)
    skel = Skeleton(H, 0.0, H * 0.18)
    tp, tr = make_trunk(skel, rng, H, r0, lean=lean, bend=0.35, roots=not young, flare=0.0 if young else 0.9)
    hc = cb * H
    n_limbs = int(rng.integers(13, 18)) if not young else int(rng.integers(9, 12))
    crown_center = np.array([tp[-1][0], hc + (H - hc) * 0.55, tp[-1][2]])
    golden = math.pi * (3 - math.sqrt(5))
    tips = []
    for i in range(n_limbs):
        rel = (i + rng.random() * 0.6) / n_limbs
        yy = hc + rel * (H - hc) * 0.92
        az = i * golden + rng.normal(0, 0.3)
        d = np.array([math.cos(az), 0, math.sin(az)])
        pitch = 0.35 + rel * 0.9 + rng.normal(0, 0.15)
        Lmax = H * 0.17 * (0.6 if young else 1.0)
        L = Lmax * (0.55 + 0.45 * math.sin(math.pi * min(1.0, 0.25 + rel * 0.9))) * rng.uniform(0.75, 1.1)
        base, rt = trunk_point(tp, tr, yy)
        path = grow_path(base + d * rt * 0.7, d + UP * pitch, L, 5, rng, gravity=0.25, wobble=0.12)
        rb = r0 * (0.22 + 0.18 * (1 - rel)) * (0.8 if young else 1)
        skel.tube(path, rb, 0.02, 1, rng, sway0=0.05, sway1=0.5)
        for k in range(2, len(path) - 1):          # needle tufts along the outer part of the limb
            if rng.random() < 0.8:
                tips.append((path[k] + perp(normalize(path[k + 1] - path[k]), rng) * 0.15, normalize(path[k + 1] - path[k] + UP * 0.5), rel))
        tips.append((path[-1], normalize(path[-1] - path[-2]), rel))
        for s in range(int(rng.integers(3, 7))):
            t = rng.uniform(0.3, 0.9)
            k = min(int(t * (len(path) - 1)), len(path) - 2)
            p = path[k]
            bd = normalize(path[k + 1] - path[k])
            sd = normalize(bd + perp(bd, rng) * 0.9 + UP * 0.3)
            sub = grow_path(p, sd, L * rng.uniform(0.3, 0.55), 3, rng, gravity=0.3, wobble=0.12)
            skel.tube(sub, rb * 0.45, 0.012, 2, rng, sway0=0.4, sway1=0.8)
            tips.append((sub[-1], normalize(sub[-1] - sub[-2]), rel))
            if len(sub) > 2 and rng.random() < 0.7:
                tips.append((sub[-2], normalize(sub[-1] - sub[-2]), rel))
    for p, d, rel in tips:
        ph = float(rng.random())
        nh = crown_normal(p, crown_center, d, 0.5)
        ao = float(0.55 + 0.45 * rel)
        # LOD0: radial tuft ball of single twigs
        for k in range(20 if not young else 12):
            g = normalize(d * 0.6 + rng.normal(0, 0.6, 3) + UP * 0.3)
            sp = "pine_a" if rng.random() < 0.65 else "pine_b"
            skel.leaf({0}, sp, p - d * 0.15, g, perp(g, rng), rng.uniform(0.45, 0.7), nh, ao, sway=1.0, phase=ph,
                      tr=0.5, flutter=0.35, flip=rng.random() < 0.5)
        skel.leaf({0}, "pine_cluster", p - d * 0.3, normalize(d + UP * 0.6), perp(d, rng), 0.9, nh, ao * 0.9,
                  sway=0.9, phase=ph, tr=0.5, flutter=0.2)
        # LOD1: two crossed cluster cards
        for k in range(3):
            g = normalize(d * 0.5 + UP * 0.7 + rng.normal(0, 0.35, 3))
            side = perp(g, rng)
            skel.leaf({1}, "pine_cluster", p - d * 0.35, g, side, 1.25, nh, ao, sway=0.9, phase=ph, tr=0.5,
                      flutter=0.2, flip=k == 1)
    # LOD2: big cluster cards around the crown
    for i in range(int(len(tips) * 0.5) + 4):
        p, d, rel = tips[int(rng.integers(0, len(tips)))]
        g = normalize(UP + d * 0.4)
        skel.leaf({2}, "pine_cluster", p - d * 0.5 - UP * 0.4, g, perp(g, rng), 2.4, crown_normal(p, crown_center, d, 0.5),
                  float(0.6 + 0.4 * rel), sway=0.6, tr=0.5, flutter=0.1)
    if not young:
        for i in range(int(hc * 1.6)):
            yy = rng.uniform(2.0, hc)
            base, rt = trunk_point(tp, tr, yy)
            az = rng.uniform(0, 2 * math.pi)
            d = np.array([math.cos(az), rng.uniform(-0.1, 0.25), math.sin(az)])
            path = grow_path(base + d * rt * 0.8, d, rng.uniform(0.1, 0.45), 2, rng, wobble=0.1)
            skel.tube(path, 0.025, 0.01, 2, rng, cap=True)
    return skel


# ----------------------------------------------------------------- deciduous
def deciduous(seed, kind, H, r0, cb, crown_r, layer, sprites, bole=None, n_main=None, twin=False, young=False,
              droop=0.0, card_len=(0.7, 1.1), density=1.0, cards_per_twig=5):
    """kind: birch | oak | decid. Recursive branching inside an ellipsoidal crown envelope."""
    rng = np.random.default_rng(seed)
    skel = Skeleton(H, float(layer), crown_r)
    trunk_top = (bole / H) if bole else 1.0
    tp, tr = make_trunk(skel, rng, H, r0, lean=0.03, bend=0.3 if kind != "oak" else 0.45,
                        top_frac=min(1.0, trunk_top * 1.05) if bole else 0.97, roots=not young,
                        flare=0.0 if young else (1.3 if kind == "oak" else 0.8))
    if twin:  # second stem from the base (common in birch)
        az = rng.uniform(0, 6.28)
        d = np.array([math.cos(az), 0, math.sin(az)])
        path = grow_path(np.array([0, 0.6, 0]) + d * r0 * 0.5, UP * 3 + d, H * 0.82, 10, rng, gravity=0.25, wobble=0.03)
        skel.tube(path, r0 * 0.7, 0.03, 1, rng, sway0=0.0, sway1=0.25)
    hc = (bole * 0.8) if (kind == "oak" and bole) else cb * H
    cc = np.array([0, hc + (H - hc) * 0.5, 0])
    a_h = (H - hc) * 0.5
    def inside(p):
        q = (p - cc)
        return (q[0] ** 2 + q[2] ** 2) / crown_r ** 2 + q[1] ** 2 / a_h ** 2 < 1.0
    n_main = n_main or (int(rng.integers(12, 19)) if kind == "birch" else int(rng.integers(9, 14)))
    golden = math.pi * (3 - math.sqrt(5))
    twigs = []  # (point, dir, level)
    def branch(p, d, L, rad, level, max_level):
        nseg = 5 if level == 1 else (4 if level == 2 else 3)
        grav = {"birch": (0.35, -0.5, -0.9), "oak": (0.05, -0.05, 0.05), "decid": (0.2, -0.1, -0.2)}[kind][min(level - 1, 2)]
        path = grow_path(p, d, L, nseg, rng, gravity=grav + droop * (level - 1), wobble=0.16 if kind == "oak" else 0.09)
        # keep inside the crown envelope: shorten if leaving
        for i in range(1, len(path)):
            if not inside(path[i]) and level > 1:
                path = path[: max(i, 2)]
                break
        skel.tube(path, rad, max(rad * 0.25, 0.006), level, rng, sway0=0.1 * level, sway1=0.35 + 0.25 * level)
        if level >= max_level:
            twigs.append((path[-1], normalize(path[-1] - path[-2]), level))
            for i in range(1, len(path) - 1):
                if rng.random() < 0.6:
                    twigs.append((path[i], normalize(path[i + 1] - path[i]), level))
            return
        if kind == "oak":
            nchild = int(rng.integers(5, 8)) if level == 1 else int(rng.integers(3, 6))
        else:
            nchild = int(rng.integers(3, 6)) if level == 1 else int(rng.integers(2, 5))
        for c in range(nchild):
            t = rng.uniform(0.3, 0.95)
            k = min(int(t * (len(path) - 1)), len(path) - 2)
            q = path[k] + (path[k + 1] - path[k]) * rng.random()
            bd = normalize(path[k + 1] - path[k])
            cd = normalize(bd + perp(bd, rng) * rng.uniform(0.6, 1.1))
            branch(q, cd, L * rng.uniform(0.4, 0.65), rad * 0.55, level + 1, max_level)
        twigs.append((path[-1], normalize(path[-1] - path[-2]), level))
    if kind == "oak" and bole:
        top = trunk_point(tp, tr, bole)[0]
        for i in range(n_main):
            az = i * golden + rng.normal(0, 0.3)
            d = normalize(np.array([math.cos(az), rng.uniform(0.8, 1.6), math.sin(az)]))
            branch(top + rng.normal(0, 0.15, 3) * np.array([1, 0.5, 1]), d, crown_r * rng.uniform(0.75, 1.05),
                   r0 * rng.uniform(0.45, 0.62), 1, 3)
    else:
        for i in range(n_main):
            rel = (i + rng.random()) / n_main
            yy = hc + rel * (H - hc) * 0.9
            az = i * golden + rng.normal(0, 0.25)
            base, rt = trunk_point(tp, tr, yy)
            env = math.sqrt(max(0.05, 1 - ((yy - cc[1]) / a_h) ** 2))
            L = crown_r * env * rng.uniform(0.85, 1.15) + 0.4
            pitch = (0.7 + 0.5 * rel) if kind == "birch" else (0.35 + 0.6 * rel)
            d = normalize(np.array([math.cos(az), pitch, math.sin(az)]))
            branch(base + np.array([d[0], 0, d[2]]) * rt * 0.6, d, L, max(rt * 0.42, 0.02), 1, 2 if young else 3)
    # foliage cards on twigs
    for p, d, lvl in twigs:
        if rng.random() > density:
            continue
        ph = float(rng.random())
        nh = crown_normal(p, cc, d, 0.45, 0.2)
        rel_h = (p[1] - hc) / max(H - hc, 1)
        depth = math.sqrt(max(0.0, ((p - cc)[0] ** 2 + (p - cc)[2] ** 2) / crown_r ** 2 + ((p - cc)[1] / a_h) ** 2))
        ao = float(np.clip(0.3 + 0.7 * depth, 0.3, 1.0) * (0.8 + 0.2 * rel_h))
        n_cards = cards_per_twig if lvl >= 2 else max(cards_per_twig - 1, 1)
        for k in range(n_cards):
            sp = sprites[int(rng.integers(0, len(sprites)))]
            axis = SPRITE[sp][1]
            if axis == "down":
                g = normalize(-UP + d * 0.35 + rng.normal(0, 0.25, 3))
            else:
                g = normalize(d + UP * 0.35 + rng.normal(0, 0.45, 3))
            L = rng.uniform(*card_len) * (0.8 if young else 1.0)
            skel.leaf({0}, sp, p, g, perp(g, rng), L, nh, ao, sway=1.0, phase=ph, bend=0.12 * L, segs=2, tr=1.0,
                      flutter=1.0, flip=rng.random() < 0.5)
    # LOD1: fewer, bigger cards at the main twig groups
    for p, d, lvl in twigs:
        if rng.random() > 0.8 * density:
            continue
        sp = sprites[int(rng.integers(0, len(sprites)))]
        axis = SPRITE[sp][1]
        g = normalize(-UP + d * 0.3) if axis == "down" else normalize(d + UP * 0.4 + rng.normal(0, 0.3, 3))
        nh = crown_normal(p, cc, d, 0.45, 0.2)
        rel_h = (p[1] - hc) / max(H - hc, 1)
        for k in range(2):
            gk = g if k == 0 else normalize(g + rng.normal(0, 0.5, 3))
            skel.leaf({1}, sp, p, gk, perp(gk, rng), card_len[1] * 1.45, nh, float(0.55 + 0.45 * rel_h), sway=0.9,
                      tr=1.0, flutter=0.6, flip=k == 1)
    # LOD2: crown shell cards
    n2 = int(10 + crown_r * 3)
    for i in range(n2):
        u, v = rng.uniform(-1, 1), rng.uniform(0, 2 * math.pi)
        r = math.sqrt(1 - u * u)
        p = cc + np.array([crown_r * 0.75 * r * math.cos(v), a_h * 0.75 * u, crown_r * 0.75 * r * math.sin(v)])
        g = normalize(UP * 0.6 + (p - cc) * np.array([1, 0, 1]) * 0.1 + rng.normal(0, 0.3, 3))
        sp = sprites[int(rng.integers(0, len(sprites)))]
        axis = SPRITE[sp][1]
        if axis == "down":
            g = -g
        skel.leaf({2}, sp, p, g, perp(g, rng), max(crown_r, a_h) * 0.95, crown_normal(p, cc, g, 0.4, 0.1),
                  float(0.6 + 0.3 * (u * 0.5 + 0.5)), sway=0.6, tr=1.0, flutter=0.2)
    return skel


def snag(seed, H, r0):
    rng = np.random.default_rng(seed)
    skel = Skeleton(H, 1.5, 1.0)   # spruce bark, dead
    tp, tr = make_trunk(skel, rng, H, r0, lean=0.05, bend=0.2, top_frac=1.0, roots=True, flare=0.8)
    for i in range(int(H * 5)):
        yy = rng.uniform(1.5, H * 0.9)
        base, rt = trunk_point(tp, tr, yy)
        az = rng.uniform(0, 2 * math.pi)
        d = np.array([math.cos(az), rng.uniform(-0.4, 0.1), math.sin(az)])
        path = grow_path(base + d * rt * 0.8, d, rng.uniform(0.2, 1.4) * (1 - yy / H * 0.5), 3, rng, gravity=-0.2, wobble=0.15)
        skel.tube(path, 0.03, 0.008, 2, rng, cap=True)
    return skel


def bush(seed, H, R, sprites, stems=(5, 9), card_len=(0.45, 0.7), layer=4):
    rng = np.random.default_rng(seed)
    skel = Skeleton(H, float(layer), R)
    cc = np.array([0, H * 0.55, 0])
    for s in range(int(rng.integers(*stems))):
        az = rng.uniform(0, 2 * math.pi)
        d = normalize(np.array([math.cos(az) * rng.uniform(0.2, 0.7), 1.0, math.sin(az) * rng.uniform(0.2, 0.7)]))
        path = grow_path(np.array([0, -0.15, 0]) + rng.normal(0, 0.08, 3) * np.array([1, 0, 1]), d, H * rng.uniform(0.75, 1.05),
                         7, rng, gravity=-0.25, wobble=0.12)
        skel.tube(path, 0.015 + 0.01 * H, 0.004, 1, rng, sway0=0.1, sway1=0.8)
        for i in range(2, len(path)):
            p = path[i]
            for k in range(7):
                sp = sprites[int(rng.integers(0, len(sprites)))]
                axis = SPRITE[sp][1]
                bd = normalize(path[i] - path[i - 1])
                g = normalize(-UP + bd * 0.3 + rng.normal(0, 0.3, 3)) if axis == "down" else normalize(bd + rng.normal(0, 0.6, 3) + UP * 0.2)
                nh = crown_normal(p, cc, g, 0.6, 0.2)
                ao = float(0.45 + 0.55 * (p[1] / H))
                L = rng.uniform(*card_len)
                skel.leaf({0}, sp, p, g, perp(g, rng), L, nh, ao, sway=1.0, phase=float(rng.random()), bend=0.1 * L,
                          segs=2, tr=1.0, flutter=1.0, flip=rng.random() < 0.5)
                if k < 3:
                    skel.leaf({1}, sp, p, g, perp(g, rng), L * 1.45, nh, ao, sway=1.0, tr=1.0, flutter=0.6)
    for i in range(int(260 * R)):
        u = rng.uniform(0.25, 1.0)
        az = rng.uniform(0, 2 * math.pi)
        p = np.array([math.cos(az) * R * 0.7 * rng.random(), H * u, math.sin(az) * R * 0.7 * rng.random()])
        sp = sprites[int(rng.integers(0, len(sprites)))]
        g = -UP if SPRITE[sp][1] == "down" else normalize(UP + (p - cc) * 0.5 + rng.normal(0, 0.4, 3))
        L = rng.uniform(*card_len)
        skel.leaf({0}, sp, p, g, perp(g, rng), L, crown_normal(p, cc, g, 0.6, 0.2), float(0.5 + 0.5 * u), sway=1.0,
                  phase=float(rng.random()), segs=2, bend=0.08 * L, tr=1.0, flutter=1.0, flip=rng.random() < 0.5)
    for i in range(8):
        az = i * math.pi / 4
        side = np.array([math.cos(az), 0, math.sin(az)])
        sp = sprites[i % len(sprites)]
        g = -UP if SPRITE[sp][1] == "down" else UP
        base = np.array([0, H * 0.95 if SPRITE[sp][1] == "down" else 0.0, 0])
        skel.leaf({2}, sp, base, g, side, H * 1.05, normalize(np.array([math.sin(az), 0.6, -math.cos(az)])), 0.8, sway=0.6, tr=1.0)
    return skel


# ------------------------------------------------------------- ground cover
def grass_clump(seed, n_cards, height):
    rng = np.random.default_rng(seed)
    m = mk.Mesh(("foliage", True))
    for i in range(n_cards):
        az = i * math.pi / n_cards + rng.normal(0, 0.2)
        side = np.array([math.cos(az), 0, math.sin(az)])
        g = normalize(UP + rng.normal(0, 0.15, 3))
        nh = normalize(UP * 0.9 + np.cross(side, g) * 0.15)
        sp = f"grass_{int(rng.integers(0, 5))}"
        base = rng.normal(0, 0.08, 3) * np.array([1, 0, 1]) - UP * 0.03
        sprite_card(m["foliage"], sp, base, g, side, height * rng.uniform(0.8, 1.2), normal_hint=nh, ao=0.9,
                    sway=1.0, phase=float(rng.random()), bend=0.06, segs=3, hnorm=0.5, translucency=1.0,
                    flutter=0.5, flip_u=rng.random() < 0.5)
    return m


def fern(seed, n_fronds, length):
    rng = np.random.default_rng(seed)
    m = mk.Mesh(("foliage", True))
    for i in range(n_fronds):
        az = i * 2 * math.pi / n_fronds + rng.normal(0, 0.25)
        out = np.array([math.cos(az), 0, math.sin(az)])
        elev = rng.uniform(0.75, 1.25)
        g = normalize(out + UP * elev)
        side = normalize(np.cross(UP, out))
        side = normalize(side * math.cos(0.5) + UP * math.sin(0.5) * (1 if rng.random() < 0.5 else -1) * 0.3)
        L = length * rng.uniform(0.75, 1.15)
        nh = normalize(UP * 0.8 + out * 0.3)
        sprite_card(m["foliage"], f"fern_{int(rng.integers(0, 5))}", rng.normal(0, 0.03, 3) * np.array([1, 0, 1]),
                    g, side, L, normal_hint=nh, ao=0.85, sway=1.0, phase=float(rng.random()), bend=L * 0.55,
                    segs=7, hnorm=0.5, translucency=1.0, flutter=0.6, flip_u=rng.random() < 0.5,
                    bend_dir=normalize(out * 0.4 - UP))
    return m


def forb(seed, height, leaves=8, sprites=("nettle_0", "nettle_1", "nettle_2", "nettle_3")):
    rng = np.random.default_rng(seed)
    m = mk.Mesh(("bark", False), ("foliage", True))
    path = grow_path(np.array([0, -0.02, 0]), UP + rng.normal(0, 0.1, 3), height, 3, rng, wobble=0.08)
    mk.tube(m["bark"], path, np.linspace(0.006, 0.003, len(path)), 3, 4.0, 1, 4.0, np.linspace(0, 1, len(path)), 0.3,
            np.linspace(0, 1, len(path)), 0.8)
    for i in range(leaves):
        t = 0.25 + 0.75 * i / leaves
        k = min(int(t * (len(path) - 1)), len(path) - 2)
        p = path[k] + (path[k + 1] - path[k]) * (t * (len(path) - 1) - k)
        az = i * 2.4 + rng.normal(0, 0.2)
        out = np.array([math.cos(az), 0, math.sin(az)])
        g = normalize(out + UP * rng.uniform(0.0, 0.5))
        side = normalize(np.cross(UP, out))
        L = height * rng.uniform(0.28, 0.42) * (1.15 - 0.4 * t)
        sprite_card(m["foliage"], sprites[int(rng.integers(0, len(sprites)))], p + g * L * 0.45, g, side, L,
                    normal_hint=normalize(UP + out * 0.3), ao=0.85, sway=0.8, phase=float(rng.random()), bend=0.0,
                    hnorm=0.5, translucency=1.0, flutter=0.8)
    return m


def compound_plant(seed, height):
    rng = np.random.default_rng(seed)
    m = mk.Mesh(("foliage", True))
    for i in range(int(rng.integers(5, 8))):
        az = i * 2.4 + rng.normal(0, 0.2)
        out = np.array([math.cos(az), 0, math.sin(az)])
        g = normalize(out * 0.6 + UP)
        sprite_card(m["foliage"], "compound_leaf", np.zeros(3), g, normalize(np.cross(UP, out)), height * rng.uniform(0.8, 1.1),
                    normal_hint=normalize(UP + out * 0.4), ao=0.85, sway=1.0, phase=float(rng.random()), bend=height * 0.3,
                    segs=3, hnorm=0.5, translucency=1.0, flutter=0.8, bend_dir=normalize(out - UP))
    return m


def moss_sprouts(seed, n):
    rng = np.random.default_rng(seed)
    m = mk.Mesh(("foliage", True))
    for i in range(n):
        p = rng.normal(0, 0.12, 3) * np.array([1, 0, 1])
        az = rng.uniform(0, math.pi)
        side = np.array([math.cos(az), 0, math.sin(az)])
        sprite_card(m["foliage"], f"moss_{int(rng.integers(0, 3))}", p - UP * 0.01, normalize(UP + rng.normal(0, 0.2, 3)), side,
                    rng.uniform(0.07, 0.14), normal_hint=UP, ao=0.8, sway=0.3, hnorm=0.5, translucency=0.8, flutter=0.2)
    return m


def fallen_log(seed, length, r0, layer):
    rng = np.random.default_rng(seed)
    skel = Skeleton(r0 * 2, float(layer) + 0.5, length)
    pts = []
    for i in range(int(length / 0.5) + 1):
        x = -length / 2 + i * 0.5
        pts.append(np.array([x, r0 * 0.75 + 0.04 * math.sin(i * 0.7), 0.06 * math.sin(i * 0.5)]))
    pts = np.array(pts)
    rad = r0 * np.linspace(1.0, 0.65, len(pts)) * (1 + 0.04 * rng.normal(0, 1, len(pts)))
    skel.tube(pts, 0, 0, 0, rng, radii=rad, cap=True,
              mod=lambda y, a: 1 + 0.06 * math.cos(3 * a) + 0.03 * math.sin(7 * a))
    skel.tubes[-1]["points"] = skel.tubes[-1]["points"][::-1].copy()  # cap at the thick, broken end
    skel.tubes[-1]["radii"] = skel.tubes[-1]["radii"][::-1].copy()
    for i in range(int(length * 0.8)):
        t = rng.uniform(0.15, 0.95)
        p = pts[int(t * (len(pts) - 1))]
        az = rng.uniform(0, 2 * math.pi)
        d = np.array([rng.uniform(-0.3, 0.3), math.cos(az), math.sin(az)])
        path = grow_path(p + d * r0 * 0.8, d, rng.uniform(0.15, 0.6), 2, rng, wobble=0.1)
        skel.tube(path, 0.03, 0.01, 2, rng, cap=True)
    return skel


def root_cluster(seed, r0):
    """Exposed roots of a long-gone tree snaking over the forest floor, half buried."""
    rng = np.random.default_rng(seed)
    skel = Skeleton(0.6, 1.5, 2.5)
    for k in range(int(rng.integers(5, 9))):
        az = rng.uniform(0, 2 * math.pi)
        d = np.array([math.cos(az), 0, math.sin(az)])
        pts = [np.array([0, 0.05, 0]) + d * 0.2]
        L = rng.uniform(1.2, 2.8)
        for i in range(1, 9):
            t = i / 8
            dd = normalize(d + perp(d, rng) * 0.35)
            d = normalize(np.array([dd[0], 0, dd[2]]))
            pts.append(pts[-1] + d * L / 8 + np.array([0, 0.07 * math.sin(t * 9 + k) - 0.03 * t, 0]))
        pts = np.array(pts)
        rad = r0 * np.linspace(1.0, 0.25, len(pts))
        skel.tube(pts, 0, 0, 1, rng, radii=rad)
        for j in range(2):
            i0 = int(rng.integers(2, 6))
            sub = grow_path(pts[i0], normalize(perp(d, rng) * np.array([1, 0.1, 1])), rng.uniform(0.4, 1.0), 4, rng, gravity=-0.1, wobble=0.15)
            skel.tube(sub, r0 * 0.4, r0 * 0.1, 2, rng)
    return skel


def branch_pile(seed, n, length):
    """Dead sticks and fallen branches lying in a loose heap."""
    rng = np.random.default_rng(seed)
    skel = Skeleton(0.5, 1.5, length)
    for k in range(n):
        az = rng.uniform(0, 2 * math.pi)
        d = np.array([math.cos(az), rng.uniform(-0.05, 0.12), math.sin(az)])
        c = rng.normal(0, length * 0.18, 3) * np.array([1, 0, 1]) + np.array([0, 0.04 + 0.05 * k / n, 0])
        L = length * rng.uniform(0.45, 1.0)
        path = grow_path(c - d * L / 2, d, L, 5, rng, wobble=0.1)
        r = rng.uniform(0.015, 0.045)
        skel.tube(path, r, r * 0.4, 1, rng, cap=True)
        for j in range(int(rng.integers(1, 4))):
            i0 = int(rng.integers(1, 5))
            sub = grow_path(path[i0], normalize(perp(normalize(path[i0 + 1] - path[i0]), rng) + d), L * rng.uniform(0.15, 0.35), 2, rng, wobble=0.15)
            skel.tube(sub, r * 0.5, r * 0.2, 2, rng)
    return skel


def fallen_tree(seed, length, r0, layer):
    """Wind-thrown conifer: trunk on the ground, root plate, dead branch stubs along the stem."""
    rng = np.random.default_rng(seed)
    skel = fallen_log(seed, length, r0, layer)
    pts = skel.tubes[0]["points"]
    # points run from the thin top (index 0) to the thick butt (last, capped)
    for i in range(int(length * 2.5)):
        t = rng.uniform(0.02, 0.75)
        p = pts[int(t * (len(pts) - 1))]
        az = rng.uniform(0, 2 * math.pi)
        d = np.array([rng.uniform(-0.6, 0.2), math.cos(az), math.sin(az)])
        path = grow_path(p + d * r0 * 0.7, d, rng.uniform(0.3, 1.3) * (0.6 + t * 0.8), 3, rng, gravity=-0.35, wobble=0.12)
        skel.tube(path, 0.025, 0.008, 2, rng, cap=True)
    # root plate at the thick end
    end = pts[-1]
    for k in range(9):
        az = 2 * math.pi * k / 9
        d = np.array([0.0, math.cos(az), math.sin(az)])
        path = grow_path(end, d - np.array([0.4, 0, 0]), r0 * rng.uniform(3.0, 5.0), 4, rng, wobble=0.15)
        skel.tube(path, r0 * 0.45, 0.02, 1, rng)
    return skel


# ------------------------------------------------------------ scanned assets
def load_scan(aid):
    from gltfio import Gltf  # local helper (tools/gltfio.py)
    g = Gltf(os.path.join(SRC, "models", aid, aid + ".gltf"))
    return g.meshes_world()


def decimate(pos, nrm, uv, idx, target_tris, lock_border=False):
    import meshoptimizer as mo
    # meshopt_simplify keeps UV seams intact (it detects them through a position remap)
    pos32 = np.ascontiguousarray(pos, np.float32)
    out = np.zeros_like(idx, dtype=np.uint32)
    n = mo.simplify(out, np.ascontiguousarray(idx, np.uint32), pos32, target_index_count=target_tris * 3,
                    target_error=0.2, options=mo.SIMPLIFY_LOCK_BORDER if lock_border else 0)
    if n > target_tris * 3 * 1.6:
        n = mo.simplify_sloppy(out, np.ascontiguousarray(idx, np.uint32), pos32, target_index_count=target_tris * 3,
                               target_error=0.5)
    return out[:n]


def scan_mesh(parts, rect, targets, sink=0.0, layer_attr=0.0, recenter=True, scale=1.0, rot_x=0.0):
    """parts: list of primitive dicts (world space). Returns list of Mesh for each LOD target."""
    P = np.concatenate([p["pos"] for p in parts]); N = np.concatenate([p["nrm"] for p in parts])
    U = np.concatenate([p["uv"] for p in parts])
    I = []; o = 0
    for p in parts:
        I.append(p["idx"] + o); o += len(p["pos"])
    I = np.concatenate(I).astype(np.uint32)
    if rot_x:
        c, s = math.cos(rot_x), math.sin(rot_x)
        R = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
        P = P @ R.T; N = N @ R.T
    if recenter:
        mn, mx = P.min(0), P.max(0)
        P = P - np.array([(mn[0] + mx[0]) / 2, mn[1] + sink * (mx[1] - mn[1]), (mn[2] + mx[2]) / 2])
    P = P * scale
    # remap uv into atlas rect (glTF uv origin top-left, same as atlas image space)
    UVa = np.stack([rect[0] + U[:, 0] * rect[2], rect[1] + U[:, 1] * rect[3]], axis=1)
    out = []
    h = max(P[:, 1].max(), 0.1)
    for tgt in targets:
        idx = I if tgt >= len(I) // 3 else decimate(P, N, U, I, tgt)
        used = np.unique(idx)
        remap = np.full(len(P), -1, np.int64); remap[used] = np.arange(len(used))
        m = mk.Mesh(("surface", False))
        hn = np.clip(P[used, 1] / h, 0, 1)
        col = np.stack([np.clip(0.6 + 0.4 * hn, 0, 1), np.zeros(len(used)), np.zeros(len(used)), np.zeros(len(used))], axis=1)
        m["surface"].add(P[used], N[used], UVa[used], np.stack([np.full(len(used), layer_attr), hn], axis=1), col,
                         remap[idx].astype(np.uint32))
        out.append(m)
    return out


# --------------------------------------------------------------------- build
CATALOG = []


def save_lods(group, name, meshes, materials, meta):
    meshes = [m for m in meshes if m.tris > 0]
    os.makedirs(os.path.join(ROOT, "assets", group), exist_ok=True)
    path = os.path.join(ROOT, "assets", group, name + ".glb")
    mk.write_glb(path, [(f"LOD{i}", m) for i, m in enumerate(meshes)], materials)
    write_scene_import(path)
    mn, mx = meshes[0].bounds()
    entry = dict(name=name, group=group, file=f"res://assets/{group}/{name}.glb",
                 tris=[m.tris for m in meshes], aabb=[mn.round(3).tolist(), mx.round(3).tolist()],
                 surfaces=[s for s, _ in materials], **meta)
    CATALOG.append(entry)
    print(f"{group:10s} {name:16s} tris {entry['tris']}  h={mx[1]:.1f}")


def write_scene_import(path):
    with open(path + ".import", "w") as f:
        f.write('[remap]\n\nimporter="scene"\nimporter_version=1\ntype="PackedScene"\n\n[params]\n\n'
                "nodes/root_type=\"Node3D\"\nmeshes/ensure_tangents=true\nmeshes/generate_lods=false\n"
                "meshes/create_shadow_meshes=true\nmeshes/light_baking=0\nmeshes/force_disable_compression=false\n"
                "skins/use_named_skins=true\nanimation/import=false\nimport_script/path=\"\"\n")


def tree_meta(skel, category, lod_d, clearance, kind):
    return dict(category=category, kind=kind, height=round(skel.H, 2), crown_radius=round(skel.crown_r, 2),
                clearance=clearance, lod=lod_d)


def main():
    FOL = [("bark", False), ("foliage", True)]
    # ---------------- large trees (14 variants)
    large = [
        ("pine_a", lambda: pine(11, 24.0, 0.31, 0.62), "pine", 0.31),
        ("pine_b", lambda: pine(12, 21.0, 0.27, 0.55, lean=0.05), "pine", 0.27),
        ("pine_c", lambda: pine(13, 17.5, 0.22, 0.50), "pine", 0.22),
        ("spruce_a", lambda: conifer(21, "spruce", 28.0, 0.35, 0.30, 3.5), "spruce", 0.35),
        ("spruce_b", lambda: conifer(22, "spruce", 22.0, 0.28, 0.22, 3.0), "spruce", 0.28),
        ("spruce_c", lambda: conifer(23, "spruce", 17.0, 0.22, 0.14, 2.6), "spruce", 0.22),
        ("fir_a", lambda: conifer(31, "fir", 25.0, 0.31, 0.32, 3.1), "fir", 0.31),
        ("fir_b", lambda: conifer(32, "fir", 19.0, 0.25, 0.24, 2.7), "fir", 0.25),
        ("birch_a", lambda: deciduous(41, "birch", 21.0, 0.17, 0.42, 3.2, 2, ["birch_twig", "leafy_branch"], card_len=(0.8, 1.2)), "birch", 0.17),
        ("birch_b", lambda: deciduous(42, "birch", 17.0, 0.14, 0.36, 2.8, 2, ["birch_twig", "leafy_branch"], twin=True, card_len=(0.75, 1.1)), "birch", 0.14),
        ("oak_a", lambda: deciduous(51, "oak", 20.0, 0.44, 0.25, 6.8, 3, ["oak_cluster"], bole=4.6, n_main=5, card_len=(0.9, 1.3), cards_per_twig=6), "oak", 0.44),
        ("oak_b", lambda: deciduous(52, "oak", 16.0, 0.35, 0.25, 5.4, 3, ["oak_cluster"], bole=3.6, n_main=4, card_len=(0.85, 1.25), cards_per_twig=6), "oak", 0.35),
        ("alder_a", lambda: deciduous(61, "decid", 14.0, 0.18, 0.30, 3.2, 5, ["decid_cluster", "leafy_branch"], card_len=(0.7, 1.0), cards_per_twig=6), "decid", 0.18),
        ("linden_a", lambda: deciduous(62, "decid", 18.0, 0.25, 0.30, 4.4, 4, ["decid_cluster"], card_len=(0.8, 1.15), cards_per_twig=6), "decid", 0.25),
    ]
    for name, fn, kind, r0 in large:
        sk = fn()
        meshes = [emit(sk, l) for l in range(3)]
        save_lods("trees", name, meshes, FOL, tree_meta(sk, "tree", [40.0, 120.0, 420.0], round(r0 * 1.6 + 0.3, 2), kind))
    # ---------------- medium vegetation (8 variants)
    medium = [
        ("young_spruce_a", lambda: conifer(121, "spruce", 6.0, 0.09, 0.02, 1.8, young=True), "spruce", 0.09),
        ("young_spruce_b", lambda: conifer(122, "spruce", 3.6, 0.06, 0.0, 1.2, young=True), "spruce", 0.06),
        ("young_fir", lambda: conifer(123, "fir", 4.4, 0.07, 0.03, 1.5, young=True), "fir", 0.07),
        ("young_pine", lambda: pine(124, 4.6, 0.07, 0.22, young=True), "pine", 0.07),
        ("young_birch_a", lambda: deciduous(141, "birch", 7.5, 0.06, 0.35, 1.5, 2, ["birch_twig", "leafy_branch"], young=True, n_main=18, card_len=(0.6, 0.9), cards_per_twig=8), "birch", 0.06),
        ("young_birch_b", lambda: deciduous(142, "birch", 5.5, 0.05, 0.30, 1.2, 2, ["leafy_branch"], young=True, n_main=16, card_len=(0.55, 0.8), cards_per_twig=8), "birch", 0.05),
        ("hazel", lambda: bush(151, 4.0, 2.0, ["decid_cluster", "leafy_branch"], stems=(12, 16), card_len=(0.6, 0.9), layer=5), "decid", 0.05),
        ("snag", lambda: snag(161, 9.0, 0.2), "snag", 0.2),
        ("young_alder", lambda: deciduous(173, "decid", 7.0, 0.07, 0.3, 1.8, 5, ["decid_cluster", "leafy_branch"], young=True, n_main=13, card_len=(0.55, 0.85), cards_per_twig=7), "decid", 0.07),
        ("rowan", lambda: deciduous(171, "decid", 6.5, 0.08, 0.35, 1.9, 5, ["decid_cluster", "leafy_branch"], young=True, n_main=12, card_len=(0.55, 0.85), cards_per_twig=7), "decid", 0.08),
        ("young_oak", lambda: deciduous(172, "decid", 5.5, 0.09, 0.3, 2.1, 3, ["oak_cluster"], young=True, n_main=10, card_len=(0.55, 0.85), cards_per_twig=7), "oak", 0.09),
    ]
    for name, fn, kind, r0 in medium:
        sk = fn()
        meshes = [emit(sk, l) for l in range(3)]
        save_lods("vegetation", name, meshes, FOL, tree_meta(sk, "understory", [25.0, 70.0, 230.0], round(r0 * 2 + 0.25, 2), kind))
    # ---------------- bushes (6 variants)
    bushes = [
        ("bush_broad_a", lambda: bush(201, 1.6, 1.0, ["decid_cluster"], stems=(8, 12)), "decid"),
        ("bush_broad_b", lambda: bush(202, 1.2, 0.9, ["decid_cluster", "leafy_branch"], stems=(8, 12), card_len=(0.4, 0.6)), "decid"),
        ("bush_birch", lambda: bush(203, 2.2, 1.1, ["leafy_branch", "birch_twig"], stems=(8, 12), card_len=(0.5, 0.8)), "birch"),
        ("bush_oak", lambda: bush(204, 1.4, 1.0, ["oak_cluster"], stems=(8, 12), card_len=(0.45, 0.7)), "oak"),
        ("sapling_fir", lambda: conifer(205, "fir", 1.6, 0.025, 0.0, 0.65, young=True), "fir"),
        ("sapling_spruce", lambda: conifer(206, "spruce", 1.1, 0.02, 0.0, 0.5, young=True), "spruce"),
        ("bush_hazel", lambda: bush(209, 2.6, 1.3, ["decid_cluster", "leafy_branch"], stems=(10, 14), card_len=(0.55, 0.8), layer=5), "decid"),
        ("bush_elder", lambda: bush(210, 2.0, 1.2, ["decid_cluster"], stems=(9, 12), card_len=(0.5, 0.75), layer=4), "decid"),
        ("juniper", lambda: bush(211, 1.5, 0.7, ["fir_a", "fir_b", "fir_c"], stems=(10, 14), card_len=(0.35, 0.55), layer=1), "fir"),
        ("bilberry_a", lambda: bush(207, 0.45, 0.55, ["leafy_branch", "birch_twig"], stems=(10, 14), card_len=(0.22, 0.32)), "decid"),
        ("bilberry_b", lambda: bush(208, 0.35, 0.45, ["leafy_branch"], stems=(8, 12), card_len=(0.18, 0.28)), "decid"),
    ]
    for name, fn, kind in bushes:
        sk = fn()
        meshes = [emit(sk, l) for l in range(3)]
        lod_d = [10.0, 24.0, 55.0] if name.startswith("bilberry") else [18.0, 45.0, 120.0]
        save_lods("vegetation", name, meshes, FOL, tree_meta(sk, "bush", lod_d, 0.5, kind))
    # ---------------- ground cover (single LOD + far fade)
    cover = [
        ("grass_a", grass_clump(301, 4, 0.42), [0.0, 0.0, 48.0], "grass"),
        ("grass_b", grass_clump(302, 3, 0.32), [0.0, 0.0, 48.0], "grass"),
        ("grass_c", grass_clump(303, 5, 0.55), [0.0, 0.0, 48.0], "grass"),
        ("grass_d", grass_clump(304, 7, 0.68), [0.0, 0.0, 48.0], "grass"),
        ("grass_e", grass_clump(305, 6, 0.4), [0.0, 0.0, 48.0], "grass"),
        ("fern_a", fern(311, 9, 0.85), [0.0, 0.0, 65.0], "fern"),
        ("fern_b", fern(312, 12, 1.05), [0.0, 0.0, 65.0], "fern"),
        ("fern_c", fern(313, 7, 0.65), [0.0, 0.0, 65.0], "fern"),
        ("fern_d", fern(314, 16, 1.25), [0.0, 0.0, 65.0], "fern"),
        ("fern_e", fern(315, 6, 0.45), [0.0, 0.0, 65.0], "fern"),
        ("nettle_a", forb(321, 0.55), [0.0, 0.0, 40.0], "forb"),
        ("nettle_b", forb(322, 0.38, leaves=6), [0.0, 0.0, 40.0], "forb"),
        ("cow_parsley", compound_plant(323, 0.45), [0.0, 0.0, 40.0], "forb"),
        ("sprouts", moss_sprouts(331, 14), [0.0, 0.0, 22.0], "sprouts"),
    ]
    for name, m, lod_d, kind in cover:
        mats = [(s, a) for s, a in FOL if s in m.s]
        save_lods("vegetation", name, [m], mats, dict(category="cover", kind=kind, height=round(m.bounds()[1][1], 2),
                                                     crown_radius=0.4, clearance=0.0, lod=lod_d))
    # ---------------- rocks (scans, atlas)
    ratl = json.load(open(os.path.join(ROOT, "assets", "textures", "rocks", "rocks_atlas.json")))["rects"]
    RM = [("surface", False)]
    for aid in ("rock_moss_set_01", "rock_moss_set_02"):
        for node, mesh, mat, d in load_scan(aid):
            nm = node.replace(aid + "_", "")
            if aid == "rock_moss_set_02" and nm in ("rock08", "rock12", "rock07"):
                continue
            meshes = scan_mesh([d], ratl[aid], [2000, 500, 120], sink=0.12)
            short = ("mossrock_a_" if aid.endswith("01") else "mossrock_b_") + nm[-2:]
            mn, mx = meshes[0].bounds()
            save_lods("rocks", short, meshes, RM, dict(category="rock", kind="rock", height=round(float(mx[1]), 2),
                                                       crown_radius=round(float(max(mx[0] - mn[0], mx[2] - mn[2]) / 2), 2),
                                                       clearance=round(float(max(mx[0] - mn[0], mx[2] - mn[2]) / 2), 2),
                                                       lod=[30.0, 85.0, 320.0]))
    parts = [d for *_, d in load_scan("boulder_01")]
    meshes = scan_mesh(parts, ratl["boulder_01"], [2600, 650, 150], sink=0.08)
    mn, mx = meshes[0].bounds()
    save_lods("rocks", "boulder", meshes, RM, dict(category="rock", kind="rock", height=round(float(mx[1]), 2),
                                                    crown_radius=round(float(max(mx[0] - mn[0], mx[2] - mn[2]) / 2), 2),
                                                    clearance=round(float(max(mx[0] - mn[0], mx[2] - mn[2]) / 2), 2),
                                                    lod=[35.0, 95.0, 340.0]))
    parts = [d for *_, d in load_scan("stone_01")]
    meshes = scan_mesh(parts, ratl["stone_01"], [160], sink=0.1, scale=1.6)
    save_lods("rocks", "stone", meshes, RM, dict(category="cover", kind="stone", height=0.1, crown_radius=0.12,
                                                  clearance=0.0, lod=[0.0, 0.0, 38.0]))
    # ---------------- props (scans, atlas) + procedural logs
    patl = json.load(open(os.path.join(ROOT, "assets", "textures", "props", "props_atlas.json")))["rects"]
    for aid, short, tg, lod_d in (("tree_stump_01", "stump_a", [1800, 450, 110], [25.0, 65.0, 160.0]),
                                  ("tree_stump_02", "stump_b", [1800, 450, 110], [25.0, 65.0, 160.0]),
                                  ("dead_tree_trunk", "log_scan", [2400, 600, 150], [28.0, 70.0, 180.0])):
        parts = [d for *_, d in load_scan(aid)]
        meshes = scan_mesh(parts, patl[aid], tg, sink=0.05 if "stump" in short else 0.0)
        mn, mx = meshes[0].bounds()
        save_lods("props", short, meshes, RM, dict(category="prop", kind=short.split("_")[0], height=round(float(mx[1]), 2),
                                                    crown_radius=round(float(max(mx[0] - mn[0], mx[2] - mn[2]) / 2), 2),
                                                    clearance=round(float(max(mx[0] - mn[0], mx[2] - mn[2]) / 2), 2), lod=lod_d))
    for node, mesh, mat, d in load_scan("dry_branches_medium_01"):
        short = "branches_" + node[-1]
        meshes = scan_mesh([d], patl["dry_branches_medium_01"], [420])
        save_lods("props", short, meshes, RM, dict(category="cover", kind="branches", height=0.2, crown_radius=0.6,
                                                    clearance=0.0, lod=[0.0, 0.0, 42.0]))
    for name, seed, L, r0, layer in (("log_pine", 401, 11.0, 0.24, 0), ("log_spruce", 402, 8.0, 0.2, 1)):
        sk = fallen_log(seed, L, r0, layer)
        meshes = [emit(sk, l) for l in range(3)]
        save_lods("props", name, meshes, FOL[:1], dict(category="prop", kind="log", height=round(r0 * 2, 2),
                                                       crown_radius=L / 2, clearance=L / 2, lod=[30.0, 75.0, 200.0]))
    # ---------------- additional environmental details (procedural, bark material)
    details = [
        ("roots_a", lambda: root_cluster(501, 0.09)), ("roots_b", lambda: root_cluster(502, 0.12)),
        ("roots_c", lambda: root_cluster(503, 0.07)), ("branch_pile_a", lambda: branch_pile(511, 14, 2.4)),
        ("branch_pile_b", lambda: branch_pile(512, 9, 1.6)),
        ("fallen_spruce", lambda: fallen_tree(521, 14.0, 0.26, 1)),
        ("roots_d", lambda: root_cluster(504, 0.15)), ("branch_pile_c", lambda: branch_pile(513, 18, 3.0)),
        ("fallen_birch", lambda: fallen_tree(522, 10.0, 0.16, 2)), ("fallen_pine", lambda: fallen_tree(523, 9.0, 0.21, 0)),
    ]
    for name, fn in details:
        sk = fn()
        meshes = [emit(sk, l) for l in range(3)]
        mn, mx = meshes[0].bounds()
        rad = float(max(mx[0] - mn[0], mx[2] - mn[2]) / 2)
        save_lods("props", name, meshes, FOL[:1], dict(category="detail", kind="log" if "fallen" in name else "detail",
                                                       height=round(float(mx[1]), 2), crown_radius=rad, clearance=rad,
                                                       lod=[22.0, 55.0, 140.0]))
    # ---------------- summary
    groups = {}
    for e in CATALOG:
        groups.setdefault(e["group"] + "/" + e["category"], 0)
        groups[e["group"] + "/" + e["category"]] += sum(e["tris"])
    total = sum(groups.values())
    with open(os.path.join(ROOT, "assets", "catalog.json"), "w") as f:
        json.dump({"variants": CATALOG, "triangle_budget": groups, "total_unique_triangles": int(total)}, f, indent=1, default=float)
    print(json.dumps(groups, indent=1), "\nTOTAL unique triangles (all LODs):", total)


if __name__ == "__main__":
    main()
