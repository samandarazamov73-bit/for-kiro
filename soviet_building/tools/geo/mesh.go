package geo

import "math"

// Vertex holds position, normal and UV (v up).
type Vertex struct {
	P, N Vec3
	UV   Vec2
}

// Group is a triangle list using one material.
type Group struct {
	Mat   string
	Verts []Vertex
	Idx   []uint32
}

// Mesh is a set of triangle groups (one per material) in world space.
type Mesh struct {
	Name   string
	Groups []*Group
	byMat  map[string]*Group
}

func NewMesh(name string) *Mesh { return &Mesh{Name: name, byMat: map[string]*Group{}} }

func (m *Mesh) G(mat string) *Group {
	if g, ok := m.byMat[mat]; ok {
		return g
	}
	g := &Group{Mat: mat}
	m.byMat[mat] = g
	m.Groups = append(m.Groups, g)
	return g
}

func (g *Group) Add(v Vertex) uint32 {
	g.Verts = append(g.Verts, v)
	return uint32(len(g.Verts) - 1)
}

func (m *Mesh) TriCount() int {
	n := 0
	for _, g := range m.Groups {
		n += len(g.Idx) / 3
	}
	return n
}

// Append copies all groups of o into m.
func (m *Mesh) Append(o *Mesh) {
	for _, og := range o.Groups {
		g := m.G(og.Mat)
		base := uint32(len(g.Verts))
		g.Verts = append(g.Verts, og.Verts...)
		for _, i := range og.Idx {
			g.Idx = append(g.Idx, i+base)
		}
	}
}

// Transform applies f to every position and fn to every normal.
func (m *Mesh) Transform(f func(Vec3) Vec3, fn func(Vec3) Vec3) {
	for _, g := range m.Groups {
		for i := range g.Verts {
			g.Verts[i].P = f(g.Verts[i].P)
			g.Verts[i].N = fn(g.Verts[i].N).Norm()
		}
	}
}

// UVFn maps a point with face normal n to a texture coordinate.
type UVFn func(p, n Vec3) Vec2

// WorldUV returns a box-projection mapper: one texture repeat = su x sv metres.
// Faces are mapped un-mirrored as seen from outside.
func WorldUV(su, sv, ou, ov float64) UVFn {
	return func(p, n Vec3) Vec2 {
		ax, ay, az := math.Abs(n.X), math.Abs(n.Y), math.Abs(n.Z)
		var u, v float64
		switch {
		case az >= ax && az >= ay:
			u, v = p.X, p.Y
			if n.Z < 0 {
				v = -p.Y
			}
		case ay >= ax:
			u, v = p.X, p.Z
			if n.Y > 0 {
				u = -p.X
			}
		default:
			u, v = -p.Y, p.Z
			if n.X > 0 {
				u = p.Y
			}
		}
		return Vec2{u/su + ou, v/sv + ov}
	}
}

func FaceNormal(a, b, c Vec3) Vec3 { return b.Sub(a).Cross(c.Sub(a)).Norm() }

// Tri adds a flat triangle (CCW front).
func (m *Mesh) Tri(mat string, a, b, c Vec3, uv UVFn) {
	n := FaceNormal(a, b, c)
	g := m.G(mat)
	i0 := g.Add(Vertex{a, n, uv(a, n)})
	i1 := g.Add(Vertex{b, n, uv(b, n)})
	i2 := g.Add(Vertex{c, n, uv(c, n)})
	g.Idx = append(g.Idx, i0, i1, i2)
}

// Poly adds a planar convex polygon (CCW front) as a triangle fan.
func (m *Mesh) Poly(mat string, pts []Vec3, uv UVFn) {
	if len(pts) < 3 {
		return
	}
	// robust normal (Newell)
	var n Vec3
	for i := range pts {
		a, b := pts[i], pts[(i+1)%len(pts)]
		n.X += (a.Y - b.Y) * (a.Z + b.Z)
		n.Y += (a.Z - b.Z) * (a.X + b.X)
		n.Z += (a.X - b.X) * (a.Y + b.Y)
	}
	n = n.Norm()
	g := m.G(mat)
	base := uint32(len(g.Verts))
	for _, p := range pts {
		g.Add(Vertex{p, n, uv(p, n)})
	}
	for i := 1; i+1 < len(pts); i++ {
		g.Idx = append(g.Idx, base, base+uint32(i), base+uint32(i+1))
	}
}

// PolyUV adds a convex polygon with explicit UVs.
func (m *Mesh) PolyUV(mat string, pts []Vec3, uvs []Vec2) {
	var n Vec3
	for i := range pts {
		a, b := pts[i], pts[(i+1)%len(pts)]
		n.X += (a.Y - b.Y) * (a.Z + b.Z)
		n.Y += (a.Z - b.Z) * (a.X + b.X)
		n.Z += (a.X - b.X) * (a.Y + b.Y)
	}
	n = n.Norm()
	g := m.G(mat)
	base := uint32(len(g.Verts))
	for i, p := range pts {
		g.Add(Vertex{p, n, uvs[i]})
	}
	for i := 1; i+1 < len(pts); i++ {
		g.Idx = append(g.Idx, base, base+uint32(i), base+uint32(i+1))
	}
}

// Quad adds a quad a,b,c,d (CCW front).
func (m *Mesh) Quad(mat string, a, b, c, d Vec3, uv UVFn) { m.Poly(mat, []Vec3{a, b, c, d}, uv) }

// Face flags for Box.
const (
	FXn = 1 << iota // face toward -X
	FXp
	FYn
	FYp
	FZn
	FZp
	FAll = FXn | FXp | FYn | FYp | FZn | FZp
)

// Box adds an axis aligned box with the selected faces.
func (m *Mesh) Box(mat string, lo, hi Vec3, faces int, uv UVFn) {
	x0, y0, z0 := lo.X, lo.Y, lo.Z
	x1, y1, z1 := hi.X, hi.Y, hi.Z
	if faces&FXn != 0 {
		m.Quad(mat, V3(x0, y1, z0), V3(x0, y0, z0), V3(x0, y0, z1), V3(x0, y1, z1), uv)
	}
	if faces&FXp != 0 {
		m.Quad(mat, V3(x1, y0, z0), V3(x1, y1, z0), V3(x1, y1, z1), V3(x1, y0, z1), uv)
	}
	if faces&FYn != 0 {
		m.Quad(mat, V3(x0, y0, z0), V3(x1, y0, z0), V3(x1, y0, z1), V3(x0, y0, z1), uv)
	}
	if faces&FYp != 0 {
		m.Quad(mat, V3(x1, y1, z0), V3(x0, y1, z0), V3(x0, y1, z1), V3(x1, y1, z1), uv)
	}
	if faces&FZn != 0 {
		m.Quad(mat, V3(x0, y1, z0), V3(x1, y1, z0), V3(x1, y0, z0), V3(x0, y0, z0), uv)
	}
	if faces&FZp != 0 {
		m.Quad(mat, V3(x0, y0, z1), V3(x1, y0, z1), V3(x1, y1, z1), V3(x0, y1, z1), uv)
	}
}

// Prism extrudes a closed CCW (seen from +axis) polygon given in the plane
// perpendicular to dir, from base points pts by vector dir. Side faces + caps.
func (m *Mesh) Prism(mat string, pts []Vec3, dir Vec3, capBase, capTop bool, uv UVFn) {
	n := len(pts)
	top := make([]Vec3, n)
	for i, p := range pts {
		top[i] = p.Add(dir)
	}
	for i := 0; i < n; i++ {
		j := (i + 1) % n
		m.Quad(mat, pts[i], pts[j], top[j], top[i], uv)
	}
	if capTop {
		m.Poly(mat, top, uv)
	}
	if capBase {
		rev := make([]Vec3, n)
		for i := range pts {
			rev[i] = pts[n-1-i]
		}
		m.Poly(mat, rev, uv)
	}
}

// Tube sweeps a circle of radius r with the given number of sides along a
// polyline with mitred joints and smooth normals. vScale = metres per V repeat.
func (m *Mesh) Tube(mat string, path []Vec3, r float64, sides int, capStart, capEnd bool, vScale float64, phase float64) {
	if len(path) < 2 {
		return
	}
	g := m.G(mat)
	np := len(path)
	dirs := make([]Vec3, np-1)
	for i := 0; i < np-1; i++ {
		dirs[i] = path[i+1].Sub(path[i]).Norm()
	}
	// initial frame
	d0 := dirs[0]
	ref := V3(0, 0, 1)
	if math.Abs(d0.Dot(ref)) > 0.9 {
		ref = V3(1, 0, 0)
	}
	a := d0.Cross(ref).Norm()
	b := d0.Cross(a).Norm()
	rings := make([][]uint32, np)
	vlen := 0.0
	for i := 0; i < np; i++ {
		var din, t Vec3
		if i == 0 {
			din, t = dirs[0], dirs[0]
		} else if i == np-1 {
			din, t = dirs[np-2], dirs[np-2]
		} else {
			din = dirs[i-1]
			t = dirs[i-1].Add(dirs[i]).Norm()
		}
		if i > 0 {
			vlen += path[i].Sub(path[i-1]).Len()
		}
		ring := make([]uint32, sides+1)
		for k := 0; k <= sides; k++ {
			th := 2*math.Pi*float64(k)/float64(sides) + phase
			off := a.Mul(math.Cos(th) * r).Add(b.Mul(math.Sin(th) * r))
			den := din.Dot(t)
			p := path[i].Add(off)
			if math.Abs(den) > 1e-6 {
				p = p.Sub(din.Mul(off.Dot(t) / den))
			}
			nrm := p.Sub(path[i])
			nrm = nrm.Sub(t.Mul(nrm.Dot(t))).Norm()
			ring[k] = g.Add(Vertex{p, nrm, V2(float64(k)/float64(sides), vlen/vScale)})
		}
		rings[i] = ring
		// parallel transport frame to next segment
		if i < np-2 {
			d1, d2 := dirs[i], dirs[i+1]
			ax := d1.Cross(d2)
			s := ax.Len()
			if s > 1e-9 {
				ax = ax.Mul(1 / s)
				ang := math.Atan2(s, d1.Dot(d2))
				a = rotAxis(a, ax, ang)
				b = rotAxis(b, ax, ang)
			}
		}
	}
	for i := 0; i < np-1; i++ {
		r0, r1 := rings[i], rings[i+1]
		for k := 0; k < sides; k++ {
			g.Idx = append(g.Idx, r0[k], r0[k+1], r1[k+1], r0[k], r1[k+1], r1[k])
		}
	}
	addCap := func(ring []uint32, n Vec3, flip bool) {
		base := uint32(len(g.Verts))
		for k := 0; k < sides; k++ {
			v := g.Verts[ring[k]]
			th := 2 * math.Pi * float64(k) / float64(sides)
			g.Add(Vertex{v.P, n, V2(0.5+0.5*math.Cos(th), 0.5+0.5*math.Sin(th))})
		}
		for k := 1; k+1 < sides; k++ {
			if flip {
				g.Idx = append(g.Idx, base, base+uint32(k+1), base+uint32(k))
			} else {
				g.Idx = append(g.Idx, base, base+uint32(k), base+uint32(k+1))
			}
		}
	}
	if capStart {
		addCap(rings[0], dirs[0].Neg(), true)
	}
	if capEnd {
		addCap(rings[np-1], dirs[np-2], false)
	}
}

func rotAxis(v, ax Vec3, ang float64) Vec3 {
	c, s := math.Cos(ang), math.Sin(ang)
	return v.Mul(c).Add(ax.Cross(v).Mul(s)).Add(ax.Mul(ax.Dot(v) * (1 - c)))
}

// BoxRot adds a box of size (sx, sy, sz) centred at c rotated by ang around Z.
func (m *Mesh) BoxRot(mat string, c Vec3, sx, sy, sz, ang float64, faces int, uv UVFn) {
	tmp := NewMesh("")
	tmp.Box(mat, V3(-sx/2, -sy/2, -sz/2), V3(sx/2, sy/2, sz/2), faces, func(p, n Vec3) Vec2 { return V2(0, 0) })
	for _, g := range tmp.Groups {
		dst := m.G(g.Mat)
		base := uint32(len(dst.Verts))
		for _, v := range g.Verts {
			p := v.P.RotZ(ang).Add(c)
			n := v.N.RotZ(ang)
			dst.Add(Vertex{p, n, uv(p, n)})
		}
		for _, i := range g.Idx {
			dst.Idx = append(dst.Idx, i+base)
		}
	}
}
