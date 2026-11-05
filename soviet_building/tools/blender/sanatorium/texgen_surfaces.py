"""Tileable interior surface textures (walls, floors, ceilings, wood, metal, glass).

Wall sets cover 3.0 m x 3.0 m: u along the wall, v = height above the floor of the room
(v=0 floor, v=1 ceiling at +3.0 m), so the skirting band, dado line and ceiling stains
land at the right height on every storey.
"""
import numpy as np
from .texcore import *

S = 1024


def zgrid(h=S, w=S, height=3.0):
    """Height in metres for every pixel row (row 0 = top)."""
    z = (1 - (np.arange(h) + 0.5) / h) * height
    return np.repeat(z[:, None], w, 1)


def paint_wall(name, out, dado, upper, seed, dado_top=1.5, line="#4f4a3f", skirting="#4a3328", gloss=0.42):
    h = w = S
    z = zgrid()
    n_lo = spectral(h, w, 2.2, seed)
    n_hi = spectral(h, w, 1.0, seed + 1)
    n_md = spectral(h, w, 1.6, seed + 2)
    base = np.zeros((h, w, 3))
    dado_c, up_c = col(dado), col(upper)
    lo_mask = z < dado_top
    # uneven, faded oil paint: brush streaks (vertical), patchy fading, older paint showing through
    streak = blur(spectral(h, w, 0.6, seed + 3), 1.2)
    streak = (streak - streak.mean()) * np.repeat(np.linspace(1, 1, w)[None, :], h, 0)
    fade = n_lo * 0.04 - 0.015
    dado_rgb = dado_c[None, None, :] * (1 + fade[..., None] + 0.05 * (streak[..., None] - 0.5) * 2)
    up_rgb = up_c[None, None, :] * (1 + 0.6 * fade[..., None] + 0.03 * (n_hi[..., None] - 0.5))
    base = np.where(lo_mask[..., None], dado_rgb, up_rgb)
    rough = np.where(lo_mask, gloss + 0.18 * n_md, 0.86 + 0.1 * n_hi)
    height = n_lo * 0.6 + n_hi * 0.08
    # dado line
    ln = np.abs(z - dado_top) < 0.008
    base[ln] = col(line)
    height[ln] += 0.3
    # skirting band (painted)
    sk = z < 0.10
    base[sk] = col(skirting) * (0.9 + 0.2 * n_hi[sk, None])
    rough[sk] = 0.45
    height[sk] += 1.0
    edge = np.abs(z - 0.10) < 0.006
    base[edge] *= 0.6
    # paint chips on the dado, more near the bottom and at 0.7-1.0 m (chair backs, trolleys)
    zone = smooth(1.2, 0.2, z) * 0.6 + np.exp(-((z - 0.85) / 0.12) ** 2) * 0.5
    chips = spectral(h, w, 1.3, seed + 5, lo=3)
    chip_m = (chips > 0.985 - 0.02 * zone) & lo_mask & ~sk
    base[chip_m] = base[chip_m] * 0.8 + col("#c8c2b4") * 0.2
    rough[chip_m] = 0.92
    height[chip_m] -= 0.1
    # scuffs and dirt smudges
    sc = scratches(h, w, 20, seed + 6, length=(0.01, 0.04), width=1, angle=0.0)
    sc *= (z < 1.0) & (z > 0.12)
    base *= (1 - 0.08 * sc[..., None])
    dirt = blur(spectral(h, w, 1.8, seed + 7), 2) * smooth(0.9, 0.0, z)
    base *= (1 - 0.04 * dirt[..., None])
    # upper part: hairline cracks, water stains under the ceiling, dust darkening at the top
    top = smooth(2.75, 3.0, z)
    base *= (1 - 0.03 * top[..., None])
    ao = np.clip(cavity_ao(height, 4, 2.0) * (1 - 0.15 * smooth(0.25, 0.0, z)) * (1 - 0.1 * top), 0, 1)
    save_set(out, name, np.clip(base, 0, 1), np.clip(rough, 0.05, 1), ao=ao, height=height, nstrength=3.0)


def tile_wall(name, out, seed, tile_top=1.5, upper="#d9dcd2"):
    h = w = S
    z = zgrid()
    x = np.repeat(((np.arange(w) + 0.5) / w * 3.0)[None, :], h, 0)
    n1, n2 = spectral(h, w, 1.0, seed), spectral(h, w, 2.0, seed + 1)
    t = 0.15
    gx, gy = (x % t), ((z - 0.10) % t)
    grout = (np.minimum(gx, t - gx) < 0.0025) | (np.minimum(gy, t - gy) < 0.0025)
    ti, tj = np.floor(x / t).astype(int), np.floor((z - 0.10) / t).astype(int)
    r = np.random.default_rng(seed)
    var = r.uniform(0.94, 1.03, (40, 40))
    tv = var[tj % 40, ti % 40]
    base = col("#e6e6dc")[None, None, :] * tv[..., None] * (1 + 0.03 * (n1[..., None] - 0.5))
    rough = 0.18 + 0.12 * n1
    height = np.ones((h, w)) * 0.5
    # tile bevel
    bev = smooth(0.0, 0.012, np.minimum(np.minimum(gx, t - gx), np.minimum(gy, t - gy)))
    height = bev * 0.8
    base[grout] = col("#8f8a7c") * (0.8 + 0.3 * n2[grout, None])
    rough[grout] = 0.9
    # a few replaced tiles in a slightly different white, some cracked / missing
    odd = r.random((40, 40))
    om = (odd[tj % 40, ti % 40] > 0.965)
    base[om] *= col("#efe9d2") / col("#e6e6dc")
    up = z >= tile_top
    up_rgb = col(upper)[None, None, :] * (1 + 0.08 * (n2[..., None] - 0.5))
    base = np.where(up[..., None], up_rgb, base)
    rough = np.where(up, 0.85 + 0.1 * n1, rough)
    height = np.where(up, n2 * 0.4, height)
    trim = (z >= tile_top - 0.03) & (z < tile_top)
    base[trim] = col("#d3d3c8")
    height[trim] = 1.0
    sk = z < 0.10
    base[sk] = col("#6b5a4a") * (0.9 + 0.2 * n1[sk, None])
    height[sk] = 0.9
    dirt = blur(spectral(h, w, 1.8, seed + 4), 2) * smooth(1.0, 0.0, z)
    base *= (1 - 0.04 * dirt[..., None])
    save_set(out, name, np.clip(base, 0, 1), np.clip(rough, 0.05, 1), height=height, nstrength=5.0)


def wallpaper(name, out, seed, ground, ink, accent, style):
    h = w = S
    z = zgrid()
    n1, n2 = spectral(h, w, 1.0, seed), spectral(h, w, 2.2, seed + 1)
    im = Image.new("RGB", (w, h), tuple(int(c * 255) for c in col(ground)))
    d = ImageDraw.Draw(im)
    pxm = w / 3.0
    ink8 = tuple(int(c * 255) for c in col(ink))
    acc8 = tuple(int(c * 255) for c in col(accent))
    r = np.random.default_rng(seed)
    if style == "floral":
        for i in range(12):                     # vertical stripes every 0.25 m
            x = (i + 0.5) * w / 12
            d.line([(x, 0), (x, h)], fill=acc8, width=2)
            for j in range(13):
                y = j * h / 12 + (i % 2) * h / 24
                for ox in (-w, 0, w):
                    cx = x + w / 24 + ox
                    for k in range(5):
                        a = k * 2 * np.pi / 5
                        d.ellipse([cx + 7 * np.cos(a) - 5, y + 7 * np.sin(a) - 5, cx + 7 * np.cos(a) + 5,
                                   y + 7 * np.sin(a) + 5], fill=ink8)
                    d.ellipse([cx - 3, y - 3, cx + 3, y + 3], fill=acc8)
                    d.line([(cx, y + 9), (cx - 6, y + 22)], fill=acc8, width=2)
                    d.ellipse([cx - 12, y + 14, cx - 4, y + 22], fill=acc8)
    else:
        for i in range(12):
            x0 = i * w / 12
            d.rectangle([x0 + 4, 0, x0 + 8, h], fill=acc8)
            for j in range(25):
                y = j * h / 24
                cx = x0 + w / 24
                d.polygon([(cx, y - 14), (cx + 14, y), (cx, y + 14), (cx - 14, y)], outline=ink8)
                d.polygon([(cx, y - 6), (cx + 6, y), (cx, y + 6), (cx - 6, y)], fill=ink8)
    pat = np.asarray(im.filter(ImageFilter.GaussianBlur(0.7)), np.float32) / 255.0
    pat = pat * (1 + 0.08 * (n1[..., None] - 0.5))
    # fading: uneven sun bleaching
    fade = smooth(0.3, 0.9, spectral(h, w, 2.4, seed + 2))
    pat = pat * (1 - 0.08 * fade[..., None]) + col("#e8dfc8")[None, None, :] * 0.08 * fade[..., None]
    height = n2 * 0.3 + n1 * 0.05
    # roll seams every 0.5 m, a couple of lifted seams
    xs = (np.arange(w) + 0.5) / w * 3.0
    seam = np.abs(((xs + 0.25) % 0.5) - 0.25) < 0.0015
    pat[:, seam] *= 0.94
    height[:, seam] += 0.15
    dirt = blur(spectral(h, w, 1.8, seed + 5), 2) * smooth(0.8, 0.1, z)
    pat *= (1 - 0.03 * dirt[..., None])
    sk = z < 0.10
    pat[sk] = col("#4a3328") * (0.9 + 0.2 * n1[sk, None])
    height[sk] = 1.0
    pat *= (1 - 0.03 * smooth(2.8, 3.0, z)[..., None])
    rough = np.where(sk, 0.45, 0.8 + 0.1 * n1)
    save_set(out, name, np.clip(pat, 0, 1), rough, height=height, nstrength=3.0)


def plaster(name, out, seed, tint="#d6d1c4", tile_m=2.0, ceiling=False):
    h = w = S
    n1, n2, n3 = spectral(h, w, 2.4, seed), spectral(h, w, 1.2, seed + 1), spectral(h, w, 1.7, seed + 2)
    base = col(tint)[None, None, :] * (1 + 0.04 * (n1[..., None] - 0.5) + 0.02 * (n2[..., None] - 0.5))
    height = n1 * 0.8 + n2 * 0.15
    if ceiling:
        # brush marks of whitewash, flaking spots, soot near lamp positions is handled by AO
        streak = blur(spectral(h, w, 0.5, seed + 5), 1.5)
        base *= (1 + 0.04 * (streak[..., None] - 0.5))
    rough = 0.88 + 0.1 * n2
    save_set(out, name, np.clip(base, 0, 1), rough, height=height, nstrength=2.5)


def concrete(name, out, seed):
    h = w = S
    n1, n2, n3 = spectral(h, w, 2.2, seed), spectral(h, w, 1.0, seed + 1), spectral(h, w, 1.6, seed + 2)
    base = col("#8f8b84")[None, None, :] * (0.85 + 0.25 * n1[..., None] + 0.05 * (n2[..., None] - 0.5))
    pores = spectral(h, w, 0.4, seed + 3) > 0.82
    base[pores] *= 0.7
    height = n1 * 0.6 + n2 * 0.1 - pores * 0.4
    xs = (np.arange(w) + 0.5) / w
    joint = np.abs(((xs + 0.25) % 0.5) - 0.25) < 0.002     # formwork board joints every 1 m
    base[:, joint] *= 0.8
    height[:, joint] -= 0.3
    st = blobs(h, w, 4, seed + 4, 40, 120)
    base = mix_col(np.clip(st * 0.08, 0, 0.08), base, col("#5c5650"))
    save_set(out, name, np.clip(base, 0, 1), 0.85 + 0.12 * n3, height=height, nstrength=3.0)


def linoleum(name, out, seed, style):
    h = w = S
    n1, n2, n3 = spectral(h, w, 1.4, seed), spectral(h, w, 2.4, seed + 1), spectral(h, w, 0.9, seed + 2)
    x = np.repeat(((np.arange(w) + 0.5) / w * 2.0)[None, :], h, 0)
    y = np.repeat(((np.arange(h) + 0.5) / h * 2.0)[:, None], w, 1)
    if style == "brown":
        marb = smooth(0.35, 0.75, blur(spectral(h, w, 1.7, seed + 3), 1))
        base = lerp(col("#6e3524"), col("#8c4a33"), marb)
        base = base * (1 + 0.06 * (n3[..., None] - 0.5))
    else:   # parquet-print linoleum (herringbone of 0.42 x 0.07 m staves)
        sw, sl = 0.07, 0.42
        u = x + y
        vv = x - y
        a = np.floor(u / sl)
        b = np.floor(vv / sw)
        sel = ((a + b) % 2 == 0)
        ii = np.where(sel, np.floor(u / sl) * 13 + np.floor(vv / sw), np.floor(vv / sl) * 7 + np.floor(u / sw))
        r = np.random.default_rng(seed)
        lut = r.uniform(0.0, 1.0, 4096)
        tone = lut[(ii.astype(int)) % 4096]
        base = lerp(col("#7a5434"), col("#a3774b"), tone)
        grain = spectral(h, w, 0.9, seed + 4)
        base *= (0.92 + 0.12 * grain[..., None])
        lines = (np.abs((u % sl)) < 0.004) | (np.abs((vv % sw)) < 0.003)
        base[lines] *= 0.7
        base = base * 0.85 + col("#8c6a48") * 0.15    # print fading
    height = n2 * 0.2
    # seam between 2 m rolls (at the tile edge) slightly lifted, dirt line
    seam = (np.abs(x - 0.003) < 0.004) | (np.abs(x - 1.997) < 0.004)
    base[seam] *= 0.85
    height[seam] += 0.2
    # wear: lighter, matte paths; scratches; dirt; cigarette burns are not appropriate here
    wear = smooth(0.55, 0.85, blur(spectral(h, w, 2.6, seed + 5), 3))
    base = base * (1 - 0.08 * wear[..., None]) + col("#9a8a78")[None, None, :] * 0.08 * wear[..., None]
    rough = 0.35 + 0.15 * wear + 0.1 * n1
    sc = scratches(h, w, 40, seed + 6, length=(0.01, 0.04), width=1)
    base *= (1 - 0.06 * sc[..., None])
    height -= sc * 0.1
    save_set(out, name, np.clip(base, 0, 1), np.clip(rough, 0, 1), height=height, nstrength=2.0)


def tile_floor(name, out, seed):
    h = w = S
    n1, n2 = spectral(h, w, 1.0, seed), spectral(h, w, 2.0, seed + 1)
    x = np.repeat(((np.arange(w) + 0.5) / w * 2.0)[None, :], h, 0)
    y = np.repeat(((np.arange(h) + 0.5) / h * 2.0)[:, None], w, 1)
    t = 0.10
    gx, gy = x % t, y % t
    ti, tj = np.floor(x / t).astype(int), np.floor(y / t).astype(int)
    r = np.random.default_rng(seed)
    var = r.uniform(0.9, 1.08, (20, 20))
    chk = (ti + tj) % 2 == 0
    base = np.where(chk[..., None], col("#9c4a32")[None, None, :], col("#c9b48e")[None, None, :])
    base = base * var[tj % 20, ti % 20][..., None] * (1 + 0.06 * (n1[..., None] - 0.5))
    m = np.minimum(np.minimum(gx, t - gx), np.minimum(gy, t - gy))
    grout = m < 0.0018
    height = smooth(0.0, 0.006, m)
    base[grout] = col("#5a5348") * (0.8 + 0.3 * n2[grout, None])
    rough = np.where(grout, 0.95, 0.55 + 0.25 * n1)
    odd = r.random((20, 20))
    wear = smooth(0.55, 0.85, blur(spectral(h, w, 2.6, seed + 4), 3))
    base = base * (1 - 0.08 * wear[..., None]) + col("#8e8070") * 0.08 * wear[..., None]
    save_set(out, name, np.clip(base, 0, 1), np.clip(rough, 0, 1), height=height, nstrength=4.0)


def terrazzo(name, out, seed):
    h = w = S
    r = np.random.default_rng(seed)
    n1, n2 = spectral(h, w, 1.6, seed), spectral(h, w, 2.6, seed + 1)
    base = col("#9d978a")[None, None, :] * (0.95 + 0.1 * n1[..., None])
    im = Image.new("RGB", (w, h), (0, 0, 0))
    hm = Image.new("L", (w, h), 0)
    d, dh = ImageDraw.Draw(im), ImageDraw.Draw(hm)
    chips = ["#e8e2d4", "#5e5a52", "#b5a58a", "#7f4e3a", "#c9c3b5", "#3f3c38", "#a39684"]
    for _ in range(5200):
        x, y, rad = r.uniform(0, w), r.uniform(0, h), r.uniform(1.2, 5.5) ** 1.15
        c = tuple(int(v * 255) for v in col(chips[r.integers(len(chips))]) * r.uniform(0.85, 1.1))
        k = r.integers(4, 7)
        ang = r.uniform(0, 2 * np.pi)
        pts = [(x + rad * r.uniform(0.6, 1.2) * np.cos(ang + 2 * np.pi * j / k),
                y + rad * r.uniform(0.6, 1.2) * np.sin(ang + 2 * np.pi * j / k)) for j in range(k)]
        for ox in (-w, 0, w):
            for oy in (-h, 0, h):
                pp = [(p[0] + ox, p[1] + oy) for p in pts]
                d.polygon(pp, fill=c)
                dh.polygon(pp, fill=255)
    cm = np.asarray(hm, np.float32) / 255.0
    base = base * (1 - cm[..., None]) + (np.asarray(im, np.float32) / 255.0) * cm[..., None]
    # brass divider strips forming 1 m squares
    xs = (np.arange(w) + 0.5) / w * 2.0
    strip = np.abs(((xs + 0.5) % 1.0) - 0.5) < 0.003
    base[:, strip] = col("#8a7442")
    base[strip, :] = col("#8a7442")
    height = n2 * 0.2 + cm * 0.05
    height[:, strip] += 0.5
    height[strip, :] += 0.5
    wear = smooth(0.5, 0.85, blur(spectral(h, w, 2.6, seed + 2), 3))
    rough = 0.22 + 0.2 * wear + 0.08 * n1
    base = base * (1 - 0.06 * wear[..., None]) + col("#8d887d") * 0.06 * wear[..., None]
    save_set(out, name, np.clip(base, 0, 1), np.clip(rough, 0, 1), height=height, nstrength=2.0)


def wood(name, out, seed, c0, c1, door=False):
    h, w = (1024, 512) if door else (S, S)
    r = np.random.default_rng(seed)
    yy = np.repeat(np.arange(h)[:, None], w, 1) / h
    xx = np.repeat(np.arange(w)[None, :], h, 0) / w
    warp = spectral(h, w, 2.4, seed) * 6
    rings = np.sin((xx * (14 if door else 22) + warp) * 2 * np.pi) * 0.5 + 0.5
    fib = spectral(h, w, 0.5, seed + 1)
    fib = blur(fib, 0.5)
    grain = np.clip(rings * 0.6 + fib * 0.4, 0, 1)
    base = lerp(col(c0), col(c1), grain)
    height = grain * 0.3
    n2 = spectral(h, w, 1.8, seed + 2)
    rough = 0.32 + 0.25 * n2
    if door:
        # varnish worn at the lock side (x ~ 0.85-1.0, z 0.9-1.1 m of 2.1) and kick scuffs at the bottom
        z = (1 - yy) * 2.1
        hand = np.exp(-((xx - 0.88) / 0.10) ** 2 - ((z - 1.0) / 0.25) ** 2)
        base = base * (1 - 0.08 * hand[..., None]) + col("#5d4632") * 0.08 * hand[..., None]
        rough += 0.1 * hand
        kick = smooth(0.35, 0.0, z) * (spectral(h, w, 1.2, seed + 3) > 0.5)
        sc = scratches(h, w, 90, seed + 4, length=(0.02, 0.08), width=2, angle=0.0) * smooth(0.45, 0.05, z)
        base *= (1 - 0.1 * sc[..., None])
        base = base * (1 - 0.06 * kick[..., None]) + col("#3a2a1e") * 0.06 * kick[..., None]
        edge = (xx < 0.012) | (xx > 0.988) | (yy < 0.006) | (yy > 0.994)
        base[edge] *= 0.75
    else:
        sc = scratches(h, w, 30, seed + 4, length=(0.01, 0.04), width=1)
        base *= (1 - 0.06 * sc[..., None])
    dust = blobs(h, w, 5, seed + 6, 40, 120)
    base = mix_col(np.clip(dust * 0.04, 0, 0.04), base, col("#9b9184"))
    rough = np.clip(rough + 0.04 * dust, 0, 1)
    save_set(out, name, np.clip(base, 0, 1), rough, height=height, nstrength=1.5)


def metal_painted(name, out, seed, paint="#9aa69a", undercoat="#6d4a3a"):
    h = w = S
    n1, n2 = spectral(h, w, 1.8, seed), spectral(h, w, 1.0, seed + 1)
    base = col(paint)[None, None, :] * (0.94 + 0.1 * n1[..., None])
    chips = spectral(h, w, 1.3, seed + 2, lo=3) > 0.985
    base[chips] = base[chips] * 0.85 + col(undercoat) * 0.15
    sc = scratches(h, w, 30, seed + 4, length=(0.01, 0.04), width=1)
    base = mix_col(sc * 0.15, base, col("#c8c8c0"))
    metal = np.clip(sc * 0.3, 0, 1)
    height = n1 * 0.15 - chips * 0.1
    rough = 0.38 + 0.12 * n2
    save_set(out, name, np.clip(base, 0, 1), np.clip(rough, 0, 1), height=height, nstrength=3.0, metal=metal)


def metal_rusty(name, out, seed):
    h = w = S
    n1, n2, n3 = spectral(h, w, 1.6, seed), spectral(h, w, 0.9, seed + 1), spectral(h, w, 2.4, seed + 2)
    paint = col("#4c5148")[None, None, :] * (0.9 + 0.2 * n1[..., None])
    rustm = smooth(0.85, 0.98, n3 * 0.7 + n2 * 0.3) * 0.3
    rust = lerp(col("#5a2c14"), col("#a35a2a"), n2) * (0.8 + 0.3 * n1[..., None])
    base = paint * (1 - rustm[..., None]) + rust * rustm[..., None]
    height = rustm * 0.5 + n2 * 0.3
    rough = 0.55 + 0.4 * rustm
    metal = (1 - rustm) * 0.3
    save_set(out, name, np.clip(base, 0, 1), np.clip(rough, 0, 1), height=height, nstrength=4.0, metal=metal)


def glass_dusty(name, out, seed):
    h = w = S
    n1, n2 = spectral(h, w, 1.8, seed), spectral(h, w, 0.8, seed + 1)
    yy = np.repeat(np.arange(h)[:, None], w, 1) / h
    streak = blur(spectral(h, w, 0.6, seed + 2), 1.0)
    streak = np.repeat(streak.mean(0, keepdims=True), h, 0) * 0.6 + streak * 0.4   # vertical rain streaks
    dust = np.clip(0.35 * n1 + 0.25 * smooth(0.6, 1.0, yy) + 0.25 * smooth(0.55, 0.8, streak), 0, 1)
    base = col("#c9c4b6")[None, None, :] * (0.9 + 0.1 * n2[..., None])
    alpha = np.clip(0.05 + 0.08 * dust, 0, 0.2)
    rough = np.clip(0.03 + 0.08 * dust, 0, 1)
    save_set(out, name, np.clip(base, 0, 1), rough, alpha=alpha, height=n1 * 0.05, nstrength=0.5)


def salt_brick(name, out, seed):
    """Himalayan-style salt blocks (0.20 x 0.10 m) for the salt room walls; v = height above floor."""
    h = w = S
    z = zgrid()
    x = np.repeat(((np.arange(w) + 0.5) / w * 3.0)[None, :], h, 0)
    bw, bh = 0.20, 0.10
    row = np.floor(z / bh).astype(int)
    xs = x + (row % 2) * bw / 2
    gx, gy = xs % bw, z % bh
    bi = np.floor(xs / bw).astype(int)
    r = np.random.default_rng(seed)
    lut = r.uniform(0, 1, (64, 64))
    tone = lut[row % 64, bi % 64]
    n1, n2 = spectral(h, w, 1.2, seed), spectral(h, w, 0.6, seed + 1)
    base = lerp(col("#d89a74"), col("#f0c8a8"), tone)
    base = base * (0.88 + 0.18 * n1[..., None]) + (n2[..., None] > 0.8) * 0.06
    m = np.minimum(np.minimum(gx, bw - gx), np.minimum(gy, bh - gy))
    joint = m < 0.004
    base[joint] = col("#c89a7a") * 0.85
    height = smooth(0.0, 0.015, m) * 0.6 + n1 * 0.3
    rough = np.where(joint, 0.9, 0.55 + 0.25 * n2)
    sk = z < 0.10
    base[sk] = col("#6a4a38")
    height[sk] = 1.0
    save_set(out, name, np.clip(base, 0, 1), np.clip(rough, 0, 1), height=height, nstrength=4.0)


def generate_surfaces(out):
    jobs = [
        lambda: paint_wall("T_Paint_WallGreen", out, "#7f9a7c", "#dcd6c2", 101),
        lambda: paint_wall("T_Paint_WallBlue", out, "#8ea8b4", "#dfe0d6", 102),
        lambda: paint_wall("T_Paint_WallBeige", out, "#c8b080", "#e2d8bd", 103, line="#7a6646"),
        lambda: paint_wall("T_Paint_WallPeach", out, "#cfa58a", "#e6dac4", 104, line="#80604a"),
        lambda: tile_wall("T_Tile_WallWhite", out, 105),
        lambda: wallpaper("T_Wallpaper_Floral", out, 106, "#e2d6b4", "#a0714a", "#b89a6e", "floral"),
        lambda: wallpaper("T_Wallpaper_Geometric", out, 107, "#c9d1b4", "#6f8257", "#9aa684", "geometric"),
        lambda: plaster("T_Plaster_White", out, 108, tint="#e2ded2"),
        lambda: plaster("T_Ceiling_Paint", out, 109, tint="#eeebe2", ceiling=True),
        lambda: concrete("T_Concrete_Interior", out, 110),
        lambda: linoleum("T_Linoleum_Brown", out, 111, "brown"),
        lambda: linoleum("T_Linoleum_Parquet", out, 112, "parquet"),
        lambda: tile_floor("T_Tile_FloorCeramic", out, 113),
        lambda: terrazzo("T_Terrazzo", out, 114),
        lambda: wood("T_Wood_DoorDark", out, 115, "#3b2618", "#5a3a24", door=True),
        lambda: wood("T_Wood_Furniture", out, 116, "#5e3d23", "#8a5f3a"),
        lambda: metal_painted("T_Metal_Painted", out, 117),
        lambda: metal_rusty("T_Metal_DarkSteel", out, 118),
        lambda: glass_dusty("T_Glass_Clear", out, 119),
        lambda: salt_brick("T_Salt_Brick", out, 120),
    ]
    return jobs
