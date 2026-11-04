package main

import (
	"math"

	. "sovbuild/geo"
)

func cosf(a float64) float64 { return math.Cos(a) }
func sinf(a float64) float64 { return math.Sin(a) }

// ventChamber is the supply-air chamber with louvres on both long sides.
func (b *B) ventChamber(x, y, z float64) {
	s := b.RoofStruct
	w, d, h := 6.0, 2.6, 1.8
	s.Box(MWeather, V3(x-w/2, y-d/2, z-0.05), V3(x+w/2, y+d/2, z+h), FXn|FXp|FYn|FYp, uvWeather)
	s.Box(MTrim, V3(x-w/2-0.06, y-d/2-0.06, z+h), V3(x+w/2+0.06, y+d/2+0.06, z+h+0.08), FAll, uvTrim)
	s.Quad(MRoof, V3(x-w/2+0.1, y-d/2+0.1, z+h+0.081), V3(x+w/2-0.1, y-d/2+0.1, z+h+0.081), V3(x+w/2-0.1, y+d/2-0.1, z+h+0.081), V3(x-w/2+0.1, y+d/2-0.1, z+h+0.081), uvRoof)
	sides := []Plane{NewPlane(V3(x-w/2, y-d/2, 0), V3(1, 0, 0)), NewPlane(V3(x+w/2, y+d/2, 0), V3(-1, 0, 0))}
	for _, pl := range sides {
		for _, sc := range []float64{1.5, 4.5} {
			fD(s, MFrame, pl, uvFrame, sc-0.8, sc+0.8, z+0.5, z+1.4, 0.005)
			for k := 0; k < 5; k++ {
				zk := z + 0.55 + float64(k)*0.17
				quadP(s, MMetal, pl, WorldUV(1, 1, 0, 0), [3]float64{sc - 0.78, zk, 0.09}, [3]float64{sc + 0.78, zk, 0.09},
					[3]float64{sc + 0.78, zk + 0.14, 0.01}, [3]float64{sc - 0.78, zk + 0.14, 0.01})
				quadP(s, MMetal, pl, WorldUV(1, 1, 0, 0), [3]float64{sc - 0.78, zk, 0.09}, [3]float64{sc - 0.78, zk + 0.14, 0.01},
					[3]float64{sc + 0.78, zk + 0.14, 0.01}, [3]float64{sc + 0.78, zk, 0.09})
			}
		}
	}
}

// roofRailing: steel posts on the parapet coping with two rail levels.
func (b *B) roofRailing() {
	top := MainTopZ + 0.07
	q := OffsetPoly(MainOutline, -0.11, true)
	m := b.RoofRail
	for i := range q {
		a, c := q[i], q[(i+1)%len(q)]
		l := math.Hypot(c.U-a.U, c.V-a.V)
		n := int(math.Ceil(l / 2.5))
		for k := 0; k < n; k++ {
			t := float64(k) / float64(n)
			p := V3(a.U+(c.U-a.U)*t, a.V+(c.V-a.V)*t, top)
			m.Tube(MMetal, []Vec3{p, p.Add(V3(0, 0, 0.62))}, 0.018, 6, false, true, 1, 0)
		}
	}
	for _, h := range []float64{0.32, 0.62} {
		mid := V3((q[0].U+q[1].U)/2, (q[0].V+q[1].V)/2, top+h)
		path := []Vec3{mid}
		for _, k := range []int{1, 2, 3, 0} {
			path = append(path, V3(q[k].U, q[k].V, top+h))
		}
		path = append(path, mid)
		m.Tube(MMetal, path, 0.016, 6, false, false, 1, 0)
	}
}
