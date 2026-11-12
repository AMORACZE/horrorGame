class_name PlayerFootsteps
extends Node
## Stride tracker for the player. Emits footsteps by distance walked, not by
## time, so the sound always matches the ground covered, and exposes the
## stride phase so the head bob stays in step with the sound.
##
## Surface ids come from metadata `surface` on the floor collider (or the
## first ancestor that has it), overridden by an Area3D on the triggers layer
## carrying `surface` metadata (a rug zone, say). Default: &"wood".
## Emits Events.player_footstep and Events.player_landed. Plays no audio.

## A footfall happened (for the camera rig and other player-local listeners).
signal stepped(surface: StringName, intensity: float)
## The player came down after being airborne. `impact` 0..1.
signal landed(impact: float)

const DEFAULT_SURFACE := &"wood"

@export_group("Stride")
## Distance per footstep at crouch / walk / hurry speed, m.
@export var stride_crouch: float = 0.55
@export var stride_walk: float = 0.8
@export var stride_hurry: float = 1.05
## Below this speed no new strides start, m/s.
@export var min_speed: float = 0.25
## When the player stops part-way through a stride (more than this fraction),
## the trailing foot comes down with a softer step.
@export_range(0.0, 1.0) var settle_step_threshold: float = 0.4

@export_group("Intensity")
@export var crouch_intensity: float = 0.4
@export var walk_intensity: float = 0.7
@export var hurry_intensity: float = 1.0
@export var settle_intensity_scale: float = 0.55

@export_group("Landing")
## Minimum airborne time before a landing counts, s.
@export var landing_min_air_time: float = 0.18
## Fall speed giving impact 0 / impact 1, m/s.
@export var landing_speed_soft: float = 1.2
@export var landing_speed_hard: float = 6.0

@export_group("Surface Probe")
## Collision mask for the floor probe ray (world + physics props).
@export_flags_3d_physics var floor_mask: int = (1 << 0) | (1 << 3)
## Collision mask for surface override areas (triggers).
@export_flags_3d_physics var zone_mask: int = 1 << 4

## Steps taken, fractional. A footfall happens each time it crosses an integer.
var stride_phase: float = 0.55

var _player: Player
var _phase_rate: float = 0.0  # phase per second, for render-rate extrapolation
var _air_time: float = 0.0
var _fall_speed: float = 0.0
var _was_grounded: bool = true
var _still_time: float = 0.0
var _settled: bool = true
# Stride re-arm after stopping: 0 done, 1 pending, 2 pending after a settle step.
var _rearm: int = 0
var _surface: StringName = DEFAULT_SURFACE


func _ready() -> void:
	_player = get_parent() as Player


func reset() -> void:
	stride_phase = 0.55
	_phase_rate = 0.0
	_air_time = 0.0
	_fall_speed = 0.0
	_was_grounded = true
	_still_time = 0.0
	_settled = true
	_rearm = 0


## Phase for rendering: the physics phase extrapolated by the interpolation fraction.
func get_visual_phase() -> float:
	var dt := 1.0 / float(Engine.physics_ticks_per_second)
	return stride_phase + _phase_rate * Engine.get_physics_interpolation_fraction() * dt


func get_floor_surface() -> StringName:
	return _surface


func _physics_process(delta: float) -> void:
	if _player == null:
		return
	var grounded := _player.is_grounded()

	if not grounded:
		_air_time += delta
		_fall_speed = maxf(_fall_speed, -_player.velocity.y)
		_phase_rate = 0.0
		_was_grounded = false
		return

	if not _was_grounded:
		_was_grounded = true
		if _air_time >= landing_min_air_time or _fall_speed >= landing_speed_soft:
			_surface = _probe_surface()
			var impact := clampf(inverse_lerp(landing_speed_soft, landing_speed_hard, _fall_speed), 0.0, 1.0)
			Events.player_landed.emit(_surface, _player.global_position, impact)
			landed.emit(impact)
			stride_phase = floorf(stride_phase) + 0.5  # next foot after half a stride
		_air_time = 0.0
		_fall_speed = 0.0

	var speed := _player.get_ground_speed()
	if speed < min_speed:
		_phase_rate = 0.0
		_still_time += delta
		if _still_time > 0.12 and not _settled:
			_settled = true
			if stride_phase - floorf(stride_phase) > settle_step_threshold:
				# The trailing foot comes down as the body settles.
				_footfall(speed, settle_intensity_scale)
				_rearm = 2
		if _still_time > 0.6 and _rearm != 0:
			# Once the bob has faded, re-arm so the first step after starting
			# again comes after about half a stride (no visible phase jump).
			stride_phase = floorf(stride_phase) + (1.55 if _rearm == 2 else 0.55)
			_rearm = 0
		return

	_still_time = 0.0
	_settled = false
	_rearm = 1
	_phase_rate = speed / _stride_length(speed)
	var before := floorf(stride_phase)
	stride_phase += _phase_rate * delta
	if floorf(stride_phase) > before:
		_footfall(speed, 1.0)


func _footfall(speed: float, scale: float) -> void:
	_surface = _probe_surface()
	var intensity := clampf(_intensity(speed) * scale, 0.05, 1.0)
	Events.player_footstep.emit(_surface, _player.global_position, intensity)
	stepped.emit(_surface, intensity)


func _stride_length(speed: float) -> float:
	if speed <= _player.walk_speed:
		var t := inverse_lerp(_player.crouch_speed, _player.walk_speed, speed)
		return lerpf(stride_crouch, stride_walk, clampf(t, 0.0, 1.0))
	var u := inverse_lerp(_player.walk_speed, _player.hurry_speed, speed)
	return lerpf(stride_walk, stride_hurry, clampf(u, 0.0, 1.0))


func _intensity(speed: float) -> float:
	if _player.get_crouch_amount() > 0.5:
		return crouch_intensity
	if speed <= _player.walk_speed:
		var t := inverse_lerp(_player.crouch_speed, _player.walk_speed, speed)
		return lerpf(crouch_intensity, walk_intensity, clampf(t, 0.0, 1.0))
	var u := inverse_lerp(_player.walk_speed, _player.hurry_speed, speed)
	return lerpf(walk_intensity, hurry_intensity, clampf(u, 0.0, 1.0))


func _probe_surface() -> StringName:
	var space := _player.get_world_3d().direct_space_state
	var feet := _player.global_position

	if zone_mask != 0:
		var pq := PhysicsPointQueryParameters3D.new()
		pq.position = feet + Vector3(0.0, 0.05, 0.0)
		pq.collision_mask = zone_mask
		pq.collide_with_areas = true
		pq.collide_with_bodies = false
		for hit: Dictionary in space.intersect_point(pq, 8):
			var zone := _surface_of(hit.get("collider") as Node)
			if zone != &"":
				return zone

	var rq := PhysicsRayQueryParameters3D.create(feet + Vector3(0.0, 0.3, 0.0), feet + Vector3(0.0, -0.35, 0.0), floor_mask, [_player.get_rid()])
	var ray := space.intersect_ray(rq)
	if ray.is_empty():
		return _surface if _surface != &"" else DEFAULT_SURFACE
	var s := _surface_of(ray.get("collider") as Node)
	return s if s != &"" else DEFAULT_SURFACE


## The `surface` metadata on `node` or its nearest ancestor, or &"" if none.
static func _surface_of(node: Node) -> StringName:
	while node != null:
		if node.has_meta(&"surface"):
			return StringName(str(node.get_meta(&"surface")))
		node = node.get_parent()
	return &""
