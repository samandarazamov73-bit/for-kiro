package main

import (
	"math"

	. "sovbuild/tex"
)

// tiles: dark red-brown ceramic facing tiles 232x67 mm, running bond, 8 mm grout.
// One repeat = 4.8 x 4.8 m (20 x 64 tiles), v = height above grade / 4.8.
func tiles() *Set {
	const size, M, TW, TH, G = 2048, 4.8, 0.24, 0.075, 0.004
	s := NewSet("T_Ceramic_Tile_RedBrown", size)
	n1, n2, n3 := NewNoise(71), NewNoise(72), NewNoise(73)
	Par(size, func(y int) {
		for x := 0; x < size; x++ {
			u := (float64(x) + 0.5) / size
			v := 1 - (float64(y)+0.5)/size
			xm, zm := u*M, v*M
			row := int(math.Floor(zm / TH))
			off := float64(row%2) * TW / 2
			col := int(math.Floor((xm + off) / TW))
			tu := (xm + off - float64(col)*TW)
			tv := zm - float64(row)*TH
			cid, rid := ((col%20)+20)%20, ((row%64)+64)%64
			edge := math.Min(math.Min(tu, TW-tu), math.Min(tv, TH-tv)) - G
			surf := Smooth(0, 0.0035, edge) // 1 on tile face, 0 in grout
			h1, h2, h3 := Hash01(cid, rid, 1), Hash01(cid, rid, 2), Hash01(cid, rid, 3)
			val := 0.86 + 0.26*h1
			if h3 < 0.03 {
				val *= 0.72 // replaced / darker tiles
			} else if h3 > 0.975 {
				val *= 1.18
			}
			hue := (h2 - 0.5) * 0.10
			clay := n1.FBM(u, v, 256, 3, 0.5)
			mott := n2.FBM(u, v, 5, 4, 0.55)
			tile := [3]float64{0.36 + hue*0.5, 0.15 + hue*0.25, 0.11 - hue*0.2}
			grout := [3]float64{0.50, 0.47, 0.43}
			splash := Smooth(0.16, 0.0, v) * (0.6 + 0.4*n3.FBM(u, v, 24, 3, 0.5))
			streak := Smooth(0.15, 0.6, n3.FBMA(u, v, 90, 3, 3, 0.6)) * 0.35
			eff := Smooth(0.45, 0.8, n2.FBM(u, v, 9, 4, 0.6)) * (1 - surf) * 0.5
			chip := 0.0
			if Hash01(cid, rid, 4) < 0.05 && edge < 0.012 && tu < 0.03 && tv < 0.03 {
				chip = 1
			}
			for c, ch := range []*F{s.R, s.G, s.B} {
				tc := tile[c] * val * (1 + 0.06*clay + 0.08*mott)
				if chip > 0 {
					tc = grout[c] * 0.9
				}
				gc := grout[c] * (1 + 0.1*clay - 0.25*Smooth(-0.3, 0.7, mott))
				col := Mix(gc, tc, surf)
				col = Mix(col, 0.20+0.02*float64(c), splash*0.45+streak*0.25)
				col = Mix(col, 0.78, eff)
				ch.P[y*size+x] = clamp01(col)
			}
			tilt := (Hash01(cid, rid, 5) - 0.5) * 0.6 * (tu / TW)
			s.Height.P[y*size+x] = surf*(1+0.08*clay+tilt) - chip*0.6 + (1-surf)*0.1*clay
			s.Rough.P[y*size+x] = clamp01(Mix(0.95, 0.42+0.2*Hash01(cid, rid, 6)+0.05*clay, surf) + splash*0.25 + streak*0.1)
			s.AO.P[y*size+x] = clamp01(Mix(0.62, 1, surf) - 0.05*splash)
		}
	})
	s.NormalStrength = 3.0
	return s
}
