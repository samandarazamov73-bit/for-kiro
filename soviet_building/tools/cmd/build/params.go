package main

// All dimensions in metres. Modelling axes: X right, Y back, Z up.
// Main facade lies at Y=0 and faces -Y. Entrance block projects to -Y.
const (
	Bay    = 3.0  // structural / facade module
	FloorH = 3.3  // floor-to-floor height
	FFL    = 1.20 // ground floor level above grade (8 risers x 150 mm)

	MainLen   = 75.0 // 25 bays
	HallBay   = 3.25 // entrance block bay (6 bays = 19.5 m)
	EntAtticZ = 11.30
	MainDepth = 16.2
	MainBays  = 25
	MainRoofZ = 14.60 // roof surface
	MainTopZ  = 15.30 // parapet / attic top

	TileTopZ = 4.40 // red-brown tile cladding top
	BeltTopZ = 4.60 // concrete belt course top
	PanelZ0  = 4.60 // origin of the facade panel grid

	EntX0, EntX1 = 27.0, 39.0 // entrance block (bays 10-13)
	EntY0        = -19.5     // entrance block front face
	EntRoofZ     = 11.60
	EntTopZ      = 12.30

	LandX0 = 22.0 // entrance landing (top of stairs / ramp)
	LandY0 = -13.0
	StepR  = 0.15 // riser
	StepT  = 0.32 // tread
	NRiser = 8

	CanX0, CanX1 = 22.6, 27.5
	CanY0, CanY1 = -12.0, -0.6
	CanZ0, CanZ1 = 4.00, 4.35
	GlazX        = 27.5 // recessed lobby glazing plane
)

// Material names.
const (
	MPanel   = "M_Concrete_FacadePanel"
	MWall    = "M_Concrete_FacadeWall"
	MTile    = "M_Ceramic_Tile_RedBrown"
	MRoof    = "M_Roofing_Bitumen"
	MTrim    = "M_Concrete_Trim"
	MPaving  = "M_Concrete_Paving"
	MWeather = "M_Concrete_Weathered"
	MMetal   = "M_Metal_Handrail"
	MGlass   = "M_Glass"
	MFrame   = "M_Window_Frame"
)
