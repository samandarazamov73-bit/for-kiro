"""Cycles CPU renders of the sanatorium (.blend from build_sanatorium.py).

    python render_interior.py --blend ../../export/blend/SovietSanatorium.blend --out ../../renders [--views a,b]
"""
import argparse
import math
import os
import sys
import time

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sanatorium.params import *  # noqa: E402

# name: (kind, location, look_at, lens_mm or ortho scale, notes)
VIEWS = {
    "plan_floor1": ("plan", 0, None, None),
    "plan_floor2": ("plan", 1, None, None),
    "plan_floor3": ("plan", 2, None, None),
    "plan_floor4": ("plan", 3, None, None),
    "ext_front_34": ("persp", (-12.0, -42.0, 16.0), (36.0, 2.0, 6.0), 30),
    "int_reception": ("persp", (28.4, -18.3, FFL + 1.65), (33.5, -6.0, FFL + 1.1), 18),
    "int_corridor_ground": ("persp", (73.6, 8.1, FFL + 1.65), (40.0, 8.1, FFL + 1.2), 20),
    "int_corridor_floor2": ("persp", (2.0, 7.4, LEVELS[1] + 1.6), (40.0, 8.3, LEVELS[1] + 1.2), 20),
    "int_elevator": ("persp", (36.0, 9.25, LEVELS[1] + 1.6), (37.6, 6.5, LEVELS[1] + 1.25), 20),
    "int_elevator_cabin": ("persp", (36.85, 4.3, FFL + 1.6), (38.0, 6.25, FFL + 1.15), 13),
    "int_main_stair": ("persp", (34.8, 0.9, LEVELS[1] + 1.6), (31.0, 5.5, LEVELS[1] + 0.4), 16),
    "int_dining": ("persp", (20.6, 5.8, FFL + 1.7), (13.0, 1.5, FFL + 0.8), 18),
    "int_kitchen": ("persp", (7.6, 4.6, FFL + 1.75), (3.0, 1.2, FFL + 0.8), 16),
    "int_director": ("persp", (43.4, 6.2, FFL + 1.6), (43.6, 0.9, FFL + 0.9), 16),
    "int_exam": ("persp", (42.15, 10.2, FFL + 1.6), (44.6, 15.4, FFL + 0.9), 16),
    "int_patient_double": ("persp", (7.0, 5.5, LEVELS[1] + 1.65), (7.6, 0.6, LEVELS[1] + 0.85), 15),
    "int_patient_single": ("persp", (51.9, 11.1, LEVELS[2] + 1.65), (52.9, 15.6, LEVELS[2] + 0.85), 15),
    "int_assisted": ("persp", (43.3, 5.9, LEVELS[1] + 1.65), (40.6, 0.9, LEVELS[1] + 0.8), 15),
    "int_club_hall": ("persp", (28.2, -0.8, LEVELS[1] + 1.8), (33.0, -17.0, LEVELS[1] + 1.5), 16),
    "int_lab": ("persp", (57.15, 10.2, FFL + 1.6), (59.5, 15.2, FFL + 0.9), 16),
    "int_nurse_post": ("persp", (25.5, 7.2, LEVELS[2] + 1.6), (28.6, 11.0, LEVELS[2] + 1.0), 18),
    "int_wc": ("persp", (29.55, 10.3, FFL + 1.65), (28.0, 15.3, FFL + 0.7), 14),
}


def setup_render(w, h, samples):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    sc.cycles.diffuse_bounces = 3
    sc.cycles.glossy_bounces = 2
    sc.cycles.transparent_max_bounces = 8
    sc.cycles.use_light_tree = True
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.render.image_settings.file_format = "PNG"


def look(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def camera(name):
    cam = bpy.data.objects.get(name)
    if cam is None:
        cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
        bpy.context.scene.collection.objects.link(cam)
    return cam


def plan_lights(level):
    """Temporary flat lighting just below the ceiling of one storey for plan cut-aways."""
    z = LEVELS[level] + CEIL_H - 0.12
    L = bpy.data.objects.get("PlanLight") or bpy.data.objects.new("PlanLight", bpy.data.lights.new("PlanLight", "AREA"))
    if L.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(L)
    L.data.shape = "RECTANGLE"
    L.data.size, L.data.size_y = 80, 40
    L.data.energy = 60000
    L.location = (37.5, 0, z)
    L.rotation_euler = (0, 0, 0)
    return L


def render_view(name, spec, out, w, h):
    sc = bpy.context.scene
    kind = spec[0]
    cam = camera("Cam_" + name)
    sc.camera = cam
    tmp = []
    hidden = []
    if kind == "plan":
        lvl = spec[1]
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = 78
        z = LEVELS[lvl] + CEIL_H - 0.15
        cam.location = (37.5, -1.75, z)
        cam.rotation_euler = (0, 0, 0)
        cam.data.clip_start = 0.01
        cam.data.clip_end = 30
        tmp.append(plan_lights(lvl))
        for ob in bpy.data.objects:
            if ob.type == "LIGHT" and ob.name != "PlanLight" and not ob.hide_render:
                ob.hide_render = True
                hidden.append(ob)
        sc.render.resolution_x, sc.render.resolution_y = 2400, 1200
    else:
        cam.data.type = "PERSP"
        cam.location = spec[1]
        look(cam, spec[2])
        cam.data.lens = spec[3]
        cam.data.clip_start = 0.05
        cam.data.clip_end = 300
        sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.view_settings.exposure = 1.0 if name.startswith("int_") else 0.0
    sc.render.filepath = os.path.join(out, name + ".png")
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"rendered {name} in {time.time() - t:.0f}s", flush=True)
    for ob in hidden:
        ob.hide_render = False
    for ob in tmp:
        bpy.data.objects.remove(ob)


def world(strength=1.0):
    sc = bpy.context.scene
    if sc.world is None:
        sc.world = bpy.data.worlds.new("World")
    wd = sc.world
    wd.use_nodes = True
    nt = wd.node_tree
    bg = nt.nodes.get("Background")
    if bg is None:
        bg = nt.nodes.new("ShaderNodeBackground")
        nt.links.new(bg.outputs[0], nt.nodes.get("World Output").inputs[0])
    bg.inputs[0].default_value = (0.62, 0.68, 0.76, 1)
    bg.inputs[1].default_value = strength


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--blend", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--views", default=",".join(VIEWS))
    ap.add_argument("--w", type=int, default=1600)
    ap.add_argument("--h", type=int, default=900)
    ap.add_argument("--samples", type=int, default=96)
    a = ap.parse_args(argv)
    bpy.ops.wm.open_mainfile(filepath=a.blend)
    os.makedirs(a.out, exist_ok=True)
    setup_render(a.w, a.h, a.samples)
    if bpy.context.scene.world is None:
        world()
    for v in a.views.split(","):
        render_view(v, VIEWS[v], a.out, a.w, a.h)
