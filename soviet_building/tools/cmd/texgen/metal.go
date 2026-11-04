package main

import (
	"math"
	"math/rand"

	. "sovbuild/tex"
)

// metal: dark grey painted steel tube, semi-metallic paint, worn spots, rust, scratches.
// One repeat = 1 m (u = around the tube, v = along).
func metal() *Set {
	const size = 1024
	s := NewSet("T_Metal_Handrail", size)
	s.HasMetal = true
	n1, n2, n3 := NewNoise(91), NewNoise(92), NewNoise(93)
	sc := NewF(size, size)
	r := rand.New(rand.NewSource(94))
	for i := 0; i < 70; i++ { // scratches along the rail
		x, y := r.Float64()*size, r.Float64()*size
		a := math.Pi/2 + (r.Float64()-0.5)*0.5
		l := 10 + r.Float64()*60
		for t := 0.0; t < l; t += 0.5 {
			sc.Stamp(x+math.Cos(a)*t, y+math.Sin(a)*t, 0.45, 0.5)
		}
	}
	Par(size, func(y int) {
		for x := 0; x < size; x++ {
			u := (float64(x) + 0.5) / size
			v := 1 - (float64(y)+0.5)/size
			i := y*size + x
			peel := n1.At(u*900, v*900, 900)*0.5 + n2.FBM(u, v, 16, 4, 0.5)
			wear := Smooth(0.45, 0.6, n2.FBM(u, v, 10, 5, 0.55)) // bare steel
			rust := Smooth(0.5, 0.75, n3.FBM(u, v, 14, 5, 0.6)) * (1 - wear*0.5)
			dirt := Smooth(-0.2, 0.7, n1.FBM(u, v, 5, 3, 0.5))
			scr := sc.P[i]
			paint := [3]float64{0.19, 0.20, 0.21}
			steel := [3]float64{0.56, 0.56, 0.57}
			rc := [3]float64{0.36, 0.20, 0.11}
			for c, ch := range []*F{s.R, s.G, s.B} {
				col := paint[c] * (1 + 0.06*peel)
				col = Mix(col, steel[c], math.Max(wear*0.85, scr*0.45))
				col = Mix(col, rc[c], rust*0.85)
				col = Mix(col, 0.24, dirt*0.15)
				ch.P[i] = clamp01(col)
			}
			s.Metal.P[i] = clamp01(Mix(Mix(0.5, 1.0, math.Max(wear, scr*0.8)), 0.0, rust))
			s.Rough.P[i] = clamp01(Mix(Mix(0.48+0.06*peel, 0.32, math.Max(wear, scr)), 0.88, rust) + 0.1*dirt)
			s.AO.P[i] = clamp01(1 - 0.08*rust)
			s.Height.P[i] = 0.25*peel - 0.5*scr + 0.6*rust*n1.At(u*300, v*300, 300) - 0.3*wear
		}
	})
	s.NormalStrength = 1.4
	return s
}
