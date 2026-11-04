# Soviet-era institutional building (1970s school) — realistic low-poly model

A game-ready reconstruction of the reference building: a 4-storey main wing with a red-brown tiled ground floor, a projecting 2-storey entrance / assembly-hall block, a canopy on columns, a wide wrap-around staircase, and a working switchback wheelchair ramp.

**42,040 triangles.** The budget was 30–60k with a target of ~45k. Scale is real-world metres. The model has 23 mesh objects in 7 groups and 10 PBR materials with custom-generated textures.

## Deliverables

| Path | Content |
|---|---|
| `export/SovietSchool.glb` | glTF 2.0 binary with all textures embedded (BaseColor/ORM as JPEG, normal maps as PNG). Recommended format. |
| `export/gltf/SovietSchool.gltf` + `.bin` | glTF 2.0 with external textures (`../../textures/*.png`) |
| `export/fbx/SovietSchool.fbx` | Binary FBX 7.4, Y-up, metres (UnitScaleFactor 100). BaseColor and Normal maps are linked. |
| `export/obj/SovietSchool.obj` + `.mtl` | Y-up, metres. The MTL uses PBR keys: `map_Kd`, `norm`, `map_Pr`, `map_Pm`, `map_Ka` |
| `textures/` | 10 PBR texture sets (see below) |
| `renders/` | Required views, a view matched to the reference camera, close-ups, and texture overview sheets |
| `tools/` | Go source for the whole pipeline: geometry, textures, GLB/glTF/OBJ/FBX writers, and the preview renderer |

Orientation (glTF/FBX/OBJ): Y is up and the main facade faces +Z. The origin is the front-left corner of the main wing at grade level.

## Scene hierarchy (triangles)

```
SovietSchool_1970s
├─ Building        MainWing_Walls 548 · EntranceBlock_Walls 102 · Facade_Trim 214 (belt course, attic bands, parapets, copings)
├─ Windows         MainWing_Window_Surrounds 8,148 · MainWing_Window_Frames 19,012 · MainWing_Window_Glass 388
│                  EntranceBlock_Window_Surrounds 966 · EntranceBlock_Window_Frames 4,366 · EntranceBlock_Window_Glass 46
│                  Lobby_CurtainWall_Doors 268
├─ Entrance        Entrance_Landing_Stairs 66 · Entrance_Stair_Handrails 880 · Entrance_Canopy 42 · Entrance_Columns 90
├─ Ramp            Ramp_Structure 94 · Ramp_Handrails 3,520
├─ Roof            Roof_Surfaces 244 · Roof_Structures 1,248 · Roof_Railing 1,304 · Roof_Drains 70
├─ RearExits       RearExit_Porches 148 · RearExit_Handrails 216
└─ Site            Site_Paving 60 (forecourt, blind strip, paths)
```

Most of the budget goes to the windows (~33k triangles across 217 units). Every window is real geometry: a precast concrete box surround with 25 mm chamfers, a sloped projecting sill, and reveals 0.30 m deep. Inside are a dark-grey frame with mullions and transoms, separate opening sashes set 12 mm back, and a recessed glass pane. Wall surfaces have very few triangles because panel joints, pores, cracks and tile grout are carried by the normal maps.

## Main dimensions

| Element | Value |
|---|---|
| Main wing | 75.0 × 16.2 m, 25 bays × 3.0 m, 4 floors × 3.3 m, ground floor at +1.20 m, roof +14.60, parapet +15.30 (+15.37 with coping) |
| Tiled base | grade to +4.40 m, concrete belt course +4.40…+4.60 |
| Entrance block | 12.0 × 19.5 m (6 bays × 3.25 m), lobby + double-height hall, roof +11.60, parapet +12.30 |
| Windows | Standard unit 2.45 × 2.55 m (clear opening about 2.0 × 2.0 m). Hall windows 2.40 × 5.00 m with 12 lights. |
| Stairs | 8 risers × 150 mm, treads 320 mm, wrap-around flights on two sides, landing 5.5 × 13 m |
| Canopy | 4.9 × 11.4 m slab at +4.00…+4.35 on five 0.4 × 0.4 m columns |

The proportions came from fitting a pinhole camera to 11 points in the reference image (`tools/camfit2.py`, about 5 px RMS). `renders/view_reference_match.png` uses that camera.

## Wheelchair ramp (U-shaped switchback)

| Item | Value |
|---|---|
| Slope | **1:16 (6.25 %)** on every run, within the 1:12 (8.33 %) maximum |
| Outer run | 8.45 m. It rises from grade at the foot of the stairs to the turning landing at +0.53 m. |
| Turning landing | 1.80 × 4.80 m, level. The clear depth inside the rail is 1.53 m, so a 1.5 m turning circle fits. |
| Inner run | 5.375 m, then an intermediate landing of 1.50 m at +0.86 m, then 5.375 m up to the entrance landing at +1.20 m |
| Rise per run | 0.53 m max (within 0.8 m per SP 59.13330 and 0.76 m per ADA) |
| Width | 1.85 m deck. **Clear width between handrails is 1.51 m**; 1.65 m between curbs. |
| Edge protection | 100 × 100 mm concrete curbs on all open edges, and solid concrete side walls down to grade |
| Handrails | 42 mm steel tubes at **0.90 m and 0.70 m**, on both sides of every run |
| Handrail continuity | Rails are continuous along runs and landings. The outer rail wraps the turning landing; the inner rail follows the landing edge at the end of the gap. |
| Extensions | 0.30 m horizontal extensions with bent-down returns at the top and bottom |
| Posts | 48 mm posts ≤ 1.5 m apart on base plates. Welded brackets keep the rails 100 mm off the posts, so the hand can slide past them. |
| Transitions | The foot is flush with the paving, with a 1.5 m level area in front. The top is flush with the entrance landing, and the 1.85 × 1.5 m zone after it is clear of columns. |
| Surface | Broom-finished, non-slip concrete. The grooves run across the direction of travel. |

## Materials and textures

Each set includes `_BaseColor.png` (sRGB), `_Normal.png` (OpenGL convention, +Y), `_ORM.png` (R = AO, G = roughness, B = metallic), plus separate `_Roughness.png` and `_AO.png`. The metal set also has `_Metallic.png`. The `.jpg` copies of BaseColor/ORM are the versions embedded in the GLB.

| Material | Texture set | Size | Repeat | Content |
|---|---|---|---|---|
| M_Concrete_FacadePanel | T_Concrete_FacadePanel | 2048 | 6.0 × 6.6 m (2 bays × 2 floors) | Aged beige panels, joints aligned with the geometry, rain streaks under every sill, cracks from window corners, pores, stains |
| M_Concrete_FacadeWall | T_Concrete_FacadeWall | 2048 | 6.0 × 6.6 m | End walls, hall block, attic bands |
| M_Ceramic_Tile_RedBrown | T_Ceramic_Tile_RedBrown | 2048 | 4.8 × 4.8 m | 232 × 67 mm tiles in running bond with 8 mm grout, varied per tile, splash dirt near grade, efflorescence |
| M_Roofing_Bitumen | T_Roofing_Bitumen | 2048 | 8 × 8 m | Dark-grey membrane with 1 m roll laps, repair patches, dried puddles, dust, moss |
| M_Concrete_Trim | T_Concrete_Trim | 1024 | 2 m | Window surrounds, sills, belt course, copings |
| M_Concrete_Paving | T_Concrete_Paving | 1024 | 3 m | Stairs, ramp, landings, paving: broom finish, saw cuts, stains |
| M_Concrete_Weathered | T_Concrete_Weathered | 1024 | 2.5 m | Canopy, columns, ramp walls, roof structures |
| M_Metal_Handrail | T_Metal_Handrail | 1024 | 1 m | Dark-grey semi-metallic paint with worn spots, rust and scratches |
| M_Glass | T_Glass | 1024 | 4 × 4 atlas | Room interiors behind the glass (dark rooms, tulle, blinds, plants), dirt and rain marks in roughness |
| M_Window_Frame | T_Window_Frame | 1024 | 1.2 m | Dark-grey painted frames with chipped paint |

UV set 0 uses world-space tiling, so texel density is consistent and panel joints line up with the modelled panels. No second UV set for lightmaps is included. Unity and Unreal can generate one on import.

## Corrections made to the reference

- **Ramp.** In the reference, both ramp runs appear to rise in the same direction, so the ramp could not actually work. It was rebuilt as a continuous switchback with correct slopes, level landings, curbs and code-height handrails. The outer run is moved further from the facade to keep the two-run look of the reference.
- **Window grid.** Spacing is regularised (3.0 m bays on the main wing, 3.25 m on the hall block), and every unit is centred on its facade panel.
- **Roof heights.** The entrance block roof sits below the 4th-floor window sills of the main wing, so no window is cut by a roof. Hidden windows behind the block were removed.
- **Canopy.** It was shortened to stay clear of window surrounds, and the first column was moved out of the ramp arrival zone.
- **Stairs.** Steps are uniform at 150 / 320 mm, flights wrap around two sides of the landing, and intermediate handrails with extensions were added.
- **Roof equipment.** Vents, the roof exit, the ventilation chamber, the antenna, the drains and the access ladder all sit on the roof surface. The roof railing is mounted on the parapet coping.

## Engine notes

- **Unity:** import the GLB with glTFast or UnityGLTF, or use the FBX. With the FBX, assign roughness/AO/metallic by hand: put `_Metallic` in R and inverted roughness in A of a mask map, or use HDRP/URP packing.
- **Unreal:** import the glTF or FBX. Normal maps are OpenGL convention, so enable "Flip Green Channel" for DirectX-style materials.
- **Blender:** use File › Import › glTF 2.0 for full PBR. The binary FBX also imports.
- **FBX limitation:** FBX has no standard PBR slots, so only BaseColor and Normal are linked. Assign the other maps from `textures/` manually.

## Rebuilding

Requires Go 1.22+ with no external dependencies:

```
cd tools
go run ./cmd/texgen -out ../textures     # ~3 min, regenerates all PBR sets
go run ./cmd/build  -root ..             # geometry + GLB/glTF/OBJ/FBX export, prints triangle counts
go run ./cmd/render -w 1600 -h 900       # preview renders into ../renders
python3 fbxcheck.py ../export/fbx/SovietSchool.fbx   # structural FBX check
```

The renders come from a small software renderer: a rasteriser with PBR shading, shadow maps and SSAO. They are meant for checking shape and materials and are not final-quality beauty shots.
