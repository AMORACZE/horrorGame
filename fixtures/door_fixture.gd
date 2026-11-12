class_name DoorFixture
extends Node3D
## Root of a door scene (door_interior.tscn, door_front.tscn). Exposes the
## door's level-facing state on the instance root so a level can set it without
## editable children. Values are pushed to the DoorInteractable in _enter_tree,
## before the door's own _ready reads them.
##
## Convention: origin at floor level, centred in the opening and in the wall's
## thickness. Hinges on local -X. A positive open angle swings the slab into
## local -Z.

@export_group("State")
@export var start_state: DoorInteractable.StartState = DoorInteractable.StartState.CLOSED
@export var locked: bool = false
## Unlocks when Game.has_flag(required_flag) at the moment it is tried.
@export var required_flag: StringName = &""
## Set the first time the door is opened.
@export var opened_flag: StringName = &""
@export var opens_away_from_player: bool = false
@export_range(-180.0, 180.0, 0.5, "suffix:°") var open_angle_degrees: float = 95.0

@export_group("Text")
@export var display_name: String = "Door"
## Empty = keep the scene's lines.
@export var observations: Array[String] = []
@export var locked_observations: Array[String] = []

@export_group("Wiring")
@export var door_path: NodePath = ^"Slab/Door"


var _pushed: bool = false


func _enter_tree() -> void:
	if _pushed:
		return
	_pushed = true
	var door := get_door()
	if door == null:
		push_warning("%s: no DoorInteractable at %s" % [name, door_path])
		return
	door.start_state = start_state
	door.locked = locked
	door.required_flag = required_flag
	door.opened_flag = opened_flag
	door.opens_away_from_player = opens_away_from_player
	door.open_angle_degrees = open_angle_degrees
	door.display_name = display_name
	if not observations.is_empty():
		door.observations = observations
	if not locked_observations.is_empty():
		door.locked_observations = locked_observations


func get_door() -> DoorInteractable:
	return get_node_or_null(door_path) as DoorInteractable
