package geo

import "math"

// Vec3 is a 3D vector in modelling space (X right, Y back, Z up, metres).
type Vec3 struct{ X, Y, Z float64 }

// Vec2 is a texture coordinate (OpenGL / Blender convention: v points up).
type Vec2 struct{ U, V float64 }

func V3(x, y, z float64) Vec3 { return Vec3{x, y, z} }
func V2(u, v float64) Vec2     { return Vec2{u, v} }

func (a Vec3) Add(b Vec3) Vec3      { return Vec3{a.X + b.X, a.Y + b.Y, a.Z + b.Z} }
func (a Vec3) Sub(b Vec3) Vec3      { return Vec3{a.X - b.X, a.Y - b.Y, a.Z - b.Z} }
func (a Vec3) Mul(s float64) Vec3   { return Vec3{a.X * s, a.Y * s, a.Z * s} }
func (a Vec3) Dot(b Vec3) float64   { return a.X*b.X + a.Y*b.Y + a.Z*b.Z }
func (a Vec3) Len() float64         { return math.Sqrt(a.Dot(a)) }
func (a Vec3) Neg() Vec3            { return Vec3{-a.X, -a.Y, -a.Z} }
func (a Vec3) Hadamard(b Vec3) Vec3 { return Vec3{a.X * b.X, a.Y * b.Y, a.Z * b.Z} }
func (a Vec3) Cross(b Vec3) Vec3 {
	return Vec3{a.Y*b.Z - a.Z*b.Y, a.Z*b.X - a.X*b.Z, a.X*b.Y - a.Y*b.X}
}
func (a Vec3) Norm() Vec3 {
	l := a.Len()
	if l < 1e-12 {
		return Vec3{0, 0, 1}
	}
	return a.Mul(1 / l)
}
func Lerp3(a, b Vec3, t float64) Vec3 { return a.Add(b.Sub(a).Mul(t)) }

func (a Vec2) Add(b Vec2) Vec2    { return Vec2{a.U + b.U, a.V + b.V} }
func (a Vec2) Sub(b Vec2) Vec2    { return Vec2{a.U - b.U, a.V - b.V} }
func (a Vec2) Mul(s float64) Vec2 { return Vec2{a.U * s, a.V * s} }

func Clamp(x, lo, hi float64) float64 {
	if x < lo {
		return lo
	}
	if x > hi {
		return hi
	}
	return x
}

// RotZ rotates a vector around the Z axis by angle a (radians).
func (a Vec3) RotZ(ang float64) Vec3 {
	c, s := math.Cos(ang), math.Sin(ang)
	return Vec3{a.X*c - a.Y*s, a.X*s + a.Y*c, a.Z}
}
