"""Room-local placement frame and clearance checks for furnishing.

Local frame of a room: v = 0 at the window wall, v grows into the room; u runs along the
window wall to the right of a viewer facing the window. Walls: W (window), B (back),
L (left, u=0), R (right, u=W). Floor modules face local -Y and have a centred footprint;
`facing` gives the room direction the module's front points to. Wall-mounted modules
(furniture.WALL) have their origin on the wall plane.

Every placement is checked:
  * floor items: inside the room, clear of door swings, radiators, pilasters and other items,
    and clear of wall-hung items they would cover;
  * wall items: on a real wall, clear of openings, door plates, other wall items (with a gap,
    so posters, plans and calendars never overlap or Z-fight) and of furniture standing in front;
  * items on top of furniture: only if the base was actually placed, inside its top surface.
The bpy side (Library.place) is only touched through B.lib, so the same code also runs in a
dry-run mode without Blender (tools: furnish preview)."""
import math
from .params import *
from . import furniture as F

EPS = 1e-6
WALL_GAP = 0.12        # minimum horizontal gap between two wall-hung items
_INFO = {}


def mod_info(key):
    """(zmin, zmax, tris) of a module, built once in plain Python."""
    if key not in _INFO:
        mb = F.MODS[key][0]()
        zs = [v[2] for v in mb.v] or [0.0]
        _INFO[key] = (min(zs), max(zs), mb.tris())
    return _INFO[key]


def _ov(a0, a1, b0, b1, m=0.0):
    return min(a1, b1) - max(a0, b0) > m


class Item:
    __slots__ = ("key", "u", "v", "facing", "z", "rect", "top", "ob", "base", "kids")

    def __init__(self, key, u, v, facing, z, rect, top, ob, base=None):
        self.key, self.u, self.v, self.facing, self.z = key, u, v, facing, z
        self.rect, self.top, self.ob, self.base, self.kids = rect, top, ob, base, []


class Ctx:
    def __init__(self, B, room, rng):
        self.B, self.room, self.rng = B, room, rng
        self.z0 = room.z0
        x0, x1, y0, y1 = room.bbox
        side = room.win
        if side is None:
            cy = (y0 + y1) / 2
            side = "south" if y1 <= 0.01 else ("front" if cy < 8.1 else "rear")
            if room.rid.endswith(("EB_E1", "EB_E2", "EB_E3", "EB_E5", "EB_E6")):
                side = "east"
        if side in ("front", "south"):
            self.O, self.U, self.V, self.W, self.D = (x1, y0), (-1, 0), (0, 1), x1 - x0, y1 - y0
        elif side == "rear":
            self.O, self.U, self.V, self.W, self.D = (x0, y1), (1, 0), (0, -1), x1 - x0, y1 - y0
        elif side == "east":
            self.O, self.U, self.V, self.W, self.D = (x1, y1), (0, -1), (-1, 0), y1 - y0, x1 - x0
        else:  # west
            self.O, self.U, self.V, self.W, self.D = (x0, y0), (0, 1), (1, 0), y1 - y0, x1 - x0
        self.rects_local = [self._rect_local(r) for r in room.rects]
        self.busy = []           # floor footprints (u0, u1, v0, v1)
        self.openings = []       # (rect, z0, z1) zones that no wall item may cover
        self.items = []          # placed floor items (Item)
        self.wall_items = []     # (axis, coord, a, b, z0, z1); axis "v": wall v=coord, interval along u
        self.doors_local = []    # (side, t0, t1, kind, depth_rect)
        self.windows_local = []  # (side, t0, t1)
        self.placed = []         # every object created (for rollback)
        self.fails = []          # rejected placements (key, u, v, reason) for previews/debugging
        self._tx = []
        self.reserve_openings()
        self.reserve_open_sides()
        if room.kind.startswith(("corridor", "service_corridor")):
            from .layout import COLUMNS_X
            for x in COLUMNS_X:
                for (ya, yb) in ((CORR_Y0, CORR_Y0 + COLUMN - CORR_T), (CORR_Y1 - COLUMN + CORR_T, CORR_Y1)):
                    a, b = self.w2l(x - COLUMN / 2 - 0.05, ya), self.w2l(x + COLUMN / 2 + 0.05, yb)
                    r = (min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]), max(a[1], b[1]))
                    self.busy.append(r)
                    self.openings.append((r, 0.0, 9.0))

    # ---------------------------------------------------------------- frames
    def w2l(self, x, y):
        dx, dy = x - self.O[0], y - self.O[1]
        return (dx * self.U[0] + dy * self.U[1], dx * self.V[0] + dy * self.V[1])

    def l2w(self, u, v):
        return (self.O[0] + u * self.U[0] + v * self.V[0], self.O[1] + u * self.U[1] + v * self.V[1])

    def _rect_local(self, r):
        a = self.w2l(r[0], r[2])
        b = self.w2l(r[1], r[3])
        return (min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]), max(a[1], b[1]))

    def dir_world(self, facing):
        du, dv = {"+u": (1, 0), "-u": (-1, 0), "+v": (0, 1), "-v": (0, -1)}[facing]
        return (du * self.U[0] + dv * self.V[0], du * self.U[1] + dv * self.V[1])

    def rot(self, facing):
        fx, fy = self.dir_world(facing)
        return math.atan2(fy, fx) + math.pi / 2

    # ------------------------------------------------------------ clearances
    def _side_of(self, u0, u1, v0, v1):
        if abs(v0) < 0.05 and abs(v1) < 0.05:
            return "W"
        if abs(v0 - self.D) < 0.05 and abs(v1 - self.D) < 0.05:
            return "B"
        if abs(u0) < 0.05 and abs(u1) < 0.05:
            return "L"
        if abs(u0 - self.W) < 0.05 and abs(u1 - self.W) < 0.05:
            return "R"
        return "X"

    def reserve_openings(self):
        lay = self.B.lay
        tall = self.room.z1 - self.room.z0 > CEIL_H + 0.1
        for g in lay.doors:
            mine_a = g.door.a == self.room.rid
            mine_b = g.door.b == self.room.rid
            if not (mine_a or mine_b):
                continue
            if tall and abs(g.z0 - self.z0) > 1.0:
                continue
            if self.room.kind.startswith("stair") and abs(g.z0 - self.z0) > 0.2:
                continue
            face = g.fa if mine_a else g.fb
            p0 = (g.c - g.ow / 2, face) if g.axis == "x" else (face, g.c - g.ow / 2)
            p1 = (g.c + g.ow / 2, face) if g.axis == "x" else (face, g.c + g.ow / 2)
            a, b = self.w2l(*p0), self.w2l(*p1)
            kind = g.door.kind
            depth = {"counter": 0.7, "window": 0.5, "port": 0.6}.get(kind, max(g.ow, 0.9) + 0.15)
            swings_here = (g.door.swing == "a") == mine_a
            if kind in ("std", "glazed", "metal", "metal_glazed", "wide", "padded", "wc_door") and not swings_here:
                depth = 0.65      # leaf opens into the other room: keep only a passage clearance
            if kind == "lift":
                depth = 1.6
            u0, u1 = min(a[0], b[0]), max(a[0], b[0])
            v0, v1 = min(a[1], b[1]), max(a[1], b[1])
            zt = (g.z1 - self.z0) + 0.12
            zb = g.z0 - self.z0 - 0.05
            if abs(u1 - u0) > abs(v1 - v0):     # opening along u
                if v0 < self.D / 2:
                    r = (u0 - 0.1, u1 + 0.1, v0 - 0.01, v0 + depth)
                else:
                    r = (u0 - 0.1, u1 + 0.1, v1 - depth, v1 + 0.01)
                plate = [(u0 - 0.75, u0 - 0.05), (u1 + 0.05, u1 + 0.75)]
                wall_axis, wall_c = "v", (v0 + v1) / 2
            else:
                if u0 < self.W / 2:
                    r = (u0 - 0.01, u0 + depth, v0 - 0.1, v1 + 0.1)
                else:
                    r = (u1 - depth, u1 + 0.01, v0 - 0.1, v1 + 0.1)
                plate = [(v0 - 0.75, v0 - 0.05), (v1 + 0.05, v1 + 0.75)]
                wall_axis, wall_c = "u", (u0 + u1) / 2
            self.busy.append(r)
            self.openings.append((r, zb, zt))
            if kind == "lift":                # landing portal, indicator, call panel, sign and rules
                lo_, hi_ = (u0, u1) if abs(u1 - u0) > abs(v1 - v0) else (v0, v1)
                self.wall_items.append((wall_axis, wall_c, lo_ - 0.8, hi_ + 0.45, 0.0, 2.75))
            if kind not in ("window", "port", "counter", "lift") and g.door.sign:
                for (p0_, p1_) in plate:     # possible door-plate positions at 1.40-1.60 m
                    self.wall_items.append((wall_axis, wall_c, p0_, p1_, 1.32, 1.68))
            side = self._side_of(u0, u1, v0, v1)
            t0, t1 = (u0, u1) if abs(u1 - u0) > abs(v1 - v0) else (v0, v1)
            self.doors_local.append((side, t0, t1, kind, r))
        # radiator strip under windows (no wall item over the whole window height)
        for wi, e in lay.win_room.items():
            if e.room is self.room:
                w = lay.windows[wi]
                pa = (w.s - w.hw, w.face) if w.axis == "x" else (w.face, w.s - w.hw)
                pb = (w.s + w.hw, w.face) if w.axis == "x" else (w.face, w.s + w.hw)
                a, b = self.w2l(*pa), self.w2l(*pb)
                u0, u1 = min(a[0], b[0]), max(a[0], b[0])
                v0, v1 = min(a[1], b[1]), max(a[1], b[1])
                if abs(u1 - u0) >= abs(v1 - v0):
                    r = (u0, u1, v0 - 0.01, v0 + 0.17) if v0 < self.D / 2 else (u0, u1, v1 - 0.17, v1)
                    t0, t1 = u0, u1
                else:
                    r = (u0 - 0.01, u0 + 0.17, v0, v1) if u0 < self.W / 2 else (u1 - 0.17, u1, v0, v1)
                    t0, t1 = v0, v1
                self.busy.append(r)
                wide = (r[0] - 0.12, r[1] + 0.12, r[2], r[3]) if abs(u1 - u0) >= abs(v1 - v0) else (r[0], r[1], r[2] - 0.12, r[3] + 0.12)
                self.openings.append((wide, -1.0, 99.0))
                self.windows_local.append((self._side_of(u0, u1, v0, v1), t0, t1))

    def reserve_open_sides(self):
        """Boundaries where this room opens into another room without a wall (nursing alcove,
        club hall foyer, hall passage, hall/phyto-bar): nothing may stand or hang against them, and
        handrails stop there."""
        lay, me = self.B.lay, self.room
        for e in lay.edges[me.rid]:
            for qid, fs in lay.edges.items():
                q = lay.rooms[qid]
                if q is me or min(me.z0 + CEIL_H, q.z1) - max(me.z0, q.z0) < 0.5:
                    continue
                for f in fs:
                    if f.axis != e.axis or f.n != -e.n or abs(f.coord - e.coord) > 1e-6:
                        continue
                    s0, s1 = max(e.a, f.a), min(e.b, f.b)
                    if s1 - s0 < 0.05:
                        continue
                    c0, c1 = e.coord, e.coord - e.n * 0.12
                    p0, p1 = ((s0, c0), (s1, c1)) if e.axis == "x" else ((c0, s0), (c1, s1))
                    a, b = self.w2l(*p0), self.w2l(*p1)
                    r = (min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]), max(a[1], b[1]))
                    self.busy.append(r)
                    self.openings.append((r, -1.0, 99.0))

    def inside(self, r):
        pts = [(r[0], r[2]), (r[1], r[2]), (r[1], r[3]), (r[0], r[3]), ((r[0] + r[1]) / 2, (r[2] + r[3]) / 2)]
        return all(any(q[0] - 0.02 <= p[0] <= q[1] + 0.02 and q[2] - 0.02 <= p[1] <= q[3] + 0.02 for q in self.rects_local)
                   for p in pts)

    def point_in(self, u, v):
        return any(q[0] - 1e-4 <= u <= q[1] + 1e-4 and q[2] - 1e-4 <= v <= q[3] + 1e-4 for q in self.rects_local)

    def free(self, r):
        return all(min(r[1], b[1]) - max(r[0], b[0]) <= 0.01 or min(r[3], b[3]) - max(r[2], b[2]) <= 0.01
                   for b in self.busy)

    def _covers_wall_item(self, r, top, z):
        """Would a floor item with footprint r and height top (above z) hide a wall-hung item?"""
        for (ax, c, a, b, wz0, wz1) in self.wall_items:
            if wz0 > z + top + 0.03 or wz1 < z:
                continue
            if ax == "v":
                if min(abs(r[2] - c), abs(r[3] - c)) < 0.15 and _ov(r[0], r[1], a, b, 0.01):
                    return True
            else:
                if min(abs(r[0] - c), abs(r[1] - c)) < 0.15 and _ov(r[2], r[3], a, b, 0.01):
                    return True
        return False

    # ------------------------------------------------------------- objects
    def _place(self, key, u, v, facing, z, props=None):
        x, y = self.l2w(u, v)
        build = F.MODS[key][0]
        ob = self.B.lib.place(key, build, self.B.coll_for(self.room.rid), f"{key}_{self.room.rid.split('.')[1]}",
                              (x, y, self.z0 + z), self.rot(facing), self.B.room_empty[self.room.rid], props)
        tris = mod_info(key)[2]
        self.B.stats["Furniture"] = self.B.stats.get("Furniture", 0) + tris
        self.B.stats["furniture_items"] = self.B.stats.get("furniture_items", 0) + 1
        self.placed.append((ob, tris))
        return ob

    def begin(self):
        self._tx.append((len(self.busy), len(self.items), len(self.wall_items), len(self.placed)))

    def commit(self):
        self._tx.pop()

    def rollback(self):
        nb, ni, nw, npl = self._tx.pop()
        for ob, tris in self.placed[npl:]:
            self.B.lib.remove(ob)
            self.B.stats["Furniture"] -= tris
            self.B.stats["furniture_items"] -= 1
        del self.busy[nb:], self.items[ni:], self.wall_items[nw:], self.placed[npl:]
        alive = {id(ob) for ob, _ in self.placed}
        for it in self.items:
            it.kids = [k for k in it.kids if id(k[1]) in alive]

    def at(self, key, u, v, facing="+v", z=0.0, check=True, props=None, foot=None):
        """Floor (or raised) item with a centred footprint."""
        assert key not in F.WALL, key
        _, fw, fd = F.MODS[key]
        if foot:
            fw, fd = foot
        along_u = facing in ("+v", "-v")
        hw, hd = (fw / 2, fd / 2) if along_u else (fd / 2, fw / 2)
        r = (u - hw, u + hw, v - hd, v + hd)
        top = mod_info(key)[1]
        if check:
            why = "outside" if not self.inside(r) else ("busy" if not self.free(r) else (
                "covers" if self._covers_wall_item(r, top, z) else None))
            if why:
                self.fails.append((key, u, v, why))
                return None
            self.busy.append(r)
        ob = self._place(key, u, v, facing, z, props)
        self.items.append(Item(key, u, v, facing, z, r, top, ob))
        return ob

    def wall(self, side, t, key, z=0.0, gap=0.02, check=True, props=None):
        """Floor item standing against bbox wall side (W/B/L/R) at position t along it, facing the room."""
        _, fw, fd = F.MODS[key]
        if side == "W":
            return self.at(key, t, gap + fd / 2, "+v", z, check=check, props=props)
        if side == "B":
            return self.at(key, t, self.D - gap - fd / 2, "-v", z, check=check, props=props)
        if side == "L":
            return self.at(key, gap + fd / 2, t, "+u", z, check=check, props=props)
        return self.at(key, self.W - gap - fd / 2, t, "-u", z, check=check, props=props)

    def item_of(self, ob):
        for it in self.items:
            if it.ob is ob:
                return it
        return None

    def on_top(self, base, key, du=0.0, dv=0.0, facing=None, props=None):
        """Places key on the top surface of an already placed item (returns None if base is None)."""
        if base is None:
            return None
        it = self.item_of(base)
        if it is None:
            return None
        _, fw, fd = F.MODS[key]
        f = facing or it.facing
        along_u = f in ("+v", "-v")
        hw, hd = (fw / 2, fd / 2) if along_u else (fd / 2, fw / 2)
        u, v = it.u + du, it.v + dv
        r = (u - hw, u + hw, v - hd, v + hd)
        b = it.rect
        if r[0] < b[0] - 0.01 or r[1] > b[1] + 0.01 or r[2] < b[2] - 0.01 or r[3] > b[3] + 0.01:
            return None
        for (k, _) in it.kids:
            if _ov(r[0], r[1], k[0], k[1]) and _ov(r[2], r[3], k[2], k[3]):
                return None
        ob = self._place(key, u, v, f, it.z + it.top, props)
        it.kids.append((r, ob))
        return ob

    # ---------------------------------------------------------- wall items
    def mount(self, u, v, facing, key, z, check=True, props=None):
        """Wall-hung item with its back on the wall plane through (u, v), facing into the room."""
        assert key in F.WALL, key
        _, fw, fd = F.MODS[key]
        zmin, zmax, _ = mod_info(key)
        za, zb = z + zmin, z + zmax
        n = {"+u": (1, 0), "-u": (-1, 0), "+v": (0, 1), "-v": (0, -1)}[facing]
        if facing in ("+v", "-v"):
            axis, c, a, b = "v", v, u - fw / 2, u + fw / 2
            strip = (a, b, v - 0.05, v + 0.05)
            dd = max(fd, 0.12)
            front = (a, b, min(v, v + n[1] * dd), max(v, v + n[1] * dd))
            probes = [(t, v) for t in (a + 0.02, (a + b) / 2, b - 0.02)]
        else:
            axis, c, a, b = "u", u, v - fw / 2, v + fw / 2
            strip = (u - 0.05, u + 0.05, a, b)
            dd = max(fd, 0.12)
            front = (min(u, u + n[0] * dd), max(u, u + n[0] * dd), a, b)
            probes = [(u, t) for t in (a + 0.02, (a + b) / 2, b - 0.02)]
        if check:
            # a real wall: inside just in front, outside just behind
            for (pu, pv) in probes:
                if not self.point_in(pu + n[0] * 0.03, pv + n[1] * 0.03) or self.point_in(pu - n[0] * 0.03, pv - n[1] * 0.03):
                    self.fails.append((key, u, v, "nowall"))
                    return None
            for (orc, oz0, oz1) in self.openings:
                if _ov(strip[0], strip[1], orc[0], orc[1], 0.005) and _ov(strip[2], strip[3], orc[2], orc[3], 0.005) \
                        and _ov(za, zb, oz0, oz1):
                    self.fails.append((key, u, v, "opening"))
                    return None
            for (ax2, c2, a2, b2, z02, z12) in self.wall_items:
                if ax2 == axis and abs(c2 - c) < 0.08 and _ov(a - WALL_GAP, b + WALL_GAP, a2, b2) \
                        and _ov(za - 0.06, zb + 0.06, z02, z12):
                    self.fails.append((key, u, v, "wallitem"))
                    return None
            for it in self.items:
                if it.top + it.z > za + 0.01 and it.z < zb:
                    r = it.rect
                    if _ov(front[0] - 0.01, front[1] + 0.01, r[0], r[1]) and _ov(front[2] - 0.01, front[3] + 0.01, r[2], r[3]):
                        self.fails.append((key, u, v, "behind:" + it.key))
                        return None
        self.wall_items.append((axis, c, a, b, za, zb))
        return self._place(key, u, v, facing, z, props)

    def hang(self, side, t, key, z, check=True):
        """Wall item on a bbox wall: W/B/L/R at position t along it."""
        if side == "W":
            return self.mount(t, 0.0, "+v", key, z, check)
        if side == "B":
            return self.mount(t, self.D, "-v", key, z, check)
        if side == "L":
            return self.mount(0.0, t, "+u", key, z, check)
        return self.mount(self.W, t, "-u", key, z, check)

    def hang_any(self, key, z, tries):
        """First successful hang from [(side, t), ...]."""
        for side, t in tries:
            ob = self.hang(side, t, key, z)
            if ob is not None:
                return ob
        return None

    def decorate(self, keys, z, sides=("L", "R", "B"), spots=(0.5, 0.3, 0.7, 0.2, 0.8, 0.4, 0.6)):
        """Hang each key on the first free spot, spreading over the given walls."""
        out = []
        for i, k in enumerate(keys):
            ok = None
            for j in range(len(sides)):
                side = sides[(i + j) % len(sides)]
                span = self.W if side in ("W", "B") else self.D
                for f in spots:
                    ok = self.hang(side, span * f, k, z)
                    if ok:
                        break
                if ok:
                    break
            out.append(ok)
        return out

    # ------------------------------------------------------------ helpers
    def door_on(self, side):
        return [d for d in self.doors_local if d[0] == side and d[3] not in ("window", "port", "counter")]

    def switch(self):
        """Light switch beside the room's main door (inside, at 0.95 m) and a socket."""
        for (side, t0, t1, kind, r) in self.doors_local:
            if kind in ("window", "port", "counter", "lift"):
                continue
            tries = [(side, t) for t in (t1 + 0.18, t0 - 0.18, t1 + 0.35, t0 - 0.35)]
            pts = []
            if side in ("W", "B"):       # passage doors: on the side walls of the passage
                vv = 0.3 if side == "W" else self.D - 0.3
                for q in self.rects_local:
                    if q[2] - 0.01 <= vv <= q[3] + 0.01:
                        pts += [(q[0], vv, "+u"), (q[1], vv, "-u")]
            else:
                uu = 0.3 if side == "L" else self.W - 0.3
                for q in self.rects_local:
                    if q[0] - 0.01 <= uu <= q[1] + 0.01:
                        pts += [(uu, q[2], "+v"), (uu, q[3], "-v")]
            ok = any(self.hang(sd, t, "light_switch", 0.95) for sd, t in tries)
            if not ok:
                for (pu, pv, f) in pts:
                    if self.mount(pu, pv, f, "light_switch", 0.95):
                        break
            break
        nf = len(self.fails)
        done = False
        for side in ("L", "R", "B", "W"):
            span = self.W if side in ("W", "B") else self.D
            for f in (0.5, 0.35, 0.65, 0.2, 0.8, 0.1, 0.9):
                if self.hang(side, span * f, "socket", 0.3):
                    done = True
                    break
            if done:
                break
        del self.fails[nf:]

    def handrails(self, sides=("W", "B"), z=0.9, ends=0.15):
        """Continuous wooden handrails along long walls, interrupted only at doors, pilasters,
        radiators, seating and wall equipment. Built as one merged mesh per room."""
        from .meshkit import MB
        mb = MB(f"Handrails_{self.room.rid.replace('.', '_')}")
        for side in sides:
            span = self.W if side in ("W", "B") else self.D
            vc = 0.0 if side in ("W", "L") else (self.D if side == "B" else self.W)
            blocks = []
            for (orc, oz0, oz1) in self.openings:
                lo, hi = (orc[0], orc[1]) if side in ("W", "B") else (orc[2], orc[3])
                near = (orc[2], orc[3]) if side in ("W", "B") else (orc[0], orc[1])
                if near[0] - 0.2 < vc < near[1] + 0.2 and oz0 < z + 0.05:
                    blocks.append((lo - 0.05, hi + 0.05))
            for it in self.items:
                r = it.rect
                lo, hi = (r[0], r[1]) if side in ("W", "B") else (r[2], r[3])
                near = (r[2], r[3]) if side in ("W", "B") else (r[0], r[1])
                if min(abs(near[0] - vc), abs(near[1] - vc)) < 0.2 and it.top + it.z > z - 0.15:
                    blocks.append((lo - 0.1, hi + 0.1))
            ax = "v" if side in ("W", "B") else "u"
            for (ax2, c2, a2, b2, z02, z12) in self.wall_items:
                if ax2 == ax and abs(c2 - vc) < 0.08 and z02 < z + 0.08 and z12 > z - 0.08:
                    blocks.append((a2 - 0.08, b2 + 0.08))
            blocks.sort()
            cur, segs = ends, []
            for (a, b) in blocks:
                if a > cur:
                    segs.append((cur, a))
                cur = max(cur, b)
            if span - ends > cur:
                segs.append((cur, span - ends))
            for (a, b) in segs:
                if b - a < 0.8:
                    continue
                inward = {"W": (0, 1), "B": (0, -1), "L": (1, 0), "R": (-1, 0)}[side]

                def P(t, off):
                    uu, vv = (t, vc) if side in ("W", "B") else (vc, t)
                    x, y = self.l2w(uu + inward[0] * off, vv + inward[1] * off)
                    return (x, y, self.z0 + z)
                mb.tube_region([P(a, 0.0), P(a, 0.075), P(b, 0.075), P(b, 0.0)], 0.022, "wood_dark", 6)
                n = max(2, int((b - a) / 1.2) + 1)
                for k in range(n):
                    t = a + 0.2 + (b - a - 0.4) * k / (n - 1)
                    p0, p1 = P(t, 0.0), P(t, 0.07)
                    mb.tube_region([(p0[0], p0[1], p0[2] - 0.06), (p1[0], p1[1], p1[2] - 0.03)], 0.008, "brass", 4)
                self.wall_items.append((ax, vc, a, b, z - 0.05, z + 0.05))
        if not mb.empty():
            self.B.add(mb, self.room.rid, name=mb.name, group="Furniture",
                       props={"handrail": True, "height_m": z})


def place_radiators_and_curtains(B):
    """Cast-iron radiator on the floor under every exterior window of a heated room; curtains in
    rooms that have them. Windows high above the floor of tall rooms (upper row of the club hall)
    get no radiator; the hall's lower windows get one standing on the hall floor."""
    lay = B.lay
    curtain_kinds = {"suite_double", "suite_single", "suite_assisted", "director", "admin_office", "gp", "consult",
                     "nurse_office", "lounge", "doctor_duty", "staff_office", "nurse_office_floor", "staff_dining",
                     "dining", "registration", "info", "guard", "library", "phytobar", "massage", "physio",
                     "salt_room", "lfk", "club_hall", "hall", "foyer", "exam", "med_reg", "housekeeping",
                     "kitchen_changing", "med_changing", "staff_changing", "janitor"}
    tulle_only = {"hydro", "wc_men", "wc_women", "wc_shower_m", "wc_shower_f", "access_bath", "treatment",
                  "treatment_small", "first_aid", "lab", "blood", "kitchen", "food_prep", "veg_prep", "distribution",
                  "dishwash"}
    no_radiator = {"shaft", "dry_store", "fridge"}
    for i, rad in enumerate(B.radiators):
        w = rad["win"]
        e = rad["edge"]
        room = e.room
        if room.kind in no_radiator:
            continue
        inward = -e.n
        if w.axis == "x":
            x, y = w.s, w.face + inward * 0.07
        else:
            x, y = w.face + inward * 0.07, w.s
        facing = (0, inward) if w.axis == "x" else (inward, 0)
        rot = math.atan2(facing[1], facing[0]) + math.pi / 2
        if room.kind.startswith("stair"):
            floor = w.z0 - (STD_Z0 + WIN_BASE)          # storey landing under the window
        else:
            floor = room.z0
            if room.kind == "club_hall" and y < ENT_IY0 + 3.25:
                floor += 0.6                            # stands on the stage, not inside it
        if w.z0 - floor > 2.2:
            continue                                    # high window: no radiator floating on the wall
        key = "radiator_hall" if w.kind == "hall" else "radiator"
        build, _, _ = F.MODS[key]
        B.lib.place(key, build, B.coll_for(room.rid), f"Radiator_{room.rid.split('.')[1]}", (x, y, floor), rot,
                    B.room_empty[room.rid])
        B.stats["Radiators"] = B.stats.get("Radiators", 0) + mod_info(key)[2]
        if w.kind == "std" and (room.kind in curtain_kinds or room.kind in tulle_only):
            cx, cy = (w.s, w.face + inward * 0.10) if w.axis == "x" else (w.face + inward * 0.10, w.s)
            ck = "curtains" if room.kind in curtain_kinds else "curtains_tulle"
            build, _, _ = F.MODS[ck]
            B.lib.place(ck, build, B.coll_for(room.rid), f"Curtains_{room.rid.split('.')[1]}", (cx, cy, w.z0 - 0.02),
                        rot, B.room_empty[room.rid])
            B.stats["Furniture"] = B.stats.get("Furniture", 0) + mod_info(ck)[2]
