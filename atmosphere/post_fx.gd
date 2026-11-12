class_name PostFx
extends CanvasLayer
## Camcorder post-process, instanced once by main.gd (CanvasLayer 50).
##
##   PostFx (layer 50)  ── Vhs: full-screen ColorRect running shaders/vhs.gdshader
##   └ OsdLayer (40)    ── CamcorderOsd: date stamp, counter, battery, zoom bar
##
## The OSD sits below the VHS pass so the tape degrades it like the picture.
## Also owns the 3D viewport's render scale and anti-aliasing.
## Settings: video/vhs_enabled, video/vhs_intensity, video/osd_enabled (in the
## OSD), video/render_scale.

## Strength of the autofocus hunt after a zoom change (0 disables it).
@export_range(0.0, 1.0) var autofocus_strength: float = 0.55
## Seconds the autofocus takes to settle.
@export_range(0.1, 3.0) var autofocus_settle_time: float = 0.9
## Use TAA on the 3D view (recommended: stabilises fog, soft shadows and thin
## window frames; the tape softens away the TAA blur anyway).
@export var use_taa: bool = true

@onready var _vhs: ColorRect = $Vhs
@onready var _osd: CamcorderOsd = $OsdLayer/CamcorderOsd

var _mat: ShaderMaterial
var _enabled: bool = true
var _intensity: float = 1.0
var _zoom: float = 0.0
var _tele_smoothed: float = 0.0
var _hunt_energy: float = 0.0
var _hunt_time: float = 10.0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_mat = _vhs.material as ShaderMaterial
	_enabled = bool(Settings.get_value(&"video", &"vhs_enabled"))
	_intensity = float(Settings.get_value(&"video", &"vhs_intensity"))
	_apply_vhs()
	_apply_render_scale(float(Settings.get_value(&"video", &"render_scale")))
	Events.setting_changed.connect(_on_setting_changed)
	Events.camera_zoom_changed.connect(_on_camera_zoom_changed)


func get_vhs_material() -> ShaderMaterial:
	return _mat


func get_osd() -> CamcorderOsd:
	return _osd


## Current autofocus blur sent to the shader (0 = sharp).
func get_focus_blur() -> float:
	return float(_mat.get_shader_parameter(&"focus_blur"))


func _process(delta: float) -> void:
	_tele_smoothed = lerpf(_tele_smoothed, _zoom, 1.0 - exp(-delta * 6.0))
	_hunt_time += delta
	var settle := maxf(autofocus_settle_time, 0.05)
	var env := exp(-_hunt_time * 3.0 / settle)
	# Overshoot-and-settle: the lens swings through focus a couple of times.
	var swing := 0.6 + 0.4 * cos(_hunt_time * TAU * 1.6 / settle)
	var blur := clampf(autofocus_strength * _hunt_energy * env * swing, 0.0, 1.0)
	if env < 0.01:
		_hunt_energy = 0.0
	_mat.set_shader_parameter(&"focus_blur", blur)
	_mat.set_shader_parameter(&"tele", _tele_smoothed)


func _on_camera_zoom_changed(amount: float) -> void:
	var step := absf(amount - _zoom)
	_zoom = clampf(amount, 0.0, 1.0)
	# Continuous zooming keeps the lens slightly soft; stopping lets it hunt.
	var remaining := _hunt_energy * exp(-_hunt_time * 3.0 / maxf(autofocus_settle_time, 0.05))
	_hunt_energy = clampf(maxf(remaining, 0.4 + step * 3.0), 0.0, 1.0)
	_hunt_time = 0.0
	# Apply immediately so the first frame after a zoom is already soft.
	_mat.set_shader_parameter(&"focus_blur", autofocus_strength * _hunt_energy)


func _apply_vhs() -> void:
	var on := _enabled and _intensity > 0.005
	_vhs.visible = on
	_mat.set_shader_parameter(&"intensity", clampf(_intensity, 0.0, 1.5))


func _apply_render_scale(value: float) -> void:
	var vp := get_viewport()
	if vp == null:
		return
	vp.scaling_3d_mode = Viewport.SCALING_3D_MODE_BILINEAR
	vp.scaling_3d_scale = clampf(value, 0.5, 1.0)
	vp.use_taa = use_taa
	vp.screen_space_aa = Viewport.SCREEN_SPACE_AA_DISABLED if use_taa else Viewport.SCREEN_SPACE_AA_FXAA
	vp.msaa_3d = Viewport.MSAA_DISABLED
	vp.use_debanding = true


func _on_setting_changed(section: StringName, key: StringName, value: Variant) -> void:
	if section != &"video":
		return
	match key:
		&"vhs_enabled":
			_enabled = bool(value)
			_apply_vhs()
		&"vhs_intensity":
			_intensity = float(value)
			_apply_vhs()
		&"render_scale":
			_apply_render_scale(float(value))
