"""Level description for the Godot game (soviet_building/game), written next to the game GLB.

Everything is converted to Godot / glTF coordinates: Godot (x, y, z) = Blender (x, z, -y), metres,
Y up. Rotations about Blender Z become rotations about Godot Y with the same sign.

Contents: rooms, door leaves (hinge, closed yaw, swing sign, size, lock), lamp fixtures per room
(state on / flicker / broken), light switches, glowing lamp shades, furniture collision boxes,
stair blockers (an electric wheelchair cannot use stairs), the elevator (cabin, door leaves, buttons),
spawn point, and free floor points for rats and cockroaches."""
import json
import math
import random
from .params import *
from .stairs_layout import stair_frame, stair_spec, CELL_U
from . import furniture as F

NO_COLLIDE = {"rug", "rug_small", "rug_big", "runner", "gym_mat", "rubber_mat", "bath_mat", "curtain_rail",
              "curtain_rail_s", "stage_curtain", "duct", "hatch", "dust_patch", "leaves_dry", "papers_floor",
              "stain_small", "cobweb_r", "cobweb_l", "papers_desk", "paper_stack"}
LOCKED_KINDS = {"electrical", "machine_room", "plumbing", "ventilation", "med_supplies", "med_equip", "waste",
                "projection", "fridge"}
RAT_KINDS = ("corridor", "corridor_patient", "service_corridor", "dining", "kitchen", "dry_store", "storage",
             "clean_linen", "dirty_linen", "waste", "hall_store", "workshop", "lounge", "club_hall", "luggage")
ROACH_KINDS = ("kitchen", "dishwash", "food_prep", "veg_prep", "distribution", "wc_men", "wc_women", "wc_shower_m",
               "wc_shower_f", "staff_wc", "dirty_linen", "waste", "staff_dining", "suite_bath", "phytobar")


def G(p):
    x, y, z = p
    return [round(x, 4), round(z, 4), round(-y, 4)]


def G2(x, y):
    return [round(x, 4), round(-y, 4)]


def _room_boxes(B, rid):
    """World AABBs (x0, x1, y0, y1, z0, z1) of the floor items of a room."""
    c = B.ctx.get(rid)
    out = []
    if c is None:
        return out
    for it in c.items:
        if it.key in NO_COLLIDE or it.top < 0.12:
            continue
        a, b = c.l2w(it.rect[0], it.rect[2]), c.l2w(it.rect[1], it.rect[3])
        z0 = c.z0 + it.z
        out.append((min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]), max(a[1], b[1]), z0, z0 + it.top, it.key))
    return out


def _stair_blockers(B):
    """Invisible walls where the flights start on every storey landing and along the lobby railing over
    the stair well (upper storeys)."""
    sp = stair_spec()
    vB1 = sp["flights"][1]["v"][1]
    L = STAIR_LANDING
    out = []
    for key in ("STAIR1", "STAIR2", "STAIR3"):
        r = B.plan.rooms["L0." + key]
        f = stair_frame(r)
        for i, z in enumerate(LEVELS):
            boxes = [(L - 0.06, L, 0.0, vB1)]
            if i > 0:
                boxes.append((L, CELL_U, vB1, vB1 + 0.08))
            for (u0, u1, v0, v1) in boxes:
                a, b = f(u0, v0), f(u1, v1)
                out.append({"min": G((min(a[0], b[0]), max(a[1], b[1]), z)),
                            "max": G((max(a[0], b[0]), min(a[1], b[1]), z + 1.6)), "kind": "stairs"})
    return out


def _free_points(B, rid, step=0.35, margin=0.18):
    room = B.plan.rooms[rid]
    boxes = _room_boxes(B, rid)
    c = B.ctx.get(rid)
    pts = []
    for (x0, x1, y0, y1) in room.rects:
        x = x0 + margin
        while x < x1 - margin:
            y = y0 + margin
            while y < y1 - margin:
                ok = all(not (bx0 - margin < x < bx1 + margin and by0 - margin < y < by1 + margin)
                         for (bx0, bx1, by0, by1, bz0, bz1, k) in boxes if bz0 < room.z0 + 0.3)
                if ok and c is not None:
                    u, v = c.w2l(x, y)
                    ok = c.free((u - 0.05, u + 0.05, v - 0.05, v + 0.05))
                if ok:
                    pts.append(G2(x, y))
                y += step
            x += step
    return pts


def export_level(B, path):
    lay, plan = B.lay, B.plan
    rng = random.Random(1976)
    rooms = []
    for r in plan.rooms.values():
        rooms.append({"id": r.rid, "num": r.num, "name": r.ru, "kind": r.kind, "dept": r.dept, "level": r.level,
                      "floor_y": round(r.z0, 3), "ceil_y": round(r.z1, 3),
                      "rects": [[round(x0, 3), round(x1, 3), round(-y1, 3), round(-y0, 3)] for (x0, x1, y0, y1) in r.rects]})
    doors = []
    for d in B.game_doors:
        a = plan.rooms.get(d["a"])
        b = plan.rooms.get(d["b"]) if d["b"] != "EXT" else None
        locked = d["ext"] or (d["kind"] == "metal" and ((a and a.kind in LOCKED_KINDS) or (b and b.kind in LOCKED_KINDS)))
        hs, w, h, t = d["hinge_sign"], d["width"], d["height"], d["thick"]
        doors.append({"name": d["name"], "group": d["door"], "hinge": G(d["hinge"]), "yaw": round(d["rot"], 5),
                      "open_sign": d["open_sign"], "width": round(w, 4), "height": round(h, 4), "thick": t,
                      "box_center": [round(hs * w / 2, 4), round(h / 2, 4), round(-t / 2, 4)],
                      "box_size": [round(w, 4), round(h, 4), t], "style": d["style"], "kind": d["kind"],
                      "level": d["level"], "a": d["a"], "b": d["b"], "locked": bool(locked), "ext": d["ext"],
                      "max_angle": 100.0 if not d["double"] else 95.0})
    fixtures = []
    for fx in B.game_fixtures:
        fixtures.append({"name": fx["name"], "room": fx["room"], "kind": fx["kind"], "state": fx["state"],
                         "energy": round(fx["energy"], 2), "color": [round(c, 3) for c in fx["color"]],
                         "pos": G(fx["pos"])})
    glows, switches = [], []
    for it in B.game_items:
        if it["key"] == "table_lamp":
            glows.append({"name": it["name"], "room": it["room"]})
        elif it["key"] == "light_switch":
            rot = it["rot"]
            fxw, fyw = math.sin(rot), -math.cos(rot)       # module front (-Y) in world
            x, y, z = it["pos"]
            switches.append({"room": it["room"], "pos": G((x + fxw * 0.01, y + fyw * 0.01, z + 0.06)),
                             "normal": [round(fxw, 4), 0.0, round(-fyw, 4)]})
    boxes = []
    for r in plan.rooms.values():
        for (x0, x1, y0, y1, z0, z1, key) in _room_boxes(B, r.rid):
            boxes.append({"min": G((x0, y1, z0)), "max": G((x1, y0, z1)), "key": key, "room": r.rid})
    rboxes = []
    for gb in B.game_boxes:
        cx, cy, cz = gb["center"]
        rboxes.append({"center": G((cx, cy, cz)), "size": [gb["size"][0], gb["size"][2], gb["size"][1]],
                       "yaw": round(gb["rot"], 5), "key": gb["key"], "room": gb["room"]})
    lift = None
    if B.game_lift:
        L = B.game_lift
        cab = L["cab"]

        def gbox(b):
            x0, x1, y0, y1, z0, z1 = b
            return {"min": G((x0, y1, z0)), "max": G((x1, y0, z1))}
        lift = {"cabin": L["cabin"], "levels": [round(z, 3) for z in LEVELS], "parked": 0,
                "inner": gbox((cab["x0"], cab["x1"], cab["y0"], cab["y1"], FFL, FFL + cab["h"])),
                "wall_t": 0.05, "door_w": L["door_w"], "door_h": L["door_h"], "door_x": L["door_x"],
                "front_y": round(-(cab["y1"]), 4), "light": G(L["light"]),
                "buttons": {k: G(v) for k, v in L["cab_buttons"].items()},
                "cab_doors": [dict(gbox(d["box"]), name=d["name"], dir=d["dir"], open=d["open"]) for d in L["cab_doors"]],
                "landings": [{"level": ld["level"], "button": G(ld["button"]),
                              "doors": [dict(gbox(d["box"]), name=d["name"], dir=d["dir"], open=d["open"])
                                        for d in ld["doors"]]} for ld in L["landings"]]}
    critters = {"rats": [], "roaches": []}
    for r in plan.rooms.values():
        if r.kind in RAT_KINDS or r.kind in ROACH_KINDS:
            pts = _free_points(B, r.rid)
            if len(pts) < 6:
                continue
            if r.kind in RAT_KINDS:
                critters["rats"].append({"room": r.rid, "level": r.level, "floor_y": round(r.z0, 3), "points": pts})
            if r.kind in ROACH_KINDS:
                critters["roaches"].append({"room": r.rid, "level": r.level, "floor_y": round(r.z0, 3), "points": pts})
    data = {"version": 1, "coords": "Godot: x = Blender x, y = Blender z (up), z = -Blender y; metres",
            "spawn": {"pos": G((32.6, -10.8, FFL)), "yaw": 0.0}, "levels": [round(z, 3) for z in LEVELS],
            "rooms": rooms, "doors": doors, "fixtures": fixtures, "glows": glows, "switches": switches,
            "boxes": boxes, "rot_boxes": rboxes, "blockers": _stair_blockers(B), "lift": lift, "critters": critters}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    return {k: (len(v) if isinstance(v, list) else 1) for k, v in data.items() if k not in ("coords", "version")}
