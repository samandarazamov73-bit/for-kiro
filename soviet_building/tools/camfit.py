"""Fit a pinhole camera to hand-picked reference-image correspondences (stdlib only)."""
import math, random

# (model X, Y, Z) -> (px, py) read from the 1024x572 reference image
PTS = [
    ((0, 0, 15.37), (190, 188)), ((0, 15, 15.37), (40, 152)),
    ((0, 0, 0), (210, 510)), ((0, 15, 0), (60, 410)),
    ((27, -18, 8.97), (870, 195)), ((39, -18, 8.97), (980, 165)),
    ((27, -18, 0), (870, 445)), ((39, -18, 0), (970, 380)),
    ((27, 0, 8.97), (585, 160)), ((75, 0, 15.37), (975, 45)),
]
CX, CY = 512, 286

def basis(yaw, pitch, roll):
    f = (math.cos(pitch) * math.cos(yaw), math.cos(pitch) * math.sin(yaw), math.sin(pitch))
    r = (math.sin(yaw), -math.cos(yaw), 0.0)
    u = (r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0])
    cr, sr = math.cos(roll), math.sin(roll)
    r2 = tuple(cr * a + sr * b for a, b in zip(r, u))
    u2 = tuple(-sr * a + cr * b for a, b in zip(r, u))
    return f, r2, u2

def err(p):
    x, y, z, yaw, pitch, roll, foc = p
    f, r, u = basis(yaw, pitch, roll)
    e = 0
    for P, (px, py) in PTS:
        d = (P[0] - x, P[1] - y, P[2] - z)
        zf = sum(a * b for a, b in zip(d, f))
        if zf <= 0.1:
            return 1e12
        sx = CX + foc * sum(a * b for a, b in zip(d, r)) / zf
        sy = CY - foc * sum(a * b for a, b in zip(d, u)) / zf
        e += (sx - px) ** 2 + (sy - py) ** 2
    return e

def nelder(p0, step, it=4000):
    n = len(p0)
    S = [list(p0)] + [[p0[j] + (step[j] if j == i else 0) for j in range(n)] for i in range(n)]
    F = [err(s) for s in S]
    for _ in range(it):
        o = sorted(range(n + 1), key=lambda i: F[i]); S = [S[i] for i in o]; F = [F[i] for i in o]
        c = [sum(S[i][j] for i in range(n)) / n for j in range(n)]
        xr = [c[j] + (c[j] - S[-1][j]) for j in range(n)]; fr = err(xr)
        if fr < F[0]:
            xe = [c[j] + 2 * (c[j] - S[-1][j]) for j in range(n)]; fe = err(xe)
            S[-1], F[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < F[-2]:
            S[-1], F[-1] = xr, fr
        else:
            xc = [c[j] + 0.5 * (S[-1][j] - c[j]) for j in range(n)]; fc = err(xc)
            if fc < F[-1]:
                S[-1], F[-1] = xc, fc
            else:
                S = [S[0]] + [[S[0][j] + 0.5 * (s[j] - S[0][j]) for j in range(n)] for s in S[1:]]
                F = [F[0]] + [err(s) for s in S[1:]]
    return S[0], F[0]

def main():
    best = None
    random.seed(3)
    for trial in range(60):
        p0 = [random.uniform(-60, 10), random.uniform(-80, -20), random.uniform(15, 60),
              random.uniform(0.0, 1.2), random.uniform(-0.8, -0.2), 0.0, random.uniform(600, 1600)]
        p, e = nelder(p0, [5, 5, 5, 0.1, 0.1, 0.02, 100])
        if best is None or e < best[1]:
            best = (p, e)
    p, e = best
    f, r, u = basis(p[3], p[4], p[5])
    print("rms px: %.1f" % math.sqrt(e / len(PTS)))
    print("cam pos: %.2f %.2f %.2f" % tuple(p[:3]))
    print("yaw %.3f pitch %.3f roll %.3f focal %.0f -> vfov %.1f deg" % (p[3], p[4], p[5], p[6], 2 * math.degrees(math.atan(286 / p[6]))))
    tgt = [p[i] + f[i] * 60 for i in range(3)]
    print("target (60 m ahead): %.2f %.2f %.2f" % tuple(tgt))
    print("up:", ["%.3f" % x for x in u])

    x, y, z = p[:3]
    for P, (px, py) in PTS:
        d = (P[0] - x, P[1] - y, P[2] - z)
        zf = sum(a * b for a, b in zip(d, f))
        sx = CX + p[6] * sum(a * b for a, b in zip(d, r)) / zf
        sy = CY - p[6] * sum(a * b for a, b in zip(d, u)) / zf
        print(P, "ref", (px, py), "model %.0f %.0f" % (sx, sy), "err %.0f %.0f" % (sx - px, sy - py))


if __name__ == "__main__":
    main()
