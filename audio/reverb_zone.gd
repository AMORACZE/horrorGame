@tool
class_name ReverbZone
extends Area3D
## A room's acoustics. While the player (group "player") is inside, the World bus
## room reverb blends to this zone's settings; leaving blends back. Overlapping
## zones: the most recently entered wins. Lives on physics layer 5 (triggers)
## and only watches layer 2 (player).
##
## Size the box with `size`, or replace the CollisionShape3D for odd rooms.

enum Preset { LIVING_ROOM, BEDROOM, KITCHEN, BATHROOM, HALLWAY, CLOSET, GARAGE, BASEMENT, STAIRWELL, CUSTOM }

## Typical domestic rooms. Values are AudioEffectReverb parameters.
const PRESETS := {
	Preset.LIVING_ROOM: {&"room_size": 0.32, &"damping": 0.72, &"wet": 0.09, &"predelay_msec": 10.0},
	Preset.BEDROOM: {&"room_size": 0.26, &"damping": 0.8, &"wet": 0.07, &"predelay_msec": 8.0},
	Preset.KITCHEN: {&"room_size": 0.34, &"damping": 0.42, &"wet": 0.14, &"predelay_msec": 9.0},
	Preset.BATHROOM: {&"room_size": 0.28, &"damping": 0.18, &"wet": 0.24, &"predelay_msec": 5.0},
	Preset.HALLWAY: {&"room_size": 0.4, &"damping": 0.5, &"wet": 0.15, &"predelay_msec": 12.0},
	Preset.CLOSET: {&"room_size": 0.12, &"damping": 0.92, &"wet": 0.04, &"predelay_msec": 3.0},
	Preset.GARAGE: {&"room_size": 0.6, &"damping": 0.3, &"wet": 0.26, &"predelay_msec": 18.0},
	Preset.BASEMENT: {&"room_size": 0.52, &"damping": 0.38, &"wet": 0.22, &"predelay_msec": 14.0},
	Preset.STAIRWELL: {&"room_size": 0.5, &"damping": 0.45, &"wet": 0.2, &"predelay_msec": 15.0},
}

@export var preset: Preset = Preset.LIVING_ROOM
@export var size: Vector3 = Vector3(4.0, 2.44, 4.0):
	set(v):
		size = v
		_update_shape()

@export_group("Custom (preset = CUSTOM)")
@export_range(0.0, 1.0, 0.01) var room_size: float = 0.32
@export_range(0.0, 1.0, 0.01) var damping: float = 0.7
@export_range(0.0, 0.5, 0.01) var wet: float = 0.1
@export_range(0.0, 50.0, 0.5, "suffix:ms") var predelay_msec: float = 10.0

const LAYER_TRIGGERS := 1 << 4  # layer 5
const MASK_PLAYER := 1 << 1     # layer 2


func _ready() -> void:
	collision_layer = LAYER_TRIGGERS
	collision_mask = MASK_PLAYER
	monitorable = false
	monitoring = true
	_update_shape()
	if Engine.is_editor_hint():
		return
	body_entered.connect(_on_body_entered)
	body_exited.connect(_on_body_exited)


func get_params() -> Dictionary:
	if preset == Preset.CUSTOM:
		return {&"room_size": room_size, &"damping": damping, &"wet": wet, &"predelay_msec": predelay_msec}
	return (PRESETS[preset] as Dictionary).duplicate()


func _on_body_entered(body: Node3D) -> void:
	if body.is_in_group(&"player"):
		Audio.enter_reverb_zone(self, get_params())


func _on_body_exited(body: Node3D) -> void:
	if body.is_in_group(&"player"):
		Audio.exit_reverb_zone(self)


func _exit_tree() -> void:
	if not Engine.is_editor_hint() and is_instance_valid(Audio):
		Audio.exit_reverb_zone(self)


func _update_shape() -> void:
	if not is_inside_tree():
		return
	var cs := get_node_or_null(^"CollisionShape3D") as CollisionShape3D
	if cs == null:
		return
	var box := cs.shape as BoxShape3D
	if box == null:
		return  # a custom shape was set: leave it alone
	if not box.resource_local_to_scene:
		box = box.duplicate() as BoxShape3D
		box.resource_local_to_scene = true
		cs.shape = box
	box.size = size
