"""Blender materials for the interior (glTF-compatible node graphs) and the combined-scene
adjustments of the existing exterior materials."""
import os
import bpy

# key -> (material name, texture set, uv tile size in metres, options)
MATS = {
    "paint_green": ("M_Paint_WallGreen", "T_Paint_WallGreen", 3.0, {}),
    "paint_blue": ("M_Paint_WallBlue", "T_Paint_WallBlue", 3.0, {}),
    "paint_beige": ("M_Paint_WallBeige", "T_Paint_WallBeige", 3.0, {}),
    "paint_peach": ("M_Paint_WallPeach", "T_Paint_WallPeach", 3.0, {}),
    "tile_wall": ("M_Tile_WallWhite", "T_Tile_WallWhite", 3.0, {}),
    "wallpaper_a": ("M_Wallpaper_Floral", "T_Wallpaper_Floral", 3.0, {}),
    "wallpaper_b": ("M_Wallpaper_Geometric", "T_Wallpaper_Geometric", 3.0, {}),
    "plaster": ("M_Plaster_White", "T_Plaster_White", 2.0, {}),
    "ceiling": ("M_Ceiling_Paint", "T_Ceiling_Paint", 2.0, {}),
    "concrete": ("M_Concrete_Interior", "T_Concrete_Interior", 2.0, {}),
    "linoleum_brown": ("M_Linoleum_Brown", "T_Linoleum_Brown", 2.0, {}),
    "linoleum_parquet": ("M_Linoleum_Parquet", "T_Linoleum_Parquet", 2.0, {}),
    "tile_floor": ("M_Tile_FloorCeramic", "T_Tile_FloorCeramic", 2.0, {}),
    "terrazzo": ("M_Terrazzo", "T_Terrazzo", 2.0, {}),
    "wood_door": ("M_Wood_DoorDark", "T_Wood_DoorDark", 1.0, {}),
    "wood": ("M_Wood_Furniture", "T_Wood_Furniture", 1.0, {}),
    "metal_painted": ("M_Metal_Painted", "T_Metal_Painted", 1.0, {"metal_map": True}),
    "metal_rusty": ("M_Metal_DarkSteel", "T_Metal_DarkSteel", 1.0, {"metal_map": True}),
    "glass_dusty": ("M_Glass_Clear", "T_Glass_Clear", 1.0, {"blend": True, "double": True}),
    "salt_brick": ("M_Salt_Brick", "T_Salt_Brick", 3.0, {}),
    "atlas_furn": ("M_Atlas_Furniture", "T_Atlas_Furniture", 1.0, {"metal_map": True}),
    "atlas_decal": ("M_Atlas_Decals", "T_Atlas_Decals", 1.0, {"clip": True, "double": True}),
    "atlas_decal_blend": ("M_Atlas_Decals_Blend", "T_Atlas_Decals", 1.0, {"blend": True, "double": True}),
    "atlas_signs": ("M_Atlas_Signs", "T_Atlas_Signs", 1.0, {}),
    "emit_fluo": ("M_Emissive_Fluorescent", None, 1.0, {"emit": (1.0, 0.94, 0.84), "strength": 6.0}),
    "emit_warm": ("M_Emissive_Incandescent", None, 1.0, {"emit": (1.0, 0.8, 0.56), "strength": 5.0}),
    "emit_shade": ("M_Emissive_LampShade", None, 1.0, {"emit": (1.0, 0.76, 0.46), "strength": 1.6}),
    "emit_off": ("M_Lamp_Off", None, 1.0, {"color": (0.62, 0.61, 0.58), "rough": 0.25}),
    "lift_lamp": ("M_Emissive_LiftLamp", None, 1.0, {"emit": (1.0, 0.25, 0.1), "strength": 3.0}),
}
UV_SCALE = {k: v[2] for k, v in MATS.items()}
NAME = {k: v[0] for k, v in MATS.items()}

_cache = {}


def _img(tex_dir, name, non_color):
    path = os.path.join(tex_dir, name + ".png")
    if not os.path.exists(path):
        return None
    key = os.path.abspath(path)
    if key in _cache:
        return _cache[key]
    im = bpy.data.images.load(path, check_existing=True)
    im.name = name
    if non_color:
        im.colorspace_settings.name = "Non-Color"
    _cache[key] = im
    return im


def gltf_output_group():
    """The node group the Blender glTF exporter reads ambient occlusion from."""
    g = bpy.data.node_groups.get("glTF Material Output")
    if g:
        return g
    g = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
    g.interface.new_socket("Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
    g.interface.new_socket("Thickness", in_out="INPUT", socket_type="NodeSocketFloat")
    g.nodes.new("NodeGroupInput")
    return g


def make(key, tex_dir):
    mname, tset, _, opt = MATS[key]
    m = bpy.data.materials.get(mname)
    if m:
        return m
    m = bpy.data.materials.new(mname)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (600, 0)
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled"); bs.location = (250, 0)
    nt.links.new(bs.outputs[0], out.inputs[0])
    if "emit" in opt:
        bs.inputs["Base Color"].default_value = (*opt["emit"], 1)
        bs.inputs["Emission Color"].default_value = (*opt["emit"], 1)
        bs.inputs["Emission Strength"].default_value = opt["strength"]
        bs.inputs["Roughness"].default_value = 0.4
        return m
    if tset is None:
        bs.inputs["Base Color"].default_value = (*opt.get("color", (0.6, 0.6, 0.6)), 1)
        bs.inputs["Roughness"].default_value = opt.get("rough", 0.5)
        return m
    base = _img(tex_dir, tset + "_BaseColor", False)
    orm = _img(tex_dir, tset + "_ORM", True)
    nrm = _img(tex_dir, tset + "_Normal", True)
    tb = nt.nodes.new("ShaderNodeTexImage"); tb.image = base; tb.location = (-500, 300)
    nt.links.new(tb.outputs["Color"], bs.inputs["Base Color"])
    if orm:
        to = nt.nodes.new("ShaderNodeTexImage"); to.image = orm; to.location = (-500, 0)
        sp = nt.nodes.new("ShaderNodeSeparateColor"); sp.location = (-200, 0)
        nt.links.new(to.outputs["Color"], sp.inputs[0])
        nt.links.new(sp.outputs[1], bs.inputs["Roughness"])
        if opt.get("metal_map"):
            nt.links.new(sp.outputs[2], bs.inputs["Metallic"])
        else:
            bs.inputs["Metallic"].default_value = 0.0
        go = nt.nodes.new("ShaderNodeGroup"); go.node_tree = gltf_output_group(); go.location = (250, -400)
        nt.links.new(sp.outputs[0], go.inputs["Occlusion"])
    if nrm:
        tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = nrm; tn.location = (-500, -300)
        nm = nt.nodes.new("ShaderNodeNormalMap"); nm.location = (-200, -300)
        nm.inputs["Strength"].default_value = 1.0
        nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bs.inputs["Normal"])
    if opt.get("blend") or opt.get("clip"):
        nt.links.new(tb.outputs["Alpha"], bs.inputs["Alpha"])
        m.surface_render_method = "BLENDED" if opt.get("blend") else "DITHERED"
        if opt.get("clip"):
            # glTF exporter writes alphaMode MASK when the alpha passes through a Math "greater than" node
            mt = nt.nodes.new("ShaderNodeMath"); mt.operation = "GREATER_THAN"; mt.location = (0, 200)
            mt.inputs[1].default_value = 0.5
            nt.links.new(tb.outputs["Alpha"], mt.inputs[0])
            nt.links.new(mt.outputs[0], bs.inputs["Alpha"])
    if key == "glass_dusty":
        bs.inputs["IOR"].default_value = 1.0     # thin pane: no refraction offset
        bs.inputs["Roughness"].default_value = 0.1
    m.use_backface_culling = not opt.get("double", False)
    return m


def all_materials(tex_dir):
    return {k: make(k, tex_dir) for k in MATS}


def adapt_exterior(tex_dir):
    """Combined scene only: see-through dusty glass instead of the fake-interior atlas glass,
    double-sided window frames (they are single-sided outward), and exterior images re-linked
    to the PNGs in textures/ instead of being packed copies from the GLB."""
    glass = make("glass_dusty", tex_dir)
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        for slot in ob.material_slots:
            if slot.material and slot.material.name.startswith("M_Glass") and slot.material is not glass:
                slot.material = glass
    fr = bpy.data.materials.get("M_Window_Frame")
    if fr:
        fr.use_backface_culling = False
    for im in list(bpy.data.images):
        if im.packed_file is None:
            continue
        for ext in (".png", ".jpg"):
            p = os.path.join(tex_dir, im.name + ext)
            if os.path.exists(p):
                new = bpy.data.images.load(p, check_existing=True)
                new.colorspace_settings.name = im.colorspace_settings.name
                im.user_remap(new)
                bpy.data.images.remove(im)
                new.name = os.path.splitext(os.path.basename(p))[0]
                break
