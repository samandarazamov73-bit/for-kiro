extends Node3D
## Sanatorium: first-person electric wheelchair in a half-abandoned Soviet sanatorium.
## Loads the building (assets/sanatorium.glb, exported by tools/blender/build_sanatorium.py) and the
## level description (assets/level.json), then builds collisions, occluders, doors, lamps and switches,
## the elevator, rats and cockroaches, sound and the player.

const Wheelchair = preload("res://scripts/wheelchair.gd")
const DoorGroup = preload("res://scripts/door_group.gd")
const LightManager = preload("res://scripts/lights.gd")
const Lift = preload("res://scripts/lift.gd")
const Critters = preload("res://scripts/critters.gd")
const Ambience = preload("res://scripts/ambience.gd")
const Hud = preload("res://scripts/hud.gd")
const Switch = preload("res://scripts/switch.gd")
const Quality = preload("res://scripts/quality.gd")

const L_WORLD := 1
const L_PLAYER := 2
const L_DOORS := 4
const L_INTERACT := 8
const L_LIFT := 16

const COLLIDE_PREFIX := ["Shell_", "Pilasters_", "WindowReveals_", "WindowSills_", "OpeningLinings", "InteriorGlazing",
	"Stair1_Flights", "Stair2_Flights", "Stair3_Flights", "Lift_Landing", "Lift_Machine", "DoorFrame_"]

var level: Dictionary
var building: Node3D
var nodes := {}
var rooms := {}
var room_list := []
var player: CharacterBody3D
var hud: CanvasLayer
var lights: Node3D
var lift: Node3D
var critters: Node3D
var ambience: Node3D
var quality: Node
var env: Environment
var moon: DirectionalLight3D
var door_groups := []
var rng := RandomNumberGenerator.new()
var stats := {}


func _ready() -> void:
	rng.seed = 1975
	_setup_input()
	_fit_window_macos()
	_setup_audio_buses()
	level = JSON.parse_string(FileAccess.get_file_as_string("res://assets/level.json"))
	var t0 := Time.get_ticks_msec()
	building = (load("res://assets/sanatorium.glb") as PackedScene).instantiate()
	add_child(building)
	_index(building)
	for r in level["rooms"]:
		rooms[r["id"]] = r
		room_list.append(r)
	_setup_environment()
	_tune_materials()
	_build_static_colliders()
	_build_occluders_and_ranges()
	_build_furniture_colliders()
	_build_blockers()
	hud = Hud.new()
	add_child(hud)
	player = Wheelchair.new()
	player.game = self
	add_child(player)
	var sp: Dictionary = level["spawn"]
	player.global_position = _v3(sp["pos"]) + Vector3(0, 0.05, 0)
	player.rotation.y = float(sp["yaw"])
	_build_doors()
	lights = LightManager.new()
	add_child(lights)
	lights.setup(self)
	_build_switches()
	lift = Lift.new()
	add_child(lift)
	lift.setup(self)
	critters = Critters.new()
	add_child(critters)
	critters.setup(self)
	ambience = Ambience.new()
	add_child(ambience)
	ambience.setup(self)
	quality = Quality.new()
	add_child(quality)
	quality.setup(self)
	stats["load_ms"] = Time.get_ticks_msec() - t0
	print("Sanatorium loaded in %d ms: %s" % [stats["load_ms"], str(stats)])
	var args := OS.get_cmdline_user_args()
	if "--test" in args or "--shots" in args:
		var tr: Node = load("res://tests/test_runner.gd").new()
		tr.game = self
		add_child(tr)
	else:
		hud.show_intro()


# ------------------------------------------------------------------------------ helpers
func _v3(a) -> Vector3:
	return Vector3(float(a[0]), float(a[1]), float(a[2]))


func _index(n: Node) -> void:
	nodes[String(n.name)] = n
	for c in n.get_children():
		_index(c)


func node(name: String) -> Node:
	return nodes.get(name)


## Room containing world point p (the smallest one when spaces overlap in height).
func room_at(p: Vector3) -> Dictionary:
	var best := {}
	for r in room_list:
		if p.y < float(r["floor_y"]) - 0.3 or p.y > float(r["ceil_y"]) + 0.1:
			continue
		for q in r["rects"]:
			if p.x >= q[0] and p.x <= q[1] and p.z >= q[2] and p.z <= q[3]:
				if best.is_empty() or (float(r["ceil_y"]) - float(r["floor_y"])) < (float(best["ceil_y"]) - float(best["floor_y"])):
					best = r
	return best


func play_at(stream_name: String, pos: Vector3, vol_db := 0.0, pitch := 1.0, max_dist := 25.0) -> void:
	var p := AudioStreamPlayer3D.new()
	p.stream = sfx(stream_name)
	p.volume_db = vol_db
	p.pitch_scale = pitch
	p.max_distance = max_dist
	p.unit_size = 3.0
	p.bus = "World"
	add_child(p)
	p.global_position = pos
	p.finished.connect(p.queue_free)
	p.play()


var _sfx_cache := {}


func sfx(name: String, loop := false) -> AudioStream:
	var key := name + ("#l" if loop else "")
	if _sfx_cache.has(key):
		return _sfx_cache[key]
	var s: AudioStreamWAV = load("res://assets/sfx/%s.wav" % name)
	if loop:
		s = s.duplicate()
		s.loop_mode = AudioStreamWAV.LOOP_FORWARD
		s.loop_begin = 0
		s.loop_end = int(s.get_length() * s.mix_rate)
	_sfx_cache[key] = s
	return s


# ------------------------------------------------------------------------------ setup
func _setup_input() -> void:
	var keys := {
		"drive_forward": [KEY_W, KEY_UP], "drive_back": [KEY_S, KEY_DOWN], "turn_left": [KEY_A, KEY_LEFT],
		"turn_right": [KEY_D, KEY_RIGHT], "interact": [KEY_E, KEY_F], "horn": [KEY_H],
		"speed_up": [KEY_EQUAL, KEY_KP_ADD, KEY_R], "speed_down": [KEY_MINUS, KEY_KP_SUBTRACT, KEY_Q],
		"pause": [KEY_ESCAPE], "fullscreen": [KEY_F11], "quality": [KEY_G, KEY_F2],
	}
	for a in keys:
		if not InputMap.has_action(a):
			InputMap.add_action(a, 0.2)
		for k in keys[a]:
			var ev := InputEventKey.new()
			ev.physical_keycode = k
			InputMap.action_add_event(a, ev)
	# Mac: Ctrl+Cmd+F is the system full-screen shortcut (F11 there shows the desktop)
	var mac_fs := InputEventKey.new()
	mac_fs.physical_keycode = KEY_F
	mac_fs.ctrl_pressed = true
	mac_fs.meta_pressed = true
	InputMap.action_add_event("fullscreen", mac_fs)
	var joy := {"interact": JOY_BUTTON_A, "horn": JOY_BUTTON_Y, "speed_up": JOY_BUTTON_RIGHT_SHOULDER,
		"speed_down": JOY_BUTTON_LEFT_SHOULDER, "pause": JOY_BUTTON_START}
	for a in joy:
		var jb := InputEventJoypadButton.new()
		jb.button_index = joy[a]
		InputMap.action_add_event(a, jb)
	for pair in [["drive_forward", JOY_AXIS_LEFT_Y, -1.0], ["drive_back", JOY_AXIS_LEFT_Y, 1.0],
			["turn_left", JOY_AXIS_LEFT_X, -1.0], ["turn_right", JOY_AXIS_LEFT_X, 1.0]]:
		var jm := InputEventJoypadMotion.new()
		jm.axis = pair[1]
		jm.axis_value = pair[2]
		InputMap.action_add_event(pair[0], jm)
	var wheel_up := InputEventMouseButton.new()
	wheel_up.button_index = MOUSE_BUTTON_WHEEL_UP
	InputMap.action_add_event("speed_up", wheel_up)
	var wheel_dn := InputEventMouseButton.new()
	wheel_dn.button_index = MOUSE_BUTTON_WHEEL_DOWN
	InputMap.action_add_event("speed_down", wheel_dn)
	var lmb := InputEventMouseButton.new()
	lmb.button_index = MOUSE_BUTTON_LEFT
	InputMap.action_add_event("interact", lmb)


func _setup_audio_buses() -> void:
	if AudioServer.get_bus_index("World") >= 0:
		return
	AudioServer.add_bus()
	var i := AudioServer.bus_count - 1
	AudioServer.set_bus_name(i, "World")
	AudioServer.set_bus_send(i, "Master")
	var rv := AudioEffectReverb.new()
	rv.room_size = 0.55
	rv.damping = 0.45
	rv.wet = 0.22
	rv.dry = 0.9
	rv.predelay_msec = 28.0
	AudioServer.add_bus_effect(i, rv)


func _setup_environment() -> void:
	env = Environment.new()
	var sky := Sky.new()
	var sm := ProceduralSkyMaterial.new()
	sm.sky_top_color = Color(0.02, 0.03, 0.06)
	sm.sky_horizon_color = Color(0.07, 0.08, 0.11)
	sm.ground_bottom_color = Color(0.01, 0.01, 0.012)
	sm.ground_horizon_color = Color(0.05, 0.05, 0.06)
	sm.sun_angle_max = 1.0
	sky.sky_material = sm
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.32, 0.34, 0.4)
	env.ambient_light_energy = 0.15
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_exposure = 1.15
	env.ssao_enabled = true
	env.ssao_radius = 1.2
	env.ssao_intensity = 2.2
	env.ssil_enabled = true
	env.ssil_intensity = 0.8
	env.glow_enabled = true
	env.glow_intensity = 0.5
	env.glow_bloom = 0.05
	env.glow_hdr_threshold = 1.2
	env.volumetric_fog_enabled = true
	env.volumetric_fog_density = 0.012
	env.volumetric_fog_albedo = Color(0.82, 0.8, 0.76)
	env.volumetric_fog_emission = Color(0, 0, 0)
	env.volumetric_fog_length = 40.0
	env.volumetric_fog_ambient_inject = 0.0
	env.adjustment_enabled = true
	env.adjustment_saturation = 0.82
	env.adjustment_contrast = 1.06
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	moon = DirectionalLight3D.new()
	moon.light_color = Color(0.55, 0.62, 0.8)
	moon.light_energy = 0.35
	moon.shadow_enabled = true
	moon.directional_shadow_max_distance = 40.0
	moon.light_volumetric_fog_energy = 0.4
	moon.rotation_degrees = Vector3(-32, -150, 0)
	add_child(moon)


## Indoors there is no sky to reflect, so fully metallic atlas regions would render black: tone metal down.
func _tune_materials() -> void:
	var seen := {}
	for key in nodes:
		var mi = nodes[key]
		if not (mi is MeshInstance3D) or mi.mesh == null:
			continue
		for i in mi.mesh.get_surface_count():
			var m = mi.mesh.surface_get_material(i)
			if m == null or seen.has(m) or not (m is BaseMaterial3D):
				continue
			seen[m] = true
			var nm: String = m.resource_name
			if nm in ["M_Atlas_Furniture", "M_Metal_Painted", "M_Metal_DarkSteel"]:
				m.metallic = 0.35
				m.metallic_specular = 0.5
	stats["materials"] = seen.size()


func _build_static_colliders() -> void:
	var n := 0
	var ext: Node = node("SovietSchool_1970s")
	var targets := []
	for key in nodes:
		var nd = nodes[key]
		if not (nd is MeshInstance3D):
			continue
		for p in COLLIDE_PREFIX:
			if String(key).begins_with(p):
				targets.append(nd)
				break
	if ext:
		var stack := [ext]
		while stack.size() > 0:
			var e: Node = stack.pop_back()
			if e is MeshInstance3D:
				targets.append(e)
			stack.append_array(e.get_children())
	for mi in targets:
		if mi.mesh == null:
			continue
		var body := StaticBody3D.new()
		body.collision_layer = L_WORLD
		body.collision_mask = 0
		var cs := CollisionShape3D.new()
		cs.shape = mi.mesh.create_trimesh_shape()
		body.add_child(cs)
		mi.add_child(body)
		n += 1
	stats["trimesh_colliders"] = n


func _build_occluders_and_ranges() -> void:
	var occ := 0
	var ranged := 0
	for key in nodes:
		var mi = nodes[key]
		if not (mi is MeshInstance3D) or mi.mesh == null:
			continue
		var sk := String(key)
		if sk.begins_with("Shell_"):
			var verts := PackedVector3Array()
			var idx := PackedInt32Array()
			for s in mi.mesh.get_surface_count():
				var arr: Array = mi.mesh.surface_get_arrays(s)
				var base := verts.size()
				verts.append_array(arr[Mesh.ARRAY_VERTEX])
				var ii: PackedInt32Array = arr[Mesh.ARRAY_INDEX]
				for k in ii:
					idx.append(base + k)
			var ao := ArrayOccluder3D.new()
			ao.set_arrays(verts, idx)
			var oi := OccluderInstance3D.new()
			oi.occluder = ao
			mi.add_child(oi)
			occ += 1
			continue
		if sk.begins_with(("Fix_")) or sk.begins_with("Shell") or sk.begins_with("Stair") or sk.begins_with("Lift"):
			continue
		var aabb: AABB = mi.get_aabb()
		var sz: float = aabb.size.length()
		if sz < 0.45:
			mi.visibility_range_end = 12.0
			mi.visibility_range_end_margin = 2.0
			ranged += 1
		elif sz < 2.6 and aabb.position.length() < 6.0:
			mi.visibility_range_end = 32.0
			mi.visibility_range_end_margin = 3.0
			ranged += 1
	stats["occluders"] = occ
	stats["ranged_meshes"] = ranged


func _box_shape(body: Node3D, mn: Vector3, mx: Vector3) -> CollisionShape3D:
	var a: Vector3 = mn.min(mx)
	var b: Vector3 = mn.max(mx)
	var cs := CollisionShape3D.new()
	var bs := BoxShape3D.new()
	bs.size = (b - a).max(Vector3(0.02, 0.02, 0.02))
	cs.shape = bs
	cs.position = (a + b) * 0.5
	body.add_child(cs)
	return cs


func _build_furniture_colliders() -> void:
	var body := StaticBody3D.new()
	body.name = "FurnitureColliders"
	body.collision_layer = L_WORLD
	body.collision_mask = 0
	add_child(body)
	for b in level["boxes"]:
		_box_shape(body, _v3(b["min"]), _v3(b["max"]))
	for b in level["rot_boxes"]:
		var cs := CollisionShape3D.new()
		var bs := BoxShape3D.new()
		bs.size = _v3(b["size"])
		cs.shape = bs
		cs.position = _v3(b["center"])
		cs.rotation.y = float(b["yaw"])
		body.add_child(cs)
	stats["furniture_boxes"] = body.get_child_count()


func _build_blockers() -> void:
	var body := StaticBody3D.new()
	body.name = "StairBlockers"
	body.collision_layer = L_WORLD
	add_child(body)
	for b in level["blockers"]:
		_box_shape(body, _v3(b["min"]), _v3(b["max"]))
	stats["stair_blockers"] = body.get_child_count()


func _build_doors() -> void:
	var holder := Node3D.new()
	holder.name = "Doors"
	add_child(holder)
	var groups := {}
	for d in level["doors"]:
		var g = groups.get(d["group"])
		if g == null:
			g = DoorGroup.new()
			g.game = self
			holder.add_child(g)
			groups[d["group"]] = g
			door_groups.append(g)
		g.add_leaf(d, node(d["name"]))
	var opened := 0
	for g in door_groups:
		g.finish_setup()
		# the building is half abandoned: some doors were left ajar
		if not g.locked and not g.ext and rng.randf() < 0.14:
			g.set_angle(rng.randf_range(12.0, 75.0))
			opened += 1
	stats["doors"] = door_groups.size()
	stats["doors_ajar"] = opened


func _build_switches() -> void:
	var n := 0
	for s in level["switches"]:
		var sw = Switch.new()
		sw.game = self
		sw.room = s["room"]
		add_child(sw)
		sw.global_position = _v3(s["pos"])
		n += 1
	stats["switches"] = n


## On a Retina Mac the 1280x720 window from project.godot opens at half size: make it about
## 80 % of the screen instead (the UI scales with it, see window/stretch in project.godot).
func _fit_window_macos() -> void:
	if not OS.has_feature("macos") or DisplayServer.get_name() == "headless":
		return
	var w := get_window()
	if w.mode != Window.MODE_WINDOWED:
		return
	var area: Rect2i = DisplayServer.screen_get_usable_rect(w.current_screen)
	var width := int(min(area.size.x * 0.8, area.size.y * 0.8 * 16.0 / 9.0))
	w.size = Vector2i(width, int(width * 9.0 / 16.0))
	w.position = area.position + (area.size - w.size) / 2


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("quality") and quality:
		quality.cycle()
		return
	if event.is_action_pressed("fullscreen"):
		var w := get_window()
		w.mode = Window.MODE_WINDOWED if w.mode == Window.MODE_FULLSCREEN else Window.MODE_FULLSCREEN
