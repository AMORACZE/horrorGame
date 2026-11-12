extends Node
## Runner for tests/props/test_props.gd (loaded at runtime so the autoloads
## that the interaction scripts reference exist before they compile).
##
## For each scene: loads and instantiates without engine/script errors or
## warnings, root is a physics body with at least one collision shape, has an
## enabled Interactable resolvable via Interactable.find_for(root) as a direct
## child, a display name, something to say (observations / description / body),
## physics layers matching its `prop_class`, and Examinables produce meshes from
## create_examine_visual(). Prints PASS/FAIL per scene; exits non-zero on failure.

const PROPS_DIR := "res://props"
const LAYER_WORLD := 1
const LAYER_INTERACT := 4
const LAYER_PHYS := 8
const EXPECTED_LAYERS: Dictionary = {
	"furniture": LAYER_WORLD | LAYER_INTERACT,
	"tabletop": LAYER_INTERACT,
	"wall": LAYER_INTERACT,
	"loose": LAYER_INTERACT | LAYER_PHYS,
}


class ErrorCatcher:
	extends Logger
	var _mutex := Mutex.new()
	var _messages: PackedStringArray = []

	func _log_error(_function: String, file: String, line: int, code: String, rationale: String,
			_editor_notify: bool, error_type: int, _script_backtraces: Array[ScriptBacktrace]) -> void:
		var kind := "WARNING" if error_type == Logger.ERROR_TYPE_WARNING else "ERROR"
		_mutex.lock()
		_messages.append("%s: %s (%s:%d)" % [kind, rationale if rationale != "" else code, file, line])
		_mutex.unlock()

	func _log_message(message: String, error: bool) -> void:
		if error:
			_mutex.lock()
			_messages.append("STDERR: " + message.strip_edges())
			_mutex.unlock()

	func take() -> PackedStringArray:
		_mutex.lock()
		var out := _messages.duplicate()
		_messages.clear()
		_mutex.unlock()
		return out


var _catcher := ErrorCatcher.new()


func _ready() -> void:
	OS.add_logger(_catcher)
	_run()


func _run() -> void:
	await get_tree().process_frame
	var paths := _find_scenes(PROPS_DIR)
	paths.sort()
	var failed := 0
	if paths.is_empty():
		print("FAIL  no scenes found under %s" % PROPS_DIR)
		failed += 1
	for path in paths:
		var problems := await _check(path)
		if problems.is_empty():
			print("PASS  %s" % path)
		else:
			failed += 1
			print("FAIL  %s" % path)
			for p in problems:
				print("        - %s" % p)
	print("")
	print("%d scenes, %d passed, %d failed" % [paths.size(), paths.size() - failed, failed])
	OS.remove_logger(_catcher)
	get_tree().quit(1 if failed > 0 else 0)


func _check(path: String) -> PackedStringArray:
	var problems := PackedStringArray()
	_catcher.take()
	var packed := load(path) as PackedScene
	if packed == null:
		problems.append("does not load as a PackedScene")
		problems.append_array(_catcher.take())
		return problems
	var inst := packed.instantiate()
	if inst == null:
		problems.append("instantiate() returned null")
		return problems
	get_tree().root.add_child(inst)
	# Two frames so deferred builders (@tool blinds/curtains) and _ready have run.
	await get_tree().process_frame
	await get_tree().process_frame

	var body := inst as CollisionObject3D
	if body == null:
		problems.append("root is %s, not a physics body" % inst.get_class())
	else:
		if PhysicsServer3D.body_get_shape_count(body.get_rid()) == 0:
			problems.append("no collision shapes")
		problems.append_array(_check_layers(body, path))
		problems.append_array(_check_interactable(body))
	for msg in _catcher.take():
		problems.append(msg)
	inst.queue_free()
	await get_tree().process_frame
	return problems


func _check_layers(body: CollisionObject3D, path: String) -> PackedStringArray:
	var problems := PackedStringArray()
	var cls := String(body.get_meta(&"prop_class", ""))
	if not EXPECTED_LAYERS.has(cls):
		problems.append("metadata prop_class missing or unknown: '%s'" % cls)
		return problems
	var expected: int = EXPECTED_LAYERS[cls]
	if body.collision_layer != expected:
		problems.append("collision_layer %d, expected %d for %s" % [body.collision_layer, expected, cls])
	if (body.collision_layer & LAYER_INTERACT) == 0:
		problems.append("not on layer 3 (interactable)")
	if body is RigidBody3D and cls != "loose":
		problems.append("RigidBody3D must be prop_class loose")
	if cls == "loose" and not body is RigidBody3D:
		problems.append("prop_class loose must be a RigidBody3D")
	if body is RigidBody3D and (body.collision_mask & LAYER_WORLD) == 0:
		problems.append("loose body does not collide with the world")
	if path.contains("rug") and body.get_meta(&"surface", &"") != &"rug":
		problems.append("rug without metadata surface = &\"rug\"")
	return problems


func _check_interactable(body: CollisionObject3D) -> PackedStringArray:
	var problems := PackedStringArray()
	var comp := Interactable.find_for(body)
	if comp == null:
		problems.append("no enabled Interactable found via Interactable.find_for(root)")
		return problems
	if comp.get_parent() != body:
		problems.append("Interactable is not a direct child of the root")
	if not comp.enabled:
		problems.append("Interactable disabled")
	if comp.get_display_name().strip_edges() == "":
		problems.append("empty display_name")
	if comp.get_prompt().strip_edges() == "":
		problems.append("empty prompt")
	var has_text := not comp.observations.is_empty()
	if comp is ExaminableInteractable:
		has_text = has_text or (comp as ExaminableInteractable).description.strip_edges() != ""
		var visual := (comp as ExaminableInteractable).create_examine_visual()
		var meshes := 0
		for c in visual.get_children():
			if c is MeshInstance3D and (c as MeshInstance3D).mesh != null:
				meshes += 1
		if meshes == 0:
			problems.append("create_examine_visual() returned no meshes")
		visual.free()
	if comp is ReadableInteractable:
		var r := comp as ReadableInteractable
		has_text = has_text or r.body.strip_edges() != ""
		if r.body.strip_edges() == "":
			problems.append("readable with empty body")
	if not has_text:
		problems.append("nothing to say: no observations, description or body")
	for line in comp.observations:
		if line.strip_edges() == "":
			problems.append("blank observation line")
	return problems


func _find_scenes(dir_path: String) -> PackedStringArray:
	var out := PackedStringArray()
	var dir := DirAccess.open(dir_path)
	if dir == null:
		return out
	for f in dir.get_files():
		if f.ends_with(".tscn"):
			out.append(dir_path.path_join(f))
	for d in dir.get_directories():
		if not d.begins_with(".") and not d.begins_with("_"):
			out.append_array(_find_scenes(dir_path.path_join(d)))
	return out
