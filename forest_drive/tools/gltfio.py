"""Minimal glTF 2.0 reader (numpy) for inspecting/decimating CC0 scans."""
import json, os, numpy as np
CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
def quat_to_mat(q):
    x, y, z, w = q
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                     [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
def node_matrix(n):
    if "matrix" in n: return np.array(n["matrix"], dtype=np.float64).reshape(4, 4).T
    m = np.eye(4)
    s = np.array(n.get("scale", [1, 1, 1])); r = n.get("rotation", [0, 0, 0, 1]); t = n.get("translation", [0, 0, 0])
    m[:3, :3] = quat_to_mat(r) * s[None, :]; m[:3, 3] = t
    return m
class Gltf:
    def __init__(self, path):
        self.path = path; self.dir = os.path.dirname(path)
        self.j = json.load(open(path))
        self.bufs = [open(os.path.join(self.dir, b["uri"]), "rb").read() for b in self.j["buffers"]]
    def acc(self, i):
        a = self.j["accessors"][i]; bv = self.j["bufferViews"][a["bufferView"]]
        dt = CT[a["componentType"]]; nc = NC[a["type"]]
        off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        stride = bv.get("byteStride", 0); isz = np.dtype(dt).itemsize * nc
        buf = self.bufs[bv["buffer"]]
        if stride and stride != isz:
            raw = np.frombuffer(buf, dtype=np.uint8, count=stride * (a["count"] - 1) + isz, offset=off)
            idx = (np.arange(a["count"])[:, None] * stride + np.arange(isz)[None, :])
            arr = raw[idx].view(dt).reshape(a["count"], nc)
        else:
            arr = np.frombuffer(buf, dtype=dt, count=a["count"] * nc, offset=off).reshape(a["count"], nc)
        arr = arr.astype(np.float64 if dt == np.float32 else arr.dtype)
        if a.get("normalized") and dt != np.float32:
            arr = arr / float(np.iinfo(dt).max)
        return arr
    def meshes_world(self):
        """Yield (node_name, mesh_name, material_name, dict of world-space arrays) for each primitive."""
        j = self.j; out = []
        def walk(ni, parent):
            n = j["nodes"][ni]; m = parent @ node_matrix(n)
            if "mesh" in n:
                me = j["meshes"][n["mesh"]]
                for p in me["primitives"]:
                    at = p["attributes"]; d = {}
                    pos = self.acc(at["POSITION"]); d["pos"] = (pos @ m[:3, :3].T) + m[:3, 3]
                    if "NORMAL" in at:
                        nm = np.linalg.inv(m[:3, :3]).T; nn = self.acc(at["NORMAL"]) @ nm.T
                        d["nrm"] = nn / np.maximum(np.linalg.norm(nn, axis=1, keepdims=True), 1e-9)
                    if "TEXCOORD_0" in at: d["uv"] = self.acc(at["TEXCOORD_0"])
                    if "COLOR_0" in at: d["col"] = self.acc(at["COLOR_0"])
                    d["idx"] = self.acc(p["indices"]).reshape(-1).astype(np.uint32) if "indices" in p else np.arange(len(pos), dtype=np.uint32)
                    mat = j["materials"][p["material"]]["name"] if "material" in p else ""
                    out.append((n.get("name", ""), me.get("name", ""), mat, d))
            for c in n.get("children", []): walk(c, m)
        sc = j["scenes"][j.get("scene", 0)]
        for r in sc["nodes"]: walk(r, np.eye(4))
        return out
    def material_textures(self):
        res = {}
        for m in self.j.get("materials", []):
            t = {}
            pbr = m.get("pbrMetallicRoughness", {})
            def img(ti): return self.j["images"][self.j["textures"][ti["index"]]["source"]]["uri"]
            if "baseColorTexture" in pbr: t["albedo"] = img(pbr["baseColorTexture"])
            if "metallicRoughnessTexture" in pbr: t["arm"] = img(pbr["metallicRoughnessTexture"])
            if "normalTexture" in m: t["normal"] = img(m["normalTexture"])
            t["alphaMode"] = m.get("alphaMode", "OPAQUE")
            res[m["name"]] = t
        return res
