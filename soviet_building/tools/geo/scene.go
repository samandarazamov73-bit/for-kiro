package geo

// Material is a PBR metallic-roughness material.
type Material struct {
	Name        string
	BaseColor   [4]float64
	Metallic    float64
	Roughness   float64
	NormalScale float64
	BaseTex     string // file name inside the texture folder (sRGB)
	NormalTex   string // OpenGL convention tangent space normal map
	ORMTex      string // R = AO, G = roughness, B = metallic
	RoughTex    string // individual maps (for OBJ/FBX users)
	AOTex       string
	MetalTex    string
	DoubleSided bool
}

// Node is a scene hierarchy element; geometry is stored in world space.
type Node struct {
	Name     string
	Mesh     *Mesh
	Children []*Node
}

func (n *Node) Add(c *Node) *Node { n.Children = append(n.Children, c); return c }

// Scene is the full export unit.
type Scene struct {
	Root      *Node
	Materials []*Material
}

func (s *Scene) Mat(name string) *Material {
	for _, m := range s.Materials {
		if m.Name == name {
			return m
		}
	}
	return nil
}

// Walk visits nodes depth first.
func (n *Node) Walk(f func(n *Node, depth int)) { n.walk(f, 0) }
func (n *Node) walk(f func(n *Node, depth int), d int) {
	f(n, d)
	for _, c := range n.Children {
		c.walk(f, d+1)
	}
}

func (s *Scene) TriCount() int {
	t := 0
	s.Root.Walk(func(n *Node, _ int) {
		if n.Mesh != nil {
			t += n.Mesh.TriCount()
		}
	})
	return t
}

// Tangents computes per-vertex tangents (xyz, w) for a group, glTF convention:
// bitangent = cross(N, T) * w points toward +v (texture up).
func Tangents(g *Group) [][4]float64 {
	n := len(g.Verts)
	tan := make([]Vec3, n)
	bit := make([]Vec3, n)
	for i := 0; i+2 < len(g.Idx); i += 3 {
		i0, i1, i2 := g.Idx[i], g.Idx[i+1], g.Idx[i+2]
		v0, v1, v2 := g.Verts[i0], g.Verts[i1], g.Verts[i2]
		e1, e2 := v1.P.Sub(v0.P), v2.P.Sub(v0.P)
		du1, dv1 := v1.UV.U-v0.UV.U, v1.UV.V-v0.UV.V
		du2, dv2 := v2.UV.U-v0.UV.U, v2.UV.V-v0.UV.V
		det := du1*dv2 - du2*dv1
		if det > -1e-12 && det < 1e-12 {
			continue
		}
		r := 1 / det
		t := e1.Mul(dv2 * r).Sub(e2.Mul(dv1 * r))
		b := e2.Mul(du1 * r).Sub(e1.Mul(du2 * r))
		for _, k := range []uint32{i0, i1, i2} {
			tan[k] = tan[k].Add(t)
			bit[k] = bit[k].Add(b)
		}
	}
	out := make([][4]float64, n)
	for i, v := range g.Verts {
		nn := v.N
		t := tan[i].Sub(nn.Mul(nn.Dot(tan[i])))
		if t.Len() < 1e-9 {
			// fallback: any perpendicular
			ref := V3(0, 0, 1)
			if nn.Z > 0.9 || nn.Z < -0.9 {
				ref = V3(1, 0, 0)
			}
			t = ref.Cross(nn)
		}
		t = t.Norm()
		w := 1.0
		if nn.Cross(t).Dot(bit[i]) < 0 {
			w = -1
		}
		out[i] = [4]float64{t.X, t.Y, t.Z, w}
	}
	return out
}
