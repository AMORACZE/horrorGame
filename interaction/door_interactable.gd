class_name DoorInteractable
extends HingedPartInteractable
## A hinged house door on an AnimatableBody3D.
##
## Scene shape: the slab body's origin sits on the hinge line (or set `pivot`),
## the slab extends along the body's local +X, and the Interactable is a child
## of the body. The closed pose is the body's transform in the scene.
##
## Adds to HingedPartInteractable: start state (closed / ajar / open), swinging
## away from whoever opens it, a chance of a creak mid-swing, and door sounds.
## Lock, `required_flag` and `opened_flag` come from MovingPartInteractable.

enum StartState { CLOSED, AJAR, OPEN }

@export_group("Door")
@export var start_state: StartState = StartState.CLOSED:
	set(value):
		start_state = value
		_apply_start_state()
## Travel used for AJAR, as a fraction of the open angle.
@export_range(0.02, 0.6, 0.01) var ajar_amount: float = 0.14
## Pick the swing direction each time so the door moves away from the player.
@export var opens_away_from_player: bool = false

@export_group("Door Sound")
@export var creak_sound: StringName = &"door_creak"
@export_range(0.0, 1.0, 0.05) var creak_chance: float = 0.35

var _creak_pending: bool = false


func _init() -> void:
	super._init()
	open_angle_degrees = 95.0
	open_duration = 1.25
	close_duration = 0.95
	open_profile = Profile.PUSH
	close_profile = Profile.LATCH
	stop_bump = 0.004
	open_sound = &"door_open"
	close_sound = &"door_close"
	locked_sound = &"door_locked"
	locked_rattle = 0.004
	locked_prompt = "Try the door"


func _ready() -> void:
	_apply_start_state()
	super._ready()


func _apply_start_state() -> void:
	match start_state:
		StartState.CLOSED:
			start_open_amount = 0.0
		StartState.AJAR:
			start_open_amount = ajar_amount
		StartState.OPEN:
			start_open_amount = 1.0
	if is_node_ready():
		snap_to(start_open_amount)


func _prepare_open(interactor: Node) -> void:
	_creak_pending = creak_sound != &"" and randf() < creak_chance
	if not opens_away_from_player or _value > 0.02:
		return
	var who := interactor as Node3D
	if who == null:
		who = Game.player
	if who == null or _body == null or not _body.is_inside_tree():
		return
	var parent := _body.get_parent() as Node3D
	var parent_xf := parent.global_transform if parent else Transform3D.IDENTITY
	# Interactor position in the closed body's frame.
	var local := (parent_xf * _rest).affine_inverse() * who.global_position
	var probe := _swing_probe()
	var ax := axis.normalized()
	# Direction the free edge moves for a positive configured swing.
	var edge_dir := ax.cross(probe - pivot) * signf(open_angle_degrees)
	var rel := local - pivot
	rel -= ax * rel.dot(ax)
	_swing_sign = -1.0 if rel.dot(edge_dir) > 0.0 else 1.0


func _swing_probe() -> Vector3:
	if not _shapes.is_empty():
		return _shapes[0].position
	return pivot + Vector3(0.4, 0.0, 0.0)


func _on_travel(before: float, after: float, _u: float) -> void:
	if not _creak_pending:
		return
	# Creak as the swing passes about a third of the way.
	var mark := 0.3
	if (before - mark) * (after - mark) <= 0.0 and before != after:
		_creak_pending = false
		_play(creak_sound, -3.0)
