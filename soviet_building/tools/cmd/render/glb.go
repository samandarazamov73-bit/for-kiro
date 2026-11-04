package main

import (
	"bytes"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"image"
	_ "image/jpeg"
	_ "image/png"
	"math"
	"os"
)

type V3 [3]float64

type Mat struct {
	Name                   string
	Base                   [4]float64
	Metal, Rough, NScale   float64
	BaseT, NormT, ORMT     *Tex
	Ground                 bool
}

type Tri struct {
	P    [3]V3
	N    [3]V3
	T    [3][4]float64
	UV   [3][2]float64
	Mat  int
	Node string
}

type gDoc struct {
	Nodes []struct {
		Name     string `json:"name"`
		Mesh     *int   `json:"mesh"`
		Children []int  `json:"children"`
	} `json:"nodes"`
	Meshes []struct {
		Name       string `json:"name"`
		Primitives []struct {
			Attributes map[string]int `json:"attributes"`
			Indices    int            `json:"indices"`
			Material   int            `json:"material"`
		} `json:"primitives"`
	} `json:"meshes"`
	Materials []struct {
		Name string `json:"name"`
		PBR  struct {
			Base  []float64 `json:"baseColorFactor"`
			Metal float64   `json:"metallicFactor"`
			Rough float64   `json:"roughnessFactor"`
			BT    *struct{ Index int } `json:"baseColorTexture"`
			MRT   *struct{ Index int } `json:"metallicRoughnessTexture"`
		} `json:"pbrMetallicRoughness"`
		NT *struct {
			Index int     `json:"index"`
			Scale float64 `json:"scale"`
		} `json:"normalTexture"`
	} `json:"materials"`
	Textures []struct {
		Source int `json:"source"`
	} `json:"textures"`
	Images []struct {
		BufferView int    `json:"bufferView"`
		Name       string `json:"name"`
	} `json:"images"`
	Accessors []struct {
		BufferView, ComponentType, Count int
		Type                             string
	} `json:"accessors"`
	BufferViews []struct {
		ByteOffset int `json:"byteOffset"`
		ByteLength int `json:"byteLength"`
	} `json:"bufferViews"`
}

func loadGLB(path string) ([]Tri, []*Mat, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, nil, err
	}
	jl := binary.LittleEndian.Uint32(data[12:])
	var doc gDoc
	if err := json.Unmarshal(data[20:20+jl], &doc); err != nil {
		return nil, nil, err
	}
	bin := data[20+jl+8:]
	view := func(i int) []byte { v := doc.BufferViews[i]; return bin[v.ByteOffset : v.ByteOffset+v.ByteLength] }
	floats := func(acc int) []float64 {
		a := doc.Accessors[acc]
		b := view(a.BufferView)
		out := make([]float64, len(b)/4)
		for i := range out {
			out[i] = float64(math.Float32frombits(binary.LittleEndian.Uint32(b[4*i:])))
		}
		return out
	}
	ints := func(acc int) []int {
		a := doc.Accessors[acc]
		b := view(a.BufferView)
		out := make([]int, a.Count)
		for i := range out {
			if a.ComponentType == 5123 {
				out[i] = int(binary.LittleEndian.Uint16(b[2*i:]))
			} else {
				out[i] = int(binary.LittleEndian.Uint32(b[4*i:]))
			}
		}
		return out
	}
	texCache := map[int]*Tex{}
	getTex := func(ti int, srgb bool) *Tex {
		if t, ok := texCache[ti]; ok {
			return t
		}
		im := doc.Images[doc.Textures[ti].Source]
		img, _, err := image.Decode(bytes.NewReader(view(im.BufferView)))
		if err != nil {
			panic(fmt.Sprint("decode ", im.Name, err))
		}
		t := newTex(img, srgb)
		texCache[ti] = t
		return t
	}
	var mats []*Mat
	for _, m := range doc.Materials {
		mt := &Mat{Name: m.Name, Metal: m.PBR.Metal, Rough: m.PBR.Rough, NScale: 1}
		copy(mt.Base[:], m.PBR.Base)
		if m.PBR.BT != nil {
			mt.BaseT = getTex(m.PBR.BT.Index, true)
		}
		if m.PBR.MRT != nil {
			mt.ORMT = getTex(m.PBR.MRT.Index, false)
		}
		if m.NT != nil {
			mt.NormT = getTex(m.NT.Index, false)
			mt.NScale = m.NT.Scale
		}
		mats = append(mats, mt)
	}
	var tris []Tri
	for _, n := range doc.Nodes {
		if n.Mesh == nil {
			continue
		}
		for _, p := range doc.Meshes[*n.Mesh].Primitives {
			pos, nor := floats(p.Attributes["POSITION"]), floats(p.Attributes["NORMAL"])
			uv, tan := floats(p.Attributes["TEXCOORD_0"]), floats(p.Attributes["TANGENT"])
			idx := ints(p.Indices)
			for i := 0; i+2 < len(idx); i += 3 {
				var t Tri
				t.Mat, t.Node = p.Material, n.Name
				for k := 0; k < 3; k++ {
					v := idx[i+k]
					t.P[k] = V3{pos[3*v], pos[3*v+1], pos[3*v+2]}
					t.N[k] = V3{nor[3*v], nor[3*v+1], nor[3*v+2]}
					t.UV[k] = [2]float64{uv[2*v], uv[2*v+1]}
					t.T[k] = [4]float64{tan[4*v], tan[4*v+1], tan[4*v+2], tan[4*v+3]}
				}
				tris = append(tris, t)
			}
		}
	}
	return tris, mats, nil
}
