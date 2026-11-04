package main

import (
	"flag"
	"fmt"
	"math/rand"
	"os"
	"path/filepath"
	"strings"

	. "sovbuild/geo"
)

func main() {
	root := flag.String("root", "..", "project root (contains textures/ and export/)")
	flag.Parse()
	texDir := filepath.Join(*root, "textures")
	exp := filepath.Join(*root, "export")
	for _, d := range []string{"", "gltf", "obj", "fbx"} {
		os.MkdirAll(filepath.Join(exp, d), 0o755)
	}

	b := &B{rng: rand.New(rand.NewSource(1977))}
	nm := NewMesh
	b.MainWalls, b.EntWalls, b.Trim = nm("MainWing_Walls"), nm("EntranceBlock_Walls"), nm("Facade_Trim")
	b.WinMain, b.WinEnt = NewWinMeshes("MainWing_Window"), NewWinMeshes("EntranceBlock_Window")
	b.Glazing, b.Porch, b.Rails = nm("Lobby_CurtainWall_Doors"), nm("RearExit_Porches"), nm("RearExit_Handrails")
	b.Stairs, b.Canopy, b.Columns = nm("Entrance_Landing_Stairs"), nm("Entrance_Canopy"), nm("Entrance_Columns")
	b.StairRails = nm("Entrance_Stair_Handrails")
	b.Ramp, b.RampRails = nm("Ramp_Structure"), nm("Ramp_Handrails")
	b.Roof, b.RoofRail, b.RoofStruct, b.Drains = nm("Roof_Surfaces"), nm("Roof_Railing"), nm("Roof_Structures"), nm("Roof_Drains")
	b.Site = nm("Site_Paving")

	b.mainFacades()
	b.entranceFacades()
	b.bands()
	b.stairs()
	b.stairRails()
	b.canopy()
	b.lobby()
	b.ramp()
	b.roofs()
	b.site()

	group := func(name string, ms ...*Mesh) *Node {
		n := &Node{Name: name}
		for _, m := range ms {
			n.Add(&Node{Name: m.Name, Mesh: m})
		}
		return n
	}
	sc := &Scene{Root: &Node{Name: "SovietSchool_1970s"}, Materials: makeMaterials(texDir)}
	r := sc.Root
	r.Add(group("Building", b.MainWalls, b.EntWalls, b.Trim))
	r.Add(group("Windows", b.WinMain.Surround, b.WinMain.Frame, b.WinMain.Glass,
		b.WinEnt.Surround, b.WinEnt.Frame, b.WinEnt.Glass, b.Glazing))
	r.Add(group("Entrance", b.Stairs, b.StairRails, b.Canopy, b.Columns))
	r.Add(group("Ramp", b.Ramp, b.RampRails))
	r.Add(group("Roof", b.Roof, b.RoofStruct, b.RoofRail, b.Drains))
	r.Add(group("RearExits", b.Porch, b.Rails))
	r.Add(group("Site", b.Site))

	total := 0
	r.Walk(func(n *Node, d int) {
		if n.Mesh != nil {
			t := n.Mesh.TriCount()
			total += t
			fmt.Printf("%s%-34s %7d tris\n", strings.Repeat("  ", d), n.Name, t)
		} else {
			fmt.Printf("%s%s/\n", strings.Repeat("  ", d), n.Name)
		}
	})
	fmt.Printf("TOTAL triangles: %d\n", total)

	jpeg := func(n string) bool { return strings.Contains(n, "_BaseColor") || strings.Contains(n, "_ORM") }
	must(WriteGLTF(sc, filepath.Join(exp, "SovietSchool.glb"), texDir, true, "", jpeg))
	must(WriteGLTF(sc, filepath.Join(exp, "gltf", "SovietSchool.gltf"), texDir, false, "../../textures/", nil))
	must(WriteOBJ(sc, filepath.Join(exp, "obj", "SovietSchool.obj"), "../../textures/"))
	must(WriteFBX(sc, filepath.Join(exp, "fbx", "SovietSchool.fbx"), "../../textures/"))
}

func must(err error) {
	if err != nil {
		fmt.Fprintln(os.Stderr, "error:", err)
		os.Exit(1)
	}
}
