class_name Player
extends CharacterBody3D
## First-person body carrying a handheld camcorder.
##
## This script owns the body: walking with weight, stairs, crouch, prop pushing,
## look state (yaw / pitch with a little inertia) and placing the camera rig on
## the body every rendered frame. The feel layers live in their own nodes:
##
##   Head (top-level, interpolated, yaw + pitch)
##   └─ HeadBob        player/camera/head_bob.gd        stride bob, strafe roll, settle, landing dip
##      └─ HandheldSway player/camera/handheld_sway.gd   noise sway, breathing, turn drag
##         └─ Camera   player/camera/camcorder_camera.gd motorised zoom / FOV
##   Footsteps          player/player_footsteps.gd       stride, surface, footstep + landing events
##   Interactor         player/player_interactor.gd      reticle ray, focus, interact
##
## Other systems only talk to the player through Events, Game.player and the
## public methods below.

## Emitted when the crouch state the player asked for changes (not the blend).
signal crouch_changed(crouching: bool)

@export_group("Movement")
## Normal walking speed, m/s.
@export var walk_speed: float = 2.0
## Speed while the sprint action is held ("hurry"), m/s.
@export var hurry_speed: float = 3.3
## Speed while crouched, m/s.
@export var crouch_speed: float = 1.0
## Fraction of the speed when walking backwards.
@export_range(0.1, 1.0) var backward_multiplier: float = 0.75
## Fraction of the speed when strafing.
@export_range(0.1, 1.0) var strafe_multiplier: float = 0.85
## How quickly the body picks up speed, m/s².
@export var acceleration: float = 7.0
## How quickly the body comes to rest when input is released, m/s².
@export var deceleration: float = 9.0
## Multiplier on acceleration while airborne.
@export_range(0.0, 1.0) var air_control: float = 0.2

@export_group("Steps")
## Tallest riser the body steps up (and sticks down) without leaving the floor, m.
@export var max_step_height: float = 0.22
## How fast the camera catches up after a step, 1/s. Higher = snappier.
@export var step_smoothing: float = 11.0
## Largest vertical camera lag allowed while smoothing steps, m.
@export var step_smoothing_max: float = 0.35

@export_group("Crouch")
@export var stand_height: float = 1.75
@export var crouch_height: float = 1.15
@export var stand_eye_height: float = 1.6
@export var crouch_eye_height: float = 1.0
## Seconds to go fully down or up.
@export var crouch_transition_time: float = 0.28

@export_group("Look")
## Radians per screen pixel at Settings controls/mouse_sensitivity = 1.
@export var mouse_radians_per_pixel: float = 0.0018
## Radians per second at full stick deflection at gamepad_sensitivity = 1.
@export var gamepad_turn_rate: float = 2.4
## Stick response exponent (1 = linear, 2 = fine control near centre).
@export var gamepad_curve: float = 1.8
## Pitch limit, degrees, up and down.
@export var pitch_limit_degrees: float = 82.0
## Time constant of the look inertia, seconds. Small: handheld, never laggy.
@export_range(0.0, 0.2) var look_smoothing: float = 0.03

@export_group("Push")
## Horizontal force applied to loose rigid bodies the player walks into, N.
@export var push_force: float = 90.0
## How far ahead of the body to feel for props, m.
@export var push_probe: float = 0.06

@onready var _collision: CollisionShape3D = $Collision
@onready var _head: Node3D = $Head
@onready var _camera: CamcorderCamera = $Head/HeadBob/HandheldSway/Camera
@onready var _footsteps: PlayerFootsteps = $Footsteps
@onready var _interactor: PlayerInteractor = $Interactor

var _capsule: CapsuleShape3D

# Look state. _target_* is where input points, _yaw/_pitch follow with inertia.
var _yaw: float = 0.0
var _pitch: float = 0.0
var _target_yaw: float = 0.0
var _target_pitch: float = 0.0
var _look_velocity: Vector2 = Vector2.ZERO  # rad/s (yaw, pitch), for feel layers

# Settings mirrors (applied via Events.setting_changed).
var _mouse_sensitivity: float = 1.0
var _gamepad_sensitivity: float = 1.0
var _invert_y: bool = false
var _toggle_crouch: bool = true

# Crouch.
var _want_crouch: bool = false
var _crouch_blend: float = 0.0  # 0 standing .. 1 crouched

# Camera placement: render-rate interpolation of the physics position plus a
# decaying vertical offset that hides discrete step-ups / step-downs.
var _prev_physics_pos: Vector3 = Vector3.ZERO
var _curr_physics_pos: Vector3 = Vector3.ZERO
var _step_offset: float = 0.0
var _grounded: bool = false

var _gravity_fallback: float = 9.8


func _ready() -> void:
	add_to_group(&"player")
	Game.player = self
	collision_layer = 1 << 1
	collision_mask = (1 << 0) | (1 << 3)
	floor_snap_length = max_step_height + 0.04
	floor_max_angle = deg_to_rad(46.0)
	floor_block_on_wall = true
	floor_constant_speed = true

	# Each player gets its own capsule so crouch never edits a shared resource.
	_capsule = (_collision.shape as CapsuleShape3D).duplicate() as CapsuleShape3D
	_capsule.radius = 0.3
	_capsule.height = stand_height
	_collision.shape = _capsule
	_set_body_height(stand_height)

	_head.top_level = true
	_head.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	_gravity_fallback = float(ProjectSettings.get_setting("physics/3d/default_gravity", 9.8))

	_read_settings()
	Events.setting_changed.connect(_on_setting_changed)
	reset_view()
	if not Game.is_input_locked():
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _exit_tree() -> void:
	if Game.player == self:
		Game.player = null


# --- Public API --------------------------------------------------------------

func get_camera() -> Camera3D:
	return _camera


## Re-read yaw / pitch from the current transform (call after placing the player
## at a spawn). Levels the body, clears velocity and camera smoothing.
func reset_view() -> void:
	var forward := -global_transform.basis.z
	var flat := Vector2(forward.x, forward.z)
	if flat.length_squared() < 0.000001:
		flat = Vector2(0.0, -1.0)
	_yaw = atan2(-flat.x, -flat.y)
	_pitch = clampf(asin(clampf(forward.normalized().y, -1.0, 1.0)), -_pitch_limit(), _pitch_limit())
	_target_yaw = _yaw
	_target_pitch = _pitch
	_look_velocity = Vector2.ZERO
	global_basis = Basis(Vector3.UP, _yaw)
	velocity = Vector3.ZERO
	_prev_physics_pos = global_position
	_curr_physics_pos = global_position
	_step_offset = 0.0
	_place_head()
	if _footsteps:
		_footsteps.reset()


## Place the player at `xform` (position + facing) and reset the view.
func teleport(xform: Transform3D) -> void:
	global_transform = xform
	reset_view()


## Set the view directly (radians). Pitch is clamped.
func set_look(yaw: float, pitch: float, immediate: bool = true) -> void:
	_target_yaw = yaw
	_target_pitch = clampf(pitch, -_pitch_limit(), _pitch_limit())
	if immediate:
		_yaw = _target_yaw
		_pitch = _target_pitch
		global_basis = Basis(Vector3.UP, _yaw)
		_place_head()


func get_yaw() -> float:
	return _yaw


func get_pitch() -> float:
	return _pitch


## Angular look velocity in rad/s (x = yaw, y = pitch).
func get_look_velocity() -> Vector2:
	return _look_velocity


## Horizontal speed over the ground, m/s.
func get_ground_speed() -> float:
	return Vector2(velocity.x, velocity.z).length()


## Velocity in the body's yaw frame: x = right, z = backwards (Godot convention).
func get_local_velocity() -> Vector3:
	return Basis(Vector3.UP, _yaw).inverse() * velocity


## True while standing on something (floor or a stair edge).
func is_grounded() -> bool:
	return _grounded


## True when the player wants to be (or is held) crouched.
func is_crouching() -> bool:
	return _want_crouch or _crouch_blend > 0.5


## 0 standing .. 1 fully crouched (smoothed).
func get_crouch_amount() -> float:
	return _crouch_blend


func get_eye_height() -> float:
	return lerpf(stand_eye_height, crouch_eye_height, _smooth01(_crouch_blend))


## Zoom amount 0 (wide) .. 1 (tele).
func get_zoom_amount() -> float:
	return _camera.zoom_amount if _camera else 0.0


func get_focused_interactable() -> Interactable:
	return _interactor.get_focused() if _interactor else null


## Surface id of whatever is under the feet (&"wood" when unknown).
func get_floor_surface() -> StringName:
	return _footsteps.get_floor_surface() if _footsteps else &"wood"


## Read a Settings value defensively: missing keys or wrong types give `fallback`.
static func read_setting(section: StringName, key: StringName, fallback: Variant) -> Variant:
	var defaults: Dictionary = Settings.DEFAULTS.get(section, {})
	if not defaults.has(key):
		return fallback
	var v: Variant = Settings.get_value(section, key)
	if fallback is float and (v is float or v is int):
		return float(v)
	if typeof(v) == typeof(fallback):
		return v
	return fallback


# --- Input -------------------------------------------------------------------

func _unhandled_input(event: InputEvent) -> void:
	if Game.is_input_locked():
		return
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.pressed and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
			get_viewport().set_input_as_handled()
			return
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		var motion := (event as InputEventMouseMotion).screen_relative
		var k := mouse_radians_per_pixel * _mouse_sensitivity * _look_scale()
		_add_look(-motion.x * k, -motion.y * k * (-1.0 if _invert_y else 1.0))
	elif event.is_action_pressed(&"crouch") and _toggle_crouch:
		_set_want_crouch(not _want_crouch)
	elif event.is_action_pressed(&"sprint") and _toggle_crouch and _want_crouch:
		_set_want_crouch(false)


func _add_look(d_yaw: float, d_pitch: float) -> void:
	_target_yaw += d_yaw
	_target_pitch = clampf(_target_pitch + d_pitch, -_pitch_limit(), _pitch_limit())


func _look_scale() -> float:
	return _camera.get_look_scale() if _camera else 1.0


func _pitch_limit() -> float:
	return deg_to_rad(pitch_limit_degrees)


# --- Per frame: look + camera placement -------------------------------------

func _process(delta: float) -> void:
	if not Game.is_input_locked():
		var stick := Input.get_vector(&"look_left", &"look_right", &"look_up", &"look_down")
		if stick != Vector2.ZERO:
			var mag := pow(minf(stick.length(), 1.0), gamepad_curve)
			var dir := stick.normalized() * mag
			var rate := gamepad_turn_rate * _gamepad_sensitivity * _look_scale() * delta
			_add_look(-dir.x * rate, -dir.y * rate * (-1.0 if _invert_y else 1.0))

	var prev_yaw := _yaw
	var prev_pitch := _pitch
	var t := 1.0 if look_smoothing <= 0.0 else 1.0 - exp(-delta / look_smoothing)
	_yaw = lerpf(_yaw, _target_yaw, t)
	_pitch = lerpf(_pitch, _target_pitch, t)
	if delta > 0.0:
		var lv := Vector2(_yaw - prev_yaw, _pitch - prev_pitch) / delta
		_look_velocity = _look_velocity.lerp(lv, 1.0 - exp(-delta * 20.0))
	# Keep the numbers small over an hour of turning.
	if absf(_yaw) > TAU * 4.0:
		var turns := floorf(_yaw / TAU) * TAU
		_yaw -= turns
		_target_yaw -= turns
	global_basis = Basis(Vector3.UP, _yaw)

	_step_offset *= exp(-delta * step_smoothing)
	if absf(_step_offset) < 0.0005:
		_step_offset = 0.0
	_place_head()


func _place_head() -> void:
	if _head == null:
		return
	var frac := clampf(Engine.get_physics_interpolation_fraction(), 0.0, 1.0)
	var p := _prev_physics_pos.lerp(_curr_physics_pos, frac)
	_head.global_position = p + Vector3(0.0, get_eye_height() + _step_offset, 0.0)
	_head.global_basis = Basis.from_euler(Vector3(_pitch, _yaw, 0.0))


# --- Physics: movement -------------------------------------------------------

func _physics_process(delta: float) -> void:
	var locked := Game.is_input_locked()
	# Something outside moved us (teleport, level placement): don't smooth it.
	if global_position.distance_to(_curr_physics_pos) > 1.0:
		_prev_physics_pos = global_position
		_curr_physics_pos = global_position
		_step_offset = 0.0

	var was_grounded := _grounded
	var y_before := global_position.y

	_update_crouch(delta, locked)

	var wish := _wish_velocity(locked)
	var hv := Vector3(velocity.x, 0.0, velocity.z)
	var rate := deceleration if wish.length_squared() < 0.0001 else acceleration
	if not was_grounded:
		rate *= air_control
	hv = hv.move_toward(wish, rate * delta)
	velocity.x = hv.x
	velocity.z = hv.z

	if was_grounded:
		velocity.y = 0.0
	else:
		velocity += _gravity_vector() * delta

	_push_props(wish, delta)
	var stepped := false
	if was_grounded and hv.length_squared() > 0.0025:
		stepped = _try_step_up(hv * delta)

	move_and_slide()

	_grounded = is_on_floor()
	if not _grounded and was_grounded and velocity.y <= 0.0:
		_grounded = _stick_down()
	if _grounded and velocity.y > 0.0:
		velocity.y = 0.0  # never launch off a step top or a ramp crest

	# Hide discrete vertical jumps (steps) from the camera.
	var dy := global_position.y - y_before
	var step_dy := 0.0
	if was_grounded and _grounded and (stepped or absf(dy) > 0.035):
		step_dy = dy
		_step_offset = clampf(_step_offset - dy, -step_smoothing_max, step_smoothing_max)

	# The step is carried by _step_offset, so take it out of the interpolation.
	_prev_physics_pos = _curr_physics_pos + Vector3(0.0, step_dy, 0.0)
	_curr_physics_pos = global_position


func _gravity_vector() -> Vector3:
	var g := get_gravity()
	if g == Vector3.ZERO:
		g = Vector3.DOWN * _gravity_fallback
	return g


func _wish_velocity(locked: bool) -> Vector3:
	if locked:
		return Vector3.ZERO
	var input := Input.get_vector(&"move_left", &"move_right", &"move_forward", &"move_back")
	if input == Vector2.ZERO:
		return Vector3.ZERO
	var local := Vector3(input.x * strafe_multiplier, 0.0, input.y)
	if input.y > 0.0:
		local.z *= backward_multiplier
	if local.length() > 1.0:
		local = local.normalized()
	var speed := walk_speed
	var crouch_t := _smooth01(_crouch_blend)
	if crouch_t > 0.01:
		speed = lerpf(walk_speed, crouch_speed, crouch_t)
	elif Input.is_action_pressed(&"sprint") and input.y < -0.3:
		speed = hurry_speed
	return Basis(Vector3.UP, _yaw) * (local * speed)


## Lift the body onto a step it is walking into. Returns true when it did.
func _try_step_up(motion: Vector3) -> bool:
	var from := global_transform
	var hit := KinematicCollision3D.new()
	if not test_move(from, motion, hit, safe_margin, false, 4):
		return false
	var blocked := false
	for i in hit.get_collision_count():
		var n := hit.get_normal(i)
		if n.angle_to(up_direction) <= floor_max_angle:
			continue  # a slope or the floor: move_and_slide handles it
		if hit.get_collider(i) is RigidBody3D:
			return false  # push props, don't climb them
		blocked = true
	if not blocked:
		return false

	# How far up is free?
	var lift := max_step_height + 0.03
	var up_hit := KinematicCollision3D.new()
	if test_move(from, Vector3.UP * lift, up_hit):
		lift = up_hit.get_travel().y
	if lift < 0.03:
		return false
	var raised := from
	raised.origin.y += lift

	# Forward from the raised position must be (mostly) free.
	var fwd_hit := KinematicCollision3D.new()
	var probe := motion
	if test_move(raised, probe, fwd_hit):
		if fwd_hit.get_travel().length() < 0.005:
			return false
		probe = fwd_hit.get_travel()
	raised.origin += probe

	# Then down onto the tread.
	var down_hit := KinematicCollision3D.new()
	if not test_move(raised, Vector3.DOWN * lift, down_hit):
		return false
	if down_hit.get_collider() is RigidBody3D:
		return false
	var rise := down_hit.get_position().y - from.origin.y
	if rise < 0.02 or rise > max_step_height + 0.005 or rise + 0.005 > lift:
		return false
	global_position.y = from.origin.y + rise + 0.005
	velocity.y = 0.0
	return true


## Walking off a step: glue the body to the tread below if it is within a step.
func _stick_down() -> bool:
	var hit := KinematicCollision3D.new()
	if not test_move(global_transform, Vector3.DOWN * (max_step_height + 0.04), hit):
		return false
	if hit.get_collider() is RigidBody3D:
		return false
	global_position += hit.get_travel()
	velocity.y = 0.0
	apply_floor_snap()
	return true


## Lean on loose rigid bodies the player is walking into. Probed along the
## intended motion before the slide, because once the body is blocked it is
## only touching the prop on some ticks.
func _push_props(wish: Vector3, delta: float) -> void:
	var speed := wish.length()
	if speed < 0.05 or push_force <= 0.0:
		return
	var dir := wish / speed
	var hit := KinematicCollision3D.new()
	if not test_move(global_transform, dir * (speed * delta + push_probe), hit, safe_margin, false, 4):
		return
	var pushed: Array[RigidBody3D] = []
	for i in hit.get_collision_count():
		var rb := hit.get_collider(i) as RigidBody3D
		if rb == null or rb.freeze or rb in pushed:
			continue
		var n := -hit.get_normal(i)
		n.y = 0.0
		if n.length_squared() < 0.0001:
			continue
		var push_dir := n.normalized()
		var facing := push_dir.dot(dir)
		if facing <= 0.2 or rb.linear_velocity.dot(push_dir) >= speed * facing:
			continue
		pushed.append(rb)
		var strength := clampf(speed / walk_speed, 0.0, 1.5) * facing
		rb.apply_central_impulse(push_dir * push_force * strength * delta)


# --- Crouch ------------------------------------------------------------------

func _update_crouch(delta: float, locked: bool) -> void:
	if not locked and not _toggle_crouch:
		var held := Input.is_action_pressed(&"crouch")
		if held != _want_crouch:
			_set_want_crouch(held)
	var target := 1.0 if _want_crouch else 0.0
	if is_equal_approx(_crouch_blend, target):
		return
	var step := delta / maxf(crouch_transition_time, 0.01)
	var next := move_toward(_crouch_blend, target, step)
	var next_height := lerpf(stand_height, crouch_height, _smooth01(next))
	if next < _crouch_blend and not _has_headroom(next_height):
		return  # something overhead: stay down until there is room
	_crouch_blend = next
	_set_body_height(next_height)


func _set_want_crouch(value: bool) -> void:
	if value == _want_crouch:
		return
	_want_crouch = value
	crouch_changed.emit(value)


func _set_body_height(h: float) -> void:
	_capsule.height = h
	_collision.position = Vector3(0.0, h * 0.5, 0.0)


## True when a capsule of height `h` fits at the current position.
func _has_headroom(h: float) -> bool:
	var space := get_world_3d().direct_space_state
	var probe := CapsuleShape3D.new()
	probe.radius = _capsule.radius - 0.02
	probe.height = h - 0.04
	var q := PhysicsShapeQueryParameters3D.new()
	q.shape = probe
	q.transform = Transform3D(Basis.IDENTITY, global_position + Vector3(0.0, h * 0.5 + 0.02, 0.0))
	q.collision_mask = collision_mask
	q.exclude = [get_rid()]
	return space.intersect_shape(q, 1).is_empty()


# --- Settings ----------------------------------------------------------------

func _read_settings() -> void:
	_mouse_sensitivity = read_setting(&"controls", &"mouse_sensitivity", 1.0)
	_gamepad_sensitivity = read_setting(&"controls", &"gamepad_sensitivity", 1.0)
	_invert_y = read_setting(&"controls", &"invert_y", false)
	_toggle_crouch = read_setting(&"controls", &"toggle_crouch", true)


func _on_setting_changed(section: StringName, _key: StringName, _value: Variant) -> void:
	if section == &"controls":
		_read_settings()


static func _smooth01(x: float) -> float:
	return smoothstep(0.0, 1.0, x)
