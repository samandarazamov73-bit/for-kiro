package tex

import (
	"math"
	"math/rand"
)

// AtP samples gradient noise with separate periods in x and y (anisotropic tiling).
func (n *Noise) AtP(x, y float64, px, py int) float64 {
	xi, yi := math.Floor(x), math.Floor(y)
	fx, fy := x-xi, y-yi
	ix, iy := int(xi), int(yi)
	mx := func(a int) int { a %= px; if a < 0 { a += px }; return a }
	my := func(a int) int { a %= py; if a < 0 { a += py }; return a }
	x0, x1, y0, y1 := mx(ix), mx(ix+1), my(iy), my(iy+1)
	g := func(cx, cy int, dx, dy float64) float64 {
		h := n.perm[(n.perm[cx&255]+cy)&511] & 255
		return n.gx[h]*dx + n.gy[h]*dy
	}
	u, v := fade(fx), fade(fy)
	a := g(x0, y0, fx, fy) + u*(g(x1, y0, fx-1, fy)-g(x0, y0, fx, fy))
	b := g(x0, y1, fx, fy-1) + u*(g(x1, y1, fx-1, fy-1)-g(x0, y1, fx, fy-1))
	return (a + v*(b-a)) * 1.414
}

// FBMA is anisotropic tileable fBm with base cells (bx, by).
func (n *Noise) FBMA(u, v float64, bx, by, oct int, gain float64) float64 {
	s, amp, nrm := 0.0, 1.0, 0.0
	for o := 0; o < oct; o++ {
		s += amp * n.AtP(u*float64(bx), v*float64(by), bx, by)
		nrm += amp
		amp *= gain
		bx, by = bx*2, by*2
	}
	return s / nrm
}

// Stamp adds an anti-aliased disc of radius r (pixels) at (x,y) with value a (max blend).
func (f *F) Stamp(x, y, r, a float64) {
	x0, x1 := int(math.Floor(x-r-1)), int(math.Ceil(x+r+1))
	y0, y1 := int(math.Floor(y-r-1)), int(math.Ceil(y+r+1))
	for py := y0; py <= y1; py++ {
		for px := x0; px <= x1; px++ {
			d := math.Hypot(float64(px)+0.5-x, float64(py)+0.5-y)
			w := math.Max(0, math.Min(1, r+0.5-d)) * a
			if w <= 0 {
				continue
			}
			wx, wy := ((px%f.W)+f.W)%f.W, ((py%f.H)+f.H)%f.H
			i := wy*f.W + wx
			if w > f.P[i] {
				f.P[i] = w
			}
		}
	}
}

// Crack draws a branching random-walk crack from (x,y) heading ang (radians, image space).
func (f *F) Crack(r *rand.Rand, x, y, ang float64, steps int, width, step float64, depth int) {
	for i := 0; i < steps; i++ {
		ang += (r.Float64() - 0.5) * 0.7
		x += math.Cos(ang) * step
		y += math.Sin(ang) * step
		w := width * (1 - 0.6*float64(i)/float64(steps))
		for k := 0.0; k < step; k += 0.5 {
			f.Stamp(x-math.Cos(ang)*k, y-math.Sin(ang)*k, w, 1)
		}
		if depth > 0 && r.Float64() < 0.04 {
			f.Crack(r, x, y, ang+(r.Float64()-0.5)*2.2, steps/3, width*0.7, step, depth-1)
		}
	}
}

func Smooth(e0, e1, x float64) float64 {
	t := math.Max(0, math.Min(1, (x-e0)/(e1-e0)))
	return t * t * (3 - 2*t)
}

func Mix(a, b, t float64) float64 { return a + (b-a)*t }
