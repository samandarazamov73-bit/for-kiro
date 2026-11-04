package main

import . "sovbuild/geo"

func (b *B) roofs() {
	in := 0.30
	b.roofSurface(in, MainLen-in, in, MainDepth-in, MainRoofZ, 24, 4,
		[]Vec2{{12.7, MainDepth / 2}, {31.3, MainDepth / 2}, {43.7, MainDepth / 2}, {62.3, MainDepth / 2}}, 0.05)
	b.roofSurface(EntX0+in, EntX1-in, EntY0+in, 0, EntRoofZ, 4, 6, []Vec2{{33.0, (EntY0 + in) / 2}}, 0.04)
	// flashing upstand where the entrance roof meets the main facade
	b.Roof.Box(MRoof, V3(EntX0+in, -0.06, EntRoofZ), V3(EntX1-in, 0, EntRoofZ+0.25), FYn|FZp, uvRoof)
	z := MainRoofZ
	for _, v := range [][3]float64{{12.5, 9.5, 0.9}, {19.5, 6.0, 0.8}, {26.0, 10.5, 0.9}, {50.5, 11.0, 0.8},
		{55.0, 5.0, 0.9}, {57.5, 9.0, 0.8}, {64.5, 10.5, 0.9}, {7.0, 11.5, 0.8}, {69.5, 4.5, 0.8}} {
		b.vent(v[0], v[1], z, 0.8, 0.8, v[2])
	}
	b.stairHouse(33.0, 7.8, z)
	b.stairHouse(66.0, 7.2, z)
	b.ventChamber(41.0, 11.2, z)
	// exhaust pipe with conical hat near the front edge
	s := b.RoofStruct
	s.Tube(MMetal, []Vec3{V3(7.5, 3.0, z-0.05), V3(7.5, 3.0, z+1.3)}, 0.09, 10, false, false, 1, 0)
	s.Tube(MMetal, []Vec3{V3(7.5, 3.0, z+1.42), V3(7.5, 3.0, z+1.43)}, 0.2, 10, true, false, 1, 0)
	for k := 0; k < 3; k++ {
		a := float64(k) * 2.0944
		p := V3(7.5, 3.0, z+1.3)
		q := p.Add(V3(0.18*cosf(a), 0.18*sinf(a), 0.12))
		s.Tube(MMetal, []Vec3{p.Add(V3(0.08*cosf(a), 0.08*sinf(a), 0)), q}, 0.01, 4, false, false, 1, 0)
	}
	// TV / radio antenna mast with guy-free cross bars
	s.Tube(MMetal, []Vec3{V3(31.0, 9.8, z), V3(31.0, 9.8, z+4.2)}, 0.03, 8, false, true, 1, 0)
	for k, h := range []float64{3.0, 3.6, 4.0} {
		w := 0.9 - 0.2*float64(k)
		s.Tube(MMetal, []Vec3{V3(31.0-w, 9.8, z+h), V3(31.0+w, 9.8, z+h)}, 0.012, 5, true, true, 1, 0)
	}
	s.Box(MMetal, V3(30.85, 9.65, z), V3(31.15, 9.95, z+0.1), FXn|FXp|FYn|FYp|FZp, WorldUV(1, 1, 0, 0))
	b.roofRailing()
	// entrance block roof: two vent stacks and a roof hatch
	b.vent(30.2, -15.8, EntRoofZ, 0.7, 0.7, 0.7)
	b.vent(36.4, -5.2, EntRoofZ, 0.7, 0.7, 0.7)
	s.Box(MWeather, V3(34.6, -12.6, EntRoofZ-0.05), V3(35.6, -11.6, EntRoofZ+0.5), FXn|FXp|FYn|FYp, uvWeather)
	s.Box(MMetal, V3(34.55, -12.65, EntRoofZ+0.5), V3(35.65, -11.55, EntRoofZ+0.56), FAll, WorldUV(1, 1, 0, 0))
	// steel access ladder from the entrance roof to the main roof (on the pier at X=33)
	yl := -0.34
	for _, x := range []float64{32.75, 33.25} {
		s.Tube(MMetal, []Vec3{V3(x, yl, EntRoofZ), V3(x, yl, MainTopZ+0.8), V3(x, yl+0.55, MainTopZ+1.05)}, 0.02, 8, false, true, 1, 0)
		for _, z := range []float64{12.6, 14.4} {
			s.Tube(MMetal, []Vec3{V3(x, yl, z), V3(x, 0, z)}, 0.012, 6, false, false, 1, 0)
		}
	}
	for z := EntRoofZ + 0.3; z < MainTopZ+0.6; z += 0.3 {
		s.Tube(MMetal, []Vec3{V3(32.75, yl, z), V3(33.25, yl, z)}, 0.011, 6, false, false, 1, 0)
	}
}

// stairHouse is the roof exit enclosure with a steel door.
func (b *B) stairHouse(x, y, z float64) {
	s := b.RoofStruct
	w, d, h := 3.0, 2.4, 2.3
	s.Box(MWeather, V3(x-w/2, y-d/2, z-0.05), V3(x+w/2, y+d/2, z+h), FXn|FXp|FYn|FYp, uvWeather)
	s.Box(MTrim, V3(x-w/2-0.06, y-d/2-0.06, z+h), V3(x+w/2+0.06, y+d/2+0.06, z+h+0.08), FAll, uvTrim)
	s.Quad(MRoof, V3(x-w/2+0.1, y-d/2+0.1, z+h+0.081), V3(x+w/2-0.1, y-d/2+0.1, z+h+0.081), V3(x+w/2-0.1, y+d/2-0.1, z+h+0.081), V3(x-w/2+0.1, y+d/2-0.1, z+h+0.081), uvRoof)
	pl := NewPlane(V3(x-w/2, y-d/2, 0), V3(1, 0, 0))
	fD(s, MFrame, pl, uvFrame, w/2-0.45, w/2+0.45, z, z+2.0, 0.02)
	fSn(s, MFrame, pl, uvFrame, w/2-0.45, z, z+2.0, 0, 0.02)
	fSp(s, MFrame, pl, uvFrame, w/2+0.45, z, z+2.0, 0, 0.02)
	fZp(s, MFrame, pl, uvFrame, z+2.0, w/2-0.45, w/2+0.45, 0, 0.02)
	s.Box(MTrim, V3(x-0.6, y-d/2-0.5, z+2.05), V3(x+0.6, y-d/2, z+2.13), FAll^FYp, uvTrim)
}
