package main

import "math"

func add(a, b V3) V3          { return V3{a[0] + b[0], a[1] + b[1], a[2] + b[2]} }
func sub(a, b V3) V3          { return V3{a[0] - b[0], a[1] - b[1], a[2] - b[2]} }
func mul(a V3, s float64) V3  { return V3{a[0] * s, a[1] * s, a[2] * s} }
func dot(a, b V3) float64     { return a[0]*b[0] + a[1]*b[1] + a[2]*b[2] }
func cross(a, b V3) V3        { return V3{a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0]} }
func length(a V3) float64     { return math.Sqrt(dot(a, a)) }
func norm(a V3) V3            { l := length(a); if l < 1e-12 { return V3{0, 1, 0} }; return mul(a, 1/l) }
func lerp(a, b V3, t float64) V3 { return add(a, mul(sub(b, a), t)) }

type M4 [16]float64 // row-major

func (m M4) apply(p V3, w float64) [4]float64 {
	var o [4]float64
	for r := 0; r < 4; r++ {
		o[r] = m[4*r]*p[0] + m[4*r+1]*p[1] + m[4*r+2]*p[2] + m[4*r+3]*w
	}
	return o
}

func mmul(a, b M4) M4 {
	var o M4
	for r := 0; r < 4; r++ {
		for c := 0; c < 4; c++ {
			for k := 0; k < 4; k++ {
				o[4*r+c] += a[4*r+k] * b[4*k+c]
			}
		}
	}
	return o
}

// Cam: glTF space (Y up). Perspective or orthographic.
type Cam struct {
	Pos, Target, Up V3
	FovY            float64 // degrees (perspective)
	OrthoH          float64 // >0 => orthographic with this view height (m)
	W, H            int
	Near, Far       float64
	View, VP        M4
	right, up, fwd  V3
}

func (c *Cam) Setup() {
	if c.Up == (V3{}) {
		c.Up = V3{0, 1, 0}
	}
	f := norm(sub(c.Target, c.Pos))
	r := norm(cross(f, c.Up))
	u := cross(r, f)
	c.right, c.up, c.fwd = r, u, f
	c.View = M4{r[0], r[1], r[2], -dot(r, c.Pos), u[0], u[1], u[2], -dot(u, c.Pos), -f[0], -f[1], -f[2], dot(f, c.Pos), 0, 0, 0, 1}
	a := float64(c.W) / float64(c.H)
	n, fa := c.Near, c.Far
	var P M4
	if c.OrthoH > 0 {
		h := c.OrthoH / 2
		w := h * a
		P = M4{1 / w, 0, 0, 0, 0, 1 / h, 0, 0, 0, 0, -2 / (fa - n), -(fa + n) / (fa - n), 0, 0, 0, 1}
	} else {
		t := 1 / math.Tan(c.FovY*math.Pi/360)
		P = M4{t / a, 0, 0, 0, 0, t, 0, 0, 0, 0, -(fa + n) / (fa - n), -2 * fa * n / (fa - n), 0, 0, -1, 0}
	}
	c.VP = mmul(P, c.View)
}

// Project returns pixel coordinates and NDC depth; ok=false behind the camera.
func (c *Cam) Project(p V3) (x, y, z float64, ok bool) {
	q := c.VP.apply(p, 1)
	if q[3] <= 1e-6 {
		return 0, 0, 0, false
	}
	x = (q[0]/q[3]*0.5 + 0.5) * float64(c.W)
	y = (0.5 - q[1]/q[3]*0.5) * float64(c.H)
	return x, y, q[2] / q[3], true
}

// ViewDepth is the distance along the view direction.
func (c *Cam) ViewDepth(p V3) float64 { return dot(sub(p, c.Pos), c.fwd) }
