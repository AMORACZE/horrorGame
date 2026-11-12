class_name JammedInteractable
extends Interactable
## Something that looks like it should open and will not: a painted-shut
## window, a stuck sash, a cupboard swollen in the heat. Using it plays a
## sound, gives the part a short shake, and says the next observation.

@export_group("Jammed")
@export var tried_prompt: String = "Try again"
## Node that shakes. Empty = none.
@export var shake_node: NodePath
@export var shake_offset: Vector3 = Vector3(0.0, 0.002, 0.0)
@export_range(0.05, 1.0, 0.01, "suffix:s") var shake_time: float = 0.28
@export var sound: StringName = &"window_rattle"
@export var sound_volume_db: float = 0.0
@export_range(0.0, 2.0, 0.01, "suffix:s") var cooldown: float = 0.4

var _tries: int = 0
var _last_use_ms: int = -100000
var _shake: Node3D = null
var _shake_rest: Vector3 = Vector3.ZERO
var _t: float = -1.0


func _init() -> void:
	prompt = "Open"


func _ready() -> void:
	_shake = get_node_or_null(shake_node) as Node3D
	if _shake:
		_shake_rest = _shake.position
	set_process(false)


func get_prompt() -> String:
	return tried_prompt if _tries > 0 else prompt


func get_tries() -> int:
	return _tries


func can_interact(interactor: Node) -> bool:
	return super.can_interact(interactor) and Time.get_ticks_msec() - _last_use_ms >= int(cooldown * 1000.0)


func _interact(_interactor: Node) -> void:
	_last_use_ms = Time.get_ticks_msec()
	_tries += 1
	var body := get_parent() as Node3D
	if body and body.is_inside_tree():
		Audio.play_attached(sound, body, sound_volume_db, randf_range(0.95, 1.05))
	say_next_observation()
	if _shake:
		_t = 0.0
		set_process(true)


func _process(delta: float) -> void:
	_t += delta
	var k := _t / shake_time
	if k >= 1.0:
		_shake.position = _shake_rest
		_t = -1.0
		set_process(false)
		return
	_shake.position = _shake_rest + shake_offset * sin(_t * 70.0) * (1.0 - k)
