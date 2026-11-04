package main

import "math"

type Env struct {
	SunDir, SunCol      V3
	SkyAmb, GroundAmb   V3
	Zenith, Horizon, Gr V3
	SM                  *VisBuf
	SCam                *Cam
}

var poisson = [12][2]float64{{-0.326, -0.406}, {-0.840, -0.074}, {-0.696, 0.457}, {-0.203, 0.621}, {0.962, -0.195}, {0.473, -0.480},
	{0.519, 0.767}, {0.185, -0.893}, {0.507, 0.064}, {0.896, 0.412}, {-0.322, -0.933}, {-0.792, -0.598}}

func (e *Env) shadow(P, N V3) float64 {
	ndl := dot(N, e.SunDir)
	off := 0.02 + 0.04*math.Min(3, math.Sqrt(math.Max(0, 1-ndl*ndl))/math.Max(ndl, 0.05))
	q := add(P, mul(N, 0.015))
	x, y, z, ok := e.SCam.Project(q)
	if !ok {
		return 1
	}
	zb := z - off*2/(e.SCam.Far-e.SCam.Near)
	lit := 0.0
	for _, p := range poisson {
		sx, sy := int(x+p[0]*1.6), int(y+p[1]*1.6)
		if sx < 0 || sy < 0 || sx >= e.SM.W || sy >= e.SM.H {
			lit++
			continue
		}
		if float64(e.SM.Z[sy*e.SM.W+sx]) >= zb {
			lit++
		}
	}
	return lit / float64(len(poisson))
}

func (e *Env) sky(d V3, rough float64) V3 {
	if d[1] < 0 {
		return lerp(e.Horizon, e.Gr, math.Min(1, -d[1]*4))
	}
	t := math.Pow(d[1], 0.6)
	s := lerp(e.Horizon, e.Zenith, t)
	// blur toward the average for rough surfaces
	return lerp(s, lerp(e.Horizon, e.Zenith, 0.5), rough)
}

func (e *Env) shade(P, N, V, alb V3, rough, met, occ float64) V3 {
	rough = math.Max(rough, 0.04)
	L := e.SunDir
	ndl := math.Max(dot(N, L), 0)
	ndv := math.Max(dot(N, V), 1e-4)
	F0 := lerp(V3{0.04, 0.04, 0.04}, alb, met)
	var direct V3
	if ndl > 0 {
		sh := e.shadow(P, N)
		if sh > 0 {
			H := norm(add(V, L))
			ndh, vdh := math.Max(dot(N, H), 0), math.Max(dot(V, H), 0)
			a2 := math.Pow(rough, 4)
			dd := ndh*ndh*(a2-1) + 1
			D := a2 / (math.Pi * dd * dd)
			k := (rough + 1) * (rough + 1) / 8
			G := ndv / (ndv*(1-k) + k) * ndl / (ndl*(1-k) + k)
			fw := math.Pow(1-vdh, 5)
			for c := 0; c < 3; c++ {
				F := F0[c] + (1-F0[c])*fw
				spec := D * G * F / (4*ndv*ndl + 1e-4)
				kd := (1 - F) * (1 - met)
				direct[c] = (kd*alb[c]/math.Pi + spec) * e.SunCol[c] * ndl * sh
			}
		}
	}
	amb := lerp(e.GroundAmb, e.SkyAmb, 0.5+0.5*N[1])
	R := sub(mul(N, 2*dot(N, V)), V)
	env := e.sky(R, rough)
	fr := math.Pow(1-ndv, 5)
	var out V3
	for c := 0; c < 3; c++ {
		Fr := F0[c] + (math.Max(1-rough, F0[c])-F0[c])*fr
		out[c] = direct[c] + alb[c]*(1-met)*amb[c]*occ + env[c]*Fr*occ*(1-0.6*rough)
	}
	return out
}

func aces(x float64) float64 {
	x *= 0.9
	return math.Max(0, math.Min(1, (x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14)))
}

func toSRGB(c float64) uint8 {
	if c <= 0.0031308 {
		c *= 12.92
	} else {
		c = 1.055*math.Pow(c, 1/2.4) - 0.055
	}
	return uint8(math.Max(0, math.Min(255, math.Round(c*255))))
}
