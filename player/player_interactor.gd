class_name PlayerInteractor
extends Node
## The reticle: a ray from the camcorder lens that finds what the player is
## looking at, keeps the focused Interactable up to date every physics frame
## and uses it on the "interact" action.
##
## Contract (docs/ARCHITECTURE.md §5): reach 2.0 m from the camera, mask
## layers 1 + 3 + 4 so walls occlude, focus()/unfocus() on change,
## Events.interaction_focus_changed(interactable or null), interact(player).

@export_group("Reach")
## How far the hand reaches from the camera, m.
@export var reach: float = 2.0
## Layers the ray sees: world (occluders), interactable, physics props.
@export_flags_3d_physics var ray_mask: int = (1 << 0) | (1 << 2) | (1 << 3)
@export var collide_with_areas: bool = true

@export_group("Input")
## Ignore "interact" for this long after input unlocks, so the press that
## closed a modal UI does not immediately reopen something, s.
@export var unlock_grace: float = 0.15

var _player: Player
var _focused: Interactable = null
var _unlock_time_ms: int = -100000


func _ready() -> void:
	_player = get_parent() as Player
	Events.input_lock_changed.connect(_on_input_lock_changed)


func _exit_tree() -> void:
	_set_focus(null)


func get_focused() -> Interactable:
	return _focused if is_instance_valid(_focused) else null


func _physics_process(_delta: float) -> void:
	if not is_instance_valid(_focused) and _focused != null:
		_focused = null
		Events.interaction_focus_changed.emit(null)
	if Game.is_input_locked():
		return
	_set_focus(_probe())


func _unhandled_input(event: InputEvent) -> void:
	if not event.is_action_pressed(&"interact"):
		return
	if Game.is_input_locked():
		return
	if event is InputEventMouseButton and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		return  # this click is for capturing the mouse (handled by Player)
	if Time.get_ticks_msec() - _unlock_time_ms < int(unlock_grace * 1000.0):
		return
	_set_focus(_probe())
	var target := get_focused()
	if target == null:
		return
	get_viewport().set_input_as_handled()
	target.interact(_player)


## What is under the reticle right now (or null).
func _probe() -> Interactable:
	var cam := _player.get_camera() if _player else null
	if cam == null or not cam.is_inside_tree():
		return null
	var origin := cam.global_position
	var dir := -cam.global_basis.z
	var q := PhysicsRayQueryParameters3D.create(origin, origin + dir * reach, ray_mask, [_player.get_rid()])
	q.collide_with_areas = collide_with_areas
	var hit := _player.get_world_3d().direct_space_state.intersect_ray(q)
	if hit.is_empty():
		return null
	return Interactable.find_for(hit.get("collider"))


func _set_focus(target: Interactable) -> void:
	if target == _focused:
		return
	if is_instance_valid(_focused):
		_focused.unfocus(_player)
	_focused = target
	if _focused:
		_focused.focus(_player)
	Events.interaction_focus_changed.emit(_focused)


func _on_input_lock_changed(locked: bool) -> void:
	if not locked:
		_unlock_time_ms = Time.get_ticks_msec()
