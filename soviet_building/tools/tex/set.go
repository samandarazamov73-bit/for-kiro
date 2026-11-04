package tex

import (
	"fmt"
	"path/filepath"
)

// Set is a PBR texture set authored in sRGB (albedo) and linear (others).
type Set struct {
	Name             string
	R, G, B          *F // base colour, sRGB encoded 0..1
	Rough, AO, Metal *F
	Height           *F
	NormalStrength   float64
	HasMetal         bool
}

func NewSet(name string, size int) *Set {
	return &Set{Name: name, R: NewF(size, size), G: NewF(size, size), B: NewF(size, size),
		Rough: NewF(size, size), AO: NewF(size, size), Metal: NewF(size, size), Height: NewF(size, size)}
}

// Save writes BaseColor, Normal, ORM (+jpg), Roughness, AO and (optionally) Metallic.
func (s *Set) Save(dir string) error {
	p := func(suf string) string { return filepath.Join(dir, s.Name+"_"+suf+".png") }
	if err := SaveRGB(p("BaseColor"), s.R, s.G, s.B, 92); err != nil {
		return err
	}
	nr, ng, nb := NormalFromHeight(s.Height, s.NormalStrength)
	if err := SaveRGB(p("Normal"), nr, ng, nb, 0); err != nil {
		return err
	}
	if err := SaveRGB(p("ORM"), s.AO, s.Rough, s.Metal, 92); err != nil {
		return err
	}
	if err := SaveGray(p("Roughness"), s.Rough); err != nil {
		return err
	}
	if err := SaveGray(p("AO"), s.AO); err != nil {
		return err
	}
	if s.HasMetal {
		if err := SaveGray(p("Metallic"), s.Metal); err != nil {
			return err
		}
	}
	fmt.Println("saved", s.Name, s.R.W)
	return nil
}
