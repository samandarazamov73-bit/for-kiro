package main

import . "sovbuild/geo"

// lobby builds the recessed aluminium curtain wall with two double doors.
func (b *B) lobby() {
	m := b.Glazing
	pl := NewPlane(V3(GlazX, 0, 0), V3(0, -1, 0)) // s = -Y, faces -X
	const n = 8
	w := (RecS1 - RecS0) / n
	z0, z1, zt := FFL, RecTopZ, 3.50
	for i := 0; i < n; i++ {
		s0 := RecS0 + float64(i)*w
		c := b.rng.Intn(16)
		cu, cv := float64(c%4)*0.25, float64(c/4)*0.25
		g := []Vec3{pl.At(s0, z0, -0.05), pl.At(s0+w, z0, -0.05), pl.At(s0+w, z1, -0.05), pl.At(s0, z1, -0.05)}
		m.PolyUV(MGlass, g, []Vec2{V2(cu+0.01, cv+0.01), V2(cu+0.24, cv+0.01), V2(cu+0.24, cv+0.24), V2(cu+0.01, cv+0.24)})
	}
	for i := 0; i <= n; i++ {
		s := RecS0 + float64(i)*w
		fD(m, MFrame, pl, uvFrame, s-0.04, s+0.04, z0, z1, 0.07)
		fSn(m, MFrame, pl, uvFrame, s-0.04, z0, z1, -0.05, 0.07)
		fSp(m, MFrame, pl, uvFrame, s+0.04, z0, z1, -0.05, 0.07)
	}
	for _, r := range [][2]float64{{z0, z0 + 0.12}, {zt - 0.04, zt + 0.04}, {z1 - 0.08, z1}} {
		fD(m, MFrame, pl, uvFrame, RecS0, RecS1, r[0], r[1], 0.06)
		fZp(m, MFrame, pl, uvFrame, r[1], RecS0, RecS1, -0.05, 0.06)
		fZn(m, MFrame, pl, uvFrame, r[0], RecS0, RecS1, -0.05, 0.06)
	}
	// double doors in bays 2 and 5: meeting stiles, kick panels, push bars
	for _, bay := range []int{2, 5} {
		s0 := RecS0 + float64(bay)*w
		sc := s0 + w/2
		fD(m, MFrame, pl, uvFrame, sc-0.05, sc+0.05, z0+0.12, zt-0.04, 0.045)
		fSn(m, MFrame, pl, uvFrame, sc-0.05, z0+0.12, zt-0.04, -0.05, 0.045)
		fSp(m, MFrame, pl, uvFrame, sc+0.05, z0+0.12, zt-0.04, -0.05, 0.045)
		fD(m, MFrame, pl, uvFrame, s0+0.04, s0+w-0.04, z0+0.12, z0+0.45, 0.04)
		fZp(m, MFrame, pl, uvFrame, z0+0.45, s0+0.04, s0+w-0.04, -0.05, 0.04)
		for _, leaf := range [][2]float64{{s0 + 0.12, sc - 0.1}, {sc + 0.1, s0 + w - 0.12}} {
			p0, p1 := pl.At(leaf[0], z0+1.0, 0.11), pl.At(leaf[1], z0+1.0, 0.11)
			b.Glazing.Tube(MMetal, []Vec3{p0, p1}, 0.018, 6, true, true, 1, 0)
			for _, s := range leaf {
				b.Glazing.Tube(MMetal, []Vec3{pl.At(s, z0+1.0, 0.045), pl.At(s, z0+1.0, 0.11)}, 0.012, 5, false, false, 1, 0)
			}
		}
	}
}
