// sheet composes a labelled-by-order contact sheet of texture maps (downscaled).
package main

import (
	"flag"
	"image"
	"image/color"
	_ "image/jpeg"
	"image/png"
	"os"
	"path/filepath"
	"strings"
)

func main() {
	dir := flag.String("dir", "../textures", "texture folder")
	out := flag.String("out", "../renders/wip/sheet.png", "output")
	cell := flag.Int("cell", 256, "cell size")
	suf := flag.String("suffix", "_BaseColor.png", "comma separated suffixes (one row each)")
	crop := flag.Float64("crop", 1, "fraction of the texture shown (1 = whole)")
	flag.Parse()
	names, _ := filepath.Glob(filepath.Join(*dir, "*_BaseColor.png"))
	sufs := strings.Split(*suf, ",")
	W, H := *cell*len(names), *cell*len(sufs)
	dst := image.NewRGBA(image.Rect(0, 0, W, H))
	for ci, n := range names {
		base := strings.TrimSuffix(n, "_BaseColor.png")
		for ri, s := range sufs {
			f, err := os.Open(base + s)
			if err != nil {
				continue
			}
			img, _, err := image.Decode(f)
			f.Close()
			if err != nil {
				continue
			}
			b := img.Bounds()
			for y := 0; y < *cell; y++ {
				for x := 0; x < *cell; x++ {
					sx := b.Min.X + int(float64(x)/float64(*cell)*float64(b.Dx())**crop)
					sy := b.Min.Y + int(float64(y)/float64(*cell)*float64(b.Dy())**crop)
					r, g, bb, _ := img.At(sx, sy).RGBA()
					dst.Set(ci**cell+x, ri**cell+y, color.RGBA{uint8(r >> 8), uint8(g >> 8), uint8(bb >> 8), 255})
				}
			}
		}
	}
	os.MkdirAll(filepath.Dir(*out), 0o755)
	f, _ := os.Create(*out)
	png.Encode(f, dst)
	f.Close()
}
