"""Image helpers for the Forest Drive texture pipeline (numpy + Pillow).

All images are handled as float32 numpy arrays in [0, 1], shape (H, W, C).
"""
from __future__ import annotations

import math
import os

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


# --------------------------------------------------------------------------- io
def load(path: str, mode: str = "RGB", size: tuple[int, int] | None = None) -> np.ndarray:
    im = Image.open(path).convert(mode)
    if size is not None and im.size != size:
        im = im.resize(size, Image.LANCZOS)
    a = np.asarray(im, dtype=np.float32) / 255.0
    if a.ndim == 2:
        a = a[:, :, None]
    return a


def to_pil(a: np.ndarray) -> Image.Image:
    a = np.clip(a, 0.0, 1.0)
    u8 = (a * 255.0 + 0.5).astype(np.uint8)
    if u8.shape[2] == 1:
        return Image.fromarray(u8[:, :, 0], "L")
    return Image.fromarray(u8, {3: "RGB", 4: "RGBA"}[u8.shape[2]])


def save(a: np.ndarray, path: str, quality: int = 92, lossless: bool = False) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im = to_pil(a)
    if path.endswith(".webp"):
        im.save(path, "WEBP", quality=quality, lossless=lossless, method=4, alpha_quality=100, exact=True)
    elif path.endswith(".png"):
        im.save(path, "PNG", optimize=True)
    else:
        im.save(path, quality=quality)


def resize(a: np.ndarray, w: int, h: int) -> np.ndarray:
    if a.shape[1] == w and a.shape[0] == h:
        return a
    chans = []
    for c in range(a.shape[2]):
        im = Image.fromarray(a[:, :, c].astype(np.float32), "F").resize((w, h), Image.LANCZOS)
        chans.append(np.asarray(im, dtype=np.float32))
    return np.clip(np.stack(chans, axis=2), 0.0, 1.0)


# ------------------------------------------------------------------------ noise
def fft_noise(size: int, beta: float = 2.0, seed: int = 0, lo: float = 1.0, hi: float | None = None,
              aspect: tuple[float, float] = (1.0, 1.0)) -> np.ndarray:
    """Tileable power-law noise (1/f^beta spectrum) normalised to [0, 1].

    aspect stretches frequencies: (fx_scale, fy_scale) > 1 compresses features along that axis.
    """
    rng = np.random.default_rng(seed)
    fy = np.fft.fftfreq(size)[:, None] * size * aspect[1]
    fx = np.fft.fftfreq(size)[None, :] * size * aspect[0]
    f = np.sqrt(fx * fx + fy * fy)
    amp = np.zeros_like(f)
    m = f >= lo
    if hi is not None:
        m &= f <= hi
    amp[m] = 1.0 / np.power(f[m], beta / 2.0)
    phase = rng.uniform(0, 2 * np.pi, f.shape)
    spec = amp * np.exp(1j * phase)
    n = np.real(np.fft.ifft2(spec)).astype(np.float32)
    n -= n.min()
    n /= max(n.max(), 1e-9)
    return n


def blur_wrap(a: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian blur with wrap-around (FFT), keeps tileability. a: (H, W) or (H, W, C)."""
    two_d = a.ndim == 2
    if two_d:
        a = a[:, :, None]
    h, w = a.shape[:2]
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    g = np.exp(-2 * (np.pi ** 2) * (sigma ** 2) * (fx * fx + fy * fy))
    out = np.empty_like(a)
    for c in range(a.shape[2]):
        out[:, :, c] = np.real(np.fft.ifft2(np.fft.fft2(a[:, :, c]) * g))
    return out[:, :, 0] if two_d else out


def height_to_normal(h: np.ndarray, strength: float) -> np.ndarray:
    """Tileable height (H, W) -> OpenGL-convention normal map RGB in [0, 1]."""
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5 * strength
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5 * strength
    # image y grows downward; OpenGL normal maps have +Y up
    n = np.stack([-dx, dy, np.ones_like(h)], axis=2)
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * 0.5 + 0.5


# ------------------------------------------------------------------------ alpha
def dilate_rgb(rgb: np.ndarray, alpha: np.ndarray, levels: int = 9) -> np.ndarray:
    """Push-pull fill of colour into transparent texels (prevents dark/coloured fringes in mips)."""
    a = (alpha[:, :, 0] if alpha.ndim == 3 else alpha) > 0.5
    pyr = [(rgb * a[:, :, None], a.astype(np.float32))]
    for _ in range(levels):
        c, w = pyr[-1]
        h2, w2 = c.shape[0] // 2, c.shape[1] // 2
        if h2 < 2 or w2 < 2:
            break
        c = c[: h2 * 2, : w2 * 2].reshape(h2, 2, w2, 2, -1).sum(axis=(1, 3))
        w = w[: h2 * 2, : w2 * 2].reshape(h2, 2, w2, 2).sum(axis=(1, 3))
        pyr.append((c, w))
    # pull: fill holes from coarser levels
    fill_c, fill_w = pyr[-1]
    fill = fill_c / np.maximum(fill_w[:, :, None], 1e-6)
    for c, w in reversed(pyr[:-1]):
        up = np.repeat(np.repeat(fill, 2, axis=0), 2, axis=1)
        up = np.pad(up, ((0, c.shape[0] - up.shape[0]), (0, c.shape[1] - up.shape[1]), (0, 0)), mode="edge")
        own = c / np.maximum(w[:, :, None], 1e-6)
        fill = np.where(w[:, :, None] > 0, own, up)
    out = rgb.copy()
    out[~a] = fill[~a]
    return out


# -------------------------------------------------------------------- normals
def rotate_normal_rgb(n_rgb: np.ndarray, angle_deg: float, flip_x: bool = False) -> np.ndarray:
    """Rotate tangent-space normal vectors to match an image rotated by angle_deg (CCW)."""
    n = n_rgb * 2.0 - 1.0
    x, y, z = n[:, :, 0], n[:, :, 1], n[:, :, 2]
    if flip_x:
        x = -x
    t = math.radians(angle_deg)
    c, s = math.cos(t), math.sin(t)
    xr = x * c - y * s
    yr = x * s + y * c
    return np.stack([xr, yr, z], axis=2) * 0.5 + 0.5


def normalize_normal_rgb(n_rgb: np.ndarray) -> np.ndarray:
    n = n_rgb * 2.0 - 1.0
    n[:, :, 2] = np.maximum(n[:, :, 2], 0.05)
    n /= np.maximum(np.linalg.norm(n, axis=2, keepdims=True), 1e-6)
    return n * 0.5 + 0.5


def luminance(rgb: np.ndarray) -> np.ndarray:
    return rgb[:, :, 0] * 0.2126 + rgb[:, :, 1] * 0.7152 + rgb[:, :, 2] * 0.0722


def srgb_to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def match_mean(rgb: np.ndarray, target_srgb: tuple[float, float, float], strength: float = 1.0) -> np.ndarray:
    """Shift colour balance so the mean (linear) colour approaches target (given in sRGB)."""
    lin = srgb_to_lin(rgb)
    mean = lin.reshape(-1, 3).mean(axis=0)
    tgt = srgb_to_lin(np.array(target_srgb, dtype=np.float32))
    gain = (tgt / np.maximum(mean, 1e-4)) ** strength
    return lin_to_srgb(lin * gain[None, None, :]).astype(np.float32)
