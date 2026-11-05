"""Pure-Python geometry resolution of the plan (no bpy): wall faces, door/window holes,
columns, validation. Shared by the 3D build and the plan drawings."""
from dataclasses import dataclass, field
from .params import *
from .exterior import exterior_windows

EPS = 1e-6
FRAMED = {"std", "glazed", "double", "double_glazed", "metal", "metal_glazed", "wide", "padded", "wc_door",
          "steel_double"}
COLUMNS_X = [6.0 * k for k in range(1, 13)]
COL_LINES = ((FRONT_Y1, FRONT_Y1 + COLUMN), (REAR_Y0 - COLUMN, REAR_Y0))  # pilasters on the corridor side


@dataclass
class Edge:
    room: object
    ri: int
    side: str          # x0 x1 y0 y1
    axis: str          # wall direction: "y" for x-edges, "x" for y-edges
    coord: float
    a: float
    b: float
    n: int             # outward normal sign along the normal axis


def edges_of(room):
    out = []
    for i, (x0, x1, y0, y1) in enumerate(room.rects):
        out += [Edge(room, i, "x0", "y", x0, y0, y1, -1), Edge(room, i, "x1", "y", x1, y0, y1, +1),
                Edge(room, i, "y0", "x", y0, x0, x1, -1), Edge(room, i, "y1", "x", y1, x0, x1, +1)]
    return out


@dataclass
class DoorGeom:
    door: object
    ea: Edge
    eb: Edge           # None for exterior doors
    axis: str
    fa: float          # face coordinate on room a side
    fb: float          # face coordinate on room b side (exterior: facade side of the reveal)
    nab: int           # direction a -> b along the normal axis
    c: float
    ow: float          # opening width
    z0: float
    z1: float

    @property
    def thickness(self):
        return abs(self.fb - self.fa)


def opening_size(d):
    if d.kind in FRAMED:
        return d.w + 0.10, d.h + 0.05
    if d.kind == "lift":
        return d.w, d.h
    return d.w, d.h


def zr_overlap(r1, r2):
    return min(r1.z1, r2.z1) - max(r1.z0, r2.z0)


class Layout:
    def __init__(self, plan):
        self.plan = plan
        self.rooms = plan.rooms
        self.edges = {rid: edges_of(r) for rid, r in self.rooms.items()}
        self.windows = exterior_windows()
        self.doors = []
        self.errors = []
        self.warnings = []
        for d in plan.doors:
            g = self.resolve_door(d)
            if g:
                self.doors.append(g)
        self.win_room = self.assign_windows()

    # ------------------------------------------------------------------ doors
    def resolve_door(self, d):
        A = self.rooms.get(d.a)
        if A is None:
            self.errors.append(f"door {d.a}->{d.b}: unknown room {d.a}")
            return None
        ow, oh = opening_size(d)
        z0 = LEVELS[d.level] + d.sill
        z1 = z0 + oh
        if not (A.z0 - EPS <= z0 and z1 <= A.z1 + EPS):
            self.errors.append(f"door {d.a}->{d.b}: z {z0:.2f}-{z1:.2f} outside room {A.z0:.2f}-{A.z1:.2f}")
        if d.b == "EXT":
            key, val = d.ext
            axis = "x" if key == "y" else "y"
            for e in self.edges[d.a]:
                if e.axis == axis and abs(e.coord - val) < 1e-4 and e.a - EPS <= d.c - ow / 2 and d.c + ow / 2 <= e.b + EPS:
                    fb = val + e.n * (EXT_T - 0.2)      # exterior steel door face is 0.2 inside the facade
                    return DoorGeom(d, e, None, axis, e.coord, fb, e.n, d.c, ow, z0, z1)
            self.errors.append(f"door {d.a}->EXT at {d.c}: no edge")
            return None
        B = self.rooms.get(d.b)
        if B is None:
            self.errors.append(f"door {d.a}->{d.b}: unknown room {d.b}")
            return None
        if not (B.z0 - EPS <= z0 and z1 <= B.z1 + EPS):
            self.errors.append(f"door {d.a}->{d.b}: z {z0:.2f}-{z1:.2f} outside room {d.b}")
        best = None
        for ea in self.edges[d.a]:
            if d.axis and ea.axis != d.axis:
                continue
            for eb in self.edges[d.b]:
                if eb.axis != ea.axis or eb.n != -ea.n:
                    continue
                gap = (eb.coord - ea.coord) * ea.n
                if not (0.02 < gap < 0.75):
                    continue
                lo, hi = max(ea.a, eb.a), min(ea.b, eb.b)
                if hi - lo < ow - EPS:
                    continue
                c = self.nudge(d.c, ow, lo, hi, ea)
                if c is None:
                    continue
                if best is None or gap < best[0]:
                    best = (gap, ea, eb, c)
        if best is None:
            self.errors.append(f"door {d.a}->{d.b} at {d.c} ({d.kind}): no shared wall")
            return None
        gap, ea, eb, c = best
        if abs(c - d.c) > 1e-6:
            self.warnings.append(f"door {d.a}->{d.b}: nudged {d.c:.2f} -> {c:.2f}")
        return DoorGeom(d, ea, eb, ea.axis, ea.coord, eb.coord, ea.n, c, ow, z0, z1)

    def nudge(self, c, ow, lo, hi, e):
        """Keep the door (plus casing) inside [lo, hi] and clear of corridor pilasters."""
        half = ow / 2 + (0.07 if True else 0)
        c = min(max(c, lo + ow / 2), hi - ow / 2)
        if e.axis == "x" and any(abs(e.coord - y) < 0.25 for y in (FRONT_Y1, CORR_Y0, CORR_Y1, REAR_Y0)):
            for _ in range(4):
                hit = [x for x in COLUMNS_X if c - half < x + COLUMN / 2 and c + half > x - COLUMN / 2]
                if not hit:
                    break
                x = hit[0]
                left, right = x - COLUMN / 2 - half, x + COLUMN / 2 + half
                c = left if abs(left - c) <= abs(right - c) and left - ow / 2 >= lo - EPS else right
                if c + ow / 2 > hi + EPS or c - ow / 2 < lo - EPS:
                    return None
        return c

    # ---------------------------------------------------------------- windows
    def assign_windows(self):
        res = {}
        for wi, w in enumerate(self.windows):
            hits = []
            for rid, es in self.edges.items():
                r = self.rooms[rid]
                for e in es:
                    if e.axis == w.axis and abs(e.coord - w.face) < 1e-4 and e.n == -w.inward \
                            and e.a - EPS <= w.s - w.hw and w.s + w.hw <= e.b + EPS \
                            and r.z0 - EPS <= w.z0 and w.z1 <= r.z1 + EPS:
                        hits.append(e)
            if len(hits) != 1:
                self.errors.append(f"window {w.facade} s={w.s:.3f} z={w.z0:.2f}: {len(hits)} rooms "
                                   f"{[h.room.rid for h in hits]}")
            else:
                res[wi] = hits[0]
        return res

    # ------------------------------------------------------------------ faces
    def face_cuts(self, e):
        """Rectangles (s0, s1, z0, z1, tag) removed from the face of edge e."""
        r = e.room
        cuts = []
        for rid, es in self.edges.items():
            q = self.rooms[rid]
            zo0, zo1 = max(r.z0, q.z0), min(r.z1, q.z1)
            if zo1 - zo0 < EPS:
                continue
            for f in es:
                if f is e or f.axis != e.axis or f.n != -e.n or abs(f.coord - e.coord) > 1e-6:
                    continue
                lo, hi = max(e.a, f.a), min(e.b, f.b)
                if hi - lo > EPS:
                    cuts.append((lo, hi, zo0, zo1, "open"))
        for g in self.doors:
            if g.ea is e or g.eb is e:
                cuts.append((g.c - g.ow / 2, g.c + g.ow / 2, g.z0, g.z1, "door"))
        for wi, we in self.win_room.items():
            if we is e:
                w = self.windows[wi]
                cuts.append((w.s - w.hw, w.s + w.hw, w.z0, w.z1, "window"))
        for sk in r.skip:
            side, _, a, b, z0, z1 = sk
            if side == e.side:
                cuts.append((e.a if a is None else a, e.b if b is None else b, z0, z1, "skip"))
        return cuts

    # ------------------------------------------------------------- validation
    def validate(self):
        P = self.plan
        by_level = {}
        for r in self.rooms.values():
            by_level.setdefault(r.level, []).append(r)
        rl = list(self.rooms.values())
        for i, a in enumerate(rl):
            for b in rl[i + 1:]:
                if zr_overlap(a, b) <= EPS:
                    continue
                for ra in a.rects:
                    for rb in b.rects:
                        ox = min(ra[1], rb[1]) - max(ra[0], rb[0])
                        oy = min(ra[3], rb[3]) - max(ra[2], rb[2])
                        if ox > 1e-4 and oy > 1e-4:
                            self.errors.append(f"overlap {a.rid} / {b.rid}: {ox:.2f} x {oy:.2f}")
            for i1, ra in enumerate(a.rects):
                for rb in a.rects[i1 + 1:]:
                    ox = min(ra[1], rb[1]) - max(ra[0], rb[0])
                    oy = min(ra[3], rb[3]) - max(ra[2], rb[2])
                    if ox > 1e-4 and oy > 1e-4:
                        self.errors.append(f"self overlap {a.rid}")
        # containment in the building outline
        for r in rl:
            for (x0, x1, y0, y1) in r.rects:
                in_main = MAIN_X0 - EPS <= x0 and x1 <= MAIN_X1 + EPS and FRONT_Y0 - 0.36 <= y0 and y1 <= REAR_Y1 + EPS
                in_eb = ENT_IX0 - 0.3 - EPS <= x0 and x1 <= ENT_IX1 + EPS and ENT_IY0 - EPS <= y0 and y1 <= 0.36
                if not (in_main or in_eb):
                    self.errors.append(f"{r.rid} rect {x0, x1, y0, y1} outside the building")
        # holes on one face must not overlap
        for rid, es in self.edges.items():
            for e in es:
                hs = [c for c in self.face_cuts(e) if c[4] in ("door", "window")]
                for i, h in enumerate(hs):
                    for k in hs[i + 1:]:
                        if min(h[1], k[1]) - max(h[0], k[0]) > 0.02 and min(h[3], k[3]) - max(h[2], k[2]) > 0.02:
                            self.errors.append(f"{rid} {e.side}: openings overlap {h[:4]} {k[:4]}")
                    if h[0] < e.a - EPS or h[1] > e.b + EPS:
                        self.errors.append(f"{rid} {e.side}: opening outside face {h[:4]}")
        # reachability from the entrance hall
        adj = {rid: set() for rid in self.rooms}
        for g in self.doors:
            if g.door.b != "EXT" and g.door.kind not in ("window", "port"):
                adj[g.door.a].add(g.door.b)
                adj[g.door.b].add(g.door.a)
        for rid, es in self.edges.items():
            for e in es:
                for c in self.face_cuts(e):
                    if c[4] == "open":
                        for qid, fs in self.edges.items():
                            if qid != rid and any(f.axis == e.axis and f.n == -e.n and abs(f.coord - e.coord) < 1e-6
                                                  and min(e.b, f.b) - max(e.a, f.a) > EPS
                                                  and zr_overlap(self.rooms[qid], e.room) > EPS for f in fs):
                                adj[rid].add(qid)
        seen, todo = {"L0.EB_HALL"}, ["L0.EB_HALL"]
        while todo:
            for q in adj[todo.pop()]:
                if q not in seen:
                    seen.add(q)
                    todo.append(q)
        for rid in self.rooms:
            if rid not in seen:
                self.errors.append(f"unreachable room {rid} ({self.rooms[rid].en})")
        # rooms without any door/opening
        return self.errors
