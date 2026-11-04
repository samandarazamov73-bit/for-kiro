"""Joint fit: camera + entrance block / main wing proportions to reference correspondences."""
import math, random
from camfit import basis, nelder, CX, CY
import camfit

TOP = 15.37  # main wing parapet top (fixed: sets the metric scale)

def points(s):
    Dm, X0, X1, D, H = s
    return [
        ((0, 0, TOP), (190, 188)), ((0, Dm, TOP), (40, 152)),
        ((0, 0, 0), (210, 510)), ((0, Dm, 0), (60, 410)),
        ((75, 0, TOP), (975, 45)),
        ((X0, 0, H), (585, 160)), ((X0, -D, H), (870, 195)), ((X1, -D, H), (980, 165)),
        ((X0, -D, 0), (870, 445)), ((X1, -D, 0), (970, 380)), ((X1, 0, H), (695, 133)),
    ]

def proj(p, P):
    x, y, z, yaw, pitch, roll, foc = p[:7]
    f, r, u = basis(yaw, pitch, roll)
    d = (P[0] - x, P[1] - y, P[2] - z)
    zf = sum(a * b for a, b in zip(d, f))
    if zf <= 0.1:
        return None
    return (CX + foc * sum(a * b for a, b in zip(d, r)) / zf, CY - foc * sum(a * b for a, b in zip(d, u)) / zf)

def err(p):
    e = 0
    for P, q in points(p[7:]):
        s = proj(p, P)
        if s is None:
            return 1e12
        e += (s[0] - q[0]) ** 2 + (s[1] - q[1]) ** 2
    # weak priors keep the shape plausible
    Dm, X0, X1, D, H = p[7:]
    e += 4 * ((Dm - 15) ** 2) + 2 * ((X1 - X0 - 12) ** 2)
    return e

camfit.err = err
best = None
random.seed(5)
for trial in range(80):
    p0 = [random.uniform(-60, 10), random.uniform(-80, -20), random.uniform(15, 60),
          random.uniform(0.3, 1.2), random.uniform(-0.7, -0.15), 0.0, random.uniform(700, 1700),
          15, 27, 39, random.uniform(14, 26), random.uniform(8, 14)]
    p, e = nelder(p0, [5, 5, 5, 0.1, 0.1, 0.02, 100, 1, 2, 2, 2, 1], it=6000)
    if best is None or e < best[1]:
        best = (p, e)
p, e = best
print("err %.0f" % e)
print("cam pos %.2f %.2f %.2f yaw %.3f pitch %.3f roll %.3f focal %.0f vfov %.1f" % (*p[:6], p[6], 2 * math.degrees(math.atan(286 / p[6]))))
print("Dm %.2f EntX0 %.2f EntX1 %.2f EntDepth %.2f EntTop %.2f" % tuple(p[7:]))
f, r, u = basis(p[3], p[4], p[5])
print("target %.2f %.2f %.2f" % tuple(p[i] + f[i] * 60 for i in range(3)))
for P, q in points(p[7:]):
    s = proj(p, P)
    print(tuple(round(c, 1) for c in P), q, "-> %.0f %.0f" % s)
