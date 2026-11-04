package main

import (
	"os"
	"path/filepath"

	. "sovbuild/geo"
)

type matDef struct {
	name, tex      string
	col            [3]float64 // preview colour when textures are missing
	metal, rough   float64
	normalScale    float64
	hasMetalMap    bool
}

var matDefs = []matDef{
	{MPanel, "T_Concrete_FacadePanel", [3]float64{0.62, 0.58, 0.52}, 0, 0.9, 1, false},
	{MWall, "T_Concrete_FacadeWall", [3]float64{0.60, 0.57, 0.51}, 0, 0.9, 1, false},
	{MTile, "T_Ceramic_Tile_RedBrown", [3]float64{0.33, 0.13, 0.09}, 0, 0.6, 1, false},
	{MRoof, "T_Roofing_Bitumen", [3]float64{0.16, 0.16, 0.16}, 0, 0.85, 1, false},
	{MTrim, "T_Concrete_Trim", [3]float64{0.68, 0.65, 0.59}, 0, 0.85, 1, false},
	{MPaving, "T_Concrete_Paving", [3]float64{0.50, 0.50, 0.48}, 0, 0.9, 1, false},
	{MWeather, "T_Concrete_Weathered", [3]float64{0.55, 0.53, 0.49}, 0, 0.92, 1, false},
	{MMetal, "T_Metal_Handrail", [3]float64{0.20, 0.21, 0.22}, 1, 0.5, 1, true},
	{MGlass, "T_Glass", [3]float64{0.05, 0.06, 0.07}, 0, 0.08, 0.3, false},
	{MFrame, "T_Window_Frame", [3]float64{0.17, 0.18, 0.19}, 0, 0.55, 1, false},
}

// makeMaterials links textures that exist in texDir (falls back to flat colours).
func makeMaterials(texDir string) []*Material {
	var out []*Material
	exists := func(n string) bool { _, err := os.Stat(filepath.Join(texDir, n)); return err == nil }
	for _, d := range matDefs {
		m := &Material{Name: d.name, Metallic: d.metal, Roughness: d.rough, NormalScale: d.normalScale}
		m.BaseColor = [4]float64{d.col[0], d.col[1], d.col[2], 1}
		if exists(d.tex + "_BaseColor.png") {
			m.BaseColor = [4]float64{1, 1, 1, 1}
			m.BaseTex = d.tex + "_BaseColor.png"
			m.NormalTex = d.tex + "_Normal.png"
			m.ORMTex = d.tex + "_ORM.png"
			m.RoughTex = d.tex + "_Roughness.png"
			m.AOTex = d.tex + "_AO.png"
			m.Metallic, m.Roughness = 1, 1 // factors multiply the ORM map
			if d.hasMetalMap {
				m.MetalTex = d.tex + "_Metallic.png"
			}
		}
		out = append(out, m)
	}
	return out
}
