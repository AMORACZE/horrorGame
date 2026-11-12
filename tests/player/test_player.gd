extends Node
## Automated player test. Runs headless:
##
##   godot --headless --audio-driver Dummy --path . res://tests/player/test_player.tscn
##
## Loads the player sandbox, drives the player with Input.action_press and
## parsed InputEventActions, prints PASS/FAIL per check and exits non-zero if
## anything failed. (A scene rather than a -s script: under -s, scripts that
## reference autoloads cannot be compiled before the autoloads exist.)

const SANDBOX := "res://tests/player/player_sandbox.tscn"
const TIMEOUT_S := 180.0
const ACTIONS: Array[StringName] = [&"move_forward", &"move_back", &"move_left", &"move_right",
	&"sprint", &"crouch", &"zoom", &"interact", &"look_left", &"look_right", &"look_up", &"look_down"]

var player: Player
var _failures: int = 0
var _checks: int = 0
var _steps: Array[StringName] = []
var _landings: Array[float] = []
var _zoom_events: Array[float] = []
var _focus_events: Array[Interactable] = []
var _observations: Array[String] = []


func _ready() -> void:
	var sandbox := (load(SANDBOX) as PackedScene).instantiate()
	add_child(sandbox)
	player = sandbox.get_node(^"Player") as Player
	Events.player_footstep.connect(func(s: StringName, _p: Vector3, _i: float) -> void: _steps.append(s))
	Events.player_landed.connect(func(_s: StringName, _p: Vector3, impact: float) -> void: _landings.append(impact))
	Events.camera_zoom_changed.connect(func(a: float) -> void: _zoom_events.append(a))
	Events.interaction_focus_changed.connect(func(it: Interactable) -> void: _focus_events.append(it))
	Events.observation_requested.connect(func(t: String) -> void: _observations.append(t))
	get_tree().create_timer(TIMEOUT_S).timeout.connect(_on_timeout)
	_run.call_deferred()


func _run() -> void:
	await _frames(10)
	check(player != null and Game.player == player, "player registered in Game.player and group",
		"group=%s" % player.is_in_group(&"player"))
	await test_walk_and_sprint()
	await test_footstep_surfaces()
	await test_stairs()
	await test_ramp()
	await test_crouch()
	await test_zoom()
	await test_interaction()
	await test_push()
	await test_input_lock()
	print("player tests: %d checks, %d failed" % [_checks, _failures])
	print("RESULT: %s" % ("PASS" if _failures == 0 else "FAIL"))
	get_tree().quit(0 if _failures == 0 else 1)


# --- Tests -------------------------------------------------------------------

func test_walk_and_sprint() -> void:
	await place(Vector3(0, 0, 9.2), 0.0)
	Input.action_press(&"move_forward")
	await _frames(40)  # accelerate
	var v_walk := await measure_speed(60)
	var forward := -player.get_local_velocity().z
	check(absf(v_walk - player.walk_speed) < 0.15, "walks forward at walk speed",
		"%.2f m/s (expected %.2f)" % [v_walk, player.walk_speed])
	check(forward > 1.8, "walk moves in the facing direction", "forward %.2f" % forward)
	release_all()

	await place(Vector3(-3, 0, 9.2), 0.0)
	Input.action_press(&"move_forward")
	Input.action_press(&"sprint")
	await _frames(50)
	var v_hurry := await measure_speed(60)
	check(v_hurry > v_walk * 1.4 and absf(v_hurry - player.hurry_speed) < 0.2, "sprint (hurry) is faster",
		"%.2f m/s vs walk %.2f" % [v_hurry, v_walk])
	release_all()
	await _frames(40)
	check(player.get_ground_speed() < 0.05, "decelerates to rest after release", "%.3f m/s" % player.get_ground_speed())


func test_footstep_surfaces() -> void:
	var cases: Array = [
		[Vector3(0, 0, 9.2), &"wood"],
		[Vector3(-8, 0, 1.6), &"carpet"],
		[Vector3(8.5, 0, 1.6), &"tile"],
		[Vector3(-8, 0, -4.4), &"linoleum"],
		[Vector3(-2.5, 0, 1.9), &"rug"],
	]
	for c: Array in cases:
		var expected: StringName = c[1]
		await place(c[0], 0.0)
		_steps.clear()
		Input.action_press(&"move_forward")
		await _frames(int(1.6 * 60) if expected == &"rug" else 120)
		release_all()
		await _frames(30)
		var matching := _steps.count(expected)
		if expected == &"rug":
			check(matching >= 1, "footstep surface from Area3D zone (rug)", "%s" % [_steps])
		else:
			check(_steps.size() >= 3 and matching == _steps.size(), "footsteps report surface '%s'" % expected, "%s" % [_steps])
	# Stride-based: walking 2 s at 2 m/s with 0.8 m strides is about 5 steps.
	await place(Vector3(0, 0, 9.2), 0.0)
	_steps.clear()
	Input.action_press(&"move_forward")
	await _frames(40)
	_steps.clear()
	var p0 := player.global_position
	await _frames(120)
	var dist := player.global_position.distance_to(p0)
	release_all()
	var stride := dist / maxf(1.0, float(_steps.size()))
	check(stride > 0.65 and stride < 0.95, "footsteps are spaced by stride distance", "%d steps over %.2f m" % [_steps.size(), dist])
	await _frames(30)


func test_stairs() -> void:
	await place(Vector3(7, 0, 9.4), 0.0)
	_landings.clear()
	Input.action_press(&"move_forward")
	var max_y := 0.0
	var max_cam_jump := 0.0
	var prev_cam := player.get_camera().global_position.y
	var max_up_vel := 0.0
	var air_frames := 0
	var prev_tick := Engine.get_physics_frames()
	for i in 300:
		await get_tree().physics_frame
		await get_tree().process_frame
		max_y = maxf(max_y, player.global_position.y)
		# Camera moves per rendered frame; normalise by physics ticks elapsed.
		var cam_y := player.get_camera().global_position.y
		var ticks := maxi(1, Engine.get_physics_frames() - prev_tick)
		prev_tick = Engine.get_physics_frames()
		max_cam_jump = maxf(max_cam_jump, absf(cam_y - prev_cam) / ticks)
		prev_cam = cam_y
		max_up_vel = maxf(max_up_vel, player.velocity.y)
		if not player.is_grounded():
			air_frames += 1
		if player.global_position.z < 1.0:
			break
	release_all()
	await _frames(20)
	var p := player.global_position
	check(max_y > 1.0 and max_y < 1.15, "climbs the 0.18 m stairs to the landing", "max y %.3f" % max_y)
	check(p.z < 2.5 and absf(p.y) < 0.03, "walks down the far side to the floor", "end %s" % p)
	check(max_up_vel < 0.5, "no launch off the steps", "max upward velocity %.2f" % max_up_vel)
	var impact := 0.0
	for x in _landings:
		impact = maxf(impact, x)
	check(impact < 0.2 and air_frames < 30, "no falling or bouncing on the stairs", "air frames %d, landings %s" % [air_frames, _landings])
	check(max_cam_jump < 0.08, "camera is smoothed over steps", "largest camera jump per frame %.3f m" % max_cam_jump)


func test_ramp() -> void:
	await place(Vector3(-7, 0, 9.4), 0.0)
	Input.action_press(&"move_forward")
	await _frames(200)
	release_all()
	await _frames(20)
	check(player.global_position.y > 0.75 and player.global_position.z < 4.2, "walks up the ramp", "at %s" % player.global_position)


func test_crouch() -> void:
	await place(Vector3(4, 0, -3.4), 0.0)
	await _frames(20)
	var stand_y := player.get_camera().global_position.y - player.global_position.y
	tap(&"crouch")
	await _frames(40)
	var crouch_y := player.get_camera().global_position.y - player.global_position.y
	check(stand_y > 1.5 and crouch_y < 1.15, "crouch lowers the camera", "eye %.2f -> %.2f" % [stand_y, crouch_y])

	Input.action_press(&"move_forward")
	await _frames(30)
	var v_crouch := await measure_speed(30)
	check(absf(v_crouch - player.crouch_speed) < 0.15, "crouch walks at crouch speed", "%.2f m/s" % v_crouch)
	await _frames(100)  # under the slab now
	release_all()
	await _frames(10)
	var under := player.global_position.z
	tap(&"crouch")  # try to stand
	await _frames(40)
	var still_y := player.get_camera().global_position.y - player.global_position.y
	check(under < -5.6 and still_y < 1.2, "cannot stand up under a low ceiling", "z %.2f, eye %.2f" % [under, still_y])

	Input.action_press(&"move_back")
	await _frames(240)
	release_all()
	await _frames(40)
	var out_y := player.get_camera().global_position.y - player.global_position.y
	check(player.global_position.z > -4.6 and out_y > 1.5, "stands up once there is headroom", "z %.2f, eye %.2f" % [player.global_position.z, out_y])

	# Hold-to-crouch when toggle_crouch is off.
	Settings.set_value(&"controls", &"toggle_crouch", false, false)
	Input.action_press(&"crouch")
	await _frames(40)
	var held := player.get_crouch_amount()
	Input.action_release(&"crouch")
	await _frames(40)
	check(held > 0.95 and player.get_crouch_amount() < 0.05, "hold-to-crouch honours controls/toggle_crouch", "held %.2f released %.2f" % [held, player.get_crouch_amount()])
	Settings.set_value(&"controls", &"toggle_crouch", true, false)


func test_zoom() -> void:
	var cam := player.get_camera() as CamcorderCamera
	var wide := cam.fov
	_zoom_events.clear()
	Input.action_press(&"zoom")
	await _seconds(2.0)
	var tele := cam.fov
	var amount := player.get_zoom_amount()
	var scale := cam.get_look_scale()
	check(wide > 60.0 and tele < 20.0 and amount > 0.99, "zoom narrows the FOV", "%.1f -> %.1f deg" % [wide, tele])
	check(_zoom_events.size() > 5 and _zoom_events.back() > 0.99, "zoom emits camera_zoom_changed while changing", "%d events, last %.3f" % [_zoom_events.size(), _zoom_events.back() if _zoom_events.size() > 0 else -1.0])
	check(scale < 0.3, "look sensitivity drops with zoom", "scale %.3f" % scale)
	var sorted := true
	for i in range(1, _zoom_events.size()):
		if _zoom_events[i] < _zoom_events[i - 1] - 0.0001:
			sorted = false
	check(sorted, "zoom-in amount rises monotonically", "")
	Input.action_release(&"zoom")
	await _seconds(2.0)
	check(absf(cam.fov - wide) < 0.05 and is_zero_approx(_zoom_events.back()), "zoom returns to wide on release", "fov %.2f last %.3f" % [cam.fov, _zoom_events.back()])

	Settings.set_value(&"video", &"fov", 60.0, false)
	await _frames(2)
	check(absf(cam.fov - 60.0) < 0.05, "wide FOV follows Settings video/fov live", "fov %.2f" % cam.fov)
	Settings.set_value(&"video", &"fov", 68.0, false)
	await _frames(2)


func test_interaction() -> void:
	var wardrobe := get_tree().current_scene.find_child("Wardrobe", true, false) as Node
	if wardrobe == null:
		wardrobe = find_child("Wardrobe", true, false)
	var target := Interactable.find_for(wardrobe)
	_focus_events.clear()
	await place(Vector3(-5, 0, -0.6), 0.0)
	await _frames(5)
	check(target != null and player.get_focused_interactable() == target, "focuses the Interactable in front",
		"focused %s" % player.get_focused_interactable())
	check(_focus_events.size() > 0 and _focus_events.back() == target, "emits interaction_focus_changed(target)", "%s" % [_focus_events])

	var hits: Array[Node] = []
	target.interacted.connect(func(who: Node) -> void: hits.append(who))
	_observations.clear()
	tap(&"interact")
	await _frames(2)
	check(hits.size() == 1 and hits[0] == player, "interact() reaches the focused Interactable", "%d calls" % hits.size())
	check(_observations.size() == 1 and _observations[0] == "The doors are painted shut.", "base Interactable says its observation", "%s" % [_observations])

	player.set_look(PI, 0.0)
	await _frames(3)
	check(player.get_focused_interactable() == null and _focus_events.back() == null, "focus clears when looking away", "%s" % player.get_focused_interactable())

	# Out of reach: 3 m back from the wardrobe.
	await place(Vector3(-5, 0, 1.0), 0.0)
	await _frames(3)
	check(player.get_focused_interactable() == null, "nothing focused beyond 2 m reach", "%s" % player.get_focused_interactable())


func test_push() -> void:
	var box := find_child("PushBox", true, false) as RigidBody3D
	var start := box.global_position
	await place(Vector3(5, 0, 1.6), 0.0)
	Input.action_press(&"move_forward")
	await _frames(90)
	release_all()
	await _frames(30)
	var moved := start.z - box.global_position.z
	check(moved > 0.3 and box.global_position.y < 0.6, "pushes a loose RigidBody3D prop", "box moved %.2f m, now %s" % [moved, box.global_position])


func test_input_lock() -> void:
	await place(Vector3(0, 0, 9.2), 0.0)
	Input.action_press(&"move_forward")
	await _frames(60)
	Game.lock_input(self)
	await _frames(30)
	check(player.get_ground_speed() < 0.05, "locking input brings the player to rest", "%.3f m/s" % player.get_ground_speed())
	var p0 := player.global_position
	var yaw0 := player.get_yaw()
	var fov0 := player.get_camera().fov
	Input.action_press(&"look_right")
	Input.action_press(&"zoom")
	Input.action_press(&"sprint")
	tap(&"crouch")
	await _frames(60)
	check(player.global_position.distance_to(p0) < 0.01, "no movement while locked", "%.3f m" % player.global_position.distance_to(p0))
	check(absf(player.get_yaw() - yaw0) < 0.0001, "no look while locked", "yaw %.4f -> %.4f" % [yaw0, player.get_yaw()])
	check(absf(player.get_camera().fov - fov0) < 0.01, "no zoom while locked", "fov %.2f -> %.2f" % [fov0, player.get_camera().fov])
	check(player.get_crouch_amount() < 0.01, "no crouch while locked", "%.2f" % player.get_crouch_amount())
	release_all()

	# Interact while locked: focus the wardrobe first, then lock.
	Game.unlock_input(self)
	await place(Vector3(-5, 0, -0.6), 0.0)
	await _frames(5)
	var target := player.get_focused_interactable()
	Game.lock_input(self)
	var hits: Array[int] = [0]
	if target:
		target.interacted.connect(func(_w: Node) -> void: hits[0] += 1)
	tap(&"interact")
	await _frames(3)
	check(target != null and hits[0] == 0, "no interaction while locked", "%d calls" % hits[0])

	Game.unlock_input(self)
	await _seconds(0.3)
	Input.action_press(&"move_forward")
	await _frames(30)
	check(player.get_ground_speed() > 0.5, "moves again after unlock", "%.2f m/s" % player.get_ground_speed())
	release_all()
	var yaw1 := player.get_yaw()
	Input.action_press(&"look_right")
	await _seconds(0.5)
	release_all()
	check(player.get_yaw() < yaw1 - 0.3, "gamepad look turns right after unlock", "yaw %.3f -> %.3f" % [yaw1, player.get_yaw()])


# --- Helpers -----------------------------------------------------------------

func check(ok: bool, what: String, detail: String) -> void:
	_checks += 1
	if not ok:
		_failures += 1
	print("%s  %s%s" % ["PASS" if ok else "FAIL", what, ("  (%s)" % detail) if detail != "" else ""])


func place(pos: Vector3, yaw: float) -> void:
	release_all()
	player.teleport(Transform3D(Basis(Vector3.UP, yaw), pos + Vector3(0, 0.02, 0)))
	await _frames(20)


func measure_speed(frames: int) -> float:
	var p0 := player.global_position
	await _frames(frames)
	var d := player.global_position - p0
	d.y = 0.0
	return d.length() / (frames / float(Engine.physics_ticks_per_second))


func tap(action: StringName) -> void:
	var down := InputEventAction.new()
	down.action = action
	down.pressed = true
	Input.parse_input_event(down)
	var up := InputEventAction.new()
	up.action = action
	up.pressed = false
	Input.parse_input_event.call_deferred(up)


func release_all() -> void:
	for a in ACTIONS:
		Input.action_release(a)


func _frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame


func _seconds(s: float) -> void:
	await get_tree().create_timer(s, true, true).timeout


func _on_timeout() -> void:
	print("FAIL  test timed out after %.0f s" % TIMEOUT_S)
	get_tree().quit(2)
