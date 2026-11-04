// grid composes several renders into one contact image (cols x rows, cell width w).
package main

import (
	"flag"
	"image"
	"image/color"
	"image/png"
	"os"
)

func main() {
	out := flag.String("out", "grid.png", "output")
	cols := flag.Int("cols", 2, "columns")
	w := flag.Int("w", 800, "cell width")
	flag.Parse()
	var imgs []image.Image
	for _, p := range flag.Args() {
		f, err := os.Open(p)
		if err != nil {
			panic(err)
		}
		im, err := png.Decode(f)
		f.Close()
		if err != nil {
			panic(err)
		}
		imgs = append(imgs, im)
	}
	b0 := imgs[0].Bounds()
	h := *w * b0.Dy() / b0.Dx()
	rows := (len(imgs) + *cols - 1) / *cols
	dst := image.NewRGBA(image.Rect(0, 0, *cols**w, rows*h))
	for i, im := range imgs {
		b := im.Bounds()
		ox, oy := (i%*cols)**w, (i / *cols)*h
		for y := 0; y < h; y++ {
			for x := 0; x < *w; x++ {
				// box filter downscale
				sx0, sx1 := x*b.Dx() / *w, (x+1)*b.Dx() / *w
				sy0, sy1 := y*b.Dy()/h, (y+1)*b.Dy()/h
				var r, g, bb, n uint32
				for sy := sy0; sy < max(sy1, sy0+1); sy++ {
					for sx := sx0; sx < max(sx1, sx0+1); sx++ {
						cr, cg, cb, _ := im.At(b.Min.X+sx, b.Min.Y+sy).RGBA()
						r, g, bb, n = r+cr, g+cg, bb+cb, n+1
					}
				}
				dst.Set(ox+x, oy+y, color.RGBA{uint8(r / n >> 8), uint8(g / n >> 8), uint8(bb / n >> 8), 255})
			}
		}
	}
	f, _ := os.Create(*out)
	png.Encode(f, dst)
	f.Close()
}
