@tool
class_name RandomOneshotEmitter
extends Node3D
## Ambient texture: plays ids from a list at random intervals from random points
## inside a box or sphere around this node. The house ticking as it heats, a dog
## a few streets away, a car going by. Texture only: keep gaps long and levels low,
## never use it to make the player jump.

enum Area { BOX, SPHERE }

@export var sound_ids: Array[StringName] = [&"house_settle"]
@export var enabled: bool = true

@export_group("Timing")
@export_range(0.5, 600.0, 0.5, "suffix:s") var min_gap: float = 12.0
@export_range(0.5, 600.0, 0.5, "suffix:s") var max_gap: float = 45.0
## The first sound waits a random time up to this long (on top of min_gap/2).
@export_range(0.0, 600.0, 0.5, "suffix:s") var initial_delay_max: float = 20.0
## Never play the same id twice in a row (when the list has more than one).
@export var avoid_repeat: bool = true

@export_group("Level")
@export_range(-40.0, 12.0, 0.5, "suffix:dB") var volume_min_db: float = -6.0
@export_range(-40.0, 12.0, 0.5, "suffix:dB") var volume_max_db: float = 0.0

@export_group("Area")
@export var area: Area = Area.BOX:
	set(v):
		area = v
		update_gizmos()
@export var box_size: Vector3 = Vector3(8.0, 2.4, 8.0):
	set(v):
		box_size = v
		update_gizmos()
@export_range(0.0, 200.0, 0.5, "suffix:m") var radius: float = 6.0:
	set(v):
		radius = v
		update_gizmos()

var _timer: float = 0.0
var _last_id: StringName = &""


func _ready() -> void:
	if Engine.is_editor_hint():
		return
	_timer = min_gap * 0.5 + randf() * initial_delay_max


func _process(delta: float) -> void:
	if Engine.is_editor_hint() or not enabled or sound_ids.is_empty():
		return
	_timer -= delta
	if _timer > 0.0:
		return
	_timer = randf_range(min_gap, maxf(min_gap, max_gap))
	trigger()


## Play one sound now (the sandbox and tests use this). Returns the player or null.
func trigger() -> AudioStreamPlayer3D:
	if sound_ids.is_empty():
		return null
	var id := sound_ids[randi() % sound_ids.size()]
	if avoid_repeat and sound_ids.size() > 1:
		while id == _last_id:
			id = sound_ids[randi() % sound_ids.size()]
	_last_id = id
	var vol := randf_range(minf(volume_min_db, volume_max_db), maxf(volume_min_db, volume_max_db))
	return Audio.play_at(id, random_point(), vol)


## A random point in the emitter's area, in global space.
func random_point() -> Vector3:
	var local := Vector3.ZERO
	if area == Area.BOX:
		local = Vector3(randf() - 0.5, randf() - 0.5, randf() - 0.5) * box_size
	else:
		# uniform in the ball
		var dir := Vector3(randfn(0.0, 1.0), randfn(0.0, 1.0), randfn(0.0, 1.0)).normalized()
		local = dir * radius * pow(randf(), 1.0 / 3.0)
	return global_transform * local
