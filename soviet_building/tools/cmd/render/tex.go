package main

import (
	"image"
	"image/color"
	"math"
)

type level struct {
	w, h int
	px   []float32
}

type Tex struct{ L []*level }

var srgbLUT [256]float32

func init() {
	for i := range srgbLUT {
		c := float64(i) / 255
		if c <= 0.04045 {
			srgbLUT[i] = float32(c / 12.92)
		} else {
			srgbLUT[i] = float32(math.Pow((c+0.055)/1.055, 2.4))
		}
	}
}

func newTex(img image.Image, srgb bool) *Tex {
	b := img.Bounds()
	w, h := b.Dx(), b.Dy()
	l0 := &level{w, h, make([]float32, w*h*4)}
	conv := func(c uint8) float32 {
		if srgb {
			return srgbLUT[c]
		}
		return float32(c) / 255
	}
	for y := 0; y < h; y++ {
		for x := 0; x < w; x++ {
			var r, g, bb, a uint8
			switch im := img.(type) {
			case *image.NRGBA:
				o := im.PixOffset(x+b.Min.X, y+b.Min.Y)
				r, g, bb, a = im.Pix[o], im.Pix[o+1], im.Pix[o+2], im.Pix[o+3]
			case *image.RGBA:
				o := im.PixOffset(x+b.Min.X, y+b.Min.Y)
				r, g, bb, a = im.Pix[o], im.Pix[o+1], im.Pix[o+2], im.Pix[o+3]
			case *image.YCbCr:
				yi, ci := im.YOffset(x+b.Min.X, y+b.Min.Y), im.COffset(x+b.Min.X, y+b.Min.Y)
				r, g, bb = color.YCbCrToRGB(im.Y[yi], im.Cb[ci], im.Cr[ci])
				a = 255
			default:
				c := color.NRGBAModel.Convert(img.At(x+b.Min.X, y+b.Min.Y)).(color.NRGBA)
				r, g, bb, a = c.R, c.G, c.B, c.A
			}
			o := 4 * (y*w + x)
			l0.px[o], l0.px[o+1], l0.px[o+2], l0.px[o+3] = conv(r), conv(g), conv(bb), float32(a)/255
		}
	}
	t := &Tex{L: []*level{l0}}
	for cur := l0; cur.w > 1 || cur.h > 1; {
		nw, nh := max(cur.w/2, 1), max(cur.h/2, 1)
		nl := &level{nw, nh, make([]float32, nw*nh*4)}
		for y := 0; y < nh; y++ {
			for x := 0; x < nw; x++ {
				for c := 0; c < 4; c++ {
					s := float32(0)
					for dy := 0; dy < 2; dy++ {
						for dx := 0; dx < 2; dx++ {
							sx, sy := min(2*x+dx, cur.w-1), min(2*y+dy, cur.h-1)
							s += cur.px[4*(sy*cur.w+sx)+c]
						}
					}
					nl.px[4*(y*nw+x)+c] = s / 4
				}
			}
		}
		t.L = append(t.L, nl)
		cur = nl
	}
	return t
}

func (l *level) bilinear(u, v float64) [4]float64 {
	x := u*float64(l.w) - 0.5
	y := v*float64(l.h) - 0.5
	x0, y0 := math.Floor(x), math.Floor(y)
	fx, fy := x-x0, y-y0
	ix, iy := int(x0), int(y0)
	wrap := func(i, n int) int { i %= n; if i < 0 { i += n }; return i }
	var out [4]float64
	for dy := 0; dy < 2; dy++ {
		for dx := 0; dx < 2; dx++ {
			w := (1 - fx + float64(dx)*(2*fx-1)) * (1 - fy + float64(dy)*(2*fy-1))
			o := 4 * (wrap(iy+dy, l.h)*l.w + wrap(ix+dx, l.w))
			for c := 0; c < 4; c++ {
				out[c] += w * float64(l.px[o+c])
			}
		}
	}
	return out
}

// Sample does trilinear filtering; lod in mip levels.
func (t *Tex) Sample(u, v, lod float64) [4]float64 {
	if lod < 0 {
		lod = 0
	}
	maxL := float64(len(t.L) - 1)
	if lod > maxL {
		lod = maxL
	}
	l0 := int(lod)
	f := lod - float64(l0)
	a := t.L[l0].bilinear(u, v)
	if f < 1e-3 || l0+1 >= len(t.L) {
		return a
	}
	b := t.L[l0+1].bilinear(u, v)
	for c := 0; c < 4; c++ {
		a[c] = a[c]*(1-f) + b[c]*f
	}
	return a
}

func (t *Tex) Size() float64 { return float64(max(t.L[0].w, t.L[0].h)) }
