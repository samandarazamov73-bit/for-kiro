package main

import . "sovbuild/geo"

func edgeNormal(a, b Vec2) Vec2 {
	d := b.Sub(a)
	l := V3(d.U, d.V, 0).Len()
	return V2(d.V/l, -d.U/l)
}

// OffsetPoly offsets a CCW polygon/polyline outward by d with mitred corners.
func OffsetPoly(p []Vec2, d float64, closed bool) []Vec2 {
	n := len(p)
	out := make([]Vec2, n)
	for i := 0; i < n; i++ {
		hasPrev, hasNext := closed || i > 0, closed || i < n-1
		var np, nn Vec2
		if hasPrev {
			np = edgeNormal(p[(i-1+n)%n], p[i])
		}
		if hasNext {
			nn = edgeNormal(p[i], p[(i+1)%n])
		}
		if !hasPrev {
			np = nn
		}
		if !hasNext {
			nn = np
		}
		s := 1 + np.U*nn.U + np.V*nn.V
		out[i] = p[i].Add(np.Add(nn).Mul(d / s))
	}
	return out
}

func nEdges(p []Vec2, closed bool) int {
	if closed {
		return len(p)
	}
	return len(p) - 1
}

// RingWall adds vertical faces along polygon p offset by off; outward=true faces out.
func RingWall(m *Mesh, mat string, p []Vec2, closed bool, off, z0, z1 float64, outward bool, uv UVFn) {
	q := OffsetPoly(p, off, closed)
	for i := 0; i < nEdges(p, closed); i++ {
		a, b := q[i], q[(i+1)%len(q)]
		A0, B0 := V3(a.U, a.V, z0), V3(b.U, b.V, z0)
		A1, B1 := V3(a.U, a.V, z1), V3(b.U, b.V, z1)
		if outward {
			m.Quad(mat, A0, B0, B1, A1, uv)
		} else {
			m.Quad(mat, B0, A0, A1, B1, uv)
		}
	}
}

// RingFlat adds a horizontal ring between offsets offIn < offOut at height z.
func RingFlat(m *Mesh, mat string, p []Vec2, closed bool, offIn, offOut, z float64, up bool, uv UVFn) {
	qi, qo := OffsetPoly(p, offIn, closed), OffsetPoly(p, offOut, closed)
	for i := 0; i < nEdges(p, closed); i++ {
		j := (i + 1) % len(p)
		o0, o1 := V3(qo[i].U, qo[i].V, z), V3(qo[j].U, qo[j].V, z)
		i0, i1 := V3(qi[i].U, qi[i].V, z), V3(qi[j].U, qi[j].V, z)
		if up {
			m.Quad(mat, o0, o1, i1, i0, uv)
		} else {
			m.Quad(mat, i0, i1, o1, o0, uv)
		}
	}
}
