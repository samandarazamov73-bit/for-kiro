package main

import . "sovbuild/geo"

// Standard school window: precast box surround 2.45 x 2.55 m, 4-pane frame.
var StdWin = WinSpec{
	W: 2.45, H: 2.55, Side: 0.23, SillH: 0.25,
	Proj: 0.16, SillProj: 0.25, SillExt: 0.05, Recess: 0.14, Slope: 0.08,
	Cols: []float64{0.5}, Rows: []float64{0.70}, FW: 0.065, FD: 0.05,
}

// HallWin is the tall assembly-hall window of the entrance block.
var HallWin = WinSpec{
	W: 2.40, H: 5.00, Side: 0.18, SillH: 0.20,
	Proj: 0.16, SillProj: 0.24, SillExt: 0.05, Recess: 0.14, Slope: 0.07,
	Cols: []float64{1.0 / 3, 2.0 / 3}, Rows: []float64{0.25, 0.5, 0.75}, FW: 0.07, FD: 0.05,
}

// Window bottom (surround base) relative to floor level.
const WinBase = 0.60

// Floor levels of the main wing.
var Floors = []float64{FFL, FFL + FloorH, FFL + 2*FloorH, FFL + 3*FloorH}

// Plan polygons (CCW seen from above).
var MainOutline = []Vec2{{0, 0}, {MainLen, 0}, {MainLen, MainDepth}, {0, MainDepth}}
var Combined = []Vec2{{0, 0}, {EntX0, 0}, {EntX0, EntY0}, {EntX1, EntY0}, {EntX1, 0},
	{MainLen, 0}, {MainLen, MainDepth}, {0, MainDepth}}
var EntOpen = []Vec2{{EntX0, 0}, {EntX0, EntY0}, {EntX1, EntY0}, {EntX1, 0}}

// EdgePlane returns the outward facade plane of the edge a->b (s from 0 to len).
func EdgePlane(a, b Vec2) (Plane, float64) {
	d := V3(b.U-a.U, b.V-a.V, 0)
	l := d.Len()
	return NewPlane(V3(a.U, a.V, 0), d.Mul(1/l)), l
}

// facade UV mappers
var uvTile = WorldUV(4.8, 4.8, 0, 0)
var uvPanel = WorldUV(6.0, 6.6, 0, -PanelZ0/6.6)

func uvWallOff(ou float64) UVFn { return WorldUV(6.0, 6.6, ou, -PanelZ0/6.6) }

var uvWall = uvWallOff(0)
var uvWallEnd = WorldUV(6.48, 6.6, 0, -PanelZ0/6.6)
var uvWallHall = WorldUV(6.5, 6.6, 0, -PanelZ0/6.6)
var uvPave = WorldUV(3, 3, 0, 0)
var uvRoof = WorldUV(8, 8, 0, 0)
var uvWeather = WorldUV(2.5, 2.5, 0, 0)
