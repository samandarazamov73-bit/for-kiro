package main

import (
	"math"
	"math/rand"

	. "sovbuild/tex"
)

type ConcreteOpts struct {
	Name             string
	Size             int
	MU, MV           float64 // metres covered by one repeat
	PU, PV           int     // panel grid inside one repeat (0 = no joints)
	Base             [3]float64
	PanelVar         float64
	Windows          bool // window-aligned streaks and corner cracks (facade panel)
	Streak, Dirt     float64
	Pores, Mottle    float64
	Rough            float64
	Cracks           int
	Seed             int64
	NormalStrength   float64
	Broom            float64 // broom finish grooves along v (paving)
	GrooveW          float64 // joint half width (m), default 7 mm
	JointMix         float64 // how dark the joint filler reads (0..1), default 1
	Stain            float64 // large soft weathering patches
}

// window geometry of the facade panel texture (2 bays x 2 floors)
const (
	winHW  = 2.45 / 2 / 6.0
	sillHW = (2.45/2 + 0.05) / 6.0
	winVB  = 0.5 / 6.6
	winVT  = (0.5 + 2.55) / 6.6
)

func frac(x float64) float64 { return x - math.Floor(x) }

func concrete(o ConcreteOpts) *Set {
	s := NewSet(o.Name, o.Size)
	n1, n2, n3 := NewNoise(o.Seed), NewNoise(o.Seed+11), NewNoise(o.Seed+23)
	r := rand.New(rand.NewSource(o.Seed))
	W := float64(o.Size)
	// crack mask: from window surround corners (stress cracks) + random hairlines
	cr := NewF(o.Size, o.Size)
	if o.Windows {
		for b := 0; b < 2; b++ {
			for f := 0; f < 2; f++ {
				uc := 0.25 + 0.5*float64(b)
				for _, c := range [][3]float64{{-winHW, winVT, -2.4}, {winHW, winVT, -0.7}, {-sillHW, winVB, 2.4}, {sillHW, winVB, 0.7}} {
					if r.Float64() < 0.55 {
						x := (uc + c[0]) * W
						y := (1 - (c[1] + 0.5*float64(f))) * W
						cr.Crack(r, x, y, c[2]+(r.Float64()-0.5)*0.5, 20+r.Intn(50), 0.9, 3, 2)
					}
				}
			}
		}
	}
	for i := 0; i < o.Cracks; i++ {
		cr.Crack(r, r.Float64()*W, r.Float64()*W, r.Float64()*2*math.Pi, 30+r.Intn(90), 0.8, 3, 2)
	}
	cr.Blur(1, 1)
	s.Height.Fill(func(u, v float64, x, y int) float64 { return 0 })
	Par(o.Size, func(y int) {
		for x := 0; x < o.Size; x++ {
			u := (float64(x) + 0.5) / W
			v := 1 - (float64(y)+0.5)/W
			i := y*o.Size + x
			o.pixel(s, i, u, v, n1, n2, n3, cr.P[i])
		}
	})
	s.NormalStrength = o.NormalStrength
	return s
}

func sq(x float64) float64 { return x * x }
func clamp01(x float64) float64 { return math.Max(0, math.Min(1, x)) }

func (o ConcreteOpts) pixel(s *Set, i int, u, v float64, n1, n2, n3 *Noise, crack float64) {
	groove, dust, runTop, tone, jd := 0.0, 0.0, 0.0, 0.0, 9.0
	if o.PU > 0 {
		fu, fv := u*float64(o.PU), v*float64(o.PV)
		tone = (Hash01(int(fu), int(fv), o.Seed) - 0.5) * 2 * o.PanelVar
		ju := math.Abs(fu-math.Round(fu)) / float64(o.PU) * o.MU
		jv := math.Abs(fv-math.Round(fv)) / float64(o.PV) * o.MV
		jd = math.Min(ju, jv)
		gw := o.GrooveW
		if gw == 0 {
			gw = 0.007
		}
		groove = 1 - Smooth(gw, gw+0.009, jd)
		above := frac(fv) / float64(o.PV) * o.MV
		below := (1 - frac(fv)) / float64(o.PV) * o.MV
		dust = math.Exp(-above / 0.04)
		runTop = math.Exp(-below / 0.7)
	}
	sn := n1.FBMA(u, v, 70, 3, 4, 0.6)
	smask := Smooth(0.02, 0.5, sn)
	wsrc, pier := 0.0, 0.0
	if o.Windows {
		pd := 1.0
		for b := 0; b < 2; b++ {
			uc := 0.25 + 0.5*float64(b)
			du := math.Abs(u - uc)
			pd = math.Min(pd, du)
			inside := Smooth(sillHW+0.004, sillHW-0.012, du)
			ends := math.Exp(-sq((du - sillHW + 0.012) / 0.011))
			for f := 0; f < 2; f++ {
				tm := frac(winVB+0.5*float64(f)-v) * o.MV
				if tm < 1.8 {
					wsrc = math.Max(wsrc, (inside*0.55+ends)*math.Exp(-tm/0.6))
				}
			}
		}
		pier = Smooth(winHW+0.004, winHW+0.03, pd)
	}
	st := clamp01(o.Streak * smask * (0.18 + 0.9*wsrc + 0.35*pier + 0.45*runTop))
	m := o.Mottle * (0.06*n1.FBM(u, v, 3, 4, 0.5) + 0.035*n2.FBM(u, v, 11, 4, 0.55) + 0.025*n3.FBM(u, v, 48, 3, 0.5))
	fg := n3.FBM(u, v, o.Size/8, 2, 0.5)
	ag := n2.At(u*float64(o.Size/3), v*float64(o.Size/3), o.Size/3)
	speck := 0.0
	if ag > 0.55 {
		speck = 0.05
	} else if ag < -0.6 {
		speck = -0.06
	}
	pore := 0.0
	if o.Pores > 0 {
		d1, _, id := Worley(u, v, o.Size/4, o.Seed+5)
		if Hash01(id, 1, o.Seed) < 0.32*o.Pores {
			rr := 0.12 + 0.14*Hash01(id, 2, o.Seed)
			pore = 1 - Smooth(rr*0.5, rr, d1)
		}
		d2, _, id2 := Worley(u, v, o.Size/18, o.Seed+7)
		if Hash01(id2, 3, o.Seed) < 0.12*o.Pores {
			rr := 0.08 + 0.08*Hash01(id2, 4, o.Seed)
			pore = math.Max(pore, 1-Smooth(rr*0.6, rr, d2))
		}
	}
	lowDirt := Smooth(-0.2, 0.6, n2.FBM(u, v, 4, 3, 0.5))
	ef := Smooth(0.35, 0.75, n3.FBM(u, v, 6, 4, 0.6)) * 0.07 * math.Exp(-jd/0.2)
	broom := 0.0
	if o.Broom > 0 {
		broom = o.Broom * n1.FBMA(u, v, o.Size/3, 6, 2, 0.5)
	}
	dirtCol := [3]float64{0.34, 0.32, 0.29}
	mastic := [3]float64{0.26, 0.25, 0.24}
	stain := Smooth(0.1, 0.55, n3.FBM(u+0.37, v+0.11, 3, 5, 0.6)) * o.Stain
	k := clamp01(st*0.6 + dust*0.22*o.Dirt + o.Dirt*0.12*lowDirt + 0.3*stain)
	jm := o.JointMix
	if jm == 0 {
		jm = 1
	}
	for c, ch := range []*F{s.R, s.G, s.B} {
		col := o.Base[c] * (1 + tone + m + 0.035*fg + speck)
		col = Mix(col, dirtCol[c], k)
		col *= (1 - 0.28*pore) * (1 - 0.4*crack)
		col = Mix(col, Mix(col*0.8, mastic[c], jm), groove) + ef
		ch.P[i] = clamp01(col)
	}
	s.Height.P[i] = 0.35*m/0.1 + 0.12*fg + 0.06*speck/0.05 - 0.5*pore - 0.7*crack - 1.3*groove*jm + broom
	s.Rough.P[i] = clamp01(o.Rough + 0.05*fg - 0.09*st + 0.04*pore - 0.18*groove + 0.3*broom)
	s.AO.P[i] = clamp01(1 - 0.5*groove - 0.35*pore - 0.45*crack - 0.04*st - 0.04*lowDirt)
	s.Metal.P[i] = 0
}
