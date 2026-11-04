package main

import (
	"math"
	"math/rand"

	. "sovbuild/tex"
)

// roofing: dark grey bitumen membrane, 1 m rolls with lap seams, repairs, dried puddles, dust.
// One repeat = 8 x 8 m.
func roofing() *Set {
	const size, M = 2048, 8.0
	s := NewSet("T_Roofing_Bitumen", size)
	n1, n2, n3 := NewNoise(81), NewNoise(82), NewNoise(83)
	r := rand.New(rand.NewSource(84))
	type patch struct{ u0, v0, u1, v1 float64 }
	var patches []patch
	for i := 0; i < 7; i++ {
		u0, v0 := r.Float64(), r.Float64()
		patches = append(patches, patch{u0, v0, u0 + 0.04 + 0.1*r.Float64(), v0 + 0.03 + 0.06*r.Float64()})
	}
	Par(size, func(y int) {
		for x := 0; x < size; x++ {
			u := (float64(x) + 0.5) / size
			v := 1 - (float64(y)+0.5)/size
			vm := v * M
			strip := int(math.Floor(vm))
			fv := vm - float64(strip)
			lap := math.Exp(-sq((fv-0.06)/0.02)) // lap edge bead near each seam
			seamLine := math.Exp(-sq(fv / 0.006))
			cu := frac(u - Hash01(strip%8, 0, 9)) * M // cross seam per strip
			cross := math.Exp(-sq(math.Min(cu, M-cu)/0.015)) + 0.6*math.Exp(-sq((math.Min(cu, M-cu)-0.1)/0.03))
			gran := n1.At(u*700, v*700, 700)
			g := 0.0
			if gran > 0.5 {
				g = 0.05
			} else if gran < -0.55 {
				g = -0.04
			}
			mott := n2.FBM(u, v, 4, 5, 0.55)
			puddle := Smooth(0.25, 0.55, n3.FBM(u, v, 3, 4, 0.5))
			ring := math.Exp(-sq((n3.FBM(u, v, 3, 4, 0.5)-0.25)/0.03)) * 0.6
			dust := Smooth(0.0, 0.6, n1.FBM(u+0.3, v, 6, 4, 0.6))
			moss := Smooth(0.62, 0.75, n2.FBM(u+0.7, v+0.2, 20, 3, 0.5))
			pt, pe := 0.0, 0.0
			for _, p := range patches {
				du := math.Min(frac(u-p.u0), 1)
				dv := math.Min(frac(v-p.v0), 1)
				if du < p.u1-p.u0 && dv < p.v1-p.v0 {
					pt = 1
					e := math.Min(math.Min(du, p.u1-p.u0-du), math.Min(dv, p.v1-p.v0-dv)) * M
					pe = math.Max(pe, math.Exp(-e/0.01))
				}
			}
			base := 0.285 * (1 + 0.12*mott + g) * (1 - 0.18*pt)
			col := [3]float64{base, base, base * 1.04}
			for c := range col {
				col[c] = Mix(col[c], []float64{0.36, 0.34, 0.31}[c], 0.28*puddle+0.35*ring+0.22*dust)
				col[c] = Mix(col[c], []float64{0.16, 0.20, 0.13}[c], 0.6*moss)
				col[c] *= 1 - 0.35*seamLine - 0.25*lap*0.5 - 0.3*cross*0.4
			}
			i := y*size + x
			s.R.P[i], s.G.P[i], s.B.P[i] = clamp01(col[0]), clamp01(col[1]), clamp01(col[2])
			s.Height.P[i] = 0.25*mott + 0.15*gran + 0.8*lap + 0.6*cross + 0.5*pe + 0.2*pt - 0.4*seamLine
			s.Rough.P[i] = clamp01(0.9 + 0.05*gran - 0.18*puddle + 0.05*dust - 0.1*pt)
			s.AO.P[i] = clamp01(1 - 0.25*seamLine - 0.08*moss)
		}
	})
	s.NormalStrength = 1.6
	return s
}
