extends Node
## Automated checks (run: godot --headless --path . -- --test) and screenshots
## (run with a display: godot --path . -- --shots --out=/abs/dir). Exits with code 0 when all checks pass.
## FPS per graphics quality level, with a display: godot --path . -- --bench --out=/abs/dir

var game
var fails := 0
var passes := 0


func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	if "--shots" in args:
		_shots.call_deferred(args)
	elif "--bench" in args:
		_bench.call_deferred(args)
	else:
		_run.call_deferred()


func check(ok: bool, what: String) -> void:
	if ok:
		passes += 1
		print("TEST OK   ", what)
	else:
		fails += 1
		print("TEST FAIL ", what)


func wait(t: float) -> void:
	await get_tree().create_timer(t, true, true).timeout


func place(p: Vector3, yaw: float) -> void:
	var pl = game.player
	pl.global_position = p
	pl.rotation = Vector3(0, yaw, 0)
	pl.velocity = Vector3.ZERO
	pl.v = 0.0
	pl.w = 0.0
	pl.input_override = Vector2.ZERO
	pl.reset_physics_interpolation()


func drive(thr: float, steer: float, t: float) -> void:
	game.player.input_override = Vector2(thr, steer)
	await wait(t)
	game.player.input_override = Vector2.ZERO
	await wait(0.6)


func _run() -> void:
	var pl = game.player
	var lv: Array = game.level["levels"]
	await wait(1.0)
	print("stats: ", game.stats)
	check(game.stats.get("doors", 0) > 200, "doors created: %d" % game.stats.get("doors", 0))
	check(game.stats.get("lights", 0) > 300, "lights created: %d" % game.stats.get("lights", 0))
	check(game.stats.get("switches", 0) > 140, "switches created: %d" % game.stats.get("switches", 0))
	check(game.stats.get("rats", 0) >= 8 and game.stats.get("rats", 0) <= 12, "rats: %d" % game.stats.get("rats", 0))
	check(game.stats.get("roaches", 0) >= 20, "roaches: %d" % game.stats.get("roaches", 0))
	check(pl.is_on_floor() and abs(pl.global_position.y - float(lv[0])) < 0.1,
		"wheelchair stands on the hall floor (y=%.3f)" % pl.global_position.y)

	# --- driving ---------------------------------------------------------------------------
	var p0: Vector3 = pl.global_position
	await drive(1.0, 0.0, 2.5)
	var d: float = pl.global_position.distance_to(p0)
	check(d > 2.5 and d < 6.5, "drives forward at speed 3 (8.6 km/h): %.2f m in 2.5 s (+ braking)" % d)
	var y0: float = pl.rotation.y
	await drive(0.0, 1.0, 1.0)
	check(abs(angle_difference(y0, pl.rotation.y)) > 0.6, "turns on the spot: %.2f rad" % abs(angle_difference(y0, pl.rotation.y)))
	pl.speed_level = 4
	place(Vector3(45.0, float(lv[0]) + 0.02, -8.1), -PI / 2)     # ground corridor, facing east
	await wait(0.3)
	p0 = pl.global_position
	await drive(1.0, 0.0, 3.0)
	d = pl.global_position.distance_to(p0)
	check(d > 7.0, "full speed 14 km/h: %.2f m in 3 s" % d)

	# --- wall stops the chair ------------------------------------------------------------------
	place(Vector3(48.0, float(lv[0]) + 0.02, -8.1), 0.0)      # facing the pilaster on the rear corridor wall
	await wait(0.3)
	p0 = pl.global_position
	await drive(1.0, 0.0, 3.0)
	check(pl.global_position.distance_to(p0) < 1.0 and pl.global_position.z > -9.3,
		"a pilaster stops the chair (moved %.2f m, z=%.2f)" % [pl.global_position.distance_to(p0), pl.global_position.z])

	# --- doors -----------------------------------------------------------------------------
	var g = null
	for dg in game.door_groups:
		if not dg.locked and not dg.ext and dg.leaves.size() == 1 and dg.angle < 1.0 and abs(dg.center.y - float(lv[0]) - 1.15) < 0.4:
			g = dg
			break
	check(g != null, "found a closed door")
	if g:
		place(Vector3(5.0, float(lv[0]) + 0.02, -8.1), 0.0)    # away from the door
		g.interact(pl)
		await wait(1.6)
		check(g.angle > 90.0, "door opens (%.0f deg)" % g.angle)
		g.interact(pl)
		await wait(1.2)
		check(g.angle < 0.5, "door closes (%.1f deg)" % g.angle)
	var lockd = null
	for dg in game.door_groups:
		if dg.locked and not dg.ext:
			lockd = dg
			break
	check(lockd != null, "technical rooms are locked")
	if lockd:
		lockd.interact(pl)
		await wait(0.2)
		check(lockd.angle < 0.5, "locked door stays shut")

	# --- elevator: ride from floor 1 to floor 3 -------------------------------------------------
	var lift = game.lift
	place(Vector3(37.5, float(lv[0]) + 0.02, -8.2), PI)      # corridor in front of the lift, facing it
	await wait(0.4)
	check(lift.floor_idx == 0, "lift is parked on floor 1 (doors %s)" % lift.state)
	lift.request(0)                                           # press the call button
	await wait(2.0)
	check(lift.state == "open", "call button opens the lift doors")
	await drive(1.0, 0.0, 2.6)
	var inside: bool = lift.player_in_cabin()
	check(inside, "drives into the cabin (z=%.2f)" % pl.global_position.z)
	if not inside:
		place(Vector3(37.5, float(lv[0]) + 0.02, -5.15), PI)
		await wait(0.3)
	lift.request(2)
	var t: float = 0.0
	while t < 30.0 and not (lift.floor_idx == 2 and lift.state == "open"):
		await wait(0.25)
		t += 0.25
	check(lift.floor_idx == 2 and lift.state == "open", "lift arrives at floor 3 and opens (%.1f s)" % t)
	check(abs(pl.global_position.y - float(lv[2])) < 0.12, "chair rode with the cabin (y=%.3f, floor %.2f)" % [pl.global_position.y, float(lv[2])])
	var rope: MeshInstance3D = game.lift.ropes[0]["mesh"]
	var rope_bottom: float = rope.position.y - rope.scale.y * 0.5
	check(game.stats.get("lift_rope_tris_cut", 0) > 0 and absf(rope_bottom - (game.lift.roof0 + game.lift.y_off)) < 0.01,
		"hoist ropes start on the cabin roof, not inside it (%d baked triangles cut, rope from y=%.2f)" % [game.stats.get("lift_rope_tris_cut", 0), rope_bottom])
	place(pl.global_position, 0.0)
	await drive(1.0, 0.0, 3.0)
	check(pl.global_position.z < -6.9 and abs(pl.global_position.y - float(lv[2])) < 0.1,
		"drives out onto the floor-3 corridor (z=%.2f y=%.2f)" % [pl.global_position.z, pl.global_position.y])
	# call it back from floor 3 to floor 2 landing
	lift.request(1)
	t = 0.0
	while t < 30.0 and not (lift.floor_idx == 1 and lift.state == "open"):
		await wait(0.25)
		t += 0.25
	check(lift.floor_idx == 1, "lift can be called to another floor (%.1f s)" % t)

	# --- stairs are blocked for the wheelchair --------------------------------------------------
	var st: Dictionary = game.level["blockers"][1]
	var mn: Vector3 = game._v3(st["min"])
	var mx: Vector3 = game._v3(st["max"])
	var c: Vector3 = (mn + mx) * 0.5
	var nrm: Vector3 = Vector3(1, 0, 0) if (mx.x - mn.x) < (mx.z - mn.z) else Vector3(0, 0, 1)
	var probe: Vector3 = c - nrm * 1.2
	if game.room_at(probe + Vector3(0, 0.3, 0)).is_empty():
		probe = c + nrm * 1.2
		nrm = -nrm
	place(Vector3(probe.x, mn.y + 0.02, probe.z), atan2(-nrm.x, -nrm.z))
	await wait(0.3)
	await drive(1.0, 0.0, 2.5)
	check(abs(pl.global_position.y - mn.y) < 0.12, "stairs are not climbable (y=%.2f, landing %.2f)" % [pl.global_position.y, mn.y])
	# ground floor STAIR1: the invisible wall stands only in front of the first step; beside it the landing is
	# open floor up to the wall of the store room under the flight (x = 31.5), which is solid
	var space: PhysicsDirectSpaceState3D = game.get_world_3d().direct_space_state
	var y0f: float = float(lv[0]) + 0.5
	var at_steps: Dictionary = space.intersect_ray(PhysicsRayQueryParameters3D.create(Vector3(31.0, y0f, -6.0), Vector3(32.0, y0f, -6.0)))
	var on_floor: Dictionary = space.intersect_ray(PhysicsRayQueryParameters3D.create(Vector3(30.3, y0f, -4.0), Vector3(31.4, y0f, -4.0)))
	var store: Dictionary = space.intersect_ray(PhysicsRayQueryParameters3D.create(Vector3(31.0, y0f, -4.0), Vector3(32.0, y0f, -4.0)))
	check(not at_steps.is_empty() and on_floor.is_empty() and not store.is_empty(),
		"STAIR1 ground floor: blocked at the steps, landing free, store-room wall solid (%s / %s / %s)" % [
			not at_steps.is_empty(), not on_floor.is_empty(), not store.is_empty()])
	# turning on the spot against a wall never swings the footrest into it
	place(Vector3(48.0, float(lv[0]) + 0.02, -8.1), 0.0)
	await wait(0.3)
	await drive(1.0, 0.0, 1.5)
	await drive(0.0, 1.0, 1.5)
	check(not pl._overlaps(pl.global_transform), "turning against a wall: the chair stays out of it")

	# --- light switch ----------------------------------------------------------------------------
	var sw = null
	for ch in game.get_children():
		if ch.get_script() == game.Switch and game.lights.working_count(ch.room) > 0 and not game.lights.is_on(ch.room):
			sw = ch
			break
	check(sw != null, "found a switch of a dark room")
	if sw:
		sw.interact(pl)
		var lit: bool = false
		for l in game.lights.groups[sw.room]["lights"]:
			lit = lit or l.visible
		check(game.lights.is_on(sw.room) and lit, "switch turns the room light on (%s)" % sw.room)
		sw.interact(pl)
		check(not game.lights.is_on(sw.room), "and off again")

	# --- rats run away ---------------------------------------------------------------------------
	var rat: Dictionary = game.critters.rats[0]
	place(rat["node"].global_position + Vector3(1.0, 0.02, 0), 0.0)
	game.critters.scare(rat["node"].global_position, 3.0)
	await wait(0.2)
	check(rat["state"] in ["flee", "hidden"], "rat flees from the wheelchair (%s)" % rat["state"])

	print("RESULT: %d passed, %d failed" % [passes, fails])
	print("ALL TESTS PASSED" if fails == 0 else "TESTS FAILED")
	get_tree().quit(0 if fails == 0 else 1)


# ------------------------------------------------------------------------------- screenshots
# name: [eye position (Blender x, y, z), look-at (Blender x, y, z), rooms switched on]
const SHOTS := {
	"hall": [Vector3(32.6, -11.6, 2.4), Vector3(31.6, 0.0, 2.0), []],
	"corridor_floor2": [Vector3(4.2, 8.1, 5.7), Vector3(40.0, 8.3, 5.5), []],
	"corridor_ground": [Vector3(70.5, 8.1, 2.4), Vector3(40.0, 8.1, 2.2), []],
	"double_room": [Vector3(6.9, 3.5, 5.7), Vector3(11.6, 1.3, 5.2), ["L1.F2"]],
	"assisted_dark": [Vector3(39.7, 3.4, 5.7), Vector3(44.6, 1.5, 5.0), []],
	"lift": [Vector3(36.4, 9.0, 2.4), Vector3(37.6, 5.6, 2.2), []],
	"lift_cabin": [Vector3(37.5, 4.5, 2.4), Vector3(37.5, 8.0, 2.2), []],
	"club_hall": [Vector3(37.6, -1.2, 5.7), Vector3(31.0, -14.0, 5.6), ["L1.EB_HALL"]],
	"lounge": [Vector3(25.9, 10.2, 5.7), Vector3(22.0, 14.8, 5.2), ["L1.R7"]],
	"kitchen": [Vector3(7.6, 4.6, 2.4), Vector3(3.0, 1.2, 1.9), ["L0.F1"]],
	"phytobar": [Vector3(34.4, -12.6, 2.4), Vector3(28.6, -18.2, 2.0), ["L0.EB_BAR"]],
	"hydro": [Vector3(68.4, 5.7, 2.4), Vector3(64.2, 1.0, 1.8), ["L0.F21"]],
	"bathroom": [Vector3(41.05, 5.85, 5.7), Vector3(39.3, 4.1, 5.0), ["L1.F13b"]],
	"dining_dark": [Vector3(20.6, 5.8, 2.4), Vector3(13.0, 1.5, 1.9), []],
}


func _shots(args: Array) -> void:
	var out: String = "/tmp"
	var only := []
	for a in args:
		if String(a).begins_with("--out="):
			out = String(a).substr(6)
		elif String(a).begins_with("--only="):
			only = String(a).substr(7).split(",")
	var pl = game.player
	game.hud.room_label.visible = false
	for name in SHOTS:
		if only.size() > 0 and not (name in only):
			continue
		var s: Array = SHOTS[name]
		for room in s[2]:
			game.lights.set_room(room, true)
		var eye := Vector3(s[0].x, s[0].z, -s[0].y)
		var tgt := Vector3(s[1].x, s[1].z, -s[1].y)
		var dir := tgt - eye
		place(Vector3(eye.x, eye.y - pl.EYE, eye.z), atan2(-dir.x, -dir.z))
		pl.look_pitch = atan2(dir.y, Vector2(dir.x, dir.z).length())
		pl.look_yaw = 0.0
		await wait(1.5)
		for i in 4:
			await RenderingServer.frame_post_draw
		var img: Image = get_viewport().get_texture().get_image()
		img.save_png(out.path_join(name + ".png"))
		print("SHOT ", name)
		for room in s[2]:
			game.lights.set_room(room, false)
	get_tree().quit(0)


# ------------------------------------------------------------------------------- benchmark
const BENCH_SPOTS := ["hall", "corridor_floor2", "double_room", "club_hall"]


func _bench(args: Array) -> void:
	var out: String = "/tmp"
	var levels := [0, 1, 2]
	for a in args:
		if String(a).begins_with("--out="):
			out = String(a).substr(6)
		if String(a).begins_with("--quality="):      # only this level: 0 Low, 1 Medium, 2 High
			levels = [clampi(int(String(a).substr(10)), 0, 2)]
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	Engine.max_fps = 0
	game.hud.room_label.visible = false
	game.lights.set_room("L1.F2", true)
	game.lights.set_room("L1.EB_HALL", true)
	print("BENCH window %s, driver %s, GPU %s" % [str(get_window().size), RenderingServer.get_current_rendering_driver_name(),
		RenderingServer.get_video_adapter_name()])
	RenderingServer.viewport_set_measure_render_time(get_viewport().get_viewport_rid(), true)
	for q in levels:
		game.quality.level = q
		game.quality.apply()
		var line := "BENCH %-8s 3D scale %.2f:" % [game.quality.NAMES[q], get_viewport().scaling_3d_scale]
		var total := 0.0
		for name in BENCH_SPOTS:
			_look_from(name)
			await wait(2.0)
			var m: Array = await _measure(4.0)
			total += m[0]
			line += "  %s %s" % [name, _fmt(m)]
			if name == "hall":
				get_viewport().get_texture().get_image().save_png(out.path_join("bench_q%d_%s.png" % [q, name]))
		line += "  | average %.1f fps" % (total / BENCH_SPOTS.size())
		var md: Array = await _drive_measure()
		print(line + "  | driving %s, %.1f m" % [_fmt(md), md[4]])
	# what each effect costs on this GPU: Medium, with one thing changed at a time
	for i in FEATURES.size():
		_feature(i)
		_look_from("hall")
		await wait(2.0)
		var mh: Array = await _measure(3.0)
		var mdr: Array = await _drive_measure()
		print("BENCH effect %-28s hall %s | driving %s" % [FEATURES[i], _fmt(mh), _fmt(mdr)])
	print("BENCH numbers: fps (shadow draw calls per frame; GPU ms, CPU ms of rendering per frame)")
	get_tree().quit(0)


const FEATURES := ["Medium as is", "no volumetric fog", "no SSAO", "no glow", "moon shadow 4 splits (old Medium)",
	"moon shadow off", "lamp shadows off", "lamps not lighting the fog", "3D resolution x0.7"]


func _feature(i: int) -> void:
	game.quality.level = 1
	game.quality.apply()
	game.env.glow_enabled = true
	game.moon.shadow_enabled = true
	for e in game.lights.all_lights:
		e["light"].light_volumetric_fog_energy = 0.5
	match i:
		1: game.env.volumetric_fog_enabled = false
		2: game.env.ssao_enabled = false
		3: game.env.glow_enabled = false
		4:
			game.moon.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
			game.moon.directional_shadow_split_1 = 0.1
		5: game.moon.shadow_enabled = false
		6: game.lights.max_shadows = 0
		7:
			for e in game.lights.all_lights:
				e["light"].light_volumetric_fog_energy = 0.0
		8:
			var vp := get_viewport()
			vp.scaling_3d_mode = Viewport.SCALING_3D_MODE_FSR
			vp.scaling_3d_scale = vp.scaling_3d_scale * 0.7


func _look_from(name: String) -> void:
	var pl = game.player
	var s: Array = SHOTS[name]
	var eye := Vector3(s[0].x, s[0].z, -s[0].y)
	var tgt := Vector3(s[1].x, s[1].z, -s[1].y)
	var dir := tgt - eye
	place(Vector3(eye.x, eye.y - pl.EYE, eye.z), atan2(-dir.x, -dir.z))
	pl.look_pitch = atan2(dir.y, Vector2(dir.x, dir.z).length())
	pl.look_yaw = 0.0


## Driving down the lit ground-floor corridor: whatever moves with the chair (and the rats) can make
## the nearby lamps redraw their shadows, which standing still never shows. Appends the distance driven.
func _drive_measure() -> Array:
	var pl = game.player
	pl.speed_level = 4
	place(Vector3(45.0, float(game.level["levels"][0]) + 0.02, -8.1), -PI / 2)
	pl.look_pitch = 0.0
	pl.look_yaw = 0.0
	await wait(2.0)
	pl.input_override = Vector2(1.0, 0.0)
	await wait(0.5)
	var p1: Vector3 = pl.global_position
	var m: Array = await _measure(3.0)
	pl.input_override = Vector2.ZERO
	m.append(pl.global_position.distance_to(p1))
	return m


func _fmt(m: Array) -> String:
	return "%.1f (%d; %.1f, %.1f)" % [m[0], m[1], m[2], m[3]]


## Frames per second, draw calls per frame spent on shadows, and the GPU and CPU time of rendering
## per frame in ms, over t seconds.
func _measure(t: float) -> Array:
	var vp := get_viewport().get_viewport_rid()
	var frames := 0
	var shadow_draws := 0
	var gpu := 0.0
	var cpu := 0.0
	var elapsed := 0.0
	var t0 := Time.get_ticks_usec()
	while elapsed < t:
		await get_tree().process_frame
		elapsed += get_process_delta_time()
		frames += 1
		shadow_draws += RenderingServer.viewport_get_render_info(vp, RenderingServer.VIEWPORT_RENDER_INFO_TYPE_SHADOW,
			RenderingServer.VIEWPORT_RENDER_INFO_DRAW_CALLS_IN_FRAME)
		gpu += RenderingServer.viewport_get_measured_render_time_gpu(vp)
		cpu += RenderingServer.viewport_get_measured_render_time_cpu(vp)
	var n := maxi(frames, 1)
	return [frames / ((Time.get_ticks_usec() - t0) / 1e6), shadow_draws / n, gpu / n, cpu / n]
