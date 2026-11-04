// Package tex provides tileable procedural noise and float image helpers.
package tex

import (
	"math"
	"math/rand"
)

// Noise is a periodic 2D gradient noise (period in lattice cells).
type Noise struct {
	perm [512]int
	gx   [256]float64
	gy   [256]float64
}

func NewNoise(seed int64) *Noise {
	r := rand.New(rand.NewSource(seed))
	n := &Noise{}
	p := r.Perm(256)
	for i := 0; i < 512; i++ {
		n.perm[i] = p[i&255]
	}
	for i := 0; i < 256; i++ {
		a := r.Float64() * 2 * math.Pi
		n.gx[i], n.gy[i] = math.Cos(a), math.Sin(a)
	}
	return n
}

func fade(t float64) float64 { return t * t * t * (t*(t*6-15) + 10) }

// At samples noise at (x,y) in lattice units, periodic with period p (cells).
func (n *Noise) At(x, y float64, p int) float64 {
	xi, yi := math.Floor(x), math.Floor(y)
	fx, fy := x-xi, y-yi
	ix, iy := int(xi), int(yi)
	mod := func(a int) int { a %= p; if a < 0 { a += p }; return a }
	x0, x1, y0, y1 := mod(ix), mod(ix+1), mod(iy), mod(iy+1)
	g := func(cx, cy int, dx, dy float64) float64 {
		h := n.perm[(n.perm[cx&255]+cy)&511] & 255
		return n.gx[h]*dx + n.gy[h]*dy
	}
	u, v := fade(fx), fade(fy)
	a := g(x0, y0, fx, fy) + u*(g(x1, y0, fx-1, fy)-g(x0, y0, fx, fy))
	b := g(x0, y1, fx, fy-1) + u*(g(x1, y1, fx-1, fy-1)-g(x0, y1, fx, fy-1))
	return (a + v*(b-a)) * 1.414
}

// FBM: tileable fractal noise on the unit square [0,1)^2; base = cells across.
func (n *Noise) FBM(u, v float64, base, oct int, gain float64) float64 {
	s, amp, norm := 0.0, 1.0, 0.0
	f := base
	for o := 0; o < oct; o++ {
		s += amp * n.At(u*float64(f), v*float64(f), f)
		norm += amp
		amp *= gain
		f *= 2
	}
	return s / norm
}

// Worley returns distances to the nearest and second nearest feature points
// (tileable, cells across = base) and the id of the nearest cell.
func Worley(u, v float64, base int, seed int64) (d1, d2 float64, id int) {
	x, y := u*float64(base), v*float64(base)
	ix, iy := int(math.Floor(x)), int(math.Floor(y))
	d1, d2 = 9, 9
	for dy := -1; dy <= 1; dy++ {
		for dx := -1; dx <= 1; dx++ {
			cx, cy := ix+dx, iy+dy
			mx, my := ((cx%base)+base)%base, ((cy%base)+base)%base
			h := hash3(mx, my, seed)
			px := float64(cx) + float64(h&1023)/1023
			py := float64(cy) + float64((h>>10)&1023)/1023
			d := math.Hypot(px-x, py-y)
			if d < d1 {
				d2, d1, id = d1, d, mx+my*base
			} else if d < d2 {
				d2 = d
			}
		}
	}
	return
}

func hash3(x, y int, s int64) uint32 {
	h := uint32(x)*374761393 + uint32(y)*668265263 + uint32(s)*2246822519
	h = (h ^ (h >> 13)) * 1274126177
	return h ^ (h >> 16)
}

// Hash01 is a deterministic random value in [0,1) for integer coordinates.
func Hash01(x, y int, s int64) float64 { return float64(hash3(x, y, s)&0xffffff) / float64(0x1000000) }
