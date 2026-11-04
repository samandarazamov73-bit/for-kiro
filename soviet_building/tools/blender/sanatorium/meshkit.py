"""Minimal mesh builder: collects polygons with per-corner UVs and material slots in plain
Python, then creates one bpy mesh. Keeps faces as quads/n-gons (triangulated on export)."""
import math
from .atlas import FURN_UV, DECAL_UV

FACES_ALL = ("-x", "+x", "-y", "+y", "-z", "+z")


class MB:
    def __init__(self, name):
        self.name = name
        self.v = []
        self.f = []
        self.uv = []
        self.mi = []
        self.mats = []
        self._mi = {}

    def _m(self, mat):
        if mat not in self._mi:
            self._mi[mat] = len(self.mats)
            self.mats.append(mat)
        return self._mi[mat]

    def poly(self, pts, uvs, mat):
        b = len(self.v)
        self.v.extend(tuple(map(float, p)) for p in pts)
        self.f.append(tuple(range(b, b + len(pts))))
        self.uv.extend(tuple(map(float, u)) for u in uvs)
        self.mi.append(self._m(mat))

    def poly_n(self, pts, uvs, mat, want):
        """Adds the polygon, reversing it if its normal points away from `want`."""
        n = newell(pts)
        if n[0] * want[0] + n[1] * want[1] + n[2] * want[2] < 0:
            pts, uvs = list(reversed(pts)), list(reversed(uvs))
        self.poly(pts, uvs, mat)

    def tris(self):
        return sum(len(f) - 2 for f in self.f)

    def extend(self, other, offset=(0, 0, 0)):
        for f, m in zip(other.f, other.mi):
            pts = [tuple(other.v[i][k] + offset[k] for k in range(3)) for i in f]
            uvs = [other.uv[i] for i in f]
            self.poly(pts, uvs, other.mats[m])

    def empty(self):
        return not self.f

    # ------------------------------------------------------------ primitives
    def quad_uvfn(self, pts, mat, uvfn):
        self.poly(pts, [uvfn(p) for p in pts], mat)

    def box(self, x0, x1, y0, y1, z0, z1, mat, faces=FACES_ALL, uv="world", scale=1.0, regions=None):
        """Axis-aligned box. uv: "world" (planar per face, metres/scale) or "region" (each face filled
        with an atlas region; regions maps face name -> region name, key "*" = default)."""
        P = {
            "-x": [(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)],
            "+x": [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
            "-y": [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
            "+y": [(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)],
            "-z": [(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)],
            "+z": [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
        }
        for fc in faces:
            pts = P[fc]
            if uv == "region":
                rn = (regions or {}).get(fc, (regions or {}).get("*"))
                m = mat
                if isinstance(rn, tuple):
                    m, rn = rn
                self.poly(pts, region_uv(rn, m), m)
            else:
                self.poly(pts, [planar_uv(p, fc, scale) for p in pts], mat)

    def tube(self, path, r, mat, sides=6, cap0=False, cap1=False, uvscale=1.0):
        """Polyline tube with mitre-free joints (ring per vertex, oriented on the averaged tangent)."""
        n = len(path)
        rings = []
        for i in range(n):
            if i == 0:
                t = sub(path[1], path[0])
            elif i == n - 1:
                t = sub(path[-1], path[-2])
            else:
                t = add(norm(sub(path[i], path[i - 1])), norm(sub(path[i + 1], path[i])))
            t = norm(t)
            up = (0, 0, 1) if abs(t[2]) < 0.9 else (1, 0, 0)
            a = norm(cross(t, up))
            b = cross(t, a)
            ring = []
            for k in range(sides):
                th = 2 * math.pi * k / sides
                ring.append(add(path[i], add(mul(a, r * math.cos(th)), mul(b, r * math.sin(th)))))
            rings.append(ring)
        L = 0.0
        for i in range(n - 1):
            seg = dist(path[i], path[i + 1])
            for k in range(sides):
                k2 = (k + 1) % sides
                p = [rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]]
                u0, u1 = k / sides, (k + 1) / sides
                self.poly(p, [(u0, L / uvscale), (u1, L / uvscale), (u1, (L + seg) / uvscale), (u0, (L + seg) / uvscale)], mat)
            L += seg
        if cap0:
            self.poly(list(reversed(rings[0])), [(0.5, 0.5)] * sides, mat)
        if cap1:
            self.poly(rings[-1], [(0.5, 0.5)] * sides, mat)

    def tube_region(self, path, r, region, sides=6, cap0=False, cap1=False, mat="atlas_furn"):
        """Tube whose UVs all sample one atlas region (ropes, rails, pipes)."""
        start = len(self.uv)
        self.tube(path, r, mat, sides, cap0, cap1)
        u0, v0, u1, v1 = (DECAL_UV if "decal" in mat else FURN_UV)[region]
        self.uv[start:] = [(u0 + (u1 - u0) * min(max(u, 0), 1), v0 + (v1 - v0) * (v % 1.0)) for (u, v) in self.uv[start:]]

    def cyl(self, cx, cy, z0, z1, r, mat, sides=8, top=True, bottom=False, region=None, axis="z"):
        rings = []
        for z in (z0, z1):
            ring = []
            for k in range(sides):
                th = 2 * math.pi * k / sides
                a, b = r * math.cos(th), r * math.sin(th)
                if axis == "z":
                    ring.append((cx + a, cy + b, z))
                elif axis == "x":
                    ring.append((z, cx + a, cy + b))
                else:
                    ring.append((cx + a, z, cy + b))
            rings.append(ring)
        uvr = FURN_UV.get(region) if region else None
        for k in range(sides):
            k2 = (k + 1) % sides
            p = [rings[0][k], rings[0][k2], rings[1][k2], rings[1][k]]
            if axis == "x":
                p = [rings[0][k2], rings[0][k], rings[1][k], rings[1][k2]]
            if uvr:
                u0, v0, u1, v1 = uvr
                a, b = u0 + (u1 - u0) * k / sides, u0 + (u1 - u0) * (k + 1) / sides
                uvs = [(a, v0), (b, v0), (b, v1), (a, v1)]
            else:
                uvs = [(k / sides * 2 * math.pi * r, z0), ((k + 1) / sides * 2 * math.pi * r, z0),
                       ((k + 1) / sides * 2 * math.pi * r, z1), (k / sides * 2 * math.pi * r, z1)]
            self.poly(p, uvs, mat)
        cen = lambda ring: [((uvr[0] + uvr[2]) / 2, (uvr[1] + uvr[3]) / 2)] * sides if uvr else [(0.5, 0.5)] * sides
        if top:
            ring = rings[1] if axis != "x" else list(reversed(rings[1]))
            self.poly(ring, cen(ring), mat)
        if bottom:
            ring = list(reversed(rings[0])) if axis != "x" else rings[0]
            self.poly(ring, cen(ring), mat)


# ---------------------------------------------------------------- uv helpers
def planar_uv(p, face, scale=1.0):
    """u points to the viewer's right when looking at the face from outside the box."""
    x, y, z = p
    if face == "-x":
        u, v = -y, z
    elif face == "+x":
        u, v = y, z
    elif face == "-y":
        u, v = x, z
    elif face == "+y":
        u, v = -x, z
    elif face == "+z":
        u, v = x, y
    else:
        u, v = x, -y
    return (u / scale, v / scale)


def region_uv(name, mat):
    """UVs filling an atlas region (counter-clockwise from bottom-left)."""
    table = DECAL_UV if "Decal" in mat else FURN_UV
    u0, v0, u1, v1 = table[name]
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def newell(pts):
    nx = ny = nz = 0.0
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        nx += (a[1] - b[1]) * (a[2] + b[2])
        ny += (a[2] - b[2]) * (a[0] + b[0])
        nz += (a[0] - b[0]) * (a[1] + b[1])
    return (nx, ny, nz)


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dist(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def norm(a):
    l = math.sqrt(sum(c * c for c in a)) or 1.0
    return (a[0] / l, a[1] / l, a[2] / l)


def subtract_rects(s0, s1, z0, z1, cuts):
    """Port of tools/cmd/build/wall.go Wall(): region minus holes -> list of (sa, sb, za, zb)."""
    eps = 1e-6
    zs = [z0, z1]
    for c in cuts:
        for z in (c[2], c[3]):
            if z0 + eps < z < z1 - eps:
                zs.append(z)
    zs = sorted(set(round(z, 6) for z in zs))
    out = []
    for k in range(len(zs) - 1):
        za, zb = zs[k], zs[k + 1]
        if zb - za < eps:
            continue
        iv = sorted((c[0], c[1]) for c in cuts if c[2] <= za + eps and c[3] >= zb - eps and c[1] > s0 and c[0] < s1)
        cur = s0
        for a, b in iv:
            if a - cur > eps:
                out.append((cur, min(a, s1), za, zb))
            cur = max(cur, b)
        if s1 - cur > eps:
            out.append((cur, s1, za, zb))
    # merge vertically adjacent strips with equal s-range (fewer quads)
    out.sort(key=lambda r: (round(r[0], 5), round(r[1], 5), r[2]))
    merged = []
    for r in out:
        if merged and abs(merged[-1][0] - r[0]) < eps and abs(merged[-1][1] - r[1]) < eps and abs(merged[-1][3] - r[2]) < eps:
            m = merged[-1]
            merged[-1] = (m[0], m[1], m[2], r[3])
        else:
            merged.append(r)
    return merged
