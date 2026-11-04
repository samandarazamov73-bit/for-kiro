package main

import (
	"math"

	. "sovbuild/tex"
)

// glass: 4x4 atlas of glazed openings seen from outside (dark rooms, tulle curtains,
// vertical blinds, plants on the sill) with dirt and rain marks for roughness.
func glass() *Set {
	const size = 1024
	s := NewSet("T_Glass", size)
	n1, n2 := NewNoise(61), NewNoise(62)
	types := []int{0, 1, 0, 2, 1, 0, 3, 1, 0, 2, 0, 1, 3, 0, 1, 2}
	Par(size, func(y int) {
		for x := 0; x < size; x++ {
			u := (float64(x) + 0.5) / size
			v := 1 - (float64(y)+0.5)/size
			cx, cy := int(u*4), int(v*4)
			lu, lv := u*4-float64(cx), v*4-float64(cy)
			k := cy*4 + cx
			hk := Hash01(k, 0, 7)
			nz := n1.FBM(u, v, 32, 3, 0.5)
			in := 0.04 + 0.035*sq(1-lv) + 0.01*nz
			col := [3]float64{in * 0.95, in, in * 1.08}
			if lv > 0.86 && lv < 0.9 && lu > 0.25 && lu < 0.75 { // switched-off ceiling lamp
				col = [3]float64{0.10, 0.10, 0.11}
			}
			switch types[k] {
			case 1: // tulle curtains
				open := 0.15 + 0.25*hk
				cover := Smooth(open+0.02, open-0.02, math.Abs(lu-0.5)*2-0.0) // centre opening
				if hk > 0.6 {
					cover = 1
				}
				fold := 0.5 + 0.5*math.Sin(lu*2*math.Pi*14+3*n2.FBM(u, v, 8, 2, 0.5))
				cv := 0.27 + 0.09*fold
				t := (1 - cover) * 0.78
				for c := range col {
					col[c] = Mix(col[c], cv*[]float64{1, 0.99, 0.96}[c], t)
				}
			case 2: // vertical blinds, partly turned
				slat := frac(lu * 11)
				gap := Smooth(0.75+0.15*hk, 0.85+0.12*hk, slat)
				bc := [3]float64{0.32, 0.31, 0.28}
				for c := range col {
					col[c] = Mix(bc[c]*(0.85+0.15*math.Cos(slat*math.Pi)), col[c], gap)
				}
			case 3: // plants on the window sill
				pl := Smooth(0.15, 0.05, lv-0.25*n2.FBM(u, v, 20, 3, 0.5)-0.1)
				for c := range col {
					col[c] = Mix(col[c], []float64{0.09, 0.16, 0.07}[c]*(0.8+0.4*nz), pl)
				}
			}
			edge := math.Min(math.Min(lu, 1-lu), math.Min(lv, 1-lv))
			dirt := Smooth(0.06, 0.0, edge)*0.6 + Smooth(0.25, 0.0, lv)*0.25
			rain := Smooth(0.2, 0.7, n2.FBMA(u, v, 120, 6, 3, 0.6))
			i := y*size + x
			for c, ch := range []*F{s.R, s.G, s.B} {
				ch.P[i] = clamp01(Mix(col[c], 0.30, dirt*0.35))
			}
			s.Rough.P[i] = clamp01(0.05 + 0.25*dirt + 0.12*rain*(0.3+0.7*(1-lv)))
			s.AO.P[i] = 1
			s.Metal.P[i] = 0
			s.Height.P[i] = 0.6*n1.FBM(u, v, 6, 2, 0.5)
		}
	})
	s.NormalStrength = 0.6
	return s
}

// frame: dark grey painted window frames with chipped paint and dirt (1.2 m repeat).
func frame() *Set {
	const size = 1024
	s := NewSet("T_Window_Frame", size)
	n1, n2, n3 := NewNoise(51), NewNoise(52), NewNoise(53)
	Par(size, func(y int) {
		for x := 0; x < size; x++ {
			u := (float64(x) + 0.5) / size
			v := 1 - (float64(y)+0.5)/size
			grain := n1.FBMA(u, v, 8, 220, 3, 0.5)
			chip := Smooth(0.58, 0.64, n2.FBM(u, v, 24, 4, 0.6))
			dirt := Smooth(-0.1, 0.7, n3.FBM(u, v, 6, 4, 0.55))
			i := y*size + x
			for c, ch := range []*F{s.R, s.G, s.B} {
				col := []float64{0.16, 0.17, 0.18}[c] * (1 + 0.08*grain)
				col = Mix(col, []float64{0.62, 0.60, 0.56}[c], chip*0.8)
				col = Mix(col, 0.22, dirt*0.25)
				ch.P[i] = clamp01(col)
			}
			s.Rough.P[i] = clamp01(0.52 + 0.06*grain + 0.25*chip + 0.15*dirt)
			s.AO.P[i] = clamp01(1 - 0.1*chip)
			s.Metal.P[i] = 0
			s.Height.P[i] = 0.3*grain - 0.8*chip
		}
	})
	s.NormalStrength = 1.5
	return s
}
