package geo

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// WriteOBJ writes Y-up OBJ + MTL. Textures are referenced from texRel.
func WriteOBJ(s *Scene, path, texRel string) error {
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()
	w := bufio.NewWriterSize(f, 1<<20)
	mtlName := strings.TrimSuffix(filepath.Base(path), filepath.Ext(path)) + ".mtl"
	fmt.Fprintf(w, "# Soviet-era institutional building, low-poly, metres, Y up\n# triangles: %d\nmtllib %s\n", s.TriCount(), mtlName)
	vbase := 1
	var walk func(n *Node, prefix string)
	walk = func(n *Node, prefix string) {
		name := n.Name
		if prefix != "" {
			name = prefix + "/" + n.Name
		}
		if n.Mesh != nil && n.Mesh.TriCount() > 0 {
			fmt.Fprintf(w, "o %s\n", strings.ReplaceAll(name, " ", "_"))
			for _, g := range n.Mesh.Groups {
				if len(g.Idx) == 0 {
					continue
				}
				for _, v := range g.Verts {
					p := toGL(v.P)
					fmt.Fprintf(w, "v %.4f %.4f %.4f\n", p[0], p[1], p[2])
				}
				for _, v := range g.Verts {
					fmt.Fprintf(w, "vt %.5f %.5f\n", v.UV.U, v.UV.V)
				}
				for _, v := range g.Verts {
					q := toGL(v.N)
					fmt.Fprintf(w, "vn %.4f %.4f %.4f\n", q[0], q[1], q[2])
				}
				fmt.Fprintf(w, "usemtl %s\ns off\n", g.Mat)
				for i := 0; i+2 < len(g.Idx); i += 3 {
					a, b, c := int(g.Idx[i])+vbase, int(g.Idx[i+1])+vbase, int(g.Idx[i+2])+vbase
					fmt.Fprintf(w, "f %d/%d/%d %d/%d/%d %d/%d/%d\n", a, a, a, b, b, b, c, c, c)
				}
				vbase += len(g.Verts)
			}
		}
		for _, c := range n.Children {
			walk(c, name)
		}
	}
	walk(s.Root, "")
	if err := w.Flush(); err != nil {
		return err
	}
	mf, err := os.Create(filepath.Join(filepath.Dir(path), mtlName))
	if err != nil {
		return err
	}
	defer mf.Close()
	mw := bufio.NewWriter(mf)
	fmt.Fprintf(mw, "# PBR extension keys (Pr/Pm/map_Pr/map_Pm/norm) are used by Blender, Unity and Unreal importers\n")
	for _, m := range s.Materials {
		fmt.Fprintf(mw, "\nnewmtl %s\n", m.Name)
		fmt.Fprintf(mw, "Kd %.4f %.4f %.4f\nKa 1 1 1\nKs 0.04 0.04 0.04\nNs %.1f\nd %.3f\nillum 2\n", m.BaseColor[0], m.BaseColor[1], m.BaseColor[2], (1-m.Roughness)*(1-m.Roughness)*900+4, m.BaseColor[3])
		fmt.Fprintf(mw, "Pr %.3f\nPm %.3f\n", m.Roughness, m.Metallic)
		if m.BaseTex != "" {
			fmt.Fprintf(mw, "map_Kd %s%s\n", texRel, m.BaseTex)
		}
		if m.RoughTex != "" {
			fmt.Fprintf(mw, "map_Pr %s%s\n", texRel, m.RoughTex)
		}
		if m.MetalTex != "" {
			fmt.Fprintf(mw, "map_Pm %s%s\n", texRel, m.MetalTex)
		}
		if m.AOTex != "" {
			fmt.Fprintf(mw, "map_Ka %s%s\n", texRel, m.AOTex)
		}
		if m.NormalTex != "" {
			fmt.Fprintf(mw, "norm %s%s\nmap_Bump -bm %.2f %s%s\n", texRel, m.NormalTex, m.NormalScale, texRel, m.NormalTex)
		}
	}
	return mw.Flush()
}
