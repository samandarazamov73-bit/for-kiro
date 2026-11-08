#!/usr/bin/env python3
"""Build the packed, game-ready textures for Forest Drive from the CC0 sources.

Outputs (under assets/textures):
  terrain/terrain_albedo_h.webp   Texture2DArray, 6 layers  RGB albedo + A height
  terrain/terrain_normal_r.webp   Texture2DArray, 6 layers  RG normal + B roughness + A AO
  road/asphalt_albedo_h.webp      Texture2DArray, 2 layers  (clean, cracked/worn asphalt)
  road/asphalt_normal_r.webp      Texture2DArray, 2 layers
  bark/bark_albedo_h.webp         Texture2DArray, 6 layers  pine, spruce/fir, birch, oak, deciduous, alder
  bark/bark_normal_r.webp         Texture2DArray, 6 layers
  foliage/foliage_albedo.webp     4K atlas RGBA (alpha = cut-out)
  foliage/foliage_normal.webp     4K atlas RG normal + B roughness + A translucency
  foliage/foliage_atlas.json      atlas rectangles (used by build_assets.py)
  rocks/rocks_albedo.webp, rocks/rocks_normal.webp     4K atlas of 4 rock scans
  props/props_albedo.webp, props/props_normal.webp     4K atlas of stumps / log / branches

The birch bark layer is generated procedurally (no CC0 birch scan was available).
Each output gets a .import file with the intended Godot import settings.

Usage: FOREST_SRC=<dir from fetch_assets.py> python3 tools/build_textures.py
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import texlib as T  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.environ.get("FOREST_SRC", os.path.join(HERE, ".cache", "src"))
OUT = os.path.join(ROOT, "assets", "textures")
L = 2048  # layer resolution for tiling materials


def ph(aid: str, mp: str, res: str = "2k") -> str:
    sub = "tex4k" if res == "4k" else "tex2k"
    p = os.path.join(SRC, sub, f"{aid}__{mp.lower()}_{res}.jpg")
    if not os.path.exists(p):
        raise FileNotFoundError(p + " (run tools/fetch_assets.py)")
    return p


def acg(aid: str, mp: str) -> str:
    return os.path.join(SRC, "acg", aid, f"{aid}_2K-JPG_{mp}.jpg")


# ----------------------------------------------------------------- import files
def write_import(path: str, kind: str, **kw) -> None:
    """kind: 'array' (Texture2DArray) or 'tex' (Texture2D)."""
    if kind == "array":
        head = 'importer="2d_array_texture"\ntype="CompressedTexture2DArray"\n'
        params = {
            "compress/mode": 2, "compress/high_quality": kw.get("hq", False), "compress/channel_pack": 0,
            "mipmaps/generate": True, "mipmaps/limit": -1,
            "slices/horizontal": 1, "slices/vertical": kw["layers"],
        }
    else:
        head = 'importer="texture"\ntype="CompressedTexture2D"\n'
        params = {
            "compress/mode": kw.get("mode", 2), "compress/high_quality": kw.get("hq", False),
            "compress/normal_map": kw.get("normal_map", 2), "compress/channel_pack": 0,
            "mipmaps/generate": kw.get("mipmaps", True), "process/fix_alpha_border": True,
            "process/size_limit": 0, "detect_3d/compress_to": 0, "roughness/mode": 0,
        }
    with open(path + ".import", "w") as f:
        f.write("[remap]\n\n" + head + "\n[params]\n\n")
        for k, v in params.items():
            f.write(f"{k}={'true' if v is True else 'false' if v is False else v}\n")


def save_array(layers: list[np.ndarray], path: str, hq: bool = False) -> None:
    stacked = np.concatenate(layers, axis=0)
    T.save(stacked, path, quality=93)
    write_import(path, "array", layers=len(layers), hq=hq)
    print("wrote", os.path.relpath(path, ROOT), stacked.shape)


def norm_height(h: np.ndarray, lo_pct=1.0, hi_pct=99.0, gamma=1.0) -> np.ndarray:
    lo, hi = np.percentile(h, lo_pct), np.percentile(h, hi_pct)
    return np.clip((h - lo) / max(hi - lo, 1e-6), 0, 1) ** gamma


def pack_material(diff, nor, rough, ao, height, tint=None, rough_bias=0.0, rough_scale=1.0):
    alb = diff[:, :, :3]
    if tint is not None:
        alb = T.match_mean(alb, tint, strength=0.8)
    a = np.concatenate([alb, height[:, :, None]], axis=2)
    r = np.clip(rough * rough_scale + rough_bias, 0.02, 1.0)
    n = np.concatenate([nor[:, :, :2], r[:, :, None], ao[:, :, None]], axis=2)
    return a, n


def ph_material(aid: str, tint=None, rough_bias=0.0, rough_scale=1.0, height_gamma=1.0):
    diff = T.load(ph(aid, "Diffuse"), "RGB", (L, L))
    nor = T.load(ph(aid, "nor_gl"), "RGB", (L, L))
    arm = T.load(ph(aid, "arm"), "RGB", (L, L))
    h = norm_height(T.load(ph(aid, "Displacement"), "L", (L, L))[:, :, 0], gamma=height_gamma)
    return pack_material(diff, nor, arm[:, :, 1], arm[:, :, 0], h, tint, rough_bias, rough_scale)


def acg_material(aid: str, tint=None, rough_bias=0.0, rough_scale=1.0, height_gamma=1.0):
    diff = T.load(acg(aid, "Color"), "RGB", (L, L))
    nor = T.load(acg(aid, "NormalGL"), "RGB", (L, L))
    rough = T.load(acg(aid, "Roughness"), "L", (L, L))[:, :, 0]
    aop = acg(aid, "AmbientOcclusion")
    ao = T.load(aop, "L", (L, L))[:, :, 0] if os.path.exists(aop) else np.ones((L, L), np.float32)
    h = norm_height(T.load(acg(aid, "Displacement"), "L", (L, L))[:, :, 0], gamma=height_gamma)
    return pack_material(diff, nor, rough, ao, h, tint, rough_bias, rough_scale)


# ------------------------------------------------------------------- terrain
def build_terrain():
    layers = [
        ph_material("forest_leaves_03", tint=(0.20, 0.17, 0.11)),          # 0 broadleaf litter
        ph_material("forest_leaves_04", tint=(0.30, 0.22, 0.14)),          # 1 needles / dry litter
        acg_material("Moss002", tint=(0.20, 0.26, 0.08), rough_bias=0.05),  # 2 moss
        ph_material("sparse_grass", tint=(0.17, 0.20, 0.09)),              # 3 grass verge
        ph_material("mud_forest", tint=(0.16, 0.12, 0.08)),                # 4 soil
        ph_material("rock_ground", tint=(0.27, 0.26, 0.24)),               # 5 gravel shoulder
    ]
    save_array([a for a, _ in layers], os.path.join(OUT, "terrain", "terrain_albedo_h.webp"))
    save_array([n for _, n in layers], os.path.join(OUT, "terrain", "terrain_normal_r.webp"), hq=True)


def build_road():
    clean = ph_material("clean_asphalt", rough_bias=0.0)
    worn = ph_material("asphalt_02", tint=(0.20, 0.20, 0.19))
    save_array([clean[0], worn[0]], os.path.join(OUT, "road", "asphalt_albedo_h.webp"))
    save_array([clean[1], worn[1]], os.path.join(OUT, "road", "asphalt_normal_r.webp"), hq=True)


# ---------------------------------------------------------------------- bark
def birch_bark(size=L, seed=7):
    """Procedural silver-birch bark: chalky white periderm, horizontal lenticels,
    dark diamond scars and peeling strips. Tileable. Returns (albedo_h, normal_r)."""
    rng = np.random.default_rng(seed)
    base = T.fft_noise(size, 2.2, seed + 1, lo=2)
    fine = T.fft_noise(size, 1.2, seed + 2, lo=8)
    streak = T.fft_noise(size, 2.0, seed + 3, lo=1, aspect=(0.25, 3.0))   # horizontal banding
    h = 0.55 + 0.08 * (base - 0.5) + 0.04 * (fine - 0.5) + 0.06 * (streak - 0.5)
    col = np.zeros((size, size, 3), np.float32)
    white = np.array([0.86, 0.85, 0.80], np.float32)
    warm = np.array([0.80, 0.72, 0.62], np.float32)
    grey = np.array([0.64, 0.64, 0.61], np.float32)
    w1 = np.clip((base - 0.55) * 4, 0, 1)[:, :, None]
    w2 = np.clip((streak - 0.6) * 4, 0, 1)[:, :, None]
    col[:] = white
    col = col * (1 - w1 * 0.6) + grey * (w1 * 0.6)
    col = col * (1 - w2 * 0.35) + warm * (w2 * 0.35)
    col *= (0.92 + 0.12 * fine)[:, :, None]
    dark = np.zeros((size, size), np.float32)   # 1 where dark scars/lenticels
    img = Image.new("L", (size * 2, size * 2), 0)
    dr = ImageDraw.Draw(img)
    S = size * 2
    def tile_draw(fn, x, y, extent):
        for ox in (-S, 0, S):
            for oy in (-S, 0, S):
                if -extent <= x + ox <= S + extent and -extent <= y + oy <= S + extent:
                    fn(x + ox, y + oy)
    # lenticels: short horizontal dark dashes
    for _ in range(2600):
        x, y = rng.uniform(0, S, 2)
        ln = rng.uniform(20, 170) * (1.4 if rng.random() < 0.15 else 1)
        th = rng.uniform(2.5, 6.5)
        v = int(rng.uniform(140, 255))
        tile_draw(lambda X, Y: dr.rounded_rectangle([X - ln / 2, Y - th / 2, X + ln / 2, Y + th / 2], radius=th / 2, fill=v), x, y, ln)
    # dark branch scars (chevrons / diamonds)
    for _ in range(26):
        x, y = rng.uniform(0, S, 2)
        w = rng.uniform(60, 260); hh = w * rng.uniform(0.35, 0.7)
        pts = [(0, -hh * 0.5), (w * 0.5, 0), (0, hh * 0.25), (-w * 0.5, 0)]
        tile_draw(lambda X, Y: dr.polygon([(X + px + rng.normal(0, 6), Y + py + rng.normal(0, 6)) for px, py in pts], fill=255), x, y, w)
    # horizontal dark bands
    for _ in range(10):
        y = rng.uniform(0, S); hh = rng.uniform(8, 30); x0 = rng.uniform(0, S); ln = rng.uniform(300, 1400)
        v = int(rng.uniform(80, 170))
        tile_draw(lambda X, Y: dr.rectangle([X, Y - hh / 2, X + ln, Y + hh / 2], fill=v), x0, y, ln)
    img = img.filter(ImageFilter.GaussianBlur(2.0)).resize((size, size), Image.LANCZOS)
    dark = np.asarray(img, np.float32) / 255.0
    dark *= 0.7 + 0.6 * T.fft_noise(size, 1.5, seed + 9, lo=16)
    dark = np.clip(dark, 0, 1)
    scar_col = np.array([0.10, 0.09, 0.085], np.float32)
    col = col * (1 - dark[:, :, None]) + scar_col * dark[:, :, None]
    # peeling strips: thin raised curls with a shadow below
    peel = Image.new("L", (S, S), 0); dp = ImageDraw.Draw(peel)
    for _ in range(140):
        x, y = rng.uniform(0, S, 2); ln = rng.uniform(80, 420); th = rng.uniform(2, 5)
        tile_draw(lambda X, Y: dp.line([(X, Y), (X + ln, Y + rng.normal(0, 4))], fill=255, width=int(th)), x, y, ln)
    peel = np.asarray(peel.filter(ImageFilter.GaussianBlur(1.2)).resize((size, size), Image.LANCZOS), np.float32) / 255.0
    col = col * (1 + 0.10 * peel[:, :, None])
    h = h - 0.35 * dark + 0.25 * peel
    h = T.blur_wrap(h, 0.8)
    nrm = T.height_to_normal(h, 22.0)
    rough = 0.62 + 0.18 * dark + 0.08 * (fine - 0.5)
    ao = 1.0 - 0.35 * dark
    alb_h = np.concatenate([np.clip(col, 0, 1), norm_height(h)[:, :, None]], axis=2)
    nr = np.concatenate([nrm[:, :, :2], rough[:, :, None], ao[:, :, None]], axis=2)
    return alb_h, nr


def build_bark():
    layers = [
        ph_material("pine_bark", tint=(0.30, 0.20, 0.15)),                 # 0 scots pine
        acg_material("Bark014", tint=(0.24, 0.18, 0.14)),                  # 1 spruce / fir
        birch_bark(),                                                      # 2 silver birch
        acg_material("Bark001", tint=(0.26, 0.25, 0.23)),                  # 3 oak
        ph_material("bark_brown_02", tint=(0.28, 0.26, 0.21)),             # 4 deciduous (maple/linden)
        ph_material("tree_bark_03", tint=(0.33, 0.33, 0.27)),              # 5 alder / hornbeam with lichen
    ]
    save_array([a for a, _ in layers], os.path.join(OUT, "bark", "bark_albedo_h.webp"))
    save_array([n for _, n in layers], os.path.join(OUT, "bark", "bark_normal_r.webp"), hq=True)


# ------------------------------------------------------------------- foliage
class Sprite:
    """An alpha-cut source cut-out: rgba (PIL RGBA), nrm (PIL RGB), rough (PIL L)."""

    def __init__(self, rgba, nrm, rough, translucency=0.5):
        self.rgba, self.nrm, self.rough, self.tr = rgba, nrm, rough, translucency

    @property
    def size(self):
        return self.rgba.size


def load_source(diff, alpha, nor, rough=None, scale=1.0):
    d = Image.open(diff).convert("RGB")
    W, H = d.size
    if scale != 1.0:
        W, H = int(W * scale), int(H * scale)
        d = d.resize((W, H), Image.LANCZOS)
    a = Image.open(alpha).convert("L").resize((W, H), Image.LANCZOS)
    n = Image.open(nor).convert("RGB").resize((W, H), Image.LANCZOS)
    r = Image.open(rough).convert("L").resize((W, H), Image.LANCZOS) if rough else Image.new("L", (W, H), 150)
    rgba = d.copy(); rgba.putalpha(a)
    return rgba, n, r


def crop_sprite(src, rect, tr=0.5, pad=6, tighten=True, clean=False):
    """Cut a region out of a source atlas. clean=True drops opaque islands that touch the crop
    border (neighbouring UV islands / stretched padding in the scans) and keeps the isolated cut-out."""
    rgba, n, r = src
    W, H = rgba.size
    x0, y0, x1, y1 = int(rect[0] * W), int(rect[1] * H), int(rect[2] * W), int(rect[3] * H)
    box = (x0, y0, x1, y1)
    if clean:
        from scipy import ndimage
        c = rgba.crop(box)
        al = np.asarray(c.split()[3], np.float32)
        lab, nl = ndimage.label(al > 20, structure=np.ones((3, 3)))
        border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
        keep = ~np.isin(lab, list(border)) & (lab > 0)
        keep = ndimage.binary_dilation(keep, iterations=2)
        al = np.where(keep, al, 0).astype(np.uint8)
        c.putalpha(Image.fromarray(al))
        full = rgba.copy(); full.paste(c, box[:2])
        rgba = full
    if tighten:
        a = np.asarray(rgba.crop(box).split()[3]) > 40
        ys, xs = np.nonzero(a)
        if len(xs):
            box = (max(x0 + xs.min() - pad, 0), max(y0 + ys.min() - pad, 0),
                   min(x0 + xs.max() + pad, W), min(y0 + ys.max() + pad, H))
    return Sprite(rgba.crop(box), n.crop(box), r.crop(box), tr)


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.rgb = np.zeros((h, w, 3), np.float32)
        self.a = np.zeros((h, w), np.float32)
        self.n = np.zeros((h, w, 3), np.float32); self.n[:] = (0.5, 0.5, 1.0)
        self.r = np.full((h, w), 0.6, np.float32)
        self.t = np.zeros((h, w), np.float32)

    def stamp(self, sp: Sprite, anchor, pos, scale, angle, flip=False, shade=1.0, tint=(1, 1, 1)):
        """Place sprite so that its anchor (fraction of sprite size) lands on pos (canvas px),
        scaled, rotated CCW by angle degrees, optionally mirrored."""
        sw, sh = sp.size
        ax, ay = anchor[0] * sw, anchor[1] * sh
        t = math.radians(angle)
        c, s = math.cos(t) * scale, math.sin(t) * scale
        fx = -1.0 if flip else 1.0
        # forward map sprite px -> canvas px (image coords, y down; visual CCW rotation)
        def fwd(x, y):
            dx, dy = (x - ax) * fx, (y - ay)
            return pos[0] + c * dx + s * dy, pos[1] - s * dx + c * dy
        corners = [fwd(0, 0), fwd(sw, 0), fwd(0, sh), fwd(sw, sh)]
        X0 = max(int(math.floor(min(p[0] for p in corners))), 0)
        Y0 = max(int(math.floor(min(p[1] for p in corners))), 0)
        X1 = min(int(math.ceil(max(p[0] for p in corners))), self.w)
        Y1 = min(int(math.ceil(max(p[1] for p in corners))), self.h)
        if X1 <= X0 or Y1 <= Y0:
            return
        # inverse affine: canvas (X, Y) relative to window origin -> sprite (x, y)
        det = c * c + s * s
        ic, is_ = c / det, s / det
        # dx = ic*(X-px) - is*(Y-py) ; dy = is*(X-px) + ic*(Y-py)
        ox, oy = X0 - pos[0], Y0 - pos[1]
        a_ = ic * fx; b_ = -is_ * fx; c_ = (ic * ox - is_ * oy) * fx + ax
        d_ = is_; e_ = ic; f_ = is_ * ox + ic * oy + ay
        data = (a_, b_, c_, d_, e_, f_)
        size = (X1 - X0, Y1 - Y0)
        rgba = np.asarray(sp.rgba.transform(size, Image.AFFINE, data, Image.BICUBIC), np.float32) / 255.0
        nrm = np.asarray(sp.nrm.transform(size, Image.AFFINE, data, Image.BILINEAR), np.float32) / 255.0
        rough = np.asarray(sp.rough.transform(size, Image.AFFINE, data, Image.BILINEAR), np.float32) / 255.0
        nrm = T.rotate_normal_rgb(nrm, angle, flip_x=flip)
        al = rgba[:, :, 3]
        win = (slice(Y0, Y1), slice(X0, X1))
        col = rgba[:, :, :3] * shade * np.array(tint, np.float32)
        self.rgb[win] = col * al[:, :, None] + self.rgb[win] * (1 - al[:, :, None])
        self.n[win] = nrm * al[:, :, None] + self.n[win] * (1 - al[:, :, None])
        self.r[win] = rough * al + self.r[win] * (1 - al)
        self.t[win] = sp.tr * al + self.t[win] * (1 - al)
        self.a[win] = al + self.a[win] * (1 - al)

    def line(self, pts, w0, w1, color, rough=0.8):
        """Tapered woody twig as a polyline (drawn opaque)."""
        img = Image.new("L", (self.w, self.h), 0); d = ImageDraw.Draw(img)
        n = len(pts) - 1
        for i in range(n):
            wi = w0 + (w1 - w0) * i / max(n, 1)
            d.line([pts[i], pts[i + 1]], fill=255, width=max(int(wi), 1))
            d.ellipse([pts[i][0] - wi / 2, pts[i][1] - wi / 2, pts[i][0] + wi / 2, pts[i][1] + wi / 2], fill=255)
        m = np.asarray(img.filter(ImageFilter.GaussianBlur(0.7)), np.float32) / 255.0
        col = np.array(color, np.float32)
        self.rgb = col * m[:, :, None] + self.rgb * (1 - m[:, :, None])
        self.a = np.maximum(self.a, m)
        self.r = rough * m + self.r * (1 - m)
        self.t = self.t * (1 - m)

    def sprite(self, tr=None) -> Sprite:
        rgba = np.concatenate([self.rgb, self.a[:, :, None]], axis=2)
        nrm = T.normalize_normal_rgb(self.n.copy())
        return Sprite(T.to_pil(rgba), T.to_pil(nrm), T.to_pil(self.r[:, :, None]), tr if tr is not None else 0.5)


def oak_leaf_mask(w, h, seed):
    """Lobed oak-leaf silhouette (L image)."""
    rng = np.random.default_rng(seed)
    S = 4
    img = Image.new("L", (w * S, h * S), 0); d = ImageDraw.Draw(img)
    lobes = rng.integers(4, 6)
    pts_l, pts_r = [], []
    for i in range(121):
        t = i / 120
        env = math.sin(math.pi * min(t ** 0.85, 1.0)) * 0.46
        lob = 0.62 + 0.38 * abs(math.cos(math.pi * lobes * (t + 0.08)))
        wid = env * lob * (1 - 0.25 * (t < 0.12))
        y = (0.04 + 0.92 * t) * h * S
        pts_l.append((w * S * (0.5 - wid), y)); pts_r.append((w * S * (0.5 + wid), y))
    d.polygon(pts_l + pts_r[::-1], fill=255)
    return img.filter(ImageFilter.GaussianBlur(S * 0.6)).resize((w, h), Image.LANCZOS)


def compose_foliage():
    rng = np.random.default_rng(1234)
    fir = load_source(ph("fir_tree_01", "twig_diff", "4k"), ph("fir_tree_01", "twig_alpha", "4k"),
                      ph("fir_tree_01", "twig_nor_gl", "4k"), ph("fir_tree_01", "twig_rough", "4k"))
    pine = load_source(ph("pine_tree_01", "twig_diff", "4k"), ph("pine_tree_01", "twig_alpha", "4k"),
                       ph("pine_tree_01", "twig_nor_gl", "4k"), ph("pine_tree_01", "twig_rough", "4k"))
    fern = load_source(ph("fern_02", "Diffuse", "4k"), ph("fern_02", "Alpha", "4k"), ph("fern_02", "nor_gl", "4k"),
                       ph("fern_02", "Rough", "4k"))
    grass = load_source(ph("grass_medium_01", "Diffuse"), ph("grass_medium_01", "Alpha"), ph("grass_medium_01", "nor_gl"),
                        ph("grass_medium_01", "Rough"))
    moss = load_source(ph("moss_01", "Diffuse"), ph("moss_01", "Alpha"), ph("moss_01", "nor_gl"))
    nettle = load_source(ph("nettle_plant", "Diffuse"), ph("nettle_plant", "Alpha"), ph("nettle_plant", "nor_gl"))
    leaf1 = load_source(acg("Leaf001", "Color"), acg("Leaf001", "Opacity"), acg("Leaf001", "NormalGL"), acg("Leaf001", "Roughness"))
    leaf3 = load_source(acg("Leaf003", "Color"), acg("Leaf003", "Opacity"), acg("Leaf003", "NormalGL"), acg("Leaf003", "Roughness"))

    S = {}
    S["fir_a"] = crop_sprite(fir, (0.305, 0.395, 0.645, 0.785), 0.30, clean=True)
    S["fir_b"] = crop_sprite(fir, (0.625, 0.445, 0.955, 0.84), 0.30, clean=True)
    S["fir_c"] = crop_sprite(fir, (0.185, 0.035, 0.43, 0.315), 0.30, clean=True)
    S["fir_d"] = crop_sprite(fir, (0.65, 0.03, 0.945, 0.375), 0.30, clean=True)
    S["fir_e"] = crop_sprite(fir, (0.495, 0.255, 0.63, 0.40), 0.30, clean=True)
    S["pine_a"] = crop_sprite(pine, (0.0, 0.02, 0.235, 0.47), 0.30, clean=True)
    S["pine_b"] = crop_sprite(pine, (0.62, 0.31, 0.98, 0.54), 0.30, clean=True)
    for i, rc in enumerate([(0.085, 0.10, 0.245, 0.955), (0.30, 0.02, 0.465, 0.775), (0.50, 0.02, 0.665, 0.505),
                            (0.705, 0.10, 0.86, 0.905), (0.505, 0.505, 0.645, 0.975)]):
        S[f"fern_{i}"] = crop_sprite(fern, rc, 0.45)
    for i, rc in enumerate([(0.20, 0.745, 0.495, 0.858), (0.59, 0.76, 0.79, 0.865), (0.02, 0.875, 0.20, 0.966),
                            (0.24, 0.885, 0.505, 0.966), (0.58, 0.865, 0.80, 0.966)]):
        S[f"grass_{i}"] = crop_sprite(grass, rc, 0.45, tighten=False)
    for i, rc in enumerate([(0.04, 0.08, 0.16, 0.26), (0.62, 0.15, 0.80, 0.46), (0.26, 0.63, 0.43, 0.90)]):
        S[f"moss_{i}"] = crop_sprite(moss, rc, 0.4)
    for i, rc in enumerate([(0.36, 0.62, 0.59, 0.86), (0.01, 0.05, 0.19, 0.25), (0.49, 0.37, 0.67, 0.58), (0.80, 0.76, 0.98, 0.94)]):
        S[f"nettle_{i}"] = crop_sprite(nettle, rc, 0.55)
    leaf_a = crop_sprite(leaf1, (0.0, 0.0, 0.5, 1.0), 0.6)
    leaf_b = crop_sprite(leaf1, (0.5, 0.0, 1.0, 1.0), 0.6)
    S["compound_leaf"] = crop_sprite(leaf3, (0.0, 0.0, 0.5, 1.0), 0.55)

    # oak leaves: Leaf001 texture under a lobed silhouette
    oak_leaves = []
    for k in range(3):
        base = leaf_a if k % 2 == 0 else leaf_b
        w, h = base.size
        m = oak_leaf_mask(w, h, 50 + k)
        a = Image.fromarray((np.asarray(base.rgba.split()[3], np.float32) * (np.asarray(m, np.float32) / 255.0)).astype(np.uint8))
        rgba = base.rgba.copy(); rgba.putalpha(a)
        oak_leaves.append(Sprite(rgba, base.nrm, base.rough, 0.5))

    fir_sprigs = [S["fir_a"], S["fir_b"], S["fir_c"], S["fir_d"], S["fir_e"]]
    bark_brown = (0.23, 0.17, 0.12)

    # --- spruce branch card (LOD1): sprigs along a drooping branch, base at left-centre
    cv = Canvas(1024, 1024)
    pts = [(20 + 980 * t, 520 + 70 * t * t + 18 * math.sin(t * 7)) for t in np.linspace(0, 1, 30)]
    cv.line(pts, 14, 3, bark_brown)
    for i in range(26):
        t = 0.06 + 0.92 * i / 25
        x, y = pts[min(int(t * 29), 29)]
        side = 1 if i % 2 == 0 else -1
        ang = side * rng.uniform(30, 65) - 90 + rng.normal(0, 6)   # sprite up = +90deg
        sc = (1.0 - 0.45 * t) * rng.uniform(0.28, 0.36) * 1024 / 1500
        sp = fir_sprigs[rng.integers(0, len(fir_sprigs))]
        cv.stamp(sp, (0.5, 0.97), (x, y), sc * 1500 / sp.size[1], ang, flip=rng.random() < 0.5,
                 shade=0.78 + 0.22 * i / 25)
    for i in range(10):  # leading shoot at tip
        cv.stamp(fir_sprigs[i % 5], (0.5, 0.97), pts[-3], 0.22 * 1024 / fir_sprigs[i % 5].size[1] * 1.6,
                 -90 + rng.normal(0, 25), shade=0.95)
    S["spruce_branch"] = cv.sprite(0.30)

    # --- conifer mass (LOD2 crown card): dense rounded/triangular blob
    cv = Canvas(1024, 1024)
    for i in range(70):
        u = rng.random()
        yy = 80 + 860 * u
        half = 60 + 400 * u
        xx = 512 + rng.uniform(-half, half)
        ang = math.degrees(math.atan2(-(yy - 300), xx - 512)) + rng.normal(0, 20) - 90
        sp = fir_sprigs[rng.integers(0, 5)]
        cv.stamp(sp, (0.5, 0.95), (xx, yy), rng.uniform(260, 380) / sp.size[1], ang, flip=rng.random() < 0.5,
                 shade=0.65 + 0.35 * i / 69)
    S["conifer_mass"] = cv.sprite(0.25)

    # --- pine cluster: tufts radiating from the base (branch tip) upward/outward
    cv = Canvas(1024, 1024)
    tufts = [S["pine_a"], S["pine_b"]]
    for i in range(16):
        ang = rng.uniform(-70, 70)
        sp = tufts[0] if rng.random() < 0.7 else tufts[1]
        anc = (0.5, 0.98) if sp is tufts[0] else (0.02, 0.6)
        rot = ang if sp is tufts[0] else ang + 90
        L_ = rng.uniform(560, 760)
        cv.stamp(sp, anc, (512 + rng.normal(0, 20), 960), L_ / max(sp.size), rot, flip=rng.random() < 0.5,
                 shade=0.7 + 0.3 * i / 15)
    S["pine_cluster"] = cv.sprite(0.30)

    # --- birch twig: drooping twig with small serrated leaves
    cv = Canvas(1024, 1024)
    pts = [(80 + 860 * t, 90 + 820 * t ** 1.6) for t in np.linspace(0, 1, 30)]
    cv.line(pts, 7, 2, (0.30, 0.22, 0.17))
    for i in range(34):
        t = 0.05 + 0.93 * rng.random()
        x, y = pts[min(int(t * 29), 29)]
        side = 1 if rng.random() < 0.5 else -1
        sp = leaf_a if rng.random() < 0.6 else leaf_b
        ang = 180 + side * rng.uniform(15, 60)   # hanging leaves (tip down)
        cv.stamp(sp, (0.5, 0.97), (x, y), rng.uniform(150, 215) / sp.size[1], ang, flip=rng.random() < 0.5,
                 shade=0.75 + 0.25 * rng.random(), tint=(0.80, 0.90, 0.66))
    S["birch_twig"] = cv.sprite(0.6)

    # --- birch twig B: denser, shorter pendulous shoot (used by young birches / bushes)
    cv = Canvas(1024, 1024)
    for k in range(3):
        x0 = 300 + 220 * k
        pts = [(x0 + 120 * math.sin(t * 2 + k), 60 + 900 * t) for t in np.linspace(0, 1, 24)]
        cv.line(pts, 6, 2, (0.30, 0.22, 0.17))
        for i in range(14):
            t = 0.08 + 0.9 * rng.random()
            x, y = pts[min(int(t * 23), 23)]
            sp = leaf_a if rng.random() < 0.6 else leaf_b
            cv.stamp(sp, (0.5, 0.97), (x, y), rng.uniform(130, 190) / sp.size[1], 180 + rng.uniform(-70, 70),
                     flip=rng.random() < 0.5, shade=0.72 + 0.28 * rng.random(), tint=(0.80, 0.90, 0.66))
    S["leafy_branch"] = cv.sprite(0.6)

    # --- oak cluster: lobed leaves clustered at shoot ends
    cv = Canvas(1024, 1024)
    stems = [((512, 1000), (512 + rng.uniform(-260, 260), rng.uniform(260, 420))) for _ in range(5)]
    for a_, b_ in stems:
        cv.line([a_, ((a_[0] + b_[0]) / 2 + rng.normal(0, 30), (a_[1] + b_[1]) / 2), b_], 9, 4, (0.26, 0.21, 0.16))
    for i in range(30):
        a_, b_ = stems[i % 5]
        tip = (b_[0] + rng.normal(0, 40), b_[1] + rng.normal(0, 40))
        ang = math.degrees(math.atan2(-(tip[1] - 600), tip[0] - 512)) - 90 + rng.normal(0, 40)
        sp = oak_leaves[rng.integers(0, 3)]
        cv.stamp(sp, (0.5, 0.97), tip, rng.uniform(300, 420) / sp.size[1], ang, flip=rng.random() < 0.5,
                 shade=0.7 + 0.3 * i / 29, tint=(0.60, 0.74, 0.50))
    S["oak_cluster"] = cv.sprite(0.5)

    # --- generic broadleaf cluster (maple/linden/alder-like)
    cv = Canvas(1024, 1024)
    pts = [(512 + 40 * math.sin(t * 3), 1010 - 900 * t) for t in np.linspace(0, 1, 20)]
    cv.line(pts, 10, 3, (0.27, 0.22, 0.17))
    for i in range(24):
        t = 0.15 + 0.85 * rng.random()
        x, y = pts[min(int(t * 19), 19)]
        side = 1 if i % 2 == 0 else -1
        sp = leaf_a if rng.random() < 0.5 else leaf_b
        ang = side * rng.uniform(25, 80) + rng.normal(0, 8)
        cv.stamp(sp, (0.5, 0.97), (x, y), rng.uniform(260, 360) / sp.size[1], ang, flip=rng.random() < 0.5,
                 shade=0.72 + 0.28 * rng.random(), tint=(0.74, 0.86, 0.62))
    S["decid_cluster"] = cv.sprite(0.6)

    # ------------------------------------------------------------ pack the atlas
    # (name, target box w, h) in pixels; sprite is fit preserving aspect.
    plan = [
        ("fir_a", 1024, 1024), ("fir_b", 1024, 1024), ("spruce_branch", 1024, 1024), ("conifer_mass", 1024, 1024),
        ("pine_cluster", 1024, 1024), ("birch_twig", 1024, 1024), ("oak_cluster", 1024, 1024), ("decid_cluster", 1024, 1024),
        ("leafy_branch", 768, 1024), ("pine_a", 512, 1024), ("fir_d", 512, 512), ("fir_c", 512, 512),
        ("fern_0", 256, 1024), ("fern_1", 256, 1024), ("fern_3", 256, 1024), ("fern_2", 256, 768), ("fern_4", 256, 768),
        ("pine_b", 768, 512), ("grass_0", 768, 384), ("grass_1", 512, 256), ("grass_2", 512, 320), ("grass_3", 512, 256),
        ("grass_4", 512, 256), ("fir_e", 256, 256), ("moss_0", 192, 256), ("moss_1", 256, 384), ("moss_2", 256, 384),
        ("nettle_0", 256, 256), ("nettle_1", 256, 256), ("nettle_2", 256, 256), ("nettle_3", 256, 256),
        ("compound_leaf", 256, 512),
    ]
    A = 4096
    atlas = Canvas(A, A)
    rects = {}
    # shelf packer (tallest first), 8px gutter
    G = 8
    items = sorted(plan, key=lambda p: -p[2])
    x = y = shelf_h = 0
    for name, bw, bh in items:
        sp = S[name]
        sw, sh = sp.size
        sc = min(bw / sw, bh / sh)
        w, h = int(sw * sc), int(sh * sc)
        if x + w > A:
            x, y, shelf_h = 0, y + shelf_h + G, 0
        if y + h > A:
            raise RuntimeError("foliage atlas overflow at " + name)
        atlas.stamp(sp, (0.0, 0.0), (x, y), sc, 0.0)
        rects[name] = [x / A, y / A, w / A, h / A]
        x += w + G
        shelf_h = max(shelf_h, h)
    print("foliage atlas used height", y + shelf_h, "of", A)
    rgb = T.dilate_rgb(atlas.rgb, atlas.a)
    nrm = T.normalize_normal_rgb(atlas.n.copy())
    nrm = T.dilate_rgb(nrm, atlas.a)
    alb = np.concatenate([rgb, atlas.a[:, :, None]], axis=2)
    nr = np.concatenate([nrm[:, :, :2], atlas.r[:, :, None], atlas.t[:, :, None]], axis=2)
    p = os.path.join(OUT, "foliage", "foliage_albedo.webp")
    T.save(alb, p, quality=94); write_import(p, "tex", hq=True, normal_map=2)
    p = os.path.join(OUT, "foliage", "foliage_normal.webp")
    T.save(nr, p, quality=94); write_import(p, "tex", hq=True, normal_map=2)
    with open(os.path.join(OUT, "foliage", "foliage_atlas.json"), "w") as f:
        json.dump({"size": A, "rects": rects}, f, indent=1)
    print("wrote foliage atlas", len(rects), "regions")


# ----------------------------------------------------------- rock/prop atlases
def scan_atlas(name: str, items: list[tuple[str, str]]):
    """2x2 atlas of scanned-asset textures. items: (asset_id, material_name) -> also writes uv rects."""
    A, H = 4096, 2048
    alb = np.zeros((A, A, 4), np.float32)
    nr = np.zeros((A, A, 4), np.float32)
    rects = {}
    for i, (aid, mat) in enumerate(items):
        base = os.path.join(SRC, "models", aid, "textures")
        def f(kind):
            for fn in os.listdir(base):
                if fn.startswith(mat + "_" + kind):
                    return os.path.join(base, fn)
            return None
        diff = T.load(f("diff"), "RGB", (H, H))
        nor = T.load(f("nor_gl"), "RGB", (H, H))
        armp = f("arm")
        if armp:
            arm = T.load(armp, "RGB", (H, H)); rough, ao = arm[:, :, 1], arm[:, :, 0]
        else:
            rough = T.load(f("rough"), "L", (H, H))[:, :, 0]; ao = np.ones((H, H), np.float32)
        ox, oy = (i % 2) * H, (i // 2) * H
        alb[oy:oy + H, ox:ox + H, :3] = diff
        alb[oy:oy + H, ox:ox + H, 3] = ao
        nr[oy:oy + H, ox:ox + H, :2] = nor[:, :, :2]
        nr[oy:oy + H, ox:ox + H, 2] = rough
        nr[oy:oy + H, ox:ox + H, 3] = 1.0
        rects[aid] = [ox / A, oy / A, H / A, H / A]
    os.makedirs(os.path.join(OUT, name), exist_ok=True)
    p = os.path.join(OUT, name, f"{name}_albedo.webp"); T.save(alb, p, quality=92); write_import(p, "tex", hq=True)
    p = os.path.join(OUT, name, f"{name}_normal.webp"); T.save(nr, p, quality=93); write_import(p, "tex", hq=True)
    with open(os.path.join(OUT, name, f"{name}_atlas.json"), "w") as fp:
        json.dump({"size": A, "rects": rects}, fp, indent=1)
    print("wrote", name, "atlas")


def main(which: list[str]):
    steps = {
        "terrain": build_terrain, "road": build_road, "bark": build_bark, "foliage": compose_foliage,
        "rocks": lambda: scan_atlas("rocks", [("rock_moss_set_01", "rock_moss_set_01"), ("rock_moss_set_02", "rock_moss_set_02"),
                                              ("boulder_01", "boulder_01"), ("stone_01", "stone_01")]),
        "props": lambda: scan_atlas("props", [("tree_stump_01", "tree_stump_01"), ("tree_stump_02", "tree_stump_02"),
                                              ("dead_tree_trunk", "dead_tree_trunk"), ("dry_branches_medium_01", "dry_branches_medium_01")]),
    }
    for k in (which or list(steps)):
        steps[k]()


if __name__ == "__main__":
    main(sys.argv[1:])
