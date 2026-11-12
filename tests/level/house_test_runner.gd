extends Node
## Runner for tests/level/test_house.gd (loaded after the autoloads exist, so
## this file can use Game / Events / Audio directly). See that file's header.

const MAIN := "res://main.tscn"
## Floor probes: world (x, z) -> expected surface id.
const SURFACES: Array = [
	[Vector2(2.0, 0.7), &"wood", "hall"],
	[Vector2(1.0, 2.6), &"carpet", "living room"],
	[Vector2(8.6, 3.4), &"linoleum", "kitchen"],
	[Vector2(4.15, 3.45), &"rug", "rug"],
]
## Walk spawn -> living room -> kitchen -> back to the spawn.
const ROUTE: Array[Vector2] = [
	Vector2(1.5, 1.1), Vector2(1.6, 2.15), Vector2(2.7, 2.2), Vector2(4.6, 2.9), Vector2(6.1, 3.3),
	Vector2(8.3, 3.4), Vector2(6.1, 3.3), Vector2(4.6, 2.9), Vector2(2.7, 2.2), Vector2(1.6, 2.15),
	Vector2(1.5, 1.1), Vector2(1.0, 0.72),
]
const CLEAR_RADIUS := 0.45  # 0.9 m wide path


class ErrorCounter extends Logger:
	var errors: PackedStringArray = []
	var _mutex := Mutex.new()

	func _log_error(function: String, file: String, line: int, code: String, rationale: String,
			_editor_notify: bool, error_type: int, _script_backtraces: Array[ScriptBacktrace]) -> void:
		if error_type == ERROR_TYPE_WARNING:
			return
		_mutex.lock()
		errors.append("%s (%s:%d %s) %s" % [code, file, line, function, rationale])
		_mutex.unlock()

	func _log_message(_message: String, _error: bool) -> void:
		pass

	func take() -> PackedStringArray:
		_mutex.lock()
		var out := errors.duplicate()
		errors.clear()
		_mutex.unlock()
		return out


var _passed: int = 0
var _failed: int = 0
var _lines: Array[String] = []
var _log := ErrorCounter.new()
var _main: Node = null
var _level: Node = null
var _player: Player = null


func _ready() -> void:
	OS.add_logger(_log)
	_run.call_deferred()


func _run() -> void:
	Events.observation_requested.connect(func(t: String) -> void: _lines.append(t))
	var packed := load(MAIN) as PackedScene
	_main = packed.instantiate()
	get_tree().root.add_child(_main)
	await _frames(5)
	var load_errors := _log.take()
	check(load_errors.is_empty(), "no errors on load", "\n    ".join(load_errors))
	_level = Game.level
	check(_level != null, "level instanced by main.tscn")
	_player = Game.player as Player
	check(_player != null, "player exists")
	if _level == null or _player == null:
		_finish()
		return

	var spawns := get_tree().get_nodes_in_group(&"player_spawn")
	check(spawns.size() == 1, "exactly one player_spawn", "found %d" % spawns.size())
	var spawn := spawns[0] as Node3D
	await _seconds(2.0)
	var drift := _player.global_position - spawn.global_position
	check(Vector2(drift.x, drift.z).length() < 0.05 and absf(drift.y) < 0.06 and _player.is_on_floor(),
		"player stands at the spawn after 2 s", "offset %s, on floor %s" % [drift, _player.is_on_floor()])

	await _test_surfaces()
	_test_clearance()
	await _test_walk()
	_test_interactables()
	await _test_front_door()
	await _test_responders()

	var late := _log.take()
	check(late.is_empty(), "no errors while playing", "\n    ".join(late))
	_finish()


func _finish() -> void:
	OS.remove_logger(_log)
	print("")
	print("house: %d passed, %d failed" % [_passed, _failed])
	get_tree().quit(1 if _failed > 0 else 0)


# --- helpers -------------------------------------------------------------------

func check(ok: bool, label: String, detail: String = "") -> void:
	if ok:
		_passed += 1
		print("PASS  " + label)
	else:
		_failed += 1
		print("FAIL  " + label + ("" if detail.is_empty() else "\n    " + detail))


func _frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame


func _seconds(t: float) -> void:
	await get_tree().create_timer(t, true, true).timeout


func _place(p: Vector2, yaw: float = 0.0) -> void:
	_player.teleport(Transform3D(Basis.IDENTITY, Vector3(p.x, 0.02, p.y)))
	_player.set_look(yaw, 0.0)


func _find(path: String) -> Node:
	var n := _level.get_node_or_null(path)
	if n == null:
		check(false, "node exists: " + path)
	return n


func _interactables_under(node: Node, out: Array[Interactable]) -> void:
	if node is Interactable:
		out.append(node as Interactable)
	for c in node.get_children():
		_interactables_under(c, out)


# --- checks -------------------------------------------------------------------

func _test_surfaces() -> void:
	var footsteps := _player.get_node(^"Footsteps") as PlayerFootsteps
	for entry: Array in SURFACES:
		var p: Vector2 = entry[0]
		_place(p)
		await _frames(6)
		var got: StringName = footsteps.call(&"_probe_surface")
		check(got == entry[1], "floor reads %s in the %s" % [entry[1], entry[2]], "got %s at %s" % [got, p])


func _test_clearance() -> void:
	var space := _player.get_world_3d().direct_space_state
	var shape := CylinderShape3D.new()
	shape.radius = CLEAR_RADIUS
	shape.height = 1.5
	var q := PhysicsShapeQueryParameters3D.new()
	q.shape = shape
	q.collision_mask = 1  # world: walls and furniture (clutter on layer 3 only is walk-through)
	var blocked: Array[String] = []
	var pts: Array[Vector2] = [Vector2(1.0, 0.72)]
	pts.append_array(ROUTE)
	for i in pts.size() - 1:
		var a := pts[i]
		var b := pts[i + 1]
		var n := maxi(1, int(a.distance_to(b) / 0.1))
		for k in n + 1:
			var p := a.lerp(b, float(k) / n)
			# Bottom at 0.26 m: above the step height, so rugs and thresholds don't count.
			q.transform = Transform3D(Basis.IDENTITY, Vector3(p.x, 0.26 + 0.75, p.y))
			var hits := space.intersect_shape(q, 4)
			if not hits.is_empty():
				var names: Array[String] = []
				for h: Dictionary in hits:
					names.append(String((h.get("collider") as Node).get_path()).get_file())
				blocked.append("%s: %s" % [p, ", ".join(names)])
				break
	check(blocked.is_empty(), "route is 0.9 m clear (spawn -> living -> kitchen -> back)", "\n    ".join(blocked))


func _test_walk() -> void:
	_place(Vector2(1.0, 0.72), PI)
	await _frames(10)
	var stuck := ""
	for target in ROUTE:
		var reached := false
		var t := 0.0
		var start := Vector2(_player.global_position.x, _player.global_position.z)
		var limit := start.distance_to(target) / _player.walk_speed * 2.0 + 2.0
		Input.action_press(&"move_forward")
		while t < limit:
			var here := Vector2(_player.global_position.x, _player.global_position.z)
			var to := target - here
			if to.length() < 0.2:
				reached = true
				break
			# yaw 0 faces -Z; yaw increases counter-clockwise (toward -X).
			_player.set_look(atan2(-to.x, -to.y), 0.0, true)
			await get_tree().physics_frame
			t += 1.0 / Engine.physics_ticks_per_second
		Input.action_release(&"move_forward")
		if not reached:
			stuck = "stopped at %s on the way to %s" % [_player.global_position, target]
			break
	await _frames(20)
	check(stuck.is_empty(), "walk spawn -> living room -> kitchen -> back arrives", stuck)
	var end := _player.global_position
	check(absf(end.y) < 0.06, "walk ends on the floor", "y = %.3f" % end.y)


func _test_interactables() -> void:
	var all: Array[Interactable] = []
	_interactables_under(_level, all)
	var bad: Array[String] = []
	for it in all:
		if not it.enabled:
			continue
		if it.get_prompt().strip_edges().is_empty() or it.get_display_name().strip_edges().is_empty():
			bad.append("%s prompt='%s' name='%s'" % [_level.get_path_to(it), it.get_prompt(), it.get_display_name()])
	print("INFO  interactables in the level: %d" % all.size())
	check(all.size() > 0 and bad.is_empty(), "every Interactable has a prompt and a name", "\n    ".join(bad))


func _test_front_door() -> void:
	var door := _find("Fixtures/Hall/FrontDoor/Slab/Door") as DoorInteractable
	if door == null:
		return
	_lines.clear()
	door.interact(_player)
	await _seconds(0.6)
	var expected := door.locked_observations[0] if not door.locked_observations.is_empty() else ""
	check(door.is_locked() and not door.is_open() and door.get_open_amount() < 0.05,
		"front door stays shut", "open amount %.2f" % door.get_open_amount())
	check(not expected.is_empty() and _lines.has(expected), "front door says its locked line",
		"heard %s, expected '%s'" % [_lines, expected])


func _test_responders() -> void:
	# Closet panel, kitchen drawer, fridge door: they move.
	for path: String in ["Fixtures/Hall/Closet/PanelFront/Slide", "Fixtures/Kitchen/BaseWest/Drawer/Drawer",
			"Fixtures/Kitchen/Fridge/FreshDoor/Hinge"]:
		var part := _find(path) as MovingPartInteractable
		if part == null:
			continue
		part.interact(_player)
		await _seconds(1.6)
		check(part.is_open() and part.get_open_amount() > 0.9, "%s opens" % path, "amount %.2f" % part.get_open_amount())
		part.interact(_player)
		await _seconds(1.4)
		check(not part.is_open(), "%s closes again" % path)
	# Lamp and TV: they switch on and off.
	for path: String in ["Fixtures/Living/LampNorth/Body/Switch", "Living/Tv/Body/Power"]:
		var it := _find(path) as Interactable
		if it == null:
			continue
		var before := bool(it.call(&"is_on"))
		it.interact(_player)
		await _seconds(0.6)
		var after := bool(it.call(&"is_on"))
		check(before == false and after == true, "%s turns on" % path, "before %s after %s" % [before, after])
		it.interact(_player)
		await _seconds(0.6)
		check(not bool(it.call(&"is_on")), "%s turns off" % path)
