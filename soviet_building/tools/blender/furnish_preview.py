"""Dry run of the furnishing (no Blender scene): runs every room recipe against the plan and draws the
footprints of all placed items, wall-hung items and handrails over the floor plans, plus a list of
the placements that were rejected by the clearance checks.

    python furnish_preview.py --out ../../work/furn [--zoom x0,x1,y0,y1,level ...]
"""
import argparse
import math
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from sanatorium.params import *  # noqa: E402
from sanatorium.plan import build_plan  # noqa: E402
from sanatorium.layout import Layout  # noqa: E402
from sanatorium import furnish, furniture as F  # noqa: E402
from sanatorium.furnish_core import mod_info  # noqa: E402
from sanatorium.meshkit import MB  # noqa: E402


class Rec:
    def __init__(self, key, loc, rot, room):
        self.key, self.loc, self.rot, self.room = key, loc, rot, room


class FakeLib:
    def __init__(self):
        self.objs = []

    def place(self, key, build, coll, name, loc, rot_z=0.0, parent=None, props=None, scale=None):
        r = Rec(key, loc, rot_z, parent)
        self.objs.append(r)
        return r

    def remove(self, ob):
        self.objs.remove(ob)


class FakeB:
    def __init__(self):
        from sanatorium import architecture
        self.plan = build_plan()
        self.lay = Layout(self.plan)
        assert not self.lay.validate()
        self.lib = FakeLib()
        self.stats = {}
        self.room_empty = {rid: rid for rid in self.plan.rooms}
        self.meshes = []
        self.radiators = architecture.window_parts(self.lay, MB("r"), MB("s"))

    def coll_for(self, rid):
        return None

    def add(self, mb, rid=None, level=None, name=None, props=None, group="Architecture"):
        self.meshes.append((rid, mb))
        self.stats[group] = self.stats.get(group, 0) + mb.tris()


def footprint(key, loc, rot):
    _, w, d = F.MODS[key]
    if key in F.WALL:
        pts = [(-w / 2, 0), (w / 2, 0), (w / 2, -d), (-w / 2, -d)]
    else:
        pts = [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)]
    c, s = math.cos(rot), math.sin(rot)
    return [(loc[0] + x * c - y * s, loc[1] + x * s + y * c) for x, y in pts]


def level_of(B, rec):
    return B.plan.rooms[rec.room].level if rec.room in B.plan.rooms else 0


def draw(B, lvl, path, box=None, S=30):
    from sanatorium.drawplan import draw_level
    tmp = path + ".base.png"
    draw_level(B.lay, lvl, tmp, S=S, title=f"furniture preview, floor {lvl + 1}")
    im = Image.open(tmp).convert("RGB")
    os.remove(tmp)
    d = ImageDraw.Draw(im)
    X0, Y1 = -1.5, MAIN_DEPTH + 1.5
    P = lambda x, y: ((x - X0) * S, (Y1 - y) * S + 60)
    f = ImageFont.truetype("/usr/share/fonts/google-noto-vf/NotoSans[wght].ttf", max(7, S // 4))
    zlo, zhi = LEVELS[lvl] - 0.1, LEVELS[lvl] + 3.2
    for r in B.lib.objs:
        room = B.plan.rooms.get(r.room)
        if room is None or not (zlo <= r.loc[2] <= zhi or (room.level == lvl and room.kind.startswith("stair") is False)):
            if not (zlo <= r.loc[2] <= zhi):
                continue
        if r.key not in F.MODS:
            continue
        pts = [P(*p) for p in footprint(r.key, r.loc, r.rot)]
        if r.key in F.WALL:
            col = (200, 30, 30)
        elif r.key in F.ON_TOP:
            col = (30, 120, 30)
        elif r.key.startswith(("radiator", "curtains")):
            col = (120, 120, 120)
        else:
            col = (30, 60, 160)
        d.polygon(pts, outline=col)
        if S >= 60 and r.key not in F.WALL and not r.key.startswith(("radiator", "curtains")):
            cx = sum(p[0] for p in pts) / 4
            cy = sum(p[1] for p in pts) / 4
            d.text((cx, cy), r.key[:12], font=f, fill=col, anchor="mm")
    for rid, mb in B.meshes:
        if B.plan.rooms[rid].level != lvl:
            continue
        for fc in mb.f:
            q = [mb.v[i] for i in fc]
            if zlo <= q[0][2] <= zhi:
                d.line([P(p[0], p[1]) for p in q] + [P(q[0][0], q[0][1])], fill=(150, 90, 20))
    if box:
        x0, x1, y0, y1 = box
        a, b = P(x0, y1), P(x1, y0)
        im = im.crop((int(a[0]), int(a[1]), int(b[0]), int(b[1])))
    im.save(path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--zoom", nargs="*", default=[])
    ap.add_argument("--fails", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    B = FakeB()
    furnish.furnish_all(B)
    print({k: v for k, v in B.stats.items()})
    cnt = Counter(r.key for r in B.lib.objs)
    print("items:", len(B.lib.objs), "distinct:", len(cnt))
    if a.fails:
        for rid, c in B.ctx.items():
            if c.fails:
                print(rid, c.room.kind, [f"{k}@{u:.2f},{v:.2f}:{why}" for (k, u, v, why) in c.fails])
    for lvl in range(4):
        draw(B, lvl, os.path.join(a.out, f"f{lvl + 1}.png"))
    for i, z in enumerate(a.zoom):
        x0, x1, y0, y1, lv = [float(t) for t in z.split(",")]
        draw(B, int(lv), os.path.join(a.out, f"zoom{i}.png"), (x0, x1, y0, y1), S=90)
