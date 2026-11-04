package main

import (
	"math"
	"runtime"
	"sync"
)

// GBuf holds per-pixel surface data reconstructed from the visibility buffer.
type GBuf struct {
	P, N           []V3
	Alb            []V3
	Rough, Met, AO []float64
	Valid          []bool
}

func parallelRows(h int, f func(y int)) {
	var wg sync.WaitGroup
	rows := make(chan int, h)
	for y := 0; y < h; y++ {
		rows <- y
	}
	close(rows)
	for w := 0; w < runtime.NumCPU(); w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for y := range rows {
				f(y)
			}
		}()
	}
	wg.Wait()
}

// baryAt returns perspective-correct barycentrics of triangle t at pixel (px,py).
func baryAt(c *Cam, t *Tri, px, py float64) ([3]float64, bool) {
	var sx, sy, iw [3]float64
	for k := 0; k < 3; k++ {
		q := c.VP.apply(t.P[k], 1)
		if q[3] <= 1e-6 {
			return [3]float64{}, false
		}
		iw[k] = 1 / q[3]
		sx[k] = (q[0]*iw[k]*0.5 + 0.5) * float64(c.W)
		sy[k] = (0.5 - q[1]*iw[k]*0.5) * float64(c.H)
	}
	area := (sx[1]-sx[0])*(sy[2]-sy[0]) - (sx[2]-sx[0])*(sy[1]-sy[0])
	if area == 0 {
		return [3]float64{}, false
	}
	l0 := ((sx[1]-px)*(sy[2]-py) - (sx[2]-px)*(sy[1]-py)) / area
	l1 := ((sx[2]-px)*(sy[0]-py) - (sx[0]-px)*(sy[2]-py)) / area
	l2 := 1 - l0 - l1
	w0, w1, w2 := l0*iw[0], l1*iw[1], l2*iw[2]
	s := w0 + w1 + w2
	return [3]float64{w0 / s, w1 / s, w2 / s}, true
}

func uvAt(t *Tri, b [3]float64) (float64, float64) {
	return b[0]*t.UV[0][0] + b[1]*t.UV[1][0] + b[2]*t.UV[2][0], b[0]*t.UV[0][1] + b[1]*t.UV[1][1] + b[2]*t.UV[2][1]
}

func buildGBuf(c *Cam, tris []Tri, mats []*Mat, vb *VisBuf) *GBuf {
	n := vb.W * vb.H
	g := &GBuf{make([]V3, n), make([]V3, n), make([]V3, n), make([]float64, n), make([]float64, n), make([]float64, n), make([]bool, n)}
	parallelRows(vb.H, func(y int) {
		for x := 0; x < vb.W; x++ {
			i := y*vb.W + x
			id := vb.ID[i]
			if id < 0 {
				continue
			}
			t := &tris[id]
			m := mats[t.Mat]
			b1, b2 := float64(vb.B1[i]), float64(vb.B2[i])
			b := [3]float64{1 - b1 - b2, b1, b2}
			P := add(add(mul(t.P[0], b[0]), mul(t.P[1], b[1])), mul(t.P[2], b[2]))
			N := norm(add(add(mul(t.N[0], b[0]), mul(t.N[1], b[1])), mul(t.N[2], b[2])))
			u, v := uvAt(t, b)
			lod := func(size float64) float64 { return 0 }
			if bx, ok1 := baryAt(c, t, float64(x)+1.5, float64(y)+0.5); ok1 {
				if by, ok2 := baryAt(c, t, float64(x)+0.5, float64(y)+1.5); ok2 {
					ux, vx := uvAt(t, bx)
					uy, vy := uvAt(t, by)
					d := math.Max(math.Hypot(ux-u, vx-v), math.Hypot(uy-u, vy-v))
					lod = func(size float64) float64 { return math.Log2(math.Max(d*size, 1e-9)) }
				}
			}
			alb := V3{m.Base[0], m.Base[1], m.Base[2]}
			rough, met, ao := m.Rough, m.Metal, 1.0
			if m.BaseT != nil {
				s := m.BaseT.Sample(u, v, lod(m.BaseT.Size()))
				alb = V3{alb[0] * s[0], alb[1] * s[1], alb[2] * s[2]}
			}
			if m.ORMT != nil {
				s := m.ORMT.Sample(u, v, lod(m.ORMT.Size()))
				ao, rough, met = s[0], rough*s[1], met*s[2]
			}
			if m.NormT != nil {
				s := m.NormT.Sample(u, v, lod(m.NormT.Size()))
				tx, ty, tz := (2*s[0]-1)*m.NScale, (2*s[1]-1)*m.NScale, 2*s[2]-1
				T := V3{b[0]*t.T[0][0] + b[1]*t.T[1][0] + b[2]*t.T[2][0], b[0]*t.T[0][1] + b[1]*t.T[1][1] + b[2]*t.T[2][1], b[0]*t.T[0][2] + b[1]*t.T[1][2] + b[2]*t.T[2][2]}
				T = norm(sub(T, mul(N, dot(N, T))))
				B := mul(cross(N, T), t.T[0][3])
				N = norm(add(add(mul(T, tx), mul(B, ty)), mul(N, tz)))
			}
			g.P[i], g.N[i], g.Alb[i] = P, N, alb
			g.Rough[i], g.Met[i], g.AO[i], g.Valid[i] = rough, met, ao, true
		}
	})
	return g
}
