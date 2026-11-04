package main

import . "sovbuild/geo"

// WinSpec describes a precast window surround with a recessed framed glazing unit.
type WinSpec struct {
	W, H     float64   // surround outer size (sill included)
	Side     float64   // side/top member width
	SillH    float64   // sill member height
	Proj     float64   // surround projection from the wall plane
	SillProj float64   // sill projection
	SillExt  float64   // sill extension beyond the surround on each side
	Recess   float64   // glass plane behind the wall plane
	Slope    float64   // sill top rise from the front edge to the glass
	Cols     []float64 // mullion positions (fractions of frame interior width)
	Rows     []float64 // transom positions (fractions of frame interior height)
	FW, FD   float64   // frame profile width, frame depth in front of glass
}

// Hole returns the wall opening needed by a window centred at sc with bottom zb.
func (w WinSpec) Hole(sc, zb float64) Rect {
	return Rect{sc - w.W/2, sc + w.W/2, zb + w.SillH, zb + w.H}
}

// WinMeshes collects the window parts (separate objects in the hierarchy).
type WinMeshes struct{ Surround, Frame, Glass *Mesh }

func NewWinMeshes(prefix string) WinMeshes {
	return WinMeshes{NewMesh(prefix + "_Surrounds"), NewMesh(prefix + "_Frames"), NewMesh(prefix + "_Glass")}
}

var uvTrim = WorldUV(2, 2, 0, 0)
var uvFrame = WorldUV(1.2, 1.2, 0, 0)

// quadP adds a quad from plane coordinates (s,z,d) triples.
func quadP(m *Mesh, mat string, pl Plane, uv UVFn, pts ...[3]float64) {
	ps := make([]Vec3, len(pts))
	for i, p := range pts {
		ps[i] = pl.At(p[0], p[1], p[2])
	}
	m.Poly(mat, ps, uv)
}

// Axis aligned faces in plane coordinates (s right, z up, d outward).
func fD(m *Mesh, mt string, pl Plane, uv UVFn, s0, s1, z0, z1, d float64) {
	quadP(m, mt, pl, uv, [3]float64{s0, z0, d}, [3]float64{s1, z0, d}, [3]float64{s1, z1, d}, [3]float64{s0, z1, d})
}
func fSp(m *Mesh, mt string, pl Plane, uv UVFn, s, z0, z1, d0, d1 float64) {
	quadP(m, mt, pl, uv, [3]float64{s, z0, d0}, [3]float64{s, z1, d0}, [3]float64{s, z1, d1}, [3]float64{s, z0, d1})
}
func fSn(m *Mesh, mt string, pl Plane, uv UVFn, s, z0, z1, d0, d1 float64) {
	quadP(m, mt, pl, uv, [3]float64{s, z0, d0}, [3]float64{s, z0, d1}, [3]float64{s, z1, d1}, [3]float64{s, z1, d0})
}
func fZp(m *Mesh, mt string, pl Plane, uv UVFn, z, s0, s1, d0, d1 float64) {
	quadP(m, mt, pl, uv, [3]float64{s0, z, d0}, [3]float64{s0, z, d1}, [3]float64{s1, z, d1}, [3]float64{s1, z, d0})
}
func fZn(m *Mesh, mt string, pl Plane, uv UVFn, z, s0, s1, d0, d1 float64) {
	quadP(m, mt, pl, uv, [3]float64{s0, z, d0}, [3]float64{s1, z, d0}, [3]float64{s1, z, d1}, [3]float64{s0, z, d1})
}

// Surround builds the precast concrete window box with a sloped projecting sill.
func (w WinSpec) Surround(m *Mesh, pl Plane, sc, zb float64) {
	a0, a1 := sc-w.W/2, sc+w.W/2
	b0, b1 := zb, zb+w.H
	i0, i1 := a0+w.Side, a1-w.Side
	j0, j1 := zb+w.SillH, b1-w.Side
	P, R, SP := w.Proj, -w.Recess, w.SillProj
	zt := func(d float64) float64 { return j0 + w.Slope*(SP-d)/(SP-R) }
	e0, e1 := a0-w.SillExt, a1+w.SillExt
	// sill: sloped top (3 parts), front, ends, underside
	quadP(m, MTrim, pl, uvTrim, [3]float64{i0, zt(R), R}, [3]float64{i0, zt(SP), SP}, [3]float64{i1, zt(SP), SP}, [3]float64{i1, zt(R), R})
	quadP(m, MTrim, pl, uvTrim, [3]float64{e0, zt(0), 0}, [3]float64{e0, zt(SP), SP}, [3]float64{i0, zt(SP), SP}, [3]float64{i0, zt(0), 0})
	quadP(m, MTrim, pl, uvTrim, [3]float64{i1, zt(0), 0}, [3]float64{i1, zt(SP), SP}, [3]float64{e1, zt(SP), SP}, [3]float64{e1, zt(0), 0})
	fD(m, MTrim, pl, uvTrim, e0, e1, b0, j0, SP)
	quadP(m, MTrim, pl, uvTrim, [3]float64{e0, b0, 0}, [3]float64{e0, b0, SP}, [3]float64{e0, j0, SP}, [3]float64{e0, zt(0), 0})
	quadP(m, MTrim, pl, uvTrim, [3]float64{e1, b0, 0}, [3]float64{e1, zt(0), 0}, [3]float64{e1, j0, SP}, [3]float64{e1, b0, SP})
	fZn(m, MTrim, pl, uvTrim, b0, e0, e1, 0, SP)
	// side and top members: fronts, outer faces (25 mm chamfer on the outer front edges), reveals, soffit
	c := 0.025
	fD(m, MTrim, pl, uvTrim, a0+c, i0, j0, b1-c, P)
	fD(m, MTrim, pl, uvTrim, i1, a1-c, j0, b1-c, P)
	fD(m, MTrim, pl, uvTrim, i0, i1, j1, b1-c, P)
	fSn(m, MTrim, pl, uvTrim, a0, j0, b1, 0, P-c)
	fSp(m, MTrim, pl, uvTrim, a1, j0, b1, 0, P-c)
	fZp(m, MTrim, pl, uvTrim, b1, a0, a1, 0, P-c)
	h := b1 - c
	quadP(m, MTrim, pl, uvTrim, [3]float64{a0, j0, P - c}, [3]float64{a0 + c, j0, P}, [3]float64{a0 + c, h, P}, [3]float64{a0, h, P - c})
	quadP(m, MTrim, pl, uvTrim, [3]float64{a1 - c, j0, P}, [3]float64{a1, j0, P - c}, [3]float64{a1, h, P - c}, [3]float64{a1 - c, h, P})
	quadP(m, MTrim, pl, uvTrim, [3]float64{a0 + c, h, P}, [3]float64{a1 - c, h, P}, [3]float64{a1 - c, b1, P - c}, [3]float64{a0 + c, b1, P - c})
	tri := func(p ...[3]float64) { quadP(m, MTrim, pl, uvTrim, p...) }
	tri([3]float64{a0, b1, P - c}, [3]float64{a0, h, P - c}, [3]float64{a0 + c, h, P})
	tri([3]float64{a0, b1, P - c}, [3]float64{a0 + c, h, P}, [3]float64{a0 + c, b1, P - c})
	tri([3]float64{a1, b1, P - c}, [3]float64{a1 - c, h, P}, [3]float64{a1, h, P - c})
	tri([3]float64{a1, b1, P - c}, [3]float64{a1 - c, b1, P - c}, [3]float64{a1 - c, h, P})
	quadP(m, MTrim, pl, uvTrim, [3]float64{i0, zt(R), R}, [3]float64{i0, j1, R}, [3]float64{i0, j1, P}, [3]float64{i0, zt(P), P})
	quadP(m, MTrim, pl, uvTrim, [3]float64{i1, zt(R), R}, [3]float64{i1, zt(P), P}, [3]float64{i1, j1, P}, [3]float64{i1, j1, R})
	fZn(m, MTrim, pl, uvTrim, j1, i0, i1, R, P)
}

// Glazing builds the window frame grid (mullions/transoms) and the glass pane.
// cell selects the interior variant in the 4x4 glass atlas.
func (w WinSpec) Glazing(fr, gl *Mesh, pl Plane, sc, zb float64, cell int) {
	i0, i1 := sc-w.W/2+w.Side, sc+w.W/2-w.Side
	jg := zb + w.SillH + w.Slope
	j1 := zb + w.H - w.Side
	R := -w.Recess
	F := R + w.FD
	fw := w.FW
	// glass with atlas cell UVs
	cu, cv := float64(cell%4)*0.25, float64(cell/4)*0.25
	gp := []Vec3{pl.At(i0, jg, R), pl.At(i1, jg, R), pl.At(i1, j1, R), pl.At(i0, j1, R)}
	gl.PolyUV(MGlass, gp, []Vec2{V2(cu+0.01, cv+0.01), V2(cu+0.24, cv+0.01), V2(cu+0.24, cv+0.24), V2(cu+0.01, cv+0.24)})
	// interior bounds of the outer frame
	x0, x1, y0, y1 := i0+fw, i1-fw, jg+fw, j1-fw
	fD(fr, MFrame, pl, uvFrame, i0, x0, jg, j1, F)
	fD(fr, MFrame, pl, uvFrame, x1, i1, jg, j1, F)
	fD(fr, MFrame, pl, uvFrame, x0, x1, jg, y0, F)
	fD(fr, MFrame, pl, uvFrame, x0, x1, y1, j1, F)
	fSp(fr, MFrame, pl, uvFrame, x0, y0, y1, R, F)
	fSn(fr, MFrame, pl, uvFrame, x1, y0, y1, R, F)
	fZp(fr, MFrame, pl, uvFrame, y0, x0, x1, R, F)
	fZn(fr, MFrame, pl, uvFrame, y1, x0, x1, R, F)
	// mullions (full interior height)
	mw := fw * 0.85
	var ms [][2]float64 // occupied s-intervals for transom splitting
	for _, c := range w.Cols {
		s := x0 + c*(x1-x0)
		ms = append(ms, [2]float64{s - mw/2, s + mw/2})
		fD(fr, MFrame, pl, uvFrame, s-mw/2, s+mw/2, y0, y1, F)
		fSn(fr, MFrame, pl, uvFrame, s-mw/2, y0, y1, R, F)
		fSp(fr, MFrame, pl, uvFrame, s+mw/2, y0, y1, R, F)
	}
	// opening sashes: a slimmer frame ring set 12 mm behind the main frame in every pane
	cols := [][2]float64{}
	cur0 := x0
	for _, m := range ms {
		cols = append(cols, [2]float64{cur0, m[0]})
		cur0 = m[1]
	}
	cols = append(cols, [2]float64{cur0, x1})
	rows := [][2]float64{}
	cz := y0
	for _, r := range w.Rows {
		z := y0 + r*(y1-y0)
		rows = append(rows, [2]float64{cz, z - mw/2})
		cz = z + mw/2
	}
	rows = append(rows, [2]float64{cz, y1})
	sw, Fs := 0.042, F-0.012
	for _, c := range cols {
		for _, r := range rows {
			pa, pb, qa, qb := c[0], c[1], r[0], r[1]
			fD(fr, MFrame, pl, uvFrame, pa, pa+sw, qa, qb, Fs)
			fD(fr, MFrame, pl, uvFrame, pb-sw, pb, qa, qb, Fs)
			fD(fr, MFrame, pl, uvFrame, pa+sw, pb-sw, qa, qa+sw, Fs)
			fD(fr, MFrame, pl, uvFrame, pa+sw, pb-sw, qb-sw, qb, Fs)
			fSp(fr, MFrame, pl, uvFrame, pa+sw, qa+sw, qb-sw, R, Fs)
			fSn(fr, MFrame, pl, uvFrame, pb-sw, qa+sw, qb-sw, R, Fs)
			fZp(fr, MFrame, pl, uvFrame, qa+sw, pa+sw, pb-sw, R, Fs)
			fZn(fr, MFrame, pl, uvFrame, qb-sw, pa+sw, pb-sw, R, Fs)
		}
	}
	// transoms split between mullions
	for _, r := range w.Rows {
		z := y0 + r*(y1-y0)
		za, zb2 := z-mw/2, z+mw/2
		cur := x0
		segs := append(ms, [2]float64{x1, x1})
		for _, sg := range segs {
			if sg[0]-cur > eps {
				fD(fr, MFrame, pl, uvFrame, cur, sg[0], za, zb2, F)
				fZp(fr, MFrame, pl, uvFrame, zb2, cur, sg[0], R, F)
				fZn(fr, MFrame, pl, uvFrame, za, cur, sg[0], R, F)
			}
			cur = sg[1]
		}
	}
}
