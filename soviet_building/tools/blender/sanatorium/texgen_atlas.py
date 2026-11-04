"""Painted texture atlases: furniture/equipment (opaque), decals (RGBA) and door plates.

All artwork is drawn procedurally with Pillow; text is Russian, as on the original signs."""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from .texcore import *
from . import atlas as A


class Tile:
    def __init__(self, w, h, seed, mode="RGB", bg=(128, 128, 128)):
        self.w, self.h = w, h
        self.r = np.random.default_rng(seed)
        self.seed = seed
        self.img = Image.new(mode, (w, h), bg if mode == "RGB" else bg + (255,) if len(bg) == 3 else bg)
        self.d = ImageDraw.Draw(self.img)
        self.hm = Image.new("L", (w, h), 128)
        self.dh = ImageDraw.Draw(self.hm)
        self.rough = 0.6
        self.metal = 0.0
        self.grime = 1.0

    def n(self, beta=1.6, k=0):
        return spectral(self.h, self.w, beta, self.seed + 31 * k)


def c8(h, a=None):
    v = tuple(int(x * 255) for x in col(h))
    return v if a is None else v + (a,)


def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c[:3]) + tuple(c[3:])


def bevel_rect(t, box, fill, depth=10, hw=3, light=1.15, dark=0.7):
    x0, y0, x1, y1 = box
    t.d.rectangle(box, fill=fill)
    t.d.line([(x0, y1), (x0, y0), (x1, y0)], fill=shade(fill, light), width=hw)
    t.d.line([(x0, y1), (x1, y1), (x1, y0)], fill=shade(fill, dark), width=hw)
    t.dh.rectangle(box, fill=128 + depth)


def grain_fill(t, c0, c1, box=None, vertical=True, k=0):
    w, h = t.w, t.h
    xx = np.repeat(np.arange(w)[None, :], h, 0) / w
    yy = np.repeat(np.arange(h)[:, None], w, 1) / h
    warp = spectral(h, w, 2.4, t.seed + k) * 5
    a = (xx if vertical else yy) * 18 + warp
    g = np.clip((np.sin(a * 2 * np.pi) * 0.5 + 0.5) * 0.6 + spectral(h, w, 0.5, t.seed + 7 + k) * 0.4, 0, 1)
    rgb = lerp(col(c0), col(c1), g)
    im = Image.fromarray(to8(rgb), "RGB")
    if box is None:
        t.img.paste(im)
    else:
        t.img.paste(im.crop(box), box[:2])


def txt(t, xy, s, size, fill, weight="Bold", anchor="mm"):
    t.d.text(xy, s, font=font(size, weight), fill=fill, anchor=anchor)


def noise_fill(t, c, amt=0.12, beta=1.8):
    n = t.n(beta)
    rgb = col(c)[None, None, :] * (1 - amt / 2 + amt * n[..., None])
    t.img.paste(Image.fromarray(to8(rgb), "RGB"))


def knob(t, x, y, r, c="#b9b2a0"):
    t.d.ellipse([x - r, y - r, x + r, y + r], fill=c8(c), outline=c8("#3a3530"))
    t.dh.ellipse([x - r, y - r, x + r, y + r], fill=200)


# ---------------------------------------------------------------- furniture painters
def p_wood_plain(t):
    grain_fill(t, "#5e3d23", "#8a5f3a"); t.rough = 0.4


def p_wood_dark(t):
    grain_fill(t, "#3b2618", "#5a3a24"); t.rough = 0.38


def p_wood_light(t):
    grain_fill(t, "#9b7650", "#c29a6a"); t.rough = 0.5


def p_wardrobe(t):
    grain_fill(t, "#5a3a22", "#83593a")
    w, h = t.w, t.h
    t.d.line([(w // 2, 6), (w // 2, h - 40)], fill=c8("#2a1a10"), width=3)
    for x0, x1 in ((10, w // 2 - 6), (w // 2 + 6, w - 10)):
        t.d.rectangle([x0, 10, x1, h - 46], outline=c8("#3a2414"), width=2)
        t.dh.rectangle([x0, 10, x1, h - 46], fill=140)
    t.d.rectangle([8, h - 38, w - 8, h - 8], fill=c8("#4a2f1c"), outline=c8("#2a1a10"), width=2)  # drawer
    knob(t, w // 2 - 14, h // 2, 6); knob(t, w // 2 + 14, h // 2, 6); knob(t, w // 2, h - 23, 5)
    t.d.rectangle([w // 2 + 9, h // 2 + 14, w // 2 + 13, h // 2 + 24], fill=c8("#151010"))  # keyhole
    t.rough = 0.42


def p_bookcase(t):
    grain_fill(t, "#5a3a22", "#83593a")
    w, h = t.w, t.h
    t.d.rectangle([12, 12, w - 12, h * 0.62], fill=c8("#1d1a17"))
    sh = [int(12 + i * (h * 0.62 - 12) / 4) for i in range(5)]
    for i in range(4):
        x = 16
        while x < w - 18:
            bw = int(t.r.uniform(6, 18))
            bh = int(t.r.uniform(0.6, 0.95) * (sh[i + 1] - sh[i] - 4))
            cc = c8(["#6a2b20", "#24465a", "#3e5a2a", "#6e5a2c", "#5a3a52", "#2f2f2f", "#8a7a5a"][t.r.integers(7)])
            t.d.rectangle([x, sh[i + 1] - 2 - bh, x + bw - 1, sh[i + 1] - 2], fill=shade(cc, t.r.uniform(.7, 1.1)))
            x += bw + int(t.r.integers(0, 3))
        t.d.line([(12, sh[i + 1]), (w - 12, sh[i + 1])], fill=c8("#6a4a2e"), width=3)
    # glass reflection
    t.d.line([(30, 20), (90, h * 0.6)], fill=c8("#4a4c4c"), width=8)
    t.d.line([(w // 2, 12), (w // 2, h * 0.62)], fill=c8("#3a2414"), width=4)
    t.d.rectangle([12, h * 0.65, w - 12, h - 12], outline=c8("#3a2414"), width=3)
    t.d.line([(w // 2, h * 0.65), (w // 2, h - 12)], fill=c8("#3a2414"), width=3)
    knob(t, w // 2 - 10, h * 0.82, 5); knob(t, w // 2 + 10, h * 0.82, 5)
    t.rough = 0.35


def p_filing(t):
    noise_fill(t, "#7d8a7c")
    w, h = t.w, t.h
    for i in range(4):
        y0 = 10 + i * (h - 20) // 4
        bevel_rect(t, (10, y0 + 4, w - 10, y0 + (h - 20) // 4 - 4), c8("#86937f"))
        t.d.rectangle([w // 2 - 30, y0 + 18, w // 2 + 30, y0 + 30], fill=c8("#d8d2bc"), outline=c8("#333"))
        t.d.rounded_rectangle([w // 2 - 36, y0 + 40, w // 2 + 36, y0 + 52], 5, fill=c8("#b8b4a8"))
        txt(t, (w // 2, y0 + 24), ["А–Г", "Д–К", "Л–П", "Р–Я"][i], 11, c8("#222"))
    t.rough, t.metal = 0.5, 0.25


def p_med_cabinet(t):
    noise_fill(t, "#e8e6de", 0.06)
    w, h = t.w, t.h
    t.d.rectangle([14, 14, w - 14, h * 0.7], fill=c8("#cfd6d6"))
    for i in range(1, 4):
        y = int(14 + i * (h * 0.7 - 14) / 4)
        t.d.line([(14, y), (w - 14, y)], fill=c8("#9aa2a2"), width=3)
        x = 22
        while x < w - 30:
            if t.r.random() < 0.45:
                bh = int(t.r.uniform(18, 40))
                cc = c8(["#7a4a1a", "#d8d8d0", "#3a6a8a", "#c8a050", "#6a2a2a"][t.r.integers(5)])
                t.d.rectangle([x, y - bh, x + 12, y - 2], fill=cc)
                t.d.rectangle([x + 2, y - bh - 5, x + 10, y - bh], fill=c8("#ddd"))
            x += 18
    t.d.line([(w // 2, 14), (w // 2, h * 0.7)], fill=c8("#d8d6ce"), width=5)
    t.d.line([(30, 24), (70, h * 0.66)], fill=c8("#eef2f2"), width=6)
    t.d.rectangle([14, h * 0.73, w - 14, h - 14], outline=c8("#b4b0a6"), width=2)
    t.d.line([(w // 2, h * 0.73), (w // 2, h - 14)], fill=c8("#b4b0a6"), width=2)
    knob(t, w // 2 - 10, h * 0.85, 4, "#9a9a92"); knob(t, w // 2 + 10, h * 0.85, 4, "#9a9a92")
    txt(t, (w // 2, h * 0.79), "✚", 18, c8("#b02a2a"))
    t.rough, t.metal = 0.3, 0.1


def p_fridge(t):
    noise_fill(t, "#e9e5d8", 0.06)
    w, h = t.w, t.h
    t.d.rounded_rectangle([6, 6, w - 6, h - 40], 16, outline=c8("#cfcabd"), width=4)
    t.d.rectangle([w - 40, h * 0.35, w - 26, h * 0.55], fill=c8("#c8c8c0"))
    txt(t, (w // 2, 50), "ЗИЛ", 34, c8("#a0a4a8"), "Black")
    t.d.rectangle([6, h - 36, w - 6, h - 6], fill=c8("#3a3a38"))
    for x in range(14, w - 14, 10):
        t.d.line([(x, h - 32), (x, h - 10)], fill=c8("#222"), width=3)
    t.rough, t.metal = 0.3, 0.05


def p_elec_panel(t):
    noise_fill(t, "#8b958c")
    w, h = t.w, t.h
    bevel_rect(t, (8, 8, w - 8, h - 8), c8("#909b91"), hw=4)
    t.d.polygon([(w // 2, 60), (w // 2 - 50, 140), (w // 2 + 50, 140)], fill=c8("#e2c22a"), outline=c8("#111"))
    t.d.line([(w // 2 + 6, 78), (w // 2 - 8, 108), (w // 2 + 8, 106), (w // 2 - 6, 134)], fill=c8("#111"), width=5)
    txt(t, (w // 2, 175), "НЕ ВЛЕЗАЙ", 22, c8("#9a1a12"))
    txt(t, (w // 2, 202), "УБЬЁТ!", 26, c8("#9a1a12"))
    txt(t, (w // 2, 250), "ЩР-1  380/220 В", 15, c8("#222"))
    t.d.rectangle([w - 40, h // 2 - 20, w - 28, h // 2 + 20], fill=c8("#333"))
    t.rough, t.metal = 0.5, 0.3


def p_elevator_door(t):
    noise_fill(t, "#7a7e72", 0.1)
    w, h = t.w, t.h
    t.d.line([(w // 2, 0), (w // 2, h)], fill=c8("#222"), width=4)
    for x0, x1 in ((6, w // 2 - 4), (w // 2 + 4, w - 6)):
        t.d.rectangle([x0, 6, x1, h - 6], outline=c8("#5a5d54"), width=3)
        for y in range(int(h * 0.25), int(h * 0.8), 60):
            t.d.line([(x0 + 10, y), (x1 - 10, y)], fill=c8("#6d7166"), width=2)
    t.rough, t.metal = 0.45, 0.35


def p_cabin_wall(t):
    grain_fill(t, "#7a5530", "#a07548", vertical=True, k=3)
    w, h = t.w, t.h
    for x in (w // 3, 2 * w // 3):
        t.d.line([(x, 0), (x, h)], fill=c8("#3a2818"), width=3)
    t.d.rectangle([0, h * 0.42, w, h * 0.46], fill=c8("#b0aca0"))
    t.rough = 0.35


def p_hose_cabinet(t):
    noise_fill(t, "#b8302a")
    w, h = t.w, t.h
    bevel_rect(t, (8, 8, w - 8, h - 8), c8("#b8302a"))
    t.d.rectangle([30, 60, w - 30, h * 0.55], fill=c8("#d8d4c8"))
    txt(t, (w // 2, 110), "ПК", 70, c8("#b8302a"), "Black")
    txt(t, (w // 2, 190), "№ 3", 34, c8("#222"))
    t.d.ellipse([w // 2 - 60, h * 0.6, w // 2 + 60, h * 0.6 + 120], outline=c8("#e8e0d0"), width=6)
    t.rough = 0.5


def p_partition(t):
    noise_fill(t, "#b9b8a6")
    t.d.rectangle([4, 4, t.w - 4, t.h - 4], outline=c8("#8a8a7a"), width=3)
    sc = scratches(t.h, t.w, 30, t.seed, (0.05, 0.2), 1)
    t.img = Image.fromarray(to8(np.asarray(t.img) / 255.0 * (1 - 0.3 * sc[..., None])))
    t.d = ImageDraw.Draw(t.img)
    t.rough = 0.5


def p_stage_curtain(t):
    w, h = t.w, t.h
    x = np.arange(w) / w
    fold = (np.sin(x * 2 * np.pi * 7) * 0.5 + 0.5) ** 1.5
    rgb = lerp(col("#3a0a0c"), col("#8e1a1e"), np.repeat(fold[None, :], h, 0))
    rgb *= (0.85 + 0.25 * spectral(h, w, 1.6, t.seed)[..., None])
    t.img = Image.fromarray(to8(rgb)); t.d = ImageDraw.Draw(t.img)
    t.hm = Image.fromarray(to8(np.repeat(fold[None, :], h, 0))); t.dh = ImageDraw.Draw(t.hm)
    t.rough = 0.9


def p_cabin_panel(t):
    noise_fill(t, "#7c7f76", 0.08)
    w, h = t.w, t.h
    bevel_rect(t, (6, 6, w - 6, h - 6), c8("#83867c"))
    txt(t, (w // 2, 26), "ЛИФТ", 16, c8("#e8e4d6"))
    for i, lab in enumerate(["4", "3", "2", "1"]):
        y = 70 + i * 56
        t.d.ellipse([w // 2 - 20, y - 20, w // 2 + 20, y + 20], fill=c8("#2a2a2a"), outline=c8("#c0bcb0"), width=3)
        txt(t, (w // 2, y), lab, 22, c8("#e8e4d6"))
    t.d.ellipse([w // 2 - 22, 310 - 22, w // 2 + 22, 310 + 22], fill=c8("#b0221c"))
    txt(t, (w // 2, 310), "СТОП", 11, c8("#fff"))
    t.d.ellipse([w // 2 - 18, 370 - 18, w // 2 + 18, 370 + 18], fill=c8("#d8b020"))
    txt(t, (w // 2, 370), "ВЫЗОВ", 9, c8("#222"))
    t.d.ellipse([w // 2 - 16, 432 - 16, w // 2 + 16, 432 + 16], fill=c8("#b8b4a4"), outline=c8("#333"), width=2)
    t.d.rectangle([w // 2 - 3, 422, w // 2 + 3, 442], fill=c8("#111"))
    txt(t, (w // 2, 462), "КЛЮЧ", 12, c8("#e8e4d6"))
    txt(t, (w // 2, 488), "500 кг", 11, c8("#d8d4c6"), "Regular")
    t.rough, t.metal = 0.45, 0.4


def p_landing_panel(t):
    noise_fill(t, "#7c7f76", 0.08)
    w, h = t.w, t.h
    bevel_rect(t, (6, 6, w - 6, h - 6), c8("#83867c"))
    t.d.rectangle([16, 20, w - 16, 110], fill=c8("#e2dccb"))
    txt(t, (w // 2, 44), "ЛИФТ", 17, c8("#9a1a12"))
    txt(t, (w // 2, 68), "СЛУЖЕБНЫЙ", 11, c8("#9a1a12"))
    txt(t, (w // 2, 92), "по ключу", 12, c8("#222"), "Regular")
    t.d.ellipse([w // 2 - 22, 180 - 22, w // 2 + 22, 180 + 22], fill=c8("#2a2a2a"), outline=c8("#c0bcb0"), width=4)
    t.d.ellipse([w // 2 - 9, 180 - 9, w // 2 + 9, 180 + 9], fill=c8("#7a1410"))
    txt(t, (w // 2, 222), "ВЫЗОВ", 13, c8("#e8e4d6"))
    t.d.ellipse([w // 2 - 24, 300 - 24, w // 2 + 24, 300 + 24], fill=c8("#b8b4a4"), outline=c8("#333"), width=3)
    t.d.rectangle([w // 2 - 4, 286, w // 2 + 4, 314], fill=c8("#111"))
    txt(t, (w // 2, 344), "ВКЛ  ВЫКЛ", 11, c8("#e8e4d6"))
    t.d.ellipse([w // 2 - 7, 400 - 7, w // 2 + 7, 400 + 7], fill=c8("#4a1a14"))
    txt(t, (w // 2, 422), "ЗАНЯТО", 11, c8("#e8e4d6"))
    t.rough, t.metal = 0.45, 0.4


def p_door_steel(t):
    noise_fill(t, "#6f6a5e", 0.12)
    bevel_rect(t, (10, 10, t.w - 10, t.h - 10), c8("#746f62"))
    t.d.rectangle([t.w - 40, t.h // 2 - 12, t.w - 22, t.h // 2 + 12], fill=c8("#333"))
    t.rough, t.metal = 0.55, 0.35


def p_door_glazed(t):
    grain_fill(t, "#3b2618", "#5a3a24")
    t.d.rectangle([28, 28, t.w - 28, t.h * 0.55], fill=c8("#55605e"))
    t.d.rectangle([28, t.h * 0.6, t.w - 28, t.h - 28], outline=c8("#2a180c"), width=3)
    t.rough = 0.4


def p_door_padded(t):
    noise_fill(t, "#4a2a1e", 0.15)
    w, h = t.w, t.h
    for i in range(0, w + h, 36):
        t.d.line([(i, 0), (i - h, h)], fill=c8("#3a2016"), width=2)
        t.d.line([(i - h, 0), (i, h)], fill=c8("#3a2016"), width=2)
    for x in range(18, w, 36):
        for y in range(18, h, 36):
            knob(t, x, y, 3, "#a89060")
    t.rough = 0.55


def p_desk_front(t):
    grain_fill(t, "#5a3a22", "#83593a", vertical=False)
    w, h = t.w, t.h
    t.d.rectangle([150, 0, w - 150, h], fill=c8("#1b130c"))
    for x0 in (8, w - 142):
        for i in range(4):
            y0 = 8 + i * (h - 16) // 4
            t.d.rectangle([x0, y0, x0 + 134, y0 + (h - 16) // 4 - 6], outline=c8("#3a2414"), width=2)
            knob(t, x0 + 67, y0 + (h - 16) // 8, 5)
    t.rough = 0.42


def p_radiator(t):
    w, h = t.w, t.h
    x = np.arange(w) / w
    sec = (np.sin(x * 2 * np.pi * 16) * 0.5 + 0.5)
    hh = np.repeat(sec[None, :], h, 0)
    yy = np.repeat((np.arange(h) / h)[:, None], w, 1)
    rgb = lerp(col("#8f8a78"), col("#d6d0bc"), hh) * (0.9 + 0.15 * spectral(h, w, 1.6, t.seed)[..., None])
    rust = smooth(0.55, 1.0, yy) * (spectral(h, w, 1.3, t.seed + 1) > 0.55)
    rgb = mix_col(rust * 0.75, rgb, col("#7a4220"))
    gap = hh < 0.08
    rgb[gap] *= 0.35
    t.img = Image.fromarray(to8(rgb)); t.d = ImageDraw.Draw(t.img)
    t.hm = Image.fromarray(to8(hh)); t.dh = ImageDraw.Draw(t.hm)
    t.rough, t.metal = 0.6, 0.15


def p_cinema_seats(t):
    w, h = t.w, t.h
    t.d.rectangle([0, 0, w, h], fill=c8("#2a1812"))
    n = 8
    for i in range(n):
        x0 = i * w / n
        t.d.rounded_rectangle([x0 + 8, 10, x0 + w / n - 8, h * 0.62], 10, fill=c8("#7a1c1c"))
        t.d.rounded_rectangle([x0 + 8, h * 0.66, x0 + w / n - 8, h - 12], 6, fill=c8("#6a1616"))
        t.d.rectangle([x0, 0, x0 + 6, h], fill=c8("#6a4628"))
        txt(t, (x0 + w / n / 2, 26), str(i + 1), 12, c8("#d8c8a0"))
    t.rough = 0.85


def p_bedside(t):
    grain_fill(t, "#5a3a22", "#83593a")
    w, h = t.w, t.h
    t.d.rectangle([8, 8, w - 8, 70], outline=c8("#3a2414"), width=2); knob(t, w // 2, 39, 6)
    t.d.rectangle([8, 80, w - 8, h - 8], outline=c8("#3a2414"), width=2); knob(t, w - 30, 150, 6)
    t.rough = 0.42


def p_drawer_front(t):
    grain_fill(t, "#5a3a22", "#83593a", vertical=False)
    t.d.rectangle([6, 6, t.w - 6, t.h - 6], outline=c8("#3a2414"), width=3); knob(t, t.w // 2, t.h // 2, 7)
    t.rough = 0.42


def p_safe(t):
    noise_fill(t, "#5f6a62")
    bevel_rect(t, (10, 10, t.w - 10, t.h - 10), c8("#66716a"))
    t.d.ellipse([90, 70, 166, 146], fill=c8("#2a2a2a"), outline=c8("#b8b4a0"), width=4)
    for k in range(12):
        a = k * np.pi / 6
        t.d.line([(128 + 30 * np.cos(a), 108 + 30 * np.sin(a)), (128 + 36 * np.cos(a), 108 + 36 * np.sin(a))],
                 fill=c8("#ddd"), width=2)
    t.d.rectangle([118, 170, 138, 210], fill=c8("#b8b4a0"))
    t.rough, t.metal = 0.45, 0.5


def p_stove_top(t):
    noise_fill(t, "#3a3a38")
    for (x, y) in ((64, 64), (192, 64), (64, 192), (192, 192)):
        t.d.rectangle([x - 52, y - 52, x + 52, y + 52], fill=c8("#1a1a1a"), outline=c8("#555"), width=3)
        for k in range(4):
            t.d.rectangle([x - 44 + k * 6, y - 44 + k * 6, x + 44 - k * 6, y + 44 - k * 6], outline=c8("#2c2c2c"))
    t.rough, t.metal = 0.6, 0.6


def p_stove_front(t):
    noise_fill(t, "#c8c6bc", 0.08)
    t.d.rectangle([10, 60, 246, 246], outline=c8("#888"), width=4)
    t.d.rectangle([30, 76, 226, 92], fill=c8("#9a9a90"))
    for x in (40, 90, 140, 190):
        knob(t, x, 30, 12, "#222")
    txt(t, (128, 170), "ЭП-6", 20, c8("#666"))
    t.rough, t.metal = 0.35, 0.6


def p_steel(t):
    w, h = t.w, t.h
    n = spectral(h, w, 1.2, t.seed)
    br = blur(np.repeat(spectral(1, w, 0.3, t.seed + 1), h, 0), 0.5)
    rgb = col("#a8aaa8")[None, None, :] * (0.85 + 0.15 * br[..., None] + 0.08 * n[..., None])
    t.img = Image.fromarray(to8(rgb)); t.d = ImageDraw.Draw(t.img)
    t.rough, t.metal = 0.35, 0.95


def p_fuse_board(t):
    noise_fill(t, "#8b958c")
    for row in range(3):
        y = 30 + row * 75
        t.d.rectangle([14, y, 242, y + 50], fill=c8("#d8d2bc"))
        for i in range(8):
            x = 22 + i * 28
            t.d.rectangle([x, y + 8, x + 18, y + 42], fill=c8("#e8e4d8"), outline=c8("#555"))
            t.d.rectangle([x + 5, y + 14, x + 13, y + 26], fill=c8("#222") if (i + row) % 3 else c8("#a01810"))
    t.rough, t.metal = 0.5, 0.2


def p_vent_unit(t):
    noise_fill(t, "#6f7c76")
    t.d.ellipse([20, 20, 236, 236], fill=c8("#2a2e2c"), outline=c8("#9aa69e"), width=6)
    for k in range(6):
        a = k * np.pi / 3
        t.d.polygon([(128, 128), (128 + 100 * np.cos(a), 128 + 100 * np.sin(a)),
                     (128 + 100 * np.cos(a + 0.5), 128 + 100 * np.sin(a + 0.5))], fill=c8("#5a625e"))
    for y in range(28, 236, 14):
        t.d.line([(26, y), (230, y)], fill=c8("#8a948e"), width=2)
    t.rough, t.metal = 0.55, 0.4


def p_pump(t):
    noise_fill(t, "#3e6a6e")
    t.d.rectangle([10, 80, 246, 180], fill=c8("#3a6468"))
    t.d.ellipse([60, 40, 196, 220], outline=c8("#2a4a4e"), width=8)
    txt(t, (128, 128), "К-90", 22, c8("#c8d0c8"))
    t.rough, t.metal = 0.5, 0.4


def p_mattress(t):
    w, h = t.w, t.h
    x = np.arange(w)
    stripes = ((x // 12) % 2 == 0)
    rgb = np.where(np.repeat(stripes[None, :], h, 0)[..., None], col("#c9c2ae"), col("#8a96a4"))
    rgb = rgb * (0.9 + 0.12 * spectral(h, w, 1.6, t.seed)[..., None])
    st = blobs(h, w, 3, t.seed, 20, 50)
    rgb = mix_col(np.clip(st * 0.5, 0, .5), rgb, col("#9c8452"))
    t.img = Image.fromarray(to8(rgb)); t.d = ImageDraw.Draw(t.img)
    t.rough = 0.9


def p_blanket(t):
    w, h = t.w, t.h
    x = np.arange(w)[None, :].repeat(h, 0)
    y = np.arange(h)[:, None].repeat(w, 1)
    chk = ((x // 32 + y // 32) % 2 == 0)
    rgb = np.where(chk[..., None], col("#6e4a3a"), col("#8a6a4a"))
    lines = (x % 32 < 3) | (y % 32 < 3)
    rgb[lines] = col("#c8b890")
    rgb *= (0.88 + 0.2 * spectral(h, w, 0.8, t.seed)[..., None])
    t.img = Image.fromarray(to8(rgb)); t.d = ImageDraw.Draw(t.img)
    t.rough = 0.95


def p_linen_white(t):
    noise_fill(t, "#dcd8cc", 0.1, 1.2)
    t.d.ellipse([170, 190, 240, 240], outline=c8("#6a7a9a"), width=3)
    txt(t, (205, 215), "Сан.", 12, c8("#6a7a9a"))
    for k in range(6):
        y = int(t.r.uniform(0, 256))
        t.d.line([(0, y), (256, y + t.r.uniform(-20, 20))], fill=c8("#c4c0b2"), width=2)
    t.rough = 0.9


def p_upholstery(c):
    def f(t):
        noise_fill(t, c, 0.2, 1.3)
        for k in range(8):
            x, y = t.r.uniform(0, 256, 2)
            t.d.line([(x, y), (x + t.r.uniform(-40, 40), y + t.r.uniform(-40, 40))], fill=shade(c8(c), 1.25), width=2)
        t.rough = 0.55 if c == "#4a2a1c" else 0.9
    return f


def p_typewriter(t):
    noise_fill(t, "#3c3e3a")
    t.d.rectangle([20, 20, 236, 70], fill=c8("#2a2a28"))
    for r in range(4):
        for i in range(11 - r % 2):
            x, y = 34 + i * 19 + (r % 2) * 9, 100 + r * 30
            t.d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=c8("#e8e4d8"), outline=c8("#111"))
    t.d.rectangle([60, 222, 196, 238], fill=c8("#e8e4d8"))
    txt(t, (128, 45), "Ятрань", 20, c8("#c8c4b4"))
    t.rough, t.metal = 0.4, 0.3


def p_tv(t):
    grain_fill(t, "#4a3020", "#6a4630")
    t.d.rounded_rectangle([18, 22, 186, 200], 26, fill=c8("#1e2422"))
    t.d.rounded_rectangle([30, 34, 174, 188], 22, fill=c8("#38423e"))
    t.d.line([(50, 50), (110, 60)], fill=c8("#5a6460"), width=6)
    for y in range(40, 200, 22):
        knob(t, 220, y, 7, "#c8c4b4")
    txt(t, (100, 228), "Рубин", 20, c8("#c8b890"))
    t.rough = 0.35


def p_piano(t):
    grain_fill(t, "#1e1410", "#2e1e16")
    t.d.rectangle([0, 150, 256, 200], fill=c8("#e8e2d0"))
    for i in range(36):
        x = i * 256 / 36
        t.d.line([(x, 150), (x, 200)], fill=c8("#888"), width=1)
        if i % 7 not in (2, 6):
            t.d.rectangle([x + 4, 150, x + 9, 180], fill=c8("#111"))
    txt(t, (128, 80), "Красный Октябрь", 18, c8("#b8a060"), "Regular")
    t.rough = 0.25


def p_book_spines(t):
    t.d.rectangle([0, 0, 256, 256], fill=c8("#2a2018"))
    for row in range(4):
        x = 0
        y1 = (row + 1) * 64 - 4
        while x < 256:
            bw = int(t.r.uniform(8, 22))
            cc = c8(["#6a2b20", "#24465a", "#3e5a2a", "#6e5a2c", "#5a3a52", "#2f2f2f", "#8a7a5a", "#7a6a50"][t.r.integers(8)])
            bh = int(t.r.uniform(40, 58))
            t.d.rectangle([x, y1 - bh, x + bw - 1, y1], fill=shade(cc, t.r.uniform(.7, 1.1)))
            t.d.line([(x + 2, y1 - bh + 8), (x + bw - 3, y1 - bh + 8)], fill=c8("#c8b070"), width=1)
            x += bw
        t.d.rectangle([0, y1, 256, y1 + 4], fill=c8("#5a3a22"))
    t.rough = 0.8


def p_binders(t):
    t.d.rectangle([0, 0, 256, 256], fill=c8("#3a2e22"))
    for row in range(2):
        x = 2
        y1 = (row + 1) * 128 - 6
        while x < 250:
            bw = int(t.r.uniform(20, 30))
            cc = c8(["#5a6a4a", "#7a5a3a", "#8a8070", "#4a5a6a", "#6a3a2a"][t.r.integers(5)])
            t.d.rectangle([x, y1 - 112, x + bw - 2, y1], fill=shade(cc, t.r.uniform(.75, 1.1)))
            t.d.rectangle([x + 4, y1 - 90, x + bw - 6, y1 - 64], fill=c8("#ddd6c2"))
            t.d.ellipse([x + bw // 2 - 4, y1 - 30, x + bw // 2 + 4, y1 - 22], fill=c8("#222"))
            x += bw
        t.d.rectangle([0, y1, 256, y1 + 6], fill=c8("#7a8478"))
    t.rough = 0.8


def p_linen_stack(t):
    t.d.rectangle([0, 0, 256, 256], fill=c8("#6a6a60"))
    for row in range(3):
        y0 = row * 85
        for i in range(4):
            x0 = 6 + i * 62
            for k in range(6):
                yy = y0 + 78 - k * 11
                t.d.rounded_rectangle([x0, yy - 10, x0 + 56, yy], 3,
                                      fill=c8(["#dcd8cc", "#cfd6dc", "#d8d0c0"][k % 3]), outline=c8("#a8a498"))
        t.d.rectangle([0, y0 + 80, 256, y0 + 85], fill=c8("#7a8478"))
    t.rough = 0.9


def p_crates(t):
    grain_fill(t, "#8a6a44", "#b08a5a", vertical=False)
    for y in range(0, 256, 42):
        t.d.rectangle([0, y, 256, y + 8], fill=c8("#3a2a1a"))
    for x in (0, 124, 248):
        t.d.rectangle([x, 0, x + 8, 256], fill=c8("#6a4a2a"))
    t.rough = 0.9


def p_sacks(t):
    noise_fill(t, "#b8a682", 0.25, 1.1)
    for k in range(10):
        x, y = t.r.uniform(0, 256, 2)
        t.d.arc([x - 60, y - 30, x + 60, y + 30], 200, 340, fill=c8("#8a7a5a"), width=3)
    txt(t, (128, 128), "МУКА", 34, c8("#5a4a3a"))
    t.rough = 0.95


def p_tools_board(t):
    grain_fill(t, "#9a8a6a", "#b8a682")
    for i in range(8):
        x = 20 + i * 30
        t.d.rectangle([x, 40, x + 6, 130], fill=c8("#4a4a48"))
        t.d.rectangle([x - 6, 30, x + 12, 50], fill=c8(["#b02a1a", "#2a4a8a", "#222"][i % 3]))
    t.d.rectangle([20, 160, 236, 230], outline=c8("#333"), width=4)
    t.rough = 0.8


def p_screen_fabric(t):
    noise_fill(t, "#e2e2d8", 0.1, 1.0)
    for x in range(0, 256, 24):
        t.d.line([(x, 0), (x, 256)], fill=c8("#d2d2c6"), width=6)
    t.rough = 0.9


def p_lift_machine(t):
    noise_fill(t, "#4f6e52")
    t.d.ellipse([30, 30, 226, 226], outline=c8("#2a3a2a"), width=10)
    for y in range(60, 200, 18):
        t.d.line([(40, y), (216, y)], fill=c8("#3c5440"), width=4)
    txt(t, (128, 128), "ЛЭ-80", 26, c8("#d8d4c0"))
    t.rough, t.metal = 0.5, 0.35


def p_clock_face(t):
    t.d.rectangle([0, 0, 256, 256], fill=c8("#2a2a28"))
    t.d.ellipse([8, 8, 248, 248], fill=c8("#e8e2cc"), outline=c8("#222"), width=8)
    for k in range(12):
        a = k * np.pi / 6
        t.d.line([(128 + 100 * np.sin(a), 128 - 100 * np.cos(a)), (128 + 112 * np.sin(a), 128 - 112 * np.cos(a))],
                 fill=c8("#222"), width=6)
    hr, mn = 3.6, 0.47     # stopped at 10:28
    t.d.line([(128, 128), (128 + 60 * np.sin(hr * 2 * np.pi / 12 * 3.3), 128 - 60 * np.cos(10.47 * np.pi / 6))],
             fill=c8("#111"), width=8)
    t.d.line([(128, 128), (128 + 90 * np.sin(mn * 2 * np.pi), 128 - 90 * np.cos(mn * 2 * np.pi))], fill=c8("#111"),
             width=5)
    txt(t, (128, 175), "СДЕЛАНО В СССР", 10, c8("#555"), "Regular")
    t.rough = 0.25


def p_dish_rack(t):
    noise_fill(t, "#9a9c98")
    for row in range(3):
        y = 20 + row * 80
        for i in range(10):
            x = 14 + i * 24
            t.d.ellipse([x, y, x + 20, y + 60], fill=c8("#e6e2d8"), outline=c8("#9a9488"))
        t.d.rectangle([0, y + 64, 256, y + 70], fill=c8("#6a6c68"))
    t.rough, t.metal = 0.4, 0.5


def p_shelf_goods(t):
    t.d.rectangle([0, 0, 256, 256], fill=c8("#4a4640"))
    for row in range(3):
        y1 = (row + 1) * 85 - 6
        x = 4
        while x < 250:
            kind = t.r.integers(3)
            if kind == 0:
                t.d.rectangle([x, y1 - 50, x + 30, y1], fill=c8("#b8a682"))
                x += 34
            elif kind == 1:
                for k in range(3):
                    t.d.rectangle([x + k * 12, y1 - 36, x + k * 12 + 10, y1], fill=c8("#8a8e8a"))
                x += 40
            else:
                t.d.rectangle([x, y1 - 30, x + 44, y1], fill=c8("#9a7a4a"))
                x += 48
        t.d.rectangle([0, y1, 256, y1 + 6], fill=c8("#7a8478"))
    t.rough = 0.85


def p_lab_equipment(t):
    noise_fill(t, "#d8d6cc")
    t.d.rectangle([20, 40, 120, 200], fill=c8("#e8e6de"), outline=c8("#888"))
    t.d.ellipse([40, 60, 100, 120], fill=c8("#333"))
    t.d.rectangle([150, 60, 236, 220], fill=c8("#5a6a6a"))
    txt(t, (193, 140), "ФЭК-56", 14, c8("#e8e8e0"))
    t.rough, t.metal = 0.4, 0.2


def p_med_boxes(t):
    t.d.rectangle([0, 0, 256, 256], fill=c8("#cfd4d4"))
    for row in range(3):
        y1 = (row + 1) * 85 - 6
        x = 4
        while x < 240:
            if t.r.random() < 0.55:
                bw = int(t.r.uniform(16, 34))
                bh = int(t.r.uniform(20, 50))
                t.d.rectangle([x, y1 - bh, x + bw, y1], fill=c8(["#e8e6dc", "#d8c8a0", "#c8d8e8", "#e0d0d0"][t.r.integers(4)]),
                              outline=c8("#999"))
            x += 36
        t.d.rectangle([0, y1, 256, y1 + 6], fill=c8("#e8e8e0"))
    t.rough = 0.6


def p_carpet(t):
    w, h = t.w, t.h
    t.d.rectangle([0, 0, w, h], fill=c8("#6e1e1a"))
    t.d.rectangle([10, 10, w - 10, h - 10], outline=c8("#1e2a4a"), width=14)
    for k in range(5):
        r = 100 - k * 20
        t.d.polygon([(w / 2, h / 2 - r), (w / 2 + r, h / 2), (w / 2, h / 2 + r), (w / 2 - r, h / 2)],
                    outline=c8(["#d8b870", "#1e2a4a", "#e8e0c8", "#3a5a3a", "#d8b870"][k]), width=6)
    a = np.asarray(t.img) / 255.0 * (0.85 + 0.2 * spectral(h, w, 1.0, t.seed)[..., None])
    t.img = Image.fromarray(to8(a)); t.d = ImageDraw.Draw(t.img)
    t.rough = 0.95


def p_runner(t):
    w, h = t.w, t.h
    t.d.rectangle([0, 0, w, h], fill=c8("#8a1e1a"))
    t.d.rectangle([0, 0, 30, h], fill=c8("#2a4a2a")); t.d.rectangle([w - 30, 0, w, h], fill=c8("#2a4a2a"))
    t.d.rectangle([34, 0, 40, h], fill=c8("#d8c890")); t.d.rectangle([w - 40, 0, w - 34, h], fill=c8("#d8c890"))
    a = np.asarray(t.img) / 255.0
    wear = smooth(0.4, 0.9, spectral(h, w, 2.0, t.seed))
    a = a * (1 - 0.35 * wear[..., None]) + col("#7a6a5a") * 0.35 * wear[..., None]
    t.img = Image.fromarray(to8(a)); t.d = ImageDraw.Draw(t.img)
    t.rough = 0.95


def p_floor_indicator(t):
    noise_fill(t, "#6f726a")
    t.d.pieslice([28, 20, 228, 220], 180, 360, fill=c8("#e2dccb"), outline=c8("#2a2a2a"), width=4)
    for i, lab in enumerate(["1", "2", "3", "4"]):
        a = np.pi * (1 - (i + 0.5) / 4)
        x, y = 128 + 78 * np.cos(a), 120 - 78 * np.sin(a)
        txt(t, (x, y), lab, 20, c8("#222"))
    txt(t, (128, 112), "ЭТАЖ", 10, c8("#444"), "Regular")
    t.rough, t.metal = 0.4, 0.3


def p_exam_couch(t):
    noise_fill(t, "#4a2a1c", 0.2, 1.3)
    for x in range(0, 256, 64):
        t.d.line([(x, 0), (x, 128)], fill=c8("#3a2014"), width=3)
    t.rough = 0.55


def p_fluo(t):
    t.d.rectangle([0, 0, t.w, t.h], fill=c8("#efeee4"))
    for x in range(0, t.w, 6):
        t.d.line([(x, 0), (x, t.h)], fill=c8("#d8d6c8"), width=2)
    t.rough = 0.3


def p_telephone(t):
    noise_fill(t, "#2a2624", 0.1)
    t.d.ellipse([24, 24, 104, 104], fill=c8("#d8d4c8"), outline=c8("#111"), width=4)
    for k in range(10):
        a = k * 2 * np.pi / 12 - 1
        x, y = 64 + 26 * np.cos(a), 64 + 26 * np.sin(a)
        t.d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=c8("#222"))
    t.rough = 0.25


def p_paper_stack(t):
    noise_fill(t, "#d8d0b8", 0.12)
    for y in range(16, 120, 8):
        t.d.line([(14, y), (14 + t.r.uniform(60, 100), y)], fill=c8("#7a7468"), width=1)
    t.rough = 0.9


def flat(c, rough=0.6, metal=0.0, amt=0.1):
    def f(t):
        noise_fill(t, c, amt)
        t.rough, t.metal = rough, metal
    return f


def p_mirror(t):
    w, h = t.w, t.h
    g = np.linspace(0.35, 0.6, w)[None, :].repeat(h, 0)
    rgb = np.dstack([g * 0.95, g, g]) * (0.9 + 0.1 * spectral(h, w, 1.4, t.seed)[..., None])
    sp = spectral(h, w, 0.6, t.seed + 1) > 0.88
    rgb[sp] = col("#2a2a28")
    t.img = Image.fromarray(to8(rgb)); t.d = ImageDraw.Draw(t.img)
    t.rough, t.metal = 0.08, 0.9


def p_emissive(t):
    t.d.rectangle([0, 0, t.w, t.h], fill=(255, 255, 250)); t.rough = 0.3; t.grime = 0


def p_switch(t):
    noise_fill(t, "#e0dcc8", 0.08)
    t.d.rectangle([24, 24, 104, 104], outline=c8("#888"), width=3)
    t.d.rectangle([52, 40, 76, 88], fill=c8("#cfcab4"), outline=c8("#666"))
    t.rough = 0.35


FURN_PAINT = {
    "wood_plain": p_wood_plain, "wardrobe_front": p_wardrobe, "bookcase_front": p_bookcase, "filing_front": p_filing,
    "med_cabinet_front": p_med_cabinet, "fridge_front": p_fridge, "elec_panel": p_elec_panel,
    "elevator_door": p_elevator_door, "cabin_wall": p_cabin_wall, "hose_cabinet": p_hose_cabinet,
    "partition": p_partition, "stage_curtain": p_stage_curtain, "cabin_panel": p_cabin_panel,
    "landing_panel": p_landing_panel, "door_steel": p_door_steel, "door_glazed": p_door_glazed,
    "door_padded": p_door_padded, "desk_front": p_desk_front, "radiator": p_radiator, "cinema_seats": p_cinema_seats,
    "bedside_front": p_bedside, "safe_front": p_safe, "stove_top": p_stove_top, "stove_front": p_stove_front,
    "steel": p_steel, "fuse_board": p_fuse_board, "vent_unit": p_vent_unit, "pump": p_pump, "mattress": p_mattress,
    "blanket": p_blanket, "linen_white": p_linen_white, "upholstery_brown": p_upholstery("#4a2a1c"),
    "upholstery_green": p_upholstery("#4e5e3e"), "typewriter_top": p_typewriter, "tv_front": p_tv,
    "piano_front": p_piano, "book_spines": p_book_spines, "binders": p_binders, "linen_stack": p_linen_stack,
    "crates": p_crates, "sacks": p_sacks, "tools_board": p_tools_board, "screen_fabric": p_screen_fabric,
    "lift_machine": p_lift_machine, "clock_face": p_clock_face, "dish_rack": p_dish_rack,
    "shelf_goods": p_shelf_goods, "lab_equipment": p_lab_equipment, "med_boxes": p_med_boxes, "carpet_rug": p_carpet,
    "runner": p_runner, "floor_indicator": p_floor_indicator, "exam_couch": p_exam_couch,
    "drawer_front": p_drawer_front, "fluo_diffuser": p_fluo, "telephone": p_telephone, "paper_stack": p_paper_stack,
    "pillow": flat("#dcd8cc", 0.9), "metal_white": flat("#e6e4dc", 0.35, 0.1), "metal_cream": flat("#d8ceb0", 0.4, 0.1),
    "metal_green": flat("#7d8a7c", 0.45, 0.3), "metal_grey": flat("#6c6e6a", 0.45, 0.5),
    "black_plastic": flat("#1e1c1a", 0.3), "chrome": flat("#c8ccce", 0.15, 1.0, 0.05),
    "porcelain": flat("#ecebe4", 0.12, 0, 0.05), "mirror": p_mirror, "lamp_shade": flat("#c8a86a", 0.85),
    "plafond": flat("#e8e4d6", 0.2), "rubber_black": flat("#22201e", 0.85), "wood_dark": p_wood_dark,
    "wood_light": p_wood_light, "leaf_green": flat("#3e5a2a", 0.7, 0, 0.3), "soil": flat("#3a2a1e", 0.95, 0, 0.3),
    "red_paint": flat("#a82a20", 0.45), "concrete": flat("#8f8b84", 0.9, 0, 0.25), "cardboard": flat("#a68a5e", 0.9),
    "aluminium": flat("#b0b2b0", 0.35, 0.9), "rust": flat("#7a3f1e", 0.9, 0.2, 0.35),
    "fabric_curtain": flat("#6a5a3a", 0.9, 0, 0.2), "velvet_red": flat("#7a1a1c", 0.9, 0, 0.2),
    "emissive_white": p_emissive, "bulb_off": flat("#8a8a80", 0.3), "switch": p_switch,
    "bucket_blue": flat("#3a5a8a", 0.4, 0.3), "enamel_pot": flat("#e8e6dc", 0.2, 0.05), "key_metal": flat("#c8b070", 0.3, 1.0),
}


def build_furniture_atlas(out, seed=500):
    W, H = A.FURN_W, A.FURN_H
    rgb = np.zeros((H, W, 3))
    rough = np.full((H, W), 0.6)
    metal = np.zeros((H, W))
    hgt = np.full((H, W), 0.5)
    grime_mask = np.zeros((H, W))
    for i, (name, w, h) in enumerate(A.FURN):
        x0, y0, x1, y1 = A.FURN_BOX[name]
        t = Tile(w, h, seed + i * 17)
        FURN_PAINT[name](t)
        a = np.asarray(t.img.convert("RGB"), np.float32) / 255.0
        lum = a.mean(-1)
        hh = np.asarray(t.hm, np.float32) / 255.0 * 0.6 + lum * 0.4
        rgb[y0:y1, x0:x1] = a
        hgt[y0:y1, x0:x1] = hh
        r = t.rough if np.ndim(t.rough) else np.full((h, w), t.rough)
        rough[y0:y1, x0:x1] = r
        metal[y0:y1, x0:x1] = t.metal
        grime_mask[y0:y1, x0:x1] = t.grime
    # global ageing: grime, dust and wear (avoids the clean, uniform look)
    g = spectral(H, W, 1.8, seed + 1)
    dust = smooth(0.55, 0.9, spectral(H, W, 2.2, seed + 2))
    rgb = rgb * (1 - 0.12 * g[..., None] * grime_mask[..., None])
    rgb = rgb * (1 - 0.15 * dust[..., None] * grime_mask[..., None]) + col("#8a8476") * 0.15 * dust[..., None] * grime_mask[..., None]
    rough = np.clip(rough + 0.15 * dust * grime_mask, 0, 1)
    save_set(out, "T_Atlas_Furniture", np.clip(rgb, 0, 1), rough, ao=cavity_ao(hgt, 3, 1.5), height=hgt,
             nstrength=4.0, metal=metal)


# ------------------------------------------------------------------- decals (RGBA)
def rgba_tile(w, h, seed):
    t = Tile(w, h, seed, "RGBA", (0, 0, 0, 0))
    return t


def poster(t, bg, title, sub, motif):
    w, h = t.w, t.h
    t.d.rectangle([0, 0, w, h], fill=c8(bg, 255))
    t.d.rectangle([6, 6, w - 6, h - 6], outline=c8("#2a2a2a", 255), width=2)
    if motif == "sun":
        t.d.ellipse([w / 2 - 70, 70, w / 2 + 70, 210], fill=c8("#e8a020", 255))
        for k in range(12):
            a = k * np.pi / 6
            t.d.line([(w / 2 + 80 * np.cos(a), 140 + 80 * np.sin(a)), (w / 2 + 110 * np.cos(a), 140 + 110 * np.sin(a))],
                     fill=c8("#e8a020", 255), width=6)
    elif motif == "hands":
        t.d.ellipse([60, 90, 196, 230], fill=c8("#e8c8a0", 255))
        for k in range(12):
            t.d.ellipse([70 + k * 10, 80 + (k % 3) * 20, 90 + k * 10, 100 + (k % 3) * 20], fill=c8("#9ac8e8", 255))
    elif motif == "cross":
        t.d.rectangle([w / 2 - 20, 80, w / 2 + 20, 220], fill=c8("#c02a20", 255))
        t.d.rectangle([w / 2 - 70, 130, w / 2 + 70, 170], fill=c8("#c02a20", 255))
    elif motif == "cig":
        t.d.rectangle([40, 140, 216, 168], fill=c8("#e8e4d8", 255))
        t.d.rectangle([180, 140, 216, 168], fill=c8("#c87a3a", 255))
        t.d.line([(30, 110), (226, 200)], fill=c8("#c02a20", 255), width=14)
    elif motif == "runner":
        t.d.ellipse([110, 70, 146, 106], fill=c8("#2a2a2a", 255))
        t.d.line([(128, 106), (118, 180), (90, 230)], fill=c8("#2a2a2a", 255), width=12)
        t.d.line([(118, 180), (150, 230)], fill=c8("#2a2a2a", 255), width=12)
        t.d.line([(90, 130), (160, 140)], fill=c8("#2a2a2a", 255), width=10)
    elif motif == "food":
        t.d.ellipse([50, 100, 206, 220], fill=c8("#f0ece0", 255), outline=c8("#888", 255), width=3)
        t.d.ellipse([90, 130, 166, 190], fill=c8("#c8a050", 255))
    yy = 252
    for line in title:
        txt(t, (w / 2, yy), line, 24, c8("#9a1a12", 255), "Black"); yy += 28
    for line in sub:
        txt(t, (w / 2, yy + 6), line, 13, c8("#222", 255), "Regular"); yy += 17


def text_sheet(t, bg, title, lines, tsz=20, lsz=11):
    w, h = t.w, t.h
    t.d.rectangle([0, 0, w, h], fill=c8(bg, 255), outline=c8("#555", 255), width=2)
    txt(t, (w / 2, 22), title, tsz, c8("#1a1a1a", 255))
    y = 44
    for ln in lines:
        if ln == "~":
            for k in range(3):
                t.d.line([(14, y + k * 9), (w - 14 - t.r.uniform(0, 60), y + k * 9)], fill=c8("#777", 255), width=2)
            y += 30
        else:
            t.d.text((14, y), ln, font=font(lsz), fill=c8("#222", 255)); y += lsz + 5


def sign(t, bg, fg, text, size=26, sub=None):
    w, h = t.w, t.h
    t.d.rounded_rectangle([1, 1, w - 2, h - 2], 6, fill=c8(bg, 255), outline=c8(fg, 255), width=3)
    if sub:
        txt(t, (w / 2, h * 0.38), text, size, c8(fg, 255))
        txt(t, (w / 2, h * 0.74), sub, int(size * 0.55), c8(fg, 255), "Regular")
    else:
        txt(t, (w / 2, h / 2), text, size, c8(fg, 255))


def arrow_sign(t, text, right=True):
    w, h = t.w, t.h
    t.d.rectangle([0, 0, w, h], fill=c8("#e8e2cc", 255), outline=c8("#2a3a5a", 255), width=3)
    if right:
        t.d.polygon([(w - 40, 14), (w - 10, h / 2), (w - 40, h - 14)], fill=c8("#2a3a5a", 255))
        txt(t, ((w - 40) / 2, h / 2), text, 18, c8("#2a3a5a", 255))
    else:
        t.d.polygon([(40, 14), (10, h / 2), (40, h - 14)], fill=c8("#2a3a5a", 255))
        txt(t, ((w + 40) / 2, h / 2), text, 18, c8("#2a3a5a", 255))


def alpha_noise_fill(t, c, a0, a1, beta=1.4):
    n = spectral(t.h, t.w, beta, t.seed)
    rgb = col(c)[None, None, :] * (0.9 + 0.2 * n[..., None])
    al = a0 + (a1 - a0) * n
    t.img = Image.fromarray(np.dstack([to8(rgb), to8(al)]), "RGBA"); t.d = ImageDraw.Draw(t.img)


def d_tulle(t):
    w, h = t.w, t.h
    x = np.arange(w)[None, :].repeat(h, 0)
    y = np.arange(h)[:, None].repeat(w, 1)
    fold = (np.sin(x / w * 2 * np.pi * 6) * 0.5 + 0.5)
    mesh = ((x % 6 < 1) | (y % 6 < 1)).astype(float)
    pattern = ((((x // 24) + (y // 24)) % 2 == 0) & (((x % 24 - 12) ** 2 + (y % 24 - 12) ** 2) < 30)).astype(float)
    al = np.clip(0.18 + 0.25 * mesh + 0.35 * pattern + 0.1 * fold, 0, 0.85)
    yel = smooth(0.0, 1.0, y / h) * 0.15
    rgb = np.dstack([np.full((h, w), .93), np.full((h, w), .91), np.full((h, w), .84)]) * (1 - yel[..., None])
    rgb *= (0.85 + 0.15 * fold[..., None])
    t.img = Image.fromarray(np.dstack([to8(rgb), to8(al)]), "RGBA"); t.d = ImageDraw.Draw(t.img)


def d_curtain(t):
    w, h = t.w, t.h
    fold = (np.sin(np.arange(w) / w * 2 * np.pi * 4) * 0.5 + 0.5)[None, :].repeat(h, 0)
    rgb = lerp(col("#4a3e22"), col("#7a6a3e"), fold) * (0.85 + 0.2 * spectral(h, w, 1.5, t.seed)[..., None])
    for y in range(40, h, 60):
        rgb[y:y + 4] *= 0.8
    t.img = Image.fromarray(np.dstack([to8(rgb), np.full((h, w), 255, np.uint8)]), "RGBA"); t.d = ImageDraw.Draw(t.img)


def d_plant(t, kind):
    w, h = t.w, t.h
    for k in range(26 if kind == 1 else 14):
        a = t.r.uniform(-2.6, -0.5)
        L = t.r.uniform(60, 120)
        x0, y0 = w / 2 + t.r.uniform(-10, 10), h - 10
        x1, y1 = x0 + np.cos(a) * L * 1.2, y0 + np.sin(a) * L * 1.6
        cc = c8(["#2e4a22", "#3e5a2a", "#4e6a32", "#5a6a2a"][t.r.integers(4)], 255)
        if kind == 1:
            t.d.polygon([(x0, y0), ((x0 + x1) / 2 - 14, (y0 + y1) / 2), (x1, y1), ((x0 + x1) / 2 + 14, (y0 + y1) / 2)],
                        fill=cc)
        else:
            t.d.line([(x0, y0), (x1, y1)], fill=c8("#3a4a22", 255), width=3)
            t.d.ellipse([x1 - 22, y1 - 14, x1 + 22, y1 + 14], fill=cc)
    if t.r.random() < 2:
        for k in range(4):
            x, y = t.r.uniform(40, 216), t.r.uniform(60, 200)
            t.d.ellipse([x - 8, y - 5, x + 8, y + 5], fill=c8("#8a7a3a", 255))   # dry leaves


def d_chair_legs(t, tube):
    w, h = t.w, t.h
    c = c8("#2a2a2a" if tube else "#4a2e1a", 255)
    wd = 7 if tube else 14
    t.d.line([(20, 0), (14, h)], fill=c, width=wd)
    t.d.line([(w - 20, 0), (w - 14, h)], fill=c, width=wd)
    t.d.line([(18, h * 0.55), (w - 18, h * 0.55)], fill=c, width=wd - 2)
    if tube:
        t.d.line([(14, h - 4), (w - 14, h - 4)], fill=c, width=wd)


def d_bed_head(t):
    w, h = t.w, t.h
    c = c8("#d8d2c2", 255)
    t.d.rectangle([6, 6, w - 6, h - 6], outline=c, width=12)
    for x in range(40, w - 20, 34):
        t.d.line([(x, 10), (x, h - 10)], fill=c, width=7)


def d_railing(t):
    w, h = t.w, t.h
    for x in range(0, w, 32):
        t.d.rectangle([x + 12, 0, x + 20, h], fill=c8("#3a3a36", 255))
    t.d.rectangle([0, h - 14, w, h], fill=c8("#3a3a36", 255))
    t.d.rectangle([0, 0, w, 10], fill=c8("#3a3a36", 255))


def d_wheel(t):
    t.d.ellipse([4, 4, 124, 124], outline=c8("#222", 255), width=10)
    t.d.ellipse([16, 16, 112, 112], outline=c8("#9a9a96", 255), width=4)
    for k in range(12):
        a = k * np.pi / 6
        t.d.line([(64, 64), (64 + 48 * np.cos(a), 64 + 48 * np.sin(a))], fill=c8("#9a9a96", 255), width=2)


def d_papers(t, n):
    for k in range(n):
        cx, cy = t.r.uniform(60, 196, 2)
        a = t.r.uniform(0, np.pi)
        ww, hh = 70, 98
        pts = [(-ww / 2, -hh / 2), (ww / 2, -hh / 2), (ww / 2, hh / 2), (-ww / 2, hh / 2)]
        rot = [(cx + x * np.cos(a) - y * np.sin(a), cy + x * np.sin(a) + y * np.cos(a)) for x, y in pts]
        t.d.polygon(rot, fill=c8(["#e2dcc6", "#d8cfae", "#e8e2d2"][k % 3], 255), outline=c8("#a89e86", 255))
        for j in range(8):
            f = -0.38 + j * 0.09
            p0 = (cx + (-ww * 0.38) * np.cos(a) - (hh * f) * np.sin(a), cy + (-ww * 0.38) * np.sin(a) + (hh * f) * np.cos(a))
            p1 = (cx + (ww * 0.3) * np.cos(a) - (hh * f) * np.sin(a), cy + (ww * 0.3) * np.sin(a) + (hh * f) * np.cos(a))
            t.d.line([p0, p1], fill=c8("#6a6458", 255), width=1)


def d_stain(t, c, amax):
    m = blobs(t.h, t.w, 3, t.seed, 30, 70)
    ring = np.clip(m * 4, 0, 1) - np.clip(m * 4 - 0.8, 0, 1)
    al = np.clip(m * amax + ring * 0.25, 0, 1)
    edge = smooth(0.0, 0.25, np.minimum.reduce([np.arange(t.w)[None, :].repeat(t.h, 0) / t.w,
                                                1 - np.arange(t.w)[None, :].repeat(t.h, 0) / t.w,
                                                np.arange(t.h)[:, None].repeat(t.w, 1) / t.h,
                                                1 - np.arange(t.h)[:, None].repeat(t.w, 1) / t.h]))
    rgb = col(c)[None, None, :] * np.ones((t.h, t.w, 1))
    t.img = Image.fromarray(np.dstack([to8(rgb), to8(al * edge)]), "RGBA"); t.d = ImageDraw.Draw(t.img)


def d_evac(t):
    w, h = t.w, t.h
    t.d.rectangle([0, 0, w, h], fill=c8("#ece8da", 255), outline=c8("#2a7a3a", 255), width=4)
    txt(t, (w / 2, 18), "ПЛАН ЭВАКУАЦИИ", 16, c8("#2a7a3a", 255))
    t.d.rectangle([20, 60, w - 20, 170], outline=c8("#222", 255), width=3)
    t.d.rectangle([20, 105, w - 20, 125], fill=c8("#d8d4c6", 255))
    for x in range(20, w - 20, 34):
        t.d.line([(x, 60), (x, 105)], fill=c8("#222", 255)); t.d.line([(x, 125), (x, 170)], fill=c8("#222", 255))
    t.d.line([(200, 115), (40, 115)], fill=c8("#2a9a3a", 255), width=4)
    t.d.polygon([(40, 108), (26, 115), (40, 122)], fill=c8("#2a9a3a", 255))
    t.d.ellipse([196, 108, 210, 122], fill=c8("#c02a20", 255))
    txt(t, (w / 2, 200), "Вы находитесь здесь  ●", 13, c8("#c02a20", 255), "Regular")
    txt(t, (w / 2, 228), "При пожаре звонить 01", 14, c8("#222", 255))


def d_notice(t):
    w, h = t.w, t.h
    grain_fill(t, "#7a5a3a", "#9a7a52")
    t.img = t.img.convert("RGBA"); t.d = ImageDraw.Draw(t.img)
    t.d.rectangle([12, 12, w - 12, h - 12], fill=c8("#9a8a6a", 255))
    txt(t, (w / 2, 34), "ДОСКА ОБЪЯВЛЕНИЙ", 22, c8("#2a1a10", 255))
    for k in range(6):
        x0, y0 = 24 + (k % 3) * 160 + t.r.uniform(-6, 6), 60 + (k // 3) * 150 + t.r.uniform(-6, 6)
        t.d.rectangle([x0, y0, x0 + 140, y0 + 130], fill=c8(["#e8e2cc", "#e2d8b8", "#d8e0e2"][k % 3], 255),
                      outline=c8("#888", 255))
        t.d.ellipse([x0 + 64, y0 - 4, x0 + 76, y0 + 8], fill=c8("#b02a1a", 255))
        txt(t, (x0 + 70, y0 + 20), ["ПРИКАЗ", "ГРАФИК", "ВНИМАНИЕ!", "СОБРАНИЕ", "ПАМЯТКА", "МЕНЮ"][k], 13,
            c8("#222", 255))
        for j in range(7):
            t.d.line([(x0 + 10, y0 + 40 + j * 12), (x0 + 130 - t.r.uniform(0, 40), y0 + 40 + j * 12)],
                     fill=c8("#666", 255), width=1)


def d_wall_carpet(t):
    w, h = t.w, t.h
    t.d.rectangle([0, 0, w, h], fill=c8("#7a1e1a", 255))
    t.d.rectangle([12, 12, w - 12, h - 12], outline=c8("#1e2a4a", 255), width=22)
    t.d.rectangle([40, 40, w - 40, h - 40], outline=c8("#d8b870", 255), width=6)
    for k in range(6):
        r = 150 - k * 24
        t.d.polygon([(w / 2, h / 2 - r * 0.8), (w / 2 + r, h / 2), (w / 2, h / 2 + r * 0.8), (w / 2 - r, h / 2)],
                    outline=c8(["#d8b870", "#1e2a4a", "#e8e0c8", "#3a5a3a", "#d8b870", "#e8e0c8"][k], 255), width=8)
    for x in range(0, w, 8):
        t.d.line([(x, 0), (x, 6)], fill=c8("#d8c8a0", 255), width=2)
        t.d.line([(x, h - 6), (x, h)], fill=c8("#d8c8a0", 255), width=2)


def d_painting(t, k):
    w, h = t.w, t.h
    t.d.rectangle([0, 0, w, h], fill=c8("#6a4a22", 255))
    sky = "#9ab4c8" if k == 1 else "#c8b48a"
    t.d.rectangle([14, 14, w - 14, h - 14], fill=c8(sky, 255))
    if k == 1:   # birches by a lake
        t.d.rectangle([14, h * 0.62, w - 14, h - 14], fill=c8("#5a7a4a", 255))
        t.d.ellipse([80, h * 0.6, 220, h * 0.75], fill=c8("#7a9ab0", 255))
        for x in (40, 60, 190):
            t.d.rectangle([x, 30, x + 6, h * 0.7], fill=c8("#e8e4d8", 255))
            t.d.ellipse([x - 26, 20, x + 30, 80], fill=c8("#4a6a32", 255))
    else:        # sea and mountains (Crimea)
        t.d.polygon([(14, h * 0.6), (90, 50), (160, h * 0.6)], fill=c8("#6a6a5a", 255))
        t.d.rectangle([14, h * 0.6, w - 14, h - 14], fill=c8("#3a6a8a", 255))
        t.d.ellipse([170, 30, 210, 70], fill=c8("#e8c870", 255))


def d_frame_photo(t):
    t.d.rectangle([0, 0, t.w, t.h], fill=c8("#3a2a1a", 255))
    t.d.rectangle([12, 12, t.w - 12, t.h - 12], fill=c8("#b8b2a0", 255))
    t.d.ellipse([40, 30, 88, 90], fill=c8("#5a564c", 255))
    t.d.rectangle([30, 90, 98, 148], fill=c8("#3a3832", 255))


def d_calendar(t):
    w, h = t.w, t.h
    t.d.rectangle([0, 0, w, h], fill=c8("#e8e2cc", 255), outline=c8("#888", 255))
    t.d.rectangle([0, 0, w, 50], fill=c8("#9a2a1a", 255))
    txt(t, (w / 2, 25), "1991", 26, c8("#f0e8d0", 255))
    txt(t, (w / 2, 66), "АВГУСТ", 13, c8("#222", 255))
    for i in range(31):
        x, y = 14 + (i % 7) * 15, 86 + (i // 7) * 18
        t.d.text((x, y), str(i + 1), font=font(9), fill=c8("#c02a20" if i % 7 == 6 else "#333", 255))
    t.d.line([(10, 90), (110, 170)], fill=c8("#2a2aa0", 255), width=2)


def build_decal_atlas(out, seed=900):
    S2 = A.DECAL_SIZE
    canvas = Image.new("RGBA", (S2, S2), (0, 0, 0, 0))
    P = {
        "tulle": d_tulle, "curtain_heavy": d_curtain,
        "poster_1": lambda t: poster(t, "#e8dfc4", ["ЗДОРОВЬЕ", "НАРОДА —"], ["богатство страны"], "sun"),
        "poster_2": lambda t: poster(t, "#e2e6da", ["МОЙТЕ РУКИ", "ПЕРЕД ЕДОЙ!"], ["Санпросвет, 1976"], "hands"),
        "poster_3": lambda t: poster(t, "#e8e2d2", ["КУРИТЬ —", "ЗДОРОВЬЮ ВРЕДИТЬ"], ["Минздрав СССР"], "cig"),
        "poster_4": lambda t: poster(t, "#dde4e8", ["ГРИПП", "ОПАСЕН!"], ["Берегите себя и близких"], "cross"),
        "poster_5": lambda t: poster(t, "#e4e8d8", ["ФИЗКУЛЬТУРА —", "ЗАЛОГ ЗДОРОВЬЯ"], ["Утренняя гимнастика 7:30"], "runner"),
        "poster_6": lambda t: poster(t, "#efe6d0", ["ДИЕТИЧЕСКОЕ", "ПИТАНИЕ"], ["Стол № 5 · Стол № 9"], "food"),
        "eye_chart": lambda t: text_sheet(t, "#f0ece0", "Ш Б", ["  М Н К", "   Ы М Б Ш", "   Б Ы Н К М", "    И Н Ш М К",
                                                               "    Н К И Б М Ш", "~", "~", "~"], 40, 20),
        "anatomy": lambda t: (poster(t, "#efe8d8", ["СЕРДЕЧНО-", "СОСУДИСТАЯ"], ["система человека"], "cross")),
        "notice_board": d_notice,
        "wall_newspaper": lambda t: text_sheet(t, "#efe6cc", "САНБЮЛЛЕТЕНЬ", ["~", "~", "~", "~", "~", "~"], 26),
        "evac_plan": d_evac, "painting_1": lambda t: d_painting(t, 1), "painting_2": lambda t: d_painting(t, 2),
        "wall_carpet": d_wall_carpet, "calendar": d_calendar,
        "schedule": lambda t: text_sheet(t, "#e8e2cc", "РАСПОРЯДОК ДНЯ",
                                         ["7:00  Подъём", "7:30  Зарядка", "8:00  Завтрак", "9:00  Процедуры",
                                          "13:00 Обед", "14:00 Тихий час", "19:00 Ужин", "22:00 Отбой"], 18, 12),
        "menu_board": lambda t: text_sheet(t, "#2a3a2e", "МЕНЮ", ["Суп молочный", "Котлета паровая", "Пюре",
                                                                  "Кисель", "~"], 22, 13),
        "lift_rules": lambda t: text_sheet(t, "#e8e2cc", "ПРАВИЛА", ["Лифт служебный.", "Пользоваться только",
                                                                   "в сопровождении", "персонала по ключу.",
                                                                   "Детям до 14 лет", "без взрослых запрещено.",
                                                                   "~", "Ответственный: Петров А.И."], 20, 12),
        "plant_1": lambda t: d_plant(t, 1), "plant_2": lambda t: d_plant(t, 2),
        "chair_legs_wood": lambda t: d_chair_legs(t, False), "chair_legs_tube": lambda t: d_chair_legs(t, True),
        "bed_head_tube": d_bed_head, "railing": d_railing, "wheel": d_wheel,
        "papers_1": lambda t: d_papers(t, 3), "papers_2": lambda t: d_papers(t, 5),
        "stain_floor": lambda t: d_stain(t, "#4a3e2a", 0.5), "stain_wall": lambda t: d_stain(t, "#8a7448", 0.45),
        "soot": lambda t: d_stain(t, "#2a2622", 0.55), "dust_sheet": lambda t: alpha_noise_fill(t, "#8a8476", 0.0, 0.5),
        "vent_grille": lambda t: [t.d.rectangle([0, 0, 128, 128], fill=c8("#d8d4c6", 255))] + [
            t.d.rectangle([12, y, 116, y + 6], fill=c8("#2a2a28", 255)) for y in range(14, 116, 12)],
        "socket": lambda t: [t.d.ellipse([2, 2, 62, 62], fill=c8("#e0dcc8", 255), outline=c8("#888", 255)),
                             t.d.ellipse([18, 28, 26, 36], fill=c8("#111", 255)),
                             t.d.ellipse([38, 28, 46, 36], fill=c8("#111", 255))],
        "light_switch": lambda t: [t.d.rectangle([2, 2, 62, 94], fill=c8("#e0dcc8", 255), outline=c8("#888", 255)),
                                   t.d.rectangle([22, 24, 42, 72], fill=c8("#cfcab4", 255), outline=c8("#666", 255))],
        "fire_sign": lambda t: sign(t, "#c02a20", "#f0e8e0", "ОГНЕТУШИТЕЛЬ", 13),
        "exit_sign": lambda t: sign(t, "#2a8a3a", "#f0f0e0", "ВЫХОД", 40),
        "no_smoking": lambda t: [t.d.ellipse([4, 4, 124, 124], fill=c8("#f0ece0", 255), outline=c8("#c02a20", 255), width=10),
                                 t.d.rectangle([28, 56, 100, 72], fill=c8("#333", 255)),
                                 t.d.line([(24, 24), (104, 104)], fill=c8("#c02a20", 255), width=10)],
        "keep_out": lambda t: sign(t, "#f0e8d0", "#9a1a12", "ПОСТОРОННИМ", 24, "вход воспрещён"),
        "lift_sign": lambda t: sign(t, "#2a3a5a", "#e8e2cc", "ЛИФТ СЛУЖЕБНЫЙ", 24, "для персонала и больных"),
        "key_only": lambda t: sign(t, "#e8d040", "#1a1a1a", "ТОЛЬКО ПО КЛЮЧУ", 22, "ключ у дежурной медсестры"),
        "wc_m": lambda t: sign(t, "#2a3a5a", "#e8e2cc", "М", 56), "wc_f": lambda t: sign(t, "#7a2a3a", "#e8e2cc", "Ж", 56),
        "wc_access": lambda t: sign(t, "#2a4a8a", "#ffffff", "♿", 56),
        "silence": lambda t: sign(t, "#e8e2cc", "#2a3a5a", "ТИХО!", 30, "идёт приём"),
        "arrow_dining": lambda t: arrow_sign(t, "Столовая", False), "arrow_medical": lambda t: arrow_sign(t, "Мед. отделение"),
        "arrow_admin": lambda t: arrow_sign(t, "Администрация"), "arrow_reception": lambda t: arrow_sign(t, "Регистратура", False),
        "arrow_hall": lambda t: arrow_sign(t, "Клубный зал", False), "arrow_stairs": lambda t: arrow_sign(t, "Лестница"),
        "arrow_lift": lambda t: arrow_sign(t, "Лифт"),
        "roof_hatch": lambda t: sign(t, "#e8e2cc", "#1a1a1a", "ВЫХОД НА КРОВЛЮ", 18),
        "electro_warning": lambda t: [t.d.polygon([(64, 6), (6, 120), (122, 120)], fill=c8("#e8c82a", 255), outline=c8("#111", 255)),
                                      t.d.line([(70, 40), (56, 78), (72, 76), (58, 110)], fill=c8("#111", 255), width=6)],
        "dirt_strip": lambda t: alpha_noise_fill(t, "#3a342a", 0.0, 0.6, 1.0),
        "frame_photo": d_frame_photo,
    }
    rgba_img = np.zeros((S2, S2, 4), np.float32)
    for i, (name, w, h) in enumerate(A.DECAL):
        x0, y0, x1, y1 = A.DECAL_BOX[name]
        t = rgba_tile(w, h, seed + i * 13)
        P[name](t)
        canvas.paste(t.img, (x0, y0))
    a = np.asarray(canvas, np.float32) / 255.0
    rgb, al = a[..., :3], a[..., 3]
    # paper/plastic ageing: yellowing and grime only where opaque
    g = spectral(S2, S2, 1.8, seed + 1)
    rgb = rgb * (0.88 + 0.1 * g[..., None]) * np.array([1.0, 0.97, 0.9])[None, None, :]
    lum = rgb.mean(-1)
    save_set(out, "T_Atlas_Decals", np.clip(rgb, 0, 1), np.full((S2, S2), 0.75), alpha=al,
             height=lum * 0.3, nstrength=1.5)


# ------------------------------------------------------------------- door plates
def build_sign_atlas(out, plan, seed=1300):
    keys = A.sign_keys(plan)
    boxes = A.sign_boxes(keys)
    S2 = A.SIGN_SIZE
    canvas = Image.new("RGB", (S2, S2), (40, 40, 40))
    special = {
        "SPEC_lift_service": ("ЛИФТ", "служебный"), "SPEC_machine": ("Машинное", "помещение лифта"),
        "SPEC_stair1": ("Лестница", "№ 1"), "SPEC_stair2": ("Лестница", "№ 2"), "SPEC_stair3": ("Лестница", "№ 3"),
        "SPEC_shower_m": ("Душевая", "мужская"), "SPEC_shower_f": ("Душевая", "женская"),
    }
    r = np.random.default_rng(seed)
    for k in keys:
        x0, y0, x1, y1 = boxes[k]
        t = Tile(x1 - x0, y1 - y0, seed + hash(k) % 10000)
        if k in special:
            a, b = special[k]
            num = ""
        else:
            room = plan.rooms[k]
            num = room.num
            a = room.ru
            b = ""
        style = r.integers(3)
        bg, fg = [("#1f2f4f", "#e8e2c8"), ("#e6e0cc", "#1a1a1a"), ("#2a2a28", "#d8c070")][style]
        t.d.rectangle([0, 0, t.w, t.h], fill=c8(bg))
        t.d.rectangle([3, 3, t.w - 4, t.h - 4], outline=c8(fg), width=2)
        if num:
            txt(t, (40, t.h / 2), num, 30, c8(fg), "Black")
            t.d.line([(78, 10), (78, t.h - 10)], fill=c8(fg), width=2)
            words = a.split()
            lines, cur = [], ""
            for wd in words:
                tt = (cur + " " + wd).strip()
                if font(17, "Bold").getlength(tt) < 166:
                    cur = tt
                else:
                    lines.append(cur); cur = wd
            lines.append(cur)
            lines = lines[:3]
            sz = 17 if len(lines) < 3 else 14
            for i, ln in enumerate(lines):
                txt(t, (167, t.h / 2 + (i - (len(lines) - 1) / 2) * (sz + 3)), ln, sz, c8(fg))
        else:
            txt(t, (t.w / 2, t.h * 0.36), a, 24, c8(fg))
            txt(t, (t.w / 2, t.h * 0.72), b, 16, c8(fg), "Regular")
        im = np.asarray(t.img, np.float32) / 255.0
        n = spectral(t.h, t.w, 1.6, seed + x0 + y0)
        im = im * (0.85 + 0.2 * n[..., None])
        if r.random() < 0.25:   # sun-faded plate
            im = im * 0.75 + 0.25 * col("#b8b0a0")
        canvas.paste(Image.fromarray(to8(im)), (x0, y0))
    a = np.asarray(canvas, np.float32) / 255.0
    save_set(out, "T_Atlas_Signs", a, np.full((S2, S2), 0.35), height=a.mean(-1) * 0.2, nstrength=1.0)


def generate_atlases(out):
    from .plan import build_plan
    return [lambda: build_furniture_atlas(out), lambda: build_decal_atlas(out),
            lambda: build_sign_atlas(out, build_plan())]
