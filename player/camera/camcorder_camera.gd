class_name CamcorderCamera
extends Camera3D
## The camcorder lens: a motorised zoom between Settings video/fov (wide) and a
## tele field of view.
##
## The zoom rocker (action "zoom", analog on a trigger) drives a motor that runs
## at a steady rate, with a short ease at each end like a real servo. The FOV is
## interpolated in focal-length space so the zoom looks even across its range.
## Emits Events.camera_zoom_changed(amount) while the amount changes.

@export_group("Zoom")
## Field of view at full tele, degrees (vertical).
@export var tele_fov: float = 18.0
## Motor speed, zoom range per second (1 = wide to tele in one second).
@export var zoom_speed: float = 0.75
## Ease time constant at the start / end of a zoom, seconds.
@export_range(0.0, 0.3) var zoom_ease: float = 0.09
## Hold the current zoom while input is locked instead of following the rocker.
@export var freeze_while_locked: bool = true

@export_group("Lens")
@export var near_clip: float = 0.05

## Current zoom amount, 0 (wide) .. 1 (tele).
var zoom_amount: float = 0.0

var _motor: float = 0.0
var _wide_fov: float = 68.0
var _last_emitted: float = 0.0


func _ready() -> void:
	near = near_clip
	_wide_fov = Player.read_setting(&"video", &"fov", 68.0)
	Events.setting_changed.connect(_on_setting_changed)
	_apply_fov()


func _process(delta: float) -> void:
	var target := _motor
	if not (freeze_while_locked and Game.is_input_locked()):
		target = clampf(Input.get_action_strength(&"zoom"), 0.0, 1.0)
	_motor = move_toward(_motor, target, zoom_speed * delta)
	var t := 1.0 if zoom_ease <= 0.0 else 1.0 - exp(-delta / zoom_ease)
	zoom_amount = lerpf(zoom_amount, _motor, t)
	if absf(zoom_amount - _motor) < 0.0005:
		zoom_amount = _motor
	_apply_fov()
	if not is_equal_approx(zoom_amount, _last_emitted):
		_last_emitted = zoom_amount
		Events.camera_zoom_changed.emit(zoom_amount)


## Wide-angle FOV currently in use (from Settings), degrees.
func get_wide_fov() -> float:
	return _wide_fov


## Optical magnification relative to wide (1 at wide, ~4 at tele).
func get_magnification() -> float:
	return _half_tan(_wide_fov) / _half_tan(fov)


## Look-sensitivity multiplier: proportional to the visible angle, so the
## image moves at the same on-screen speed at any zoom.
func get_look_scale() -> float:
	return _half_tan(fov) / _half_tan(_wide_fov)


## Jump straight to a zoom amount (no motor), e.g. for cutscenes or tests.
func set_zoom_immediate(amount: float) -> void:
	_motor = clampf(amount, 0.0, 1.0)
	zoom_amount = _motor
	_apply_fov()


func _apply_fov() -> void:
	var wide := log(_half_tan(_wide_fov))
	var tele := log(_half_tan(minf(tele_fov, _wide_fov)))
	fov = rad_to_deg(2.0 * atan(exp(lerpf(wide, tele, zoom_amount))))


func _on_setting_changed(section: StringName, key: StringName, _value: Variant) -> void:
	if section == &"video" and key == &"fov":
		_wide_fov = Player.read_setting(&"video", &"fov", 68.0)
		_apply_fov()


static func _half_tan(fov_degrees: float) -> float:
	return tan(deg_to_rad(clampf(fov_degrees, 1.0, 170.0)) * 0.5)
