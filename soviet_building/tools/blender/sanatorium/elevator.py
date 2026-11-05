"""Passenger / bed elevator for the guests (1970s Soviet type, lower machine room).

Shaft x 36.2-38.8, y 3.7-6.5 (clear 2.6 x 2.8 m), pit at +-0.2, head under the roof slab.
Cabin 1.9 x 2.2 x 2.2 m clear (wheelchair + attendant or a bed), 1000 kg, door 1.2 m centre-opening.
Free to use: a call button on every landing, floor buttons in the cabin. The cabin waits at floor 1
with the landing and cabin doors open; on the other floors the landing doors are closed."""
import math
from .params import *
from .meshkit import MB
from .atlas import FURN_UV, DECAL_UV

SX0, SX1, SY0, SY1 = SHAFT
CAB = dict(x0=36.55, x1=38.45, y0=4.05, y1=6.25, h=2.2)   # clear inside
WALL_T = 0.05


def R(region):
    u0, v0, u1, v1 = FURN_UV[region]
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def RD(region):
    u0, v0, u1, v1 = DECAL_UV[region]
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def face_y(mb, x0, x1, z0, z1, y, want, mat, uv):
    mb.poly_n([(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], uv if want[1] < 0 else [uv[1], uv[0], uv[3], uv[2]],
              mat, want)


def landing(level, open_=False):
    """Corridor-side portal, two-leaf landing door (open where the cabin waits), floor indicator,
    call panel, signs."""
    L = LEVELS[level]
    mb = MB(f"Lift_Landing_L{level}")
    cx, w, h = LIFT_DOOR_X, LIFT_DOOR_W, LIFT_DOOR_H
    yc = CORR_Y0            # corridor face of the corridor wall (6.7)
    ys = FRONT_Y1           # shaft face (6.5)
    # portal: steel jambs + head on the corridor face, 0.12 wide, 0.03 proud
    pw, pp = 0.12, 0.03
    for (x0, x1, z0, z1) in ((cx - w / 2 - pw, cx - w / 2, L, L + h + pw), (cx + w / 2, cx + w / 2 + pw, L, L + h + pw),
                             (cx - w / 2, cx + w / 2, L + h, L + h + pw)):
        mb.box(x0, x1, yc, yc + pp, z0, z1, "atlas_furn", faces=("+y", "-x", "+x", "+z"), uv="region",
               regions={"*": "metal_grey"})
    # jamb lining through the wall
    for x, want in ((cx - w / 2, (1, 0, 0)), (cx + w / 2, (-1, 0, 0))):
        mb.poly_n([(x, ys, L), (x, yc, L), (x, yc, L + h), (x, ys, L + h)], R("metal_grey"), "atlas_furn", want)
    mb.poly_n([(cx - w / 2, ys, L + h), (cx + w / 2, ys, L + h), (cx + w / 2, yc, L + h), (cx - w / 2, yc, L + h)],
              R("metal_grey"), "atlas_furn", (0, 0, -1))
    # steel sill
    mb.box(cx - w / 2, cx + w / 2, ys - 0.05, yc + 0.03, L - 0.02, L + 0.005, "atlas_furn", faces=("+z", "+y"),
           uv="region", regions={"*": "aluminium"})
    # centre-opening landing doors (two leaves); open = slid into the wall pockets beside the opening
    u0, v0, u1, v1 = FURN_UV["elevator_door"]
    um = (u0 + u1) / 2
    yd = ys + 0.06
    sh = w / 2 if open_ else 0.0
    for (x0, x1, ua, ub) in ((cx - w / 2 - 0.02 - sh, cx - sh, u0, um), (cx + sh, cx + w / 2 + 0.02 + sh, um, u1)):
        uv = [(ua, v0), (ub, v0), (ub, v1), (ua, v1)]
        mb.poly_n([(x0, yd + 0.03, L), (x1, yd + 0.03, L), (x1, yd + 0.03, L + h), (x0, yd + 0.03, L + h)], uv,
                  "atlas_furn", (0, 1, 0))
        mb.poly_n([(x0, yd, L), (x1, yd, L), (x1, yd, L + h), (x0, yd, L + h)], R("metal_grey"), "atlas_furn",
                  (0, -1, 0))
    # mechanical floor indicator (semicircular dial) above the portal
    zi = L + h + pw + 0.08
    mb.box(cx - 0.26, cx + 0.26, yc, yc + 0.07, zi, zi + 0.26, "atlas_furn", faces=("-x", "+x", "+z", "-z"),
           uv="region", regions={"*": "metal_grey"})
    face_y(mb, cx - 0.26, cx + 0.26, zi, zi + 0.26, yc + 0.07, (0, 1, 0), "atlas_furn", R("floor_indicator"))
    # needle pointing at "1" (cabin parked on the ground floor): thin quad from the dial centre
    ang = math.pi * (1 - 0.5 / 4)
    # seen from the corridor the dial's left (floor "1") is world +X
    nx, nz = -math.cos(ang) * 0.17, math.sin(ang) * 0.17
    px, pz = cx, zi + 0.02
    nrm = (-nz * 0.06, nx * 0.06)
    nd = [(px - nrm[0] * 0.15, yc + 0.075, pz - nrm[1] * 0.15), (px + nrm[0] * 0.15, yc + 0.075, pz + nrm[1] * 0.15),
          (px + nx, yc + 0.075, pz + nz), (px + nx, yc + 0.075, pz + nz)]
    mb.poly_n(nd[:3], R("black_plastic")[:3], "atlas_furn", (0, 1, 0))
    # call panel beside the door (towards +X), button at 1.0 m (reachable from a wheelchair)
    kx = cx + w / 2 + pw + 0.12
    pz0, pz1 = L + 0.78, L + 1.28
    mb.box(kx - 0.065, kx + 0.065, yc, yc + 0.025, pz0, pz1, "atlas_furn", faces=("-x", "+x", "+z", "-z"),
           uv="region", regions={"*": "metal_grey"})
    face_y(mb, kx - 0.065, kx + 0.065, pz0, pz1, yc + 0.025, (0, 1, 0), "atlas_furn", R("landing_panel"))
    _knob(mb, kx, yc + 0.025, pz0 + 0.5 * (1 - 180 / 512), 0.024, 0.014, "black_plastic")
    # lift sign and rules (decals) left of the portal
    dec = MB(f"Lift_Signs_L{level}")
    sx = cx - w / 2 - pw - 0.05
    for (x0, x1, z0, z1, reg) in ((sx - 0.5, sx, L + 1.55, L + 1.80, "lift_sign"),
                                   (sx - 0.36, sx - 0.12, L + 1.12, L + 1.44, "lift_rules")):
        face_y(dec, x0, x1, z0, z1, yc + 0.004, (0, 1, 0), "atlas_decal", RD(reg))
    return mb, dec


def _knob(mb, x, y, z, r, depth, region, sides=8):
    """Cylinder pointing +Y out of a panel face at (x, y, z)."""
    u0, v0, u1, v1 = FURN_UV[region]
    ring0, ring1 = [], []
    for k in range(sides):
        th = 2 * math.pi * k / sides
        ring0.append((x + r * math.cos(th), y, z + r * math.sin(th)))
        ring1.append((x + r * math.cos(th), y + depth, z + r * math.sin(th)))
    for k in range(sides):
        k2 = (k + 1) % sides
        mb.poly_n([ring0[k], ring0[k2], ring1[k2], ring1[k]], [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], "atlas_furn",
                  (math.cos(2 * math.pi * (k + .5) / sides), 0, math.sin(2 * math.pi * (k + .5) / sides)))
    mb.poly_n(ring1, [((u0 + u1) / 2, (v0 + v1) / 2)] * sides, "atlas_furn", (0, 1, 0))


def cabin(floor_z, open_=True):
    """Cabin parked with its floor at floor_z (doors open); separate object so it can be animated."""
    mb = MB("Lift_Cabin")
    c = CAB
    x0, x1, y0, y1, h = c["x0"], c["x1"], c["y0"], c["y1"], c["h"]
    z0, z1 = floor_z, floor_z + h
    t = WALL_T
    dx0, dx1 = LIFT_DOOR_X - LIFT_DOOR_W / 2, LIFT_DOOR_X + LIFT_DOOR_W / 2
    wall_uv = lambda: R("cabin_wall")
    # inner walls (laminate), door wall has the opening
    mb.poly_n([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], wall_uv(), "atlas_furn", (0, 1, 0))
    mb.poly_n([(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)], wall_uv(), "atlas_furn", (1, 0, 0))
    mb.poly_n([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], wall_uv(), "atlas_furn", (-1, 0, 0))
    for (a, b, za, zb) in ((x0, dx0, z0, z1), (dx1, x1, z0, z1), (dx0, dx1, z0 + LIFT_DOOR_H, z1)):
        mb.poly_n([(a, y1, za), (b, y1, za), (b, y1, zb), (a, y1, zb)], R("metal_grey"), "atlas_furn", (0, -1, 0))
    # floor (linoleum) and ceiling with a plafond
    mb.poly_n([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)],
              [(x0 / 2, y0 / 2), (x1 / 2, y0 / 2), (x1 / 2, y1 / 2), (x0 / 2, y1 / 2)], "linoleum_brown", (0, 0, 1))
    mb.poly_n([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], R("metal_white"), "atlas_furn", (0, 0, -1))
    mb.box(37.2, 37.8, 4.9, 5.4, z1 - 0.06, z1, "atlas_furn", faces=("-x", "+x", "-y", "+y"), uv="region",
           regions={"*": "plafond"})
    mb.poly_n([(37.2, 4.9, z1 - 0.06), (37.8, 4.9, z1 - 0.06), (37.8, 5.4, z1 - 0.06), (37.2, 5.4, z1 - 0.06)],
              [(0, 0), (1, 0), (1, 1), (0, 1)], "emit_warm", (0, 0, -1))
    # outer shell (painted steel) and car-top inspection box
    X0, X1, Y0, Y1, Z1 = x0 - t, x1 + t, y0 - t, y1 + t, z1 + 0.15
    mb.box(X0, X1, Y0, Y1, z0 - 0.15, Z1, "atlas_furn", faces=("-x", "+x", "-y", "+z", "-z"), uv="region",
           regions={"*": "metal_grey"})
    for (a, b, za, zb) in ((X0, dx0, z0 - 0.15, Z1), (dx1, X1, z0 - 0.15, Z1), (dx0, dx1, z0 + LIFT_DOOR_H, Z1)):
        mb.poly_n([(a, Y1, za), (b, Y1, za), (b, Y1, zb), (a, Y1, zb)], R("metal_grey"), "atlas_furn", (0, 1, 0))
    mb.poly_n([(dx0, y1, z0), (dx1, y1, z0), (dx1, Y1, z0), (dx0, Y1, z0)], R("aluminium"), "atlas_furn", (0, 0, 1))
    mb.box(36.8, 37.3, 4.4, 4.8, Z1, Z1 + 0.25, "atlas_furn", faces=("-x", "+x", "-y", "+y", "+z"), uv="region",
           regions={"*": "metal_green", "+y": "fuse_board"})
    # cabin doors (inside face); open = slid behind the front wall panels
    u0, v0, u1, v1 = FURN_UV["elevator_door"]
    um = (u0 + u1) / 2
    sh = LIFT_DOOR_W / 2 if open_ else 0.0
    for (a, b, ua, ub) in ((dx0 - 0.02 - sh, LIFT_DOOR_X - sh, u0, um), (LIFT_DOOR_X + sh, dx1 + 0.02 + sh, um, u1)):
        uv = [(ub, v0), (ua, v0), (ua, v1), (ub, v1)]
        mb.poly_n([(a, y1 + 0.02, z0), (b, y1 + 0.02, z0), (b, y1 + 0.02, z0 + LIFT_DOOR_H), (a, y1 + 0.02, z0 + LIFT_DOOR_H)],
                  uv, "atlas_furn", (0, -1, 0))
    # control panel on the door wall (inside), right of the opening: buttons 4..1, STOP, CALL, DOOR OPEN
    px0, px1 = dx1 + 0.12, dx1 + 0.28
    pz0, pz1 = z0 + 0.85, z0 + 1.55
    mb.box(px0, px1, y1 - 0.03, y1, pz0, pz1, "atlas_furn", faces=("-x", "+x", "+z", "-z"), uv="region",
           regions={"*": "metal_grey"})
    face_y(mb, px0, px1, pz0, pz1, y1 - 0.03, (0, -1, 0), "atlas_furn", R("cabin_panel"))
    pcx = (px0 + px1) / 2
    for i, frac in enumerate((70, 126, 182, 238, 310, 370, 432)):
        zz = pz1 - (pz1 - pz0) * frac / 512
        region = {4: "red_paint", 5: "brass"}.get(i, "black_plastic")
        _knob_neg(mb, pcx, y1 - 0.03, zz, 0.016 if i < 4 else 0.02, 0.01, region)
    # handrails on the back and side walls (accessibility)
    mb.tube_region([(x0 + 0.15, y0 + 0.05, z0 + 0.9), (x1 - 0.15, y0 + 0.05, z0 + 0.9)], 0.018, "chrome", 6, True, True)
    for x, sx in ((x0 + 0.05, 1), (x1 - 0.05, -1)):
        mb.tube_region([(x, y0 + 0.2, z0 + 0.9), (x, y1 - 0.35, z0 + 0.9)], 0.018, "chrome", 6, True, True)
    # fold-down seat on the left wall
    mb.box(x0, x0 + 0.32, y0 + 0.75, y0 + 1.2, z0 + 0.48, z0 + 0.52, "atlas_furn", faces=("+x", "-y", "+y", "+z", "-z"),
           uv="region", regions={"*": "wood_light"})
    return mb


def _remap_tail(mb, nfaces, region):
    u0, v0, u1, v1 = FURN_UV[region]
    k = sum(len(f) for f in mb.f[-nfaces:])
    mb.uv[-k:] = [(u0 + (u1 - u0) * 0.5, v0 + (v1 - v0) * 0.5)] * k


def _knob_neg(mb, x, y, z, r, depth, region, sides=8):
    u0, v0, u1, v1 = FURN_UV[region]
    ring0, ring1 = [], []
    for k in range(sides):
        th = 2 * math.pi * k / sides
        ring0.append((x + r * math.cos(th), y, z + r * math.sin(th)))
        ring1.append((x + r * math.cos(th), y - depth, z + r * math.sin(th)))
    for k in range(sides):
        k2 = (k + 1) % sides
        mb.poly_n([ring0[k], ring0[k2], ring1[k2], ring1[k]], [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], "atlas_furn",
                  (math.cos(2 * math.pi * (k + .5) / sides), 0, math.sin(2 * math.pi * (k + .5) / sides)))
    mb.poly_n(ring1, [((u0 + u1) / 2, (v0 + v1) / 2)] * sides, "atlas_furn", (0, -1, 0))


def shaft_equipment():
    """Guide rails, counterweight with its rails, hoist ropes, pit buffers, overhead pulley beam."""
    mb = MB("Lift_Shaft_Equipment")
    z0, z1 = SHAFT_PIT_Z, SHAFT_TOP_Z
    yc = (CAB["y0"] + CAB["y1"]) / 2
    for x in (SX0 + 0.06, SX1 - 0.06):
        mb.box(x - 0.04, x + 0.04, yc - 0.04, yc + 0.04, z0, z1, "metal_rusty", faces=("-x", "+x", "-y", "+y"),
               uv="world", scale=1.0)
    # counterweight behind the cabin (near the top when the cabin is at the bottom)
    cwz = 10.8
    mb.box(37.0, 38.0, SY0 + 0.04, SY0 + 0.26, cwz, cwz + 1.6, "atlas_furn",
           faces=("-x", "+x", "-y", "+y", "+z", "-z"), uv="region", regions={"*": "rust"})
    for x in (36.92, 38.08):
        mb.box(x - 0.03, x + 0.03, SY0 + 0.0, SY0 + 0.06, z0, z1, "metal_rusty", faces=("-x", "+x", "+y"), uv="world")
    # ropes: cabin -> overhead pulleys -> counterweight
    top = z1 - 0.35
    for dx in (-0.06, 0.06):
        mb.tube_region([(37.5 + dx, 5.15, FFL + CAB["h"] + 0.15), (37.5 + dx, 5.15, top)], 0.008, "black_plastic", 4)
        mb.tube_region([(37.5 + dx, SY0 + 0.15, cwz + 1.6), (37.5 + dx, SY0 + 0.15, top)], 0.008, "black_plastic", 4)
        # ropes down to the lower machine room through the floor sleeve
        mb.tube_region([(37.5 + dx, SY0 + 0.3, top), (37.5 + dx, SY0 + 0.3, FFL + 0.3)], 0.008, "black_plastic", 4)
    # overhead pulley beam and sheaves
    mb.box(SX0, SX1, 4.9, 5.3, top, top + 0.25, "metal_rusty", faces=("-x", "+x", "-y", "+y", "-z"), uv="world")
    mb.cyl(4.6, top - 0.3, 37.15, 37.85, 0.28, "metal_rusty", sides=10, top=True, bottom=True, axis="x")
    # pit buffers
    for x in (37.0, 38.0):
        mb.cyl(x, 5.15, z0, z0 + 0.45, 0.09, "atlas_furn", sides=8, region="red_paint")
    return mb


def machine_room():
    """Lower machine room (ground floor, F12 front): traction machine, controller, rope sleeves."""
    mb = MB("Lift_MachineRoom_Equipment")
    z = FFL
    mb.box(36.5, 38.0, 1.8, 2.6, z, z + 0.25, "concrete", faces=("-x", "+x", "-y", "+y", "+z"), uv="world")
    mb.box(36.6, 37.3, 1.9, 2.5, z + 0.25, z + 0.85, "atlas_furn", faces=("-x", "+x", "-y", "+y", "+z"), uv="region",
           regions={"*": "metal_green", "-y": "lift_machine"})
    mb.cyl(1.9, z + 0.75, 37.3, 37.9, 0.32, "atlas_furn", sides=12, top=True, bottom=True, axis="x", region="rust")
    mb.box(36.2, 36.9, 0.4, 0.75, z, z + 1.9, "atlas_furn", faces=("-x", "+x", "+y", "+z"), uv="region",
           regions={"*": "metal_green", "+y": "elec_panel"})
    mb.box(38.3, 38.9, 0.4, 0.7, z + 0.9, z + 1.6, "atlas_furn", faces=("-x", "+y", "+z", "-z"), uv="region",
           regions={"*": "metal_grey", "-x": "fuse_board"})
    for dx in (-0.06, 0.06):
        mb.tube_region([(37.5 + dx, 2.0, z + 1.0), (37.5 + dx, 3.62, z + 1.0)], 0.008, "black_plastic", 4)
    return mb


def props():
    return {"elevator": True, "locked": False, "public": True, "parked_level": 1, "doors_open_level": 1,
            "capacity_kg": 1000, "capacity_persons": 12, "cabin_clear_m": "1.9 x 2.2 x 2.2",
            "door_clear_m": LIFT_DOOR_W,
            "control": "call button on every landing; cabin buttons 1-4, stop, dispatcher call, door open"}
