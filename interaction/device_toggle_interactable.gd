class_name DeviceToggleInteractable
extends Interactable
## An appliance with an on/off control: TV power button, faucet handle,
## radio knob, a telephone's receiver (lifted = on).
##
## On/off shows and hides nodes, drives Switchable targets (screen glow, dial
## lamp), runs an optional loop on its own AudioStreamPlayer3D, and can move a
## control part (a handle turning, a hook switch popping up).

signal toggled(on: bool)

@export_group("Device")
@export var start_on: bool = false
@export var on_prompt: String = "Turn on"
@export var off_prompt: String = "Turn off"
@export_range(0.0, 2.0, 0.01, "suffix:s") var cooldown: float = 0.3

@export_group("Drives")
## Switchables set to match the device state.
@export var targets: Array[NodePath] = []
## Nodes visible only while on / only while off.
@export var show_when_on: Array[NodePath] = []
@export var show_when_off: Array[NodePath] = []

@export_group("Control Motion")
## Part that moves between off and on poses (handle, knob, hook). Optional.
@export var moving_part: NodePath
@export var on_offset: Vector3 = Vector3.ZERO
@export var on_rotation_degrees: Vector3 = Vector3.ZERO
@export_range(0.01, 2.0, 0.01, "suffix:s") var move_time: float = 0.15

@export_group("Sound")
@export var on_sound: StringName = &"button_press"
@export var off_sound: StringName = &"button_press"
## Loop while on (tv_static, faucet_run, phone_dial_tone, tape_hiss). Empty = none.
@export var loop_sound: StringName = &""
@export var loop_volume_db: float = -8.0
@export_range(0.1, 20.0, 0.1) var loop_unit_size: float = 2.0
## Where the loop plays from. Empty = the parent body.
@export var loop_anchor: NodePath
@export_range(0.0, 2.0, 0.01, "suffix:s") var loop_delay: float = 0.0
@export var sound_volume_db: float = 0.0

var _on: bool = false
var _last_use_ms: int = -100000
var _fresh_index: int = 0
var _loop: AudioStreamPlayer3D = null
var _part: Node3D = null
var _part_rest_pos: Vector3 = Vector3.ZERO
var _part_rest_rot: Vector3 = Vector3.ZERO
var _tween: Tween = null
var _loop_serial: int = 0


func _ready() -> void:
	_on = start_on
	_part = get_node_or_null(moving_part) as Node3D
	if _part:
		_part_rest_pos = _part.position
		_part_rest_rot = _part.rotation_degrees
	if loop_sound != &"":
		var anchor := get_node_or_null(loop_anchor) as Node3D if not loop_anchor.is_empty() else get_parent() as Node3D
		if anchor:
			_loop = LoopEmitter.create_player(anchor, loop_sound, loop_volume_db, loop_unit_size)
	_apply(true)
	_push_targets.call_deferred(true)


func is_on() -> bool:
	return _on


func get_prompt() -> String:
	return off_prompt if _on else on_prompt


func can_interact(interactor: Node) -> bool:
	return super.can_interact(interactor) and Time.get_ticks_msec() - _last_use_ms >= int(cooldown * 1000.0)


## The loop player, or null if this device has no loop.
func get_loop_player() -> AudioStreamPlayer3D:
	return _loop


## Whether the loop is meant to be running (true even when no stream exists yet).
func is_loop_active() -> bool:
	return LoopEmitter.is_wanted(_loop)


func set_on(on: bool) -> void:
	if on != _on:
		_toggle()


func _interact(_interactor: Node) -> void:
	_last_use_ms = Time.get_ticks_msec()
	_toggle()


func _toggle() -> void:
	_on = not _on
	var body := get_parent() as Node3D
	if body and body.is_inside_tree():
		Audio.play_attached(on_sound if _on else off_sound, body, sound_volume_db, randf_range(0.97, 1.03))
	_apply(false)
	_push_targets(false)
	toggled.emit(_on)
	if _on and _fresh_index < observations.size():
		var line := observations[_fresh_index]
		_fresh_index += 1
		if line.strip_edges() != "":
			say(line)


func _push_targets(instant: bool) -> void:
	for p in targets:
		var s := Switchable.resolve(get_node_or_null(p))
		if s:
			s.set_on(_on, instant)


func _apply(instant: bool) -> void:
	for p in show_when_on:
		var n := get_node_or_null(p) as Node3D
		if n:
			n.visible = _on
	for p in show_when_off:
		var n := get_node_or_null(p) as Node3D
		if n:
			n.visible = not _on
	if _loop:
		_loop_serial += 1
		if _on and loop_delay > 0.0 and not instant and is_inside_tree():
			var serial := _loop_serial
			LoopEmitter.set_playing(_loop, false)
			_loop.set_meta(&"loop_wanted", true)
			get_tree().create_timer(loop_delay).timeout.connect(func() -> void:
				if serial == _loop_serial and _on and is_instance_valid(_loop):
					LoopEmitter.set_playing(_loop, true))
		else:
			LoopEmitter.set_playing(_loop, _on)
	if _part:
		var pos := _part_rest_pos + (on_offset if _on else Vector3.ZERO)
		var rot := _part_rest_rot + (on_rotation_degrees if _on else Vector3.ZERO)
		if _tween:
			_tween.kill()
		if instant or not is_inside_tree():
			_part.position = pos
			_part.rotation_degrees = rot
		else:
			_tween = create_tween().set_parallel(true).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
			_tween.tween_property(_part, "position", pos, move_time)
			_tween.tween_property(_part, "rotation_degrees", rot, move_time)
