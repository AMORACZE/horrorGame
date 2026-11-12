extends Node
## Session state (autoload: `Game`).
##
## Owns the things that outlive any one scene: world flags, the player reference,
## and the input-lock stack that modal UI uses to take control away from the player.
## No story logic lives here.

## The current player node (set by the player on _ready, cleared on exit).
var player: Node3D = null

## The currently loaded level root.
var level: Node = null

var _flags: Dictionary = {}
var _input_locks: Array[Object] = []


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS


# --- World flags -------------------------------------------------------------
# Small persistent facts about the world ("front_door_unlocked", "read_note_kitchen").
# This is the hook a future save system and story layer will build on.

func set_flag(flag: StringName, value: Variant = true) -> void:
	if _flags.get(flag) == value:
		return
	_flags[flag] = value
	Events.flag_changed.emit(flag, value)


func get_flag(flag: StringName, default: Variant = false) -> Variant:
	return _flags.get(flag, default)


func has_flag(flag: StringName) -> bool:
	return bool(_flags.get(flag, false))


func get_flags() -> Dictionary:
	return _flags.duplicate()


# --- Input lock --------------------------------------------------------------
# Anything that needs the player to stop moving/looking (examine view, reader,
# pause menu) pushes itself here and pops when done. The player controller only
# checks `Game.is_input_locked()`. Mouse capture follows the lock automatically.

func lock_input(owner_obj: Object) -> void:
	if owner_obj in _input_locks:
		return
	var was_locked := is_input_locked()
	_input_locks.append(owner_obj)
	if not was_locked:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		Events.input_lock_changed.emit(true)


func unlock_input(owner_obj: Object) -> void:
	if owner_obj not in _input_locks:
		return
	_input_locks.erase(owner_obj)
	if not is_input_locked():
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
		Events.input_lock_changed.emit(false)


func is_input_locked() -> bool:
	# Drop locks whose owners were freed without unlocking.
	for i in range(_input_locks.size() - 1, -1, -1):
		if not is_instance_valid(_input_locks[i]):
			_input_locks.remove_at(i)
	return not _input_locks.is_empty()
