extends Node
## Graphics quality: Low / Medium / High, switched with G (or F2) and remembered between runs.
## The 3D picture is rendered at a resolution limited by a pixel budget and upscaled with AMD FSR 1,
## so a Retina MacBook (2560x1600 and more) does not render 4 million pixels per frame.
## Mac (Apple M1 and newer) starts on Medium, Windows and Linux on High.

const NAMES := ["Низкое", "Среднее", "Высокое"]
const SAVE_PATH := "user://settings.cfg"

# per level: Low, Medium, High
const PIXEL_BUDGET := [1280 * 720, 1700 * 960, 0]   # max 3D pixels per frame, 0 = native resolution
const SSAO := [false, true, true]
const SSIL := [false, false, true]
const FOG_SIZE := [[40, 48], [52, 56], [64, 64]]       # volumetric fog froxel grid (xy, depth)
const SHADOWED_LAMPS := [3, 5, 8]
const SHADOW_ATLAS := [2048, 2048, 4096]
const MOON_ATLAS := [2048, 2048, 4096]
const MOON_SHADOW_DIST := [24.0, 32.0, 40.0]
const SOFT_SHADOWS := [RenderingServer.SHADOW_QUALITY_SOFT_VERY_LOW, RenderingServer.SHADOW_QUALITY_SOFT_LOW,
	RenderingServer.SHADOW_QUALITY_SOFT_LOW]

var game
var level := 2


func setup(g) -> void:
	game = g
	level = 1 if OS.has_feature("macos") else 2
	var cfg := ConfigFile.new()
	if cfg.load(SAVE_PATH) == OK:
		level = clampi(int(cfg.get_value("graphics", "quality", level)), 0, 2)
	get_window().size_changed.connect(_apply_scale)
	apply()


func cycle() -> void:
	level = (level + 1) % NAMES.size()
	apply()
	var cfg := ConfigFile.new()
	cfg.load(SAVE_PATH)
	cfg.set_value("graphics", "quality", level)
	cfg.save(SAVE_PATH)
	game.hud.message("Графика: " + NAMES[level])


func apply() -> void:
	var env: Environment = game.env
	env.volumetric_fog_enabled = fog_supported()
	env.ssao_enabled = SSAO[level]
	env.ssil_enabled = SSIL[level]
	RenderingServer.environment_set_volumetric_fog_volume_size(FOG_SIZE[level][0], FOG_SIZE[level][1])
	RenderingServer.positional_soft_shadow_filter_set_quality(SOFT_SHADOWS[level])
	RenderingServer.directional_soft_shadow_filter_set_quality(SOFT_SHADOWS[level])
	RenderingServer.directional_shadow_atlas_set_size(MOON_ATLAS[level], true)
	game.moon.directional_shadow_max_distance = MOON_SHADOW_DIST[level]
	get_viewport().positional_shadow_atlas_size = SHADOW_ATLAS[level]
	if game.lights:
		game.lights.max_shadows = SHADOWED_LAMPS[level]
	_apply_scale()


## Godot 4.7's Metal driver turns on texture atomics from the macOS version alone, but the texture format
## behind volumetric fog needs an Apple Silicon GPU. On Intel Macs and virtual GPUs the fog breaks, so it
## stays off there unless GODOT_MTL_DISABLE_IMAGE_ATOMICS=1 makes Godot use its fallback path.
func fog_supported() -> bool:
	if RenderingServer.get_current_rendering_driver_name() != "metal":
		return true
	if OS.get_environment("GODOT_MTL_DISABLE_IMAGE_ATOMICS") == "1":
		return true
	return RenderingServer.get_video_adapter_name().begins_with("Apple M")


func _apply_scale() -> void:
	var vp := get_viewport()
	var px := get_window().size
	var budget: int = PIXEL_BUDGET[level]
	var scale := 1.0
	if budget > 0 and px.x * px.y > budget:
		scale = clampf(sqrt(float(budget) / float(px.x * px.y)), 0.4, 1.0)
	if scale < 0.99:
		vp.scaling_3d_mode = Viewport.SCALING_3D_MODE_FSR
		vp.scaling_3d_scale = scale
		vp.fsr_sharpness = 0.25
	else:
		vp.scaling_3d_mode = Viewport.SCALING_3D_MODE_BILINEAR
		vp.scaling_3d_scale = 1.0
