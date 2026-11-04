# Sanatorium interior (c. 1975) inside the existing building

The interior is built inside the existing exterior model (`export/SovietSchool.glb`), which is the only building in this repository. The exterior files are not modified. The new files contain the exterior plus a complete, explorable interior: 4 floors, 209 rooms, 234 doors and openings, 3 staircases and a key-locked service elevator. Every one of the 217 exterior windows opens into a real room.

The 1st floor holds reception, administration, the medical department, dining/catering and technical rooms, and has **no patient bedrooms**. Floors 2–4 are patient accommodation with nursing support rooms.

**Triangles:** interior 63,639, exterior 42,040, combined scene ≈ 105,700. Repeated modules (doors, beds, radiators, fixtures...) are shared meshes, so glTF instancing keeps the files small.

## Deliverables

| Path | Content |
|---|---|
| `export/blend/SovietSanatorium.blend` | Blender 4.5 LTS scene: exterior + interior. Textures are linked relatively from `textures/`. Collections per floor, one empty per room with metadata. |
| `export/SovietSanatorium.glb` | glTF 2.0 binary, exterior + interior, textures embedded (JPEG), 279 punctual lights, custom properties as `extras` (19 MB) |
| `export/SovietSanatorium_Interior.glb` | Interior only, same structure (9.5 MB) |
| `export/fbx/SovietSanatorium.fbx` | FBX, Y-up, textures referenced from `textures/` |
| `plans/plan_floor1..4.png` | Floor plans generated from the same data as the 3D model |
| `plans/rooms.csv` | Room schedule: floor, number, Russian/English name, department, area, windows, doors |
| `renders/interior/` | Cycles renders of the main spaces |
| `textures/T_*` (22 new sets) | Interior PBR sets and atlases (see below). The 10 exterior sets are unchanged. |
| `tools/blender/` | Python source of the whole interior pipeline (plan data, validator, textures, geometry, renders) |

The original `SovietSchool.*` files are untouched. The exterior inside the new files differs in two ways only. The window glass uses a see-through dusty glass material instead of the fake-room atlas, because real rooms are now behind it. The window frames are double-sided.

## Building facts used

All dimensions come from the Go generator (`tools/cmd/build`) and are reproduced in `tools/blender/sanatorium/params.py` and `exterior.py`:

- Main wing 75.0 × 16.2 m, 25 bays × 3.0 m, 4 floors at +1.20 / +4.50 / +7.80 / +11.10 (floor-to-floor 3.3 m), roof +14.60.
- Entrance block 12.0 × 19.5 m in front of bays 9–12, ground floor plus a double-height hall up to the roof at +11.60. Together with the main wing it forms the L/T-shaped plan of the reference.
- Recessed glazed lobby with two double doors at x = 27.5, the entrance landing at +1.20, the ramp and stairs, and two rear steel exit doors at x = 4.5 and 70.5.
- Window positions for every facade, including the hall windows and the end-wall corridor windows.
- Roof exits (stair houses) at x = 33 and x = 66 and the ventilation chamber at x = 41. The stairs and the roof hatches sit under them.

## Structure

| Element | Value |
|---|---|
| Exterior walls | 0.35 m (interior face), window reveals with plaster lining and painted sills |
| Corridor | Central double-loaded corridor y 6.7–9.5, clear width 2.8 m (2.4 m at the pilasters), 0.2 m load-bearing walls |
| Frame | 0.4 × 0.4 m pilasters every 6 m on both corridor walls |
| Partitions | 0.12 m on the 3 m bay lines; rooms are 1, 2 or 3 bays wide |
| Slabs / ceilings | 0.3 m slabs, clear height 3.0 m; club hall 6.7 m |
| Front rooms | y 0.35–6.5 (6.15 m deep), rear rooms y 9.7–15.85 |

## Floor programme

Room numbers are on the door plates in the model and in `plans/rooms.csv`.

**Floor 1 (ground), 66 spaces**
- *Entrance & reception (entrance block):* entrance vestibule with glazed double doors, reception hall, registration office with service windows and counter, receptionist workspace, information desk, security/guard room, visitor coatroom (counter), luggage storage (counter), waiting area. Public men's and women's restrooms and cleaning equipment storage are on the main corridor next to the hall.
- *Administration (front, east):* secretary, director (padded door from the secretary), deputy director, chief administrator, accountant, HR, general administration, staff meeting room, head nurse, staff room, document archive, records storage.
- *Medical (rear, east):* medical registration and medical archive, general practitioner, examination room, consultation room, nurse's office, treatment/injection room, blood sampling, small laboratory, first aid room, medical equipment storage, medical supplies storage, medical staff changing room and restroom.
- *Dining & catering (west, separate service corridor closed by double doors):* dining hall (3 bays), food distribution counter with serving line, kitchen (hot shop), food preparation, vegetable preparation, dishwashing, dry food storage, refrigerated storage, kitchen staff changing room and restroom, staff dining room.
- *Technical & service:* electrical distribution room, water/plumbing and heating substation, ventilation room, maintenance workshop, general storage, janitor's room, clean linen, dirty linen, staff changing room, utility room, waste collection room, lower elevator machine room.

**Floors 2–4 (patient accommodation), 47–49 spaces each**
- 27 single and 63 double patient bedrooms in total. Each has beds, bedside tables, a wardrobe, a small desk or table, chairs, a lamp, a sink, curtains, a radiator and a picture.
- Floor 2: two assisted-care rooms with hospital beds, a wheelchair, an IV stand, 1.1 m doors and en-suite accessible bathrooms, next to the elevator. A doctor-on-duty room. The **club hall / patient lounge** (double height) with stage, curtain, cinema rows, piano, TV corner and chess tables, plus its foyer and storeroom.
- Floor 3: projection booth for the club hall, patient relaxation lounge (TV, sofa, books).
- Floor 4: patient relaxation lounge; steel ladders and hatches to the two roof exits.
- Every upper floor has a nursing station open to the corridor, a nurse's office, a treatment room, a housekeeping room, clean linen storage, dirty linen collection, an accessible bathroom (WC, bath, shower, grab bars), shared men's and women's bathrooms with WCs and showers, a staff office or medical storage, a utility room, and benches with plants in the stair lobbies.

## Stairs, elevator and accessibility

- **Three U-shaped staircases**, one module: 2 × 11 risers of 150 mm, 300 mm treads, 1.44 m flights, mid-landings and floor landings, terrazzo treads, painted walls. Wooden handrails at 0.9 m on steel balusters on the well side and a wall handrail on the other side. The main stair (bays 10–11, off the reception hall) is lit by the front windows. The west and east stairs (rear bays 1–2 and 22–23) lead to the existing rear exit doors.
- **Service elevator (key-operated)**: concrete shaft 2.6 × 2.8 m (x 36.2–38.8, y 3.7–6.5) with a pit and headroom, guide rails, counterweight, ropes, overhead sheave, buffers, and a lower machine room with traction machine and controller.
  - Cabin 1.9 × 2.2 × 2.2 m clear, wheelchair-sized, with laminate walls, handrail, plafond and control panel (buttons 1–4, STOP, CALL, key switch). It is parked on floor 1 with all doors **closed**.
  - Each landing has a steel portal, a 1.1 m two-leaf door, a semicircular mechanical floor indicator, a call panel with a key switch and keyhole, and signs: «ЛИФТ СЛУЖЕБНЫЙ», «ТОЛЬКО ПО КЛЮЧУ», «Посторонним вход воспрещён», operating rules.
  - The cabin, shaft and landing objects carry `locked: true`, `requires_key: "KEY_LIFT_SERVICE_01"`, `doors_closed: true`, `parked_level: 1`. The game must implement the key check; the model only provides the geometry and these flags.
- **Accessibility:** 2.8 m corridors kept clear (equipment is wall-mounted; benches stand only in pilaster bays), 1.0–1.1 m doors to assisted rooms, the first aid room and accessible bathrooms, an accessible WC in every shared bathroom, grab bars, and turning space of at least 1.5 m in the accessible rooms. The exterior ramp leads to the level reception hall and on to the elevator.

## Doors

There are 239 door leaves. Types: wood, wood with glazing, wired-glass double doors (stairs, dining hall, club hall), steel (technical, archives), padded (director), plus service counters, glazed partitions and projection ports. Every door sits in a frame with casings on both faces and a threshold. 58 leaves are left ajar at varied angles; the rest are closed. Locations are validated: each door connects two rooms through a shared wall, does not hit a pilaster, and has a clear swing zone (furniture placement checks against it). Door node `extras`: `door`, `open_angle_deg`, `hinge`, `opens_into`, `locked` (closed steel doors), `type`.

## Lighting and atmosphere

- 365 ceiling fixtures: fluorescent battens (offices, medical, kitchen, corridors), glass plafonds (patient rooms, bathrooms, stairs), bare bulbs (stores, technical rooms), pendants (club hall). Each has `light_state` = `on`, `flicker` or `broken`; the share of broken fixtures is higher in patient and technical areas. Reception and offices are brighter, corridors are dimmer.
- 279 point lights for the working fixtures. Flickering ones have `flicker: true` and a looping energy keyframe stutter in the .blend; the keyframes are not exported, so engines should drive flicker from the property.
- Weak overcast daylight (sun + sky) in the .blend.
- Neglect is shown with textures and decals, without structural damage: ceiling water stains, hairline cracks, chipped paint, worn linoleum paths, dust on furniture, scattered papers in offices and the dining hall, some tipped chairs, a cleaning cart left in a corridor, empty medicine shelves, faded posters, a 1991 calendar, stopped clocks.

## Materials and textures (new)

All textures are generated procedurally by `tools/blender/texgen_interior.py` and are tileable. They follow the existing convention: `_BaseColor`, `_Normal` (OpenGL, +Y), `_ORM` (R = AO, G = roughness, B = metallic), `_Roughness`, `_AO`, plus `_Metallic` for metal sets.

| Set | Use |
|---|---|
| T_Paint_WallGreen / Blue / Beige / Peach | Oil-painted dado (1.5 m) with whitewashed upper wall and skirting: faded, chipped, scuffed, cracked, water-stained below the ceiling. The texture is mapped to storey height so the dado line is always at 1.5 m. |
| T_Tile_WallWhite | 150 mm glazed tiles to 1.5 m with replaced, cracked and missing tiles (kitchen, WCs, medical) |
| T_Wallpaper_Floral / Geometric | Soviet wallpapers with roll seams, lifted edges, sun fading, stains (offices, patient rooms) |
| T_Plaster_AgedWhite, T_Ceiling_Paint | Aged plaster; ceilings with brush marks, flaking, water rings, mould spots |
| T_Linoleum_WornBrown / Parquet | Worn red-brown linoleum and parquet-print linoleum with seams, wear paths and scratches |
| T_Tile_FloorCeramic, T_Terrazzo_Old | 100 mm two-colour ceramic tiles; terrazzo with brass divider strips (reception, corridor, stairs) |
| T_Wood_DoorDark, T_Wood_Furniture | Varnished dark door wood with worn handle zone and kick marks; furniture wood |
| T_Metal_Painted, T_Metal_Rusty, T_Concrete_Interior, T_Glass_Dusty | Painted and rusty metal, shaft concrete, dusty and streaked window glass (alpha) |
| T_Atlas_Furniture (4096 × 2048) | Fronts and details of all furniture and equipment: wardrobes, bookcases, filing and medicine cabinets, ZIL fridge, electrical panels, fire hose cabinet, elevator doors and panels, floor indicator, radiators, stoves, typewriter, TV, piano, textiles, and flat colour swatches |
| T_Atlas_Decals (2048, alpha) | Tulle and curtains, health posters, eye chart, notice board, evacuation plan, paintings, wall carpet, calendar, schedules, plants, chair legs and balusters, papers, stains, all signs (exit, fire extinguisher, WC, lift, directions) |
| T_Atlas_Signs (2048) | 198 door plates with room number and Russian name |

## Custom properties (glTF `extras`)

- Room empties `Room_<number>_<Name>`: `room_id`, `number`, `name_ru`, `name_en`, `department`, `area_m2`, `kind`.
- Floor empties `Floor1_Ground` … `Floor4`: `level_z`.
- Doors: see above. Elevator: see above. Fixtures: `light_state`, `fixture`. Stairs: `stair`, `risers_per_storey`, `riser_mm`, `tread_mm`, `flight_width_m`.

## Rebuilding

The pipeline runs with the Blender Python module (no Blender install needed) or inside Blender 4.5 LTS:

```
python -m venv .venv && .venv/bin/pip install bpy==4.5.4 pillow
cd tools/blender
../../.venv/bin/python texgen_interior.py                 # ~1 min, writes 22 texture sets into ../../textures
../../.venv/bin/python build_sanatorium.py                # ~20 s: validates the plan, builds, saves .blend, exports GLB/FBX, writes plans/
../../.venv/bin/python render_interior.py --blend ../../export/blend/SovietSanatorium.blend --out ../../renders/interior
# or: blender -b -P build_sanatorium.py
```

On a headless Linux machine the `bpy` wheel needs `libSM`, `libICE`, `libXt` and `libglvnd` (GL/GLX/OpenGL/EGL). Renders use Cycles on the CPU.

Source layout (`tools/blender/sanatorium/`): `params.py` (dimensions), `exterior.py` (window list from the Go generator), `plan.py` (all rooms and doors as data), `layout.py` (wall/door/window resolution and validation: overlaps, unreachable rooms, windows without a room, doors without a shared wall), `drawplan.py`, `texgen_*.py`, `architecture.py`, `doors.py`, `stairs.py`, `elevator.py`, `furniture.py`, `furnish*.py`, `lighting.py`.

## Limitations

- No lightmap UV set; generate one in the engine. Baked lighting is not included.
- Wall decals and furniture use the shared atlases; small detail (chair legs, balusters, bed rails, wheels) is alpha-tested quads.
- The elevator lock and the flicker of lamps are data flags; logic belongs to the engine.
- No separate reference image was provided, so the existing exterior model was used as the architectural reference.
