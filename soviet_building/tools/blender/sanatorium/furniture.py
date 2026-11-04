"""Low-poly furniture and equipment modules. Every module is built once and instanced.

Convention: origin at floor level in the centre of the footprint, front faces local -Y,
footprint x in [-w/2, w/2], y in [-d/2, d/2]. Detail lives in the atlas textures."""
import math
from .meshkit import MB
from .atlas import FURN_UV, DECAL_UV

A, DEC = "atlas_furn", "atlas_decal"


def bx(mb, x0, x1, y0, y1, z0, z1, regions, faces=("-x", "+x", "-y", "+y", "+z"), mat=A):
    mb.box(x0, x1, y0, y1, z0, z1, mat, faces=faces, uv="region", regions=regions)


def quad(mb, pts, region, mat=A, want=None):
    u0, v0, u1, v1 = (DECAL_UV if "decal" in mat else FURN_UV)[region]
    uv = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    if want:
        mb.poly_n(pts, uv, mat, want)
    else:
        mb.poly(pts, uv, mat)


def legs_alpha(mb, w, d, h, region="chair_legs_wood"):
    """Two crossed side-silhouette quads instead of four leg boxes (double-sided alpha)."""
    for x in (-w / 2 + 0.02, w / 2 - 0.02):
        quad(mb, [(x, -d / 2, 0), (x, d / 2, 0), (x, d / 2, h), (x, -d / 2, h)], region, DEC)


def cyl_r(mb, cx, cy, z0, z1, r, region, sides=8, top=True):
    mb.cyl(cx, cy, z0, z1, r, A, sides=sides, top=top, bottom=False, region=region)


# ----------------------------------------------------------------------------- bedroom
def bed(style="blanket"):
    mb = MB("bed")
    w, d = 0.9, 2.0
    bx(mb, -w / 2, w / 2, -d / 2, d / 2, 0.12, 0.38, {"*": "wood_plain"}, ("-x", "+x", "-y", "+y"))
    top = {"blanket": "blanket", "linen": "linen_white", "bare": "mattress"}[style]
    bx(mb, -w / 2 + 0.02, w / 2 - 0.02, -d / 2 + 0.03, d / 2 - 0.03, 0.38, 0.55,
       {"*": "mattress" if style == "bare" else "linen_white", "+z": top}, ("-x", "+x", "-y", "+y", "+z"))
    if style != "bare":
        bx(mb, -0.32, 0.32, d / 2 - 0.45, d / 2 - 0.08, 0.55, 0.66, {"*": "pillow"}, ("-y", "+z"))
    bx(mb, -w / 2 - 0.02, w / 2 + 0.02, d / 2 - 0.04, d / 2, 0.0, 0.95, {"*": "wood_plain"}, ("-x", "+x", "-y", "+y", "+z"))
    bx(mb, -w / 2 - 0.02, w / 2 + 0.02, -d / 2, -d / 2 + 0.04, 0.0, 0.62, {"*": "wood_plain"}, ("-x", "+x", "-y", "+y", "+z"))
    return mb


def bed_hospital():
    mb = MB("bed_hospital")
    w, d = 0.95, 2.05
    bx(mb, -w / 2, w / 2, -d / 2, d / 2, 0.45, 0.52, {"*": "metal_white"}, ("-x", "+x", "-y", "+y", "-z"))
    bx(mb, -w / 2 + 0.03, w / 2 - 0.03, -d / 2 + 0.05, d / 2 - 0.05, 0.52, 0.66,
       {"*": "mattress", "+z": "linen_white"}, ("-x", "+x", "-y", "+y", "+z"))
    for y, h in ((d / 2 - 0.02, 1.05), (-d / 2 + 0.02, 0.85)):
        quad(mb, [(-w / 2, y, 0.0), (w / 2, y, 0.0), (w / 2, y, h), (-w / 2, y, h)], "bed_head_tube", DEC)
    for x in (-w / 2 + 0.03, w / 2 - 0.03):   # side legs as silhouettes
        quad(mb, [(x, -d / 2, 0), (x, d / 2, 0), (x, d / 2, 0.47), (x, -d / 2, 0.47)], "chair_legs_tube", DEC)
    return mb


def bedside():
    mb = MB("bedside")
    bx(mb, -0.22, 0.22, -0.2, 0.2, 0, 0.62, {"*": "wood_plain", "-y": "bedside_front"})
    return mb


def wardrobe(w=1.0):
    mb = MB("wardrobe")
    bx(mb, -w / 2, w / 2, -0.28, 0.28, 0, 1.9, {"*": "wood_plain", "-y": "wardrobe_front"})
    return mb


def desk_small():
    mb = MB("desk_small")
    w, d, h = 1.0, 0.55, 0.75
    bx(mb, -w / 2, w / 2, -d / 2, d / 2, h - 0.03, h, {"*": "wood_plain"}, ("-x", "+x", "-y", "+y", "+z", "-z"))
    bx(mb, w / 2 - 0.42, w / 2 - 0.02, -d / 2 + 0.02, d / 2 - 0.02, 0, h - 0.03, {"*": "wood_plain", "-y": "bedside_front"},
       ("-x", "+x", "-y"))
    bx(mb, -w / 2 + 0.02, -w / 2 + 0.05, -d / 2 + 0.02, d / 2 - 0.02, 0, h - 0.03, {"*": "wood_plain"}, ("-x", "+x", "-y"))
    return mb


def desk_office(w=1.4):
    mb = MB("desk_office")
    d, h = 0.75, 0.76
    bx(mb, -w / 2, w / 2, -d / 2, d / 2, h - 0.035, h, {"*": "wood_dark", "+z": "wood_plain"},
       ("-x", "+x", "-y", "+y", "+z", "-z"))
    bx(mb, -w / 2 + 0.02, w / 2 - 0.02, -d / 2 + 0.03, d / 2 - 0.03, 0, h - 0.035,
       {"*": "wood_plain", "+y": "desk_front"}, ("-x", "+x", "+y", "-y"))
    return mb


def chair(style="wood"):
    mb = MB("chair")
    w, d = 0.42, 0.42
    seat = {"wood": "wood_plain", "tube": "upholstery_brown", "green": "upholstery_green"}[style]
    bx(mb, -w / 2, w / 2, -d / 2, d / 2, 0.42, 0.46, {"*": seat}, ("-x", "+x", "-y", "+y", "+z", "-z"))
    bx(mb, -w / 2, w / 2, d / 2 - 0.03, d / 2, 0.62, 0.9, {"*": seat if style != "wood" else "wood_plain"},
       ("-x", "+x", "-y", "+y", "+z"))
    legs_alpha(mb, w, d, 0.43, "chair_legs_tube" if style != "wood" else "chair_legs_wood")
    for x in (-w / 2 + 0.02, w / 2 - 0.02):
        quad(mb, [(x, d / 2 - 0.02, 0.43), (x, d / 2, 0.43), (x, d / 2, 0.62), (x, d / 2 - 0.02, 0.62)],
             "chair_legs_tube" if style != "wood" else "chair_legs_wood", DEC)
    return mb


def armchair(region="upholstery_brown"):
    mb = MB("armchair")
    w, d = 0.7, 0.75
    bx(mb, -w / 2 + 0.08, w / 2 - 0.08, -d / 2, d / 2 - 0.12, 0.18, 0.42, {"*": region}, ("-x", "+x", "-y", "+z"))
    bx(mb, -w / 2 + 0.08, w / 2 - 0.08, d / 2 - 0.15, d / 2, 0.18, 0.85, {"*": region}, ("-x", "+x", "-y", "+y", "+z"))
    for x0, x1 in ((-w / 2, -w / 2 + 0.08), (w / 2 - 0.08, w / 2)):
        bx(mb, x0, x1, -d / 2, d / 2, 0.0, 0.6, {"*": "wood_plain"}, ("-x", "+x", "-y", "+y", "+z"))
    return mb


def sofa(w=1.8):
    mb = MB("sofa")
    d = 0.8
    bx(mb, -w / 2 + 0.1, w / 2 - 0.1, -d / 2, d / 2 - 0.15, 0.1, 0.42, {"*": "upholstery_green"}, ("-x", "+x", "-y", "+z"))
    bx(mb, -w / 2 + 0.1, w / 2 - 0.1, d / 2 - 0.18, d / 2, 0.1, 0.9, {"*": "upholstery_green"},
       ("-x", "+x", "-y", "+y", "+z"))
    for x0, x1 in ((-w / 2, -w / 2 + 0.1), (w / 2 - 0.1, w / 2)):
        bx(mb, x0, x1, -d / 2, d / 2, 0.0, 0.62, {"*": "wood_plain"}, ("-x", "+x", "-y", "+y", "+z"))
    return mb


def table(w=0.8, d=0.8, h=0.75, top="wood_plain"):
    mb = MB("table")
    bx(mb, -w / 2, w / 2, -d / 2, d / 2, h - 0.03, h, {"*": "wood_dark", "+z": top}, ("-x", "+x", "-y", "+y", "+z", "-z"))
    legs_alpha(mb, w, d, h - 0.03, "chair_legs_wood")
    return mb


def table_lamp():
    mb = MB("table_lamp")
    bx(mb, -0.07, 0.07, -0.07, 0.07, 0, 0.03, {"*": "black_plastic"}, ("-y", "+z"))
    bx(mb, -0.01, 0.01, -0.01, 0.01, 0.03, 0.32, {"*": "chrome"}, ("-x", "-y"))
    pts_b = [(-0.13, -0.13, 0.30), (0.13, -0.13, 0.30), (0.13, 0.13, 0.30), (-0.13, 0.13, 0.30)]
    pts_t = [(-0.07, -0.07, 0.46), (0.07, -0.07, 0.46), (0.07, 0.07, 0.46), (-0.07, 0.07, 0.46)]
    for k in range(4):
        k2 = (k + 1) % 4
        quad(mb, [pts_b[k], pts_b[k2], pts_t[k2], pts_t[k]], "lamp_shade")
    return mb


def sink_wall():
    mb = MB("sink")
    bx(mb, -0.25, 0.25, -0.2, 0.2, 0.68, 0.85, {"*": "porcelain"}, ("-x", "+x", "-y", "+z", "-z"))
    bx(mb, -0.02, 0.02, 0.1, 0.2, 0.85, 1.0, {"*": "chrome"}, ("-x", "-y", "+z"))
    quad(mb, [(-0.25, 0.195, 1.15), (0.25, 0.195, 1.15), (0.25, 0.195, 1.65), (-0.25, 0.195, 1.65)], "mirror",
         want=(0, -1, 0))
    return mb


def radiator(w=1.4):
    mb = MB("radiator")
    bx(mb, -w / 2, w / 2, -0.05, 0.05, 0.1, 0.7, {"*": "metal_cream", "-y": "radiator", "+z": "radiator"},
       ("-x", "+x", "-y", "+z"))
    return mb


def curtains(w=2.0, h=2.1):
    mb = MB("curtains")
    quad(mb, [(-w / 2, 0, 0), (w / 2, 0, 0), (w / 2, 0, h), (-w / 2, 0, h)], "tulle", "atlas_decal_blend")
    for x0, x1 in ((-w / 2 - 0.2, -w / 2 + 0.25), (w / 2 - 0.25, w / 2 + 0.2)):
        quad(mb, [(x0, -0.05, 0), (x1, -0.05, 0), (x1, -0.05, h + 0.1), (x0, -0.05, h + 0.1)], "curtain_heavy", DEC)
    return mb


def wall_quad(region, w, h, mat=DEC):
    """Flat item on a wall: front faces -Y, back at y=0 (poster, plan, carpet...)."""
    mb = MB("wq_" + region)
    quad(mb, [(-w / 2, -0.004, 0), (w / 2, -0.004, 0), (w / 2, -0.004, h), (-w / 2, -0.004, h)], region, mat, (0, -1, 0))
    return mb


def floor_quad(region, w, d, mat=DEC, z=0.004):
    mb = MB("fq_" + region)
    quad(mb, [(-w / 2, -d / 2, z), (w / 2, -d / 2, z), (w / 2, d / 2, z), (-w / 2, d / 2, z)], region, mat, (0, 0, 1))
    return mb


def wall_box(region, w, h, t, side="metal_grey"):
    """Wall-hung box (clock, cabinets, panels) with the textured front facing -Y; origin at its bottom."""
    mb = MB("wb_" + region)
    bx(mb, -w / 2, w / 2, -t, 0, 0, h, {"*": side, "-y": region}, ("-x", "+x", "-y", "+z", "-z"))
    return mb


# ----------------------------------------------------------------------------- office
def cabinet(region, w, d, h, side="wood_plain"):
    mb = MB("cab_" + region)
    bx(mb, -w / 2, w / 2, -d / 2, d / 2, 0, h, {"*": side, "-y": region})
    return mb


def typewriter():
    mb = MB("typewriter")
    bx(mb, -0.22, 0.22, -0.18, 0.18, 0, 0.12, {"*": "black_plastic", "+z": "typewriter_top"}, ("-x", "+x", "-y", "+y", "+z"))
    bx(mb, -0.25, 0.25, 0.08, 0.16, 0.12, 0.2, {"*": "black_plastic"}, ("-x", "+x", "-y", "+y", "+z"))
    return mb


def telephone():
    mb = MB("telephone")
    bx(mb, -0.11, 0.11, -0.1, 0.1, 0, 0.08, {"*": "black_plastic", "+z": "telephone"}, ("-x", "+x", "-y", "+y", "+z"))
    bx(mb, -0.12, 0.12, 0.02, 0.08, 0.08, 0.12, {"*": "black_plastic"}, ("-x", "+x", "-y", "+y", "+z"))
    return mb


def papers(k=1):
    return floor_quad(f"papers_{k}", 0.45, 0.45, DEC, z=0.003)


def paper_stack():
    mb = MB("paper_stack")
    bx(mb, -0.15, 0.15, -0.11, 0.11, 0, 0.06, {"*": "paper_stack"}, ("-x", "+x", "-y", "+y", "+z"))
    return mb


def meeting_table(w=2.6, d=1.0):
    mb = table(w, d, 0.76, "upholstery_green")
    return mb


def coat_stand():
    mb = MB("coat_stand")
    mb.tube_region([(0, 0, 0.02), (0, 0, 1.75)], 0.02, "wood_dark", 4, cap1=True)
    for a in range(3):
        th = a * 2.094
        mb.tube_region([(0, 0, 1.6), (0.18 * math.cos(th), 0.18 * math.sin(th), 1.7)], 0.012, "wood_dark", 3)
        mb.tube_region([(0, 0, 0.1), (0.25 * math.cos(th), 0.25 * math.sin(th), 0.02)], 0.015, "wood_dark", 3)
    return mb


def tv():
    mb = MB("tv")
    bx(mb, -0.32, 0.32, -0.25, 0.25, 0.55, 1.05, {"*": "wood_dark", "-y": "tv_front"}, ("-x", "+x", "-y", "+y", "+z"))
    legs_alpha(mb, 0.6, 0.45, 0.55, "chair_legs_tube")
    return mb


def piano():
    mb = MB("piano")
    bx(mb, -0.75, 0.75, -0.3, 0.3, 0, 1.25, {"*": "wood_dark", "-y": "piano_front"}, ("-x", "+x", "-y", "+y", "+z"))
    bx(mb, -0.72, 0.72, -0.48, -0.3, 0.66, 0.74, {"*": "wood_dark", "+z": "piano_front"}, ("-x", "+x", "-y", "+z"))
    return mb


def bench(w=1.6):
    mb = MB("bench")
    bx(mb, -w / 2, w / 2, -0.2, 0.2, 0.42, 0.46, {"*": "wood_light"}, ("-x", "+x", "-y", "+y", "+z", "-z"))
    bx(mb, -w / 2, w / 2, 0.16, 0.2, 0.55, 0.85, {"*": "wood_light"}, ("-x", "+x", "-y", "+y", "+z"))
    legs_alpha(mb, w, 0.4, 0.43, "chair_legs_tube")
    return mb


def seat_row(n=3):
    """Linked waiting-room seats (bent plywood on a steel beam)."""
    mb = MB("seat_row")
    w = 0.52 * n
    bx(mb, -w / 2, w / 2, -0.22, 0.2, 0.42, 0.47, {"*": "wood_light"}, ("-x", "+x", "-y", "+y", "+z", "-z"))
    bx(mb, -w / 2, w / 2, 0.16, 0.21, 0.55, 0.88, {"*": "wood_light"}, ("-x", "+x", "-y", "+y", "+z"))
    legs_alpha(mb, w - 0.1, 0.42, 0.42, "chair_legs_tube")
    return mb


def plant(kind=1, h=1.1):
    mb = MB("plant")
    cyl_r(mb, 0, 0, 0, 0.32, 0.16, "cardboard" if kind == 1 else "red_paint", sides=6)
    for a in (0.0, math.pi / 2):
        c, s = math.cos(a) * 0.4, math.sin(a) * 0.4
        quad(mb, [(-c, -s, 0.25), (c, s, 0.25), (c, s, 0.25 + h), (-c, -s, 0.25 + h)], f"plant_{kind}", DEC)
    return mb


def fire_ext():
    mb = MB("fire_ext")
    cyl_r(mb, 0, -0.08, 0.6, 1.1, 0.075, "red_paint", sides=6)
    bx(mb, -0.03, 0.03, -0.1, -0.06, 1.1, 1.16, {"*": "black_plastic"}, ("-x", "+x", "-y", "+z"))
    return mb


def clock():
    return wall_box("clock_face", 0.32, 0.32, 0.05, "black_plastic")


def cleaning_cart():
    mb = MB("cleaning_cart")
    bx(mb, -0.35, 0.35, -0.25, 0.25, 0.1, 0.75, {"*": "bucket_blue"}, ("-x", "+x", "-y", "+y", "+z"))
    cyl_r(mb, 0.15, 0, 0.75, 0.98, 0.14, "bucket_blue", sides=6)
    mb.tube_region([(-0.3, 0.1, 0.75), (-0.42, 0.25, 1.75)], 0.012, "wood_light", 4)
    return mb


def bucket():
    mb = MB("bucket")
    cyl_r(mb, 0, 0, 0, 0.3, 0.15, "enamel_pot", sides=6)
    return mb


# ----------------------------------------------------------------------------- medical
def exam_couch():
    mb = MB("exam_couch")
    w, d = 0.65, 1.9
    bx(mb, -w / 2, w / 2, -d / 2, d / 2 - 0.5, 0.5, 0.62, {"*": "exam_couch"}, ("-x", "+x", "-y", "+y", "+z"))
    pts = [(-w / 2, d / 2 - 0.5, 0.62), (w / 2, d / 2 - 0.5, 0.62), (w / 2, d / 2, 0.85), (-w / 2, d / 2, 0.85)]
    quad(mb, pts, "exam_couch")
    quad(mb, [(-w / 2, d / 2, 0.5), (w / 2, d / 2, 0.5), (w / 2, d / 2, 0.85), (-w / 2, d / 2, 0.85)], "exam_couch")
    for x in (-w / 2 + 0.03, w / 2 - 0.03):
        quad(mb, [(x, -d / 2, 0), (x, d / 2, 0), (x, d / 2, 0.5), (x, -d / 2, 0.5)], "chair_legs_tube", DEC)
    return mb


def instrument_table():
    mb = MB("instrument_table")
    for z in (0.35, 0.82):
        bx(mb, -0.3, 0.3, -0.22, 0.22, z, z + 0.03, {"*": "steel"}, ("-x", "+x", "-y", "+y", "+z", "-z"))
    legs_alpha(mb, 0.6, 0.44, 0.82, "chair_legs_tube")
    bx(mb, -0.2, 0.05, -0.12, 0.08, 0.85, 0.92, {"*": "enamel_pot"}, ("-x", "+x", "-y", "+y", "+z"))
    return mb


def screen3():
    mb = MB("screen")
    for k, (x0, x1, y0, y1) in enumerate(((-0.9, -0.33, 0.15, -0.05), (-0.3, 0.3, -0.05, -0.05), (0.33, 0.9, -0.05, 0.15))):
        # front and back faces 15 mm apart (coincident opposite faces render black in Cycles)
        quad(mb, [(x0, y0 - 0.008, 0.15), (x1, y1 - 0.008, 0.15), (x1, y1 - 0.008, 1.7), (x0, y0 - 0.008, 1.7)], "screen_fabric")
        quad(mb, [(x1, y1 + 0.008, 0.15), (x0, y0 + 0.008, 0.15), (x0, y0 + 0.008, 1.7), (x1, y1 + 0.008, 1.7)], "screen_fabric")
    return mb


def scale_med():
    mb = MB("scale")
    bx(mb, -0.25, 0.25, -0.3, 0.3, 0, 0.12, {"*": "metal_white", "+z": "rubber_black"})
    bx(mb, -0.04, 0.04, 0.22, 0.3, 0.12, 1.4, {"*": "metal_white"}, ("-x", "+x", "-y", "+y"))
    bx(mb, -0.2, 0.2, 0.18, 0.3, 1.4, 1.5, {"*": "metal_white", "-y": "steel"})
    return mb


def iv_stand():
    mb = MB("iv_stand")
    mb.tube_region([(0, 0, 0.02), (0, 0, 1.9)], 0.012, "chrome", 5, cap1=True)
    mb.tube_region([(-0.15, 0, 1.85), (0.15, 0, 1.85)], 0.008, "chrome", 4)
    for a in range(4):
        th = a * math.pi / 2
        mb.tube_region([(0, 0, 0.05), (0.28 * math.cos(th), 0.28 * math.sin(th), 0.02)], 0.012, "chrome", 4)
    return mb


def wheelchair():
    mb = MB("wheelchair")
    bx(mb, -0.23, 0.23, -0.22, 0.2, 0.48, 0.52, {"*": "upholstery_brown"}, ("-x", "+x", "-y", "+y", "+z", "-z"))
    quad(mb, [(-0.23, 0.2, 0.52), (0.23, 0.2, 0.52), (0.23, 0.24, 0.95), (-0.23, 0.24, 0.95)], "upholstery_brown")
    for x in (-0.3, 0.3):
        quad(mb, [(x, -0.28, 0.0), (x, 0.32, 0.0), (x, 0.32, 0.6), (x, -0.28, 0.6)], "wheel", DEC)
    return mb


def stretcher():
    mb = MB("stretcher")
    bx(mb, -0.3, 0.3, -0.95, 0.95, 0.72, 0.8, {"*": "metal_white", "+z": "mattress"}, ("-x", "+x", "-y", "+y", "+z"))
    legs_alpha(mb, 0.6, 1.8, 0.72, "chair_legs_tube")
    return mb


def oxygen():
    mb = MB("oxygen")
    cyl_r(mb, 0, 0, 0, 1.3, 0.11, "metal_green", sides=8)
    return mb


def microscope():
    mb = MB("microscope")
    bx(mb, -0.1, 0.1, -0.12, 0.12, 0, 0.04, {"*": "black_plastic"})
    bx(mb, -0.025, 0.025, 0.04, 0.1, 0.04, 0.32, {"*": "black_plastic"}, ("-x", "+x", "-y", "+y", "+z"))
    mb.tube_region([(0, 0.07, 0.3), (0, -0.02, 0.38)], 0.02, "chrome", 6, cap1=True)
    return mb


def centrifuge():
    mb = MB("centrifuge")
    cyl_r(mb, 0, 0, 0, 0.3, 0.2, "metal_white", sides=8)
    return mb


# ----------------------------------------------------------------------------- kitchen
def stove():
    mb = MB("stove")
    bx(mb, -0.52, 0.52, -0.42, 0.42, 0, 0.85, {"*": "steel", "-y": "stove_front", "+z": "stove_top"})
    return mb


def kettle():
    mb = MB("kettle")
    cyl_r(mb, 0, 0, 0, 0.95, 0.42, "steel", sides=10)
    bx(mb, -0.08, 0.08, -0.5, -0.4, 0.15, 0.3, {"*": "steel"}, ("-x", "+x", "-y", "+z"))
    return mb


def prep_table(w=1.5):
    mb = MB("prep_table")
    bx(mb, -w / 2, w / 2, -0.4, 0.4, 0.82, 0.86, {"*": "steel"}, ("-x", "+x", "-y", "+y", "+z", "-z"))
    bx(mb, -w / 2 + 0.05, w / 2 - 0.05, -0.35, 0.35, 0.18, 0.21, {"*": "steel"}, ("-x", "+x", "-y", "+y", "+z"))
    legs_alpha(mb, w - 0.05, 0.75, 0.82, "chair_legs_tube")
    return mb


def kitchen_sink(w=1.2):
    mb = MB("kitchen_sink")
    bx(mb, -w / 2, w / 2, -0.3, 0.3, 0.55, 0.88, {"*": "steel", "+z": "black_plastic"}, ("-x", "+x", "-y", "+y", "+z"))
    legs_alpha(mb, w - 0.05, 0.55, 0.55, "chair_legs_tube")
    bx(mb, -0.02, 0.02, 0.22, 0.3, 0.88, 1.1, {"*": "chrome"}, ("-x", "+x", "-y", "+z"))
    return mb


def rack(region, w=1.2, d=0.5, h=1.8):
    """Shelf rack: the textured front shows the stored goods; sides are uprights."""
    mb = MB("rack_" + region)
    bx(mb, -w / 2, w / 2, -d / 2, d / 2, 0, h, {"*": "metal_grey", "-y": region, "+z": "metal_grey"},
       ("-x", "+x", "-y", "+z"))
    return mb


def crate_stack():
    mb = MB("crates")
    bx(mb, -0.3, 0.3, -0.2, 0.2, 0, 0.6, {"*": "crates", "+z": "cardboard"})
    return mb


def sack():
    mb = MB("sack")
    bx(mb, -0.25, 0.25, -0.18, 0.18, 0, 0.7, {"*": "sacks"})
    return mb


def serving_line(w=2.4):
    mb = MB("serving_line")
    bx(mb, -w / 2, w / 2, -0.35, 0.35, 0, 0.88, {"*": "steel", "-y": "steel"})
    mb.tube_region([(-w / 2, -0.5, 0.82), (w / 2, -0.5, 0.82)], 0.02, "chrome", 4)
    mb.tube_region([(-w / 2, -0.4, 0.82), (w / 2, -0.4, 0.82)], 0.02, "chrome", 4)
    return mb


def dishwasher():
    mb = MB("dishwasher")
    bx(mb, -0.6, 0.6, -0.4, 0.4, 0, 1.5, {"*": "steel", "-y": "stove_front"})
    return mb


def peeler():
    mb = MB("peeler")
    cyl_r(mb, 0, 0, 0, 0.9, 0.28, "steel", sides=8)
    return mb


# ----------------------------------------------------------------------------- technical
def workbench():
    mb = MB("workbench")
    bx(mb, -0.8, 0.8, -0.35, 0.35, 0.8, 0.86, {"*": "wood_light"}, ("-x", "+x", "-y", "+y", "+z", "-z"))
    bx(mb, 0.25, 0.78, -0.33, 0.33, 0, 0.8, {"*": "metal_green", "-y": "filing_front"}, ("-x", "+x", "-y"))
    legs_alpha(mb, 1.55, 0.65, 0.8, "chair_legs_tube")
    bx(mb, -0.75, -0.55, -0.3, -0.15, 0.86, 1.0, {"*": "metal_grey"})
    return mb


def pump_unit():
    mb = MB("pump")
    bx(mb, -0.6, 0.6, -0.3, 0.3, 0, 0.2, {"*": "concrete"})
    bx(mb, -0.5, 0.0, -0.22, 0.22, 0.2, 0.62, {"*": "pump"})
    mb.cyl(0.0, 0.0, 0.0, 0.5, 0.2, A, sides=8, top=True, bottom=True, region="pump", axis="x")
    return mb


def boiler():
    mb = MB("boiler")
    cyl_r(mb, 0, 0, 0, 1.9, 0.38, "metal_grey", sides=10)
    return mb


def duct(length, w=0.6, h=0.4):
    mb = MB("duct")
    bx(mb, -length / 2, length / 2, -w / 2, w / 2, 0, h, {"*": "aluminium"}, ("-y", "+y", "-z", "+z"))
    return mb


def locker():
    mb = MB("locker")
    bx(mb, -0.25, 0.25, -0.25, 0.25, 0, 1.85, {"*": "metal_grey", "-y": "door_steel"})
    return mb


def laundry_cart():
    mb = MB("laundry_cart")
    bx(mb, -0.4, 0.4, -0.3, 0.3, 0.15, 0.95, {"*": "screen_fabric", "+z": "linen_white"})
    legs_alpha(mb, 0.8, 0.6, 0.15, "chair_legs_tube")
    return mb


def bin_():
    mb = MB("bin")
    cyl_r(mb, 0, 0, 0, 0.8, 0.28, "metal_green", sides=8)
    return mb


def toilet():
    mb = MB("toilet")
    bx(mb, -0.19, 0.19, -0.3, 0.2, 0, 0.4, {"*": "porcelain"})
    bx(mb, -0.22, 0.22, 0.05, 0.25, 1.75, 2.0, {"*": "porcelain"}, ("-x", "+x", "-y", "+z", "-z"))  # high cistern
    quad(mb, [(-0.02, 0.2, 0.35), (0.02, 0.2, 0.35), (0.02, 0.2, 1.75), (-0.02, 0.2, 1.75)], "chrome", A, (0, -1, 0))
    return mb


def urinal():
    mb = MB("urinal")
    bx(mb, -0.2, 0.2, -0.32, 0.0, 0.45, 1.05, {"*": "porcelain"}, ("-x", "+x", "-y", "+z", "-z"))
    return mb


def cubicle(w=0.95, d=1.4, h=1.9):
    """WC / shower cubicle: two side partitions and a door panel (front, half open)."""
    mb = MB("cubicle")
    for x in (-w / 2, w / 2):
        bx(mb, x - 0.02, x + 0.02, -d / 2, d / 2, 0.15, h, {"*": "partition"}, ("-x", "+x", "-y", "+z"))
    return mb


def shower():
    mb = MB("shower")
    bx(mb, -0.45, 0.45, -0.45, 0.45, 0, 0.08, {"*": "porcelain"}, ("-x", "+x", "-y", "+y", "+z"))
    quad(mb, [(-0.015, 0.44, 0.8), (0.015, 0.44, 0.8), (0.015, 0.44, 2.05), (-0.015, 0.44, 2.05)], "chrome", A, (0, -1, 0))
    bx(mb, -0.05, 0.05, 0.25, 0.44, 2.02, 2.06, {"*": "chrome"}, ("-x", "+x", "-y", "-z"))
    quad(mb, [(-0.45, -0.45, 0.2), (0.45, -0.45, 0.2), (0.45, -0.45, 2.0), (-0.45, -0.45, 2.0)], "tulle",
         "atlas_decal_blend")
    return mb


def grab_bar(l=0.8):
    mb = MB("grab_bar")
    mb.tube_region([(-l / 2, -0.07, 0), (-l / 2, -0.07, 0.0), (l / 2, -0.07, 0)], 0.017, "chrome", 6, True, True)
    return mb


def bathtub():
    mb = MB("bathtub")
    bx(mb, -0.35, 0.35, -0.85, 0.85, 0, 0.55, {"*": "enamel_pot", "+z": "porcelain"})
    return mb


def stage(w, d, h=0.6):
    mb = MB("stage")
    bx(mb, -w / 2, w / 2, -d / 2, d / 2, 0, h, {"*": "wood_dark", "+z": "wood_plain"}, ("-y", "+z", "-x", "+x"))
    return mb


def projector():
    mb = MB("projector")
    bx(mb, -0.25, 0.25, -0.4, 0.4, 0.0, 0.9, {"*": "metal_green"})
    bx(mb, -0.2, 0.2, -0.45, 0.35, 0.9, 1.3, {"*": "metal_grey"})
    mb.cyl(0.0, 1.15, -0.65, -0.45, 0.06, A, sides=6, top=True, bottom=False, region="chrome", axis="y")
    for y in (-0.25, 0.25):
        mb.cyl(y, 1.55, -0.03, 0.03, 0.28, A, sides=8, top=True, bottom=True, region="aluminium", axis="x")
    return mb


def ladder(h):
    mb = MB("ladder")
    for x in (-0.22, 0.22):
        mb.tube_region([(x, 0, 0), (x, 0, h)], 0.018, "metal_grey", 4)
    z = 0.3
    while z < h:
        mb.tube_region([(-0.22, 0, z), (0.22, 0, z)], 0.012, "metal_grey", 4)
        z += 0.3
    return mb


def hatch():
    mb = MB("hatch")
    bx(mb, -0.4, 0.4, -0.4, 0.4, -0.03, 0, {"*": "door_steel"}, ("-x", "+x", "-y", "+y", "-z"))
    return mb


def radio():
    return wall_box("vent_unit", 0.18, 0.12, 0.08, "wood_dark")


def mirror_frame():
    return wall_quad("mirror", 0.5, 0.6, A)


DIMS = {}   # key -> (w, d) footprint, filled by register()


def cinema_row(n=8):
    mb = MB("cinema_row")
    w = 0.52 * n
    bx(mb, -w / 2, w / 2, -0.25, 0.25, 0.0, 0.9, {"*": "velvet_red", "-y": "cinema_seats", "+y": "wood_dark",
                                                    "+z": "wood_dark"})
    return mb


def curtains_tulle(w=2.0, h=1.9):
    mb = MB("curtains_tulle")
    quad(mb, [(-w / 2, 0, 0), (w / 2, 0, 0), (w / 2, 0, h), (-w / 2, 0, h)], "tulle", "atlas_decal_blend")
    return mb


def stage_curtain(w, h):
    mb = MB("stage_curtain")
    quad(mb, [(-w / 2, 0, 0), (w / 2, 0, 0), (w / 2, 0, h), (-w / 2, 0, h)], "stage_curtain", A, (0, -1, 0))
    return mb


def M(fn, w, d):
    return (fn, w, d)


MODS = {
    "bed": M(lambda: bed("blanket"), 0.94, 2.0), "bed_linen": M(lambda: bed("linen"), 0.94, 2.0),
    "bed_bare": M(lambda: bed("bare"), 0.94, 2.0), "bed_hospital": M(bed_hospital, 0.95, 2.05),
    "bedside": M(bedside, 0.44, 0.4), "wardrobe": M(wardrobe, 1.0, 0.56), "wardrobe_wide": M(lambda: wardrobe(1.4), 1.4, 0.56),
    "desk_small": M(desk_small, 1.0, 0.55), "desk_office": M(desk_office, 1.4, 0.75),
    "desk_wide": M(lambda: desk_office(1.6), 1.6, 0.75),
    "chair": M(lambda: chair("wood"), 0.42, 0.45), "chair_tube": M(lambda: chair("tube"), 0.42, 0.45),
    "chair_green": M(lambda: chair("green"), 0.42, 0.45), "armchair": M(armchair, 0.7, 0.75),
    "armchair_green": M(lambda: armchair("upholstery_green"), 0.7, 0.75), "sofa": M(sofa, 1.8, 0.8),
    "table_sq": M(lambda: table(0.8, 0.8), 0.8, 0.8), "table_small": M(lambda: table(0.6, 0.6, 0.72), 0.6, 0.6),
    "table_dining": M(lambda: table(1.2, 0.8, 0.75, "metal_white"), 1.2, 0.8),
    "table_coffee": M(lambda: table(0.9, 0.55, 0.5), 0.9, 0.55),
    "table_lab": M(lambda: table(1.4, 0.7, 0.85, "metal_white"), 1.4, 0.7),
    "table_lamp": M(table_lamp, 0.26, 0.26), "sink": M(sink_wall, 0.5, 0.4),
    "radiator": M(radiator, 1.4, 0.1), "radiator_hall": M(lambda: radiator(1.8), 1.8, 0.1),
    "curtains": M(lambda: curtains(2.0, 1.9), 2.4, 0.1), "curtains_tulle": M(curtains_tulle, 2.2, 0.06),
    "bookcase": M(lambda: cabinet("bookcase_front", 0.9, 0.4, 1.9), 0.9, 0.4),
    "filing": M(lambda: cabinet("filing_front", 0.5, 0.6, 1.3, "metal_green"), 0.5, 0.6),
    "med_cabinet": M(lambda: cabinet("med_cabinet_front", 0.8, 0.4, 1.8, "metal_white"), 0.8, 0.4),
    "safe": M(lambda: cabinet("safe_front", 0.6, 0.55, 0.9, "metal_green"), 0.6, 0.55),
    "fridge": M(lambda: cabinet("fridge_front", 0.6, 0.6, 1.5, "metal_white"), 0.6, 0.6),
    "fridge_ind": M(lambda: cabinet("fridge_front", 1.2, 0.7, 2.0, "steel"), 1.2, 0.7),
    "elec_cabinet": M(lambda: cabinet("elec_panel", 0.8, 0.35, 1.9, "metal_green"), 0.8, 0.35),
    "binders": M(lambda: rack("binders", 1.0, 0.4, 2.0), 1.0, 0.4),
    "books": M(lambda: rack("book_spines", 1.0, 0.35, 1.9), 1.0, 0.35),
    "linen_rack": M(lambda: rack("linen_stack", 1.2, 0.5, 2.0), 1.2, 0.5),
    "goods_rack": M(lambda: rack("shelf_goods", 1.2, 0.5, 1.9), 1.2, 0.5),
    "dish_rack": M(lambda: rack("dish_rack", 1.2, 0.5, 1.8), 1.2, 0.5),
    "medbox_rack": M(lambda: rack("med_boxes", 1.0, 0.4, 1.9), 1.0, 0.4),
    "tool_rack": M(lambda: rack("tools_board", 1.2, 0.4, 1.9), 1.2, 0.4),
    "lab_rack": M(lambda: rack("lab_equipment", 1.2, 0.6, 1.0), 1.2, 0.6),
    "typewriter": M(typewriter, 0.5, 0.36), "telephone": M(telephone, 0.24, 0.2), "paper_stack": M(paper_stack, 0.3, 0.22),
    "papers_1": M(lambda: papers(1), 0.45, 0.45), "papers_2": M(lambda: papers(2), 0.45, 0.45),
    "meeting_table": M(meeting_table, 2.4, 1.0), "coat_stand": M(coat_stand, 0.5, 0.5), "tv": M(tv, 0.64, 0.5),
    "piano": M(piano, 1.5, 0.8), "bench": M(bench, 1.6, 0.4), "seat_row": M(seat_row, 1.56, 0.44),
    "plant_1": M(lambda: plant(1), 0.4, 0.4), "plant_2": M(lambda: plant(2, 0.8), 0.4, 0.4),
    "fire_ext": M(fire_ext, 0.16, 0.2), "cleaning_cart": M(cleaning_cart, 0.7, 0.5), "bucket": M(bucket, 0.3, 0.3),
    "exam_couch": M(exam_couch, 0.65, 1.9), "instrument_table": M(instrument_table, 0.6, 0.44),
    "screen": M(screen3, 1.8, 0.3), "scale": M(scale_med, 0.5, 0.6), "iv_stand": M(iv_stand, 0.56, 0.56),
    "wheelchair": M(wheelchair, 0.62, 0.6), "stretcher": M(stretcher, 0.6, 1.9), "oxygen": M(oxygen, 0.22, 0.22),
    "microscope": M(microscope, 0.2, 0.24), "centrifuge": M(centrifuge, 0.4, 0.4),
    "stove": M(stove, 1.04, 0.84), "kettle": M(kettle, 0.84, 0.84), "prep_table": M(prep_table, 1.5, 0.8),
    "kitchen_sink": M(kitchen_sink, 1.2, 0.6), "crates": M(crate_stack, 0.6, 0.4), "sack": M(sack, 0.5, 0.36),
    "serving_line": M(serving_line, 2.4, 0.7), "dishwasher": M(dishwasher, 1.2, 0.8), "peeler": M(peeler, 0.56, 0.56),
    "workbench": M(workbench, 1.6, 0.7), "pump": M(pump_unit, 1.2, 0.6), "boiler": M(boiler, 0.76, 0.76),
    "duct": M(lambda: duct(2.6), 2.6, 0.6), "locker": M(locker, 0.5, 0.5), "laundry_cart": M(laundry_cart, 0.8, 0.6),
    "bin": M(bin_, 0.56, 0.56), "toilet": M(toilet, 0.44, 0.5), "urinal": M(urinal, 0.4, 0.32),
    "cubicle": M(cubicle, 0.99, 1.4), "shower": M(shower, 0.9, 0.9), "grab_bar": M(grab_bar, 0.8, 0.07),
    "bathtub": M(bathtub, 0.7, 1.7), "projector": M(projector, 0.5, 0.9), "cinema_row": M(cinema_row, 4.16, 0.5),
    "ladder": M(lambda: ladder(3.0), 0.5, 0.05), "hatch": M(hatch, 0.8, 0.8),
    "rug": M(lambda: floor_quad("carpet_rug", 2.0, 1.4, A), 2.0, 1.4),
    "runner": M(lambda: floor_quad("runner", 0.9, 3.0, A), 0.9, 3.0),
    "stain": M(lambda: floor_quad("stain_floor", 1.2, 1.2, "atlas_decal_blend"), 1.2, 1.2),
    "dust": M(lambda: floor_quad("dust_sheet", 1.5, 1.5, "atlas_decal_blend"), 1.5, 1.5),
    "clock": M(clock, 0.32, 0.05), "radio": M(radio, 0.18, 0.08),
    "hose_cabinet": M(lambda: wall_box("hose_cabinet", 0.6, 0.9, 0.22, "red_paint"), 0.6, 0.22),
    "fuse_box": M(lambda: wall_box("fuse_board", 0.5, 0.6, 0.15, "metal_green"), 0.5, 0.15),
    "elec_panel_wall": M(lambda: wall_box("elec_panel", 0.45, 0.8, 0.15, "metal_green"), 0.45, 0.15),
    "mirror": M(mirror_frame, 0.5, 0.01),
    "stage": M(lambda: stage(11.3, 3.2), 11.3, 3.2), "stage_curtain": M(lambda: stage_curtain(10.4, 5.4), 10.4, 0.02),
}
for _k, (_r, _w, _h) in {
    "poster_1": ("poster_1", 0.5, 0.75), "poster_2": ("poster_2", 0.5, 0.75), "poster_3": ("poster_3", 0.5, 0.75),
    "poster_4": ("poster_4", 0.5, 0.75), "poster_5": ("poster_5", 0.5, 0.75), "poster_6": ("poster_6", 0.5, 0.75),
    "eye_chart": ("eye_chart", 0.35, 0.7), "anatomy": ("anatomy", 0.5, 0.75), "notice_board": ("notice_board", 1.0, 0.75),
    "wall_newspaper": ("wall_newspaper", 0.9, 0.6), "evac_plan": ("evac_plan", 0.6, 0.4),
    "painting_1": ("painting_1", 0.6, 0.45), "painting_2": ("painting_2", 0.6, 0.45),
    "wall_carpet": ("wall_carpet", 1.6, 1.2), "calendar": ("calendar", 0.25, 0.38), "schedule": ("schedule", 0.5, 0.38),
    "menu_board": ("menu_board", 0.6, 0.45), "frame_photo": ("frame_photo", 0.25, 0.32),
    "arrow_dining": ("arrow_dining", 0.5, 0.125), "arrow_medical": ("arrow_medical", 0.5, 0.125),
    "arrow_admin": ("arrow_admin", 0.5, 0.125), "arrow_reception": ("arrow_reception", 0.5, 0.125),
    "arrow_hall": ("arrow_hall", 0.5, 0.125), "arrow_stairs": ("arrow_stairs", 0.5, 0.125),
    "arrow_lift": ("arrow_lift", 0.5, 0.125), "exit_sign": ("exit_sign", 0.4, 0.15), "fire_sign": ("fire_sign", 0.2, 0.2),
    "no_smoking": ("no_smoking", 0.2, 0.2), "keep_out": ("keep_out", 0.4, 0.15), "silence": ("silence", 0.4, 0.15),
    "wc_m": ("wc_m", 0.18, 0.18), "wc_f": ("wc_f", 0.18, 0.18), "wc_access": ("wc_access", 0.18, 0.18),
    "electro_warning": ("electro_warning", 0.2, 0.2), "roof_hatch_sign": ("roof_hatch", 0.5, 0.125),
    "socket": ("socket", 0.08, 0.08), "light_switch": ("light_switch", 0.08, 0.12), "soot": ("soot", 0.9, 0.9),
    "stain_wall": ("stain_wall", 1.0, 1.0), "vent_grille": ("vent_grille", 0.25, 0.25),
}.items():
    MODS[_k] = M((lambda r=_r, w=_w, h=_h: wall_quad(r, w, h)), _w, 0.01)
