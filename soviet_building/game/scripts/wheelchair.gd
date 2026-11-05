extends CharacterBody3D
## Electric wheelchair seen from the seat (first person).
## Drive model of a real mid-wheel-drive / rear-drive power chair controlled by a joystick:
## - five speed settings (2.2 .. 6.3 km/h), reverse at 45 % of the forward speed;
## - limited motor acceleration and stronger braking when the stick is released (electromagnetic brakes
##   click open when you start and engage when you stop; a stopped chair does not roll);
## - differential drive: turns on the spot, turns slower the faster it goes;
## - the front casters swing round when you change direction (a small heading wobble);
## - on slopes gravity speeds it up or slows it down a little;
## - it does not slide along walls: hitting something stops the chair with a bump.

var game

const SPEEDS := [0.6, 0.9, 1.2, 1.45, 1.75]
const REVERSE := 0.45
const ACCEL := 0.75
const BRAKE := 1.7
const YAW_MAX := 1.35
const YAW_ACC := 3.4
const RADIUS := 0.36
const EYE := 1.18
const MOUSE_SENS := 0.0024
const REACH := 2.4

var speed_level := 2
var v := 0.0
var w := 0.0
var caster := 0.0
var caster_kick := 0.0
var last_dir := 1.0
var head: Node3D
var cam: Camera3D
var chair: Node3D
var stick: Node3D
var look_yaw := 0.0
var look_pitch := -0.08
var look_idle := 0.0
var shake := 0.0
var t := 0.0
var braked := true
var input_override = null
var target = null
var motor: AudioStreamPlayer
var wheels: AudioStreamPlayer
var _ray_frame := 0
var _last_room := ""


func _ready() -> void:
	collision_layer = game.L_PLAYER
	collision_mask = game.L_WORLD | game.L_DOORS | game.L_LIFT
	floor_max_angle = deg_to_rad(20.0)
	floor_snap_length = 0.12
	floor_stop_on_slope = true
	floor_constant_speed = true
	safe_margin = 0.02
	platform_on_leave = CharacterBody3D.PLATFORM_ON_LEAVE_DO_NOTHING
	var cs := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = RADIUS
	cap.height = 1.3
	cs.shape = cap
	cs.position = Vector3(0, 0.65, 0)
	add_child(cs)
	head = Node3D.new()
	head.position = Vector3(0, EYE, 0.06)
	add_child(head)
	cam = Camera3D.new()
	cam.fov = 74.0
	cam.near = 0.02
	cam.far = 400.0
	head.add_child(cam)
	cam.current = true
	_build_chair()
	motor = _loop_player("motor_loop", -80.0)
	wheels = _loop_player("wheels_loop", -80.0)
	if not ("--test" in OS.get_cmdline_user_args() or "--shots" in OS.get_cmdline_user_args()):
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _loop_player(name: String, vol: float) -> AudioStreamPlayer:
	var p := AudioStreamPlayer.new()
	p.stream = game.sfx(name, true)
	p.volume_db = vol
	add_child(p)
	p.play()
	return p


func _mat(c: Color, rough := 0.7, metal := 0.0) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.roughness = rough
	m.metallic = metal
	return m


func _box(parent: Node3D, size: Vector3, pos: Vector3, mat: Material) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	mi.material_override = mat
	mi.position = pos
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	parent.add_child(mi)
	return mi


func _plaid() -> StandardMaterial3D:
	var img := Image.create(64, 64, false, Image.FORMAT_RGB8)
	for y in 64:
		for x in 64:
			var a := (x / 8) % 2
			var b := (y / 8) % 2
			var c := Color(0.2, 0.24, 0.18).lerp(Color(0.46, 0.4, 0.3), (a + b) * 0.5)
			if x % 16 == 0 or y % 16 == 0:
				c = Color(0.42, 0.14, 0.1)
			img.set_pixel(x, y, c)
	var m := StandardMaterial3D.new()
	m.albedo_texture = ImageTexture.create_from_image(img)
	m.uv1_scale = Vector3(2, 2, 2)
	m.roughness = 0.95
	return m


func _build_chair() -> void:
	chair = Node3D.new()
	add_child(chair)
	var leather := _mat(Color(0.06, 0.055, 0.05), 0.55)
	var steel := _mat(Color(0.18, 0.19, 0.2), 0.4, 0.8)
	var rubber := _mat(Color(0.03, 0.03, 0.03), 0.9)
	var blanket := _plaid()
	for sx in [-1.0, 1.0]:
		_box(chair, Vector3(0.075, 0.05, 0.42), Vector3(0.275 * sx, 0.74, -0.06), leather)
		_box(chair, Vector3(0.025, 0.25, 0.025), Vector3(0.275 * sx, 0.6, -0.24), steel)
		var wheel := MeshInstance3D.new()
		var cm := CylinderMesh.new()
		cm.top_radius = 0.3
		cm.bottom_radius = 0.3
		cm.height = 0.04
		cm.radial_segments = 24
		wheel.mesh = cm
		wheel.material_override = rubber
		wheel.rotation.z = PI / 2
		wheel.position = Vector3(0.34 * sx, 0.3, 0.08)
		chair.add_child(wheel)
		var rim := MeshInstance3D.new()
		var rm := TorusMesh.new()
		rm.inner_radius = 0.25
		rm.outer_radius = 0.27
		rim.mesh = rm
		rim.material_override = _mat(Color(0.7, 0.72, 0.74), 0.25, 1.0)
		rim.rotation.z = PI / 2
		rim.position = Vector3(0.38 * sx, 0.3, 0.08)
		chair.add_child(rim)
		_box(chair, Vector3(0.1, 0.08, 0.25), Vector3(0.09 * sx, 0.12, -0.6), _mat(Color(0.16, 0.1, 0.06), 0.6))
	# legs under a plaid blanket: two rounded thighs and the blanket hanging over the knees
	for sx in [-1.0, 1.0]:
		var thigh := MeshInstance3D.new()
		var cp := CapsuleMesh.new()
		cp.radius = 0.085
		cp.height = 0.5
		cp.radial_segments = 12
		cp.rings = 4
		thigh.mesh = cp
		thigh.material_override = blanket
		thigh.rotation.x = PI / 2
		thigh.position = Vector3(0.105 * sx, 0.6, -0.27)
		thigh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		chair.add_child(thigh)
		var shin := MeshInstance3D.new()
		var cs2 := CapsuleMesh.new()
		cs2.radius = 0.06
		cs2.height = 0.46
		shin.mesh = cs2
		shin.material_override = _mat(Color(0.12, 0.1, 0.09), 0.9)
		shin.position = Vector3(0.1 * sx, 0.35, -0.52)
		shin.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		chair.add_child(shin)
	_box(chair, Vector3(0.44, 0.3, 0.02), Vector3(0, 0.46, -0.59), blanket)
	_box(chair, Vector3(0.44, 0.02, 0.24), Vector3(0, 0.07, -0.6), steel)
	_box(chair, Vector3(0.08, 0.05, 0.13), Vector3(0.275, 0.785, -0.22), _mat(Color(0.05, 0.05, 0.05), 0.4))
	stick = Node3D.new()
	stick.position = Vector3(0.275, 0.81, -0.23)
	chair.add_child(stick)
	_box(stick, Vector3(0.012, 0.06, 0.012), Vector3(0, 0.03, 0), steel)
	var knob := MeshInstance3D.new()
	var sm := SphereMesh.new()
	sm.radius = 0.018
	sm.height = 0.036
	knob.mesh = sm
	knob.material_override = _mat(Color(0.04, 0.04, 0.04), 0.3)
	knob.position = Vector3(0, 0.065, 0)
	stick.add_child(knob)
	var led := _box(chair, Vector3(0.012, 0.004, 0.012), Vector3(0.255, 0.811, -0.19), StandardMaterial3D.new())
	var lm: StandardMaterial3D = led.material_override
	lm.emission_enabled = true
	lm.emission = Color(0.2, 1.0, 0.3)
	lm.emission_energy_multiplier = 2.0


func _unhandled_input(event: InputEvent) -> void:
	if get_tree().paused:
		return
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		look_yaw = clamp(look_yaw - event.relative.x * MOUSE_SENS, -2.1, 2.1)
		look_pitch = clamp(look_pitch - event.relative.y * MOUSE_SENS, -1.25, 1.0)
		look_idle = 0.0
	elif event is InputEventMouseButton and event.pressed and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED \
			and not game.hud.menu_open():
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	if event.is_action_pressed("speed_up"):
		speed_level = min(speed_level + 1, SPEEDS.size() - 1)
		game.hud.set_speed(speed_level, SPEEDS.size())
		game.play_at("button", global_position + Vector3(0.27, 0.8, 0), -14.0, 1.4, 4.0)
	elif event.is_action_pressed("speed_down"):
		speed_level = max(speed_level - 1, 0)
		game.hud.set_speed(speed_level, SPEEDS.size())
		game.play_at("button", global_position + Vector3(0.27, 0.8, 0), -14.0, 1.2, 4.0)
	elif event.is_action_pressed("horn"):
		game.play_at("horn", global_position + Vector3(0, 0.8, 0), -6.0, 1.0, 30.0)
		game.critters.scare(global_position, 8.0)
	elif event.is_action_pressed("interact"):
		if target != null and is_instance_valid(target):
			target.interact(self)


func joystick() -> Vector2:
	if input_override != null:
		return input_override
	var thr: float = Input.get_action_strength("drive_forward") - Input.get_action_strength("drive_back")
	var st: float = Input.get_action_strength("turn_right") - Input.get_action_strength("turn_left")
	var right := Vector2(Input.get_joy_axis(0, JOY_AXIS_RIGHT_X), Input.get_joy_axis(0, JOY_AXIS_RIGHT_Y))
	if right.length() > 0.2:
		look_yaw = clamp(look_yaw - right.x * 0.04, -2.1, 2.1)
		look_pitch = clamp(look_pitch - right.y * 0.03, -1.25, 1.0)
		look_idle = 0.0
	return Vector2(thr, st)


func _physics_process(dt: float) -> void:
	t += dt
	var j := joystick()
	var vmax: float = SPEEDS[speed_level]
	var vt: float = j.x * vmax * (REVERSE if j.x < 0.0 else 1.0)
	# motor torque: accelerate slowly, brake harder (and when the stick goes the other way)
	var a: float = ACCEL if (absf(vt) > absf(v) and signf(vt) == signf(v)) or absf(v) < 0.02 else BRAKE
	if abs(j.x) < 0.05:
		a = BRAKE
	v = move_toward(v, vt, a * dt)
	var turn_scale: float = 1.0 - 0.55 * clamp(abs(v) / SPEEDS[-1], 0.0, 1.0)
	var wt: float = -j.y * YAW_MAX * turn_scale * (0.75 if speed_level < 1 else 1.0)
	w = move_toward(w, wt, YAW_ACC * dt)
	# casters swing round when the direction of travel reverses
	var dir: float = signf(v) if absf(v) > 0.05 else last_dir
	if dir != last_dir:
		caster_kick = randf_range(-1.0, 1.0) * 0.5
		last_dir = dir
	caster = lerp(caster, caster_kick, 6.0 * dt)
	caster_kick = move_toward(caster_kick, 0.0, 1.5 * dt)
	var yaw_rate: float = w + caster * 0.35 * clampf(absf(v) * 2.0, 0.0, 1.0)
	rotate_y(yaw_rate * dt)
	# brakes
	var moving: bool = abs(v) > 0.02 or abs(w) > 0.02 or j.length() > 0.05
	if moving and braked:
		braked = false
		game.play_at("brake_release", global_position + Vector3(0, 0.3, 0), -12.0, 1.0, 6.0)
	elif not moving and not braked:
		braked = true
		game.play_at("brake_engage", global_position + Vector3(0, 0.3, 0), -14.0, 1.0, 6.0)
	var fwd := -global_transform.basis.z
	# slope: gravity along the floor speeds the chair up downhill (only while driving; the brakes hold it otherwise)
	if is_on_floor() and not braked:
		var n := get_floor_normal()
		v += 9.81 * n.dot(fwd) * 0.3 * dt
	var vel := fwd * v
	if is_on_floor():
		velocity = Vector3(vel.x, min(velocity.y, 0.0), vel.z)
	else:
		velocity = Vector3(vel.x, velocity.y - 9.81 * dt, vel.z)
	var before := global_position
	move_and_slide()
	# hitting something: stop with a bump instead of gliding along it
	for i in get_slide_collision_count():
		var c: KinematicCollision3D = get_slide_collision(i)
		var nrm := c.get_normal()
		if abs(nrm.y) > 0.6:
			continue
		var into: float = -nrm.dot(fwd * signf(v))
		if into > 0.45 and abs(v) > 0.25:
			var hit: float = abs(v)
			v *= 0.1
			shake = clamp(hit * 0.025, 0.004, 0.05)
			game.play_at("bump", global_position + fwd * RADIUS + Vector3(0, 0.4, 0), linear_to_db(clamp(hit / 1.6, 0.15, 1.0)), randf_range(0.9, 1.1), 18.0)
			game.critters.scare(global_position, 4.0)
			break
		elif into > 0.2:
			v *= 0.85
	var moved: Vector3 = (global_position - before) / maxf(dt, 0.0001)
	_update_sound(moved.length())
	_update_view(dt)
	_update_target()
	_update_room()


func _update_sound(spd: float) -> void:
	var load_f: float = clamp(abs(v) / SPEEDS[-1] + abs(w) * 0.25, 0.0, 1.2)
	motor.volume_db = lerp(motor.volume_db, -60.0 if load_f < 0.02 else linear_to_db(0.16 + 0.5 * load_f) - 6.0, 0.2)
	motor.pitch_scale = 0.75 + 0.55 * clamp(abs(v) / SPEEDS[-1], 0.0, 1.0) + 0.15 * abs(w)
	var roll: float = clamp(spd / SPEEDS[-1], 0.0, 1.0)
	wheels.volume_db = lerp(wheels.volume_db, -60.0 if roll < 0.02 else linear_to_db(0.1 + 0.6 * roll) - 4.0, 0.2)
	wheels.pitch_scale = 0.8 + 0.4 * roll


func _update_view(dt: float) -> void:
	look_idle += dt
	if look_idle > 2.5 and abs(v) > 0.3:
		look_yaw = lerp(look_yaw, 0.0, 1.2 * dt)
	head.rotation = Vector3(look_pitch, look_yaw, 0)
	var vib: float = clamp(abs(v) / SPEEDS[-1], 0.0, 1.0)
	shake = move_toward(shake, 0.0, 0.12 * dt)
	cam.position = Vector3(randf_range(-1, 1) * shake, sin(t * 23.0) * 0.0018 * vib + randf_range(-1, 1) * shake,
		0.0)
	chair.rotation.z = sin(t * 17.0) * 0.002 * vib
	stick.rotation = Vector3(-joystick().x * 0.35, 0, -joystick().y * 0.35)


func _update_target() -> void:
	_ray_frame += 1
	if _ray_frame % 3 != 0:
		return
	var from := cam.global_position
	var to := from - cam.global_basis.z * REACH
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(from, to, game.L_WORLD | game.L_DOORS | game.L_INTERACT | game.L_LIFT,
		[get_rid()])
	q.collide_with_areas = true
	var hit: Dictionary = get_world_3d().direct_space_state.intersect_ray(q)
	var new_target = null
	if not hit.is_empty():
		var col: Object = hit["collider"]
		if col.has_meta("interact"):
			new_target = col.get_meta("interact")
	target = new_target
	game.hud.set_prompt(target.prompt(self) if target != null else "")


func _update_room() -> void:
	if _ray_frame % 15 != 0:
		return
	var r: Dictionary = game.room_at(global_position + Vector3(0, 0.3, 0))
	var id: String = r.get("id", "")
	if id != _last_room and id != "":
		_last_room = id
		game.hud.show_room(r)
