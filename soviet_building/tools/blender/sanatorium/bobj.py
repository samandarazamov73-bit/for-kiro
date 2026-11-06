"""bpy object helpers (collections, empties, mesh objects, shared module meshes)."""
import math
import bmesh
import bpy
from mathutils import Vector
from .materials import NAME

_coll = {}


def collection(name, parent=None):
    if name in _coll:
        return _coll[name]
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c) if c.name not in (
        parent or bpy.context.scene.collection).children else None
    _coll[name] = c
    return c


def empty(name, coll, parent=None, loc=(0, 0, 0), props=None):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.3
    e.location = loc
    coll.objects.link(e)
    if parent:
        e.parent = parent
    for k, v in (props or {}).items():
        e[k] = v
    return e


def mesh_data(mb, mats, name=None):
    me = bpy.data.meshes.new(name or mb.name)
    me.from_pydata(mb.v, [], mb.f)
    for m in mb.mats:
        me.materials.append(mats[m] if m in mats else bpy.data.materials.get(NAME.get(m, m)))
    if mb.f:
        me.polygons.foreach_set("material_index", mb.mi)
        uvl = me.uv_layers.new(name="UVMap")
        flat = [c for uv in mb.uv for c in uv]
        uvl.data.foreach_set("uv", flat)
    me.validate(clean_customdata=False)
    me.update()
    return me


def mesh_object(mb, mats, coll, parent=None, name=None, props=None):
    if mb.empty():
        return None
    me = mesh_data(mb, mats, name)
    ob = bpy.data.objects.new(name or mb.name, me)
    coll.objects.link(ob)
    if parent:
        ob.parent = parent
    for k, v in (props or {}).items():
        ob[k] = v
    return ob


def soften(me, width=0.01, segments=2, bevel_above=50.0, smooth_below=50.0):
    """Takes the "made of boxes" look off a module: welds its loose quads, rounds every sharp edge with a
    small two-segment bevel, and sets area-weighted normals, so large faces stay flat while the rounded
    edges and the sides of cylinders shade smoothly. The silhouette and footprint stay the same."""
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    lim = math.radians(bevel_above)

    def wide(f):            # thin parts (legs, rails, hooks, buttons) stay as they are: rounding them shows
        return min(e.calc_length() for e in f.edges) > 0.035     # no difference and only costs triangles
    # glowing lamp shades and lamp glass stay as they are: a bevel shows on them as dark seams
    glow = {i for i, m in enumerate(me.materials) if m and ("Emissive" in m.name or "Lamp_Off" in m.name)}
    edges = [e for e in bm.edges if e.is_manifold and e.calc_face_angle(0.0) > lim
             and all(wide(f) and f.material_index not in glow for f in e.link_faces)]
    if edges and width > 0.0:
        bmesh.ops.bevel(bm, geom=edges, offset=width, offset_type="OFFSET", segments=segments, profile=0.5,
                        affect="EDGES", clamp_overlap=True, loop_slide=True)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges)
    bm.to_mesh(me)
    bm.free()
    me.validate(clean_customdata=False)
    me.update()
    if not me.polygons:
        return
    me.shade_smooth()
    cos_lim = math.cos(math.radians(smooth_below))
    around = [[] for _ in me.vertices]
    for p in me.polygons:
        n, a = p.normal.copy(), p.area
        for vi in p.vertices:
            around[vi].append((n, a))
    normals = [None] * len(me.loops)
    for p in me.polygons:
        n0 = p.normal
        for li in p.loop_indices:
            acc = Vector((0.0, 0.0, 0.0))
            for n, a in around[me.loops[li].vertex_index]:
                if n.dot(n0) > cos_lim:
                    acc += n * a
            normals[li] = acc.normalized() if acc.length > 1e-12 else n0.copy()
    me.normals_split_custom_set(normals)


def soften_width(mb):
    """Bevel size from the module's size: about a centimetre on furniture, less on small things."""
    if not mb.v:
        return 0.0
    ext = max(max(v[k] for v in mb.v) - min(v[k] for v in mb.v) for k in range(3))
    return min(0.012, max(0.003, ext * 0.02))


class Library:
    """Shared module meshes (linked duplicates -> glTF mesh instancing)."""

    def __init__(self, mats):
        self.mats = mats
        self.meshes = {}
        self.unique_tris = 0

    def get(self, key, builder):
        if key not in self.meshes:
            mb = builder()
            me = mesh_data(mb, self.mats, "SM_" + key)
            # modules shaped from round cross-sections (lofts) only need the smooth normals
            soften(me, 0.0 if getattr(mb, "smooth_only", False) else soften_width(mb))
            tris = sum(len(p.vertices) - 2 for p in me.polygons)
            self.unique_tris += tris
            self.meshes[key] = (me, tris)
        return self.meshes[key]

    def place(self, key, builder, coll, name, loc, rot_z=0.0, parent=None, props=None, scale=None):
        me, tris = self.get(key, builder)
        ob = bpy.data.objects.new(name, me)
        ob.location = loc
        ob.rotation_euler = (0, 0, rot_z)
        if scale:
            ob.scale = scale
        coll.objects.link(ob)
        if parent:
            ob.parent = parent
            ob.matrix_parent_inverse = parent.matrix_world.inverted()
        for k, v in (props or {}).items():
            ob[k] = v
        return ob

    def remove(self, ob):
        bpy.data.objects.remove(ob, do_unlink=True)
