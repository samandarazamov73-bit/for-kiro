"""Low-poly furniture and equipment modules. Every module is built once and instanced.

Convention: origin at floor level in the centre of the footprint, front faces local -Y,
footprint x in [-w/2, w/2], y in [-d/2, d/2]. Detail lives in the atlas textures."""
import math
from .meshkit import MB
from .atlas import FURN_UV, DECAL_UV

A, DEC = "atlas_furn", "atlas_decal"


def bx(mb, x0, x1, y0, y1, z0, z1, regions, faces=("-x", "+x", "-y", "+y", "+z"), mat=A):
    mb.box(x0, x1, y0, y1, z0, z1, mat, faces=faces, uv="region", regions=regions)


def cushion(mb, x0, x1, y0, y1, z0, z1, region, c=0.035, skip=()):
    """Upholstered block with rounded-off (chamfered) top edges: inset top, four sloping strips, sides.
    `skip` lists sides ("-x", "+x", "-y", "+y") that are hidden and not built."""
    c = min(c, (x1 - x0) / 3, (y1 - y0) / 3, (z1 - z0) / 2)
    u0, v0, u1, v1 = FURN_UV[region]
    uv = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    zt, zc = z1, z1 - c
    top = [(x0 + c, y0 + c, zt), (x1 - c, y0 + c, zt), (x1 - c, y1 - c, zt), (x0 + c, y1 - c, zt)]
    mb.poly_n(top, uv, A, (0, 0, 1))
    rim = [(x0, y0, zc), (x1, y0, zc), (x1, y1, zc), (x0, y1, zc)]
    sides = [("-y", 0, 1, (0, -1, 0.7)), ("+x", 1, 2, (1, 0, 0.7)), ("+y", 2, 3, (0, 1, 0.7)), ("-x", 3, 0, (-1, 0, 0.7))]
    for name, i, k, want in sides:
        mb.poly_n([rim[i], rim[k], top[k], top[i]], uv, A, want)
        if name in skip:
            continue
        a, b = rim[i], rim[k]
        mb.poly_n([(a[0], a[1], z0), (b[0], b[1], z0), b, a], uv, A, (want[0], want[1], 0))


def quad(mb, pts, region, mat=A, want=None):
    u0, v0, u1, v1 = (DECAL_UV if "decal" in mat else FURN_UV)[region]
    uv = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    if want:
        mb.poly_n(pts, uv, mat, want)
    else:
        mb.poly(pts, uv, mat)


def legs_alpha(mb, w, d, h, region="chair_legs_wood"):
    """Four real legs (the name is kept from the earlier alpha-card version). Wood: square 32 mm
    legs with side stretchers on small pieces; tube: 22 mm dark steel legs."""
    tube = region != "chair_legs_wood"
    s = 0.022 if tube else 0.032
    reg = "metal_grey" if tube else "wood_dark"
    ins = s / 2 + 0.008
    xs, ys = (-w / 2 + ins, w / 2 - ins), (-d / 2 + ins, d / 2 - ins)
    for x in xs:
        for y in ys:
            bx(mb, x - s / 2, x + s / 2, y - s / 2, y + s / 2, 0.0, h, {"*": reg}, ("-x", "+x", "-y", "+y"))
    if not tube and w < 0.9 and d < 0.9 and h > 0.3:
        for x in xs:          # side stretchers at 0.15 m
            bx(mb, x - 0.012, x + 0.012, ys[0] + s / 2, ys[1] - s / 2, 0.13, 0.16, {"*": reg}, ("-x", "+x", "+z", "-z"))


def cyl_r(mb, cx, cy, z0, z1, r, region, sides=8, top=True):
    mb.cyl(cx, cy, z0, z1, r, A, sides=sides, top=top, bottom=False, region=region)


# ------------------------------------------------------------- rounded shapes from cross-sections
def oval(cx, cy, rx, ry, z, n=20, p=2.0):
    """Superellipse ring, counter-clockwise seen from above: p=2 is an ellipse, larger p a rounded rectangle."""
    pts = []
    for k in range(n):
        t = 2 * math.pi * k / n
        c, s_ = math.cos(t), math.sin(t)
        pts.append((cx + rx * math.copysign(abs(c) ** (2 / p), c), cy + ry * math.copysign(abs(s_) ** (2 / p), s_), z))
    return pts


def loft(mb, rings, region, inward=False, mat=A):
    """Skin through rings of equal size, from the first to the last; faces outward (or inward, for the
    inside of a bowl). UVs fill the atlas region."""
    u0, v0, u1, v1 = FURN_UV[region]
    n, m = len(rings[0]), len(rings) - 1
    for j in range(m):
        a, b = rings[j], rings[j + 1]
        for k in range(n):
            k2 = (k + 1) % n
            pts = [a[k], a[k2], b[k2], b[k]]
            uvs = [(u0 + (u1 - u0) * k / n, v0 + (v1 - v0) * j / m), (u0 + (u1 - u0) * (k + 1) / n, v0 + (v1 - v0) * j / m),
                   (u0 + (u1 - u0) * (k + 1) / n, v0 + (v1 - v0) * (j + 1) / m), (u0 + (u1 - u0) * k / n, v0 + (v1 - v0) * (j + 1) / m)]
            if inward:
                pts, uvs = pts[::-1], uvs[::-1]
            mb.poly(pts, uvs, mat)


def band(mb, outer, inner, region, want=(0, 0, 1), mat=A):
    """Flat or sloping strip between two rings (a rim, a seat, a lip)."""
    u0, v0, u1, v1 = FURN_UV[region]
    n = len(outer)
    for k in range(n):
        k2 = (k + 1) % n
        mb.poly_n([outer[k], outer[k2], inner[k2], inner[k]],
                  [(u0 + (u1 - u0) * k / n, v0), (u0 + (u1 - u0) * (k + 1) / n, v0),
                   (u0 + (u1 - u0) * (k + 1) / n, v1), (u0 + (u1 - u0) * k / n, v1)], mat, want)


def cap(mb, ring, region, want=(0, 0, 1), mat=A):
    u0, v0, u1, v1 = FURN_UV[region]
    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    uvs = [(u0 + (u1 - u0) * (p[0] - x0) / max(x1 - x0, 1e-6), v0 + (v1 - v0) * (p[1] - y0) / max(y1 - y0, 1e-6)) for p in ring]
    mb.poly_n(list(ring), uvs, mat, want)


def pot(mb, cx, cy, z0, h, r, region):
    """Flower pot: tapering sides, a rolled rim, dark earth inside."""
    n = 16
    rings = [oval(cx, cy, r * 0.74, r * 0.74, z0, n), oval(cx, cy, r * 0.94, r * 0.94, z0 + h * 0.8, n),
             oval(cx, cy, r * 1.06, r * 1.06, z0 + h * 0.84, n), oval(cx, cy, r * 1.06, r * 1.06, z0 + h, n)]
    loft(mb, rings, region)
    inner = oval(cx, cy, r * 0.92, r * 0.92, z0 + h, n)
    band(mb, rings[-1], inner, region)
    cap(mb, oval(cx, cy, r * 0.92, r * 0.92, z0 + h - 0.03, n), "soil")
    loft(mb, [oval(cx, cy, r * 0.92, r * 0.92, z0 + h - 0.03, n), inner], region, inward=True)


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
    reg = "metal_grey" if style != "wood" else "wood_dark"
    for x in (-w / 2 + 0.028, w / 2 - 0.028):         # back posts carrying the backrest
        bx(mb, x - 0.012, x + 0.012, d / 2 - 0.028, d / 2 - 0.004, 0.46, 0.62, {"*": reg}, ("-x", "+x", "-y", "+y"))
    return mb


def armchair(region="upholstery_brown"):
    """1970s easy chair: rounded seat and back cushions between flat wooden arm panels, legs below."""
    mb = MB("armchair")
    w, d = 0.7, 0.75
    cushion(mb, -w / 2 + 0.07, w / 2 - 0.07, -d / 2 + 0.02, d / 2 - 0.13, 0.22, 0.44, region, 0.04, ("-x", "+x"))
    cushion(mb, -w / 2 + 0.07, w / 2 - 0.07, d / 2 - 0.17, d / 2 - 0.02, 0.3, 0.86, region, 0.045, ("-x", "+x"))
    bx(mb, -w / 2 + 0.07, w / 2 - 0.07, -d / 2 + 0.04, d / 2 - 0.04, 0.16, 0.22, {"*": "wood_dark"}, ("-y", "+y"))
    for x0, x1 in ((-w / 2, -w / 2 + 0.07), (w / 2 - 0.07, w / 2)):
        bx(mb, x0, x1, -d / 2, d / 2, 0.2, 0.6, {"*": "wood_plain"}, ("-x", "+x", "-y", "+y", "+z", "-z"))
        for y in (-d / 2 + 0.05, d / 2 - 0.05):
            xm = (x0 + x1) / 2
            bx(mb, xm - 0.018, xm + 0.018, y - 0.018, y + 0.018, 0.0, 0.2, {"*": "wood_dark"}, ("-x", "+x", "-y", "+y"))
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


def _sofa(w=1.8, region="upholstery_green"):
    """Three-seat sofa: three rounded seat cushions, two back cushions, wooden arm panels, legs."""
    mb = MB("sofa_" + region)
    d = 0.8
    inner = w - 0.2
    for k in range(3):
        a = -inner / 2 + k * inner / 3
        cushion(mb, a + 0.004, a + inner / 3 - 0.004, -d / 2 + 0.02, d / 2 - 0.18, 0.2, 0.45, region, 0.04,
                ("-x", "+x") if k == 1 else (("-x",) if k == 0 else ("+x",)))
    for k in range(2):
        a = -inner / 2 + k * inner / 2
        cushion(mb, a + 0.004, a + inner / 2 - 0.004, d / 2 - 0.22, d / 2 - 0.02, 0.32, 0.9, region, 0.05,
                ("-x", "+x"))
    bx(mb, -inner / 2, inner / 2, -d / 2 + 0.04, d / 2 - 0.04, 0.12, 0.2, {"*": "wood_dark"}, ("-y", "+y"))
    for x0, x1 in ((-w / 2, -w / 2 + 0.1), (w / 2 - 0.1, w / 2)):
        bx(mb, x0, x1, -d / 2, d / 2, 0.12, 0.62, {"*": "wood_plain"}, ("-x", "+x", "-y", "+y", "+z", "-z"))
        for y in (-d / 2 + 0.06, d / 2 - 0.06):
            xm = (x0 + x1) / 2
            bx(mb, xm - 0.02, xm + 0.02, y - 0.02, y + 0.02, 0.0, 0.12, {"*": "wood_dark"}, ("-x", "+x", "-y", "+y"))
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
        mb.poly([pts_b[k], pts_b[k2], pts_t[k2], pts_t[k]], [(0, 0), (1, 0), (1, 1), (0, 1)], "emit_shade")
    return mb


def sink_wall():
    """Wall-hung washbasin with a rounded front and a real bowl, a swan-neck tap and the mirror above."""
    mb = MB("sink")
    mb.smooth_only = True
    n = 14
    out = [oval(0, 0.02, 0.19, 0.15, 0.68, n, 3.2), oval(0, 0.0, 0.24, 0.19, 0.8, n, 3.6),
           oval(0, 0.0, 0.25, 0.2, 0.85, n, 3.6)]
    loft(mb, out, "porcelain")
    cap(mb, out[0], "porcelain", want=(0, 0, -1))
    inner = oval(0, -0.015, 0.205, 0.15, 0.85, n, 3.0)
    band(mb, out[-1], inner, "porcelain")
    drain = oval(0, -0.02, 0.07, 0.05, 0.76, n, 2.4)
    loft(mb, [drain, oval(0, -0.018, 0.16, 0.115, 0.82, n, 2.8), inner], "porcelain", inward=True)
    cap(mb, drain, "porcelain")
    mb.tube_region([(0, 0.17, 0.85), (0, 0.17, 0.95), (0, 0.15, 0.985), (0, 0.11, 0.99), (0, 0.08, 0.96)], 0.011,
                   "chrome", 8, False, True)
    for x in (-0.06, 0.06):
        cyl_r(mb, x, 0.165, 0.85, 0.88, 0.016, "chrome")
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
    quad(mb, [(-w / 2, -0.008, 0), (w / 2, -0.008, 0), (w / 2, -0.008, h), (-w / 2, -0.008, h)], region, mat, (0, -1, 0))
    return mb


def floor_quad(region, w, d, mat=DEC, z=0.008):
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
    """Soviet desk telephone: a body with a sloping front carrying the rotary dial, and the handset with
    its ear and mouth cups lying on the cradle."""
    mb = MB("telephone")
    mb.smooth_only = True
    base = oval(0, 0, 0.11, 0.1, 0.0, 16, 5.0)
    top = oval(0, 0.03, 0.092, 0.058, 0.085, 16, 5.0)
    loft(mb, [base, oval(0, 0.005, 0.108, 0.094, 0.02, 16, 5.0), top], "black_plastic")
    cap(mb, top, "black_plastic")
    # rotary dial on the sloping front, facing up and forward
    c0 = (0.0, -0.062, 0.05)
    nrm = (0.0, -0.62, 0.78)
    up = (0.0, 0.78, 0.62)
    disc = []
    for z in (0.0, 0.007):
        ring = []
        for k in range(16):
            t = 2 * math.pi * k / 16
            ring.append(tuple(c0[i] + nrm[i] * z + (math.cos(t) * 0.04 if i == 0 else 0.0) + up[i] * math.sin(t) * 0.04
                              for i in range(3)))
        disc.append(ring)
    loft(mb, disc, "chrome")
    cap(mb, disc[1], "telephone", want=nrm)
    # handset: a bent grip between two cups, resting on two cradle prongs
    for x in (-0.06, 0.06):
        bx(mb, x - 0.012, x + 0.012, 0.015, 0.045, 0.085, 0.1, {"*": "black_plastic"}, ("-x", "+x", "-y", "+y", "+z"))
    mb.tube_region([(-0.112, 0.03, 0.104), (-0.088, 0.03, 0.12), (0.088, 0.03, 0.12), (0.112, 0.03, 0.104)], 0.013,
                   "black_plastic", 8, True, True)
    for x in (-0.112, 0.112):
        loft(mb, [oval(x, 0.03, 0.022, 0.022, 0.088, 12), oval(x, 0.03, 0.027, 0.027, 0.1, 12),
                  oval(x, 0.03, 0.026, 0.026, 0.108, 12)], "black_plastic")
        cap(mb, oval(x, 0.03, 0.026, 0.026, 0.108, 12), "black_plastic")
        cap(mb, oval(x, 0.03, 0.022, 0.022, 0.088, 12), "black_plastic", want=(0, 0, -1))
    return mb


def papers(k=1):
    return floor_quad(f"papers_{k}", 0.45, 0.45, DEC, z=0.011)


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
    pot(mb, 0, 0, 0, 0.32, 0.16, "cardboard" if kind == 1 else "red_paint")
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
    legs_alpha(mb, w, d, 0.5, "chair_legs_tube")
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
    """Floor-standing WC pan with a rounded bowl and rim, a seat, and a close-coupled cistern."""
    mb = MB("toilet")
    mb.smooth_only = True
    n = 14
    out = [oval(0, -0.07, 0.1, 0.13, 0.0, n, 2.6), oval(0, -0.085, 0.13, 0.17, 0.14, n, 2.4),
           oval(0, -0.1, 0.165, 0.2, 0.3, n, 2.3), oval(0, -0.105, 0.172, 0.205, 0.38, n, 2.3)]
    loft(mb, out, "porcelain")
    inner = oval(0, -0.115, 0.13, 0.155, 0.38, n, 2.3)
    band(mb, out[-1], inner, "porcelain")
    loft(mb, [oval(0, -0.13, 0.06, 0.07, 0.22, n, 2.2), oval(0, -0.12, 0.11, 0.13, 0.33, n, 2.3), inner], "porcelain",
         inward=True)
    cap(mb, oval(0, -0.13, 0.06, 0.07, 0.22, n, 2.2), "glass_dark" if "glass_dark" in FURN_UV else "porcelain")
    # seat: a flat ring lying on the rim
    so0, so1 = oval(0, -0.105, 0.178, 0.212, 0.385, n, 2.3), oval(0, -0.105, 0.178, 0.212, 0.41, n, 2.3)
    si0, si1 = oval(0, -0.115, 0.122, 0.148, 0.385, n, 2.3), oval(0, -0.115, 0.122, 0.148, 0.41, n, 2.3)
    loft(mb, [so0, so1], "metal_white")
    band(mb, so1, si1, "metal_white")
    loft(mb, [si0, si1], "metal_white", inward=True)
    bx(mb, -0.12, 0.12, 0.04, 0.12, 0.0, 0.36, {"*": "porcelain"}, ("-x", "+x", "-y"))           # foot to the wall
    bx(mb, -0.19, 0.19, 0.06, 0.24, 0.36, 0.78, {"*": "porcelain"}, ("-x", "+x", "-y", "+z"))    # cistern
    bx(mb, -0.2, 0.2, 0.05, 0.24, 0.78, 0.8, {"*": "porcelain"}, ("-x", "+x", "-y", "+z", "-z"))  # cistern lid
    bx(mb, -0.02, 0.02, 0.13, 0.17, 0.8, 0.815, {"*": "chrome"}, ("-x", "+x", "-y", "+y", "+z"))  # flush button
    return mb


def urinal():
    mb = MB("urinal")
    bx(mb, -0.2, 0.2, -0.32, 0.0, 0.45, 1.05, {"*": "porcelain"}, ("-x", "+x", "-y", "+z", "-z"))
    return mb


def cubicle(w=0.95, d=1.4, h=1.9, bars="left", door=True, curtain=False):
    """WC / shower cubicle placed with its back (+y) against the wall: two side partitions, the door
    leaf open inwards against the right partition, and grab bars inside by the toilet."""
    mb = MB("cubicle")
    for x in (-w / 2, w / 2):
        bx(mb, x - 0.02, x + 0.02, -d / 2, d / 2, 0.15, h, {"*": "partition"}, ("-x", "+x", "-y", "+z"))
    if door:   # leaf parallel to the right partition, 1 cm clear of it
        bx(mb, w / 2 - 0.055, w / 2 - 0.03, -d / 2, -d / 2 + 0.62, 0.17, h - 0.02, {"*": "partition"},
           ("-x", "+x", "-y", "+y", "+z"))
    if curtain:
        mb.tube_region([(-w / 2, -d / 2 + 0.05, h), (w / 2, -d / 2 + 0.05, h)], 0.012, "chrome", 4)
        for y, want in ((-d / 2 + 0.05, (0, -1, 0)), (-d / 2 + 0.06, (0, 1, 0))):
            u0, v0, u1, v1 = FURN_UV["curtain_med"]
            xa, xb = -w / 2 + 0.03, -w / 2 + 0.03 + w * 0.45
            mb.poly_n([(xa, y, 0.25), (xb, y, 0.25), (xb, y, h - 0.03), (xa, y, h - 0.03)],
                      [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], A, want)
    sides = {"left": (-1,), "right": (1,), "both": (-1, 1), "none": ()}[bars]
    for sx in sides:
        x = sx * (w / 2 - 0.02 - 0.07)
        mb.tube_region([(sx * (w / 2 - 0.02), 0.05, 0.75), (x, 0.05, 0.75), (x, d / 2 - 0.12, 0.75),
                        (sx * (w / 2 - 0.02), d / 2 - 0.12, 0.75)], 0.016, "chrome", 6)
    return mb


def shower(s=0.9, curtain=True):
    """Shower tray with riser and head on the back (+y) wall; optional curtain on the front."""
    mb = MB("shower")
    h = s / 2
    bx(mb, -h, h, -h, h, 0, 0.08, {"*": "porcelain"}, ("-x", "+x", "-y", "+y", "+z"))
    quad(mb, [(-0.015, h - 0.01, 0.8), (0.015, h - 0.01, 0.8), (0.015, h - 0.01, 2.05), (-0.015, h - 0.01, 2.05)], "chrome",
         A, (0, -1, 0))
    bx(mb, -0.05, 0.05, h - 0.2, h - 0.01, 2.02, 2.06, {"*": "chrome"}, ("-x", "+x", "-y", "-z"))
    if curtain:
        mb.tube_region([(-h, -h, 2.0), (h, -h, 2.0)], 0.01, "chrome", 4)
        quad(mb, [(-h, -h, 0.2), (-h + s * 0.55, -h, 0.2), (-h + s * 0.55, -h, 1.98), (-h, -h, 1.98)], "tulle",
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
        mb.tube_region([(x, -0.12, 0), (x, -0.12, h)], 0.018, "metal_grey", 4)
        for z in (0.4, h - 0.3):
            mb.tube_region([(x, 0, z), (x, -0.12, z)], 0.012, "metal_grey", 4)
    z = 0.3
    while z < h:
        mb.tube_region([(-0.22, -0.12, z), (0.22, -0.12, z)], 0.012, "metal_grey", 4)
        z += 0.3
    return mb


def hatch():
    mb = MB("hatch")
    bx(mb, -0.4, 0.4, -0.4, 0.4, -0.03, 0, {"*": "door_steel"}, ("-x", "+x", "-y", "+y", "-z"))
    return mb


def radio():
    return wall_box("radio_front", 0.22, 0.18, 0.08, "wood_dark")


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


# =============================================================================== v2 modules
# Cozy guest rooms, spa department, games, luggage, phyto-bar. Same conventions as above;
# wall-mounted modules (WALL set at the end) have their origin on the wall plane, bottom edge.

def bed_made(spread="bedspread_a", w=0.9, d=2.0):
    """Made bed: wooden frame, mattress in a white sheet, bedspread draped over the sides and folded
    back at the head, one plump pillow."""
    mb = MB("bed_made")
    bx(mb, -w / 2, w / 2, -d / 2, d / 2, 0.12, 0.36, {"*": "wood_plain"}, ("-x", "+x", "-y", "+y"))
    cushion(mb, -w / 2 + 0.02, w / 2 - 0.02, -d / 2 + 0.03, d / 2 - 0.05, 0.36, 0.53, "linen_white", 0.045)
    y1 = d / 2 - 0.62                      # spread ends below the pillow, sheet folded over it
    cushion(mb, -w / 2 - 0.015, w / 2 + 0.015, -d / 2 + 0.01, y1, 0.30, 0.565, spread, 0.05)
    bx(mb, -w / 2 + 0.005, w / 2 - 0.005, y1, y1 + 0.14, 0.53, 0.55, {"*": "linen_white"}, ("+y", "+z"))
    cushion(mb, -0.33, 0.33, d / 2 - 0.47, d / 2 - 0.08, 0.53, 0.68, "pillow", 0.05, ("+y",))
    bx(mb, -w / 2 - 0.02, w / 2 + 0.02, d / 2 - 0.04, d / 2, 0.0, 0.98, {"*": "wood_plain"},
       ("-x", "+x", "-y", "+y", "+z"))
    bx(mb, -w / 2 - 0.02, w / 2 + 0.02, -d / 2, -d / 2 + 0.04, 0.0, 0.62, {"*": "wood_plain"},
       ("-x", "+x", "-y", "+y", "+z"))
    return mb


def bed_hospital_made():
    """Height-adjustable care bed with a made bedspread (assisted rooms)."""
    mb = MB("bed_hosp")
    w, d = 0.95, 2.05
    bx(mb, -w / 2, w / 2, -d / 2, d / 2, 0.45, 0.52, {"*": "metal_white"}, ("-x", "+x", "-y", "+y", "-z"))
    cushion(mb, -w / 2 + 0.03, w / 2 - 0.03, -d / 2 + 0.05, d / 2 - 0.05, 0.52, 0.66, "linen_white", 0.045)
    y1 = d / 2 - 0.62
    cushion(mb, -w / 2 + 0.01, w / 2 - 0.01, -d / 2 + 0.04, y1, 0.47, 0.675, "bedspread_b", 0.05)
    cushion(mb, -0.33, 0.33, d / 2 - 0.47, d / 2 - 0.1, 0.66, 0.79, "pillow", 0.05, ("+y",))
    for y, h in ((d / 2 - 0.02, 1.05), (-d / 2 + 0.02, 0.85)):
        quad(mb, [(-w / 2, y, 0.0), (w / 2, y, 0.0), (w / 2, y, h), (-w / 2, y, h)], "bed_head_tube", DEC)
    legs_alpha(mb, w - 0.04, d - 0.08, 0.45, "chair_legs_tube")
    for sx in (-1, 1):      # side rail on the upper half (safety), down on the access side in the texture
        mb.tube_region([(sx * (w / 2 + 0.01), 0.1, 0.8), (sx * (w / 2 + 0.01), d / 2 - 0.15, 0.8)], 0.012, "chrome", 4)
    return mb


def recliner(region="upholstery_beige"):
    """Reclining relaxation chair (salt room / inhalatorium): seat, inclined back and leg rest."""
    mb = MB("recliner")
    w = 0.66
    bx(mb, -w / 2, w / 2, -0.25, 0.3, 0.32, 0.46, {"*": region}, ("-x", "+x", "-y", "+y", "+z"))
    u0, v0, u1, v1 = FURN_UV[region]
    uv = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    back = [(-w / 2, 0.3, 0.42), (w / 2, 0.3, 0.42), (w / 2, 0.68, 1.02), (-w / 2, 0.68, 1.02)]
    rest = [(-w / 2, -0.72, 0.30), (w / 2, -0.72, 0.30), (w / 2, -0.25, 0.44), (-w / 2, -0.25, 0.44)]
    for pts in (back, rest):
        mb.poly_n(pts, uv, A, (0, -0.4, 1))
        off = [(x, y + (0.06 if pts is back else 0), z - 0.08) for x, y, z in pts]
        mb.poly_n(off, uv, A, (0, 0.4, -1))
        for x in (-w / 2, w / 2):
            q = [p for p in pts if abs(p[0] - x) < 1e-6]
            r = [p for p in off if abs(p[0] - x) < 1e-6]
            mb.poly_n([q[0], q[1], r[1], r[0]], uv, A, (x, 0, 0))
    for x0, x1 in ((-w / 2 - 0.07, -w / 2), (w / 2, w / 2 + 0.07)):
        bx(mb, x0, x1, -0.25, 0.42, 0.0, 0.58, {"*": "wood_light"}, ("-x", "+x", "-y", "+y", "+z"))
    return mb


def massage_table():
    mb = MB("massage_table")
    w, d = 0.65, 1.9
    bx(mb, -w / 2, w / 2, -d / 2, d / 2, 0.66, 0.76, {"*": "leatherette_cream"}, ("-x", "+x", "-y", "+y", "+z"))
    bx(mb, -0.28, 0.28, -d / 2 + 0.2, -d / 2 + 0.95, 0.761, 0.765, {"*": "towel"}, ("+z", "-x", "+x"))
    cyl_r(mb, 0, d / 2 - 0.2, 0.76, 0.86, 0.1, "leatherette_cream", sides=6)
    legs_alpha(mb, w, d - 0.2, 0.66, "chair_legs_tube")
    return mb


def stool():
    mb = MB("stool")
    cyl_r(mb, 0, 0, 0.5, 0.56, 0.18, "upholstery_brown", sides=8)
    for a in (0.4, 0.4 + 2.094, 0.4 + 4.189):     # three splayed tube legs
        mb.tube_region([(0.06 * math.cos(a), 0.06 * math.sin(a), 0.5), (0.17 * math.cos(a), 0.17 * math.sin(a), 0.0)],
                       0.011, "metal_grey", 4)
    return mb


def physio_device():
    mb = MB("physio_device")
    bx(mb, -0.25, 0.25, -0.2, 0.2, 0.18, 0.95, {"*": "metal_white", "-y": "physio_panel"})
    legs_alpha(mb, 0.46, 0.36, 0.18, "chair_legs_tube")
    mb.tube_region([(0.15, 0.1, 0.95), (0.15, 0.1, 1.35), (0.15, -0.35, 1.45)], 0.015, "metal_grey", 4)
    cyl_r(mb, 0.15, -0.38, 1.33, 1.43, 0.09, "metal_white", sides=6)
    return mb


def curtain_rail(L=2.4, h=2.05, ceil=3.0):
    """Ceiling-hung medical curtain on a straight rail (cubicle divider), double-sided fabric."""
    mb = MB("curtain_rail")
    mb.tube_region([(-L / 2, 0, h + 0.03), (L / 2, 0, h + 0.03)], 0.012, "chrome", 4)
    for x in (-L / 2 + 0.1, L / 2 - 0.1):
        mb.tube_region([(x, 0, h + 0.03), (x, 0, ceil)], 0.008, "chrome", 4)
    u0, v0, u1, v1 = FURN_UV["curtain_med"]
    for y, want in ((-0.006, (0, -1, 0)), (0.006, (0, 1, 0))):
        mb.poly_n([(-L / 2, y, 0.3), (L / 2, y, 0.3), (L / 2, y, h), (-L / 2, y, h)],
                  [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], A, want)
    return mb


def hydro_bath():
    """Therapeutic (whirlpool) bath with an enamel basin and a control panel at the head end."""
    mb = MB("hydro_bath")
    w, h, t = 0.85, 0.65, 0.07
    ya, yb = -1.0, 0.75                     # tub; the control panel fills y 0.75..1.0 (footprint 0.85 x 2.0)
    bx(mb, -w / 2, w / 2, ya, yb, 0, h, {"*": "enamel_pot"}, ("-x", "+x", "-y", "+y"))
    for (x0, x1, y0, y1) in ((-w / 2, w / 2, ya, ya + t), (-w / 2, w / 2, yb - t, yb),
                             (-w / 2, -w / 2 + t, ya + t, yb - t), (w / 2 - t, w / 2, ya + t, yb - t)):
        bx(mb, x0, x1, y0, y1, h - 0.02, h, {"*": "porcelain"}, ("+z",))
    x0, x1, y0, y1 = -w / 2 + t, w / 2 - t, ya + t, yb - t
    bx(mb, x0, x1, y0, y1, 0.12, h - 0.02, {"*": "porcelain"}, ("-x", "+x", "-y", "+y"))   # inner walls (flip below)
    k = 4
    for i in range(len(mb.f) - k, len(mb.f)):
        mb.f[i] = tuple(reversed(mb.f[i]))
    bx(mb, x0, x1, y0, y1, 0.0, 0.12, {"*": "porcelain"}, ("+z",))
    bx(mb, -0.3, 0.3, yb, 1.0, 0.0, 0.95, {"*": "metal_white", "-y": "hydro_panel"}, ("-x", "+x", "-y", "+y", "+z"))
    return mb


def inhaler():
    """Table-top compressor inhaler with a hose and mouthpiece."""
    mb = MB("inhaler")
    bx(mb, -0.13, 0.13, -0.1, 0.1, 0, 0.16, {"*": "metal_white", "-y": "physio_panel"}, ("-x", "+x", "-y", "+y", "+z"))
    mb.tube_region([(0.08, -0.05, 0.16), (0.1, -0.15, 0.3), (0.05, -0.2, 0.34)], 0.01, "rubber_black", 4)
    return mb


def charcot_console():
    mb = MB("charcot_console")
    bx(mb, -0.5, 0.5, -0.25, 0.25, 0, 1.15, {"*": "metal_white", "-y": "shower_console"})
    for x in (-0.3, 0.3):
        mb.tube_region([(x, -0.25, 0.9), (x, -0.45, 0.85), (x * 1.4, -0.6, 0.15)], 0.018, "rubber_black", 4)
    return mb


def bar_counter(L=3.0):
    mb = MB("bar_counter")
    bx(mb, -L / 2, L / 2, -0.28, 0.28, 0, 1.02, {"*": "wood_dark", "-y": "bar_front"}, ("-x", "+x", "-y", "+y"))
    bx(mb, -L / 2 - 0.04, L / 2 + 0.04, -0.36, 0.32, 1.02, 1.07, {"*": "wood_dark", "+z": "wood_plain"})
    return mb


def buvette():
    """Mineral water pump-room stand: tiled panel with three taps over a stone basin."""
    mb = MB("buvette")
    bx(mb, -0.65, 0.65, -0.12, 0.12, 0, 1.75, {"*": "porcelain", "-y": "buvette_front"}, ("-x", "+x", "-y", "+z"))
    bx(mb, -0.6, 0.6, -0.42, -0.12, 0.72, 0.86, {"*": "concrete", "+z": "steel"})
    for x in (-0.35, 0.0, 0.35):
        mb.tube_region([(x, -0.12, 1.12), (x, -0.3, 1.12), (x, -0.3, 1.04)], 0.014, "chrome", 5)
    return mb


def samovar():
    mb = MB("samovar")
    cyl_r(mb, 0, 0, 0, 0.06, 0.1, "brass", sides=8)
    cyl_r(mb, 0, 0, 0.06, 0.4, 0.15, "brass", sides=8)
    cyl_r(mb, 0, 0, 0.4, 0.46, 0.06, "black_plastic", sides=6)
    cyl_r(mb, 0, 0, 0.46, 0.56, 0.07, "enamel_pot", sides=6)       # teapot on top
    mb.tube_region([(0, -0.15, 0.15), (0, -0.22, 0.13)], 0.012, "brass", 4, cap1=True)
    return mb


def table_round(top="tablecloth", r=0.38, h=0.74):
    mb = MB("table_round")
    cyl_r(mb, 0, 0, h - 0.03, h, r, top, sides=10)
    mb.tube_region([(0, 0, 0.02), (0, 0, h - 0.03)], 0.03, "wood_dark", 5)
    cyl_r(mb, 0, 0, 0, 0.03, 0.24, "wood_dark", sides=8)
    return mb


def table_cloth(w=1.2, d=0.8, h=0.75):
    """Dining table with a white tablecloth hanging 12 cm over the edges."""
    mb = MB("table_cloth")
    bx(mb, -w / 2 - 0.02, w / 2 + 0.02, -d / 2 - 0.02, d / 2 + 0.02, h - 0.14, h, {"*": "tablecloth"},
       ("-x", "+x", "-y", "+y", "+z"))
    legs_alpha(mb, w, d, h - 0.14, "chair_legs_wood")
    return mb


def vase():
    mb = MB("vase")
    mb.smooth_only = True
    n = 12
    loft(mb, [oval(0, 0, 0.035, 0.035, 0.0, n), oval(0, 0, 0.055, 0.055, 0.06, n), oval(0, 0, 0.045, 0.045, 0.12, n),
              oval(0, 0, 0.028, 0.028, 0.15, n), oval(0, 0, 0.034, 0.034, 0.165, n)], "porcelain")
    cap(mb, oval(0, 0, 0.034, 0.034, 0.165, n), "soil")
    for a in (0.0, math.pi / 2):
        c, s = math.cos(a) * 0.13, math.sin(a) * 0.13
        quad(mb, [(-c, -s, 0.1), (c, s, 0.1), (c, s, 0.38), (-c, -s, 0.38)], "plant_4", DEC)
    return mb


def tv_small():
    mb = MB("tv_small")
    bx(mb, -0.24, 0.24, -0.2, 0.2, 0.0, 0.4, {"*": "wood_dark", "-y": "tv_front"}, ("-x", "+x", "-y", "+y", "+z"))
    return mb


def tv_cabinet():
    mb = MB("tv_cabinet")
    bx(mb, -0.45, 0.45, -0.22, 0.22, 0.0, 0.55, {"*": "wood_plain", "-y": "drawer_front"})
    return mb


def game_board(region, w=0.42, d=0.42):
    mb = MB("game_" + region)
    bx(mb, -w / 2, w / 2, -d / 2, d / 2, 0, 0.025, {"*": "wood_dark", "+z": region}, ("-x", "+x", "-y", "+y", "+z"))
    return mb


def game_chess():
    mb = game_board("chessboard")
    s = 0.38 / 8
    k = 0
    for row, reg in ((0, "porcelain"), (1, "porcelain"), (6, "black_plastic"), (7, "black_plastic")):
        for col_ in range(0, 8, 2 if row in (1, 6) else 1):
            if row in (0, 7) and col_ % 2:
                continue
            x, y = -0.19 + (col_ + 0.5) * s, -0.19 + (row + 0.5) * s
            h = 0.035 if row in (1, 6) else 0.06 + 0.01 * (k % 3)
            mb.box(x - 0.011, x + 0.011, y - 0.011, y + 0.011, 0.025, 0.025 + h, A,
                   faces=("-x", "+x", "-y", "+y", "+z"), uv="region", regions={"*": reg})
            k += 1
    return mb


def game_checkers():
    mb = game_board("checkers_board")
    return mb


def game_dominoes():
    mb = MB("game_dominoes")
    for i, (x, y, a) in enumerate(((-0.12, 0.0, 0), (-0.07, 0.0, 0), (-0.02, 0.0, 0), (0.03, 0.0, 0),
                                   (0.03, 0.06, 1), (0.03, 0.12, 1), (0.1, -0.12, 0), (0.15, -0.12, 0))):
        hw, hd = (0.024, 0.012) if a == 0 else (0.012, 0.024)
        mb.box(x - hd, x + hd, y - hw, y + hw, 0, 0.008, A, faces=("-x", "+x", "-y", "+y", "+z"), uv="region",
               regions={"*": "porcelain", "+z": "dominoes"})
    return mb


def game_backgammon():
    return game_board("backgammon", 0.5, 0.32)


def billiard():
    """Russian billiards table (2.6 x 1.45 m): carved legs, wooden rails, green cloth with balls."""
    mb = MB("billiard")
    w, d, h = 1.45, 2.6, 0.8
    bx(mb, -w / 2, w / 2, -d / 2, d / 2, h - 0.25, h - 0.04, {"*": "wood_dark"}, ("-x", "+x", "-y", "+y", "-z"))
    u0, v0, u1, v1 = FURN_UV["billiard_cloth"]
    mb.poly_n([(-w / 2 + 0.1, -d / 2 + 0.1, h - 0.04), (w / 2 - 0.1, -d / 2 + 0.1, h - 0.04),
               (w / 2 - 0.1, d / 2 - 0.1, h - 0.04), (-w / 2 + 0.1, d / 2 - 0.1, h - 0.04)],
              [(u0, v1), (u0, v0), (u1, v0), (u1, v1)], A, (0, 0, 1))
    for (x0, x1, y0, y1) in ((-w / 2, w / 2, -d / 2, -d / 2 + 0.1), (-w / 2, w / 2, d / 2 - 0.1, d / 2),
                             (-w / 2, -w / 2 + 0.1, -d / 2 + 0.1, d / 2 - 0.1), (w / 2 - 0.1, w / 2, -d / 2 + 0.1, d / 2 - 0.1)):
        bx(mb, x0, x1, y0, y1, h - 0.04, h, {"*": "wood_dark", "+z": "wood_plain"}, ("-x", "+x", "-y", "+y", "+z"))
    for x in (-w / 2 + 0.12, w / 2 - 0.12):
        for y in (-d / 2 + 0.15, 0.0, d / 2 - 0.15):
            bx(mb, x - 0.07, x + 0.07, y - 0.07, y + 0.07, 0, h - 0.25, {"*": "wood_dark"}, ("-x", "+x", "-y", "+y"))
    return mb


def cue_rack():
    mb = MB("cue_rack")
    bx(mb, -0.35, 0.35, -0.04, 0, 0.9, 1.0, {"*": "wood_dark"}, ("-x", "+x", "-y", "+z", "-z"))
    bx(mb, -0.35, 0.35, -0.06, 0, 0.1, 0.16, {"*": "wood_dark"}, ("-x", "+x", "-y", "+z"))
    for i in range(4):
        x = -0.24 + i * 0.16
        mb.tube_region([(x, -0.05, 0.14), (x, -0.05, 1.5)], 0.012, "wood_light", 4, cap1=True)
    return mb


def suitcase(region="suitcase_a", w=0.62, d=0.2, h=0.44):
    mb = MB("suitcase_" + region)
    bx(mb, -w / 2, w / 2, -d / 2, d / 2, 0, h, {"*": "upholstery_brown" if region == "suitcase_a" else "upholstery_green",
                                               "-y": region, "+y": region})
    mb.tube_region([(-0.1, 0, h), (-0.08, 0, h + 0.05), (0.08, 0, h + 0.05), (0.1, 0, h)], 0.012, "black_plastic", 4)
    return mb


def travel_bag():
    mb = MB("travel_bag")
    bx(mb, -0.26, 0.26, -0.15, 0.15, 0, 0.3, {"*": "travel_bag"})
    mb.tube_region([(-0.12, 0, 0.3), (-0.08, 0, 0.42), (0.08, 0, 0.42), (0.12, 0, 0.3)], 0.012, "black_plastic", 4)
    return mb


def ex_bike():
    """Exercise bicycle (veloergometer)."""
    mb = MB("ex_bike")
    bx(mb, -0.25, 0.25, -0.45, 0.45, 0, 0.06, {"*": "metal_grey"})
    quad(mb, [(0, -0.42, 0.06), (0, 0.0, 0.06), (0, 0.0, 0.5), (0, -0.42, 0.5)], "wheel", DEC)
    mb.tube_region([(0, 0.3, 0.06), (0, 0.15, 0.85)], 0.025, "metal_white", 5)
    bx(mb, -0.12, 0.12, 0.05, 0.3, 0.85, 0.92, {"*": "upholstery_brown"})
    mb.tube_region([(0, -0.25, 0.06), (0, -0.35, 1.05)], 0.025, "metal_white", 5)
    mb.tube_region([(-0.25, -0.35, 1.05), (0.25, -0.35, 1.05)], 0.018, "rubber_black", 4)
    bx(mb, -0.08, 0.08, -0.42, -0.34, 0.95, 1.05, {"*": "black_plastic", "+y": "floor_indicator"})
    return mb


def wall_bars(n=12, h=2.6):
    mb = MB("wall_bars")
    for x in (-0.45, 0.45):
        bx(mb, x - 0.035, x + 0.035, -0.14, -0.02, 0, h, {"*": "wood_light"}, ("-x", "+x", "-y", "+z"))
    for i in range(n):
        z = 0.15 + i * (h - 0.3) / (n - 1)
        mb.tube_region([(-0.41, -0.08, z), (0.41, -0.08, z)], 0.016, "wood_light", 5)
    return mb


def gym_bench():
    mb = MB("gym_bench")
    bx(mb, -1.0, 1.0, -0.15, 0.15, 0.3, 0.35, {"*": "wood_light"}, ("-x", "+x", "-y", "+y", "+z", "-z"))
    for x in (-0.85, 0.85):
        bx(mb, x - 0.03, x + 0.03, -0.14, 0.14, 0, 0.3, {"*": "wood_light"}, ("-x", "+x", "-y", "+y"))
    return mb


def floor_lamp():
    mb = MB("floor_lamp")
    cyl_r(mb, 0, 0, 0, 0.03, 0.16, "black_plastic", sides=8)
    mb.tube_region([(0, 0, 0.03), (0, 0, 1.4)], 0.012, "brass", 4)
    n = 8
    rb, rt, zb, zt = 0.24, 0.16, 1.32, 1.6
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        p = [(rb * math.cos(a0), rb * math.sin(a0), zb), (rb * math.cos(a1), rb * math.sin(a1), zb),
             (rt * math.cos(a1), rt * math.sin(a1), zt), (rt * math.cos(a0), rt * math.sin(a0), zt)]
        mb.poly(p, [(0, 0), (1, 0), (1, 1), (0, 1)], "emit_shade")
    return mb


def sconce():
    """Wall lamp with a fabric shade (corridors, lounges)."""
    mb = MB("sconce")
    bx(mb, -0.05, 0.05, -0.03, 0, 0.0, 0.12, {"*": "brass"}, ("-x", "+x", "-y", "+z", "-z"))
    mb.tube_region([(0, -0.02, 0.06), (0, -0.14, 0.12)], 0.008, "brass", 4)
    n = 6
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        cx, cy = 0.0, -0.17
        p = [(cx + 0.11 * math.cos(a0), cy + 0.11 * math.sin(a0), 0.08), (cx + 0.11 * math.cos(a1), cy + 0.11 * math.sin(a1), 0.08),
             (cx + 0.07 * math.cos(a1), cy + 0.07 * math.sin(a1), 0.26), (cx + 0.07 * math.cos(a0), cy + 0.07 * math.sin(a0), 0.26)]
        mb.poly(p, [(0, 0), (1, 0), (1, 1), (0, 1)], "emit_shade")
    return mb


def towel_rail(w=0.6):
    mb = MB("towel_rail")
    mb.tube_region([(-w / 2, 0, 0.0), (-w / 2, -0.08, 0.0), (w / 2, -0.08, 0.0), (w / 2, 0, 0.0)], 0.012, "chrome", 5)
    for y, want in ((-0.075, (0, -1, 0)), (-0.085, (0, 1, 0))):
        u0, v0, u1, v1 = FURN_UV["towel"]
        mb.poly_n([(-w / 2 + 0.08, y, -0.45), (w / 2 - 0.08, y, -0.45), (w / 2 - 0.08, y, 0.0), (-w / 2 + 0.08, y, 0.0)],
                  [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], A, want)
    return mb


def shower_seat():
    mb = MB("shower_seat")
    bx(mb, -0.22, 0.22, -0.42, 0, 0.45, 0.49, {"*": "wood_light"}, ("-x", "+x", "-y", "+z", "-z"))
    for x in (-0.2, 0.2):
        mb.tube_region([(x, 0, 0.2), (x, -0.38, 0.45)], 0.01, "chrome", 4)
    return mb


def grab_bar_v(h=0.6):
    mb = MB("grab_bar_v")
    mb.tube_region([(0, 0, 0), (0, -0.07, 0), (0, -0.07, h), (0, 0, h)], 0.017, "chrome", 6)
    return mb


def grab_bar_l():
    """L-shaped bar beside a toilet or sink: horizontal 0.5 m at the bottom, vertical 0.6 m."""
    mb = MB("grab_bar_l")
    mb.tube_region([(-0.25, 0, 0), (-0.25, -0.07, 0), (0.25, -0.07, 0), (0.25, -0.07, 0.6), (0.25, 0, 0.6)],
                   0.017, "chrome", 6)
    return mb


def grab_fold():
    """Fold-down support arm beside an accessible toilet (projects 0.7 m from the wall)."""
    mb = MB("grab_fold")
    bx(mb, -0.06, 0.06, -0.03, 0, -0.08, 0.08, {"*": "chrome"}, ("-x", "+x", "-y", "+z", "-z"))
    mb.tube_region([(-0.04, -0.03, 0.0), (-0.04, -0.7, 0.0), (0.04, -0.7, 0.0), (0.04, -0.03, 0.0)], 0.016, "chrome", 6)
    return mb


def coat_hooks(w=0.8):
    mb = MB("coat_hooks")
    bx(mb, -w / 2, w / 2, -0.025, 0, 0, 0.1, {"*": "wood_dark"}, ("-x", "+x", "-y", "+z", "-z"))
    for i in range(4):
        x = -w / 2 + (i + 0.5) * w / 4
        mb.tube_region([(x, -0.02, 0.05), (x, -0.08, 0.07), (x, -0.09, 0.11)], 0.006, "brass", 4)
    return mb


def carafe():
    mb = MB("carafe")
    cyl_r(mb, 0, 0, 0, 0.2, 0.05, "chrome", sides=6)
    cyl_r(mb, 0.09, 0, 0, 0.09, 0.03, "chrome", sides=6)
    return mb


def palm():
    mb = MB("palm")
    cyl_r(mb, 0, 0, 0, 0.42, 0.2, "wood_dark", sides=8)
    for a in (0.3, 0.3 + math.pi / 2):
        c, s = math.cos(a) * 0.55, math.sin(a) * 0.55
        quad(mb, [(-c, -s, 0.3), (c, s, 0.3), (c, s, 2.0), (-c, -s, 2.0)], "plant_3", DEC)
    return mb


def plant_stand():
    """Wooden flower stand with a flowering geranium."""
    mb = MB("plant_stand")
    bx(mb, -0.17, 0.17, -0.17, 0.17, 0.6, 0.63, {"*": "wood_dark"}, ("-x", "+x", "-y", "+y", "+z", "-z"))
    legs_alpha(mb, 0.32, 0.32, 0.6, "chair_legs_wood")
    pot(mb, 0, 0, 0.63, 0.17, 0.11, "red_paint")
    for a in (0.0, math.pi / 2):
        c, s = math.cos(a) * 0.26, math.sin(a) * 0.26
        quad(mb, [(-c, -s, 0.72), (c, s, 0.72), (c, s, 1.2), (-c, -s, 1.2)], "plant_4", DEC)
    return mb


MODS.update({
    "bed_a": M(lambda: bed_made("bedspread_a"), 0.94, 2.0), "bed_b": M(lambda: bed_made("bedspread_b"), 0.94, 2.0),
    "bed_c": M(lambda: bed_made("blanket"), 0.94, 2.0), "bed_hosp": M(bed_hospital_made, 0.97, 2.05),
    "armchair_red": M(lambda: armchair("upholstery_red"), 0.7, 0.75),
    "armchair_beige": M(lambda: armchair("upholstery_beige"), 0.7, 0.75),
    "sofa_brown": M(lambda: _sofa(1.8, "upholstery_brown"), 1.8, 0.8),
    "sofa_beige": M(lambda: _sofa(1.8, "upholstery_beige"), 1.8, 0.8),
    "sofa_red": M(lambda: _sofa(1.8, "upholstery_red"), 1.8, 0.8),
    "recliner": M(recliner, 0.8, 1.45), "massage_table": M(massage_table, 0.65, 1.9), "stool": M(stool, 0.36, 0.36),
    "physio_device": M(physio_device, 0.5, 0.45), "curtain_rail": M(curtain_rail, 2.4, 0.05),
    "curtain_rail_s": M(lambda: curtain_rail(1.7), 1.7, 0.05),
    "hydro_bath": M(hydro_bath, 0.85, 2.0), "charcot_console": M(charcot_console, 1.0, 0.5),
    "bar_counter": M(bar_counter, 3.0, 0.68), "buvette": M(buvette, 1.3, 0.42), "samovar": M(samovar, 0.3, 0.3),
    "tea_shelf": M(lambda: rack("tea_jars", 1.2, 0.35, 1.9), 1.2, 0.35),
    "table_round": M(table_round, 0.76, 0.76), "table_cloth": M(table_cloth, 1.24, 0.84),
    "table_cloth_sq": M(lambda: table_cloth(0.8, 0.8), 0.84, 0.84),
    "vase": M(vase, 0.26, 0.26), "inhaler": M(inhaler, 0.26, 0.2), "tv_small": M(tv_small, 0.48, 0.4), "tv_cabinet": M(tv_cabinet, 0.9, 0.44),
    "game_chess": M(game_chess, 0.42, 0.42), "game_checkers": M(game_checkers, 0.42, 0.42),
    "game_dominoes": M(game_dominoes, 0.3, 0.3), "game_backgammon": M(game_backgammon, 0.5, 0.32),
    "billiard": M(billiard, 1.45, 2.6),
    "suitcase_a": M(lambda: suitcase("suitcase_a"), 0.62, 0.2), "suitcase_b": M(lambda: suitcase("suitcase_b"), 0.62, 0.2),
    "travel_bag": M(travel_bag, 0.52, 0.3), "luggage_rack": M(lambda: rack("luggage_shelf", 1.2, 0.5, 1.9), 1.2, 0.5),
    "ex_bike": M(ex_bike, 0.5, 0.9), "gym_bench": M(gym_bench, 2.0, 0.3),
    "gym_mat": M(lambda: floor_quad("gym_mat", 1.8, 0.6, A, z=0.012), 1.8, 0.6),
    "rubber_mat": M(lambda: floor_quad("rubber_mat", 0.8, 1.8, A, z=0.012), 0.8, 1.8),
    "bath_mat": M(lambda: floor_quad("bath_mat", 0.6, 0.45, A, z=0.012), 0.6, 0.45),
    "rug_small": M(lambda: floor_quad("carpet_rug", 1.4, 0.9, A), 1.4, 0.9),
    "rug_big": M(lambda: floor_quad("carpet_rug", 2.6, 1.8, A), 2.6, 1.8),
    "floor_lamp": M(floor_lamp, 0.48, 0.48), "carafe": M(carafe, 0.2, 0.12),
    "palm": M(palm, 0.6, 0.6), "plant_stand": M(plant_stand, 0.36, 0.36),
    "cubicle": M(lambda: cubicle(0.95, 1.4, bars="left"), 0.99, 1.4),
    "cubicle_r": M(lambda: cubicle(0.95, 1.4, bars="right"), 0.99, 1.4),
    "cubicle_wide": M(lambda: cubicle(1.5, 1.6, bars="both"), 1.54, 1.6),
    "shower_cubicle": M(lambda: cubicle(1.0, 1.2, bars="left", door=False, curtain=True), 1.04, 1.2),
    "chair_soft": M(lambda: chair("tube"), 0.42, 0.45),
    "seat_row2": M(lambda: seat_row(2), 1.04, 0.44),
    "shower_s": M(lambda: shower(0.8), 0.8, 0.8), "shower_tray": M(lambda: shower(0.9, False), 0.9, 0.9),
    "table_read": M(lambda: table(1.4, 0.8, 0.75, "upholstery_green"), 1.4, 0.8),
    # wall-mounted
    "call_button": M(lambda: wall_box("call_button", 0.08, 0.11, 0.025, "metal_white"), 0.08, 0.025),
    "call_panel": M(lambda: wall_box("call_panel", 0.5, 0.25, 0.06, "metal_white"), 0.5, 0.06),
    "cue_rack": M(cue_rack, 0.7, 0.06), "wall_bars": M(wall_bars, 0.97, 0.14),
    "mirror_big": M(lambda: wall_quad("mirror", 1.8, 1.5, A), 1.8, 0.01),
    "sconce": M(sconce, 0.24, 0.28), "towel_rail": M(towel_rail, 0.62, 0.1), "shower_seat": M(shower_seat, 0.44, 0.42),
    "grab_bar_s": M(lambda: grab_bar(0.45), 0.45, 0.09), "grab_bar_v": M(grab_bar_v, 0.06, 0.09),
    "grab_bar_l": M(grab_bar_l, 0.54, 0.09), "grab_fold": M(grab_fold, 0.12, 0.72),
    "coat_hooks": M(coat_hooks, 0.8, 0.1),
})
for _k, (_r, _w, _h) in {
    "poster_7": ("poster_7", 0.5, 0.75), "poster_8": ("poster_8", 0.5, 0.75), "poster_9": ("poster_9", 0.5, 0.75),
    "poster_10": ("poster_10", 0.5, 0.75), "painting_3": ("painting_3", 1.2, 0.6),
    "welcome_banner": ("welcome_banner", 2.4, 0.45), "menu_phyto": ("menu_phyto", 0.6, 0.45),
    "buvette_sign": ("buvette_sign", 0.8, 0.3), "schedule_proc": ("schedule_proc", 0.6, 0.45),
    "arrow_spa": ("arrow_spa", 0.5, 0.125), "papers_desk": ("papers_1", 0.4, 0.4),
}.items():
    MODS[_k] = M((lambda r=_r, w=_w, h=_h: wall_quad(r, w, h)), _w, 0.01)
MODS["papers_desk"] = M(lambda: floor_quad("papers_1", 0.38, 0.38, DEC, z=0.004), 0.38, 0.38)
for _k in ("stain", "dust", "papers_1", "papers_2", "soot", "stain_wall", "key_only"):
    MODS.pop(_k, None)
MODS["radio"] = M(radio, 0.22, 0.08)

# wall-mounted modules: origin on the wall plane at the bottom edge, body towards local -Y
WALL = {k for k in MODS if k.startswith(("poster_", "painting_", "arrow_"))} | {
    "eye_chart", "anatomy", "notice_board", "wall_newspaper", "evac_plan", "wall_carpet", "calendar", "schedule",
    "menu_board", "frame_photo", "exit_sign", "fire_sign", "no_smoking", "keep_out", "silence", "wc_m", "wc_f",
    "wc_access", "electro_warning", "roof_hatch_sign", "socket", "light_switch", "vent_grille", "clock", "radio",
    "hose_cabinet", "fuse_box", "elec_panel_wall", "mirror", "fire_ext", "grab_bar", "ladder",
    "call_button", "call_panel", "cue_rack", "wall_bars", "mirror_big", "sconce", "towel_rail", "shower_seat",
    "grab_bar_s", "grab_bar_v", "grab_bar_l", "grab_fold", "coat_hooks", "welcome_banner", "menu_phyto",
    "buvette_sign", "schedule_proc",
}
# items that stand on other furniture (no floor footprint of their own)
ON_TOP = {"table_lamp", "telephone", "typewriter", "paper_stack", "papers_desk", "microscope", "centrifuge",
          "samovar", "vase", "tv_small", "game_chess", "game_checkers", "game_dominoes", "game_backgammon",
          "carafe", "suitcase_a", "suitcase_b", "travel_bag", "inhaler"}


# ====================================================================== v3: half-abandoned mood
def cobweb(mirror=False):
    """Cobweb hanging in an upper room corner. Corner at the origin, walls along +x and +y (mirror: +x and -y)."""
    mb = MB("cobweb")
    sy = -1 if mirror else 1
    pts = [(0.62, 0.012 * sy, 0.0), (0.012, 0.62 * sy, 0.0), (0.012, 0.012 * sy, -0.7)]
    u0, v0, u1, v1 = DECAL_UV["cobweb"]
    mb.poly(pts, [(u1, v1), (u0, v1), ((u0 + u1) / 2, v0)], "atlas_decal_blend")
    return mb


def bed_strip():
    """Bed stripped of its linen: striped mattress, the blanket folded at the foot, no pillow."""
    mb = bed("bare")
    bx(mb, -0.3, 0.3, -0.95, -0.6, 0.55, 0.67, {"*": "blanket"}, ("-x", "+x", "-y", "+y", "+z"))
    return mb


MODS.update({
    "cobweb_r": M(lambda: cobweb(False), 0.62, 0.62), "cobweb_l": M(lambda: cobweb(True), 0.62, 0.62),
    "bed_strip": M(bed_strip, 0.94, 2.0),
    "dust_patch": M(lambda: floor_quad("dust_patch", 1.6, 1.6, "atlas_decal_blend", z=0.009), 1.6, 1.6),
    "leaves_dry": M(lambda: floor_quad("leaves_dry", 0.7, 0.35, DEC, z=0.010), 0.7, 0.35),
    "papers_floor": M(lambda: floor_quad("papers_1", 0.5, 0.5, DEC, z=0.011), 0.5, 0.5),
    "stain_small": M(lambda: floor_quad("stain_small", 0.7, 0.7, "atlas_decal_blend", z=0.010), 0.7, 0.7),
})
