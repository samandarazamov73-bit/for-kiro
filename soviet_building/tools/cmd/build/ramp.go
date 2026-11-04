package main

import . "sovbuild/geo"

// Switchback ramp, slope 1:16 (6.25 %), deck 1.85 m (1.51 m clear between handrails).
const (
	RSlope   = 1.0 / 16
	RXStart  = 18.2  // outer run foot (grade)
	RXTurn1  = 9.75  // turning landing edge
	RXTurn0  = 7.95  // turning landing far edge (1.8 m)
	RXMid0   = 15.125 // inner run intermediate landing
	RXMid1   = 16.625
	RYO0     = -5.25 // outer run deck
	RYO1     = -3.40
	RYI0     = -2.30 // inner run deck
	RYI1     = -0.45
	Curb     = 0.10 // curb width and height
	RampBase = -0.15
)

var ZTurn = (RXStart - RXTurn1) * RSlope    // 0.528
var ZMid = ZTurn + (RXMid0-RXTurn1)*RSlope  // 0.864

// zOuter / zInner give the deck height along X.
func zOuter(x float64) float64 { return (RXStart - x) * RSlope }
func zInner(x float64) float64 {
	switch {
	case x <= RXMid0:
		return ZTurn + (x-RXTurn1)*RSlope
	case x <= RXMid1:
		return ZMid
	default:
		return ZMid + (x-RXMid1)*RSlope
	}
}

// deck builds one straight segment between x0 (height za) and x1 (height zb):
// deck surface, curbs on both edges, and solid side walls down to grade.
func (b *B) deck(x0, x1, y0, y1, za, zb float64, wallLo, wallHi bool) {
	m := b.Ramp
	c := Curb
	m.Quad(MPaving, V3(x0, y0+c, za), V3(x1, y0+c, zb), V3(x1, y1-c, zb), V3(x0, y1-c, za), uvPave)
	for _, e := range [][2]float64{{y0, y0 + c}, {y1 - c, y1}} {
		m.Quad(MPaving, V3(x0, e[0], za+c), V3(x1, e[0], zb+c), V3(x1, e[1], zb+c), V3(x0, e[1], za+c), uvPave)
	}
	m.Quad(MPaving, V3(x0, y0+c, za), V3(x0, y0+c, za+c), V3(x1, y0+c, zb+c), V3(x1, y0+c, zb), uvPave)
	m.Quad(MPaving, V3(x1, y1-c, zb), V3(x1, y1-c, zb+c), V3(x0, y1-c, za+c), V3(x0, y1-c, za), uvPave)
	if wallLo {
		m.Quad(MWeather, V3(x0, y0, RampBase), V3(x1, y0, RampBase), V3(x1, y0, zb+c), V3(x0, y0, za+c), uvWeather)
	}
	if wallHi {
		m.Quad(MWeather, V3(x1, y1, RampBase), V3(x0, y1, RampBase), V3(x0, y1, za+c), V3(x1, y1, zb+c), uvWeather)
	}
}
