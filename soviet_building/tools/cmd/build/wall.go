package main

import (
	"sort"

	. "sovbuild/geo"
)

// Plane is a vertical facade plane: world = O + U*s + Z*z + N*d, N = U x Z (outward).
type Plane struct{ O, U, N Vec3 }

func NewPlane(o, u Vec3) Plane { return Plane{o, u, u.Cross(V3(0, 0, 1))} }

func (p Plane) At(s, z, d float64) Vec3 {
	return p.O.Add(p.U.Mul(s)).Add(V3(0, 0, z)).Add(p.N.Mul(d))
}

// Rect is a rectangle in plane coordinates.
type Rect struct{ S0, S1, Z0, Z1 float64 }

const eps = 1e-6

// Wall emits region [s0,s1]x[z0,z1] at depth d minus the holes (quads only).
func Wall(m *Mesh, mat string, pl Plane, s0, s1, z0, z1, d float64, holes []Rect, uv UVFn) {
	zs := []float64{z0, z1}
	for _, h := range holes {
		for _, z := range []float64{h.Z0, h.Z1} {
			if z > z0+eps && z < z1-eps {
				zs = append(zs, z)
			}
		}
	}
	sort.Float64s(zs)
	for k := 0; k+1 < len(zs); k++ {
		za, zb := zs[k], zs[k+1]
		if zb-za < eps {
			continue
		}
		var iv [][2]float64
		for _, h := range holes {
			if h.Z0 <= za+eps && h.Z1 >= zb-eps && h.S1 > s0 && h.S0 < s1 {
				iv = append(iv, [2]float64{h.S0, h.S1})
			}
		}
		sort.Slice(iv, func(i, j int) bool { return iv[i][0] < iv[j][0] })
		cur := s0
		emit := func(a, b float64) {
			if b-a > eps {
				m.Quad(mat, pl.At(a, za, d), pl.At(b, za, d), pl.At(b, zb, d), pl.At(a, zb, d), uv)
			}
		}
		for _, h := range iv {
			emit(cur, h[0])
			if h[1] > cur {
				cur = h[1]
			}
		}
		emit(cur, s1)
	}
}
