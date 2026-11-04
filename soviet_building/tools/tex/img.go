package tex

import (
	"math"
	"runtime"
	"sync"
)

// F is a single channel float map (row 0 = top of the image).
type F struct {
	W, H int
	P    []float64
}

func NewF(w, h int) *F { return &F{w, h, make([]float64, w*h)} }

func (f *F) At(x, y int) float64 {
	x, y = ((x%f.W)+f.W)%f.W, ((y%f.H)+f.H)%f.H
	return f.P[y*f.W+x]
}

// Bilinear samples with wrap at (u,v) in [0,1) image space (v down).
func (f *F) Bilinear(u, v float64) float64 {
	x, y := u*float64(f.W)-0.5, v*float64(f.H)-0.5
	x0, y0 := math.Floor(x), math.Floor(y)
	fx, fy := x-x0, y-y0
	ix, iy := int(x0), int(y0)
	a := f.At(ix, iy) + (f.At(ix+1, iy)-f.At(ix, iy))*fx
	b := f.At(ix, iy+1) + (f.At(ix+1, iy+1)-f.At(ix, iy+1))*fx
	return a + (b-a)*fy
}

// Par runs fn(y) for all rows in parallel.
func Par(h int, fn func(y int)) {
	var wg sync.WaitGroup
	ch := make(chan int, h)
	for y := 0; y < h; y++ {
		ch <- y
	}
	close(ch)
	for i := 0; i < runtime.NumCPU(); i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for y := range ch {
				fn(y)
			}
		}()
	}
	wg.Wait()
}

// Fill evaluates fn(u, v, x, y) for every pixel; u,v in [0,1) with v UP (texture space).
func (f *F) Fill(fn func(u, v float64, x, y int) float64) *F {
	Par(f.H, func(y int) {
		for x := 0; x < f.W; x++ {
			u := (float64(x) + 0.5) / float64(f.W)
			v := 1 - (float64(y)+0.5)/float64(f.H)
			f.P[y*f.W+x] = fn(u, v, x, y)
		}
	})
	return f
}

// Blur is a separable wrap-around box blur applied n times (approx. gaussian).
func (f *F) Blur(r, n int) *F {
	tmp := make([]float64, len(f.P))
	for it := 0; it < n; it++ {
		Par(f.H, func(y int) {
			s := 0.0
			for k := -r; k <= r; k++ {
				s += f.At(k, y)
			}
			for x := 0; x < f.W; x++ {
				tmp[y*f.W+x] = s / float64(2*r+1)
				s += f.At(x+r+1, y) - f.At(x-r, y)
			}
		})
		copy(f.P, tmp)
		Par(f.W, func(x int) {
			s := 0.0
			for k := -r; k <= r; k++ {
				s += f.At(x, k)
			}
			for y := 0; y < f.H; y++ {
				tmp[y*f.W+x] = s / float64(2*r+1)
				s += f.At(x, y+r+1) - f.At(x, y-r)
			}
		})
		copy(f.P, tmp)
	}
	return f
}

func (f *F) Clone() *F { g := NewF(f.W, f.H); copy(g.P, f.P); return g }
