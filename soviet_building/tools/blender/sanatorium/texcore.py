"""Procedural texture helpers (numpy + Pillow). All noise is spectral, hence tileable."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT = "/usr/share/fonts/google-noto-vf/NotoSans[wght].ttf"


_FONTS = {}


def font(sz, weight="Regular"):
    """Noto Sans variable font; available named instances: Regular, Medium, SemiBold, Bold."""
    weight = {"Black": "Bold", "Heavy": "Bold"}.get(weight, weight)
    key = (int(sz), weight)
    if key not in _FONTS:
        f = ImageFont.truetype(FONT, int(sz))
        f.set_variation_by_name(weight)
        _FONTS[key] = f
    return _FONTS[key]


class RNG:
    def __init__(self, seed):
        self.r = np.random.default_rng(seed)


def spectral(h, w, beta, seed, lo=0.0):
    """Tileable fractal noise in [0, 1] with power spectrum 1/f^beta."""
    r = np.random.default_rng(seed)
    wn = r.standard_normal((h, w))
    F = np.fft.fft2(wn)
    fy = np.fft.fftfreq(h)[:, None] * h
    fx = np.fft.fftfreq(w)[None, :] * w
    f = np.sqrt(fx * fx + fy * fy)
    f[0, 0] = 1
    amp = 1.0 / f ** beta
    if lo:
        amp *= (f >= lo)
    amp[0, 0] = 0
    n = np.real(np.fft.ifft2(F * amp))
    n -= n.min()
    return n / (n.max() + 1e-9)


def blur(a, px):
    """Tileable gaussian blur via FFT."""
    h, w = a.shape[:2]
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    g = np.exp(-2 * (np.pi * px) ** 2 * (fx * fx + fy * fy))
    if a.ndim == 2:
        return np.real(np.fft.ifft2(np.fft.fft2(a) * g))
    return np.stack([np.real(np.fft.ifft2(np.fft.fft2(a[..., c]) * g)) for c in range(a.shape[2])], -1)


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0 + 1e-9), 0, 1)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    t = np.asarray(t)
    if np.ndim(a) and np.asarray(a).ndim == 1 and t.ndim == 2:
        t = t[..., None]
    elif t.ndim == 2 and np.ndim(b) == 3:
        t = t[..., None]
    return a + (b - a) * t


def col(hexstr):
    h = hexstr.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def mix_col(mask, base, c):
    """Blend a constant colour into base (H,W,3) with mask (H,W)."""
    return base * (1 - mask[..., None]) + np.asarray(c)[None, None, :] * mask[..., None]


def normal_from_height(h, strength):
    """OpenGL-convention normal map (+Y up), tileable."""
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * strength
    n = np.stack([-dx, dy, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


def cavity_ao(h, px=6, amount=1.5):
    d = h - blur(h, px)
    return np.clip(1 + d * amount, 0.45, 1.0)


def scratches(h, w, n, seed, length=(0.02, 0.15), width=1, angle=None, wrap=True):
    """Thin random lines as a float mask (tileable by drawing wrapped copies)."""
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed)
    for _ in range(n):
        x, y = r.uniform(0, w), r.uniform(0, h)
        a = r.uniform(0, np.pi) if angle is None else angle + r.normal(0, 0.15)
        L = r.uniform(*length) * w
        pts = [(x, y)]
        for k in range(4):
            a += r.normal(0, 0.12)
            x, y = x + np.cos(a) * L / 4, y + np.sin(a) * L / 4
            pts.append((x, y))
        v = int(r.uniform(90, 255))
        for ox in ((-w, 0, w) if wrap else (0,)):
            for oy in ((-h, 0, h) if wrap else (0,)):
                d.line([(p[0] + ox, p[1] + oy) for p in pts], fill=v, width=width)
    return np.asarray(im, np.float32) / 255.0


def cracks(h, w, n, seed, step=6, branch=0.25):
    """Branching hairline cracks (random walk polylines)."""
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed)

    def walk(x, y, a, steps, width):
        pts = [(x, y)]
        for _ in range(steps):
            a += r.normal(0, 0.35)
            x += np.cos(a) * step
            y += np.sin(a) * step
            pts.append((x, y))
            if r.random() < branch / 10 and steps > 8:
                walk(x, y, a + r.choice([-1, 1]) * r.uniform(0.5, 1.2), int(steps * 0.4), 1)
        for ox in (-w, 0, w):
            for oy in (-h, 0, h):
                d.line([(p[0] + ox, p[1] + oy) for p in pts], fill=255, width=width)

    for _ in range(n):
        walk(r.uniform(0, w), r.uniform(0, h), r.uniform(0, 2 * np.pi), int(r.uniform(20, 70)), 1)
    return np.asarray(im, np.float32) / 255.0


def blobs(h, w, n, seed, rmin, rmax, soft=0.6):
    """Soft irregular stains (tileable)."""
    base = spectral(h, w, 1.6, seed + 99)
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed)
    for _ in range(n):
        x, y, rad = r.uniform(0, w), r.uniform(0, h), r.uniform(rmin, rmax)
        v = int(r.uniform(120, 255))
        for ox in (-w, 0, w):
            for oy in (-h, 0, h):
                d.ellipse([x - rad + ox, y - rad * r.uniform(0.6, 1.4) + oy, x + rad + ox, y + rad + oy], fill=v)
    m = np.asarray(im, np.float32) / 255.0
    m = blur(m, (rmin + rmax) * 0.25 * soft)
    m = np.clip(m * (0.6 + 0.8 * base), 0, 1)
    return m


def to8(a):
    return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)


GRAIN = 0.05       # "new but grimy": fine film-grain noise and dust specks on every surface


def grain(base, rough, seed, amt=GRAIN, mask=None):
    """Tileable fine grain (near-white noise), soft mottling and sparse dark dust specks."""
    h, w = base.shape[:2]
    fine = spectral(h, w, 0.15, seed + 7001)
    mid = spectral(h, w, 1.3, seed + 7002)
    specks = (spectral(h, w, 0.05, seed + 7003) > 0.985).astype(float)
    k = np.ones((h, w)) if mask is None else mask
    f = 1 + k * (amt * (fine - 0.5) * 2 + amt * 0.8 * (mid - 0.5) - 0.18 * specks)
    base = base * f[..., None]
    rough = np.clip(np.asarray(rough) + k * 0.06 * (fine - 0.5), 0, 1) if np.ndim(rough) else rough
    return base, rough


def save_set(out_dir, name, base, rough, ao=None, height=None, nstrength=4.0, metal=None, alpha=None,
             normal=None, grain_amt=GRAIN):
    """Writes the project-convention PBR set: _BaseColor, _Normal (OpenGL), _ORM (R=AO G=rough B=metal),
    _Roughness, _AO (+ _Metallic when metal is given)."""
    os.makedirs(out_dir, exist_ok=True)
    h, w = base.shape[:2]
    if grain_amt:
        if np.ndim(rough) == 0:
            rough = np.full((h, w), float(rough))
        base, rough = grain(np.clip(base, 0, 1), rough, sum(map(ord, name)), grain_amt)
        base = np.clip(base, 0, 1)
    if ao is None:
        ao = cavity_ao(height) if height is not None else np.ones((h, w))
    if normal is None:
        normal = normal_from_height(height, nstrength) if height is not None else np.dstack(
            [np.full((h, w), .5), np.full((h, w), .5), np.ones((h, w))])
    m = np.zeros((h, w)) if metal is None else metal
    p = lambda s: os.path.join(out_dir, f"{name}_{s}.png")
    if alpha is not None:
        Image.fromarray(np.dstack([to8(base), to8(alpha)]), "RGBA").save(p("BaseColor"), optimize=True)
    else:
        Image.fromarray(to8(base), "RGB").save(p("BaseColor"), optimize=True)
    Image.fromarray(to8(normal), "RGB").save(p("Normal"), optimize=True)
    Image.fromarray(to8(np.dstack([ao, rough, m])), "RGB").save(p("ORM"), optimize=True)
    Image.fromarray(to8(rough), "L").save(p("Roughness"), optimize=True)
    Image.fromarray(to8(ao), "L").save(p("AO"), optimize=True)
    if metal is not None:
        Image.fromarray(to8(m), "L").save(p("Metallic"), optimize=True)
