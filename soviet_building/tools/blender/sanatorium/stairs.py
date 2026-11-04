"""U-shaped stairs (11 + 11 risers of 150/300 mm per storey) for the three stair cells.

Concrete flights with terrazzo treads, landings and floor-level lobbies at each storey,
well railings with alpha-textured balusters and a wooden handrail, wall handrail on the
corridor side (handrails on both sides of every flight for accessibility)."""
from .params import *
from .meshkit import MB
from .stairs_layout import stair_frame, stair_spec, CELL_U, CELL_V
from .atlas import FURN_UV, DECAL_UV

RAIL_H = 0.90


class Local:
    """Maps stair-local (u, v, z) to world and builds polygons with a desired local normal."""

    def __init__(self, room, mb):
        self.f = stair_frame(room)
        o = self.f(0, 0)
        ux, uy = self.f(1, 0)
        vx, vy = self.f(0, 1)
        self.U = (ux - o[0], uy - o[1])
        self.V = (vx - o[0], vy - o[1])
        self.mb = mb

    def p(self, u, v, z):
        x, y = self.f(u, v)
        return (x, y, z)

    def dirw(self, du, dv, dz):
        return (self.U[0] * du + self.V[0] * dv, self.U[1] * du + self.V[1] * dv, dz)

    def poly(self, pts, mat, want, uvmode="uv"):
        P = [self.p(*q) for q in pts]
        if uvmode == "uv":
            uvs = [(q[0] / 2.0, q[1] / 2.0) for q in pts]
        elif uvmode == "uz":
            uvs = [(q[0] / 2.0, q[2] / 2.0) for q in pts]
        else:
            uvs = [(q[1] / 2.0, q[2] / 2.0) for q in pts]
        self.mb.poly_n(P, uvs, mat, self.dirw(*want))


def flight(L, base, dirn, v0, v1, mb_walk, mb_side, sides, to_floor=False):
    """One flight: risers/treads on mb_walk, stepped side faces and soffit on mb_side."""
    n = RISERS_PER_FLIGHT
    u0 = STAIR_LANDING if dirn > 0 else STAIR_LANDING + STAIR_RUN
    du = TREAD * dirn
    for k in range(n):
        u = u0 + du * k
        za, zb = base + k * RISER, base + (k + 1) * RISER
        L.poly([(u, v0, za), (u, v1, za), (u, v1, zb), (u, v0, zb)], "terrazzo", (-dirn, 0, 0), "vz")
        if k < n - 1:
            ua, ub = sorted((u, u + du))
            L.poly([(ua, v0, zb), (ub, v0, zb), (ub, v1, zb), (ua, v1, zb)], "terrazzo", (0, 0, 1))
    # soffit: from the bottom nosing line to the landing underside
    ue = u0 + du * (n - 1)
    zt = base + n * RISER
    s0 = (u0, base - 0.0)
    s1 = (ue, zt - 0.2)
    L.poly([(s0[0], v0, s0[1]), (s0[0], v1, s0[1]), (s1[0], v1, s1[1]), (s1[0], v0, s1[1])], "plaster", (0, 0, -1))
    # stepped side profiles
    for v, want in sides:
        prof = [(u0, base)]
        for k in range(n):
            u = u0 + du * k
            prof.append((u, base + (k + 1) * RISER))
            if k < n - 1:
                prof.append((u + du, base + (k + 1) * RISER))
        prof.append((ue, zt - 0.2))
        if to_floor:
            prof = [(u0, base)] + prof[1:-1] + [(ue, zt - 0.2), (ue, base)]
        pts = [(u, v, z) for (u, z) in prof]
        L.poly(pts, "plaster", (0, want, 0), "uz")


def slab(L, u0, u1, v0, v1, z, t, mat_top, edges, bottom=True):
    L.poly([(u0, v0, z), (u1, v0, z), (u1, v1, z), (u0, v1, z)], mat_top, (0, 0, 1))
    if bottom:
        L.poly([(u0, v0, z - t), (u1, v0, z - t), (u1, v1, z - t), (u0, v1, z - t)], "plaster", (0, 0, -1))
    for e in edges:
        if e == "u0":
            L.poly([(u0, v0, z - t), (u0, v1, z - t), (u0, v1, z), (u0, v0, z)], "plaster", (-1, 0, 0), "vz")
        if e == "u1":
            L.poly([(u1, v0, z - t), (u1, v1, z - t), (u1, v1, z), (u1, v0, z)], "plaster", (1, 0, 0), "vz")
        if e == "v1":
            L.poly([(u0, v1, z - t), (u1, v1, z - t), (u1, v1, z), (u0, v1, z)], "plaster", (0, 1, 0), "uz")
        if e == "v0":
            L.poly([(u0, v0, z - t), (u1, v0, z - t), (u1, v0, z), (u0, v0, z)], "plaster", (0, -1, 0), "uz")


def railing(L, mb_rail, mb_infill, pts, wall=False):
    """Handrail through stair-local points (u, v, z_walk); balusters as an alpha panel below."""
    path = [L.p(u, v, z + RAIL_H) for (u, v, z) in pts]
    start = len(mb_rail.uv)
    mb_rail.tube(path, 0.025, "atlas_furn", sides=6, cap0=True, cap1=True)
    u0, v0, u1, v1 = FURN_UV["wood_dark"]
    mb_rail.uv[start:] = [(u0 + (u1 - u0) * min(max(u, 0), 1), v0 + (v1 - v0) * (v % 1.0)) for (u, v) in mb_rail.uv[start:]]
    if wall:
        return
    u0, v0, u1, v1 = DECAL_UV["railing"]
    for a, b in zip(pts[:-1], pts[1:]):
        la = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
        if la < 0.2:
            continue
        q = [L.p(a[0], a[1], a[2] + 0.05), L.p(b[0], b[1], b[2] + 0.05), L.p(b[0], b[1], b[2] + RAIL_H - 0.03),
             L.p(a[0], a[1], a[2] + RAIL_H - 0.03)]
        # the railing region is tileable horizontally: repeat by stretching u inside the region is not
        # possible in an atlas, so long runs are split into 0.5 m panels
        n = max(1, int(round(la / 0.5)))
        for k in range(n):
            t0, t1 = k / n, (k + 1) / n
            lerp = lambda P, Q, t: tuple(P[i] + (Q[i] - P[i]) * t for i in range(3))
            qq = [lerp(q[0], q[1], t0), lerp(q[0], q[1], t1), lerp(q[3], q[2], t1), lerp(q[3], q[2], t0)]
            mb_infill.poly(qq, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], "atlas_decal")


def build_stair(room, top_level=3):
    mb = MB(f"Stair_{room.rid}")
    rail = MB(f"StairRails_{room.rid}")
    inf = MB(f"StairBalusters_{room.rid}")
    L = Local(room, mb)
    sp = stair_spec()
    vA0, vA1 = sp["flights"][0]["v"]
    vB0, vB1 = sp["flights"][1]["v"]
    uL, uM = STAIR_LANDING, STAIR_LANDING + STAIR_RUN
    for i in range(top_level + 1):
        z = LEVELS[i]
        if i > 0:
            # floor landing + lobby at storey level (L-shaped slab around the void)
            slab(L, 0, uL, 0, vB1, z, SLAB_T, "terrazzo", ["u1"])
            slab(L, 0, CELL_U, vB1, CELL_V, z, SLAB_T, "terrazzo", [])
            L.poly([(uL, vB1, z - SLAB_T), (CELL_U, vB1, z - SLAB_T), (CELL_U, vB1, z), (uL, vB1, z)], "plaster",
                   (0, -1, 0), "uz")
            # lobby-edge railing over the void
            railing(L, rail, inf, [(uL, vB1 + 0.04, z), (CELL_U - 0.02, vB1 + 0.04, z)])
        if i == top_level:
            # top storey: guard the void on the floor-landing side above flight A
            railing(L, rail, inf, [(uL + 0.03, 0.02, z), (uL + 0.03, vB1, z)])
            continue
        zm = z + RISERS_PER_FLIGHT * RISER
        ground = i == 0
        flight(L, z, +1, vA0, vA1, mb, mb, [(vA1, +1)])
        flight(L, zm, -1, vB0, vB1, mb, mb, [(vB0, -1), (vB1, +1)])
        if ground:
            # close the low space under flight B / mid-landing towards the lobby (no head-height hazard)
            L.poly([(uL, vB1, z), (CELL_U, vB1, z), (CELL_U, vB1, zm - 0.2), (uM, vB1, zm - 0.2),
                    (uM, vB1, zm), (uL, vB1, zm + 1.45)], "plaster", (0, 1, 0), "uz")
        slab(L, uM, CELL_U, 0, vB1, zm, 0.2, "terrazzo", ["u0", "v1"])
        # well railings (inner side of both flights, joined across the well at the mid-landing)
        railing(L, rail, inf, [(uL, vA1 - 0.04, z + RISER), (uM, vA1 - 0.04, zm), (uM + 0.12, vA1 - 0.04, zm)])
        railing(L, rail, inf, [(uM + 0.12, vB0 + 0.04, zm), (uM, vB0 + 0.04, zm), (uL, vB0 + 0.04, zm + 1.65 - RISER)])
        railing(L, rail, inf, [(uM + 0.12, vA1 - 0.04, zm), (uM + 0.12, vB0 + 0.04, zm)])
        # outer (lobby-side) railing of flight B and around the mid-landing
        railing(L, rail, inf, [(CELL_U - 0.02, vB1 - 0.04, zm), (uM, vB1 - 0.04, zm),
                               (uL, vB1 - 0.04, zm + 1.65 - RISER)])
        # wall handrail along flight A (corridor-side wall) and around the mid landing wall
        railing(L, rail, inf, [(uL - 0.3, 0.06, z), (uL, 0.06, z), (uM, 0.06, zm), (CELL_U - 0.06, 0.06, zm),
                               (CELL_U - 0.06, vA1, zm)], wall=True)
    return mb, rail, inf
