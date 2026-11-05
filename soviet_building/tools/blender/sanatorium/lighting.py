"""Ceiling fixtures (glass plafonds, warm-white fluorescent battens in service rooms, bulbs in stores,
pendants in the club hall), one point light per fixture, extra warm light from floor lamps and wall
sconces, and soft daylight. Every fixture works: light_state = "on" (exported to glTF extras)."""
import math
import bpy
from .params import *
from .meshkit import MB
from .stairs_layout import stair_frame, CELL_U, CELL_V

FLUO_W, FLUO_D, FLUO_H = 1.28, 0.24, 0.09
FLUO_KINDS = ("kitchen", "food_prep", "veg_prep", "distribution", "dishwash", "workshop", "lab", "treatment",
              "first_aid", "blood", "exam", "physio", "med_reg", "registration", "info", "guard", "janitor",
              "kitchen_changing", "staff_changing", "med_changing", "lfk", "hydro", "service_corridor")
BULB_KINDS = ("waste", "fridge", "dry_store", "storage", "cleaning_store", "utility", "med_archive",
              "med_supplies", "med_equip", "machine_room", "electrical", "plumbing", "ventilation", "projection",
              "hall_store", "med_storage", "luggage", "dirty_linen", "clean_linen", "coatroom")
WARM_KINDS = ("salt_room", "massage", "lounge", "library", "phytobar", "suite_double", "suite_single",
              "suite_assisted", "director", "club_hall")


def fluo_mesh():
    mb = MB("Fixture_Fluo")
    w, d, h = FLUO_W / 2, FLUO_D / 2, FLUO_H
    mb.box(-w, w, -d, d, -h, 0, "atlas_furn", faces=("-x", "+x", "-y", "+y"), uv="region", regions={"*": "metal_white"})
    mb.poly_n([(-w, -d, -h), (w, -d, -h), (w, d, -h), (-w, d, -h)], [(0, 0), (1, 0), (1, 1), (0, 1)], "emit_fluo",
              (0, 0, -1))
    return mb


def plafond_mesh(r=0.22):
    mb = MB("Fixture_Plafond")
    n = 8
    ring_t = [(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n), 0) for k in range(n)]
    ring_b = [(0.8 * r * math.cos(2 * math.pi * k / n), 0.8 * r * math.sin(2 * math.pi * k / n), -0.11) for k in range(n)]
    for k in range(n):
        k2 = (k + 1) % n
        mb.poly_n([ring_t[k], ring_t[k2], ring_b[k2], ring_b[k]], [(0, 0), (1, 0), (1, 1), (0, 1)], "emit_warm",
                  (math.cos(2 * math.pi * (k + .5) / n), math.sin(2 * math.pi * (k + .5) / n), -0.5))
    mb.poly_n(ring_b, [(0.5, 0.5)] * n, "emit_warm", (0, 0, -1))
    return mb


def bulb_mesh():
    mb = MB("Fixture_Bulb")
    mb.cyl(0, 0, -0.12, 0, 0.035, "atlas_furn", sides=6, top=False, bottom=False, region="black_plastic")
    mb.cyl(0, 0, -0.22, -0.12, 0.05, "emit_warm", sides=6, top=False, bottom=True)
    return mb


def pendant_mesh(drop=2.2):
    mb = MB("Fixture_Pendant")
    mb.tube_region([(0, 0, 0), (0, 0, -drop)], 0.008, "black_plastic", 4)
    n = 10
    top = [(0.08 * math.cos(2 * math.pi * k / n), 0.08 * math.sin(2 * math.pi * k / n), -drop) for k in range(n)]
    bot = [(0.32 * math.cos(2 * math.pi * k / n), 0.32 * math.sin(2 * math.pi * k / n), -drop - 0.25) for k in range(n)]
    for k in range(n):
        k2 = (k + 1) % n
        mb.poly_n([top[k], top[k2], bot[k2], bot[k]], [(0, 0), (1, 0), (1, 1), (0, 1)], "atlas_furn",
                  (math.cos(2 * math.pi * (k + .5) / n), math.sin(2 * math.pi * (k + .5) / n), 0.6))
    for k in range(n):  # inner side, emissive (lit shade)
        k2 = (k + 1) % n
        mb.poly_n([top[k2], top[k], bot[k], bot[k2]], [(0, 0), (1, 0), (1, 1), (0, 1)], "emit_warm",
                  (-math.cos(2 * math.pi * (k + .5) / n), -math.sin(2 * math.pi * (k + .5) / n), -0.6))
    return mb


def grid(x0, x1, y0, y1, spacing):
    nx = max(1, int(round((x1 - x0) / spacing)))
    ny = max(1, int(round((y1 - y0) / spacing)))
    for i in range(nx):
        for j in range(ny):
            yield (x0 + (i + 0.5) * (x1 - x0) / nx, y0 + (j + 0.5) * (y1 - y0) / ny)


def fixtures_for_room(r):
    """Returns [(kind, x, y, z_ceiling, rot)]: enough fixtures that no part of a room stays dark."""
    out = []
    big = max(r.rects, key=lambda q: (q[1] - q[0]) * (q[3] - q[2]))
    x0, x1, y0, y1 = big
    zc = r.z1
    if r.kind == "shaft":
        return out
    if r.kind in ("stair_main", "stair_end"):
        f = stair_frame(r)
        for i in range(4):
            zt = LEVELS[i + 1] - SLAB_T if i < 3 else r.z1
            for (u, v) in ((CELL_U / 2, (CELL_V + 2.98) / 2), (CELL_U / 2, 1.5)):
                x, y = f(u, v)
                out.append(("plafond", x, y, zt, 0))
        return out
    if r.kind in ("corridor", "corridor_patient"):
        n = int(round((x1 - x0) / 3.0))
        for i in range(n):
            out.append(("plafond", x0 + (i + 0.5) * (x1 - x0) / n, (y0 + y1) / 2, zc, 0))
        return out
    if r.kind == "club_hall":
        for (x, y) in grid(x0 + 1, x1 - 1, y0 + 3.4, y1 - 0.6, 3.2):
            out.append(("pendant", x, y, zc, 0))
        return out
    kind = "fluo" if r.kind in FLUO_KINDS else ("bulb" if r.kind in BULB_KINDS else "plafond")
    if kind == "bulb":
        out.append(("bulb", (x0 + x1) / 2, (y0 + y1) / 2, zc, 0))
        return out
    long_x = (x1 - x0) >= (y1 - y0)
    for q in r.rects:
        qa = (q[1] - q[0]) * (q[3] - q[2])
        if qa < 1.5 and len(r.rects) > 1:
            continue
        sp = 2.8 if kind == "fluo" else 3.0
        for (x, y) in grid(q[0], q[1], q[2], q[3], sp):
            out.append((kind, x, y, zc, 0 if long_x else math.pi / 2))
    if not out:
        out.append((kind, (x0 + x1) / 2, (y0 + y1) / 2, zc, 0))
    return out


ENERGY = {"fluo": 75.0, "plafond": 70.0, "bulb": 40.0, "pendant": 190.0}
COLOR = {"fluo": (1.0, 0.93, 0.82), "plafond": (1.0, 0.83, 0.62), "bulb": (1.0, 0.8, 0.6), "pendant": (1.0, 0.84, 0.64)}
BUILDERS = {"fluo": fluo_mesh, "plafond": plafond_mesh, "bulb": bulb_mesh, "pendant": pendant_mesh}
DROP = {"fluo": FLUO_H + 0.05, "plafond": 0.16, "bulb": 0.28, "pendant": 2.55}


def _light(B, coll, parent, name, loc, energy, color, size=0.15):
    ld = bpy.data.lights.new("PL_" + name, "POINT")
    ld.energy = energy
    ld.color = color
    ld.shadow_soft_size = size
    lo = bpy.data.objects.new("Lamp_" + name, ld)
    lo.location = loc
    lo["light_state"] = "on"
    coll.objects.link(lo)
    lo.parent = parent
    return lo


def build_lights(B):
    lights = fixtures = 0
    for r in B.plan.rooms.values():
        warm = 1.12 if r.kind in WARM_KINDS else 1.0
        tint = (1.0, 0.72, 0.48) if r.kind == "salt_room" else None
        for i, (kind, x, y, zc, rot) in enumerate(fixtures_for_room(r)):
            coll = B.coll_for(r.rid)
            parent = B.room_empty[r.rid]
            key = f"Fixture_{kind}"
            B.lib.place(key, BUILDERS[kind], coll, f"Light_{kind}_{r.rid.split('.')[1]}", (x, y, zc), rot, parent,
                        props={"light_state": "on", "fixture": kind})
            B.stats["Lights"] = B.stats.get("Lights", 0) + B.lib.meshes[key][1]
            fixtures += 1
            room_h = r.z1 - r.z0
            e = ENERGY[kind] * warm * (1.0 if room_h < 3.5 or kind == "pendant" else 1.3)
            _light(B, coll, parent, f"{r.rid.split('.')[1]}_{lights}", (x, y, zc - DROP[kind]), e, tint or COLOR[kind])
            lights += 1
    # warm pools of light from floor lamps and wall sconces placed by the furnishing
    extra = 0
    for ob in list(bpy.data.objects):
        if ob.type != "MESH" or not ob.data.name.startswith(("SM_floor_lamp", "SM_sconce", "SM_table_lamp")):
            continue
        if ob.data.name.startswith("SM_table_lamp"):
            continue          # shade glow only (keeps the light count moderate)
        c, s = math.cos(ob.rotation_euler[2]), math.sin(ob.rotation_euler[2])
        if ob.data.name.startswith("SM_floor_lamp"):
            loc, e = (ob.location[0], ob.location[1], ob.location[2] + 1.45), 22.0
        else:
            dx, dy = 0.17 * s, -0.17 * c          # local -Y (into the room)
            loc, e = (ob.location[0] + dx, ob.location[1] + dy, ob.location[2] + 0.17), 12.0
        _light(B, ob.users_collection[0], ob.parent, f"{ob.name}_glow", loc, e, (1.0, 0.76, 0.5), 0.08)
        extra += 1
    B.stats["light_fixtures"] = fixtures
    B.stats["point_lights"] = lights + extra
    B.stats["lamp_lights"] = extra
    daylight()


def daylight():
    sc = bpy.context.scene
    sun = bpy.data.objects.get("Sun_Day")
    if sun is None:
        sd = bpy.data.lights.new("Sun_Day", "SUN")
        sd.energy = 4.0
        sd.angle = math.radians(8)
        sd.color = (1.0, 0.94, 0.84)
        sun = bpy.data.objects.new("Sun_Day", sd)
        sc.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(55), 0, math.radians(-28))   # from the front-left, afternoon sun
    if sc.world is None:
        sc.world = bpy.data.worlds.new("Sky_Day")
    w = sc.world
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes.get("Background") or nt.nodes.new("ShaderNodeBackground")
    out = nt.nodes.get("World Output") or nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg.outputs[0], out.inputs[0])
    bg.inputs[0].default_value = (0.62, 0.70, 0.80, 1)
    bg.inputs[1].default_value = 2.0
