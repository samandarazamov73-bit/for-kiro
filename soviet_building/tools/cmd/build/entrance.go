package main

import . "sovbuild/geo"

const StairY1 = -2.30 // stairs end at the ramp's outer side wall

// stairs builds the entrance landing and the wrap-around flight (steps on the -X and -Y sides).
func (b *B) stairs() {
	m := b.Stairs
	top := float64(NRiser) * StepR // = FFL
	// landing top (incl. the strip inside the lobby recess) and the face toward the ramp gap
	m.Quad(MPaving, V3(LandX0, LandY0, top), V3(EntX0, LandY0, top), V3(EntX0, 0, top), V3(LandX0, 0, top), uvPave)
	m.Quad(MPaving, V3(EntX0, -RecS1, top), V3(GlazX, -RecS1, top), V3(GlazX, -RecS0, top), V3(EntX0, -RecS0, top), uvPave)
	m.Quad(MPaving, V3(LandX0, 0, -0.15), V3(LandX0, -0.45, -0.15), V3(LandX0, -0.45, top), V3(LandX0, 0, top), uvPave)
	for k := 1; k <= NRiser; k++ {
		run := float64(NRiser-k) * StepT
		xk, yk := LandX0-run, LandY0-run
		z0, z1 := float64(k-1)*StepR, float64(k)*StepR
		// risers facing -X and -Y
		m.Quad(MPaving, V3(xk, StairY1, z0), V3(xk, yk, z0), V3(xk, yk, z1), V3(xk, StairY1, z1), uvPave)
		m.Quad(MPaving, V3(xk, yk, z0), V3(EntX0, yk, z0), V3(EntX0, yk, z1), V3(xk, yk, z1), uvPave)
		if k == NRiser {
			break
		}
		// L-shaped tread
		x1, y1 := xk+StepT, yk+StepT
		m.Quad(MPaving, V3(xk, yk, z1), V3(x1, yk, z1), V3(x1, StairY1, z1), V3(xk, StairY1, z1), uvPave)
		m.Quad(MPaving, V3(x1, yk, z1), V3(EntX0, yk, z1), V3(EntX0, y1, z1), V3(x1, y1, z1), uvPave)
	}
}

var ColY = []float64{-2.9, -5.075, -7.25, -9.425, -11.6}

func (b *B) canopy() {
	c := b.Canopy
	x0, x1, y0, y1, z0, z1 := CanX0, CanX1, CanY0, CanY1, CanZ0, CanZ1
	c.Box(MWeather, V3(x0, y0, z0), V3(x1, y1, z1), FXn|FYn|FYp|FZn, uvWeather)
	// roofed top with a low upstand along the free edges
	u := 0.12
	c.Quad(MRoof, V3(x0+u, y0+u, z1), V3(x1, y0+u, z1), V3(x1, y1-u, z1), V3(x0+u, y1-u, z1), uvRoof)
	c.Box(MWeather, V3(x0, y0, z1), V3(x0+u, y1, z1+0.12), FXn|FXp|FYn|FYp|FZp, uvWeather)
	c.Box(MWeather, V3(x0+u, y0, z1), V3(x1, y0+u, z1+0.12), FYn|FYp|FZp, uvWeather)
	c.Box(MWeather, V3(x0+u, y1-u, z1), V3(x1, y1, z1+0.12), FYn|FYp|FZp, uvWeather)
	// rain spout at the front-left corner
	c.Box(MMetal, V3(x0-0.35, y0+0.4, z1-0.02), V3(x0, y0+0.5, z1+0.06), FXn|FYn|FYp|FZp|FZn, WorldUV(1, 1, 0, 0))
	// columns with plinths
	for _, y := range ColY {
		cx := x0 + 0.4
		b.Columns.Box(MWeather, V3(cx-0.2, y-0.2, FFL+0.12), V3(cx+0.2, y+0.2, z0), FXn|FXp|FYn|FYp, uvWeather)
		b.Columns.Box(MWeather, V3(cx-0.26, y-0.26, FFL), V3(cx+0.26, y+0.26, FFL+0.12), FXn|FXp|FYn|FYp|FZp, uvWeather)
	}
}
