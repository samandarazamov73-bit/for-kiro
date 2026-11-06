"""Grime textures for the sanatorium game: multiply masks (white = untouched) laid over walls, ceilings
and floors in world space by scripts/game.gd (StandardMaterial3D detail texture, world triplanar UV2).

The wall mask is one storey high (3.3 m, the floor-to-floor height) and is aligned to the floors, so its
bottom rows always sit at floor level and its top rows under the ceiling. That lets the dirt follow
causes instead of being sprinkled evenly: a dirty band and scuffs at the bottom of the walls, water
stains with dark tide marks coming down from the ceiling with drips below them, a dusty line under the
ceiling, and old, slightly uneven paint in between. Ceilings get a few yellowed leak stains, floors a
faint unevenness. Everything tiles horizontally.

    python grime_gen.py [--out ../game/assets]
"""
import argparse
import os

import numpy as np
from PIL import Image

RNG = np.random.default_rng(1975)
STOREY = 3.3          # floor to floor, metres (texture height of the wall mask)
CEILING = 3.0         # rooms are 3 m high; above that is the slab


def periodic_noise(h, w, sigma_px, rng=RNG):
    """Smooth noise in [0, 1] that tiles in both directions (Gaussian-filtered white noise, via FFT)."""
    white = rng.standard_normal((h, w))
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    g = np.exp(-2 * (np.pi * sigma_px) ** 2 * (fx ** 2 + fy ** 2))
    n = np.real(np.fft.ifft2(np.fft.fft2(white) * g))
    n -= n.min()
    return n / max(n.max(), 1e-9)


def fractal(h, w, sigmas, gains, rng=RNG):
    out = np.zeros((h, w))
    for s, g in zip(sigmas, gains):
        out += g * (periodic_noise(h, w, s, rng) - 0.5)
    return out


def stain(mask_rgb, cx, cy, rx, ry, xs, ys, body, ring, rng, wrap_w):
    """A leak stain: an irregular patch, faint in the middle and darker towards its edge, bounded by a thin
    brown tide mark, with fainter rings of older leaks inside."""
    h, w = mask_rgb.shape[:2]
    dx = (xs - cx + wrap_w / 2) % wrap_w - wrap_w / 2      # wrap horizontally
    dy = ys - cy
    r = min(rx, ry)
    edge = 0.75 * (periodic_noise(h, w, max(3.0, r / 4.5), rng) - 0.5) \
        + 0.4 * (periodic_noise(h, w, max(1.5, r / 14.0), rng) - 0.5)
    f = np.sqrt((dx / rx) ** 2 + (dy / ry) ** 2) + 0.9 * edge
    inside = np.clip((1.0 - f) / 0.08, 0.0, 1.0) * (0.3 + 0.7 * np.clip(f, 0.0, 1.0) ** 2)
    rings = np.exp(-((f - 1.0) / 0.022) ** 2) + 0.45 * np.exp(-((f - 0.8) / 0.02) ** 2) \
        + 0.25 * np.exp(-((f - 0.6) / 0.02) ** 2)
    for c in range(3):
        mask_rgb[..., c] *= 1.0 - inside * (1.0 - body[c])
        mask_rgb[..., c] *= 1.0 - np.clip(rings, 0, 1) * (1.0 - ring[c])
    return f


def wall(width_m=12.0, w=1536, h=512):
    """Rows: top = 3.3 m above the floor, bottom = the floor."""
    m = np.ones((h, w, 3))
    ys, xs = np.mgrid[0:h, 0:w].astype(float)
    height = (1.0 - (ys + 0.5) / h) * STOREY                  # metres above the floor
    px_m = w / width_m
    # old paint: faintly uneven, slightly yellowed in places
    paint = fractal(h, w, [90, 30, 8], [1.0, 0.5, 0.25])
    m *= (1.0 - 0.1 * np.clip(paint + 0.5, 0, 1))[..., None] * np.array([1.0, 0.99, 0.96])
    # dirty band at the bottom: floor washing, shoes, wheels; its upper edge wanders
    top = 0.4 + 0.16 * (periodic_noise(h, w, 60)[0][None, :] - 0.5)
    band = np.clip(1.0 - height / top, 0.0, 1.0) ** 1.5
    band *= 0.7 + 0.6 * periodic_noise(h, w, 20)
    m *= 1.0 - band[..., None] * 0.42 * np.array([1.0, 1.06, 1.18])
    # scuffs: long soft smudges where chairs, trolleys and wheelchairs rubbed the wall
    for _ in range(9):
        cx, cy = RNG.uniform(0, w), h * (1.0 - RNG.uniform(0.08, 0.4) / STOREY)
        rx, ry = RNG.uniform(0.25, 0.8) * px_m, RNG.uniform(0.015, 0.05) * px_m
        dx = (xs - cx + w / 2) % w - w / 2
        s = np.exp(-((dx / rx) ** 2 + ((ys - cy) / ry) ** 2)) * RNG.uniform(0.06, 0.14)
        m *= 1.0 - s[..., None] * np.array([1.0, 1.05, 1.15])
    # dusty line under the ceiling
    dust = np.exp(-((height - CEILING + 0.05) / 0.12) ** 2) * 0.07
    m *= 1.0 - dust[..., None]
    # leaks from above: stains hanging from the ceiling line, with drips running down from them
    ceil_y = h * (1.0 - CEILING / STOREY)
    for k in range(4):
        cx = (k + RNG.uniform(0.2, 0.8)) * w / 4
        rx, ry = RNG.uniform(0.3, 0.75) * px_m, RNG.uniform(0.3, 0.8) * px_m
        cy = ceil_y - ry * RNG.uniform(0.0, 0.3)       # it comes out of the ceiling: only the lower part shows
        body = (0.9, 0.84, 0.68)
        ring = (0.66, 0.54, 0.38)
        stain(m, cx, cy, rx, ry, xs, ys, body, ring, RNG, w)
        for _ in range(RNG.integers(2, 6)):
            x0 = cx + RNG.uniform(-0.8, 0.8) * rx
            y0 = cy + ry * RNG.uniform(0.3, 0.8)
            length = RNG.uniform(0.25, 1.4) * px_m
            width = RNG.uniform(0.006, 0.02) * px_m
            dx = (xs - x0 + w / 2) % w - w / 2
            t = (ys - y0) / length
            drip = np.exp(-(dx / width) ** 2) * np.clip(1.0 - t, 0, 1) * (t > 0) * RNG.uniform(0.14, 0.26)
            m *= 1.0 - drip[..., None] * np.array([1.0, 1.1, 1.35])
    return np.clip(m, 0, 1)


def ceiling(size=1024):
    m = np.ones((size, size, 3))
    ys, xs = np.mgrid[0:size, 0:size].astype(float)
    m *= (1.0 - 0.05 * np.clip(fractal(size, size, [120, 40], [1.0, 0.4]) + 0.5, 0, 1))[..., None]
    for _ in range(2):
        cx, cy = RNG.uniform(0, size), RNG.uniform(0, size)
        r = RNG.uniform(0.05, 0.11) * size
        stain(m, cx, cy, r, r * RNG.uniform(0.6, 1.1), xs, (ys - cy + size / 2) % size - size / 2 + cy,
              (0.92, 0.86, 0.72), (0.68, 0.56, 0.4), RNG, size)
    return np.clip(m, 0, 1)


def floor(size=1024):
    m = np.ones((size, size, 3))
    n = fractal(size, size, [140, 45, 12], [1.0, 0.6, 0.3])
    m *= (1.0 - 0.16 * np.clip(n + 0.5, 0, 1))[..., None] * np.array([1.0, 0.985, 0.95])
    specks = periodic_noise(size, size, 1.2)
    m *= 1.0 - (np.clip((specks - 0.82) / 0.18, 0, 1) * 0.25)[..., None]
    return np.clip(m, 0, 1)


def save(arr, path):
    Image.fromarray((arr * 255 + 0.5).astype(np.uint8), "RGB").save(path, optimize=True)
    print(path, arr.shape[1], "x", arr.shape[0])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "game", "assets"))
    a = ap.parse_args()
    save(wall(), os.path.join(a.out, "grime_wall.png"))
    save(ceiling(), os.path.join(a.out, "grime_ceiling.png"))
    save(floor(), os.path.join(a.out, "grime_floor.png"))
