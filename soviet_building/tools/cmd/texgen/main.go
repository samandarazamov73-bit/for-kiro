package main

import (
	"flag"
	"fmt"
	"os"
	"strings"
	"time"

	. "sovbuild/tex"
)

func main() {
	out := flag.String("out", "../textures", "output folder")
	only := flag.String("only", "", "comma separated set names (substring match)")
	flag.Parse()
	os.MkdirAll(*out, 0o755)
	gens := []struct {
		name string
		fn   func() *Set
	}{
		{"T_Concrete_FacadePanel", func() *Set {
			return concrete(ConcreteOpts{Name: "T_Concrete_FacadePanel", Size: 2048, MU: 6.0, MV: 6.6, PU: 2, PV: 2,
				Base: [3]float64{0.69, 0.66, 0.60}, PanelVar: 0.04, Windows: true, Streak: 1.0, Dirt: 1.2, Stain: 1.0,
				Pores: 1, Mottle: 1, Rough: 0.9, Cracks: 5, Seed: 101, NormalStrength: 2.4})
		}},
		{"T_Concrete_FacadeWall", func() *Set {
			return concrete(ConcreteOpts{Name: "T_Concrete_FacadeWall", Size: 2048, MU: 6.0, MV: 6.6, PU: 2, PV: 2,
				Base: [3]float64{0.68, 0.65, 0.59}, PanelVar: 0.045, Streak: 0.9, Dirt: 1.2, Stain: 1.1,
				Pores: 1, Mottle: 1.1, Rough: 0.9, Cracks: 9, Seed: 202, NormalStrength: 2.4})
		}},
		{"T_Concrete_Trim", func() *Set {
			return concrete(ConcreteOpts{Name: "T_Concrete_Trim", Size: 1024, MU: 2, MV: 2,
				Base: [3]float64{0.70, 0.675, 0.62}, Streak: 0.75, Dirt: 1.3, Stain: 1.0,
				Pores: 0.7, Mottle: 0.8, Rough: 0.82, Cracks: 2, Seed: 303, NormalStrength: 1.8})
		}},
		{"T_Concrete_Weathered", func() *Set {
			return concrete(ConcreteOpts{Name: "T_Concrete_Weathered", Size: 1024, MU: 2.5, MV: 2.5,
				Base: [3]float64{0.60, 0.58, 0.54}, Streak: 0.9, Dirt: 1.6, Stain: 1.0,
				Pores: 1.3, Mottle: 1.4, Rough: 0.93, Cracks: 6, Seed: 404, NormalStrength: 2.2})
		}},
		{"T_Concrete_Paving", func() *Set {
			return concrete(ConcreteOpts{Name: "T_Concrete_Paving", Size: 1024, MU: 3, MV: 3, PU: 1, PV: 1,
				Base: [3]float64{0.53, 0.53, 0.51}, PanelVar: 0.03, Streak: 0.0, Dirt: 1.3, Stain: 0.8, GrooveW: 0.002, JointMix: 0.2,
				Pores: 1.2, Mottle: 1.3, Rough: 0.92, Cracks: 2, Seed: 505, NormalStrength: 2.2, Broom: 0.35})
		}},
		{"T_Ceramic_Tile_RedBrown", tiles},
		{"T_Roofing_Bitumen", roofing},
		{"T_Metal_Handrail", metal},
		{"T_Glass", glass},
		{"T_Window_Frame", frame},
	}
	for _, g := range gens {
		if *only != "" {
			hit := false
			for _, o := range strings.Split(*only, ",") {
				hit = hit || strings.Contains(g.name, o)
			}
			if !hit {
				continue
			}
		}
		t := time.Now()
		s := g.fn()
		if err := s.Save(*out); err != nil {
			panic(err)
		}
		fmt.Printf("  %s %v\n", g.name, time.Since(t).Round(time.Millisecond))
	}
}
