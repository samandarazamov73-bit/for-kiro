"""2D floor plan drawings (PNG) generated from the same plan data as the 3D build."""
import math
from PIL import Image, ImageDraw, ImageFont
from .params import *

FONT = "/usr/share/fonts/google-noto-vf/NotoSans[wght].ttf"
DEPT_COL = {
    "A_entrance": (236, 214, 160), "B_admin": (196, 214, 236), "C_medical": (196, 236, 214),
    "D_catering": (240, 196, 170), "E_technical": (214, 206, 196), "P_patient": (232, 222, 240), "S_spa": (186, 226, 236),
    "CIRC": (246, 244, 236),
}
DEPT_EN = {"A_entrance": "Entrance & reception", "B_admin": "Administration", "C_medical": "Medical",
           "D_catering": "Dining & catering", "E_technical": "Technical & service", "P_patient": "Guests (rooms, leisure)",
           "S_spa": "Spa treatments",
           "CIRC": "Circulation"}


def font(sz, bold=False):
    f = ImageFont.truetype(FONT, sz)
    f.set_variation_by_name("Bold" if bold else "Regular")
    return f


def draw_level(layout, lvl, path, S=30, title=""):
    X0, X1, Y0, Y1 = -1.5, MAIN_LEN + 1.5, ENT_Y0 - 1.5, MAIN_DEPTH + 1.5
    W, H = int((X1 - X0) * S), int((Y1 - Y0) * S) + 150
    im = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(im)

    def P(x, y):  # plan: +Y (rear) at the top of the sheet
        return ((x - X0) * S, (Y1 - y) * S + 60)

    def rect(x0, x1, y0, y1, **kw):
        a, b = P(x0, y1), P(x1, y0)
        d.rectangle([a[0], a[1], b[0], b[1]], **kw)

    # building mass (walls appear as the gaps between rooms)
    rect(0, MAIN_LEN, 0, MAIN_DEPTH, fill=(70, 70, 72))
    show_eb = True
    if show_eb:
        rect(ENT_X0, ENT_X1, ENT_Y0, 0, fill=(70, 70, 72))
    zmid = LEVELS[lvl] + 1.5
    rooms = [r for r in layout.rooms.values() if r.z0 - 1e-6 <= zmid <= r.z1 + 1e-6 or r.level == lvl]
    rooms = [r for r in rooms if r.z0 <= LEVELS[lvl] + 0.01 + (3.0 if r.level == lvl else 0) and r.z1 > LEVELS[lvl]]
    for r in rooms:
        col = DEPT_COL[r.dept]
        if r.kind in ("stair_main", "stair_end"):
            col = (225, 225, 225)
        if r.kind == "shaft":
            col = (150, 150, 150)
        for (x0, x1, y0, y1) in r.rects:
            rect(x0, x1, y0, y1, fill=col)
        if r.kind == "club_hall" and lvl != 1:
            for (x0, x1, y0, y1) in r.rects:
                rect(x0, x1, y0, y1, fill=(238, 238, 238))
    # columns
    for x in [6.0 * k for k in range(1, 13)]:
        for (ya, yb) in ((FRONT_Y1, FRONT_Y1 + COLUMN), (REAR_Y0 - COLUMN, REAR_Y0)):
            rect(x - COLUMN / 2, x + COLUMN / 2, ya, yb, fill=(40, 40, 40))
    # windows
    for wi, e in layout.win_room.items():
        w = layout.windows[wi]
        if w.level != lvl and not (w.kind == "hall" and lvl == 1) or (w.kind == "std" and w.level != lvl):
            continue
        a, b = w.s - w.hw, w.s + w.hw
        if w.axis == "x":
            rect(a, b, min(w.plane, w.face), max(w.plane, w.face), fill=(150, 200, 235))
        else:
            rect(min(w.plane, w.face), max(w.plane, w.face), a, b, fill=(150, 200, 235))
    # doors / openings
    for g in layout.doors:
        if g.door.level != lvl:
            continue
        k = g.door.kind
        fa, fb = g.fa, g.fb
        a, b = g.c - g.ow / 2, g.c + g.ow / 2
        col = {"window": (150, 200, 235), "port": (150, 200, 235), "counter": (240, 230, 120),
               "lift": (200, 60, 60)}.get(k, (255, 255, 255))
        lo, hi = min(fa, fb), max(fa, fb)
        if g.axis == "x":
            rect(a, b, lo, hi, fill=col)
        else:
            rect(lo, hi, a, b, fill=col)
        if k in ("window", "port", "counter", "lift", "opening"):
            continue
        # swing arc into room "a" (or b) side
        side = g.fa if g.door.swing == "a" else g.fb
        sgn = -g.nab if g.door.swing == "a" else g.nab
        leaves = [(a, +1), (b, -1)] if ("double" in k) else [(a if g.door.hinge == "l" else b, +1 if g.door.hinge == "l" else -1)]
        lw = (b - a) / len(leaves)
        for (hs, dirn) in leaves:
            if g.axis == "x":
                cx, cy = P(hs, side)
                r = lw * S
                ang = 90 if sgn < 0 else -90
                pts = []
                for t in range(0, 91, 10):
                    th = math.radians(t)
                    pts.append((cx + dirn * r * math.cos(th), cy - (1 if sgn > 0 else -1) * r * math.sin(th)))
                d.line(pts, fill=(120, 120, 120), width=1)
                d.line([pts[-1], (cx, cy)], fill=(40, 40, 40), width=2)
            else:
                cx, cy = P(side, hs)
                r = lw * S
                pts = []
                for t in range(0, 91, 10):
                    th = math.radians(t)
                    pts.append((cx + (1 if sgn > 0 else -1) * r * math.sin(th), cy - dirn * r * math.cos(th)))
                d.line(pts, fill=(120, 120, 120), width=1)
                d.line([pts[-1], (cx, cy)], fill=(40, 40, 40), width=2)
    # stairs: tread lines
    for r in rooms:
        if r.kind not in ("stair_main", "stair_end"):
            continue
        for seg in stair_plan_lines(r):
            d.line([P(*seg[0]), P(*seg[1])], fill=(110, 110, 110), width=1)
        if r.kind == "shaft":
            pass
    for r in rooms:
        if r.kind == "shaft":
            x0, x1, y0, y1 = r.rects[0]
            d.line([P(x0, y0), P(x1, y1)], fill=(60, 60, 60), width=2)
            d.line([P(x0, y1), P(x1, y0)], fill=(60, 60, 60), width=2)
    # labels
    fn, fs, fb = font(15, True), font(11), font(13, True)
    for r in rooms:
        if r.kind == "club_hall" and lvl != 1:
            continue
        x0, x1, y0, y1 = max(r.rects, key=lambda q: (q[1] - q[0]) * (q[3] - q[2]))
        cx, cy = P((x0 + x1) / 2, (y0 + y1) / 2)
        wpx = (x1 - x0) * S - 6
        lines = []
        if r.num:
            lines.append((r.num, fn))
        words, cur = r.en.split(), ""
        for wd in words:
            t = (cur + " " + wd).strip()
            if d.textlength(t, font=fs) <= wpx:
                cur = t
            else:
                if cur:
                    lines.append((cur, fs))
                cur = wd
        if cur:
            lines.append((cur, fs))
        if len(lines) > 7:
            lines = lines[:7]
        hh = sum(f.size + 2 for _, f in lines)
        yy = cy - hh / 2
        for t, f in lines:
            tw = d.textlength(t, font=f)
            d.text((cx - tw / 2, yy), t, font=f, fill=(20, 20, 20))
            yy += f.size + 2
    # title, scale bar, legend
    d.text((20, 12), title, font=font(26, True), fill=(10, 10, 10))
    bx, by = 20, H - 60
    for i in range(10):
        d.rectangle([bx + i * S, by, bx + (i + 1) * S, by + 8], fill=(0, 0, 0) if i % 2 == 0 else (255, 255, 255),
                    outline=(0, 0, 0))
    d.text((bx, by + 12), "0        5        10 m", font=fs, fill=(0, 0, 0))
    lx = 380
    for k, col in DEPT_COL.items():
        d.rectangle([lx, by, lx + 22, by + 16], fill=col, outline=(0, 0, 0))
        d.text((lx + 28, by), DEPT_EN[k], font=fs, fill=(0, 0, 0))
        lx += 34 + d.textlength(DEPT_EN[k], font=fs) + 18
    for col, t in (((150, 200, 235), "window / glazing"), ((240, 230, 120), "service counter"),
                   ((200, 60, 60), "lift door")):
        d.rectangle([lx, by, lx + 22, by + 16], fill=col, outline=(0, 0, 0))
        d.text((lx + 28, by), t, font=fs, fill=(0, 0, 0))
        lx += 34 + d.textlength(t, font=fs) + 18
    d.text((20, H - 30), "Main facade (entrance side) at the bottom. North arrow not given in the source model.",
           font=fs, fill=(90, 90, 90))
    im.save(path, optimize=True)


def stair_plan_lines(r):
    """Tread lines for the plan, consistent with stairs.py (local frame via stair_frame)."""
    from .stairs_layout import stair_frame, stair_spec
    fr = stair_frame(r)
    out = []
    sp = stair_spec()
    for flight in sp["flights"]:
        (u0, u1), (v0, v1) = flight["u"], flight["v"]
        n = RISERS_PER_FLIGHT - 1
        for i in range(n + 1):
            u = u0 + (u1 - u0) * i / n
            out.append((fr(u, v0), fr(u, v1)))
        out.append((fr(u0, v0), fr(u1, v0)))
        out.append((fr(u0, v1), fr(u1, v1)))
    return out
