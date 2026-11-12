class_name SwitchInteractable
extends Interactable
## A switch: wall toggle, lamp knob, pull chain. Drives Switchable targets.
##
## Modes:
## - SET (wall switch): the switch has its own position; using it flips that
##   position and sets every target to match. Targets are synced on load.
## - TOGGLE (a lamp's own switch, a pull chain): no state of its own; flips the
##   first target and makes the others follow it. Its prompt follows the target,
##   so a wall switch and the lamp switch never disagree about what you see.
##
## Targets are NodePaths to a Switchable or a node with a Switchable child.

signal toggled(on: bool)

enum Mode { SET, TOGGLE }

@export_group("Switch")
@export var targets: Array[NodePath] = []
@export var mode: Mode = Mode.SET
## SET mode: the switch position at start.
@export var start_on: bool = false
@export var on_prompt: String = "Switch on"
@export var off_prompt: String = "Switch off"
## Minimum time between uses (a switch has a throw).
@export_range(0.0, 1.0, 0.01, "suffix:s") var cooldown: float = 0.12

@export_group("Lever")
## Visual part that flips (toggle bat, knob). Optional.
@export var lever: NodePath
@export var lever_on_rotation_degrees: Vector3 = Vector3(-14.0, 0.0, 0.0)
@export var lever_off_rotation_degrees: Vector3 = Vector3(14.0, 0.0, 0.0)
## Extra lever offset while on (pull chain pulled), applied briefly on each use.
@export var lever_tug_offset: Vector3 = Vector3.ZERO
@export_range(0.01, 0.5, 0.01, "suffix:s") var lever_time: float = 0.05

@export_group("Sound")
@export var on_sound: StringName = &"switch_on"
@export var off_sound: StringName = &"switch_off"
@export var sound_volume_db: float = 0.0

var _on: bool = false
var _last_use_ms: int = -100000
var _fresh_index: int = 0
var _lever: Node3D = null
var _lever_rest: Vector3 = Vector3.ZERO
var _tween: Tween = null


func _ready() -> void:
	_on = start_on
	_lever = get_node_or_null(lever) as Node3D
	if _lever:
		_lever_rest = _lever.position
	_pose_lever(true)
	if mode == Mode.SET:
		_push_to_targets.call_deferred(true)


func is_on() -> bool:
	if mode == Mode.TOGGLE:
		var t := _first_target()
		return t.is_on() if t else _on
	return _on


func get_prompt() -> String:
	return off_prompt if is_on() else on_prompt


func can_interact(interactor: Node) -> bool:
	return super.can_interact(interactor) and Time.get_ticks_msec() - _last_use_ms >= int(cooldown * 1000.0)


## Flip the switch as if used, without an interactor (tests, scripted setup).
func set_on(on: bool) -> void:
	if is_on() != on:
		_flip()


func _interact(_interactor: Node) -> void:
	_last_use_ms = Time.get_ticks_msec()
	_flip()


func _flip() -> void:
	var on := not is_on()
	_on = on
	_push_to_targets(false)
	_pose_lever(false)
	var body := get_parent() as Node3D
	if body and body.is_inside_tree():
		Audio.play_attached(on_sound if on else off_sound, body, sound_volume_db, randf_range(0.97, 1.03))
	toggled.emit(on)
	var failure := ""
	if on:
		for p in targets:
			var s := Switchable.resolve(get_node_or_null(p))
			if s and not s.is_working():
				failure = s.get_failure_line()
				break
	if failure != "":
		say(failure)
	elif _fresh_index < observations.size():
		var line := observations[_fresh_index]
		_fresh_index += 1
		if line.strip_edges() != "":
			say(line)


func _push_to_targets(instant: bool) -> void:
	for p in targets:
		var s := Switchable.resolve(get_node_or_null(p))
		if s:
			s.set_on(_on, instant)
		elif not instant:
			push_warning("%s: target %s is not Switchable" % [get_path(), p])


func _first_target() -> Switchable:
	for p in targets:
		var s := Switchable.resolve(get_node_or_null(p))
		if s:
			return s
	return null


func get_switchables() -> Array[Switchable]:
	var out: Array[Switchable] = []
	for p in targets:
		var s := Switchable.resolve(get_node_or_null(p))
		if s:
			out.append(s)
	return out


func _pose_lever(instant: bool) -> void:
	if _lever == null:
		return
	var rot := lever_on_rotation_degrees if is_on() else lever_off_rotation_degrees
	if _tween:
		_tween.kill()
	if instant:
		_lever.rotation_degrees = rot
		_lever.position = _lever_rest
		return
	_tween = create_tween()
	_tween.tween_property(_lever, "rotation_degrees", rot, lever_time).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	if lever_tug_offset != Vector3.ZERO:
		_tween.parallel().tween_property(_lever, "position", _lever_rest + lever_tug_offset, 0.08)
		_tween.tween_property(_lever, "position", _lever_rest, 0.25).set_trans(Tween.TRANS_SINE)
