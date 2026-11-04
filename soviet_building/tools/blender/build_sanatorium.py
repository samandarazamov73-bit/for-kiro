"""Builds the sanatorium interior inside the existing SovietSchool exterior.

Run with the Blender Python module (pip install bpy==4.5.*) or with Blender itself:
    python build_sanatorium.py [--root ../..] [--no-export]
    blender -b -P build_sanatorium.py -- [--root ../..]

Outputs (relative to soviet_building/):
    export/blend/SovietSanatorium.blend      exterior + interior, textures linked from textures/
    export/SovietSanatorium.glb              exterior + interior, textures embedded (JPEG)
    export/SovietSanatorium_Interior.glb     interior only
    export/fbx/SovietSanatorium.fbx          exterior + interior, textures referenced from textures/
    plans/plan_floor{1..4}.png               floor plans from the same data
    plans/rooms.csv                          room schedule
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402

from sanatorium.params import *  # noqa: E402,F401
from sanatorium.plan import build_plan  # noqa: E402
from sanatorium.layout import Layout  # noqa: E402
from sanatorium import materials, architecture, bobj  # noqa: E402
from sanatorium.meshkit import MB  # noqa: E402

STAGES = ["architecture", "doors", "stairs", "elevator", "furniture", "lights"]


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.normpath(os.path.join(HERE, "..", "..")))
    ap.add_argument("--tex", default=None, help="texture folder (default <root>/textures)")
    ap.add_argument("--no-export", action="store_true")
    ap.add_argument("--blend", default=None)
    ap.add_argument("--stages", default=",".join(STAGES))
    return ap.parse_args(argv)


def level_of_z(z):
    k = 0
    for i, L in enumerate(LEVELS):
        if z >= L - 0.5:
            k = i
    return k


class Build:
    def __init__(self, a):
        self.a = a
        self.root = a.root
        self.tex = a.tex or os.path.join(a.root, "textures")
        self.plan = build_plan()
        self.lay = Layout(self.plan)
        errs = self.lay.validate()
        if errs:
            raise SystemExit("plan errors:\n" + "\n".join(errs))
        self.stats = {}

    def import_exterior(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=os.path.join(self.root, "export", "SovietSchool.glb"))
        ext = bpy.data.objects["SovietSchool_1970s"]
        self.root_empty = bobj.empty("SovietSanatorium", bpy.context.scene.collection)
        ext.parent = self.root_empty
        cext = bobj.collection("Exterior")
        for ob in list(bpy.context.scene.collection.objects):
            if ob is not self.root_empty:
                bpy.context.scene.collection.objects.unlink(ob)
                cext.objects.link(ob)
        self.exterior_tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons)
                                 for o in cext.objects if o.type == "MESH")
        materials.adapt_exterior(self.tex)

    def setup(self):
        self.mats = materials.all_materials(self.tex)
        self.lib = bobj.Library(self.mats)
        self.cint = bobj.collection("Interior")
        self.int_empty = bobj.empty("Interior", self.cint, self.root_empty)
        self.level_empty, self.level_coll = {}, {}
        names = ["Floor1_Ground", "Floor2", "Floor3", "Floor4"]
        for i in range(4):
            c = bobj.collection(f"Interior_{names[i]}", self.cint)
            self.level_coll[i] = c
            self.level_empty[i] = bobj.empty(names[i], c, self.int_empty, props={"level_z": LEVELS[i]})
        self.room_empty = {}
        for r in self.plan.rooms.values():
            e = bobj.empty(f"Room_{r.num or r.rid.split('.')[1]}_{r.en.split('(')[0].strip().replace(' ', '')}"[:60],
                           self.level_coll[r.level], self.level_empty[r.level],
                           props={"room_id": r.rid, "number": r.num, "name_ru": r.ru, "name_en": r.en,
                                  "department": r.dept, "area_m2": round(r.area, 2), "kind": r.kind})
            self.room_empty[r.rid] = e

    def coll_for(self, rid):
        return self.level_coll[self.plan.rooms[rid].level]

    def add(self, mb, rid=None, level=None, name=None, props=None, group="Architecture"):
        if mb.empty():
            return None
        if rid:
            coll, parent = self.coll_for(rid), self.room_empty[rid]
        else:
            coll, parent = self.level_coll[level], self.level_empty[level]
        ob = bobj.mesh_object(mb, self.mats, coll, parent, name or mb.name, props)
        self.stats[group] = self.stats.get(group, 0) + mb.tris()
        return ob

    # ------------------------------------------------------------------ stages
    def architecture(self):
        lay = self.lay
        for r in self.plan.rooms.values():
            self.add(architecture.room_shell(lay, r), r.rid, name=f"Shell_{r.rid.replace('.', '_')}")
        reveals = {i: MB(f"WindowReveals_L{i}") for i in range(4)}
        sills = {i: MB(f"WindowSills_L{i}") for i in range(4)}
        tmp_r, tmp_s = MB("r"), MB("s")
        self.radiators = architecture.window_parts(lay, tmp_r, tmp_s)
        # split per level by z
        for src, dst in ((tmp_r, reveals), (tmp_s, sills)):
            for f, m in zip(src.f, src.mi):
                z = min(src.v[i][2] for i in f)
                dst[level_of_z(z)].poly([src.v[i] for i in f], [src.uv[i] for i in f], src.mats[m])
        for i in range(4):
            self.add(reveals[i], level=i, group="Windows")
            self.add(sills[i], level=i, group="Windows")
            mb = MB(f"OpeningLinings_L{i}")
            self.add(mb, level=i)
            p = MB(f"Pilasters_L{i}")
            architecture.pilasters(lay, i, p)
            self.add(p, level=i, group="Structure")
        lin = MB("OpeningLinings")
        architecture.opening_linings(lay, lin)
        per = {i: MB(f"OpeningLinings_L{i}") for i in range(4)}
        for f, m in zip(lin.f, lin.mi):
            z = min(lin.v[k][2] for k in f)
            per[level_of_z(z)].poly([lin.v[k] for k in f], [lin.uv[k] for k in f], lin.mats[m])
        for i in range(4):
            self.add(per[i], level=i)

    def doors(self):
        from sanatorium.place_doors import build_doors
        build_doors(self)

    def stairs(self):
        from sanatorium.stairs import build_stair
        for key in ("STAIR1", "STAIR2", "STAIR3"):
            r = self.plan.rooms["L0." + key]
            mb, rail, inf = build_stair(r)
            props = {"stair": True, "risers_per_storey": 22, "riser_mm": 150, "tread_mm": 300, "flight_width_m": 1.44}
            self.add(mb, r.rid, name=f"{key.title()}_Flights", props=props, group="Stairs")
            self.add(rail, r.rid, name=f"{key.title()}_Handrails", group="Stairs")
            self.add(inf, r.rid, name=f"{key.title()}_Balusters", group="Stairs")

    def elevator(self):
        from sanatorium import elevator as E
        shaft = self.plan.rooms["L0.SHAFT"]
        parent = self.room_empty[shaft.rid]
        parent.update(E.props()) if hasattr(parent, "update") else None
        for k, v in E.props().items():
            parent[k] = v
        cab = self.add(E.cabin(FFL), shaft.rid, name="Lift_Cabin", props=E.props(), group="Elevator")
        self.add(E.shaft_equipment(), shaft.rid, name="Lift_Shaft_Equipment", group="Elevator")
        self.add(E.machine_room(), "L0.F12", name="Lift_Machine", group="Elevator")
        ld = bpy.data.lights.new("PL_LiftCabin", "POINT")
        ld.energy, ld.color, ld.shadow_soft_size = 18.0, (1.0, 0.86, 0.66), 0.2
        lo = bpy.data.objects.new("Lamp_LiftCabin", ld)
        lo.location = (37.5, 5.15, FFL + 2.0)
        self.coll_for(shaft.rid).objects.link(lo)
        lo.parent = parent
        for lvl in range(4):
            mb, dec = E.landing(lvl)
            p = dict(E.props()); p["landing_level"] = lvl + 1
            self.add(mb, level=lvl, name=f"Lift_Landing_Floor{lvl + 1}", props=p, group="Elevator")
            self.add(dec, level=lvl, name=f"Lift_Signs_Floor{lvl + 1}", group="Signs")

    def lights(self):
        from sanatorium.lighting import build_lights
        build_lights(self)

    def furniture(self):
        from sanatorium.furnish import furnish_all
        furnish_all(self)

    def run(self):
        t = time.time()
        self.import_exterior()
        self.setup()
        stages = self.a.stages.split(",")
        for st in STAGES:
            if st in stages and hasattr(self, st):
                t1 = time.time()
                getattr(self, st)()
                print(f"stage {st}: {time.time() - t1:.1f}s", flush=True)
        self.report()
        self.write_plans()
        blend = self.a.blend or os.path.join(self.root, "export", "blend", "SovietSanatorium.blend")
        os.makedirs(os.path.dirname(blend), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
        bpy.ops.file.make_paths_relative()
        bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True, relative_remap=True)
        print(f"saved {blend}  total {time.time() - t:.1f}s")
        if not self.a.no_export:
            self.export()

    def write_plans(self):
        from sanatorium.drawplan import draw_level
        pdir = os.path.join(self.root, "plans")
        os.makedirs(pdir, exist_ok=True)
        titles = ["Floor 1 (ground, +1.20): reception, administration, medical, dining, service",
                  "Floor 2 (+4.50): patient rooms, assisted-care rooms, club hall",
                  "Floor 3 (+7.80): patient rooms, lounge, projection booth",
                  "Floor 4 (+11.10): patient rooms, lounge, roof access"]
        for lv in range(4):
            draw_level(self.lay, lv, os.path.join(pdir, f"plan_floor{lv + 1}.png"), title=titles[lv])
        win = {}
        for wi, e in self.lay.win_room.items():
            win[e.room.rid] = win.get(e.room.rid, 0) + 1
        with open(os.path.join(pdir, "rooms.csv"), "w", encoding="utf-8") as f:
            f.write("floor,number,id,name_ru,name_en,department,area_m2,windows,doors\n")
            for r in sorted(self.plan.rooms.values(), key=lambda r: (r.level, r.num or "zz", r.rid)):
                nd = sum(1 for g in self.lay.doors if r.rid in (g.door.a, g.door.b) and g.door.kind not in ("window", "port"))
                f.write(f"{r.level + 1},{r.num},{r.rid},\"{r.ru}\",\"{r.en}\",{r.dept},{r.area:.1f},{win.get(r.rid, 0)},{nd}\n")

    def export(self):
        exp = os.path.join(self.root, "export")
        for ob in bpy.data.objects:
            if ob.name.startswith(("PlanLight", "Cam_", "probe")):
                bpy.data.objects.remove(ob)
        common = dict(export_format="GLB", export_image_format="JPEG", export_jpeg_quality=88, export_extras=True,
                      export_lights=True, export_animations=False, export_yup=True, export_apply=False,
                      export_cameras=False)
        t = time.time()
        bpy.ops.export_scene.gltf(filepath=os.path.join(exp, "SovietSanatorium.glb"), **common)
        print(f"glb combined {time.time() - t:.0f}s")
        bpy.ops.object.select_all(action="DESELECT")
        sel = [self.root_empty] + [o for o in self.cint.all_objects]
        for o in sel:
            o.select_set(True)
        sun = bpy.data.objects.get("Sun_Overcast")
        bpy.ops.export_scene.gltf(filepath=os.path.join(exp, "SovietSanatorium_Interior.glb"), use_selection=True,
                                  **common)
        bpy.ops.object.select_all(action="DESELECT")
        os.makedirs(os.path.join(exp, "fbx"), exist_ok=True)
        bpy.ops.export_scene.fbx(filepath=os.path.join(exp, "fbx", "SovietSanatorium.fbx"), path_mode="RELATIVE",
                                 embed_textures=False, use_custom_props=True, axis_forward="-Z", axis_up="Y",
                                 apply_unit_scale=True, object_types={"EMPTY", "MESH", "LIGHT"})
        for f in ("SovietSanatorium.glb", "SovietSanatorium_Interior.glb", "fbx/SovietSanatorium.fbx"):
            p = os.path.join(exp, f)
            print(f"{f}: {os.path.getsize(p) / 1e6:.1f} MB")

    def report(self):
        tot = 0
        for ob in self.cint.all_objects:
            if ob.type == "MESH":
                tot += sum(len(p.vertices) - 2 for p in ob.data.polygons)
        self.stats["interior_scene_tris"] = tot
        self.stats["exterior_tris"] = self.exterior_tris
        self.stats["rooms"] = len(self.plan.rooms)
        self.stats["doors"] = len(self.lay.doors)
        print(json.dumps(self.stats, indent=1))


if __name__ == "__main__":
    Build(args()).run()
