package main

import (
	"math"

	. "sovbuild/geo"
)

// stepsOut builds a straight flight descending outward (+d) from a landing edge at d0.
// Top of the flight is at FFL; s range [s0,s1].
func stepsOut(m *Mesh, pl Plane, s0, s1, d0 float64, n int, rise, tread float64) {
	for k := 0; k < n; k++ { // k = 0 is the riser at the landing edge
		zt := FFL - float64(k)*rise
		d := d0 + float64(k)*tread
		fD(m, MPaving, pl, uvPave, s0, s1, zt-rise, zt, d) // riser
		if k > 0 {
			fZp(m, MPaving, pl, uvPave, zt, s0, s1, d-tread, d) // tread
			// exposed step ends
			fSn(m, MPaving, pl, uvPave, s0, -0.15, zt, d-tread, d)
			fSp(m, MPaving, pl, uvPave, s1, -0.15, zt, d-tread, d)
		}
	}
}

// rearExits builds two emergency exit porches on the rear facade and returns door holes.
func (b *B) rearExits(pl Plane) []Rect {
	var holes []Rect
	for _, sc := range []float64{4.5, 70.5} {
		p := b.Porch
		// door opening with concrete surround and recessed steel door
		holes = append(holes, Rect{sc - 0.95, sc + 0.95, FFL, FFL + 2.6})
		fD(b.Trim, MTrim, pl, uvTrim, sc-0.95, sc-0.75, FFL, FFL+2.6, 0.08)
		fD(b.Trim, MTrim, pl, uvTrim, sc+0.75, sc+0.95, FFL, FFL+2.6, 0.08)
		fD(b.Trim, MTrim, pl, uvTrim, sc-0.75, sc+0.75, FFL+2.4, FFL+2.6, 0.08)
		fSn(b.Trim, MTrim, pl, uvTrim, sc-0.95, FFL, FFL+2.6, 0, 0.08)
		fSp(b.Trim, MTrim, pl, uvTrim, sc+0.95, FFL, FFL+2.6, 0, 0.08)
		fZp(b.Trim, MTrim, pl, uvTrim, FFL+2.6, sc-0.95, sc+0.95, 0, 0.08)
		fSp(b.Trim, MTrim, pl, uvTrim, sc-0.75, FFL, FFL+2.4, -0.2, 0.08)
		fSn(b.Trim, MTrim, pl, uvTrim, sc+0.75, FFL, FFL+2.4, -0.2, 0.08)
		fZn(b.Trim, MTrim, pl, uvTrim, FFL+2.4, sc-0.75, sc+0.75, -0.2, 0.08)
		fD(b.Trim, MFrame, pl, uvFrame, sc-0.75, sc+0.75, FFL, FFL+2.4, -0.2)
		// landing 2.8 x 1.6 m, flight of 8 risers, canopy
		fZp(p, MPaving, pl, uvPave, FFL, sc-1.4, sc+1.4, 0, 1.6)
		fSn(p, MPaving, pl, uvPave, sc-1.4, -0.15, FFL, 0, 1.6)
		fSp(p, MPaving, pl, uvPave, sc+1.4, -0.15, FFL, 0, 1.6)
		stepsOut(p, pl, sc-1.4, sc+1.4, 1.6, NRiser, StepR, 0.30)
		cz := FFL + 2.85
		fZp(p, MWeather, pl, uvWeather, cz+0.15, sc-1.5, sc+1.5, 0, 1.5)
		fZn(p, MWeather, pl, uvWeather, cz, sc-1.5, sc+1.5, 0, 1.5)
		fD(p, MWeather, pl, uvWeather, sc-1.5, sc+1.5, cz, cz+0.15, 1.5)
		fSn(p, MWeather, pl, uvWeather, sc-1.5, cz, cz+0.15, 0, 1.5)
		fSp(p, MWeather, pl, uvWeather, sc+1.5, cz, cz+0.15, 0, 1.5)
		// handrail on the open side of the flight
		var path []Vec3
		for _, q := range [][2]float64{{0.2, FFL + 0.9}, {1.6, FFL + 0.9}, {1.6 + 7*0.3, 0.9 + StepR}, {1.6 + 7*0.3 + 0.3, 0.9 + StepR}} {
			path = append(path, pl.At(sc+1.32, q[1], q[0]))
		}
		b.Rails.Tube(MMetal, path, 0.025, 8, true, true, 1, 0)
		for _, d := range []float64{0.2, 1.6, 2.65, 3.55} {
			z := FFL
			if d > 1.6 {
				z = FFL - math.Ceil((d-1.6)/0.3)*StepR
			}
			top := FFL + 0.9
			if d > 1.6 {
				top = FFL + 0.9 - (d-1.6)/(7*0.3)*(7*StepR)
			}
			b.Rails.Tube(MMetal, []Vec3{pl.At(sc+1.32, z, d), pl.At(sc+1.32, top, d)}, 0.02, 6, false, false, 1, 0)
		}
	}
	return holes
}
