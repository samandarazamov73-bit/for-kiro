# Sanatorium interior (c. 1975–85) inside the existing building, and the Godot game

The interior is built inside the existing exterior model (`export/SovietSchool.glb`), which is the only building in this repository. The exterior files are not modified.

The building is a Soviet sanatorium for elderly guests that has been left half abandoned: the furniture is still in place and the layout is intact, but dust, cobwebs and dead plants show that nobody has looked after it for a while, and some lamps are dead or flickering. The mood is mildly scary, not horror. The 1st floor holds reception, a phyto-bar, the treatment (spa) department, the medical department, dining and service rooms. Floors 2–4 are guest floors with rooms that each have their own bathroom.

The building is also a playable **Godot 4.7 game** (first-person electric wheelchair): see [`game/README.md`](game/README.md) and the in-game screenshots [`renders/game_overview.jpg`](renders/game_overview.jpg).

The Cycles renders in [`renders/interior_overview.jpg`](renders/interior_overview.jpg) were made before the half-abandoned pass (they show the clean lighting and the earlier furniture); the game screenshots show the current state.

**Triangles:** interior 147,488, exterior 42,040, combined scene 189,528 (budget 200k). Repeated modules (beds, chairs, doors, radiators, lamps...) are shared meshes, so glTF instancing keeps the files small.

## Deliverables

| Path | Content |
|---|---|
| `export/blend/SovietSanatorium.blend` | Blender 4.5 LTS scene: exterior + interior. Textures are linked relatively from `textures/`. Collections per floor, one empty per room with metadata. |
| `export/SovietSanatorium.glb` | glTF 2.0 binary, exterior + interior, textures embedded (JPEG), 518 point lights plus the sun, custom properties as `extras` (24.1 MB) |
| `export/SovietSanatorium_Interior.glb` | Interior only, same structure (14.4 MB) |
| `export/fbx/SovietSanatorium.fbx` | FBX, Y-up, textures referenced from `textures/` (7.2 MB) |
| `plans/plan_floor1..4.png` | Floor plans generated from the same data as the 3D model |
| `plans/rooms.csv` | Room schedule: floor, number, Russian/English name, department, area, windows, doors |
| `renders/interior/` | 24 Cycles renders of the main spaces; `renders/interior_overview.jpg` shows them all |
| `textures/T_*` (23 new sets) | Interior PBR sets and atlases (see below). The 10 exterior sets are unchanged. |
| `game/` | Godot 4.7 project: `assets/sanatorium.glb` (whole building without lights), `assets/level.json` (doors, lamps, switches, lift, colliders, critter areas), sounds, scripts, tests |
| `renders/game/`, `renders/game_overview.jpg` | Screenshots taken in the game |
| `tools/blender/` | Python source of the whole pipeline (plan data, validator, textures, geometry, furnishing, renders, game export, sound generator) |

The original `SovietSchool.*` files are untouched. The exterior inside the new files differs in two ways only. The window glass uses a clear glass material instead of the fake-room atlas, because real rooms are now behind it. The window frames are double-sided.

## Building facts used

All dimensions come from the Go generator (`tools/cmd/build`) and are reproduced in `tools/blender/sanatorium/params.py` and `exterior.py`:

- Main wing 75.0 × 16.2 m, 25 bays × 3.0 m, 4 floors at +1.20 / +4.50 / +7.80 / +11.10 (floor-to-floor 3.3 m), roof +14.60.
- Entrance block 12.0 × 19.5 m in front of bays 9–12, ground floor plus a double-height hall up to the roof at +11.60.
- Recessed glazed lobby with two double doors at x = 27.5, the entrance landing at +1.20, the ramp and stairs, and two rear steel exit doors at x = 4.5 and 70.5.
- Window positions for every facade. All 217 exterior windows open into a real room.
- Roof exits (stair houses) at x = 33 and x = 66. The stairs and the roof hatches sit under them.

## Structure

| Element | Value |
|---|---|
| Exterior walls | 0.35 m (interior face), window reveals with plaster lining and painted sills |
| Corridor | Central double-loaded corridor y 6.7–9.5, clear width 2.8 m (2.4 m at the pilasters), 0.2 m load-bearing walls |
| Frame | 0.4 × 0.4 m pilasters every 6 m on both corridor walls |
| Partitions | 0.12 m on the 3 m bay lines; most rooms are 2 bays (6 m) wide |
| Slabs / ceilings | 0.3 m slabs, clear height 3.0 m; club hall 6.7 m |
| Front rooms | y 0.35–6.5 (6.15 m deep), rear rooms y 9.7–15.85 |

## Floor programme

212 spaces in total: 161 rooms and 51 en-suite bathrooms, 237 doors and openings. Room numbers are on the door plates in the model and in `plans/rooms.csv`.

**Floor 1 (ground), 61 spaces, no guest bedrooms**
- *Entrance & reception (entrance block):* vestibule with a carpet runner, reception hall and waiting area (sofa group, armchairs, palms, «ДОБРО ПОЖАЛОВАТЬ!» banner), registration with two clerks behind the service windows, information desk, guard room, visitor coatroom, luggage storage with racks of suitcases and bags.
- *Phyto-bar and mineral water buvette* (50 m², south end of the entrance block): wooden bar counter with a samovar, shelves of herbal tea jars, a tiled buvette with three mineral water taps (Нарзан, Ессентуки № 17, Славяновская), five round cafe tables with four chairs each, palms and flowers.
- *Administration:* only two offices, the chief physician (padded door) and administration/accounts.
- *Spa (treatment) department, front east, 2-bay rooms of 34–36 m²:* massage room (two padded tables behind a curtain), physiotherapy (three curtained cubicles with couches and УВЧ devices), salt room and inhalatorium (salt-brick walls, six reclining chairs, three inhalation stations), hydrotherapy (two whirlpool baths, two showers with grab bars, Charcot shower console, rubber mats), therapeutic exercise hall (wall bars, large mirror, exercise bikes, mats, gym bench).
- *Medical (rear east):* medical registration and archive, general practitioner, examination room, consultation room, head nurse, treatment room, blood sampling, laboratory, first aid, medical equipment and supplies stores, medical staff changing room and restroom. Every doctor's room has a desk with a chair for the doctor and one for the guest; examination, GP, consultation, treatment and first aid rooms have an examination couch with a screen.
- *Dining & catering (west, own service corridor):* dining hall with eight tables in white cloths, four chairs each (32 seats, two sittings) and flowers on every table; kitchen, food preparation, distribution, dishwashing, dry and cold stores, staff changing room and restroom, staff dining room.
- *Technical:* electrical room, plumbing/heating substation, ventilation room, workshop, stores, janitor's room, linen rooms, waste room, lower elevator machine room. Public men's and women's restrooms are next to the reception hall.

**Floors 2–4 (guest floors), 50–51 spaces each**
- 51 guest rooms, 94 beds: 41 double rooms (29–31 m²), 8 single rooms (12–13 m²) and 2 assisted-care double rooms (29 m²). Every room has its own bathroom.
- *Double room:* two made beds with bedspreads, bedside tables with lamps, a nurse call button at the head of each bed, a radio point at 1.3 m, two pictures, a wardrobe with a suitcase on top, coat hooks, a sitting corner by the window (two armchairs, a small table with flowers, a floor lamp), a TV on a cabinet, a writing desk with a lamp and a chair, a large rug, a flower stand, curtains and tulle.
- *Single room:* made bed, bedside table with lamp, call button, radio, desk under the window, armchair, wardrobe, TV, rug.
- *Assisted-care room (floor 2, next to the elevator):* two care beds with side rails and a 1.1 m wheelchair passage between them, call buttons, a table with two chairs, TV, wide wardrobe, a parked wheelchair, no rugs; 1.1 m entrance door.
- *En-suite bathroom:* toilet with an L grab bar, washbasin with mirror and a vertical bar, shower with curtain, towel rail, bath mat. The accessible version (6.1 m², 0.9 m door) adds a level shower tray with a fold-down seat, a fold-down arm at the toilet and a call button.
- *Lounge on every floor (36 m²):* TV corner with a sofa, two armchairs and a coffee table on a rug, a floor lamp, two game tables with full chair sets (two of chess, checkers, dominoes and backgammon on each floor), bookcases, a palm, a wall newspaper and a seascape.
- *Club hall (floor 2, double height, 216 m²):* stage with curtain, piano, ten cinema rows; behind them a Russian billiards table with a cue rack, four game tables, two soft seating groups, bookcases, palms and flower stands.
- Floor 3: doctors' room and projection booth. Floor 4: library and reading room; ladders and hatches to the two roof exits.
- On every guest floor: nursing station open to the corridor (desk, phone, call indicator panel), nurse's office, treatment room, housekeeping room, linen rooms, an accessible bathroom (bathtub, toilet, shower with a stool, grab bars, call button), shared men's and women's WC and shower rooms.

## Corridors and accessibility

- Continuous wooden handrails at 0.9 m on both corridor walls of every floor. They stop only at doors, pilasters, open alcoves and wall equipment.
- Soft seating in the free wall bays: sofas with wall lamps and pictures above, pairs of armchairs with a small table, benches with flower stands. On the guest floors seats are never placed directly opposite each other, so the corridor keeps its clear width.
- Waiting seats outside the doctors' rooms on the ground floor; palms and flower stands at the stair and elevator lobbies.
- Public WCs: grab bars inside every cubicle next to the toilet, bars beside the washbasins, a wide accessible cubicle with bars on both sides and a call button. The shower rooms have shower cubicles with seats, a bench and coat hooks.
- Staff restrooms (catering and medical) have a toilet, washbasin with mirror, grab bar and towel rail.
- 1.0–1.3 m doors to the spa rooms, the first aid room and accessible bathrooms; turning space of at least 1.5 m in accessible rooms. The exterior ramp leads to the level reception hall and on to the elevator.

## Stairs and elevator

- **Three U-shaped staircases**, one module: 2 × 11 risers of 150 mm, 300 mm treads, 1.44 m flights, terrazzo treads, wooden handrails on both sides. Each storey landing has a flower stand; the end stairs also have a bench.
- **Passenger elevator, free to use (no key).** Concrete shaft 2.6 × 2.8 m with pit, guide rails, counterweight, ropes, overhead sheave and buffers; lower machine room with traction machine and controller.
  - Cabin 1.9 × 2.2 × 2.2 m clear, 1000 kg / 12 persons, wheelchair- or bed-sized. Laminate walls, handrails on three walls, fold-down seat, plafond, control panel with buttons 1–4, STOP, dispatcher call and door open.
  - The cabin waits at floor 1 **with the landing and cabin doors open**. On floors 2–4 the landing doors are closed.
  - Each landing has a steel portal with a 1.2 m two-leaf door, a mechanical floor indicator, a call button at 1.0 m, a «ЛИФТ — для отдыхающих и персонала» sign and the operating rules.
  - Properties on the cabin, shaft and landings: `locked: false`, `public: true`, `parked_level: 1`, `doors_open_level: 1`, `capacity_kg: 1000`, `capacity_persons: 12`.

## Doors

244 door leaves in 237 openings. Room doors are 2.3 m high; ordinary doors are 1.0 m wide, bathroom and small service doors 0.9 m (0.8 m in five narrow passages beside pilasters), double doors 1.5–1.6 m, so the wheelchair passes everywhere. The leaf fills the frame with 6 mm clearance, and a door stop strip on the jamb covers the gap; thresholds are flush with the floor. Types: wood, wood with glazing, wired-glass double doors (stairs, dining hall, lounges), steel (technical rooms), padded (chief physician), plus service counters, glazed partitions and projection ports. Every door sits in a frame with casings on both faces and a threshold. All leaves are modelled closed (the game opens some of them at start); the swing zone of every door is kept free of furniture. Door leaves are named `DoorLeaf_<door>_<leaf>` with the origin on the hinge. En-suite bathroom doors open into the bedroom. Door node `extras`: `door`, `open_angle_deg`, `hinge`, `opens_into`, `locked` (closed steel technical doors), `type`.

## Furnishing rules

Furniture is placed by recipes per room type (`tools/blender/sanatorium/furnish.py`) with these checks (`furnish_core.py`):

- Floor items must lie inside the room and must not overlap each other, door swing zones, radiators, pilasters or open sides of the room.
- Wall items (posters, pictures, schedules, calendars, evacuation plans, wall newspapers, warning signs, menus, switches, sockets, call buttons, grab bars...) must sit on a real wall, clear of openings and door plates, with at least 12 cm between neighbours. They never overlap or Z-fight. They are not hung behind tall furniture, and tall furniture is not placed in front of them.
- Items on top of furniture (lamps, phones, papers, vases, TVs, games, suitcases, samovar) are only placed if the piece below exists, and only inside its top.
- A table and its chairs are placed as one set: either the full set fits or none of it is placed.
- Radiators stand on the floor under every window of a heated room. In the club hall they stand on the hall floor (on the stage at the stage end); the upper hall windows have none. Dry and cold food stores have no radiator.
- `tools/blender/furnish_preview.py` runs all recipes without Blender, draws every footprint over the floor plans and lists the rejected placements.

About 3,400 items, 215 radiators, curtains and tulle in all furnished rooms. Chairs, tables, couches and stools have real legs (no flat alpha cards); armchairs, sofas and pillows have rounded cushions.

**Signs of neglect** (`mood()` in `furnish.py`, kept light): cobwebs in upper room corners (144), dust patches (127), dry leaves under the plants, which are almost dead (brown, drooping foliage in the textures), a few papers on office floors, small stains in wet rooms and corridors, 18 beds stripped to the mattress, chairs left slightly askew, and things left behind in the corridors (a wheelchair, a laundry cart, a cleaning cart, a stretcher).

## Lighting

- 526 ceiling fixtures: glass plafonds (guest rooms, corridors, offices, lounges, stairs), warm-white fluorescent battens (kitchen, medical, physiotherapy, exercise hall, registration), bulbs in stores and technical rooms, pendants in the club hall. `light_state`: 422 `on`, 29 `flicker`, 75 `broken` (dark glass, no light). Fixtures are named `Fix_<n>`, table lamps, floor lamps and sconces `Glow_<n>`.
- The pendant lamps no longer Z-fight: the glowing inner side of the shade sits 1 cm inside the outer shell.
- One point light per fixture, warm colour (2700–3200 K), spaced about 3 m apart so that no corner stays dark. Corridors have a plafond every 3 m.
- 64 extra warm lights from floor lamps and wall sconces. Table lamp shades glow.
- Afternoon sun and sky in the .blend.

## Materials and textures (new)

All textures are generated procedurally by `tools/blender/texgen_interior.py` and are tileable. They follow the existing convention: `_BaseColor`, `_Normal` (OpenGL, +Y), `_ORM` (R = AO, G = roughness, B = metallic), `_Roughness`, `_AO`, plus `_Metallic` for metal sets. Every set has a fine film-grain noise with sparse dust specks (`texcore.grain`), so surfaces look new but grimy. On top of that there is light wear: scuffs and dirt near the skirting, faint water marks under ceilings, worn linoleum paths, darker tile grout.

| Set | Use |
|---|---|
| T_Paint_WallGreen / Blue / Beige / Peach | Oil-painted dado (1.5 m) with a light upper wall and skirting, mapped to storey height so the dado line is always at 1.5 m |
| T_Tile_WallWhite | 150 mm glazed tiles to 1.5 m (bathrooms, kitchen, medical, hydrotherapy) |
| T_Wallpaper_Floral / Geometric | Soviet wallpapers (offices, guest rooms, lounges, library) |
| T_Salt_Brick | Salt blocks for the salt room |
| T_Plaster_White, T_Ceiling_Paint | Plaster and ceilings |
| T_Linoleum_Brown / Parquet | Red-brown linoleum and parquet-print linoleum |
| T_Tile_FloorCeramic, T_Terrazzo | 100 mm two-colour ceramic tiles; terrazzo with brass divider strips (reception, ground corridor, stairs) |
| T_Wood_DoorDark, T_Wood_Furniture | Varnished door wood; furniture wood |
| T_Metal_Painted, T_Metal_DarkSteel, T_Concrete_Interior, T_Glass_Clear | Painted metal, dark steel (lift shaft), shaft concrete, clear window glass (alpha) |
| T_Atlas_Furniture (4096 × 2048) | Fronts and details of all furniture and equipment: bedspreads, upholstery, chess/checkers/backgammon boards, dominoes, billiard cloth, suitcases, luggage shelves, physiotherapy and hydrotherapy panels, bar and buvette fronts, tea jars, tablecloth, medical curtains, call buttons and call panel, radio, wardrobes, bookcases, cabinets, fridge, elevator doors and panels, TV, piano, and colour swatches |
| T_Atlas_Decals (2048, alpha) | Tulle and curtains, health and leisure posters, paintings and a wide seascape, wall carpet, calendar, daily and treatment schedules, phyto-bar menu, plants (palm, geranium, ferns), chair legs and balusters, papers, all signs |
| T_Atlas_Signs (2048) | 152 door plates with room number and Russian name (wood-tone on guest floors, blue enamel elsewhere) |

## Custom properties (glTF `extras`)

- Room empties `Room_<number>_<Name>`: `room_id`, `number`, `name_ru`, `name_en`, `department`, `area_m2`, `kind`, `floor`, `floor_elevation_m`, `ceiling_elevation_m`.
- Floor empties `Floor1_Ground` … `Floor4`: `floor`, `floor_elevation_m`, `ceiling_elevation_m`, `clear_height_m`, `elevation_axis`. Elevations are heights above the model origin. They are Blender Z in the .blend and Y in the Y-up GLB/FBX exports.
- Doors and elevator: see above. Fixtures and lamps: `light_state`, `fixture`. Handrails: `handrail`, `height_m`. Stairs: `stair`, `risers_per_storey`, `riser_mm`, `tread_mm`, `flight_width_m`.

## Rebuilding

The pipeline runs with the Blender Python module (no Blender install needed) or inside Blender 4.5 LTS:

```
python -m venv .venv && .venv/bin/pip install bpy==4.5.4 pillow
cd tools/blender
../../.venv/bin/python texgen_interior.py                 # ~1 min, writes 23 texture sets into ../../textures
../../.venv/bin/python furnish_preview.py --out /tmp/furn  # optional: furniture plans without Blender
../../.venv/bin/python build_sanatorium.py                # ~20 s: validates the plan, builds, saves .blend, exports GLB/FBX, writes plans/
../../.venv/bin/python render_interior.py --blend ../../export/blend/SovietSanatorium.blend --out ../../renders/interior
# or: blender -b -P build_sanatorium.py
```

On a headless Linux machine the `bpy` wheel needs `libSM`, `libICE`, `libXt` and `libglvnd` (GL/GLX/OpenGL/EGL). Renders use Cycles on the CPU (32 samples, about 2.7 min per 1280 × 720 view on 8 cores).

Source layout (`tools/blender/sanatorium/`): `params.py` (dimensions), `exterior.py` (window list from the Go generator), `plan.py` (all rooms and doors as data), `layout.py` (wall/door/window resolution and validation: overlaps, unreachable rooms, windows without a room, doors without a shared wall), `drawplan.py`, `texgen_*.py`, `architecture.py`, `doors.py`, `stairs.py`, `elevator.py`, `furniture.py` (modules), `furnish_core.py` (placement and checks), `furnish.py` (room recipes), `lighting.py`.

## Limitations

- No lightmap UV set; generate one in the engine. Baked lighting is not included.
- Small detail (chair legs, balusters, bed rails, wheels, plants) uses alpha-tested quads from the shared atlases.
- In the GLB/FBX files the doors are closed and the elevator does not move; in the Godot game they work (`game/`). Lift door leaves are separate objects (`LiftDoor_F<n>_L/R`, `LiftCabDoor_L/R`).
- No separate reference image was provided, so the existing exterior model was used as the architectural reference.
