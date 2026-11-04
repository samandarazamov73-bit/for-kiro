package main

import . "sovbuild/geo"

const (
	RecS0, RecS1 = 0.9, 11.7 // lobby recess along the -X face (s = -Y)
	RecTopZ      = CanZ0
	HallBase     = 6.00
)

func (b *B) entranceFacades() {
	m := b.EntWalls
	// -X face (inner corner): s = -Y
	pl, l := EdgePlane(Combined[1], Combined[2])
	var tileH, wallH []Rect
	for _, k := range []int{4, 5} {
		tileH = append(tileH, b.win(b.WinEnt, StdWin, pl, float64(k)*HallBay+HallBay/2, FFL+WinBase))
	}
	for k := 0; k < 6; k++ {
		wallH = append(wallH, b.win(b.WinEnt, HallWin, pl, float64(k)*HallBay+HallBay/2, HallBase))
	}
	tileH = append(tileH, Rect{0, -LandY0, -0.15, FFL}, Rect{RecS0, RecS1, FFL, RecTopZ})
	Wall(m, MTile, pl, 0, l, -0.15, TileTopZ, 0, tileH, uvTile)
	Wall(m, MWall, pl, 0, l, PanelZ0, EntAtticZ, 0, wallH, uvWallHall)
	// recess returns (tile) and the strip above the recess head
	fSp(m, MTile, pl, uvTile, RecS0, FFL, RecTopZ, -(GlazX - EntX0), 0)
	fSn(m, MTile, pl, uvTile, RecS1, FFL, RecTopZ, -(GlazX - EntX0), 0)

	// front face (narrow, one window column)
	pl, l = EdgePlane(Combined[2], Combined[3])
	tileH = []Rect{b.win(b.WinEnt, StdWin, pl, l/2, FFL+WinBase)}
	wallH = []Rect{b.win(b.WinEnt, StdWin, pl, l/2, 5.6), b.win(b.WinEnt, StdWin, pl, l/2, 8.7)}
	Wall(m, MTile, pl, 0, l, -0.15, TileTopZ, 0, tileH, uvTile)
	Wall(m, MWall, pl, 0, l, PanelZ0, EntAtticZ, 0, wallH, uvWallOff(0.25))

	// +X face
	pl, l = EdgePlane(Combined[3], Combined[4])
	tileH, wallH = nil, nil
	for k := 0; k < 6; k++ {
		s := float64(k)*HallBay + HallBay/2
		tileH = append(tileH, b.win(b.WinEnt, StdWin, pl, s, FFL+WinBase))
		wallH = append(wallH, b.win(b.WinEnt, HallWin, pl, s, HallBase))
	}
	Wall(m, MTile, pl, 0, l, -0.15, TileTopZ, 0, tileH, uvTile)
	Wall(m, MWall, pl, 0, l, PanelZ0, EntAtticZ, 0, wallH, uvWallHall)
}

// bands: belt course, attic bands, parapets and copings.
func (b *B) bands() {
	t := b.Trim
	RingWall(t, MTrim, Combined, true, 0.06, TileTopZ, BeltTopZ, true, uvTrim)
	RingFlat(t, MTrim, Combined, true, 0, 0.06, BeltTopZ, true, uvTrim)
	RingFlat(t, MTrim, Combined, true, 0, 0.06, TileTopZ, false, uvTrim)
	type par struct {
		p             []Vec2
		closed        bool
		z0, roof, top float64
	}
	for _, q := range []par{{MainOutline, true, 14.35, MainRoofZ, MainTopZ}, {EntOpen, false, EntAtticZ, EntRoofZ, EntTopZ}} {
		RingWall(t, MWall, q.p, q.closed, 0.08, q.z0, q.top, true, uvWall)
		RingFlat(t, MWall, q.p, q.closed, 0, 0.08, q.z0, false, uvWall)
		RingWall(t, MRoof, q.p, q.closed, -0.30, q.roof, q.roof+0.25, false, uvRoof)
		RingWall(t, MWall, q.p, q.closed, -0.30, q.roof+0.25, q.top, false, uvWall)
		// coping
		RingWall(t, MTrim, q.p, q.closed, 0.12, q.top, q.top+0.07, true, uvTrim)
		RingWall(t, MTrim, q.p, q.closed, -0.34, q.top, q.top+0.07, false, uvTrim)
		RingFlat(t, MTrim, q.p, q.closed, -0.34, 0.12, q.top+0.07, true, uvTrim)
		RingFlat(t, MTrim, q.p, q.closed, 0.08, 0.12, q.top, false, uvTrim)
		RingFlat(t, MTrim, q.p, q.closed, -0.34, -0.30, q.top, false, uvTrim)
	}
}
