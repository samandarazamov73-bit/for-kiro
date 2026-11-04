"""bpy object helpers (collections, empties, mesh objects, shared module meshes)."""
import bpy
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


class Library:
    """Shared module meshes (linked duplicates -> glTF mesh instancing)."""

    def __init__(self, mats):
        self.mats = mats
        self.meshes = {}
        self.unique_tris = 0

    def get(self, key, builder):
        if key not in self.meshes:
            mb = builder()
            self.unique_tris += mb.tris()
            self.meshes[key] = (mesh_data(mb, self.mats, "SM_" + key), mb.tris())
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
