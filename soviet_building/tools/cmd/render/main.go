package main

import (
	"flag"
	"fmt"
	"image"
	"image/color"
	"image/png"
	"math"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// gl converts modelling coordinates (X right, Y back, Z up) to glTF space.
func gl(x, y, z float64) V3 { return V3{x, z, -y} }

type View struct {
	Name        string
	Pos, Target V3 // modelling coords
	Fov, Ortho  float64
}

var views = []View{
	{"reference_match", V3{-28.12, -50.87, 26.07}, V3{11.63, -8.97, 9.81}, 25.5, 0},
	{"front", V3{37.5, -76, 11}, V3{37.5, 0, 7}, 40, 0},
	{"front_left_34", V3{-22, -47, 19}, V3{32, -2, 6}, 40, 0},
	{"front_right_34", V3{97, -50, 21}, V3{42, -2, 6}, 40, 0},
	{"rear", V3{34, 76, 21}, V3{37.5, 7, 6}, 42, 0},
	{"top", V3{37.5, -2, 120}, V3{37.5, -2, 0}, 0, 50},
	{"closeup_ramp", V3{2.0, -13.0, 3.0}, V3{14.0, -2.5, 0.6}, 50, 0},
	{"closeup_ramp_foot", V3{22.5, -9.5, 2.6}, V3{12.0, -3.0, 0.7}, 50, 0},
	{"closeup_entrance", V3{13, -27, 7}, V3{24.5, -7, 2.4}, 45, 0},
	{"closeup_facade", V3{6, -14, 11}, V3{14, 0, 8.5}, 40, 0},
	{"roof_detail", V3{18, -14, 26}, V3{40, 8, 15}, 45, 0},
}

func main() {
	glb := flag.String("glb", "../export/SovietSchool.glb", "model")
	out := flag.String("out", "../renders", "output dir")
	w := flag.Int("w", 1600, "width")
	h := flag.Int("h", 900, "height")
	ss := flag.Int("ss", 2, "supersampling")
	only := flag.String("views", "", "comma separated view names")
	nocull := flag.Bool("nocull", false, "disable back-face culling")
	flag.Parse()
	t0 := time.Now()
	tris, mats, err := loadGLB(*glb)
	if err != nil {
		panic(err)
	}
	fmt.Printf("loaded %d tris, %d materials in %v\n", len(tris), len(mats), time.Since(t0))
	ground := &Mat{Name: "ground", Base: [4]float64{0.93, 0.93, 0.92, 1}, Rough: 1, NScale: 1, Ground: true}
	mats = append(mats, ground)
	gi := len(mats) - 1
	g0, g1, g2, g3 := gl(-200, -200, -0.02), gl(300, -200, -0.02), gl(300, 200, -0.02), gl(-200, 200, -0.02)
	up := V3{0, 1, 0}
	tris = append(tris, Tri{P: [3]V3{g0, g1, g2}, N: [3]V3{up, up, up}, Mat: gi}, Tri{P: [3]V3{g0, g2, g3}, N: [3]V3{up, up, up}, Mat: gi})

	env := &Env{SunDir: norm(gl(-0.42, -0.62, 0.78)), SunCol: V3{3.3, 3.15, 2.95},
		SkyAmb: V3{0.42, 0.45, 0.50}, GroundAmb: V3{0.30, 0.29, 0.28},
		Zenith: V3{0.30, 0.45, 0.75}, Horizon: V3{0.80, 0.84, 0.90}, Gr: V3{0.30, 0.29, 0.27}}
	center := gl(37.5, -2, 6)
	sc := &Cam{Pos: add(center, mul(env.SunDir, 150)), Target: center, OrthoH: 105, W: 6144, H: 6144, Near: 1, Far: 320}
	sc.Setup()
	env.SCam = sc
	env.SM = newVisBuf(sc.W, sc.H)
	rasterize(sc, tris, env.SM, false)
	fmt.Printf("shadow map %v\n", time.Since(t0))
	os.MkdirAll(*out, 0o755)
	for _, v := range views {
		if *only != "" && !strings.Contains(","+*only+",", ","+v.Name+",") {
			continue
		}
		c := &Cam{Pos: gl(v.Pos[0], v.Pos[1], v.Pos[2]), Target: gl(v.Target[0], v.Target[1], v.Target[2]), FovY: v.Fov, OrthoH: v.Ortho,
			W: *w * *ss, H: *h * *ss, Near: 0.3, Far: 600}
		if v.Ortho > 0 {
			c.Up = V3{0, 0, -1}
			c.Near = 1
		}
		c.Setup()
		img := render(c, tris, mats, env, *ss, !*nocull)
		f, _ := os.Create(filepath.Join(*out, "view_"+v.Name+".png"))
		png.Encode(f, img)
		f.Close()
		fmt.Printf("%s done %v\n", v.Name, time.Since(t0))
	}
}

func render(c *Cam, tris []Tri, mats []*Mat, env *Env, ss int, cull bool) image.Image {
	vb := newVisBuf(c.W, c.H)
	rasterize(c, tris, vb, cull)
	g := buildGBuf(c, tris, mats, vb)
	ao := ssao(c, g, vb.W, vb.H)
	W, H := c.W/ss, c.H/ss
	img := image.NewNRGBA(image.Rect(0, 0, W, H))
	parallelRows(H, func(y int) {
		for x := 0; x < W; x++ {
			var acc V3
			for dy := 0; dy < ss; dy++ {
				for dx := 0; dx < ss; dx++ {
					i := (y*ss+dy)*c.W + x*ss + dx
					if !g.Valid[i] {
						acc = add(acc, V3{1, 1, 1})
						continue
					}
					V := norm(sub(c.Pos, g.P[i]))
					col := env.shade(g.P[i], g.N[i], V, g.Alb[i], g.Rough[i], g.Met[i], g.AO[i]*ao[i])
					acc = add(acc, V3{aces(col[0]), aces(col[1]), aces(col[2])})
				}
			}
			acc = mul(acc, 1/float64(ss*ss))
			img.Set(x, y, color.NRGBA{toSRGB(acc[0]), toSRGB(acc[1]), toSRGB(acc[2]), 255})
		}
	})
	return img
}

var hemi [16]V3

func init() {
	for k := range hemi {
		u1 := (float64(k) + 0.5) / float64(len(hemi))
		u2 := math.Mod(float64(k)*0.618034, 1)
		r := math.Sqrt(u1)
		a := 2 * math.Pi * u2
		hemi[k] = V3{r * math.Cos(a), r * math.Sin(a), math.Sqrt(1 - u1)}
	}
}

func ssao(c *Cam, g *GBuf, W, H int) []float64 {
	ao := make([]float64, W*H)
	parallelRows(H, func(y int) {
		for x := 0; x < W; x++ {
			i := y*W + x
			ao[i] = 1
			if !g.Valid[i] {
				continue
			}
			P, N := g.P[i], g.N[i]
			t := norm(cross(N, V3{0.37, 0.71, 0.6}))
			b := cross(N, t)
			rot := float64((x*7+y*13)%16) / 16 * 2 * math.Pi
			cr, sr := math.Cos(rot), math.Sin(rot)
			occ := 0.0
			for k, d := range hemi {
				dx, dy := d[0]*cr-d[1]*sr, d[0]*sr+d[1]*cr
				dir := add(add(mul(t, dx), mul(b, dy)), mul(N, d[2]))
				r := 0.9 * math.Pow((float64(k)+1)/float64(len(hemi)), 1.6)
				S := add(add(P, mul(N, 0.02)), mul(dir, r))
				sx, sy, _, ok := c.Project(S)
				if !ok || sx < 0 || sy < 0 || int(sx) >= W || int(sy) >= H {
					continue
				}
				j := int(sy)*W + int(sx)
				if !g.Valid[j] {
					continue
				}
				dS, dQ := c.ViewDepth(S), c.ViewDepth(g.P[j])
				if dQ < dS-0.015 && dS-dQ < 1.2 {
					occ++
				}
			}
			ao[i] = 1 - 0.85*occ/float64(len(hemi))
		}
	})
	return ao
}
