package geo

import "math"

// WriteFBX writes a binary FBX 7.4 file (Y up, metres via UnitScaleFactor=100).
func WriteFBX(s *Scene, path, texRel string) error {
	root := &fnode{}
	fbxHeader(root)
	uid := int64(1000000)
	next := func() int64 { uid++; return uid }
	docs := root.add("Documents")
	docs.add("Count", int32(1))
	doc := docs.add("Document", next(), "", "Scene")
	dp := doc.add("Properties70")
	p70(dp, "SourceObject", "object", "", "")
	p70(dp, "ActiveAnimStackName", "KString", "", "", "")
	doc.add("RootNode", int64(0))
	root.add("References")
	defs := root.add("Definitions")
	objs := &fnode{name: "Objects"}
	conns := &fnode{name: "Connections"}
	oo := func(c, p int64) { conns.add("C", "OO", c, p) }
	op := func(c, p int64, prop string) { conns.add("C", "OP", c, p, prop) }
	counts := map[string]int{}

	matID := map[string]int64{}
	for _, m := range s.Materials {
		id := next()
		matID[m.Name] = id
		counts["Material"]++
		mn := objs.add("Material", id, m.Name+"\x00\x01Material", "")
		mn.add("Version", int32(102))
		mn.add("ShadingModel", "Phong")
		mn.add("MultiLayer", int32(0))
		pp := mn.add("Properties70")
		p70(pp, "DiffuseColor", "Color", "", "A", m.BaseColor[0], m.BaseColor[1], m.BaseColor[2])
		p70(pp, "DiffuseFactor", "Number", "", "A", 1.0)
		p70(pp, "SpecularColor", "Color", "", "A", 0.5, 0.5, 0.5)
		p70(pp, "SpecularFactor", "Number", "", "A", 0.3*(1-m.Roughness)+0.05)
		p70(pp, "ShininessExponent", "Number", "", "A", math.Pow(2, 10*(1-m.Roughness))+2)
		p70(pp, "ReflectionFactor", "Number", "", "A", m.Metallic)
		for _, t := range []struct{ file, prop string }{{m.BaseTex, "DiffuseColor"}, {m.NormalTex, "NormalMap"}} {
			if t.file == "" {
				continue
			}
			tid, vid := next(), next()
			counts["Texture"]++
			counts["Video"]++
			rel := texRel + t.file
			tn := objs.add("Texture", tid, t.file+"\x00\x01Texture", "")
			tn.add("Type", "TextureVideoClip")
			tn.add("Version", int32(202))
			tn.add("TextureName", t.file+"\x00\x01Texture")
			tp := tn.add("Properties70")
			p70(tp, "UseMaterial", "bool", "", "", int32(1))
			tn.add("Media", t.file+"\x00\x01Video")
			tn.add("FileName", rel)
			tn.add("RelativeFilename", rel)
			tn.add("ModelUVTranslation", 0.0, 0.0)
			tn.add("ModelUVScaling", 1.0, 1.0)
			tn.add("Texture_Alpha_Source", "None")
			tn.add("Cropping", int32(0), int32(0), int32(0), int32(0))
			vn := objs.add("Video", vid, t.file+"\x00\x01Video", "Clip")
			vn.add("Type", "Clip")
			vp := vn.add("Properties70")
			p70(vp, "Path", "KString", "XRefUrl", "", rel)
			vn.add("UseMipMap", int32(0))
			vn.add("Filename", rel)
			vn.add("RelativeFilename", rel)
			oo(vid, tid)
			op(tid, id, t.prop)
		}
	}
	var walk func(n *Node, parent int64)
	walk = func(n *Node, parent int64) {
		mid := next()
		counts["Model"]++
		kind := "Null"
		if n.Mesh != nil && n.Mesh.TriCount() > 0 {
			kind = "Mesh"
		}
		mn := objs.add("Model", mid, n.Name+"\x00\x01Model", kind)
		mn.add("Version", int32(232))
		pp := mn.add("Properties70")
		p70(pp, "Lcl Translation", "Lcl Translation", "", "A", 0.0, 0.0, 0.0)
		p70(pp, "Lcl Rotation", "Lcl Rotation", "", "A", 0.0, 0.0, 0.0)
		p70(pp, "Lcl Scaling", "Lcl Scaling", "", "A", 1.0, 1.0, 1.0)
		p70(pp, "DefaultAttributeIndex", "int", "Integer", "", int32(0))
		p70(pp, "InheritType", "enum", "", "", int32(1))
		mn.add("Shading", true)
		mn.add("Culling", "CullingOff")
		oo(mid, parent)
		if kind == "Mesh" {
			gid := next()
			counts["Geometry"]++
			fbxGeometry(objs, gid, n.Mesh)
			oo(gid, mid)
			for _, g := range n.Mesh.Groups {
				if len(g.Idx) > 0 {
					oo(matID[g.Mat], mid)
				}
			}
		}
		for _, c := range n.Children {
			walk(c, mid)
		}
	}
	walk(s.Root, 0)
	total := 1
	defs.add("Version", int32(100))
	for _, c := range counts {
		total += c
	}
	defs.add("Count", int32(total))
	defs.add("ObjectType", "GlobalSettings").add("Count", int32(1))
	for _, k := range []string{"Model", "Geometry", "Material", "Texture", "Video"} {
		defs.add("ObjectType", k).add("Count", int32(counts[k]))
	}
	root.kids = append(root.kids, objs, conns)
	root.add("Takes").add("Current", "")
	return fbxFinish(root, path)
}

func fbxGeometry(objs *fnode, gid int64, m *Mesh) {
	type key [3]int64
	cp := map[key]int32{}
	var verts, normals, uvs []float64
	var pvi, uvi, mats []int32
	mi := int32(0)
	for _, g := range m.Groups {
		if len(g.Idx) == 0 {
			continue
		}
		for t := 0; t+2 < len(g.Idx); t += 3 {
			for k := 0; k < 3; k++ {
				v := g.Verts[g.Idx[t+k]]
				p := toGL(v.P)
				q := key{int64(math.Round(float64(p[0]) * 1e4)), int64(math.Round(float64(p[1]) * 1e4)), int64(math.Round(float64(p[2]) * 1e4))}
				ci, ok := cp[q]
				if !ok {
					ci = int32(len(verts) / 3)
					cp[q] = ci
					verts = append(verts, float64(p[0]), float64(p[1]), float64(p[2]))
				}
				if k == 2 {
					pvi = append(pvi, ^ci)
				} else {
					pvi = append(pvi, ci)
				}
				n := toGL(v.N)
				normals = append(normals, float64(n[0]), float64(n[1]), float64(n[2]))
				uvi = append(uvi, int32(len(uvs)/2))
				uvs = append(uvs, v.UV.U, v.UV.V)
			}
			mats = append(mats, mi)
		}
		mi++
	}
	gn := objs.add("Geometry", gid, m.Name+"\x00\x01Geometry", "Mesh")
	gn.add("Properties70")
	gn.add("GeometryVersion", int32(124))
	gn.add("Vertices", verts)
	gn.add("PolygonVertexIndex", pvi)
	ln := gn.add("LayerElementNormal", int32(0))
	ln.add("Version", int32(101))
	ln.add("Name", "")
	ln.add("MappingInformationType", "ByPolygonVertex")
	ln.add("ReferenceInformationType", "Direct")
	ln.add("Normals", normals)
	lu := gn.add("LayerElementUV", int32(0))
	lu.add("Version", int32(101))
	lu.add("Name", "UVMap")
	lu.add("MappingInformationType", "ByPolygonVertex")
	lu.add("ReferenceInformationType", "IndexToDirect")
	lu.add("UV", uvs)
	lu.add("UVIndex", uvi)
	lm := gn.add("LayerElementMaterial", int32(0))
	lm.add("Version", int32(101))
	lm.add("Name", "")
	lm.add("MappingInformationType", "ByPolygon")
	lm.add("ReferenceInformationType", "IndexToDirect")
	lm.add("Materials", mats)
	ly := gn.add("Layer", int32(0))
	ly.add("Version", int32(100))
	for _, t := range []string{"LayerElementNormal", "LayerElementUV", "LayerElementMaterial"} {
		le := ly.add("LayerElement")
		le.add("Type", t)
		le.add("TypedIndex", int32(0))
	}
}
