"""Room shells: inner wall faces with openings, floors, ceilings, window reveals and sills,
door-opening linings, corridor pilasters. Pure geometry into MB builders."""
from .params import *
from .layout import COLUMNS_X, FRAMED
from .meshkit import MB, subtract_rects
from .materials import UV_SCALE
from .atlas import FURN_UV

STAIR_KINDS = ("stair_main", "stair_end")


def wall_bands(room):
    z0, z1 = room.z0, room.z1
    if room.kind == "shaft":
        return [(z0, z1, "concrete", None)]
    if room.kind in STAIR_KINDS:
        out = []
        for i, L in enumerate(LEVELS):
            a, b = max(L, z0), min(L + FLOOR_H if i < 3 else z1, z1)
            if b - a > 1e-6:
                out.append((a, b, room.wall, L))
        return out
    if z1 - z0 > CEIL_H + 0.01:
        return [(z0, z0 + CEIL_H, room.wall, z0), (z0 + CEIL_H, z1, room.upper_wall, None)]
    return [(z0, z1, room.wall, z0)]


def wall_uv(mat, s_signed, z, vref):
    sc = UV_SCALE.get(mat, 3.0)
    if vref is None:
        return (s_signed / sc, z / sc)
    return (s_signed / 3.0, (z - vref) / 3.0)


def face_quad(mb, e, sa, sb, za, zb, mat, vref, inset=0.0):
    """Quad on edge e facing into the room (normal = -e.n)."""
    c = e.coord - e.n * inset
    if e.axis == "y":       # plane x = c
        if e.n < 0:        # faces +X, right = +Y
            pts = [(c, sa, za), (c, sb, za), (c, sb, zb), (c, sa, zb)]
            sg = 1
        else:              # faces -X, right = -Y
            pts = [(c, sb, za), (c, sa, za), (c, sa, zb), (c, sb, zb)]
            sg = -1
        uvs = [wall_uv(mat, sg * p[1], p[2], vref) for p in pts]
    else:                   # plane y = c
        if e.n < 0:        # faces +Y, right = -X
            pts = [(sb, c, za), (sa, c, za), (sa, c, zb), (sb, c, zb)]
            sg = -1
        else:              # faces -Y, right = +X
            pts = [(sa, c, za), (sb, c, za), (sb, c, zb), (sa, c, zb)]
            sg = 1
        uvs = [wall_uv(mat, sg * p[0], p[2], vref) for p in pts]
    mb.poly(pts, uvs, mat)


def world_uv(mat, x, y):
    s = UV_SCALE.get(mat, 2.0)
    return (x / s, y / s)


def floor_quad(mb, x0, x1, y0, y1, z, mat, up=True):
    pts = [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]
    if not up:
        pts = list(reversed(pts))
    mb.poly(pts, [world_uv(mat, p[0], p[1]) for p in pts], mat)


def at(e, s, z, d):
    """World point on edge e: s along the wall, z height, d = offset outward from the face (into the wall)."""
    c = e.coord + e.n * d
    return (c, s, z) if e.axis == "y" else (s, c, z)


def sdir(e):
    return (0.0, 1.0, 0.0) if e.axis == "y" else (1.0, 0.0, 0.0)


def into_room(e):
    return (-e.n, 0.0, 0.0) if e.axis == "y" else (0.0, -e.n, 0.0)


def neg(v):
    return (-v[0], -v[1], -v[2])


def reveal(mb, e, s0, s1, z0, z1, depth, mat, sides=("l", "r", "t", "b")):
    """Lining of an opening in the face of edge e, from the face to `depth` into the wall."""
    D = depth
    S = sdir(e)

    def q(p, uvmode, want):
        uvs = [(s / 2.0, d / 2.0) if uvmode == "s" else (d / 2.0, z / 2.0) for (s, z, d) in p]
        mb.poly_n([at(e, s, z, d) for (s, z, d) in p], uvs, mat, want)
    if "l" in sides:
        q([(s0, z0, 0), (s0, z0, D), (s0, z1, D), (s0, z1, 0)], "z", S)
    if "r" in sides:
        q([(s1, z0, 0), (s1, z0, D), (s1, z1, D), (s1, z1, 0)], "z", neg(S))
    if "t" in sides:
        q([(s0, z1, 0), (s0, z1, D), (s1, z1, D), (s1, z1, 0)], "s", (0, 0, -1))
    if "b" in sides:
        q([(s0, z0, 0), (s0, z0, D), (s1, z0, D), (s1, z0, 0)], "s", (0, 0, 1))


def fix_orientation_axis(e):
    return e


def room_shell(lay, room):
    mb = MB(f"Shell_{room.rid}")
    for e in lay.edges[room.rid]:
        cuts = lay.face_cuts(e)
        rects = subtract_rects(e.a, e.b, room.z0, room.z1, cuts)
        for (sa, sb, za, zb) in rects:
            for (ba, bb, mat, vref) in wall_bands(room):
                a, b = max(za, ba), min(zb, bb)
                if b - a > 1e-6:
                    face_quad(mb, e, sa, sb, a, b, mat, vref)
    for (x0, x1, y0, y1) in room.rects:
        fm = "concrete" if room.kind == "shaft" else room.floor
        if room.kind not in STAIR_KINDS or True:
            floor_quad(mb, x0, x1, y0, y1, room.z0, fm, True)
        cm = "concrete" if room.kind == "shaft" else ("plaster" if room.kind in STAIR_KINDS else room.ceil)
        floor_quad(mb, x0, x1, y0, y1, room.z1, cm, False)
    return mb


def window_parts(lay, mb_reveal, mb_sill):
    """Interior reveals and sill boards of all exterior windows; returns radiator slots."""
    rads = []
    sill_uv = FURN_UV["metal_white"]
    for wi, e in lay.win_room.items():
        w = lay.windows[wi]
        depth = abs(w.glass - w.face)
        s0, s1 = w.s - w.hw, w.s + w.hw
        reveal(mb_reveal, e, s0, s1, w.z0, w.z1, depth, "plaster", sides=("l", "r", "t"))
        # sill board: top flush with the glass bottom, 50 mm overhang, 30 mm thick
        a0, a1 = s0 - 0.05, s1 + 0.05
        top = w.z0
        pts_top = [at(e, a0, top, depth), at(e, a1, top, depth), at(e, a1, top, -0.05), at(e, a0, top, -0.05)]
        pts_front = [at(e, a0, top - 0.035, -0.05), at(e, a1, top - 0.035, -0.05), at(e, a1, top, -0.05),
                     at(e, a0, top, -0.05)]
        pts_under = [at(e, a0, top - 0.035, 0), at(e, a1, top - 0.035, 0), at(e, a1, top - 0.035, -0.05),
                     at(e, a0, top - 0.035, -0.05)]
        u0, v0, u1, v1 = sill_uv
        uv4 = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        IN, S = into_room(e), sdir(e)
        mb_sill.poly_n(pts_top, uv4, "atlas_furn", (0, 0, 1))
        mb_sill.poly_n(pts_front, uv4, "atlas_furn", IN)
        floor_z = w.z0 - (STD_Z0 + WIN_BASE) if w.kind == "std" else LEVELS[1]
        rads.append(dict(room=e.room.rid, edge=e, s=w.s, width=min(2 * w.hw - 0.2, 1.6), floor=floor_z, win=w))
    return rads


def opening_linings(lay, mb):
    """Reveal linings for doorways without frames (counters, glazed openings, ports, open arches)."""
    for g in lay.doors:
        if g.door.kind in FRAMED or g.door.kind == "lift":
            continue
        e = g.ea
        depth = g.thickness
        sides = ("l", "r", "t", "b") if g.door.sill > 0 else ("l", "r", "t")
        reveal(mb, e, g.c - g.ow / 2, g.c + g.ow / 2, g.z0, g.z1, depth, "plaster", sides)


def narrow_portals(lay, mb, limit=1.0, head=2.3, T=0.12):
    """Where two rectangles of one room meet over less than `limit` (only the 0.9 m passage from the entrance hall
    past the vestibule; the 1.16 m entries beside the bathroom pods stay open), there is no wall at all and the
    opening read as walls that fail to meet. Such a junction gets what a builder would put there: a lintel
    down to `head` above the floor, wood linings on the jambs and under the lintel, and casings where the
    wall continues past the opening."""
    from .doors import CASE_W, CASE_T
    wu0, wv0, wu1, wv1 = FURN_UV["wood_dark"]
    wood = [(wu0, wv0), (wu1, wv0), (wu1, wv1), (wu0, wv1)]
    for room in lay.rooms.values():
        q = room.rects
        for i in range(len(q)):
            for j in range(len(q)):
                A, B = q[i], q[j]          # A: the narrow passage, B: the room it opens into
                for ax in (0, 1):          # 0: junction plane x = X, 1: plane y = Y
                    a0, a1 = (A[0], A[1]) if ax == 0 else (A[2], A[3])
                    b0, b1 = (B[0], B[1]) if ax == 0 else (B[2], B[3])
                    s_a = (A[2], A[3]) if ax == 0 else (A[0], A[1])
                    s_b = (B[2], B[3]) if ax == 0 else (B[0], B[1])
                    if abs(a1 - b0) < 1e-4:
                        X, k = a1, 1
                    elif abs(b1 - a0) < 1e-4:
                        X, k = a0, -1
                    else:
                        continue
                    lo, hi = max(s_a[0], s_b[0]), min(s_a[1], s_b[1])
                    # only a real passage: A is no wider than the junction, and the junction is narrow
                    if not (0.5 < hi - lo < limit) or s_a[1] - s_a[0] > hi - lo + 1e-4:
                        continue
                    z0, zb, z1 = room.z0, room.z0 + head, room.z0 + CEIL_H

                    def P(d, s_, z):           # d: offset from the plane towards B
                        return (X + k * d, s_, z) if ax == 0 else (s_, X + k * d, z)

                    def N(d, ds, dz):
                        return (k * d, ds, dz) if ax == 0 else (ds, k * d, dz)
                    wall_uv_ = lambda pts: [((p_[1] if ax == 0 else p_[0]) / 3.0, (p_[2] - z0) / 3.0) for p_ in pts]
                    for d, sg in ((0.0, 1), (-T, -1)):        # lintel faces on both sides, painted like the walls
                        pts = [P(d, lo, zb), P(d, hi, zb), P(d, hi, z1), P(d, lo, z1)]
                        mb.poly_n(pts, wall_uv_(pts), room.wall, N(sg, 0, 0))
                    # wood linings under the lintel and on the jambs (4 mm proud of the side walls)
                    mb.poly_n([P(-T, lo, zb), P(CASE_T, lo, zb), P(CASE_T, hi, zb), P(-T, hi, zb)], wood,
                              "atlas_furn", (0, 0, -1))
                    for s_, ds in ((lo + 0.004, 1), (hi - 0.004, -1)):
                        mb.poly_n([P(-T, s_, z0), P(CASE_T, s_, z0), P(CASE_T, s_, zb), P(-T, s_, zb)], wood,
                                  "atlas_furn", N(0, ds, 0))
                    # casings: B's wall continues past the junction on a side -> jamb casing there; heads on both faces
                    ext_lo, ext_hi = s_b[0] < lo - 0.05, s_b[1] > hi + 0.05
                    c0, c1 = lo - (CASE_W if ext_lo else 0.0), hi + (CASE_W if ext_hi else 0.0)
                    for d, sg, cl, ch in ((CASE_T, 1, c0, c1), (-T - CASE_T, -1, lo, hi)):
                        mb.poly_n([P(d, cl, zb), P(d, ch, zb), P(d, ch, zb + CASE_W), P(d, cl, zb + CASE_W)], wood,
                                  "atlas_furn", N(sg, 0, 0))
                    for side, on in ((lo, ext_lo), (hi, ext_hi)):
                        if on:
                            sa, sb_ = (side - CASE_W, side) if side == lo else (side, side + CASE_W)
                            mb.poly_n([P(CASE_T, sa, z0), P(CASE_T, sb_, z0), P(CASE_T, sb_, zb + CASE_W),
                                       P(CASE_T, sa, zb + CASE_W)], wood, "atlas_furn", N(1, 0, 0))


def pilasters(lay, level, mb):
    """0.4 x 0.4 frame columns on the corridor side of both corridor walls."""
    L = LEVELS[level]
    corr = [r for r in lay.rooms.values() if r.level == level and r.kind.startswith(("corridor", "service_corridor"))]
    for r in corr:
        mat = r.wall
        for (x0, x1, y0, y1) in r.rects:
            for x in COLUMNS_X:
                if not (x0 + 0.25 < x < x1 - 0.25):
                    continue
                for (ya, yb, face_y) in ((CORR_Y0, CORR_Y0 + COLUMN - CORR_T, +1), (CORR_Y1 - COLUMN + CORR_T, CORR_Y1, -1)):
                    xa, xb = x - COLUMN / 2, x + COLUMN / 2
                    z0, z1 = L, L + CEIL_H
                    yf = yb if face_y > 0 else ya
                    ywall = ya if face_y > 0 else yb
                    # corridor-facing face
                    if face_y > 0:
                        pts = [(xb, yf, z0), (xa, yf, z0), (xa, yf, z1), (xb, yf, z1)]
                        uv = [(-p[0] / 3, (p[2] - L) / 3) for p in pts]
                    else:
                        pts = [(xa, yf, z0), (xb, yf, z0), (xb, yf, z1), (xa, yf, z1)]
                        uv = [(p[0] / 3, (p[2] - L) / 3) for p in pts]
                    mb.poly(pts, uv, mat)
                    # side faces
                    for xs, nx in ((xa, -1), (xb, +1)):
                        if nx < 0:
                            pts = [(xs, yb, z0), (xs, ya, z0), (xs, ya, z1), (xs, yb, z1)]
                        else:
                            pts = [(xs, ya, z0), (xs, yb, z0), (xs, yb, z1), (xs, ya, z1)]
                        uv = [((p[1] * (-nx)) / 3, (p[2] - L) / 3) for p in pts]
                        mb.poly(pts, uv, mat)
                    # small ceiling/floor patches are hidden (column meets slab)
