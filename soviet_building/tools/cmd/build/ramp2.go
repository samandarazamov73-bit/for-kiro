package main

import (
	"math"

	. "sovbuild/geo"
)

// ramp assembles runs, landings, curbs and side walls.
func (b *B) ramp() {
	m, c := b.Ramp, Curb
	zt := ZTurn
	// outer run (rises toward -X from the foot at RXStart) and inner run (rises toward +X)
	b.deck(RXTurn1, RXStart, RYO0, RYO1, zt, 0, true, true)
	b.deck(RXTurn1, RXMid0, RYI0, RYI1, zt, ZMid, true, true)
	b.deck(RXMid0, RXMid1, RYI0, RYI1, ZMid, ZMid, true, true)
	b.deck(RXMid1, LandX0, RYI0, RYI1, ZMid, FFL, true, true)
	// turning landing: deck, curbs on three sides, side walls
	x0, x1, y0, y1 := RXTurn0, RXTurn1, RYO0, RYI1
	m.Quad(MPaving, V3(x0+c, y0+c, zt), V3(x1, y0+c, zt), V3(x1, y1-c, zt), V3(x0+c, y1-c, zt), uvPave)
	m.Box(MPaving, V3(x0, y0, zt), V3(x0+c, y1, zt+c), FXp|FZp, uvPave)
	m.Box(MPaving, V3(x0+c, y0, zt), V3(x1, y0+c, zt+c), FYp|FZp, uvPave)
	m.Box(MPaving, V3(x0+c, y1-c, zt), V3(x1, y1, zt+c), FYn|FZp, uvPave)
	m.Box(MWeather, V3(x0, y0, RampBase), V3(x1, y1, zt+c), FXn, uvWeather)
	m.Quad(MWeather, V3(x0, y0, RampBase), V3(x1, y0, RampBase), V3(x1, y0, zt+c), V3(x0, y0, zt+c), uvWeather)
	m.Quad(MWeather, V3(x1, y1, RampBase), V3(x0, y1, RampBase), V3(x0, y1, zt+c), V3(x1, y1, zt+c), uvWeather)
	// face closing the gap between the runs, and curb ends at the landing
	m.Box(MWeather, V3(x1-0.01, RYO1, RampBase), V3(x1, RYI0, zt+c), FXp, uvWeather)
	m.Box(MPaving, V3(x1-c, RYO1-c, zt), V3(x1, RYI0+c, zt+c), FXn|FYn|FYp|FZp, uvPave)
	// curb ends at the foot of the outer run and at the top of the inner run
	for _, y := range [][2]float64{{RYO0, RYO0 + c}, {RYO1 - c, RYO1}} {
		m.Box(MPaving, V3(RXStart-0.01, y[0], 0), V3(RXStart, y[1], c), FXp, uvPave)
	}
	for _, y := range [][2]float64{{RYI0, RYI0 + c}, {RYI1 - c, RYI1}} {
		m.Box(MPaving, V3(LandX0-0.01, y[0], FFL), V3(LandX0, y[1], FFL+c), FXp, uvPave)
	}
	b.rampRails()
}

// railPt is a handrail path vertex: plan position + deck height below it.
type railPt struct{ x, y, deck float64 }

func arc(cx, cy, r, a0, a1 float64, n int, deck float64) []railPt {
	var out []railPt
	for i := 0; i <= n; i++ {
		a := (a0 + (a1-a0)*float64(i)/float64(n)) * 3.14159265358979 / 180
		out = append(out, railPt{cx + r*math.Cos(a), cy + r*math.Sin(a), deck})
	}
	return out
}
