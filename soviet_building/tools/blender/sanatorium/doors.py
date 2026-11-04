"""Door modules: frames (casing + jamb lining), leaves pivoting at the hinge, lever handles,
glazed partitions, service counters, projection ports and door plates.

Door-local frame: x along the wall (0 = opening centre), y across the wall from face A (y=0)
to face B (y=T), z up from the storey floor."""
import math
from .meshkit import MB
from .atlas import FURN_UV
from .params import *

CASE_W, CASE_T = 0.07, 0.015
LEAF_T = 0.04
GAP = 0.05          # jamb lining width each side (opening = leaf + 2*GAP)


def rot_for(axis, nab):
    return {("x", 1): 0.0, ("x", -1): math.pi, ("y", 1): -math.pi / 2, ("y", -1): math.pi / 2}[(axis, nab)]


def to_world(g, x, y):
    """Door-local (x, y) -> world (X, Y) for door geometry g."""
    r = rot_for(g.axis, g.nab)
    c, s = math.cos(r), math.sin(r)
    X0, Y0 = (g.c, g.fa) if g.axis == "x" else (g.fa, g.c)
    return (X0 + x * c - y * s, Y0 + x * s + y * c)


def ruv(region):
    u0, v0, u1, v1 = FURN_UV[region]
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def frame_mesh(ow, oh, T, mat, region=None):
    """Casing on both faces + jamb lining through the wall. 9 quads."""
    mb = MB("frame")
    h, w2 = oh, ow / 2
    uv = (lambda: ruv(region)) if region else None

    def q(pts, want):
        uvs = uv() if uv else [((p[0] + p[1]) * 1.0, p[2]) for p in pts]
        mb.poly_n(pts, uvs, mat, want)
    # jamb lining (extends over the casing thickness)
    y0, y1 = -CASE_T, T + CASE_T
    q([(-w2, y0, 0), (-w2, y1, 0), (-w2, y1, h), (-w2, y0, h)], (1, 0, 0))
    q([(w2, y0, 0), (w2, y1, 0), (w2, y1, h), (w2, y0, h)], (-1, 0, 0))
    q([(-w2, y0, h), (w2, y0, h), (w2, y1, h), (-w2, y1, h)], (0, 0, -1))
    for yf, want in ((-CASE_T, (0, -1, 0)), (T + CASE_T, (0, 1, 0))):
        q([(-w2 - CASE_W, yf, 0), (-w2, yf, 0), (-w2, yf, h), (-w2 - CASE_W, yf, h)], want)
        q([(w2, yf, 0), (w2 + CASE_W, yf, 0), (w2 + CASE_W, yf, h), (w2, yf, h)], want)
        q([(-w2 - CASE_W, yf, h), (w2 + CASE_W, yf, h), (w2 + CASE_W, yf, h + CASE_W), (-w2 - CASE_W, yf, h + CASE_W)], want)
    return mb


def leaf_mesh(w, h, style, hinge_sign, skip_back=False):
    """Leaf with the hinge edge on the local origin; extends along +x*hinge_sign, thickness 0..LEAF_T in y.
    style: wood, glazed, metal, metal_glazed, padded, wired."""
    mb = MB("leaf")
    s = hinge_sign
    X = lambda x: x * s
    t = LEAF_T
    if style in ("metal", "metal_glazed"):
        face_mat, face_uv = "atlas_furn", ruv("door_steel")
    elif style == "padded":
        face_mat, face_uv = "atlas_furn", ruv("door_padded")
    else:
        face_mat, face_uv = "wood_door", [(0, 0), (1, 0), (1, 1), (0, 1)]
    glass = style in ("glazed", "metal_glazed", "wired")
    gx0, gx1, gz0, gz1 = 0.13 * w / 0.9, w - 0.13 * w / 0.9, 1.05, 1.95
    if style == "wired":
        gz0, gz1 = 0.75, 1.95

    def face_uvs(pts):
        u0, v0 = face_uv[0]
        u1, v1 = face_uv[2]
        return [(u0 + (u1 - u0) * (abs(p[0]) / w), v0 + (v1 - v0) * (p[2] / h)) for p in pts]

    for yf, want in ((0.0, (0, -1, 0)), (t, (0, 1, 0))):
        if skip_back and yf == t:
            continue
        if glass:
            rects = [(0, w, 0, gz0), (0, w, gz1, h), (0, gx0, gz0, gz1), (gx1, w, gz0, gz1)]
        else:
            rects = [(0, w, 0, h)]
        for (a, b, z0, z1) in rects:
            pts = [(X(a), yf, z0), (X(b), yf, z0), (X(b), yf, z1), (X(a), yf, z1)]
            mb.poly_n(pts, face_uvs(pts), face_mat, want)
    edge_uv = ruv("wood_dark") if face_mat == "wood_door" else ruv("metal_grey")
    # hinge and lock edges (top/bottom edges are not visible and are skipped)
    for x, want in ((0, (-s, 0, 0)), (w, (s, 0, 0))):
        mb.poly_n([(X(x), 0, 0), (X(x), t, 0), (X(x), t, h), (X(x), 0, h)], edge_uv, "atlas_furn", want)
    if glass:
        for (pts, want) in (
            ([(X(gx0), 0, gz0), (X(gx0), t, gz0), (X(gx0), t, gz1), (X(gx0), 0, gz1)], (s, 0, 0)),
            ([(X(gx1), 0, gz0), (X(gx1), t, gz0), (X(gx1), t, gz1), (X(gx1), 0, gz1)], (-s, 0, 0)),
            ([(X(gx0), 0, gz0), (X(gx1), 0, gz0), (X(gx1), t, gz0), (X(gx0), t, gz0)], (0, 0, 1)),
            ([(X(gx0), 0, gz1), (X(gx1), 0, gz1), (X(gx1), t, gz1), (X(gx0), t, gz1)], (0, 0, -1))):
            mb.poly_n(pts, edge_uv, "atlas_furn", want)
        g = [(X(gx0), t / 2, gz0), (X(gx1), t / 2, gz0), (X(gx1), t / 2, gz1), (X(gx0), t / 2, gz1)]
        mb.poly(g, [(0, 0), (1, 0), (1, 1), (0, 1)], "glass_dusty")
    # lever handles on both faces at 1.0 m (aluminium), 0.06 m from the lock edge
    hx = w - 0.07
    for yf, d in ((0.0, -1), (t, 1)):
        if skip_back and yf == t:
            continue
        # one lever per face (5 faces, the face against the leaf is skipped); rosette is in the texture
        ya, yb = (yf - 0.035, yf) if d < 0 else (yf, yf + 0.035)
        _hbox(mb, X(hx - 0.12), X(hx + 0.012), ya, yb, 0.982, 1.008,
              skip=("+y" if d < 0 else "-y", "-z", "-x" if s > 0 else "+x"))
    return mb


def _hbox(mb, x0, x1, y0, y1, z0, z1, skip=None):
    if x0 > x1:
        x0, x1 = x1, x0
    faces = [f for f in ("-x", "+x", "-y", "+y", "+z", "-z") if f not in (skip or ())]
    mb.box(x0, x1, y0, y1, z0, z1, "atlas_furn", faces=faces, uv="region", regions={"*": "aluminium"})


def glazed_opening(ow, oh, T, mat="atlas_furn"):
    """Fixed glazing in an interior opening (registration windows, stair-lobby window)."""
    mb = MB("glazing")
    y = T / 2
    mb.poly([(-ow / 2, y, 0), (ow / 2, y, 0), (ow / 2, y, oh), (-ow / 2, y, oh)], [(0, 0), (1, 0), (1, 1), (0, 1)],
            "glass_dusty")
    bar = 0.04
    for (x0, x1, z0, z1) in ((-ow / 2, ow / 2, 0, bar), (-ow / 2, ow / 2, oh - bar, oh), (-ow / 2, -ow / 2 + bar, 0, oh),
                             (ow / 2 - bar, ow / 2, 0, oh), (-bar / 2, bar / 2, 0, oh)):
        mb.box(x0, x1, y - 0.025, y + 0.025, z0, z1, mat, faces=("-y", "+y", "-x", "+x", "+z", "-z"), uv="region",
               regions={"*": "wood_dark"})
    return mb


def counter_board(ow, T, depth_a=0.30, depth_b=0.10):
    """Service counter shelf through the opening (wood), z=0 at the opening sill."""
    mb = MB("counter")
    mb.box(-ow / 2 - 0.05, ow / 2 + 0.05, -depth_a, T + depth_b, -0.04, 0.0, "atlas_furn",
           faces=("+z", "-z", "-y", "+y", "-x", "+x"), uv="region", regions={"*": "wood_plain"})
    return mb


def plate_quad(mb, g, x_local, z, y_local, key, boxes, size, w=0.32, h=0.10, facing=+1):
    """Door plate on a wall face (facing +1 = towards local +y)."""
    from .atlas import SIGN_SIZE
    x0, y0, x1, y1 = boxes[key]
    u0, u1 = (x0 + 1) / SIGN_SIZE, (x1 - 1) / SIGN_SIZE
    v0, v1 = 1 - (y1 - 1) / SIGN_SIZE, 1 - (y0 + 1) / SIGN_SIZE
    xa, xb = x_local - w / 2, x_local + w / 2
    if facing > 0:          # normal towards local +y: reverse so the text reads left-to-right
        xa, xb = xb, xa
    pts = []
    for (x, zz) in ((xa, z), (xb, z), (xb, z + h), (xa, z + h)):
        X, Y = to_world(g, x, y_local)
        pts.append((X, Y, zz))
    mb.poly(pts, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], "atlas_signs")
