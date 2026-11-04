package main

import . "sovbuild/geo"

const (
	RailOff, PostOff = 0.15, 0.05 // rail / post axis from the deck edge
	RailHi, RailLo   = 0.90, 0.70 // handrail heights above the deck
	RailR, PostR     = 0.021, 0.024
	RailExt          = 0.30 // horizontal extensions at both ends
)

// railTube sweeps one handrail level along a path with bent-down end returns.
func (b *B) railTube(path []railPt, h float64) {
	var pts []Vec3
	n := len(path)
	ret := func(p, q railPt, rev bool) []Vec3 {
		d := V3(p.x-q.x, p.y-q.y, 0).Norm()
		top := p.deck + h
		a := V3(p.x, p.y, top).Add(d.Mul(0.05)).Add(V3(0, 0, -0.05))
		c := V3(p.x, p.y, top).Add(d.Mul(0.05)).Add(V3(0, 0, -0.14))
		if rev {
			return []Vec3{c, a}
		}
		return []Vec3{a, c}
	}
	pts = append(pts, ret(path[0], path[1], true)...)
	for _, p := range path {
		pts = append(pts, V3(p.x, p.y, p.deck+h))
	}
	pts = append(pts, ret(path[n-1], path[n-2], false)...)
	b.RampRails.Tube(MMetal, pts, RailR, 10, true, true, 1.0, 0)
}

func (b *B) rampRails() {
	zt := ZTurn
	yo, yi, xf, r := RYO0+RailOff, RYI1-RailOff, RXTurn0+RailOff, 0.15
	outer := []railPt{{RXStart + RailExt, yo, 0}, {RXStart, yo, 0}, {RXTurn1, yo, zt}}
	outer = append(outer, arc(xf+r, yo+r, r, 270, 180, 3, zt)...)
	outer = append(outer, arc(xf+r, yi-r, r, 180, 90, 3, zt)...)
	outer = append(outer, railPt{RXTurn1, yi, zt}, railPt{RXMid0, yi, ZMid}, railPt{RXMid1, yi, ZMid},
		railPt{LandX0, yi, FFL}, railPt{LandX0 + RailExt, yi, FFL})
	ya, yb := RYO1-RailOff, RYI0+RailOff
	inner := []railPt{{RXStart + RailExt, ya, 0}, {RXStart, ya, 0}}
	xg := RXTurn1 - RailOff // rail along the landing edge at the end of the gap
	inner = append(inner, arc(xg+r, ya+r, r, 270, 180, 3, zt)...)
	inner = append(inner, arc(xg+r, yb-r, r, 180, 90, 3, zt)...)
	inner = append(inner, railPt{RXMid0, yb, ZMid}, railPt{RXMid1, yb, ZMid},
		railPt{LandX0, yb, FFL}, railPt{LandX0 + RailExt, yb, FFL})
	for _, p := range [][]railPt{outer, inner} {
		b.railTube(p, RailHi)
		b.railTube(p, RailLo)
	}
	// posts with welded brackets carrying both rail levels
	type post struct{ x, y, deck, dx, dy float64 }
	var posts []post
	line := func(xa, xb float64, n int, y, dy float64, z func(float64) float64) {
		for i := 0; i < n; i++ {
			x := xa + (xb-xa)*float64(i)/float64(n-1)
			posts = append(posts, post{x, y, z(x), 0, dy})
		}
	}
	line(RXStart-0.1, RXTurn1+0.1, 7, RYO0+PostOff, 1, zOuter)
	line(RXStart-0.1, RXTurn1+0.1, 7, RYO1-PostOff, -1, zOuter)
	line(RXTurn1+0.1, LandX0-0.1, 9, RYI0+PostOff, 1, zInner)
	line(RXTurn1+0.1, LandX0-0.1, 9, RYI1-PostOff, -1, zInner)
	for _, y := range []float64{RYO0 + 0.4, (RYO0 + RYI1) / 2, RYI1 - 0.4} {
		posts = append(posts, post{RXTurn0 + PostOff, y, zt, 1, 0})
	}
	posts = append(posts, post{RXTurn1 - PostOff, (RYO1 + RYI0) / 2, zt, -1, 0})
	for _, p := range posts {
		base := V3(p.x, p.y, p.deck+Curb)
		b.RampRails.Tube(MMetal, []Vec3{base, V3(p.x, p.y, p.deck+RailHi)}, PostR, 8, false, true, 1, 0)
		for _, h := range []float64{RailHi, RailLo} {
			a := V3(p.x, p.y, p.deck+h)
			c := a.Add(V3(p.dx, p.dy, 0).Mul(RailOff - PostOff))
			b.RampRails.Tube(MMetal, []Vec3{a, c}, 0.012, 6, false, false, 1, 0)
		}
		// base plate
		b.RampRails.Box(MMetal, V3(p.x-0.05, p.y-0.04, p.deck+Curb), V3(p.x+0.05, p.y+0.04, p.deck+Curb+0.012), FXn|FXp|FYn|FYp|FZp, WorldUV(1, 1, 0, 0))
	}
}
