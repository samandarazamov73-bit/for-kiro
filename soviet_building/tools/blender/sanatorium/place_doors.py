"""Places door modules for every resolved door of the layout."""
import math
from .params import *
from .layout import FRAMED, COLUMNS_X
from .meshkit import MB
from . import doors as D
from .atlas import sign_keys, sign_boxes

STYLE = {"std": "wood", "wide": "wood", "wc_door": "wood", "glazed": "glazed", "double": "wood",
         "double_glazed": "wired", "metal": "metal", "metal_glazed": "metal_glazed", "padded": "padded",
         "steel_double": "metal"}
CORRIDORISH = ("corridor", "service_corridor", "corridor_patient", "hall", "waiting", "foyer", "club_hall",
               "nurse_post", "stair_main", "stair_end", "vestibule")


def build_doors(B):
    lay, lib = B.lay, B.lib
    keys = sign_keys(B.plan)
    boxes = sign_boxes(keys)
    plates = {i: MB(f"DoorPlates_L{i}") for i in range(4)}
    glazing = {i: MB(f"InteriorGlazing_L{i}") for i in range(4)}
    count = 0
    for gi, g in enumerate(lay.doors):
        d = g.door
        lvl = d.level
        rid = d.a if B.plan.rooms[d.a].level == lvl and not B.plan.rooms[d.a].kind.startswith("stair") else (
            d.b if d.b != "EXT" else d.a)
        coll = B.coll_for(rid) if rid in B.plan.rooms and B.plan.rooms[rid].level == lvl else B.level_coll[lvl]
        parent = B.room_empty.get(rid) if B.plan.rooms[rid].level == lvl else B.level_empty[lvl]
        rot = D.rot_for(g.axis, g.nab)
        X0, Y0 = D.to_world(g, 0, 0)
        T = g.thickness
        if d.kind == "lift":
            continue
        if d.kind not in ("window", "port", "counter"):
            # threshold: closes the floor inside the wall thickness (room floors stop at the wall faces)
            mbt = MB("thr")
            mbt.box(-g.ow / 2, g.ow / 2, -D.CASE_T, T + D.CASE_T, -0.02, 0.008, "atlas_furn", faces=("+z", "-y", "+y"),
                    uv="region", regions={"*": "wood_dark" if d.kind in FRAMED and d.b != "EXT" else "concrete"})
            _merge_local(glazing[lvl], mbt, g, g.z0)
        if d.kind in FRAMED:
            style = STYLE[d.kind]
            region = "metal_grey" if style.startswith("metal") else "wood_dark"
            fkey = f"Frame_{g.ow:.2f}x{g.z1 - g.z0:.2f}_T{T:.2f}_{region}"
            lib.place(fkey, lambda: D.frame_mesh(g.ow, g.z1 - g.z0, T, "atlas_furn", region), coll,
                      f"DoorFrame_{d.a.split('.')[1]}_{gi}", (X0, Y0, g.z0), rot, parent)
            B.stats["Doors"] = B.stats.get("Doors", 0) + lib.meshes[fkey][1]
            double = d.kind in ("double", "double_glazed", "steel_double")
            inner = g.ow - 2 * D.GAP
            leaves = [(-inner / 2, +1, inner / 2), (inner / 2, -1, inner / 2)] if double else (
                [(-inner / 2, +1, inner)] if d.hinge == "l" else [(inner / 2, -1, inner)])
            into_a = d.swing == "a"
            ext = d.b == "EXT"
            if ext:
                into_a = True
            for li, (hx, hs, lw) in enumerate(leaves):
                ly = (0.0 if into_a else T - D.LEAF_T)
                if ext:
                    ly = T - D.LEAF_T - 0.006
                lkey = f"Leaf_{style}_{lw:.2f}x{d.h:.2f}_{'L' if hs > 0 else 'R'}{'_nb' if ext else ''}"
                hxw, hyw = D.to_world(g, hx, ly if into_a else ly + D.LEAF_T)
                ang = math.radians(d.ang if not double or li == 0 else d.ang * 0.6)
                # opening direction: into room a (local -y) or b (local +y)
                sgn = (-1 if into_a else 1) * hs
                lrot = rot + sgn * ang
                # leaf mesh is built with y from 0..LEAF_T; when the hinge sits on the b side, flip the leaf
                ob = lib.place(lkey, lambda: D.leaf_mesh(lw, d.h, style, hs, skip_back=ext), coll,
                               f"Door_{d.a.split('.')[1]}_{'to_' + d.b.split('.')[-1]}_{gi}_{li}",
                               (hxw, hyw, g.z0 + 0.01), lrot if into_a else lrot, parent,
                               props={"door": True, "open_angle_deg": float(d.ang), "hinge": "left" if hs > 0 else "right",
                                      "opens_into": d.a if into_a else d.b, "locked": d.kind in ("metal",) and d.ang == 0,
                                      "type": d.kind})
                if not into_a:
                    ob.location = (*D.to_world(g, hx, T - D.LEAF_T), g.z0 + 0.01)
                B.stats["Doors"] = B.stats.get("Doors", 0) + lib.meshes[lkey][1]
                count += 1
        elif d.kind in ("window", "port"):
            mb = D.glazed_opening(g.ow, g.z1 - g.z0, T)
            _merge_local(glazing[lvl], mb, g, g.z0)
        elif d.kind == "counter":
            _merge_local(glazing[lvl], D.counter_board(g.ow, T), g, g.z0)
        # door plate on the corridor side
        if d.sign and d.kind in FRAMED and d.b != "EXT":
            ra, rb = B.plan.rooms[d.a], B.plan.rooms[d.b]
            if ra.num and (rb.kind in CORRIDORISH or not rb.num):
                key, y_local, facing = d.a, T + 0.004, +1
            elif rb.num and (ra.kind in CORRIDORISH or not ra.num):
                key, y_local, facing = d.b, -0.004, -1
            else:
                key, y_local, facing = d.a, T + 0.004, +1
            if key in boxes:
                latch = +1 if d.hinge == "l" else -1
                xl = latch * (g.ow / 2 + D.CASE_W + 0.22)
                z = g.z0 + 1.45
                if _hits_pilaster(g, xl, y_local) or _off_face(g, xl):
                    xl = -xl
                    if _hits_pilaster(g, xl, y_local) or _off_face(g, xl):
                        xl, z = 0.0, g.z1 + D.CASE_W + 0.06
                D.plate_quad(plates[lvl], g, xl, z, y_local, key, boxes, None, facing=facing * (1 if True else -1))
    for i in range(4):
        B.add(plates[i], level=i, group="Signs")
        B.add(glazing[i], level=i, group="Doors")
    B.stats["door_leaves"] = count


def _merge_local(dst, mb, g, z0):
    for f, m in zip(mb.f, mb.mi):
        pts = []
        for k in f:
            x, y, z = mb.v[k]
            X, Y = D.to_world(g, x, y)
            pts.append((X, Y, z + z0))
        dst.poly(pts, [mb.uv[k] for k in f], mb.mats[m])


def _hits_pilaster(g, xl, yl):
    X, Y = D.to_world(g, xl, yl)
    if g.axis != "x":
        return False
    for x in COLUMNS_X:
        if abs(X - x) < COLUMN / 2 + 0.2 and (CORR_Y0 - 0.05 < Y < CORR_Y0 + 0.3 or CORR_Y1 - 0.3 < Y < CORR_Y1 + 0.05):
            return True
    return False


def _off_face(g, xl):
    lo, hi = max(g.ea.a, g.eb.a if g.eb else g.ea.a), min(g.ea.b, g.eb.b if g.eb else g.ea.b)
    s = g.c + xl * (1 if (g.axis == "x") == (g.nab > 0) else -1) if g.axis == "x" else None
    X, Y = D.to_world(g, xl, 0)
    s = X if g.axis == "x" else Y
    return not (lo + 0.2 < s < hi - 0.2)
