"""Furnishing recipes per room kind: a clean, fully working 1970s-80s Soviet sanatorium for elderly
guests. Rooms are laid out deliberately (one plan per room type, mirrored where the room is), every
item is collision-checked by furnish_core, wall items never overlap, things on desks only appear on
desks that exist, and every table gets its full chair set (or the whole set is skipped)."""
import math
import random
from .params import *
from .furnish_core import Ctx, place_radiators_and_curtains, mod_info
from .stairs_layout import stair_frame, CELL_U, CELL_V
from . import furniture as F

R = {}


def recipe(*kinds):
    def deco(fn):
        for k in kinds:
            R[k] = fn
        return fn
    return deco


def first(tries):
    for t in tries:
        ob = t()
        if ob is not None:
            return ob
    return None


class Mir:
    """Mirror the room's local u axis (so one layout serves rooms on both sides of the corridor)."""

    def __init__(self, c, flip):
        self.c, self.f = c, flip
        self.W, self.D = c.W, c.D

    def u(self, u):
        return self.c.W - u if self.f else u

    def fc(self, facing):
        if not self.f or facing is None:
            return facing
        return {"+u": "-u", "-u": "+u"}.get(facing, facing)

    def at(self, key, u, v, facing="+v", **kw):
        return self.c.at(key, self.u(u), v, self.fc(facing), **kw)

    def mount(self, u, v, facing, key, z, **kw):
        return self.c.mount(self.u(u), v, self.fc(facing), key, z, **kw)

    def hang(self, side, t, key, z):
        if side in ("L", "R"):
            return self.c.hang({"L": "R", "R": "L"}[side] if self.f else side, t, key, z)
        return self.c.hang(side, self.u(t), key, z)

    def on_top(self, base, key, du=0.0, dv=0.0, facing=None):
        return self.c.on_top(base, key, -du if self.f else du, dv, self.fc(facing))

    def set(self, table, u, v, facing, chair, seats, **kw):
        s = [(-du if self.f else du, dv, self.fc(f)) for (du, dv, f) in seats]
        return table_set(self.c, table, self.u(u), v, self.fc(facing), chair, s, **kw)


# ------------------------------------------------------------------ seat sets
def rect4(tw, td, off=0.2):
    """4 chairs at a rectangular table (tw along u, td along v): two per long side."""
    return [(-tw / 4, -(td / 2 + off), "+v"), (tw / 4, -(td / 2 + off), "+v"),
            (-tw / 4, td / 2 + off, "-v"), (tw / 4, td / 2 + off, "-v")]


def sq4(s, off=0.2):
    return [(0, -(s / 2 + off), "+v"), (0, s / 2 + off, "-v"), (-(s / 2 + off), 0, "+u"), (s / 2 + off, 0, "-u")]


def pair_u(s, off=0.2):
    return [(-(s / 2 + off), 0, "+u"), (s / 2 + off, 0, "-u")]


def pair_v(s, off=0.2):
    return [(0, -(s / 2 + off), "+v"), (0, s / 2 + off, "-v")]


def rot_seats(seats):
    """Seat list for a table placed facing +u instead of +v (swap axes)."""
    sw = {"+v": "+u", "-v": "-u", "+u": "+v", "-u": "-v"}
    return [(dv, du, sw[f]) for (du, dv, f) in seats]


def table_set(c, table, u, v, facing, chair, seats, top=None):
    """Table plus every chair of the set, or nothing at all."""
    c.begin()
    t = c.at(table, u, v, facing)
    if t is None:
        c.rollback()
        return None
    trect = c.busy.pop()                 # chairs may tuck under their own table
    for (du, dv, f) in seats:
        if c.at(chair, u + du, v + dv, f) is None:
            c.rollback()
            return None
    c.busy.append(trect)
    c.commit()
    for k in (top or ()):
        c.on_top(t, k)
    return t


def lamp_and(c, base, extra=(), du=0.0):
    c.on_top(base, "table_lamp", du)
    for k in extra:
        c.on_top(base, k)


def narrow_rect(c):
    """The corridor-side (narrower) rectangle of an L-shaped suite and the flip flag."""
    rs = sorted(c.rects_local, key=lambda q: q[2])
    if len(rs) < 2:
        return None, False
    n = rs[1]
    return n, n[0] > 0.01


def far_window(c, m, default=None):
    """Centre (mirrored frame) of the window-wall window farthest from u=0."""
    cs = [m.u((t0 + t1) / 2) for (s, t0, t1) in c.windows_local if s == "W"]
    return max(cs) if cs else (default if default is not None else c.W - 1.5)


def plants(c, spots, key="plant_stand"):
    for (u, v) in spots:
        c.at(key, u, v, "+v")


# =============================================================== guest rooms
@recipe("suite_double")
def suite_double(c):
    """Two made beds with their heads on the side wall, bedside tables with lamps, call buttons,
    radio, wardrobe at the entrance, a sitting corner by the window, TV, writing desk, rug, plant."""
    n, flip = narrow_rect(c)
    m = Mir(c, flip)
    W = c.W
    Wn = n[1] - n[0]                       # width of the corridor-side part (bath block beyond)
    yb = n[2]                              # v where the bath block starts
    spread = "bed_a" if c.rng.random() < 0.5 else "bed_b"
    bA = m.at("bed_strip" if c.rng.random() < 0.2 else spread, 1.02, 1.30, "+u")
    bB = m.at("bed_strip" if c.rng.random() < 0.2 else spread, 1.02, 3.14, "+u")
    s1 = m.at("bedside", 0.24, 2.22, "+u")
    s2 = m.at("bedside", 0.24, 3.88, "+u")
    m.on_top(s1, "table_lamp")
    m.on_top(s2, "table_lamp")
    m.on_top(s1, "carafe", 0.0, -0.1)
    wr = m.at("wardrobe", 0.3, 5.35, "+u")
    m.on_top(wr, "suitcase_a" if c.rng.random() < 0.5 else "suitcase_b", 0.0, 0.0, "+u")
    # call buttons at both bed heads, radio point at reach height, pictures above the beds
    m.mount(0.0, 1.92, "+u", "call_button", 0.78)
    m.mount(0.0, 2.52, "+u", "call_button", 0.78)
    m.mount(0.0, 2.22, "+u", "radio", 1.32)
    m.mount(0.0, 1.30, "+u", c.rng.choice(["painting_1", "painting_2"]), 1.25)
    m.mount(0.0, 3.14, "+u", c.rng.choice(["painting_2", "painting_1"]), 1.25)
    m.mount(0.0, 4.40, "+u", "coat_hooks", 1.6)
    # sitting group under the far window, TV and desk on the side wall
    wc2 = far_window(c, m)
    tb = m.at("table_small", wc2, 0.58, "+v")
    m.on_top(tb, "vase")
    m.at("armchair_beige" if spread == "bed_a" else "armchair_red", wc2 - 0.76, 0.76, "+u")
    m.at("armchair_beige" if spread == "bed_a" else "armchair_red", wc2 + 0.76, 0.76, "-u")
    m.at("floor_lamp", wc2 - 1.42, 0.42, "+v")
    tvc = m.at("tv_cabinet", W - 0.24, 2.05, "-u")
    m.on_top(tvc, "tv_small", facing="-u")
    dk = m.at("desk_small", W - 0.3, 3.08, "-u")
    m.on_top(dk, "table_lamp", 0.0, 0.3)
    m.at("chair", W - 0.84, 3.08, "+u")
    m.mount(Wn + 0.57, yb, "-v", "schedule", 1.42)
    m.at("rug_big", 3.25, 2.2, "+v", check=False)
    m.at("plant_stand", 0.25, 0.40, "+v")
    c.switch()


@recipe("suite_single")
def suite_single(c):
    """Single room: bed along the side wall with its head on the bathroom wall, bedside, desk under the
    window, armchair, wardrobe, TV, call button, radio, rug, coat hooks in the entrance passage."""
    n, flip = narrow_rect(c)       # passage (unflipped: low u), bathroom beyond it at high u
    m = Mir(c, not flip)
    W = c.W
    yb = n[2]
    # unflipped frame here: passage on the high-u side (mirror of the double room logic)
    pw = n[1] - n[0]
    bed = m.at(c.rng.choice(["bed_a", "bed_b", "bed_strip"]), 0.49, yb - 1.02, "-v")
    sd = m.at("bedside", 1.2, yb - 0.23, "-v")
    m.on_top(sd, "table_lamp")
    m.mount(1.05, yb, "-v", "call_button", 0.8)
    m.mount(1.3, yb, "-v", "radio", 1.4)
    m.mount(0.0, yb - 1.0, "+u", c.rng.choice(["painting_1", "painting_2"]), 1.25)
    wc = far_window(c, m, W / 2)
    dk = m.at("desk_small", wc + 0.42, 0.455, "+v")
    m.on_top(dk, "table_lamp", -0.3)
    m.at("chair", wc + 0.42, 1.0, "-v")
    m.at("armchair_beige", 0.45, 0.78, "+u")
    m.at("wardrobe", W - 0.3, yb - 1.13, "-u")
    tvc = m.at("tv_cabinet", W - 0.24, 1.3, "-u")
    m.on_top(tvc, "tv_small", facing="-u")
    m.at("rug_small", 1.5, yb - 1.0, "+u", check=False)
    m.mount(W, yb + 0.95, "-u", "coat_hooks", 1.6)
    c.switch()


@recipe("suite_assisted")
def suite_assisted(c):
    """Room for guests with reduced mobility: two care beds with a 1.1 m wheelchair passage between,
    call buttons, no rugs, table with two chairs, TV, wide wardrobe, parked wheelchair."""
    n, flip = narrow_rect(c)
    m = Mir(c, flip)
    W = c.W
    b1 = m.at("bed_hosp", 1.05, 1.0, "+u")
    b2 = m.at("bed_hosp", 1.05, 3.1, "+u")
    s1 = m.at("bedside", 0.24, 0.27, "+u")
    s2 = m.at("bedside", 0.24, 3.87, "+u")
    m.on_top(s1, "table_lamp")
    m.on_top(s2, "table_lamp")
    m.mount(0.0, 1.62, "+u", "call_button", 0.85)
    m.mount(0.0, 2.48, "+u", "call_button", 0.85)
    m.mount(0.0, 2.05, "+u", "radio", 1.3)
    m.mount(0.0, 1.0, "+u", "painting_1", 1.3)
    m.mount(0.0, 3.1, "+u", "painting_2", 1.3)
    m.at("wardrobe_wide", 0.3, 5.3, "+u")
    wc2 = far_window(c, m)
    m.set("table_small", wc2, 0.62, "+v", "chair", pair_u(0.6), top=("vase",))
    tvc = m.at("tv_cabinet", W - 0.24, 1.9, "-u")
    m.on_top(tvc, "tv_small", facing="-u")
    m.at("wheelchair", W - 0.42, 2.85, "-u")
    m.at("armchair_beige", 3.0, 0.62, "+v")
    m.mount(W, 1.0, "-u", "schedule", 1.3)
    c.switch()


def bath_fixtures(c, access=False):
    """En-suite bathroom: toilet with grab bar, washbasin with mirror and a bar beside it, shower
    corner with a curtain (seat and bars in the accessible version), towel rail, bath mat."""
    doors = [d for d in c.doors_local if d[3] not in ("window", "port", "counter")]
    side = doors[0][0] if doors else "L"
    m = Mir(c, side == "R")
    W, D = c.W, c.D
    tl = first([lambda: m.at("toilet", W - 0.27, 0.52, "-u"), lambda: m.at("toilet", W - 0.45, 0.27, "+v")])
    if access:
        m.mount(W, 1.0, "-u", "grab_fold", 0.75) or m.mount(W, 1.05, "-u", "grab_bar_l", 0.7)
        m.mount(W - 0.32, 0.0, "+v", "grab_bar_l", 0.7)
        m.mount(W, 1.45, "-u", "call_button", 0.85)
    else:
        m.mount(W, 1.02, "-u", "grab_bar_l", 0.7)
    sk = first([lambda: m.at("sink", 0.42, 0.22, "+v"), lambda: m.at("sink", W / 2 - 0.1, 0.22, "+v")])
    if sk is not None:
        m.mount(0.79, 0.0, "+v", "grab_bar_v", 0.8)
    else:                                   # door at the window end: washbasin on the door wall further in
        sk = first([lambda: m.at("sink", 0.2, 1.62, "+u"), lambda: m.at("sink", 0.2, 1.45, "+u")])
        if sk is not None:
            m.mount(0.0, 1.62 + 0.4, "+u", "grab_bar_v", 0.8)
    s = "shower_tray" if access else ("shower" if W > 1.5 else "shower_s")
    half = F.MODS[s][1] / 2
    sh = first([lambda: m.at(s, W - half - 0.01, D - half - 0.004, "-v"),
                lambda: m.at(s, half + 0.01, D - half - 0.004, "-v")])
    if sh is not None and access:
        m.mount(W, D - 0.47, "-u", "shower_seat", 0.0, check=False)
        m.mount(W, D - 1.0, "-u", "grab_bar_v", 0.8, check=False)
    first([lambda: m.mount(0.0, D - 0.4, "+u", "towel_rail", 1.15),
           lambda: m.mount(0.45, D, "-v", "towel_rail", 1.15),
           lambda: m.mount(0.0, 0.45, "+u", "towel_rail", 1.15)])
    if sh is not None:
        m.at("bath_mat", W - half - 0.02 if access else W - half, D - 2 * half - 0.3, "+v", check=False)
    c.switch()


@recipe("suite_bath")
def suite_bath(c):
    bath_fixtures(c, access=False)


@recipe("suite_bath_access")
def suite_bath_access(c):
    bath_fixtures(c, access=True)


# ================================================================== circulation
def wall_segments(c, side, min_len, avoid=()):
    """Free intervals along a long wall (no door/pilaster/radiator/item within 0.5 m of the wall)."""
    span = c.W if side in ("W", "B") else c.D
    vc = 0.0 if side in ("W", "L") else (c.D if side == "B" else c.W)
    bl = []
    for r in c.busy:
        lo, hi = (r[0], r[1]) if side in ("W", "B") else (r[2], r[3])
        near = (r[2], r[3]) if side in ("W", "B") else (r[0], r[1])
        if near[0] - 0.5 < vc < near[1] + 0.5 or min(abs(near[0] - vc), abs(near[1] - vc)) < 0.5:
            bl.append((lo, hi))
    bl += list(avoid)
    bl.sort()
    cur, out = 0.25, []
    for a, b in bl:
        if a - cur >= min_len:
            out.append((cur, a))
        cur = max(cur, b)
    if span - 0.25 - cur >= min_len:
        out.append((cur, span - 0.25))
    return out


def corridor_seating(c, sides=("W", "B"), kinds=("sofa", "chairs", "bench"), every=0, painting=True):
    """Soft seating in the free wall bays of a corridor, never opposite each other."""
    taken = {"W": [], "B": []}
    k = 0
    sofas = ["sofa_beige", "sofa_brown", "sofa_red"]
    arms = ["armchair_red", "armchair_beige"]
    for side in sides:
        other = "B" if side == "W" else "W"
        facing = "+v" if side == "W" else "-v"
        v0 = 0.0 if side == "W" else c.D
        sgn = 1 if side == "W" else -1
        for i, (a, b) in enumerate(wall_segments(c, side, 2.3, taken[side])):
            if i % (every + 1):
                continue
            mid = (a + b) / 2
            if any(min(mid + 1.2, y) - max(mid - 1.2, x) > 0 for (x, y) in taken[other]):
                continue
            kind = kinds[k % len(kinds)]
            ok = False
            if kind == "sofa":
                ok = c.at(sofas[k % 3], mid, v0 + sgn * 0.42, facing) is not None
                span = (mid - 0.95, mid + 0.95)
            elif kind == "chairs":
                c.begin()
                t = c.at("table_small", mid, v0 + sgn * 0.34, facing)
                a1 = c.at(arms[k % 2], mid - 0.7, v0 + sgn * 0.4, facing)
                a2 = c.at(arms[k % 2], mid + 0.7, v0 + sgn * 0.4, facing)
                if t is None or a1 is None or a2 is None:
                    c.rollback()
                else:
                    c.commit()
                    c.on_top(t, "vase")
                    ok = True
                span = (mid - 1.1, mid + 1.1)
            else:
                ok = c.at("bench", mid, v0 + sgn * 0.22, facing) is not None
                span = (mid - 0.85, mid + 0.85)
                if ok and b - a > 2.6:
                    c.at("plant_stand", mid + 1.1, v0 + sgn * 0.22, facing)
            if ok:
                k += 1
                taken[side].append(span)
                if painting:
                    c.mount(mid, v0, facing, ["painting_1", "painting_2", "painting_3"][k % 3], 1.3)
                    if kind == "sofa":
                        for dx in (-1.25, 1.25):
                            c.mount(mid + dx, v0, facing, "sconce", 1.55)
    return taken


@recipe("corridor_patient")
def corridor_patient(c):
    """Guest-floor corridor: fire safety equipment and signs first, then soft seating in the free bays
    between the doors (with pictures and wall lamps above), plants, and continuous handrails."""
    lvl = c.room.level
    X = lambda x: x - c.O[0]
    # fire safety at the stairs and in the middle
    for x, side in ((10.2, "B"), (31.9, "B"), (64.8, "W"), (48.6, "W")):
        first([lambda: c.hang(side, X(x), "fire_ext", 0.0), lambda: c.hang(side, X(x) + 0.6, "fire_ext", 0.0),
               lambda: c.hang(side, X(x) - 0.6, "fire_ext", 0.0)])
    for x in (13.5, 46.5, 64.5):
        first([lambda: c.hang("W", X(x), "hose_cabinet", 1.0), lambda: c.hang("B", X(x), "hose_cabinet", 1.0),
               lambda: c.hang("W", X(x) + 1.0, "hose_cabinet", 1.0), lambda: c.hang("B", X(x) + 1.0, "hose_cabinet", 1.0)])
    for x in (6.0, 38.6, 68.0):
        first([lambda: c.hang("B", X(x), "evac_plan", 1.45), lambda: c.hang("W", X(x), "evac_plan", 1.45),
               lambda: c.hang("B", X(x) + 0.8, "evac_plan", 1.45), lambda: c.hang("W", X(x) + 0.8, "evac_plan", 1.45)])
    for t, k in ((10.5, "arrow_stairs"), (60.0, "arrow_stairs"), (40.5, "arrow_lift"), (20.5, "arrow_stairs")):
        first([lambda: c.hang("W", X(t), k, 2.2), lambda: c.hang("B", X(t), k, 2.2), lambda: c.hang("W", X(t) + 0.7, k, 2.2)])
    first([lambda: c.hang("B", X(39.3), "clock", 2.25), lambda: c.hang("W", X(39.3), "clock", 2.25)])
    first([lambda: c.hang("W", X(36.0), "notice_board", 1.2), lambda: c.hang("B", X(34.3), "notice_board", 1.2),
           lambda: c.hang("W", X(42.5), "notice_board", 1.2)])
    first([lambda: c.hang("W", X(44.2), "schedule", 1.42), lambda: c.hang("B", X(44.2), "schedule", 1.42)])
    first([lambda: c.hang("W", X(18.0), "wall_newspaper", 1.3), lambda: c.hang("B", X(18.0), "wall_newspaper", 1.3),
           lambda: c.hang("W", X(23.0), "wall_newspaper", 1.3)])
    for t, k in ((51.5, "poster_10"), (55.5, "poster_5"), (15.5, "poster_1"), (58.5, "poster_7")):
        first([lambda: c.hang("W", X(t), k, 1.3), lambda: c.hang("B", X(t), k, 1.3)])
    first([lambda: c.hang("W", X(8.5), "no_smoking", 1.75), lambda: c.hang("B", X(8.5), "no_smoking", 1.75)])
    if lvl == 3:
        # roof access under the stair houses: steel ladder + hatch (kept locked, signed)
        for (xh, yw) in ((33.0, "W"), (66.0, "B")):
            t = X(xh)
            if c.hang(yw, t, "ladder", 0.0):
                c.hang(yw, t + 0.75, "roof_hatch_sign", 1.8)
                vv = 0.45 if yw == "W" else c.D - 0.45
                c.at("hatch", t, vv, "+v", z=CEIL_H - 0.001, check=False)
    corridor_seating(c)
    # plants at the stair and lift lobbies
    for x in (2.6, 31.2, 35.6, 39.6, 63.6, 72.8):
        first([lambda: c.at("palm", X(x), 0.36, "+v"), lambda: c.at("palm", X(x), c.D - 0.36, "-v"),
               lambda: c.at("plant_stand", X(x), 0.24, "+v"), lambda: c.at("plant_stand", X(x), c.D - 0.24, "-v")])
    c.handrails(("W", "B"))


@recipe("corridor")
def corridor_ground(c):
    """Ground-floor corridor between reception and the medical/spa wings: waiting seats at the doctors'
    rooms, sofas at the spa wing, signs, fire equipment, handrails."""
    X = lambda x: x - c.O[0]
    for x, side in ((16.2, "B"), (31.8, "W"), (48.6, "W"), (64.8, "W")):
        first([lambda: c.hang(side, X(x), "fire_ext", 0.0), lambda: c.hang(side, X(x) + 0.6, "fire_ext", 0.0),
               lambda: c.hang(side, X(x) - 0.6, "fire_ext", 0.0)])
    for x in (46.5, 64.5):
        first([lambda: c.hang("W", X(x), "hose_cabinet", 1.0), lambda: c.hang("B", X(x), "hose_cabinet", 1.0),
               lambda: c.hang("W", X(x) + 1.0, "hose_cabinet", 1.0), lambda: c.hang("B", X(x) + 1.0, "hose_cabinet", 1.0)])
    for x in (29.0, 68.0):
        first([lambda: c.hang("B", X(x), "evac_plan", 1.45), lambda: c.hang("W", X(x), "evac_plan", 1.45),
               lambda: c.hang("W", X(x) + 0.8, "evac_plan", 1.45)])
    for t, k in ((20.0, "arrow_dining"), (31.5, "arrow_reception"), (44.0, "arrow_medical"), (49.5, "arrow_spa"),
                 (41.0, "arrow_lift"), (61.0, "arrow_stairs"), (42.5, "arrow_admin")):
        first([lambda: c.hang("W", X(t), k, 2.2), lambda: c.hang("B", X(t), k, 2.2), lambda: c.hang("W", X(t) + 0.7, k, 2.2),
               lambda: c.hang("B", X(t) + 0.7, k, 2.2)])
    first([lambda: c.hang("W", X(39.5), "clock", 2.25), lambda: c.hang("B", X(39.5), "clock", 2.25)])
    first([lambda: c.hang("B", X(57.0), "schedule_proc", 1.35), lambda: c.hang("W", X(57.0), "schedule_proc", 1.35),
           lambda: c.hang("B", X(51.0), "schedule_proc", 1.35)])
    first([lambda: c.hang("W", X(54.5), "silence", 1.85), lambda: c.hang("B", X(54.5), "silence", 1.85)])
    for t, k in ((45.0, "poster_4"), (59.0, "poster_9"), (52.0, "poster_7"), (26.5, "poster_6")):
        first([lambda: c.hang("W", X(t), k, 1.3), lambda: c.hang("B", X(t), k, 1.3)])
    # waiting seats outside the doctors' rooms (rear side) and soft seating at the spa (front side)
    for (a, b) in wall_segments(c, "W", 1.15):
        if X(36.0) < a and b < X(70.0):
            first([lambda: c.at("seat_row", (a + b) / 2, 0.24, "+v"), lambda: c.at("seat_row2", (a + b) / 2, 0.24, "+v")])
    corridor_seating(c, sides=("B",), kinds=("sofa", "chairs"))
    for x in (16.0, 30.0, 35.6, 39.6, 73.4):
        first([lambda: c.at("palm", X(x), 0.36, "+v"), lambda: c.at("palm", X(x), c.D - 0.36, "-v"),
               lambda: c.at("plant_stand", X(x), 0.24, "+v"), lambda: c.at("plant_stand", X(x), c.D - 0.24, "-v")])
    c.handrails(("W", "B"))


@recipe("service_corridor")
def service_corridor(c):
    first([lambda: c.hang("W", 2.5, "menu_board", 1.3), lambda: c.hang("B", 2.5, "menu_board", 1.3)])
    first([lambda: c.hang("W", 11.0, "fire_ext", 0.0), lambda: c.hang("B", 11.0, "fire_ext", 0.0)])
    first([lambda: c.hang("B", 6.0, "evac_plan", 1.45), lambda: c.hang("W", 6.0, "evac_plan", 1.45)])
    first([lambda: c.hang("W", 13.5, "poster_2", 1.3), lambda: c.hang("B", 13.5, "poster_2", 1.3)])


@recipe("hall")
def hall(c):
    """Reception hall and waiting area: a soft seating group facing the registration windows, plants,
    a carpet runner from the entrance doors, welcome banner, notice board, signs."""
    m = c
    m.at("sofa_beige", 2.25, 0.6, "+v")
    tb = m.at("table_coffee", 2.25, 1.55, "+v")
    m.on_top(tb, "vase")
    m.at("armchair_red", 1.6, 2.45, "-v")
    m.at("armchair_red", 2.9, 2.45, "-v")
    m.at("palm", 3.9, 0.45, "+v")
    m.at("plant_stand", 3.9, 6.6, "+v")
    m.at("plant_stand", 3.9, 10.7, "+v")
    m.at("runner", 2.6, 6.7, "+u", check=False)
    m.mount(2.4, 13.0, "-v", "welcome_banner", 2.42)
    m.mount(3.85, 13.0, "-v", "notice_board", 1.2)
    m.mount(0.55, 13.0, "-v", "evac_plan", 1.45)
    first([lambda: m.hang("L", 4.71, "poster_10", 1.75), lambda: m.hang("L", 6.65, "poster_10", 1.75)])
    first([lambda: m.hang("L", 6.65, "schedule", 1.75), lambda: m.hang("L", 4.71, "schedule", 1.75)])
    first([lambda: m.hang("L", 9.1, "clock", 2.4), lambda: m.hang("L", 5.7, "clock", 2.4)])
    # passage to the corridor (F9 area of the hall)
    m.at("bench", 7.67, 16.0, "-u")
    m.at("plant_stand", 7.67, 17.2, "-u")
    m.mount(5.01, 15.0, "+u", "arrow_medical", 2.2)
    m.mount(5.01, 16.0, "+u", "arrow_spa", 2.2)
    m.mount(5.01, 17.0, "+u", "arrow_dining", 2.2)
    m.mount(5.01, 16.3, "+u", "poster_7", 1.3)
    m.hang("R", 18.2, "arrow_lift", 2.2)


@recipe("vestibule")
def vestibule(c):
    c.at("runner", c.W / 2, 1.22, "+u", check=False)
    for t in (0.6, 10.0):
        c.at("plant_stand", t, 0.3, "+v")


@recipe("foyer")
def foyer(c):
    """Club hall foyer on floor 2 (open to the corridor): benches, plants, programme posters."""
    c.wall("L", 3.0, "bench")
    c.wall("R", 3.0, "bench")
    c.at("plant_stand", 0.3, 4.4, "+u")
    c.at("plant_stand", c.W - 0.3, 4.4, "-u")
    c.hang("L", 3.0, "poster_5", 1.3)
    c.hang("R", 3.0, "poster_10", 1.3)
    c.hang("L", 5.3, "schedule", 1.42)


# ================================================================ entrance block
@recipe("luggage")
def luggage(c):
    """Left-luggage room: racks of numbered suitcases and bags, a counter-side desk for the attendant."""
    c.wall("R", 0.85, "luggage_rack")
    c.wall("R", 2.07, "luggage_rack")
    c.wall("L", 1.0, "luggage_rack")
    c.at("suitcase_a", 1.25, 1.75, "+u")
    c.at("suitcase_b", 1.55, 1.75, "+u")
    c.at("travel_bag", 1.4, 2.25, "+v")
    c.switch()


@recipe("coatroom")
def coatroom(c):
    for v in (1.0, 2.1):
        for u in (0.7, 1.6, 2.5):
            c.at("coat_stand", u, v, "+v")
    c.switch()


def office_desk(c, u, v, facing, desk="desk_office", chair="chair_tube", visitor=True, phone=True, lamp=True,
                typewriter=False):
    """Desk with its chair (and a visitor chair) as one set; items on top only if the desk exists."""
    off = {"+v": (0, -1), "-v": (0, 1), "+u": (-1, 0), "-u": (1, 0)}[facing]   # sitter side
    seats = [(off[0] * 0.62, off[1] * 0.62, {"+v": "+v", "-v": "-v", "+u": "+u", "-u": "-u"}[facing])]
    t = table_set(c, desk, u, v, facing, chair, seats)
    if t is None:
        return None
    if visitor:
        first([lambda: c.at("chair", u - off[0] * 0.75, v - off[1] * 0.75, {"+v": "-v", "-v": "+v", "+u": "-u", "-u": "+u"}[facing]),
               lambda: c.at("chair", u + off[1] * 0.95, v + off[0] * 0.95, facing)])
    w = F.MODS[desk][1]
    sx, sy = (off[1], -off[0])            # along the desk
    if phone:
        c.on_top(t, "telephone", sx * (w / 2 - 0.2), sy * (w / 2 - 0.2))
    if lamp:
        c.on_top(t, "table_lamp", -sx * (w / 2 - 0.18), -sy * (w / 2 - 0.18))
    c.on_top(t, "paper_stack", -sx * 0.15, -sy * 0.15)
    if typewriter:
        c.on_top(t, "typewriter", sx * 0.15, sy * 0.15)
    return t


def counter_desks(c, typewriter=False, lamp=True):
    """Clerks' desks right behind the service windows to the hall (B wall), facing the visitors."""
    out = []
    for (side, t0, t1, kind, r) in c.doors_local:
        if side == "B" and kind == "window":
            out.append(office_desk(c, (t0 + t1) / 2, c.D - 0.5 - 0.39, "+v", visitor=False, lamp=lamp,
                                   typewriter=typewriter and not out))
    return out


@recipe("registration")
def registration(c):
    """Registration: two clerks at desks behind the hall windows, card index, binders, safe."""
    counter_desks(c, typewriter=True)
    for t in (0.6, 1.2, 1.8):
        c.wall("L", t, "filing")
    c.wall("R", 1.0, "binders")
    c.wall("R", 2.1, "binders")
    c.wall("W", 3.19, "safe")
    c.decorate(["calendar", "schedule"], 1.45, ("L", "R"))
    c.switch()


@recipe("info")
def info(c):
    counter_desks(c)
    c.wall("R", 1.0, "binders")
    c.decorate(["calendar", "evac_plan"], 1.45, ("R", "W"))
    c.switch()


@recipe("guard")
def guard(c):
    counter_desks(c, lamp=False)
    c.wall("R", 0.7, "locker")
    c.wall("R", 1.3, "locker")
    c.hang("R", 2.2, "fuse_box", 1.3)
    c.at("chair", 2.3, 1.2, "-u")
    c.decorate(["clock", "calendar", "evac_plan"], 1.45, ("W", "R", "L"))
    c.switch()


# ======================================================================= catering
@recipe("kitchen")
def kitchen(c):
    for t in (1.0, 2.1, 3.2):
        c.wall("L", t, "stove")
    c.wall("R", 1.0, "kettle")
    c.wall("R", 2.0, "kettle")
    c.at("prep_table", c.W / 2 + 0.2, 4.2, "+u")
    c.wall("R", 3.4, "prep_table")
    c.wall("L", 4.8, "kitchen_sink")
    c.wall("R", 5.2, "dish_rack")
    # exhaust canopy over the stoves, its duct up into the ceiling (a duct hanging across the room ended in mid-air)
    c.wall("L", 2.1, "kitchen_hood", z=2.0, check=False)
    c.decorate(["menu_board", "electro_warning"], 1.5, ("B",))


@recipe("food_prep")
def food_prep(c):
    c.wall("R", 1.0, "prep_table")
    c.wall("R", 2.6, "prep_table")
    c.wall("L", 1.5, "kitchen_sink")
    c.wall("L", 3.2, "fridge_ind")
    c.at("bin", 1.4, 4.6, "+v")
    c.decorate(["poster_2"], 1.4, ("L", "R"))


@recipe("veg_prep")
def veg_prep(c):
    c.wall("L", 1.0, "kitchen_sink")
    c.at("peeler", c.W - 0.5, 1.0, "-u")
    c.wall("R", 2.3, "prep_table")
    c.at("crates", 0.5, 2.6, "+u")


@recipe("distribution")
def distribution(c):
    c.wall("R", 3.2, "serving_line")
    c.wall("L", 4.6, "dish_rack")
    c.decorate(["menu_board"], 1.5, ("B",))


@recipe("dining")
def dining(c):
    """Dining hall: tables with white cloths and four chairs each (full sets only), flowers on every
    table, plants, menu and posters."""
    cols = (1.55, 3.95, 6.35)
    rows = (1.2, 3.05, 4.9)
    for u in cols:
        for v in rows:
            table_set(c, "table_cloth", u, v, "+v", "chair", rect4(1.2, 0.8), top=("vase",))
    for (u, v) in ((7.75, 0.45), (7.9, 4.75), (0.3, 1.3)):
        c.at("plant_stand", u, v, "+v")
    c.at("palm", 8.0, 5.6, "+v")
    c.decorate(["menu_board", "poster_6", "painting_2", "painting_1", "clock"], 1.45, ("B", "L", "R"))


@recipe("dishwash")
def dishwash(c):
    c.wall("R", 1.3, "dishwasher")
    c.wall("L", 1.5, "kitchen_sink")
    c.wall("L", 3.0, "kitchen_sink")
    c.wall("R", 3.2, "dish_rack")
    c.at("bin", 1.4, 5.0, "+v")


@recipe("dry_store")
def dry_store(c):
    for t in (0.85, 2.1):
        c.wall("L", t, "goods_rack")
    c.wall("R", 1.3, "goods_rack")
    c.at("sack", 1.45, 2.4, "+v")


@recipe("fridge")
def fridge(c):
    c.wall("L", 0.8, "fridge_ind")
    c.wall("R", 0.9, "goods_rack")
    c.at("crates", 1.5, 1.9, "+v")


@recipe("kitchen_changing", "staff_changing", "med_changing")
def changing(c):
    for t in (0.5, 1.05, 1.6, 2.15):
        c.wall("L", t, "locker")
    c.wall("R", 1.2, "bench")
    c.hang("R", 2.6, "mirror", 1.2)
    c.decorate(["schedule"], 1.45, ("R", "W"))
    c.switch()


@recipe("staff_wc")
def staff_wc(c):
    """Staff restroom: toilet with a grab bar, washbasin with mirror, towel rail."""
    c.wall("W", c.W / 2, "toilet")
    first([lambda: c.wall("L", 1.0, "sink"), lambda: c.wall("R", 1.0, "sink")])
    first([lambda: c.hang("R", 0.6, "grab_bar_l", 0.7), lambda: c.hang("L", 0.6, "grab_bar_l", 0.7)])
    first([lambda: c.hang("R", 1.45, "towel_rail", 1.15), lambda: c.hang("L", 1.6, "towel_rail", 1.15)])
    c.switch()


@recipe("staff_dining")
def staff_dining(c):
    for v in (1.4, 3.4):
        table_set(c, "table_cloth", c.W / 2, v, "+v", "chair", rect4(1.2, 0.8), top=("vase",))
    c.wall("L", 5.0, "fridge")
    c.decorate(["calendar", "poster_6", "painting_1"], 1.4, ("R", "L"))
    c.switch()


# ===================================================================== technical
@recipe("plumbing")
def plumbing(c):
    c.at("pump", 0.9, 1.2, "+u")
    c.at("boiler", c.W - 0.6, 1.0, "-u")
    c.hang("L", 2.8, "elec_panel_wall", 1.2)


@recipe("electrical")
def electrical(c):
    c.wall("L", 0.8, "elec_cabinet")
    c.wall("L", 1.7, "elec_cabinet")
    c.hang("R", 1.3, "electro_warning", 1.6)
    c.hang("R", 0.6, "fuse_box", 1.2)


@recipe("ventilation")
def ventilation(c):
    c.at("pump", 1.0, 1.5, "+u")
    c.at("duct", c.W / 2, 3.0, "+u", z=CEIL_H - 0.5, check=False)
    c.wall("R", 3.5, "elec_cabinet")
    c.hang("L", 4.5, "vent_grille", 2.4)


@recipe("workshop")
def workshop(c):
    c.wall("L", 1.3, "workbench")
    c.wall("R", 1.0, "tool_rack")
    c.wall("R", 2.3, "goods_rack")
    c.at("chair", 1.3, 1.6, "-u")
    c.decorate(["calendar", "electro_warning"], 1.5, ("L", "R"))


@recipe("storage", "utility", "cleaning_store", "hall_store")
def storage(c):
    c.wall("L", min(0.8, c.D / 2), "goods_rack")
    if c.room.kind in ("utility", "cleaning_store"):
        first([lambda: c.at("cleaning_cart", c.W / 2, c.D * 0.3, "+u"), lambda: c.at("cleaning_cart", c.W - 0.3, 0.75, "-u")])
        first([lambda: c.at("bucket", c.W - 0.3, c.D * 0.6, "+v"), lambda: c.at("bucket", c.W - 0.3, 1.3, "+v")])
    if c.room.kind == "hall_store":
        for t in (1.8, 2.6):
            c.wall("R", t, "seat_row")
        c.at("chair", 1.2, 2.3, "+v")
        c.at("chair", 1.6, 2.3, "+v")


@recipe("waste")
def waste(c):
    for v in (0.5, 1.2):
        c.at("bin", 0.4, v, "+v")


@recipe("clean_linen")
def clean_linen(c):
    c.wall("L", 0.8, "linen_rack")
    c.wall("L", 2.2, "linen_rack") if c.D > 3 else None
    c.wall("R", 1.0, "linen_rack")
    first([lambda: c.at("laundry_cart", c.W / 2, c.D - 1.1, "+u"), lambda: c.at("laundry_cart", 1.5, 1.4, "+v")])


@recipe("dirty_linen")
def dirty_linen(c):
    c.at("laundry_cart", c.W / 2, 0.9, "+v")
    c.at("bin", c.W / 2 - 0.2, 0.35, "+v") if c.W > 1.4 else None


@recipe("janitor")
def janitor(c):
    c.wall("L", 0.8, "locker")
    c.wall("L", 1.35, "locker")
    table_set(c, "table_small", c.W - 0.55, 0.85, "+v", "chair", [(-0.5, 0, "+u")])
    c.at("cleaning_cart", 1.2, 2.7, "+u")
    c.wall("R", 2.7, "kitchen_sink")
    c.switch()


@recipe("machine_room")
def machine_room(c):
    c.hang("L", 2.5, "electro_warning", 1.6)
    c.hang("R", 2.6, "keep_out", 1.7)


# ===================================================================== offices
@recipe("director")
def director(c):
    """Chief physician: wide desk facing the door with an armchair, two visitor chairs, a small
    meeting table, bookcases, safe, rug, plant."""
    du = c.W / 2
    c.at("rug_big", du, 2.9, "+u", check=False)
    t = table_set(c, "desk_wide", du, 1.35, "+v", "armchair", [(0, -0.72, "+v")])
    if t:
        c.on_top(t, "telephone", 0.55, 0.05)
        c.on_top(t, "table_lamp", -0.6, 0.1)
        c.on_top(t, "paper_stack", -0.2, 0.05)
        c.on_top(t, "papers_desk", 0.15, 0.05)
    c.at("chair", du - 0.38, 2.12, "-v")
    c.at("chair", du + 0.38, 2.12, "-v")
    c.wall("L", 3.3, "bookcase")
    c.wall("L", 4.25, "bookcase")
    c.wall("R", 3.4, "safe")
    c.at("coat_stand", c.W - 0.35, 4.6, "-u")
    c.at("plant_stand", 0.3, 0.45, "+v")
    c.decorate(["painting_3", "calendar", "clock"], 1.45, ("L", "R", "B"), spots=(0.3, 0.5, 0.7, 0.2))
    c.switch()


@recipe("admin_office")
def admin_office(c):
    """Administration and accounts: two desks (one with a typewriter), cabinets, safe."""
    office_desk(c, c.W / 2, 1.35, "-v", typewriter=True, visitor=False)
    office_desk(c, c.W / 2, 3.5, "+v", visitor=False)
    c.wall("L", 4.8, "filing")
    c.wall("R", 4.9, "safe")
    c.at("plant_stand", 0.3, 0.45, "+v")
    c.decorate(["calendar", "schedule", "frame_photo"], 1.45, ("L", "R"))
    c.switch()


@recipe("staff_office", "doctor_duty")
def staff_office(c):
    """Doctors' room / doctor on duty: desks, a sofa for the night shift, tea table, cabinet, sink."""
    office_desk(c, 1.0, 1.0, "+u", visitor=False) if c.W > 3.5 else office_desk(c, c.W / 2, 1.35, "+v", visitor=True)
    if c.W > 3.5:
        office_desk(c, 4.4, 1.05, "+v", visitor=False)
        c.at("sofa_brown", 4.4, 2.75, "-v")
        c.wall("L", 4.3, "bookcase")
    else:
        c.at("sofa_brown", c.W - 0.42, 2.7, "-u")
    first([lambda: c.wall("L", 3.0, "sink"), lambda: c.wall("L", 4.5, "sink")])
    first([lambda: c.at("coat_stand", 2.53, 4.6, "-u"), lambda: c.at("coat_stand", 2.53, 4.0, "-u")])
    c.decorate(["calendar", "schedule", "painting_1"], 1.45, ("L", "R", "B"))
    c.switch()


@recipe("archive", "records", "med_archive", "med_supplies", "med_equip", "med_storage")
def archive(c):
    key = {"med_supplies": "medbox_rack", "med_equip": "goods_rack", "med_storage": "medbox_rack"}.get(c.room.kind, "binders")
    for t in (0.6, 1.7, 2.8):
        if t + 0.5 < c.D:
            c.wall("L", t, key)
    if c.W > 2.3:
        for t in (0.8, 2.0):
            if t + 0.5 < c.D:
                c.wall("R", t, key if c.room.kind != "med_equip" else "med_cabinet")
    if c.room.kind == "med_equip":
        c.at("wheelchair", c.W / 2, 0.75, "+v")
    c.switch()


# ===================================================================== medical
def doctor_corner(c, u_desk=0.4, v_desk=1.4):
    """Doctor's desk against the left wall, doctor's chair, patient chair at the desk end."""
    t = table_set(c, "desk_office", u_desk, v_desk, "-u", "chair_tube", [(0.62, 0, "-u")])
    if t:
        c.on_top(t, "table_lamp", 0, -0.5)
        c.on_top(t, "paper_stack", 0, 0.2)
        c.on_top(t, "telephone", 0, 0.52)
    c.at("chair", 1.05, v_desk + 1.05, "-v")
    return t


def couch_with_screen(c, vs):
    """Examination couch along the right wall with a folding screen in front of it."""
    for v in vs:
        for dv in (0.0, -0.2, 0.2, -0.4):
            c.begin()
            a = c.at("exam_couch", c.W - 0.36, v, "-v")
            b = c.at("screen", c.W - 0.85, v + dv, "-u") if a else None
            if a and b:
                c.commit()
                return a
            c.rollback()
    return None


@recipe("nurse_office_floor")
def nurse_office_floor(c):
    """Floor nurse's office: desk at the side wall, files, medicine cabinet, chair for a guest."""
    doctor_corner(c)
    c.wall("R", 0.9, "filing")
    c.wall("R", 1.85, "med_cabinet")
    c.decorate(["schedule", "calendar"], 1.45, ("R", "L", "B"))
    c.switch()


@recipe("gp", "consult", "nurse_office")
def gp(c):
    doctor_corner(c)
    if c.room.kind in ("gp", "consult"):
        couch_with_screen(c, (2.2, 4.3, 1.6))
        c.at("scale", c.W - 0.3, 4.6, "-u") if c.D > 5 else None
    else:
        c.wall("R", 1.6, "filing")
        c.wall("R", 2.2, "filing") if c.D > 4 else None
    first([lambda: c.wall("R", 3.4 if c.D > 4 else 2.9, "med_cabinet"), lambda: c.wall("R", 2.6, "med_cabinet")])
    first([lambda: c.wall("L", 3.1, "sink"), lambda: c.wall("L", 2.4, "sink")])
    if c.D > 5:
        c.wall("L", 4.3, "filing")
        c.at("coat_stand", c.W - 0.35, 4.85, "-u")
    c.at("plant_stand", c.W - 0.3, 0.4, "+v") if c.room.kind != "nurse_office_floor" else None
    c.decorate(["anatomy", "poster_4", "calendar"], 1.45, ("R", "L", "B"))
    c.switch()


@recipe("exam")
def exam(c):
    """Examination room: couch with a screen, doctor's desk and chair, instrument table, scale, sink."""
    doctor_corner(c, v_desk=1.2)
    couch_with_screen(c, (2.6, 3.8))
    c.wall("R", 0.8, "instrument_table")
    c.wall("R", 4.6, "med_cabinet")
    first([lambda: c.wall("L", 4.0, "sink"), lambda: c.wall("L", 3.5, "sink")])
    c.wall("L", 4.65, "scale")
    c.decorate(["eye_chart", "calendar"], 1.25, ("L", "B"))
    c.switch()


@recipe("treatment", "treatment_small", "first_aid", "blood")
def treatment(c):
    """Treatment / first aid: couch with a screen, instrument table, cabinets, sink, chair for the nurse;
    blood sampling room: phlebotomy armchair, table, small fridge."""
    if c.room.kind == "blood":
        c.at("armchair", c.W - 0.42, 0.9, "-u")
        c.wall("R", 1.75, "instrument_table")
        c.at("chair_tube", 1.6, 0.9, "+u")
        c.wall("L", 1.6, "fridge")
        c.wall("W", 2.2, "med_cabinet")
        c.decorate(["schedule"], 1.45, ("L", "R"))
        c.switch()
        return
    couch_with_screen(c, (2.2, 3.6))
    c.wall("L", 1.2, "instrument_table")
    c.at("iv_stand", c.W - 0.3, 3.5, "-u")
    c.wall("L", 2.3, "med_cabinet")
    c.wall("R", 4.2, "med_cabinet")
    first([lambda: c.wall("L", 3.4, "sink"), lambda: c.wall("L", 4.6, "sink")])
    c.at("chair_tube", 1.1, 1.2, "-u")
    if c.room.kind == "first_aid":
        c.at("oxygen", 0.3, 0.5, "+v")
        c.at("wheelchair", 1.1, 4.4, "+v")
    c.decorate(["poster_4", "schedule"], 1.45, ("R", "B", "L"))
    c.switch()


@recipe("lab")
def lab(c):
    t1 = c.wall("L", 1.2, "table_lab")
    t2 = c.wall("L", 2.7, "table_lab")
    c.on_top(t1, "microscope", 0.0, 0.0)
    c.on_top(t2, "centrifuge")
    c.wall("R", 1.3, "lab_rack")
    c.wall("R", 2.6, "fridge")
    c.at("chair_tube", 1.05, 1.2, "-u")
    c.decorate(["schedule", "calendar"], 1.5, ("B", "R"))
    c.switch()


@recipe("med_reg")
def med_reg(c):
    """Medical registration behind the corridor counter: clerk's desk and chair, card files."""
    t = table_set(c, "desk_small", 0.3, 1.3, "+u", "chair_tube", [(0.55, 0, "-u")])
    c.on_top(t, "telephone", 0, -0.3)
    c.on_top(t, "paper_stack", 0, 0.1)
    c.on_top(t, "table_lamp", 0, 0.35)
    first([lambda: c.wall("R", 0.6, "filing"), lambda: c.wall("W", 2.4, "filing")])
    first([lambda: c.wall("R", 1.15, "filing"), lambda: c.wall("W", 1.9, "filing")])
    c.decorate(["calendar"], 1.45, ("R", "L"))
    c.switch()


# ================================================================ spa department
@recipe("massage")
def massage(c):
    """Massage room: two padded tables separated by a ceiling-hung curtain, stools, towel rack,
    masseur's desk, washbasin, coat stand, plants."""
    W = c.W
    for u in (1.4, W - 1.4):
        c.at("massage_table", u, 2.25, "+v")
        c.at("stool", u + (0.62 if u < W / 2 else -0.62), 1.55, "+v")
    c.at("curtain_rail", W / 2, 2.2, "+u", check=False)
    c.wall("L", 4.0, "linen_rack")
    t = table_set(c, "desk_small", 0.55, 5.3, "+u", "chair", [(0.55, 0.0, "-u")])
    c.on_top(t, "table_lamp", 0, -0.3)
    first([lambda: c.wall("R", 4.0, "sink"), lambda: c.wall("R", 3.6, "sink")])
    c.at("coat_stand", W - 0.35, 5.5, "-u")
    for (u, v) in ((W / 2, 0.4), (0.3, 0.45), (W - 0.3, 0.45)):
        c.at("plant_stand", u, v, "+v")
    c.decorate(["schedule_proc", "poster_10", "painting_1"], 1.45, ("L", "R", "B"))
    c.switch()


@recipe("physio")
def physio(c):
    """Physiotherapy: three curtained cubicles, each with a couch and a treatment device; nurse's
    desk with timer, sink, cabinet."""
    W = c.W
    pitch = W / 3
    for i in range(3):
        u = pitch * (i + 0.5) - 0.2
        c.at("exam_couch", u, 1.25, "+v")
        c.at("physio_device", u + 0.62, 0.62, "+v")
        c.at("stool", u + 0.6, 1.75, "+v")
        if i < 2:
            c.at("curtain_rail", pitch * (i + 1), 1.35, "+u", check=False)
    t = table_set(c, "desk_small", 0.55, 5.2, "+u", "chair_tube", [(0.55, 0.0, "-u")])
    c.on_top(t, "table_lamp", 0, -0.3)
    c.on_top(t, "paper_stack", 0, 0.2)
    first([lambda: c.wall("R", 4.6, "sink"), lambda: c.wall("R", 3.8, "sink")])
    c.wall("R", 3.4, "med_cabinet")
    c.wall("L", 3.8, "linen_rack")
    c.decorate(["schedule_proc", "anatomy", "poster_10"], 1.45, ("B", "L", "R"))
    c.switch()


@recipe("salt_room")
def salt_room(c):
    """Salt room (halochamber) and inhalatorium: salt-brick walls, reclining armchairs facing a seascape,
    inhaler stations at the side wall, soft light, plants."""
    W = c.W
    for (u, v) in ((1.1, 1.35), (2.25, 1.35), (3.4, 1.35), (1.1, 3.25), (2.25, 3.25), (3.4, 3.25)):
        c.at("recliner", u, v, "-v")
    for v in (1.0, 2.3, 3.6):      # inhalation stations
        table_set(c, "table_small", W - 0.35, v, "-u", "chair_soft", [(-0.55, 0, "+u")], top=("inhaler",))
    c.at("physio_device", W - 0.3, 4.6, "-u")
    c.at("palm", 0.35, 5.6, "+v")
    c.at("plant_stand", W / 2, 0.35, "+v")
    c.decorate(["painting_3"], 1.3, ("L",), spots=(0.45, 0.35, 0.55))
    c.decorate(["schedule_proc", "poster_10"], 1.45, ("B", "R", "L"))
    c.switch()


@recipe("hydro")
def hydro(c):
    """Hydrotherapy: two therapy baths behind curtains, a Charcot shower console with its shower area,
    a circular shower, rubber mats, grab bars, towel racks, rest couch."""
    W = c.W
    for u in (0.75, 2.15):
        c.at("hydro_bath", u, 1.3, "-v")
    c.at("curtain_rail_s", 1.45, 1.25, "+u", check=False)
    c.at("rubber_mat", 1.45, 3.05, "+u", check=False)
    c.at("shower_tray", W - 0.5, 0.75, "-u")
    c.mount(W, 1.37, "-u", "grab_bar_v", 0.8)
    c.at("shower_tray", W - 0.5, 2.1, "-u")
    c.mount(W, 2.72, "-u", "grab_bar_v", 0.8)
    c.at("charcot_console", 0.27, 4.4, "+u")          # douche console; the guest stands at the far wall
    c.at("rubber_mat", W - 0.5, 4.3, "+v", check=False)
    c.mount(W, 4.3, "-u", "grab_bar", 1.0)
    c.wall("L", 3.0, "linen_rack")
    c.at("bench", 1.5, c.D - 0.22, "-v")
    c.mount(1.5, c.D, "-v", "coat_hooks", 1.6)
    first([lambda: c.hang("R", 3.25, "towel_rail", 1.15), lambda: c.hang("L", 2.0, "towel_rail", 1.15)])
    c.decorate(["schedule_proc", "poster_7"], 1.45, ("B", "L"))
    c.switch()


@recipe("lfk")
def lfk(c):
    """Therapeutic exercise hall: wall bars, a big mirror, exercise bikes, mats, gym bench, instructor's
    stool, posters."""
    W = c.W
    for v in (1.0, 2.1, 3.2):
        c.hang("L", v, "wall_bars", 0.0)
    c.hang("R", 2.3, "mirror_big", 0.35)
    for u in (1.6, 2.7):
        c.at("ex_bike", u, 0.75, "+v")
    for v in (1.6, 2.4, 3.2):
        c.at("gym_mat", 2.9, v, "+v", check=False)
    c.at("gym_bench", 2.6, 4.25, "+v")
    c.at("stool", W - 0.6, 4.4, "-u")
    c.at("plant_stand", W - 0.3, 0.4, "+v")
    c.decorate(["poster_9", "poster_5", "clock"], 1.5, ("B", "R"))
    c.switch()


@recipe("phytobar")
def phytobar(c):
    """Phyto-bar and mineral water buvette: bar counter with a samovar and herbal tea jars behind it,
    a tiled buvette with three mineral water taps in the alcove, round cafe tables with four chairs,
    palms and flowers everywhere."""
    W, D = c.W, c.D
    bar = c.at("bar_counter", 5.1, 1.3, "+v")
    c.on_top(bar, "samovar", -1.0, 0.0)
    c.on_top(bar, "vase", 0.9, 0.0)
    c.on_top(bar, "carafe", 0.3, 0.0)
    for u in (3.75, 4.95):
        c.wall("W", u, "tea_shelf")
    c.wall("W", 6.2, "fridge")
    c.hang("W", 4.35, "menu_phyto", 2.0)
    c.hang("W", 6.9, "poster_8", 1.35)
    c.at("buvette", 6.2, D - 0.23, "-v")
    c.mount(6.2, D, "-v", "buvette_sign", 2.0)
    for (u, v) in ((2.0, 3.05), (4.3, 3.05), (6.5, 3.6), (2.0, 5.15), (4.3, 5.15)):
        table_set(c, "table_round", u, v, "+v", "chair", sq4(0.76, 0.24), top=("vase",))
    for (u, v) in ((5.2, 6.9), (7.2, 6.8)):
        c.at("palm", u, v, "+v")
    for (u, v) in ((7.2, 1.3), (7.2, 4.5), (1.2, 0.4), (2.7, 0.4)):
        c.at("plant_stand", u, v, "+v")
    c.mount(W, 2.9, "-u", "painting_1", 1.4)
    c.mount(W, 6.0, "-u", "poster_7", 1.3)
    c.switch()


# ================================================================ guest floors
@recipe("nurse_post")
def nurse_post(c):
    """Nursing station (open alcove): desk facing the corridor, call indicator panel, phone, lamp,
    files, medicine cabinet, two chairs for visitors, plant."""
    t = table_set(c, "desk_office", 0.82, 1.2, "-v", "chair_tube", [(0, -0.62, "+v")])
    if t:
        c.on_top(t, "telephone", 0.45)
        c.on_top(t, "table_lamp", -0.5)
        c.on_top(t, "paper_stack", -0.05)
    c.hang("W", 0.82, "call_panel", 1.75)
    c.at("filing", c.W - 0.3, 1.6, "-u")
    c.at("plant_stand", 0.25, 2.5, "+u")
    c.hang("L", 1.6, "schedule", 1.42)


@recipe("housekeeping")
def housekeeping(c):
    c.at("laundry_cart", 0.5, 1.3, "+u")
    d = table_set(c, "desk_small", c.W - 0.3, 1.05, "-u", "chair", [(-0.55, 0, "+u")])
    c.on_top(d, "table_lamp", 0, 0.3)
    c.on_top(d, "paper_stack", 0, -0.2)
    c.switch()


def wc_room(c, men, shower):
    """Public WC / shower room: cubicles with toilets and grab bars inside (accessible cubicle at the
    window end), urinals for men, washbasins with mirrors and grab bars near the entrance; in the
    upper-floor shower rooms two shower cubicles with seats, a bench and coat hooks."""
    W = c.W
    # accessible cubicle at the window end, then standard ones
    if c.at("cubicle_wide", 0.8, 0.96, "+u"):
        c.at("toilet", 0.27, 0.96, "+u", check=False)
        c.mount(0.0, 1.45, "+u", "call_button", 0.85, check=False)
    n = 1 if shower else (2 if men else 3)
    for i in range(n):
        v = 1.74 + 0.5 + i * 1.0
        if c.at("cubicle", 0.7, v, "+u"):
            c.at("toilet", 0.27, v, "+u", check=False)
    if shower:
        for v in (3.3, 4.36):          # showers further in on the right, bench opposite
            if c.at("shower_cubicle", W - 0.6, v, "-u"):
                c.at("shower_tray", W - 0.5, v, "-u", check=False)
                c.mount(W, v + 0.32, "-u", "shower_seat", 0.0, check=False)
        c.wall("L", 3.6, "bench")
        c.hang("L", 3.6, "coat_hooks", 1.6)
        sinks = (1.2, 1.95)
    else:
        if men:
            for v in (2.3, 3.0):
                c.wall("R", v, "urinal")
        sinks = (3.9, 4.6) if men else (2.6, 3.3, 4.0)
    for v in sinks:
        c.wall("R", v, "sink")
    for v in (sinks[0] - 0.42, sinks[-1] + 0.42):
        c.hang("R", v, "grab_bar_v", 0.8)
    c.switch()


@recipe("wc_men")
def wc_men(c):
    wc_room(c, True, False)


@recipe("wc_women")
def wc_women(c):
    wc_room(c, False, False)


@recipe("wc_shower_m")
def wc_shower_m(c):
    wc_room(c, True, True)


@recipe("wc_shower_f")
def wc_shower_f(c):
    wc_room(c, False, True)


@recipe("access_bath")
def access_bath(c):
    """Accessible bathroom: bathtub with grab bars, toilet with a fold-down arm and wall bar, washbasin
    with bars, shower with a chair, call buttons, wheelchair parking."""
    W = c.W
    c.at("bathtub", W - 0.37, 1.05, "+v")
    c.hang("R", 1.05, "grab_bar", 0.85)
    c.hang("R", 2.15, "call_button", 0.9)
    c.at("toilet", 0.27, 2.4, "+u")
    c.hang("L", 2.95, "grab_fold", 0.75)
    c.hang("L", 1.85, "grab_bar_l", 0.7)
    c.at("sink", 0.22, 3.75, "+u")
    c.hang("L", 3.33, "grab_bar_v", 0.8)
    c.hang("L", 4.17, "grab_bar_v", 0.8)
    sh = c.at("shower_tray", W - 0.47, 3.1, "-u")
    if sh:
        c.at("stool", W - 0.5, 3.1, "+v", z=0.08, check=False)
        c.hang("R", 3.7, "grab_bar_v", 0.8)
    c.at("wheelchair", W - 0.42, 4.35, "-v")
    c.hang("L", 4.75, "towel_rail", 1.15)
    c.at("bath_mat", 1.2, 1.05, "+u", check=False)
    c.switch()


@recipe("lounge")
def lounge(c):
    """Floor lounge: TV corner with a sofa, two armchairs and a coffee table on a rug, floor lamp;
    game tables (chess, checkers or dominoes, backgammon) with full chair sets; bookcases; plants."""
    W = c.W
    lvl = c.room.level
    c.at("rug_big", 4.2, 1.6, "+u", check=False)
    tvc = c.at("tv_cabinet", W - 0.24, 1.6, "-u")
    c.on_top(tvc, "tv_small", facing="-u")
    c.at(["sofa_beige", "sofa_brown", "sofa_red"][lvl % 3], 3.0, 1.6, "+u")
    tb = c.at("table_coffee", 4.2, 1.6, "+u")
    c.on_top(tb, "vase")
    c.at("armchair_red", 4.2, 0.56, "+v")
    c.at("armchair_red", 4.2, 2.72, "-v")
    c.at("floor_lamp", 2.95, 0.42, "+v")
    games = [("game_chess", "game_dominoes"), ("game_checkers", "game_backgammon"), ("game_chess", "game_checkers")][lvl % 3]
    table_set(c, "table_sq", 1.3, 1.45, "+v", "chair", pair_u(0.8), top=(games[0],))
    table_set(c, "table_sq", 1.3, 3.45, "+v", "chair", sq4(0.8), top=(games[1],))
    first([lambda: c.wall("L", 4.6, "bookcase"), lambda: c.wall("L", 5.4, "bookcase")])
    c.wall("R", 4.75, "books")
    c.at("palm", W - 0.36, 3.45, "-u")
    c.at("plant_stand", 0.25, 0.35, "+v")
    c.hang("B", 4.3, "painting_3", 1.4)
    c.hang("L", 2.45, "wall_newspaper", 1.3)
    c.hang("B", 0.55, "schedule", 1.42)
    c.switch()


@recipe("library")
def library(c):
    """Library and reading room: bookcases along one wall, a green-cloth reading table with lamps and
    chairs, an armchair with a floor lamp by the window, the librarian's desk at the door."""
    W = c.W
    for v in (1.2, 2.15, 3.1, 4.05):
        c.wall("L", v, "bookcase")
    t = table_set(c, "table_read", W - 0.42, 2.1, "+u", "chair", [(-0.62, -0.35, "+u"), (-0.62, 0.35, "+u")])
    c.on_top(t, "table_lamp", 0, -0.4)
    c.on_top(t, "table_lamp", 0, 0.4)
    c.at("armchair_red", 1.5, 0.62, "+v")
    c.at("floor_lamp", 2.35, 0.45, "+v")
    d = table_set(c, "desk_small", W - 0.3, 4.4, "-u", "chair", [(-0.55, 0, "+u")])
    c.on_top(d, "table_lamp", 0, -0.3)
    c.hang("R", 2.1, "painting_1", 1.4)
    c.hang("R", 3.6, "poster_1", 1.3)
    c.hang("B", 2.4, "clock", 2.3)
    c.switch()


@recipe("projection")
def projection(c):
    c.at("projector", 0.94, 1.15, "-v")
    c.at("projector", 1.94, 1.15, "-v")
    c.wall("L", 3.0, "goods_rack")
    c.at("chair", 1.4, 2.0, "-v")
    c.hang("R", 3.5, "keep_out", 1.6)


@recipe("club_hall")
def club_hall(c):
    """Club hall: stage with curtain, piano, cinema rows; behind them a lounge with a Russian billiards
    table, four game tables (chess, checkers, dominoes, backgammon), soft armchair groups, bookcases,
    palms and flower stands, pictures between the windows."""
    W, D = c.W, c.D
    c.at("stage", W / 2, 1.6, "+v", foot=(W, 3.2), check=False)
    c.busy.append((0.0, W, 0.0, 3.2))
    c.at("stage_curtain", W / 2, 0.25, "+v", z=0.6, check=False)
    c.at("piano", 0.62, 4.3, "+u")
    for k in range(5):
        for u in (W / 2 - 2.68, W / 2 + 2.68):
            c.at("cinema_row", u, 5.4 + k * 1.0, "-v")
    # billiards with cue clearance
    if c.at("billiard", 8.4, 13.2, "+v"):
        c.busy.append((6.6, 10.25, 10.85, 15.55))
        c.hang("R", 12.65, "cue_rack", 0.0)
    for (u, v, g) in ((2.0, 11.6, "game_chess"), (4.4, 11.6, "game_checkers"), (2.0, 13.6, "game_dominoes"),
                      (4.4, 13.6, "game_backgammon")):
        table_set(c, "table_sq", u, v, "+v", "chair", pair_u(0.8), top=(g,))
    # soft corner by the storeroom door and by the foyer door
    c.at("sofa_brown", 2.6, 16.75, "-v")
    tb = c.at("table_coffee", 2.6, 15.8, "+v")
    c.on_top(tb, "vase")
    c.at("armchair_beige", 1.25, 15.8, "+u")
    c.at("armchair_beige", 3.95, 15.8, "-u")
    t = c.at("table_round", 8.0, 16.6, "+v")
    c.on_top(t, "vase")
    c.at("armchair_red", 7.0, 16.6, "+u")
    c.at("armchair_red", 9.0, 16.6, "-u")
    first([lambda: c.wall("L", 15.9, "bookcase"), lambda: c.wall("R", 15.9, "bookcase")])
    for (u, v) in ((10.8, 3.6), (0.5, 10.3), (10.8, 10.3)):
        c.at("palm", u, v, "+v")
    for (u, v) in ((0.4, 6.15), (0.4, 9.4), (10.9, 6.15), (10.9, 9.4)):
        c.at("plant_stand", u, v, "+v")
    for side in ("L", "R"):
        for (v, k) in ((2.9, "painting_2"), (6.15, "painting_1"), (9.4, "poster_5"), (12.65, "painting_2")):
            c.hang(side, v, k, 2.0 if v < 3.3 else (1.7 if v > 12 else 1.55))
    c.hang("B", 3.3, "notice_board", 1.25)
    c.hang("B", 8.0, "wall_newspaper", 1.3)


@recipe("stair_main", "stair_end")
def stair(c):
    """Storey-level stair lobbies by the windows: a bench and a plant on every floor."""
    r = c.room
    f = stair_frame(r)
    o, p1 = f(0, 0), f(0, -1)
    rot = math.atan2(p1[1] - o[1], p1[0] - o[0]) + math.pi / 2
    for i, L in enumerate(LEVELS):
        items = [("plant_stand", f(CELL_U - 0.4, CELL_V - 0.4), 0)]
        if r.kind == "stair_end" or i in (2, 3):
            items.append(("bench", f(3.6, CELL_V - 0.5), rot))
        for key, (x, y), ro in items:
            c.B.lib.place(key, F.MODS[key][0], c.B.coll_for(r.rid), f"{key}_{r.rid}_{i}", (x, y, L), ro,
                          c.B.room_empty[r.rid])
            w_, d_ = F.MODS[key][1], F.MODS[key][2]
            c.B.game_boxes.append({"room": r.rid, "center": (x, y, L + 0.45), "size": (w_, d_, 0.9), "rot": ro, "key": key})
            c.B.stats["Furniture"] = c.B.stats.get("Furniture", 0) + mod_info(key)[2]


@recipe("shaft")
def none(c):
    pass


# ================================================================== half-abandoned mood
COBWEB_P = {"E_technical": 0.9, "D_catering": 0.6, "C_medical": 0.5, "P_patient": 0.45, "S_spa": 0.4,
            "B_admin": 0.5, "A_entrance": 0.3, "CIRC": 0.6}
PAPER_KINDS = ("director", "admin_office", "registration", "info", "guard", "med_reg", "med_archive", "nurse_post",
               "nurse_office", "nurse_office_floor", "staff_office", "doctor_duty", "library", "gp", "consult")
STAIN_KINDS = ("wc_men", "wc_women", "wc_shower_m", "wc_shower_f", "kitchen", "dishwash", "food_prep", "veg_prep",
               "corridor", "corridor_patient", "service_corridor", "dirty_linen", "waste", "staff_wc", "suite_bath")
PLANT_KEYS = ("plant_stand", "palm", "plant_1", "plant_2")


def mood(c):
    """Light traces of neglect, never in the way: cobwebs in upper corners, dust patches, dry leaves under
    the dying plants, a few papers on office floors, small stains in wet rooms and corridors."""
    r = c.room
    if r.kind in ("shaft",) or r.kind.startswith("stair"):
        return
    rng = c.rng
    # every room that is not open circulation gets a light switch by its door (the game uses them)
    if not r.kind.startswith(("corridor", "service_corridor")) and r.kind not in ("vestibule", "hall", "foyer") and \
            not any(lg["key"] == "light_switch" and lg["room"] == r.rid for lg in c.B.game_items):
        c.switch()
    tall = r.z1 - r.z0
    # cobwebs in the corners of the largest rectangle
    if rng.random() < COBWEB_P.get(r.dept, 0.4):
        q = max(c.rects_local, key=lambda t: (t[1] - t[0]) * (t[3] - t[2]))
        corners = [(q[0], q[2], "+u", "+v"), (q[1], q[2], "-u", "+v"), (q[0], q[3], "+u", "-v"), (q[1], q[3], "-u", "-v")]
        rng.shuffle(corners)
        for (u, v, fu, fv) in corners[: 1 + (rng.random() < 0.4)]:
            ex = c.dir_world(fu)
            ey = c.dir_world(fv)
            right = ex[0] * ey[1] - ex[1] * ey[0] > 0
            x, y = c.l2w(u, v)
            rot = math.atan2(ex[1], ex[0])
            key = "cobweb_r" if right else "cobweb_l"
            ob = c.B.lib.place(key, F.MODS[key][0], c.B.coll_for(r.rid), f"Cobweb_{r.rid.split('.')[1]}",
                               (x, y, r.z1 - 0.004), rot if right else rot, c.B.room_empty[r.rid])
            c.B.stats["Furniture"] = c.B.stats.get("Furniture", 0) + mod_info(key)[2]
    # dust patches on the floor (soft, under or between furniture)
    for _ in range(1 if r.area < 20 else 2):
        if rng.random() < 0.55:
            q = max(c.rects_local, key=lambda t: (t[1] - t[0]) * (t[3] - t[2]))
            if q[1] - q[0] > 1.8 and q[3] - q[2] > 1.8:
                c.at("dust_patch", rng.uniform(q[0] + 0.8, q[1] - 0.8), rng.uniform(q[2] + 0.8, q[3] - 0.8), "+v",
                     check=False)
    # dry leaves under plants
    for it in list(c.items):
        if it.key in PLANT_KEYS and rng.random() < 0.7:
            c.at("leaves_dry", it.u + rng.uniform(-0.25, 0.25), it.v + rng.uniform(-0.2, 0.2),
                 rng.choice(["+u", "-u", "+v", "-v"]), check=False)
    # papers fallen on office floors
    if r.kind in PAPER_KINDS and rng.random() < 0.6:
        for _ in range(12):
            u, v = rng.uniform(0.4, c.W - 0.4), rng.uniform(0.6, c.D - 0.6)
            rr = (u - 0.25, u + 0.25, v - 0.25, v + 0.25)
            if c.inside(rr) and c.free(rr):
                c.at("papers_floor", u, v, rng.choice(["+u", "-u", "+v", "-v"]), check=False)
                break
    # small stains
    if r.kind in STAIN_KINDS:
        n = max(1, int(r.area / 40)) if r.kind.startswith(("corridor", "service")) else (1 if rng.random() < 0.5 else 0)
        for _ in range(n):
            q = rng.choice(c.rects_local)
            if q[1] - q[0] > 1.0 and q[3] - q[2] > 1.0:
                c.at("stain_small", rng.uniform(q[0] + 0.4, q[1] - 0.4), rng.uniform(q[2] + 0.4, q[3] - 0.4), "+v",
                     check=False)
    # things left behind in the guest-floor corridors
    if r.kind == "corridor_patient":
        left = {1: "wheelchair", 2: "laundry_cart", 3: "cleaning_cart"}[r.level]
        for (a, b) in wall_segments(c, "W", 1.6):
            if 12 < a < c.W - 12 and c.at(left, (a + b) / 2, 0.42, "+u", cover_ok=True):
                break
    if r.kind == "corridor":
        for (a, b) in wall_segments(c, "B", 2.2):
            if 25 < a < c.W - 6 and c.at("stretcher", (a + b) / 2, c.D - 0.35, "+u", cover_ok=True):
                break


def furnish_all(B):
    place_radiators_and_curtains(B)
    missing = set()
    B.ctx = {}
    for r in B.plan.rooms.values():
        fn = R.get(r.kind)
        if fn is None:
            missing.add(r.kind)
            continue
        c = Ctx(B, r, random.Random(r.seed))
        fn(c)
        mood(c)
        B.ctx[r.rid] = c
    B.stats["recipes_missing"] = sorted(missing)
