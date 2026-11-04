package geo

import (
	"bytes"
	"compress/zlib"
	"encoding/binary"
	"math"
)

// Minimal binary FBX 7.4 encoder (structure mirrors Blender's encode_bin.py).

type fprop struct {
	t    byte
	data []byte
}

type fnode struct {
	name  string
	props []fprop
	kids  []*fnode
}

func le(v any) []byte {
	var b bytes.Buffer
	binary.Write(&b, binary.LittleEndian, v)
	return b.Bytes()
}

func arrProp(t byte, n int, raw []byte) fprop {
	var out bytes.Buffer
	enc := uint32(0)
	payload := raw
	if len(raw) > 128 {
		var z bytes.Buffer
		w, _ := zlib.NewWriterLevel(&z, zlib.BestCompression)
		w.Write(raw)
		w.Close()
		payload, enc = z.Bytes(), 1
	}
	binary.Write(&out, binary.LittleEndian, uint32(n))
	binary.Write(&out, binary.LittleEndian, enc)
	binary.Write(&out, binary.LittleEndian, uint32(len(payload)))
	out.Write(payload)
	return fprop{t, out.Bytes()}
}

func toProp(v any) fprop {
	switch x := v.(type) {
	case int32:
		return fprop{'I', le(x)}
	case int:
		return fprop{'I', le(int32(x))}
	case int64:
		return fprop{'L', le(x)}
	case float64:
		return fprop{'D', le(x)}
	case bool:
		if x {
			return fprop{'C', []byte{1}}
		}
		return fprop{'C', []byte{0}}
	case string:
		return fprop{'S', append(le(uint32(len(x))), x...)}
	case []byte:
		return fprop{'R', append(le(uint32(len(x))), x...)}
	case []float64:
		return arrProp('d', len(x), le(x))
	case []int32:
		return arrProp('i', len(x), le(x))
	case []int64:
		return arrProp('l', len(x), le(x))
	}
	panic("fbx: unsupported property type")
}

func (n *fnode) add(name string, props ...any) *fnode {
	c := &fnode{name: name}
	for _, p := range props {
		c.props = append(c.props, toProp(p))
	}
	n.kids = append(n.kids, c)
	return c
}

// p70 adds a Properties70 "P" entry.
func p70(n *fnode, name, typ, label, flags string, vals ...any) {
	n.add("P", append([]any{name, typ, label, flags}, vals...)...)
}

func (n *fnode) propLen() int {
	s := 0
	for _, p := range n.props {
		s += 1 + len(p.data)
	}
	return s
}

func (n *fnode) needsSentinel() bool { return len(n.kids) > 0 || len(n.props) == 0 }

func (n *fnode) size() int {
	s := 13 + len(n.name) + n.propLen()
	for _, k := range n.kids {
		s += k.size()
	}
	if n.needsSentinel() {
		s += 13
	}
	return s
}

func (n *fnode) write(b *bytes.Buffer) {
	end := b.Len() + n.size()
	binary.Write(b, binary.LittleEndian, uint32(end))
	binary.Write(b, binary.LittleEndian, uint32(len(n.props)))
	binary.Write(b, binary.LittleEndian, uint32(n.propLen()))
	b.WriteByte(byte(len(n.name)))
	b.WriteString(n.name)
	for _, p := range n.props {
		b.WriteByte(p.t)
		b.Write(p.data)
	}
	for _, k := range n.kids {
		k.write(b)
	}
	if n.needsSentinel() {
		b.Write(make([]byte, 13))
	}
}

var _ = math.Pi
