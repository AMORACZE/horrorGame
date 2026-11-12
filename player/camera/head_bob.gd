class_name HeadBob
extends Node3D
## Body motion layer of the camera rig: what walking does to a held camera.
##
## - Stride bob: one dip per footfall and a side-to-side shift per pair of
##   steps, phase-locked to PlayerFootsteps so the picture and the sound agree.
## - Strafe roll: a slight lean into sideways movement.
## - Settle: the camera pitches a touch with acceleration (forward on stopping,
##   back on starting) through a soft spring, so stops have a little weight.
## - Landing dip after a drop.
## All scaled by Settings comfort/head_bob. Writes only this node's local transform.

@export_group("Stride Bob")
## Vertical dip per footfall at walking speed, m.
@export var bob_vertical: float = 0.022
## Side-to-side shift per stride at walking speed, m.
@export var bob_lateral: float = 0.014
## Roll that follows the side shift, degrees.
@export var bob_roll_degrees: float = 0.35
## Nod per footfall, degrees.
@export var bob_pitch_degrees: float = 0.25
## How fast bob fades in / out with speed, 1/s.
@export var bob_response: float = 6.0
## Amplitude multiplier while crouched.
@export_range(0.0, 1.0) var crouch_bob_scale: float = 0.6

@export_group("Strafe Roll")
## Roll at walking speed sideways, degrees.
@export var strafe_roll_degrees: float = 1.1
@export var strafe_roll_response: float = 5.0

@export_group("Settle")
## Pitch per m/s² of forward acceleration, degrees.
@export var accel_pitch_degrees: float = 0.07
## Spring stiffness / damping of the settle (and landing) motion.
@export var settle_stiffness: float = 90.0
@export var settle_damping: float = 11.0
## Largest settle pitch, degrees.
@export var settle_max_degrees: float = 1.4

@export_group("Landing")
## Downward kick per unit of landing impact, m/s.
@export var landing_kick: float = 0.9
## Small kick for a step settling on the floor after stopping, m/s.
@export var stop_kick: float = 0.08

var _player: Player
var _steps: PlayerFootsteps
var _strength: float = 1.0  # Settings comfort/head_bob
var _bob_weight: float = 0.0
var _roll: float = 0.0
var _prev_forward_speed: float = 0.0
var _accel_filtered: float = 0.0
var _settle_pitch: float = 0.0
var _settle_pitch_vel: float = 0.0
var _dip: float = 0.0
var _dip_vel: float = 0.0
var _was_moving: bool = false


func _ready() -> void:
	_player = _find_player()
	_strength = Player.read_setting(&"comfort", &"head_bob", 1.0)
	Events.setting_changed.connect(_on_setting_changed)
	if _player:
		_steps = _player.get_node_or_null(^"Footsteps") as PlayerFootsteps
	if _steps:
		_steps.landed.connect(_on_landed)


func _process(delta: float) -> void:
	if _player == null or delta <= 0.0:
		return
	var local_v := _player.get_local_velocity()
	var speed := Vector2(local_v.x, local_v.z).length()
	var grounded := _player.is_grounded()

	# Stride bob ---------------------------------------------------------------
	var target_weight := 0.0
	if grounded:
		target_weight = clampf(speed / maxf(_player.walk_speed, 0.01), 0.0, 1.5)
	_bob_weight = lerpf(_bob_weight, target_weight, 1.0 - exp(-delta * bob_response))
	var amp := _bob_weight * _strength * lerpf(1.0, crouch_bob_scale, _player.get_crouch_amount())
	var phase := _steps.get_visual_phase() if _steps else 0.0
	var dip := 0.5 + 0.5 * cos(TAU * phase)  # 1 at each footfall
	var side := sin(PI * phase)              # one sway per two steps
	var bob_pos := Vector3(side * bob_lateral, -dip * bob_vertical, 0.0) * amp
	var bob_rot := Vector3(-dip * deg_to_rad(bob_pitch_degrees), 0.0, -side * deg_to_rad(bob_roll_degrees)) * amp

	# Strafe roll --------------------------------------------------------------
	var target_roll := -clampf(local_v.x / maxf(_player.walk_speed, 0.01), -1.5, 1.5) * deg_to_rad(strafe_roll_degrees)
	_roll = lerpf(_roll, target_roll * _strength, 1.0 - exp(-delta * strafe_roll_response))

	# Settle: pitch with forward acceleration, through a spring -----------------
	var forward_speed := -local_v.z
	var accel := (forward_speed - _prev_forward_speed) / delta
	_prev_forward_speed = forward_speed
	_accel_filtered = lerpf(_accel_filtered, accel, 1.0 - exp(-delta * 12.0))
	var max_settle := deg_to_rad(settle_max_degrees)
	var settle_target := clampf(-_accel_filtered * deg_to_rad(accel_pitch_degrees), -max_settle, max_settle) * _strength
	_settle_pitch = _spring(_settle_pitch, settle_target, delta, true)

	# Landing / stop dip -------------------------------------------------------
	var moving := speed > 0.15
	if _was_moving and not moving and grounded:
		_dip_vel -= stop_kick * _strength
	_was_moving = moving
	_dip = _spring(_dip, 0.0, delta, false)

	position = bob_pos + Vector3(0.0, _dip, 0.0)
	rotation = bob_rot + Vector3(_settle_pitch, 0.0, _roll)


## Semi-implicit damped spring on either the settle pitch or the dip.
func _spring(value: float, target: float, delta: float, is_pitch: bool) -> float:
	var vel := _settle_pitch_vel if is_pitch else _dip_vel
	vel += (-(value - target) * settle_stiffness - vel * settle_damping) * delta
	value += vel * delta
	if is_pitch:
		_settle_pitch_vel = vel
	else:
		_dip_vel = vel
		value = clampf(value, -0.12, 0.05)
	return value


func _on_landed(impact: float) -> void:
	_dip_vel -= landing_kick * clampf(impact, 0.0, 1.0) * _strength


func _on_setting_changed(section: StringName, key: StringName, _value: Variant) -> void:
	if section == &"comfort" and key == &"head_bob":
		_strength = Player.read_setting(&"comfort", &"head_bob", 1.0)


func _find_player() -> Player:
	var n := get_parent()
	while n != null:
		if n is Player:
			return n as Player
		n = n.get_parent()
	return null
