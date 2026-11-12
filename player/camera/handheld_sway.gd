class_name HandheldSway
extends Node3D
## Hands layer of the camera rig: a camcorder held by a person standing still.
##
## - Drift: slow, smooth noise on pitch / yaw / roll (arms never hold still).
## - Tremor: a much smaller, quicker noise layer.
## - Breathing: a slow rise and fall with a matching nod.
## - Turn drag: the camera rolls a hair into fast turns.
## All scaled by Settings comfort/camera_sway and boosted while zoomed (a long
## lens is harder to hold steady; the optics already magnify the motion, so the
## extra boost is modest). Writes only this node's local transform.

@export_group("Drift")
## Peak drift angles, degrees (pitch, yaw, roll).
@export var drift_degrees: Vector3 = Vector3(0.32, 0.42, 0.28)
## Drift speed, noise cycles per second.
@export var drift_frequency: float = 0.22
## Positional drift, m.
@export var drift_position: float = 0.004

@export_group("Tremor")
@export var tremor_degrees: Vector3 = Vector3(0.05, 0.05, 0.03)
@export var tremor_frequency: float = 1.6

@export_group("Breathing")
## Seconds per breath.
@export var breath_period: float = 4.4
@export var breath_rise: float = 0.0045
@export var breath_pitch_degrees: float = 0.18

@export_group("Turn Drag")
## Roll per rad/s of yaw speed, degrees.
@export var turn_roll_degrees: float = 0.35
@export var turn_roll_max_degrees: float = 1.2

@export_group("Movement")
## Extra drift while walking (multiplier at walking speed).
@export var moving_drift_boost: float = 1.35

@export_group("Zoom")
## Sway multiplier at full tele (on top of the optical magnification).
@export var zoom_sway_boost: float = 1.3

var _player: Player
var _strength: float = 1.0  # Settings comfort/camera_sway
var _noise := FastNoiseLite.new()
var _time: float = 0.0
var _turn_roll: float = 0.0
var _move_boost: float = 1.0


func _ready() -> void:
	_player = _find_player()
	_noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	_noise.frequency = 1.0
	_noise.fractal_type = FastNoiseLite.FRACTAL_NONE
	_noise.seed = randi()
	_time = randf() * 100.0
	_strength = Player.read_setting(&"comfort", &"camera_sway", 1.0)
	Events.setting_changed.connect(_on_setting_changed)


func _process(delta: float) -> void:
	_time += delta
	var zoom := _player.get_zoom_amount() if _player else 0.0
	var speed := _player.get_ground_speed() if _player else 0.0
	var walk := _player.walk_speed if _player else 2.0
	_move_boost = lerpf(_move_boost, lerpf(1.0, moving_drift_boost, clampf(speed / walk, 0.0, 1.0)), 1.0 - exp(-delta * 2.0))
	var amp := _strength * lerpf(1.0, zoom_sway_boost, zoom)

	var td := _time * drift_frequency
	var drift := Vector3(_n(0.0, td), _n(37.0, td), _n(91.0, td))
	var tt := _time * tremor_frequency
	var tremor := Vector3(_n(211.0, tt), _n(263.0, tt), _n(307.0, tt))
	var rot := Vector3(
		drift.x * drift_degrees.x + tremor.x * tremor_degrees.x,
		drift.y * drift_degrees.y + tremor.y * tremor_degrees.y,
		drift.z * drift_degrees.z + tremor.z * tremor_degrees.z) * _move_boost

	var breath := sin(TAU * _time / maxf(breath_period, 0.5))
	rot.x += breath * breath_pitch_degrees

	var yaw_speed := _player.get_look_velocity().x if _player else 0.0
	var max_turn := turn_roll_max_degrees
	var target_turn := clampf(yaw_speed * turn_roll_degrees, -max_turn, max_turn)
	_turn_roll = lerpf(_turn_roll, target_turn, 1.0 - exp(-delta * 6.0))

	rotation = Vector3(deg_to_rad(rot.x), deg_to_rad(rot.y), deg_to_rad(rot.z + _turn_roll)) * amp
	position = Vector3(
		_n(401.0, td) * drift_position,
		_n(433.0, td) * drift_position + breath * breath_rise,
		0.0) * _strength


func _n(offset: float, t: float) -> float:
	return clampf(_noise.get_noise_2d(t, offset) * 1.4, -1.0, 1.0)


func _on_setting_changed(section: StringName, key: StringName, _value: Variant) -> void:
	if section == &"comfort" and key == &"camera_sway":
		_strength = Player.read_setting(&"comfort", &"camera_sway", 1.0)


func _find_player() -> Player:
	var n := get_parent()
	while n != null:
		if n is Player:
			return n as Player
		n = n.get_parent()
	return null
