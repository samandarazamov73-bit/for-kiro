"""Ceiling fixtures (fluorescent battens, glass plafonds, bare bulbs, hall pendants), point lights
for the working ones, weak overcast daylight. Fixture state is stored as a custom property:
light_state = on | flicker | broken (exported to glTF extras)."""
import math
import random
import bpy
from .params import *
from .meshkit import MB
from .stairs_layout import stair_frame, CELL_U, CELL_V

FLUO_W, FLUO_D, FLUO_H = 1.28, 0.24, 0.09
STATE_P = {   # probability (on, flicker); rest broken
    "A_entrance": (0.9, 0.05), "B_admin": (0.8, 0.05), "C_medical": (0.8, 0.08), "D_catering": (0.6, 0.1),
    "E_technical": (0.45, 0.1), "P_patient": (0.55, 0.08), "CIRC": (0.7, 0.12),
}
PLAFOND_KINDS = ("patient_single", "patient_double", "patient_assisted", "assisted_bath", "access_bath",
                 "wc_men", "wc_women", "wc_shower_m", "wc_shower_f", "kitchen_wc", "med_wc", "vestibule", "foyer",
                 "nurse_post", "housekeeping", "clean_linen", "dirty_linen", "lounge", "staff_room")
BULB_KINDS = ("waste", "fridge", "dry_store", "storage", "cleaning_store", "utility", "records", "archive",
              "med_supplies", "med_equip", "machine_room", "electrical", "plumbing", "ventilation", "projection",
              "hall_store", "med_storage", "luggage")


def fluo_mesh(state):
    mb = MB("Fixture_Fluo")
    w, d, h = FLUO_W / 2, FLUO_D / 2, FLUO_H
    mb.box(-w, w, -d, d, -h, 0, "atlas_furn", faces=("-x", "+x", "-y", "+y"), uv="region", regions={"*": "metal_white"})
    mat = {"on": "emit_fluo", "flicker": "emit_fluo_dim", "broken": "emit_off"}[state]
    mb.poly_n([(-w, -d, -h), (w, -d, -h), (w, d, -h), (-w, d, -h)], [(0, 0), (1, 0), (1, 1), (0, 1)], mat, (0, 0, -1))
    return mb


def plafond_mesh(state, r=0.19):
    mb = MB("Fixture_Plafond")
    mat = {"on": "emit_warm", "flicker": "emit_warm", "broken": "emit_off"}[state]
    n = 6
    ring_t = [(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n), 0) for k in range(n)]
    ring_b = [(0.8 * r * math.cos(2 * math.pi * k / n), 0.8 * r * math.sin(2 * math.pi * k / n), -0.11) for k in range(n)]
    for k in range(n):
        k2 = (k + 1) % n
        mb.poly_n([ring_t[k], ring_t[k2], ring_b[k2], ring_b[k]], [(0, 0), (1, 0), (1, 1), (0, 1)], mat,
                  (math.cos(2 * math.pi * (k + .5) / n), math.sin(2 * math.pi * (k + .5) / n), -0.5))
    mb.poly_n(ring_b, [(0.5, 0.5)] * n, mat, (0, 0, -1))
    return mb


def bulb_mesh(state):
    mb = MB("Fixture_Bulb")
    mb.cyl(0, 0, -0.12, 0, 0.035, "atlas_furn", sides=6, top=False, bottom=False, region="black_plastic")
    mat = {"on": "emit_warm", "flicker": "emit_warm", "broken": "emit_off"}[state]
    mb.cyl(0, 0, -0.22, -0.12, 0.05, mat, sides=6, top=False, bottom=True)
    return mb


def pendant_mesh(state, drop=2.2):
    mb = MB("Fixture_Pendant")
    mb.tube_region([(0, 0, 0), (0, 0, -drop)], 0.008, "black_plastic", 4)
    mat = {"on": "emit_warm", "flicker": "emit_warm", "broken": "emit_off"}[state]
    n = 10
    top = [(0.08 * math.cos(2 * math.pi * k / n), 0.08 * math.sin(2 * math.pi * k / n), -drop) for k in range(n)]
    bot = [(0.32 * math.cos(2 * math.pi * k / n), 0.32 * math.sin(2 * math.pi * k / n), -drop - 0.25) for k in range(n)]
    for k in range(n):
        k2 = (k + 1) % n
        mb.poly_n([top[k], top[k2], bot[k2], bot[k]], [(0, 0), (1, 0), (1, 1), (0, 1)], "atlas_furn",
                  (math.cos(2 * math.pi * (k + .5) / n), math.sin(2 * math.pi * (k + .5) / n), 0.6))
    for k in range(n):  # inner side, emissive (lit shade)
        k2 = (k + 1) % n
        mb.poly_n([top[k2], top[k], bot[k], bot[k2]], [(0, 0), (1, 0), (1, 1), (0, 1)], mat,
                  (-math.cos(2 * math.pi * (k + .5) / n), -math.sin(2 * math.pi * (k + .5) / n), -0.6))
    for i in range(len(mb.uv) - 4 * n * 2, len(mb.uv) - 4 * n):
        pass
    return mb


def _state(rng, dept, kind):
    on, fl = STATE_P.get(dept, (0.5, 0.1))
    if kind in ("hall", "waiting", "registration", "guard", "info", "vestibule"):
        on, fl = 0.95, 0.03
    x = rng.random()
    return "on" if x < on else ("flicker" if x < on + fl else "broken")


def grid(x0, x1, y0, y1, spacing):
    nx = max(1, int(round((x1 - x0) / spacing)))
    ny = max(1, int(round((y1 - y0) / spacing)))
    for i in range(nx):
        for j in range(ny):
            yield (x0 + (i + 0.5) * (x1 - x0) / nx, y0 + (j + 0.5) * (y1 - y0) / ny)


def fixtures_for_room(r):
    """Returns [(kind, x, y, z_ceiling, rot)]."""
    out = []
    big = max(r.rects, key=lambda q: (q[1] - q[0]) * (q[3] - q[2]))
    x0, x1, y0, y1 = big
    zc = r.z1
    if r.kind in ("shaft",):
        return out
    if r.kind in ("stair_main", "stair_end"):
        f = stair_frame(r)
        for i in range(4):
            zt = LEVELS[i + 1] - SLAB_T if i < 3 else r.z1
            x, y = f(CELL_U / 2, (CELL_V + 2.98) / 2)
            out.append(("plafond", x, y, zt, 0))
        return out
    if r.kind.startswith("corridor") or r.kind == "service_corridor":
        n = int((x1 - x0) / 4.5)
        for i in range(n):
            out.append(("fluo", x0 + (i + 0.5) * (x1 - x0) / n, (y0 + y1) / 2, zc, 0))
        return out
    if r.kind == "club_hall":
        for (x, y) in grid(x0 + 1, x1 - 1, y0 + 4, y1 - 1, 3.6):
            out.append(("pendant", x, y, zc, 0))
        return out
    if r.kind in PLAFOND_KINDS:
        for q in r.rects:
            if (q[1] - q[0]) * (q[3] - q[2]) > 4.5:
                n = 2 if (q[3] - q[2]) > 5 and r.kind not in ("patient_single", "patient_double") else 1
                for (x, y) in grid(q[0], q[1], q[2], q[3], 10 if n == 1 else 3.2):
                    out.append(("plafond", x, y, zc, 0))
        if not out:
            out.append(("plafond", (x0 + x1) / 2, (y0 + y1) / 2, zc, 0))
        return out
    if r.kind in BULB_KINDS:
        out.append(("bulb", (x0 + x1) / 2, (y0 + y1) / 2, zc, 0))
        return out
    long_x = (x1 - x0) >= (y1 - y0)
    for (x, y) in grid(x0, x1, y0, y1, 2.6 if r.kind in ("hall", "waiting", "dining", "kitchen") else 3.1):
        out.append(("fluo", x, y, zc, 0 if long_x else math.pi / 2))
    return out


ENERGY = {"fluo": 55.0, "plafond": 35.0, "bulb": 25.0, "pendant": 60.0}
COLOR = {"fluo": (0.92, 0.97, 1.0), "plafond": (1.0, 0.86, 0.66), "bulb": (1.0, 0.8, 0.6), "pendant": (1.0, 0.85, 0.65)}
BUILDERS = {"fluo": fluo_mesh, "plafond": plafond_mesh, "bulb": bulb_mesh, "pendant": pendant_mesh}


def build_lights(B):
    rng = random.Random(1975)
    lights = 0
    fixtures = 0
    for r in B.plan.rooms.values():
        for (kind, x, y, zc, rot) in fixtures_for_room(r):
            st = _state(rng, r.dept, r.kind)
            coll = B.coll_for(r.rid)
            parent = B.room_empty[r.rid]
            key = f"Fixture_{kind}_{st}"
            ob = B.lib.place(key, (lambda k=kind, s=st: BUILDERS[k](s)), coll, f"Light_{kind}_{r.rid.split('.')[1]}",
                             (x, y, zc), rot, parent, props={"light_state": st, "fixture": kind})
            B.stats["Lights"] = B.stats.get("Lights", 0) + B.lib.meshes[key][1]
            fixtures += 1
            if st == "broken":
                continue
            ld = bpy.data.lights.new(f"PL_{kind}_{st}_{lights}", "POINT")
            ld.energy = ENERGY[kind] * (0.35 if st == "flicker" else 1.0) * (0.8 + 0.4 * rng.random())
            ld.color = COLOR[kind]
            ld.shadow_soft_size = 0.15
            ld["flicker"] = st == "flicker"
            lo = bpy.data.objects.new(f"Lamp_{r.rid.split('.')[1]}_{lights}", ld)
            drop = {"fluo": FLUO_H + 0.05, "plafond": 0.16, "bulb": 0.28, "pendant": 2.55}[kind]
            lo.location = (x, y, zc - drop)
            lo["flicker"] = st == "flicker"
            coll.objects.link(lo)
            lo.parent = parent
            if st == "flicker":
                _flicker(ld, rng)
            lights += 1
    B.stats["light_fixtures"] = fixtures
    B.stats["point_lights"] = lights
    daylight()


def _flicker(ld, rng):
    """Keyframed on/off stutter (48 frames, loops) for flickering tubes."""
    e = ld.energy
    f = 1
    while f < 48:
        ld.energy = e * (1.0 if rng.random() < 0.6 else rng.uniform(0.0, 0.25))
        ld.keyframe_insert("energy", frame=f)
        f += rng.choice((1, 2, 3, 6))
    ld.energy = e


def daylight():
    sc = bpy.context.scene
    sun = bpy.data.objects.get("Sun_Overcast")
    if sun is None:
        sd = bpy.data.lights.new("Sun_Overcast", "SUN")
        sd.energy = 3.5
        sd.angle = math.radians(12)
        sd.color = (1.0, 0.95, 0.88)
        sun = bpy.data.objects.new("Sun_Overcast", sd)
        sc.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(58), 0, math.radians(-28))   # from the front-left, low afternoon sun
    if sc.world is None:
        sc.world = bpy.data.worlds.new("Sky_Overcast")
    w = sc.world
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes.get("Background") or nt.nodes.new("ShaderNodeBackground")
    out = nt.nodes.get("World Output") or nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg.outputs[0], out.inputs[0])
    bg.inputs[0].default_value = (0.60, 0.66, 0.74, 1)
    bg.inputs[1].default_value = 2.2
