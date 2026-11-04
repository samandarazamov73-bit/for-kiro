package main

import (
	"math"

	. "sovbuild/geo"
)

// roofSurface builds a gently dished roof membrane draining to internal funnels.
func (b *B) roofSurface(x0, x1, y0, y1, z float64, nx, ny int, drains []Vec2, depth float64) {
	m := b.Roof
	h := func(x, y float64, edge bool) float64 {
		if edge {
			return z
		}
		d := 0.0
		for _, p := range drains {
			r := math.Hypot(x-p.U, y-p.V)
			d = math.Max(d, depth*math.Exp(-r*r/18))
		}
		return z - d + (b.rng.Float64()-0.5)*0.012
	}
	grid := make([][]Vec3, nx+1)
	for i := 0; i <= nx; i++ {
		grid[i] = make([]Vec3, ny+1)
		for j := 0; j <= ny; j++ {
			x := x0 + (x1-x0)*float64(i)/float64(nx)
			y := y0 + (y1-y0)*float64(j)/float64(ny)
			grid[i][j] = V3(x, y, h(x, y, i == 0 || j == 0 || i == nx || j == ny))
		}
	}
	for i := 0; i < nx; i++ {
		for j := 0; j < ny; j++ {
			a, c, d, e := grid[i][j], grid[i+1][j], grid[i+1][j+1], grid[i][j+1]
			m.Tri(MRoof, a, c, d, uvRoof)
			m.Tri(MRoof, a, d, e, uvRoof)
		}
	}
	for _, p := range drains {
		zd := z - depth
		// cast-iron funnel: square flange + low strainer dome
		b.Drains.Box(MMetal, V3(p.U-0.25, p.V-0.25, zd-0.01), V3(p.U+0.25, p.V+0.25, zd+0.015), FXn|FXp|FYn|FYp|FZp, WorldUV(1, 1, 0, 0))
		top := V3(p.U, p.V, zd+0.12)
		c := []Vec3{V3(p.U-0.14, p.V-0.14, zd+0.015), V3(p.U+0.14, p.V-0.14, zd+0.015), V3(p.U+0.14, p.V+0.14, zd+0.015), V3(p.U-0.14, p.V+0.14, zd+0.015)}
		for k := 0; k < 4; k++ {
			b.Drains.Tri(MMetal, c[k], c[(k+1)%4], top, WorldUV(0.3, 0.3, 0, 0))
		}
	}
}

// vent builds a masonry ventilation shaft with a raised cap.
func (b *B) vent(x, y, z, w, d, h float64) {
	m := b.RoofStruct
	m.Box(MWeather, V3(x-w/2, y-d/2, z-0.05), V3(x+w/2, y+d/2, z+h), FXn|FXp|FYn|FYp|FZp, uvWeather)
	g, t := 0.18, 0.07
	m.Box(MWeather, V3(x-w/2-0.1, y-d/2-0.1, z+h+g), V3(x+w/2+0.1, y+d/2+0.1, z+h+g+t), FAll, uvWeather)
	for _, s := range [][2]float64{{-1, -1}, {1, -1}, {1, 1}, {-1, 1}} {
		cx, cy := x+s[0]*(w/2-0.05), y+s[1]*(d/2-0.05)
		m.Box(MWeather, V3(cx-0.04, cy-0.04, z+h), V3(cx+0.04, cy+0.04, z+h+g), FXn|FXp|FYn|FYp, uvWeather)
	}
}
