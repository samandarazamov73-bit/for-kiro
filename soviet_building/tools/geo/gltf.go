package geo

import (
	"bytes"
	"encoding/binary"
	"encoding/json"
	"math"
	"os"
	"path/filepath"
	"strings"
)

// toGL converts modelling space (Z up, Y back) to glTF (Y up, +Z front).
func toGL(v Vec3) [3]float32 { return [3]float32{float32(v.X), float32(v.Z), float32(-v.Y)} }

type gltfDoc struct {
	Asset       map[string]any   `json:"asset"`
	Scene       int              `json:"scene"`
	Scenes      []map[string]any `json:"scenes"`
	Nodes       []map[string]any `json:"nodes"`
	Meshes      []map[string]any `json:"meshes"`
	Materials   []map[string]any `json:"materials"`
	Textures    []map[string]any `json:"textures,omitempty"`
	Images      []map[string]any `json:"images,omitempty"`
	Samplers    []map[string]any `json:"samplers,omitempty"`
	Accessors   []map[string]any `json:"accessors"`
	BufferViews []map[string]any `json:"bufferViews"`
	Buffers     []map[string]any `json:"buffers"`
}

type gltfBuilder struct {
	doc      gltfDoc
	bin      bytes.Buffer
	texIndex map[string]int
	texDir   string
	embed    bool
	imgDir   string // relative uri prefix for non embedded
	jpegFor  func(name string) bool
}

func (b *gltfBuilder) align() {
	for b.bin.Len()%4 != 0 {
		b.bin.WriteByte(0)
	}
}

func (b *gltfBuilder) view(data []byte, target int) int {
	b.align()
	off := b.bin.Len()
	b.bin.Write(data)
	v := map[string]any{"buffer": 0, "byteOffset": off, "byteLength": len(data)}
	if target != 0 {
		v["target"] = target
	}
	b.doc.BufferViews = append(b.doc.BufferViews, v)
	return len(b.doc.BufferViews) - 1
}

func (b *gltfBuilder) accessor(view, compType, count int, typ string, min, max []float64) int {
	a := map[string]any{"bufferView": view, "componentType": compType, "count": count, "type": typ}
	if min != nil {
		a["min"] = min
		a["max"] = max
	}
	b.doc.Accessors = append(b.doc.Accessors, a)
	return len(b.doc.Accessors) - 1
}

func (b *gltfBuilder) texture(name string) int {
	if name == "" {
		return -1
	}
	if i, ok := b.texIndex[name]; ok {
		return i
	}
	img := map[string]any{"name": strings.TrimSuffix(name, filepath.Ext(name))}
	if b.embed {
		data, err := os.ReadFile(filepath.Join(b.texDir, name))
		if err != nil {
			panic(err)
		}
		mime := "image/png"
		if strings.HasSuffix(name, ".jpg") {
			mime = "image/jpeg"
		}
		img["bufferView"] = b.view(data, 0)
		img["mimeType"] = mime
	} else {
		img["uri"] = b.imgDir + name
	}
	b.doc.Images = append(b.doc.Images, img)
	b.doc.Textures = append(b.doc.Textures, map[string]any{"sampler": 0, "source": len(b.doc.Images) - 1})
	i := len(b.doc.Textures) - 1
	b.texIndex[name] = i
	return i
}

// texName lets the GLB embed use alternative (e.g. jpg) files when present.
func (b *gltfBuilder) texName(name string) string {
	if name == "" || !b.embed || b.jpegFor == nil || !b.jpegFor(name) {
		return name
	}
	j := strings.TrimSuffix(name, filepath.Ext(name)) + ".jpg"
	if _, err := os.Stat(filepath.Join(b.texDir, j)); err == nil {
		return j
	}
	return name
}

func f32bytes(vals []float32) []byte {
	out := make([]byte, 4*len(vals))
	for i, v := range vals {
		binary.LittleEndian.PutUint32(out[4*i:], math.Float32bits(v))
	}
	return out
}

// WriteGLTF writes a .glb (embed=true, textures embedded) or .gltf + .bin
// (embed=false, textures referenced from imgDir).
func WriteGLTF(s *Scene, path, texDir string, embed bool, imgDir string, jpegFor func(string) bool) error {
	b := &gltfBuilder{texIndex: map[string]int{}, texDir: texDir, embed: embed, imgDir: imgDir, jpegFor: jpegFor}
	b.doc.Asset = map[string]any{"version": "2.0", "generator": "sovbuild (custom Go pipeline)", "extras": map[string]any{"units": "metres", "up": "+Y"}}
	b.doc.Samplers = []map[string]any{{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}}
	matIndex := map[string]int{}
	for i, m := range s.Materials {
		pbr := map[string]any{
			"baseColorFactor": m.BaseColor[:],
			"metallicFactor":  m.Metallic,
			"roughnessFactor": m.Roughness,
		}
		mat := map[string]any{"name": m.Name, "pbrMetallicRoughness": pbr}
		if t := b.texture(b.texName(m.BaseTex)); t >= 0 {
			pbr["baseColorTexture"] = map[string]any{"index": t}
		}
		if t := b.texture(b.texName(m.ORMTex)); t >= 0 {
			pbr["metallicRoughnessTexture"] = map[string]any{"index": t}
			mat["occlusionTexture"] = map[string]any{"index": t, "strength": 1.0}
		}
		if t := b.texture(m.NormalTex); t >= 0 {
			ns := m.NormalScale
			if ns == 0 {
				ns = 1
			}
			mat["normalTexture"] = map[string]any{"index": t, "scale": ns}
		}
		if m.DoubleSided {
			mat["doubleSided"] = true
		}
		b.doc.Materials = append(b.doc.Materials, mat)
		matIndex[m.Name] = i
	}
	var addNode func(n *Node) int
	addNode = func(n *Node) int {
		node := map[string]any{"name": n.Name}
		idx := len(b.doc.Nodes)
		b.doc.Nodes = append(b.doc.Nodes, node)
		if n.Mesh != nil && n.Mesh.TriCount() > 0 {
			var prims []map[string]any
			for _, g := range n.Mesh.Groups {
				if len(g.Idx) == 0 {
					continue
				}
				nv := len(g.Verts)
				pos := make([]float32, 0, nv*3)
				nor := make([]float32, 0, nv*3)
				uv := make([]float32, 0, nv*2)
				tg := make([]float32, 0, nv*4)
				mn := []float64{math.Inf(1), math.Inf(1), math.Inf(1)}
				mx := []float64{math.Inf(-1), math.Inf(-1), math.Inf(-1)}
				tans := Tangents(g)
				for i, v := range g.Verts {
					p := toGL(v.P)
					q := toGL(v.N)
					pos = append(pos, p[0], p[1], p[2])
					nor = append(nor, q[0], q[1], q[2])
					uv = append(uv, float32(v.UV.U), float32(1-v.UV.V))
					t := toGL(V3(tans[i][0], tans[i][1], tans[i][2]))
					tg = append(tg, t[0], t[1], t[2], float32(tans[i][3]))
					for k := 0; k < 3; k++ {
						mn[k] = math.Min(mn[k], float64(p[k]))
						mx[k] = math.Max(mx[k], float64(p[k]))
					}
				}
				aPos := b.accessor(b.view(f32bytes(pos), 34962), 5126, nv, "VEC3", mn, mx)
				aNor := b.accessor(b.view(f32bytes(nor), 34962), 5126, nv, "VEC3", nil, nil)
				aUV := b.accessor(b.view(f32bytes(uv), 34962), 5126, nv, "VEC2", nil, nil)
				aTan := b.accessor(b.view(f32bytes(tg), 34962), 5126, nv, "VEC4", nil, nil)
				var ib []byte
				ct := 5125
				if nv < 65536 {
					ct = 5123
					ib = make([]byte, 2*len(g.Idx))
					for i, x := range g.Idx {
						binary.LittleEndian.PutUint16(ib[2*i:], uint16(x))
					}
				} else {
					ib = make([]byte, 4*len(g.Idx))
					for i, x := range g.Idx {
						binary.LittleEndian.PutUint32(ib[4*i:], x)
					}
				}
				aIdx := b.accessor(b.view(ib, 34963), ct, len(g.Idx), "SCALAR", nil, nil)
				mi, ok := matIndex[g.Mat]
				if !ok {
					panic("unknown material " + g.Mat)
				}
				prims = append(prims, map[string]any{
					"attributes": map[string]any{"POSITION": aPos, "NORMAL": aNor, "TEXCOORD_0": aUV, "TANGENT": aTan},
					"indices":    aIdx, "material": mi, "mode": 4,
				})
			}
			b.doc.Meshes = append(b.doc.Meshes, map[string]any{"name": n.Name, "primitives": prims})
			node["mesh"] = len(b.doc.Meshes) - 1
		}
		var kids []int
		for _, c := range n.Children {
			kids = append(kids, addNode(c))
		}
		if len(kids) > 0 {
			node["children"] = kids
		}
		return idx
	}
	root := addNode(s.Root)
	b.doc.Scenes = []map[string]any{{"name": "Scene", "nodes": []int{root}}}
	b.align()
	if embed {
		b.doc.Buffers = []map[string]any{{"byteLength": b.bin.Len()}}
		js, err := json.Marshal(b.doc)
		if err != nil {
			return err
		}
		for len(js)%4 != 0 {
			js = append(js, ' ')
		}
		var out bytes.Buffer
		total := 12 + 8 + len(js) + 8 + b.bin.Len()
		binary.Write(&out, binary.LittleEndian, uint32(0x46546C67))
		binary.Write(&out, binary.LittleEndian, uint32(2))
		binary.Write(&out, binary.LittleEndian, uint32(total))
		binary.Write(&out, binary.LittleEndian, uint32(len(js)))
		binary.Write(&out, binary.LittleEndian, uint32(0x4E4F534A))
		out.Write(js)
		binary.Write(&out, binary.LittleEndian, uint32(b.bin.Len()))
		binary.Write(&out, binary.LittleEndian, uint32(0x004E4942))
		out.Write(b.bin.Bytes())
		return os.WriteFile(path, out.Bytes(), 0o644)
	}
	binName := strings.TrimSuffix(filepath.Base(path), filepath.Ext(path)) + ".bin"
	b.doc.Buffers = []map[string]any{{"byteLength": b.bin.Len(), "uri": binName}}
	js, err := json.MarshalIndent(b.doc, "", " ")
	if err != nil {
		return err
	}
	if err := os.WriteFile(filepath.Join(filepath.Dir(path), binName), b.bin.Bytes(), 0o644); err != nil {
		return err
	}
	return os.WriteFile(path, js, 0o644)
}
