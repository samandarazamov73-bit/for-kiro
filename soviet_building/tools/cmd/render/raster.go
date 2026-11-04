package main

import (
	"math"
	"runtime"
	"sync"
)

type VisBuf struct {
	W, H   int
	Z      []float32
	ID     []int32
	B1, B2 []float32
}

func newVisBuf(w, h int) *VisBuf {
	v := &VisBuf{W: w, H: h, Z: make([]float32, w*h), ID: make([]int32, w*h), B1: make([]float32, w*h), B2: make([]float32, w*h)}
	for i := range v.Z {
		v.Z[i] = float32(math.Inf(1))
		v.ID[i] = -1
	}
	return v
}

type sv struct {
	x, y, z, iw float64
	b          [3]float64 // barycentrics in the original triangle
}
type stri struct {
	v  [3]sv
	id int32
}

// setup projects and near-clips triangles into screen space.
func setup(c *Cam, tris []Tri, cull bool) []stri {
	var out []stri
	near := 0.05
	for ti := range tris {
		t := &tris[ti]
		type cv struct {
			q [4]float64
			b [3]float64
		}
		poly := make([]cv, 0, 6)
		for k := 0; k < 3; k++ {
			var b [3]float64
			b[k] = 1
			poly = append(poly, cv{c.VP.apply(t.P[k], 1), b})
		}
		if c.OrthoH == 0 {
			var clipped []cv
			for i := range poly {
				a, bb := poly[i], poly[(i+1)%len(poly)]
				da, db := a.q[3]-near, bb.q[3]-near
				if da >= 0 {
					clipped = append(clipped, a)
				}
				if (da >= 0) != (db >= 0) {
					s := da / (da - db)
					var n cv
					for j := 0; j < 4; j++ {
						n.q[j] = a.q[j] + (bb.q[j]-a.q[j])*s
					}
					for j := 0; j < 3; j++ {
						n.b[j] = a.b[j] + (bb.b[j]-a.b[j])*s
					}
					clipped = append(clipped, n)
				}
			}
			poly = clipped
		}
		if len(poly) < 3 {
			continue
		}
		vs := make([]sv, len(poly))
		for i, p := range poly {
			iw := 1 / p.q[3]
			vs[i] = sv{(p.q[0]*iw*0.5 + 0.5) * float64(c.W), (0.5 - p.q[1]*iw*0.5) * float64(c.H), p.q[2] * iw, iw, p.b}
		}
		for i := 1; i+1 < len(vs); i++ {
			s := stri{[3]sv{vs[0], vs[i], vs[i+1]}, int32(ti)}
			area := (s.v[1].x-s.v[0].x)*(s.v[2].y-s.v[0].y) - (s.v[2].x-s.v[0].x)*(s.v[1].y-s.v[0].y)
			if area == 0 || (cull && area > 0) {
				continue
			}
			out = append(out, s)
		}
	}
	return out
}

// rasterize fills the visibility buffer (parallel over row bands).
func rasterize(c *Cam, tris []Tri, vb *VisBuf, cull bool) {
	st := setup(c, tris, cull)
	const band = 32
	nb := (vb.H + band - 1) / band
	bins := make([][]int32, nb)
	for i, s := range st {
		y0 := math.Min(s.v[0].y, math.Min(s.v[1].y, s.v[2].y))
		y1 := math.Max(s.v[0].y, math.Max(s.v[1].y, s.v[2].y))
		b0, b1 := int(math.Max(0, math.Floor(y0)))/band, int(math.Min(float64(vb.H-1), math.Ceil(y1)))/band
		for b := b0; b <= b1 && b < nb; b++ {
			if b >= 0 {
				bins[b] = append(bins[b], int32(i))
			}
		}
	}
	var wg sync.WaitGroup
	jobs := make(chan int, nb)
	for b := 0; b < nb; b++ {
		jobs <- b
	}
	close(jobs)
	for w := 0; w < runtime.NumCPU(); w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for b := range jobs {
				for _, si := range bins[b] {
					rastTri(&st[si], vb, b*band, min((b+1)*band, vb.H))
				}
			}
		}()
	}
	wg.Wait()
}

func rastTri(s *stri, vb *VisBuf, ylo, yhi int) {
	v0, v1, v2 := s.v[0], s.v[1], s.v[2]
	minx := int(math.Max(0, math.Floor(math.Min(v0.x, math.Min(v1.x, v2.x)))))
	maxx := int(math.Min(float64(vb.W-1), math.Ceil(math.Max(v0.x, math.Max(v1.x, v2.x)))))
	miny := int(math.Max(float64(ylo), math.Floor(math.Min(v0.y, math.Min(v1.y, v2.y)))))
	maxy := int(math.Min(float64(yhi-1), math.Ceil(math.Max(v0.y, math.Max(v1.y, v2.y)))))
	area := (v1.x-v0.x)*(v2.y-v0.y) - (v2.x-v0.x)*(v1.y-v0.y)
	ia := 1 / area
	for y := miny; y <= maxy; y++ {
		py := float64(y) + 0.5
		for x := minx; x <= maxx; x++ {
			px := float64(x) + 0.5
			l0 := ((v1.x-px)*(v2.y-py) - (v2.x-px)*(v1.y-py)) * ia
			l1 := ((v2.x-px)*(v0.y-py) - (v0.x-px)*(v2.y-py)) * ia
			l2 := 1 - l0 - l1
			if l0 < -1e-9 || l1 < -1e-9 || l2 < -1e-9 {
				continue
			}
			z := l0*v0.z + l1*v1.z + l2*v2.z
			i := y*vb.W + x
			if float32(z) >= vb.Z[i] || z < -1 || z > 1 {
				continue
			}
			w0, w1, w2 := l0*v0.iw, l1*v1.iw, l2*v2.iw
			sw := 1 / (w0 + w1 + w2)
			w0, w1, w2 = w0*sw, w1*sw, w2*sw
			vb.Z[i] = float32(z)
			vb.ID[i] = s.id
			vb.B1[i] = float32(w0*v0.b[1] + w1*v1.b[1] + w2*v2.b[1])
			vb.B2[i] = float32(w0*v0.b[2] + w1*v1.b[2] + w2*v2.b[2])
		}
	}
}
