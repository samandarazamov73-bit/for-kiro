package main

import (
	"math/rand"

	. "sovbuild/geo"
)

// B accumulates all meshes of the building.
type B struct {
	rng                 *rand.Rand
	MainWalls, EntWalls *Mesh
	Trim                *Mesh
	WinMain, WinEnt     WinMeshes
	Glazing             *Mesh // lobby curtain wall + doors
	Porch               *Mesh // rear exit porches
	Rails               *Mesh // rear exit handrails
	StairRails          *Mesh // entrance stair handrails
	Stairs, Canopy      *Mesh
	Columns             *Mesh
	Ramp, RampRails     *Mesh
	Roof, RoofRail      *Mesh
	RoofStruct, Drains  *Mesh
	Site                *Mesh
}

func (b *B) win(wm WinMeshes, spec WinSpec, pl Plane, sc, zb float64) Rect {
	spec.Surround(wm.Surround, pl, sc, zb)
	spec.Glazing(wm.Frame, wm.Glass, pl, sc, zb, b.rng.Intn(16))
	return spec.Hole(sc, zb)
}

// hiddenByEntrance reports main facade bays covered by the entrance block.
func hiddenByEntrance(k, f int) bool { return k >= 9 && k <= 12 && f <= 2 }

func (b *B) mainFacades() {
	m := b.MainWalls
	// front (Y=0) and rear (Y=15): identical 25 x 4 window grids
	for side := 0; side < 2; side++ {
		var pl Plane
		if side == 0 {
			pl = NewPlane(V3(0, 0, 0), V3(1, 0, 0))
		} else {
			pl = NewPlane(V3(MainLen, MainDepth, 0), V3(-1, 0, 0))
		}
		var tileH, panelH []Rect
		for k := 0; k < MainBays; k++ {
			for f, fl := range Floors {
				if side == 0 && hiddenByEntrance(k, f) {
					continue
				}
				if side == 1 && f == 0 && (k == 1 || k == 23) {
					continue // rear exits
				}
				h := b.win(b.WinMain, StdWin, pl, float64(k)*Bay+Bay/2, fl+WinBase)
				if f == 0 {
					tileH = append(tileH, h)
				} else {
					panelH = append(panelH, h)
				}
			}
		}
		if side == 0 {
			tileH = append(tileH, Rect{LandX0, EntX0, -0.15, FFL})
			Wall(m, MTile, pl, 0, EntX0, -0.15, TileTopZ, 0, tileH, uvTile)
			Wall(m, MTile, pl, EntX1, MainLen, -0.15, TileTopZ, 0, tileH, uvTile)
			panelH = append(panelH, Rect{EntX0, EntX1, PanelZ0, EntRoofZ})
		} else {
			tileH = append(tileH, b.rearExits(pl)...)
			Wall(m, MTile, pl, 0, MainLen, -0.15, TileTopZ, 0, tileH, uvTile)
		}
		Wall(m, MPanel, pl, 0, MainLen, PanelZ0, 14.35, 0, panelH, uvPanel)
	}
	// end walls: one window column (corridor ends)
	ends := []Plane{NewPlane(V3(0, MainDepth, 0), V3(0, -1, 0)), NewPlane(V3(MainLen, 0, 0), V3(0, 1, 0))}
	for _, pl := range ends {
		var tileH, wallH []Rect
		for f, fl := range Floors {
			h := b.win(b.WinMain, StdWin, pl, MainDepth/2, fl+WinBase)
			if f == 0 {
				tileH = append(tileH, h)
			} else {
				wallH = append(wallH, h)
			}
		}
		Wall(m, MTile, pl, 0, MainDepth, -0.15, TileTopZ, 0, tileH, uvTile)
		Wall(m, MWall, pl, 0, MainDepth, PanelZ0, 14.35, 0, wallH, uvWallEnd)
	}
}
