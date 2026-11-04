package tex

import (
	"bufio"
	"image"
	"image/color"
	"image/jpeg"
	"image/png"
	"math"
	"os"
	"path/filepath"
)

func c8(v float64) uint8 { return uint8(math.Max(0, math.Min(255, math.Round(v*255)))) }

// LinToSRGB converts a linear value to sRGB encoding.
func LinToSRGB(c float64) float64 {
	c = math.Max(0, math.Min(1, c))
	if c <= 0.0031308 {
		return c * 12.92
	}
	return 1.055*math.Pow(c, 1/2.4) - 0.055
}

func writeImg(path string, img image.Image, jpgQ int) error {
	os.MkdirAll(filepath.Dir(path), 0o755)
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()
	w := bufio.NewWriterSize(f, 1<<20)
	if jpgQ > 0 {
		err = jpeg.Encode(w, img, &jpeg.Options{Quality: jpgQ})
	} else {
		enc := png.Encoder{CompressionLevel: png.BestCompression}
		err = enc.Encode(w, img)
	}
	if err != nil {
		return err
	}
	return w.Flush()
}

// SaveRGB writes three channels (already encoded 0..1) as PNG (and JPEG if jpgQ>0).
func SaveRGB(path string, r, g, b *F, jpgQ int) error {
	img := image.NewRGBA(image.Rect(0, 0, r.W, r.H))
	Par(r.H, func(y int) {
		for x := 0; x < r.W; x++ {
			i := y*r.W + x
			img.SetRGBA(x, y, color.RGBA{c8(r.P[i]), c8(g.P[i]), c8(b.P[i]), 255})
		}
	})
	if err := writeImg(path, img, 0); err != nil {
		return err
	}
	if jpgQ > 0 {
		return writeImg(path[:len(path)-4]+".jpg", img, jpgQ)
	}
	return nil
}

// SaveGray writes a single channel PNG.
func SaveGray(path string, f *F) error {
	img := image.NewGray(image.Rect(0, 0, f.W, f.H))
	Par(f.H, func(y int) {
		for x := 0; x < f.W; x++ {
			img.Pix[y*img.Stride+x] = c8(f.P[y*f.W+x])
		}
	})
	return writeImg(path, img, 0)
}

// NormalFromHeight builds an OpenGL convention (green up) tangent space normal map.
// strength = height units -> slope per pixel.
func NormalFromHeight(h *F, strength float64) (r, g, b *F) {
	r, g, b = NewF(h.W, h.H), NewF(h.W, h.H), NewF(h.W, h.H)
	Par(h.H, func(y int) {
		for x := 0; x < h.W; x++ {
			dx := (h.At(x+1, y-1) + 2*h.At(x+1, y) + h.At(x+1, y+1) - h.At(x-1, y-1) - 2*h.At(x-1, y) - h.At(x-1, y+1)) / 8
			dy := (h.At(x-1, y+1) + 2*h.At(x, y+1) + h.At(x+1, y+1) - h.At(x-1, y-1) - 2*h.At(x, y-1) - h.At(x+1, y-1)) / 8
			nx, ny, nz := -dx*strength, dy*strength, 1.0
			l := math.Sqrt(nx*nx + ny*ny + nz*nz)
			i := y*h.W + x
			r.P[i], g.P[i], b.P[i] = nx/l*0.5+0.5, ny/l*0.5+0.5, nz/l*0.5+0.5
		}
	})
	return
}
