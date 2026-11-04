package geo

import (
	"bytes"
	"encoding/binary"
	"math"
	"os"
)

var fbxFileID = []byte{0x28, 0xb3, 0x2a, 0xeb, 0xb6, 0x24, 0xcc, 0xc2, 0xbf, 0xc8, 0xb0, 0x2a, 0xa9, 0x2b, 0xfc, 0xf1}
var fbxFootID = []byte{0xfa, 0xbc, 0xab, 0x09, 0xd0, 0xc8, 0xd4, 0x66, 0xb1, 0x76, 0xfb, 0x83, 0x1c, 0xf7, 0x26, 0x7e}
var fbxFootEnd = []byte{0xf8, 0x5a, 0x8c, 0x6a, 0xde, 0xf5, 0xd9, 0x7e, 0xec, 0xe9, 0x0c, 0xe3, 0x75, 0x8f, 0x29, 0x0b}

const fbxCreator = "sovbuild FBX 7.4 exporter"

func fbxHeader(root *fnode) {
	hx := root.add("FBXHeaderExtension")
	hx.add("FBXHeaderVersion", int32(1003))
	hx.add("FBXVersion", int32(7400))
	hx.add("EncryptionType", int32(0))
	ts := hx.add("CreationTimeStamp")
	for _, kv := range []struct {
		k string
		v int32
	}{{"Version", 1000}, {"Year", 1970}, {"Month", 1}, {"Day", 1}, {"Hour", 10}, {"Minute", 0}, {"Second", 0}, {"Millisecond", 0}} {
		ts.add(kv.k, kv.v)
	}
	hx.add("Creator", fbxCreator)
	si := hx.add("SceneInfo", "GlobalInfo\x00\x01SceneInfo", "UserData")
	si.add("Type", "UserData")
	si.add("Version", int32(100))
	md := si.add("MetaData")
	md.add("Version", int32(100))
	for _, k := range []string{"Title", "Subject", "Author", "Keywords", "Revision", "Comment"} {
		v := ""
		if k == "Title" {
			v = "Soviet-era institutional building (low poly)"
		}
		md.add(k, v)
	}
	si.add("Properties70")
	root.add("FileId", fbxFileID)
	root.add("CreationTime", "1970-01-01 10:00:00:000")
	root.add("Creator", fbxCreator)
	gs := root.add("GlobalSettings")
	gs.add("Version", int32(1000))
	gp := gs.add("Properties70")
	for _, a := range []struct {
		n string
		v int32
	}{{"UpAxis", 1}, {"UpAxisSign", 1}, {"FrontAxis", 2}, {"FrontAxisSign", 1}, {"CoordAxis", 0}, {"CoordAxisSign", 1}, {"OriginalUpAxis", 1}, {"OriginalUpAxisSign", 1}} {
		p70(gp, a.n, "int", "Integer", "", a.v)
	}
	p70(gp, "UnitScaleFactor", "double", "Number", "", 100.0)
	p70(gp, "OriginalUnitScaleFactor", "double", "Number", "", 100.0)
	p70(gp, "AmbientColor", "ColorRGB", "Color", "", 0.0, 0.0, 0.0)
	p70(gp, "DefaultCamera", "KString", "", "", "Producer Perspective")
	p70(gp, "TimeMode", "enum", "", "", int32(11))
	p70(gp, "TimeSpanStart", "KTime", "Time", "", int64(0))
	p70(gp, "TimeSpanStop", "KTime", "Time", "", int64(46186158000))
	p70(gp, "CustomFrameRate", "double", "Number", "", -1.0)
}

func fbxFinish(root *fnode, path string) error {
	var b bytes.Buffer
	b.WriteString("Kaydara FBX Binary  \x00")
	b.Write([]byte{0x1a, 0x00})
	binary.Write(&b, binary.LittleEndian, uint32(7400))
	// node end offsets are absolute: the encoder measures from the buffer start
	for _, k := range root.kids {
		k.write(&b)
	}
	b.Write(make([]byte, 13))
	b.Write(fbxFootID)
	b.Write(make([]byte, 4))
	pad := ((b.Len() + 15) &^ 15) - b.Len()
	if pad == 0 {
		pad = 16
	}
	b.Write(make([]byte, pad))
	binary.Write(&b, binary.LittleEndian, uint32(7400))
	b.Write(make([]byte, 120))
	b.Write(fbxFootEnd)
	return os.WriteFile(path, b.Bytes(), 0o644)
}

var _ = math.Abs
