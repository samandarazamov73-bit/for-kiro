extends Node
## Automated checks, screenshots and benchmark.
##   godot --path . -- --test                      checks (exit code 0 = all passed)
##   godot --path . -- --shots --out=<dir>         screenshots from fixed viewpoints
##   godot --path . -- --bench --out=<dir>         drives the autopilot round the loop and records frame times

var world: ForestWorld
var out_dir := "user://shots"
var failures: Array[String] = []
var passes := 0


func run(w: ForestWorld, args: PackedStringArray) -> void:
	world = w
	for a in args:
		if a.begins_with("--out="):
			out_dir = a.get_slice("=", 1)
	DirAccess.make_dir_recursive_absolute(out_dir)
	if "--test" in args:
		await run_tests()
	if "--shots" in args:
		await run_shots(args)
	if "--bench" in args:
		await run_bench()
	get_tree().quit(1 if failures.size() > 0 else 0)


# ------------------------------------------------------------------ helpers
func frames(n: int) -> void:
	for i in n:
		await get_tree().process_frame


func settle(n := 6) -> void:
	world._update_globals()
	world.terrain.update_lods(world.rig.camera.global_position, true)
	world.forest.lod_manager.update_now(world.rig.camera)
	await frames(n)
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw


func snap(name: String) -> void:
	if DisplayServer.get_name() == "headless":
		return
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	var path := out_dir.path_join(name + ".png")
	img.save_png(path)
	print("shot ", path)


func check(cond: bool, what: String) -> void:
	if cond:
		passes += 1
		print("  ok   ", what)
	else:
		failures.append(what)
		print("  FAIL ", what)


func look_from(pos: Vector3, target: Vector3) -> void:
	world.rig.set_mode(CameraRig.Mode.FREE)
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	var cam := world.rig.camera
	cam.global_position = pos
	cam.look_at(target, Vector3.UP)
	var e := cam.global_transform.basis.get_euler()
	world.rig._pitch = e.x
	world.rig._yaw = e.y


func road_view(s: float, lateral: float, height: float, ahead: float, look_h := 1.0) -> void:
	var here := world.road.sample(s, lateral)
	var tgt := world.road.sample(s + ahead, lateral * 0.5)
	look_from(here.origin + Vector3.UP * height, tgt.origin + Vector3.UP * look_h)


# -------------------------------------------------------------------- shots
func run_shots(args: PackedStringArray) -> void:
	var only := ""
	var settle_frames := 5
	for a in args:
		if a.begins_with("--only="):
			only = a.get_slice("=", 1)
		if a.begins_with("--settle="):
			settle_frames = int(a.get_slice("=", 1))
	var views := {
		"01_road_straight": func(): road_view(60.0, -1.7, 1.3, 40.0, 1.6),
		"02_road_curve": func(): road_view(1320.0, -1.7, 1.3, 35.0, 1.4),
		"03_driver_low": func(): road_view(260.0, -1.0, 0.9, 30.0, 1.2),
		"04_roadside": func(): road_view(820.0, -6.5, 1.6, 8.0, 1.0),
		"05_forest_inside": func(): road_view(500.0, -32.0, 1.7, 25.0, 2.5),
		"06_canopy_up": func(): road_view(980.0, -1.7, 1.4, 14.0, 9.0),
		"07_aerial": func(): road_view(400.0, 20.0, 70.0, 150.0, -10.0),
		"08_ground_detail": func(): road_view(1700.0, -7.5, 0.7, 4.0, -0.4),
		"10_lod_debug": func():
			RenderingServer.global_shader_parameter_set("debug_lod", true)
			road_view(1500.0, -1.7, 24.0, 60.0, 0.0),
		"09_chase_car": func():
			world.rig.set_mode(CameraRig.Mode.CHASE)
			world.car.reset_to(world._road_spawn(2400.0))
			world.rig.camera.global_position = world.car.global_position + Vector3(0, 3, 8)
			for i in 30:
				world.rig._chase(1.0 / 30.0),
	}
	world.hud.visible = false
	for name in views:
		if only != "" and not Array(only.split(",")).any(func(o): return name.begins_with(o)):
			continue
		views[name].call()
		await settle(settle_frames)
		await snap(name)
		RenderingServer.global_shader_parameter_set("debug_lod", false)


# -------------------------------------------------------------------- tests
func run_tests() -> void:
	print("== Forest Drive checks ==")
	GraphicsSettings.set_preset(GraphicsSettings.Preset.HIGH, false)   # deterministic, not saved
	await frames(2)
	var t0 := Time.get_ticks_msec()
	_test_resources()
	_test_terrain()
	_test_road()
	_test_placement()
	_test_seams()
	_test_budget()
	await _test_lod()
	await _test_presets()
	await _test_car()
	print("== %d passed, %d failed (%.1f s) ==" % [passes, failures.size(), (Time.get_ticks_msec() - t0) / 1000.0])
	if failures.is_empty():
		print("ALL TESTS PASSED")
	else:
		for f in failures:
			print("FAILED: ", f)


func _test_resources() -> void:
	var cat: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/catalog.json"))
	var missing := 0
	for v in cat["variants"]:
		if not ResourceLoader.exists(v["file"]):
			missing += 1
			print("     missing ", v["file"])
	check(missing == 0, "all %d catalog meshes exist" % cat["variants"].size())
	var bad := 0
	for m in ForestGenerator.MATERIALS.values() + ["res://assets/materials/terrain.tres", "res://assets/materials/road.tres"]:
		var mat := load(m) as ShaderMaterial
		if mat == null or mat.shader == null:
			bad += 1
			continue
		for u in mat.shader.get_shader_uniform_list():
			if str(u["hint_string"]) == "Texture2D" or str(u["hint_string"]) == "Texture2DArray":
				if mat.get_shader_parameter(u["name"]) == null:
					bad += 1
					print("     ", m, " has no texture for ", u["name"])
	check(bad == 0, "materials load and every sampler has a texture")
	var lods_ok := true
	for v in cat["variants"]:
		var meshes := ForestGenerator.load_lod_meshes(v, world.forest.materials)
		if meshes.size() != v["tris"].size() or meshes.is_empty():
			lods_ok = false
		for m in meshes:
			for si in m.get_surface_count():
				if not (m.surface_get_material(si) is ShaderMaterial):
					lods_ok = false
	check(lods_ok, "every variant has its LOD meshes with shared shader materials")
	var tree_lods := 0
	for v in cat["variants"]:
		if v["category"] == "tree" and v["tris"].size() == 3 and v["tris"][0] > v["tris"][1] and v["tris"][1] > v["tris"][2]:
			tree_lods += 1
	check(tree_lods >= 12, "%d tree variants with 3 decreasing LODs (>= 12)" % tree_lods)


func _test_terrain() -> void:
	var t := world.terrain
	check(t.heights.size() == t.res * t.res, "heightmap %dx%d loaded" % [t.res, t.res])
	check(t.chunks.size() == 1024, "1024 terrain chunks")
	var lo := INF
	var hi := -INF
	for h in t.heights:
		lo = minf(lo, h)
		hi = maxf(hi, h)
	check(hi - lo > 20.0, "terrain is not flat (relief %.1f m)" % (hi - lo))


func _test_road() -> void:
	var r := world.road
	var n := r.points.size()
	var max_gap := 0.0
	var max_grade := 0.0
	var below := 0
	for i in n:
		var a := r.points[i]
		var b := r.points[(i + 1) % n]
		max_gap = maxf(max_gap, a.distance_to(b))
		max_grade = maxf(max_grade, absf(b.y - a.y) / maxf(Vector2(b.x - a.x, b.z - a.z).length(), 0.01))
		# terrain must stay under the asphalt
		for lat in [-4.0, -2.0, 0.0, 2.0, 4.0]:
			var p := r.sample(float(i), lat).origin
			if world.terrain.height_at(p.x, p.z) > p.y - 0.02:
				below += 1
	check(max_gap < 1.5, "road centreline is continuous (max gap %.2f m), closed loop of %.0f m" % [max_gap, r.length])
	check(max_grade < 0.08, "road grade <= 8 %% (max %.1f %%)" % (max_grade * 100.0))
	check(below == 0, "terrain never pokes through the asphalt (%d of %d samples)" % [below, n * 5])
	check(r.triangles >= 15000 and r.triangles <= 40000, "road mesh %d triangles, %d sections" % [r.triangles, r.sections])


## Road index for fast nearest-distance queries.
func _road_grid() -> Dictionary:
	var g := {}
	for i in world.road.points.size():
		var p := world.road.points[i]
		var k := Vector2i(floori(p.x / 16.0), floori(p.z / 16.0))
		if not g.has(k):
			g[k] = PackedVector2Array()
		g[k].append(Vector2(p.x, p.z))
	return g


func _road_dist(g: Dictionary, x: float, z: float) -> float:
	var k := Vector2i(floori(x / 16.0), floori(z / 16.0))
	var best := INF
	for dz in range(-2, 3):
		for dx in range(-2, 3):
			var arr = g.get(k + Vector2i(dx, dz))
			if arr == null:
				continue
			for p: Vector2 in arr:
				best = minf(best, p.distance_squared_to(Vector2(x, z)))
	return sqrt(best)


func _test_placement() -> void:
	var g := _road_grid()
	var lm := world.forest.lod_manager
	var floating := 0
	var buried := 0
	var on_road := 0
	var worst_float := 0.0
	var checked := 0
	for v in lm.variants:
		if v.cover:
			continue
		var meta: Dictionary = world.forest.catalog[v.name]
		var min_road := 6.0
		match str(meta["category"]):
			"tree": min_road = 6.6
			"understory": min_road = 6.3
			"bush": min_road = 6.1
			"rock": min_road = 6.9
			"prop", "detail": min_road = 8.0
		for cid in v.cells:
			var buf: PackedFloat32Array = v.cells[cid]
			for i in range(0, buf.size(), 16):
				var x := buf[i + 3]
				var y := buf[i + 7]
				var z := buf[i + 11]
				var ground := world.terrain.height_at(x, z)
				var dy := y - ground
				checked += 1
				if dy > 0.08:
					floating += 1
					worst_float = maxf(worst_float, dy)
				if dy < -1.0 and meta["category"] != "rock":
					buried += 1
				if _road_dist(g, x, z) < min_road:
					on_road += 1
	check(floating == 0, "no floating objects (%d of %d above ground, worst %.2f m)" % [floating, checked, worst_float])
	check(buried == 0, "no buried trees/props (%d)" % buried)
	check(on_road == 0, "no tree, bush, rock or prop on the road or its shoulders (%d)" % on_road)
	var cover_on_road := 0
	var data := ForestGenerator.load_instance_set(str(world.meta["instances"]["cover"]))
	var f: PackedFloat32Array = data["floats"]
	for i in range(0, f.size(), 16 * 7):
		if _road_dist(g, f[i + 3], f[i + 11]) < 4.95:
			cover_on_road += 1
	check(cover_on_road == 0, "ground cover stays off the asphalt (sampled %d)" % (f.size() / (16 * 7)))


func _test_seams() -> void:
	# The fine chunk's odd border vertices are fully morphed when the neighbour is coarser, so the
	# remaining gap is bounded by the bilinear error at that spacing; skirts must cover it.
	var t := world.terrain
	var worst := [0.0, 0.0, 0.0, 0.0]
	for k in 4:
		var g: float = TerrainSystem.SPACING[k + 1]
		for c in range(0, t.res - 1, 64):
			for s in range(0, t.res - 1 - int(g), int(g)):
				for axis in 2:
					var x := float(c) if axis == 0 else float(s)
					var z := float(s) if axis == 0 else float(c)
					var dx := 0.0 if axis == 0 else g
					var dz := g if axis == 0 else 0.0
					var mid := t.height_at(t.origin + x + dx * 0.5, t.origin + z + dz * 0.5)
					var lin := (t.height_at(t.origin + x, t.origin + z) + t.height_at(t.origin + x + dx, t.origin + z + dz)) * 0.5
					worst[k] = maxf(worst[k], absf(mid - lin))
	var ok := true
	for k in 4:
		if worst[k] > TerrainSystem.SKIRT[k + 1]:
			ok = false
	check(ok, "terrain LOD seams covered by skirts (max gap per level %s m, skirts %s m)" % [
		str(worst.map(func(v): return snappedf(v, 0.01))), str(TerrainSystem.SKIRT.slice(1))])


func _test_budget() -> void:
	var b := PerfStats.allocated_budget(world)
	print("     allocated unique triangles: ", JSON.stringify(b))
	check(int(b["total"]) >= 380000 and int(b["total"]) <= 520000, "environment geometry budget %d triangles (target 400-500k)" % b["total"])


func _test_lod() -> void:
	road_view(300.0, -1.7, 1.3, 30.0, 1.4)
	await settle(4)
	var lm := world.forest.lod_manager
	var vis: Array = lm.stats["visible_instances"]
	check(vis[0] > 0 and vis[1] > 0 and vis[2] > 0 and vis[3] > 0, "LOD buckets filled near the road (LOD0 %d, LOD1 %d, LOD2 %d, ground cover %d)" % vis)
	check(lm.total_instances() > 400000, "%d instanced trees/plants/rocks/props/ground cover managed" % lm.total_instances())
	var bad := 0
	var cam := world.rig.camera.global_position
	var cs := lm.cell_size
	for v in lm.variants:
		var bands := lm._bands(v)
		var limit: float = (bands[0].z + bands[0].w) * 1.25 + 8.0 + cs * 1.42
		for cid in v.buckets[0].get("cells", PackedInt32Array()):
			var cc := Vector2(lm.origin + (cid % lm.grid + 0.5) * cs, lm.origin + (cid / lm.grid + 0.5) * cs)
			if cc.distance_to(Vector2(cam.x, cam.z)) > limit:
				bad += 1
	check(bad == 0, "LOD0 buckets only hold nearby cells (%d stray)" % bad)
	var nodes := Performance.get_monitor(Performance.OBJECT_NODE_COUNT)
	check(nodes < 2500, "scene stays light: %d nodes for %d instances (MultiMesh buckets)" % [nodes, lm.total_instances()])
	# turning around must re-cull
	road_view(300.0, -1.7, 1.3, -30.0, 1.4)
	await settle(4)
	check(lm.stats["updates"] >= 2, "LOD/culling updates run when the camera turns")


func _test_presets() -> void:
	var start: int = GraphicsSettings.preset
	var ok := true
	for p in 4:
		GraphicsSettings.set_preset(p, false)
		await frames(3)
		var s := GraphicsSettings.settings
		if not is_equal_approx(world.sun.directional_shadow_max_distance, float(s["shadow_distance"])):
			ok = false
		if not is_equal_approx(world.forest.lod_manager.lod_scale, float(s["lod_scale"])):
			ok = false
	GraphicsSettings.set_preset(start, false)
	await frames(2)
	check(ok, "all four graphics presets apply (Low, Medium, High, Ultra)")


func _test_car() -> void:
	world.rig.set_mode(CameraRig.Mode.CHASE)
	var s0 := 120.0
	world.car.reset_to(world._road_spawn(s0))
	await frames(30)
	Input.action_press("accelerate", 1.0)
	for i in 240:
		await get_tree().physics_frame
	Input.action_release("accelerate")
	var car := world.car
	var s1 := world.road.nearest_s(car.global_position)
	var lat := world.road.lateral_offset(car.global_position)
	var road_y := world.road.sample(s1, lat).origin.y
	check(car.speed_kmh > 25.0, "car accelerates on the road (%.0f km/h after 4 s)" % car.speed_kmh)
	check(s1 > s0 + 15.0, "car drives forward along the road (%.0f m)" % (s1 - s0))
	check(absf(car.global_position.y - road_y) < 1.2, "car stays on the road surface (height %.2f m)" % (car.global_position.y - road_y))
	# steering: holding "left" must yaw the car to the left (counter-clockwise seen from above)
	var f0 := -car.global_transform.basis.z
	Input.action_press("steer_left", 1.0)
	Input.action_press("accelerate", 0.4)
	for i in 60:
		await get_tree().physics_frame
	Input.action_release("steer_left")
	Input.action_release("accelerate")
	var f1 := -car.global_transform.basis.z
	check(f0.cross(f1).y > 0.02, "steering left turns the car left (yaw change %.1f deg)" % rad_to_deg(asin(clampf(f0.cross(f1).y, -1.0, 1.0))))


# -------------------------------------------------------------------- bench
func run_bench() -> void:
	world.hud.visible = false
	var presets := [GraphicsSettings.preset]
	if "--all-presets" in OS.get_cmdline_user_args():
		presets = [0, 1, 2, 3]
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--presets="):
			presets = []
			for n in a.get_slice("=", 1).split(","):
				presets.append(GraphicsSettings.NAMES.map(func(x): return x.to_lower()).find(n.to_lower()))
	var secs := 25.0
	var min_frames := 0
	var warmup := 30
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--seconds="):
			secs = float(a.get_slice("=", 1))
		if a.begins_with("--frames="):
			min_frames = int(a.get_slice("=", 1))
		if a.begins_with("--settle="):
			warmup = int(a.get_slice("=", 1))
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	Engine.max_fps = 0
	var report := {"gpu": RenderingServer.get_video_adapter_name(), "api": RenderingServer.get_video_adapter_api_version(),
			"os": OS.get_name(), "cpu": OS.get_processor_name(), "resolution": str(get_viewport().get_visible_rect().size),
			"allocated_triangles": PerfStats.allocated_budget(world), "load_ms": world.build_ms, "presets": {}}
	for p in presets:
		GraphicsSettings.set_preset(p, false)
		world.rig.set_mode(CameraRig.Mode.CINEMATIC)
		world.rig.place_cinematic(60.0)
		world.rig.cinematic_speed = 22.0
		await settle(warmup)
		var times := PackedFloat32Array()
		var samples := []
		var t_end := Time.get_ticks_msec() + int(secs * 1000.0)
		var last := Time.get_ticks_usec()
		var next_sample := Time.get_ticks_msec() + 1000
		while Time.get_ticks_msec() < t_end or times.size() < min_frames:
			await get_tree().process_frame
			var now := Time.get_ticks_usec()
			times.append((now - last) / 1000.0)
			last = now
			if Time.get_ticks_msec() >= next_sample or times.size() <= min_frames:
				next_sample = Time.get_ticks_msec() + 1000
				samples.append(PerfStats.snapshot(world))
		var sorted := times.duplicate()
		sorted.sort()
		var avg := 0.0
		for t in times:
			avg += t
		avg /= maxf(times.size(), 1)
		var p99 := sorted[int(sorted.size() * 0.99)] if sorted.size() > 0 else 0.0
		var p95 := sorted[int(sorted.size() * 0.95)] if sorted.size() > 0 else 0.0
		var pick := func(key): return samples.map(func(d): return d[key])
		var r := {
			"frames": times.size(), "avg_ms": avg, "avg_fps": 1000.0 / maxf(avg, 0.001), "p95_ms": p95, "p99_ms": p99,
			"one_percent_low_fps": 1000.0 / maxf(p99, 0.001),
			"main_primitives": _avg(pick.call("main_primitives")), "shadow_primitives": _avg(pick.call("shadow_primitives")),
			"main_draw_calls": _avg(pick.call("main_draw_calls")), "shadow_draw_calls": _avg(pick.call("shadow_draw_calls")),
			"video_mem_mb": _avg(pick.call("video_mem_mb")), "texture_mem_mb": _avg(pick.call("texture_mem_mb")),
			"ram_static_mb": _avg(pick.call("ram_static_mb")),
			"lod_instances": world.forest.lod_manager.stats["visible_instances"],
			"lod_update_ms": world.forest.lod_manager.stats["last_update_ms"],
		}
		report["presets"][GraphicsSettings.NAMES[p]] = r
		print("BENCH %s: %.1f fps avg, 1%% low %.1f fps, %.2f ms avg, main %d tris / %d draws, shadow %d tris / %d draws, VRAM %.0f MB" % [
			GraphicsSettings.NAMES[p], r["avg_fps"], r["one_percent_low_fps"], avg, r["main_primitives"], r["main_draw_calls"],
			r["shadow_primitives"], r["shadow_draw_calls"], r["video_mem_mb"]])
		await snap("bench_%s" % GraphicsSettings.NAMES[p].to_lower())
	var f := FileAccess.open(out_dir.path_join("bench.json"), FileAccess.WRITE)
	f.store_string(JSON.stringify(report, "  "))
	print("bench report ", out_dir.path_join("bench.json"))


func _avg(a: Array) -> float:
	if a.is_empty():
		return 0.0
	var s := 0.0
	for x in a:
		s += float(x)
	return s / a.size()
