"""Room-local placement frame and clearance checks for furnishing.

Local frame of a room: v = 0 at the window wall, v grows into the room; u runs along the
window wall to the right of a viewer facing the window. Walls: W (window), B (back),
L (left, u=0), R (right, u=W). Modules face local -Y; `facing` gives the room direction
the module's front points to."""
import math
from .params import *
from . import doors as D
from . import furniture as F

EPS = 1e-6


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
        self.busy = []
        self.openings = []
        self.reserve_openings()
        n0 = len(self.busy)
        if room.kind.startswith(("corridor", "service_corridor")):
            from .layout import COLUMNS_X
            for x in COLUMNS_X:
                for (ya, yb) in ((CORR_Y0, CORR_Y0 + COLUMN - CORR_T), (CORR_Y1 - COLUMN + CORR_T, CORR_Y1)):
                    a, b = self.w2l(x - COLUMN / 2 - 0.05, ya), self.w2l(x + COLUMN / 2 + 0.05, yb)
                    self.busy.append((min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]), max(a[1], b[1])))
        self.openings = list(self.busy)

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
        if isinstance(facing, (int, float)):
            return (math.cos(facing), math.sin(facing))
        du, dv = {"+u": (1, 0), "-u": (-1, 0), "+v": (0, 1), "-v": (0, -1)}[facing]
        return (du * self.U[0] + dv * self.V[0], du * self.U[1] + dv * self.V[1])

    def rot(self, facing):
        fx, fy = self.dir_world(facing)
        return math.atan2(fy, fx) + math.pi / 2

    # ------------------------------------------------------------ clearances
    def reserve_openings(self):
        lay = self.B.lay
        for g in lay.doors:
            mine_a = g.door.a == self.room.rid
            mine_b = g.door.b == self.room.rid
            if not (mine_a or mine_b):
                continue
            if g.door.level != self.room.level and not self.room.kind.startswith("stair"):
                pass
            if self.room.z1 - self.room.z0 > CEIL_H + 0.1 and abs(g.z0 - self.z0) > 1.0:
                continue
            face = g.fa if mine_a else g.fb
            p0 = (g.c - g.ow / 2, face) if g.axis == "x" else (face, g.c - g.ow / 2)
            p1 = (g.c + g.ow / 2, face) if g.axis == "x" else (face, g.c + g.ow / 2)
            a, b = self.w2l(*p0), self.w2l(*p1)
            depth = {"counter": 0.7, "window": 0.5, "port": 0.6}.get(g.door.kind, max(g.ow, 0.9) + 0.15)
            u0, u1 = min(a[0], b[0]), max(a[0], b[0])
            v0, v1 = min(a[1], b[1]), max(a[1], b[1])
            if abs(u1 - u0) > abs(v1 - v0):     # opening along u
                if v0 < self.D / 2:
                    self.busy.append((u0 - 0.1, u1 + 0.1, v0 - 0.01, v0 + depth))
                else:
                    self.busy.append((u0 - 0.1, u1 + 0.1, v1 - depth, v1 + 0.01))
            else:
                if u0 < self.W / 2:
                    self.busy.append((u0 - 0.01, u0 + depth, v0 - 0.1, v1 + 0.1))
                else:
                    self.busy.append((u1 - depth, u1 + 0.01, v0 - 0.1, v1 + 0.1))
        # radiator strip under windows
        for wi, e in lay.win_room.items():
            if e.room is self.room:
                w = lay.windows[wi]
                pa = (w.s - w.hw, w.face) if w.axis == "x" else (w.face, w.s - w.hw)
                pb = (w.s + w.hw, w.face) if w.axis == "x" else (w.face, w.s + w.hw)
                a, b = self.w2l(*pa), self.w2l(*pb)
                u0, u1 = min(a[0], b[0]), max(a[0], b[0])
                v0, v1 = min(a[1], b[1]), max(a[1], b[1])
                if abs(u1 - u0) >= abs(v1 - v0):
                    self.busy.append((u0, u1, v0 - 0.01, v0 + 0.17) if v0 < self.D / 2 else (u0, u1, v1 - 0.17, v1))
                else:
                    self.busy.append((u0 - 0.01, u0 + 0.17, v0, v1) if u0 < self.W / 2 else (u1 - 0.17, u1, v0, v1))

    def inside(self, r):
        # every corner must be inside one of the room rects (rect union containment, good enough for L shapes)
        pts = [(r[0], r[2]), (r[1], r[2]), (r[1], r[3]), (r[0], r[3]), ((r[0] + r[1]) / 2, (r[2] + r[3]) / 2)]
        return all(any(q[0] - 0.02 <= p[0] <= q[1] + 0.02 and q[2] - 0.02 <= p[1] <= q[3] + 0.02 for q in self.rects_local)
                   for p in pts)

    def free(self, r):
        return all(min(r[1], b[1]) - max(r[0], b[0]) <= 0.01 or min(r[3], b[3]) - max(r[2], b[2]) <= 0.01
                   for b in self.busy)

    # ------------------------------------------------------------- placing
    def at(self, key, u, v, facing="+v", z=0.0, foot=None, check=True, props=None, tilt=None):
        build, fw, fd = F.MODS[key]
        if foot:
            fw, fd = foot
        along_u = facing in ("+v", "-v")
        hw, hd = (fw / 2, fd / 2) if along_u else (fd / 2, fw / 2)
        r = (u - hw, u + hw, v - hd, v + hd)
        if check:
            if not self.inside(r) or not self.free(r):
                return None
            self.busy.append(r)
        x, y = self.l2w(u, v)
        ob = self.B.lib.place(key, build, self.B.coll_for(self.room.rid), f"{key}_{self.room.rid.split('.')[1]}",
                              (x, y, self.z0 + z), self.rot(facing), self.B.room_empty[self.room.rid], props)
        if tilt:
            ob.rotation_euler[0] = tilt[0]
            ob.rotation_euler[1] = tilt[1]
        self.B.stats["Furniture"] = self.B.stats.get("Furniture", 0) + self.B.lib.meshes[key][1]
        self.B.stats["furniture_items"] = self.B.stats.get("furniture_items", 0) + 1
        return ob

    def wall(self, side, t, key, z=0.0, gap=0.02, check=True, props=None):
        """Against wall side (W/B/L/R) at position t along it, facing into the room."""
        build, fw, fd = F.MODS[key]
        if side == "W":
            return self.at(key, t, gap + fd / 2, "+v", z, check=check, props=props)
        if side == "B":
            return self.at(key, t, self.D - gap - fd / 2, "-v", z, check=check, props=props)
        if side == "L":
            return self.at(key, gap + fd / 2, t, "+u", z, check=check, props=props)
        return self.at(key, self.W - gap - fd / 2, t, "-u", z, check=check, props=props)

    def hang(self, side, t, key, z, w=None):
        """Wall-hung flat item (poster, clock...) at height z, checked against openings on that wall."""
        build, fw, fd = F.MODS[key]
        half = (w or fw) / 2
        if side in ("W", "B"):
            r = (t - half, t + half, (0 if side == "W" else self.D) - 0.05, (0 if side == "W" else self.D) + 0.05)
        else:
            r = ((0 if side == "L" else self.W) - 0.05, (0 if side == "L" else self.W) + 0.05, t - half, t + half)
        if not self.free_wall(r, z):
            return None
        return self.wall(side, t, key, z, gap=0.0, check=False)

    def free_wall(self, r, z):
        for b in self.openings:
            if min(r[1], b[1]) - max(r[0], b[0]) > 0.01 and min(r[3], b[3]) - max(r[2], b[2]) > 0.01:
                return False
        return True


def place_radiators_and_curtains(B):
    """Cast-iron radiator under every exterior window; curtains in rooms that would have had them."""
    from .lighting import PLAFOND_KINDS
    lay = B.lay
    curtain_kinds = {"patient_single", "patient_double", "patient_assisted", "director", "deputy", "chief_admin",
                     "accountant", "hr", "admin_office", "meeting", "head_nurse", "staff_room", "secretary", "gp",
                     "consult", "nurse_office", "lounge", "doctor_duty", "staff_office", "nurse_office_floor",
                     "staff_dining", "dining", "registration", "info", "guard"}
    for rad in B.radiators:
        w = rad["win"]
        e = rad["edge"]
        room = e.room
        if room.kind == "shaft":
            continue
        inward = -e.n
        if w.axis == "x":
            x, y = w.s, w.face + inward * 0.07
            facing = (0, inward)
        else:
            x, y = w.face + inward * 0.07, w.s
            facing = (inward, 0)
        rot = math.atan2(facing[1], facing[0]) + math.pi / 2
        floor = w.z0 - (STD_Z0 + WIN_BASE) if w.kind == "std" else LEVELS[1]
        key = "radiator_hall" if w.kind == "hall" else "radiator"
        build, _, _ = F.MODS[key]
        B.lib.place(key, build, B.coll_for(room.rid), f"Radiator_{room.rid.split('.')[1]}", (x, y, floor), rot,
                    B.room_empty[room.rid])
        B.stats["Radiators"] = B.stats.get("Radiators", 0) + B.lib.meshes[key][1]
        if room.kind in curtain_kinds and w.kind == "std":
            cx, cy = (w.s, w.face + inward * 0.10) if w.axis == "x" else (w.face + inward * 0.10, w.s)
            ck = "curtains" if (hash(room.rid) % 5) else "curtains_tulle"
            build, _, _ = F.MODS[ck]
            B.lib.place(ck, build, B.coll_for(room.rid), f"Curtains_{room.rid.split('.')[1]}", (cx, cy, w.z0 - 0.02),
                        rot, B.room_empty[room.rid])
            B.stats["Furniture"] = B.stats.get("Furniture", 0) + B.lib.meshes[ck][1]
