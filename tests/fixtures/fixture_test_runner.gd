extends Node
## Runner for tests/fixtures/test_fixtures.gd (which loads this after the
## autoloads exist, so this file can use Game / Events / Audio directly).
##
## Instantiates every fixture, uses each interactable twice and checks that the
## state changes and comes back, prompts follow, locks hold, flags unlock,
## switches drive their targets, lights warm up, and doors never push into the
## player. Prints PASS/FAIL per check; exits non-zero on any failure.

const FIXTURES: Array[String] = [
	"res://fixtures/door_interior.tscn",
	"res://fixtures/door_front.tscn",
	"res://fixtures/closet_sliding.tscn",
	"res://fixtures/light_switch.tscn",
	"res://fixtures/table_lamp.tscn",
	"res://fixtures/floor_lamp.tscn",
	"res://fixtures/ceiling_light.tscn",
	"res://fixtures/ceiling_fan.tscn",
	"res://fixtures/tv_crt.tscn",
	"res://fixtures/vcr.tscn",
	"res://fixtures/dresser_drawers.tscn",
	"res://fixtures/kitchen_cabinet_base.tscn",
	"res://fixtures/kitchen_cabinet_wall.tscn",
	"res://fixtures/fridge.tscn",
	"res://fixtures/kitchen_sink.tscn",
	"res://fixtures/telephone.tscn",
	"res://fixtures/stereo_console.tscn",
	"res://fixtures/window_double_hung.tscn",
]

var _passed: int = 0
var _failed: int = 0
var _lines: Array[String] = []
var _slot: int = 0
var _player: Node3D = null


func _ready() -> void:
	_run.call_deferred()


func _run() -> void:
	Events.observation_requested.connect(func(t: String) -> void: _lines.append(t))
	_player = Node3D.new()
	_player.name = "TestPlayer"
	get_tree().root.add_child(_player)

	for path in FIXTURES:
		await _test_generic(path)
	await _test_door_ajar_and_interrupt()
	await _test_door_flag_unlock()
	await _test_door_away_from_player()
	await _test_door_blocked_by_player()
	await _test_switch_drives_light()
	await _test_lamp_two_switches()
	await _test_dead_bulb()
	await _test_fan()
	await _test_fridge()
	await _test_tv()
	await _test_phone_and_faucet()
	await _test_vcr()
	await _test_sandbox_loads()

	print("")
	print("fixtures: %d passed, %d failed" % [_passed, _failed])
	get_tree().quit(1 if _failed > 0 else 0)


# --- helpers -------------------------------------------------------------------

func check(ok: bool, label: String) -> void:
	if ok:
		_passed += 1
		print("PASS  " + label)
	else:
		_failed += 1
		print("FAIL  " + label)


func _spawn(path: String, setup: Callable = Callable()) -> Node3D:
	var packed := load(path) as PackedScene
	if packed == null:
		check(false, "%s loads" % path)
		return null
	var inst := packed.instantiate() as Node3D
	inst.position = Vector3(float(_slot) * 25.0, 0.0, 0.0)
	_slot += 1
	if setup.is_valid():
		setup.call(inst)
	get_tree().root.add_child(inst)
	await _frames(3)
	return inst


func _frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame


func _wait(seconds: float) -> void:
	await get_tree().create_timer(seconds).timeout


func _settle(m: MovingPartInteractable, timeout: float = 5.0) -> void:
	await _frames(2)
	var start := Time.get_ticks_msec()
	while m.is_moving() and Time.get_ticks_msec() - start < int(timeout * 1000.0):
		await get_tree().physics_frame
	await _frames(2)


func _place_player(at: Vector3) -> void:
	_player.global_position = at


static func _interactables(node: Node) -> Array[Interactable]:
	var out: Array[Interactable] = []
	for c in node.get_children():
		if c is Interactable:
			out.append(c)
		out.append_array(_interactables(c))
	return out


func _name(i: Interactable) -> String:
	return "%s/%s" % [i.get_parent().owner.name if i.get_parent().owner else "?", i.get_parent().name]


# --- generic: every interactable in every fixture ------------------------------

func _test_generic(path: String) -> void:
	var inst := await _spawn(path)
	if inst == null:
		return
	var list := _interactables(inst)
	check(not list.is_empty(), "%s has interactables" % path.get_file())
	for it in list:
		var label := "%s %s" % [path.get_file(), _name(it)]
		var body := it.get_parent() as CollisionObject3D
		check(body != null and (body.collision_layer & 4) != 0, label + ": body on layer 3")
		check(Interactable.find_for(body) == it, label + ": find_for resolves")
		check(it.get_display_name() != "", label + ": has a display name")
		_place_player(body.global_position + body.global_transform.basis.z * 1.2 + Vector3.UP * 0.6)
		if it is MovingPartInteractable:
			await _cycle_moving(it as MovingPartInteractable, label)
		elif it is SwitchInteractable:
			await _cycle_switch(it as SwitchInteractable, label)
		elif it is DeviceToggleInteractable:
			await _cycle_device(it as DeviceToggleInteractable, label)
		elif it is JammedInteractable:
			await _cycle_jammed(it as JammedInteractable, label)
		else:
			_lines.clear()
			it.interact(_player)
			check(not _lines.is_empty(), label + ": says an observation")
	inst.queue_free()
	await _frames(2)


func _cycle_moving(m: MovingPartInteractable, label: String) -> void:
	var p0 := m.get_prompt()
	if m.is_locked():
		_lines.clear()
		m.interact(_player)
		await _wait(0.5)
		check(not m.is_open(), label + ": locked part stays shut")
		check(not _lines.is_empty(), label + ": locked part says why")
		check(m.get_prompt() != p0, label + ": prompt changes after a locked try (%s -> %s)" % [p0, m.get_prompt()])
		return
	var was_open := m.is_open()
	m.interact(_player)
	if m.auto_close_after > 0.0:
		await _wait(0.1)
		check(m.get_goal() > 0.99, label + ": starts opening")
		check(m.get_prompt() != p0, label + ": prompt changes (%s -> %s)" % [p0, m.get_prompt()])
		await _wait(m.open_duration + m.auto_close_after + m.close_duration + 0.5)
		check(not m.is_open(), label + ": springs shut by itself")
		return
	var p1 := m.get_prompt()
	await _settle(m)
	check(m.is_open() != was_open, label + ": state changes (open=%s)" % m.is_open())
	check(m.get_open_amount() > 0.97 or m.get_open_amount() < 0.03, label + ": settles at an end (%.3f)" % m.get_open_amount())
	check(p1 != p0, label + ": prompt changes (%s -> %s)" % [p0, p1])
	m.interact(_player)
	await _settle(m)
	check(m.is_open() == was_open, label + ": state returns")
	check(m.get_prompt() == p0, label + ": prompt returns (%s)" % m.get_prompt())


func _cycle_switch(s: SwitchInteractable, label: String) -> void:
	await _wait(0.2)
	var on0 := s.is_on()
	var p0 := s.get_prompt()
	s.interact(_player)
	check(s.is_on() != on0, label + ": switch flips")
	check(s.get_prompt() != p0, label + ": prompt changes (%s -> %s)" % [p0, s.get_prompt()])
	for t in s.get_switchables():
		check(t.is_on() == s.is_on(), label + ": target %s follows" % t.name)
	await _wait(0.5)
	s.interact(_player)
	check(s.is_on() == on0, label + ": switch returns")
	check(s.get_prompt() == p0, label + ": prompt returns")
	for t in s.get_switchables():
		check(t.is_on() == on0, label + ": target %s returns" % t.name)
	await _wait(0.5)


func _cycle_device(d: DeviceToggleInteractable, label: String) -> void:
	await _wait(0.6)
	var on0 := d.is_on()
	var p0 := d.get_prompt()
	d.interact(_player)
	check(d.is_on() != on0, label + ": device toggles")
	check(d.get_prompt() != p0, label + ": prompt changes (%s -> %s)" % [p0, d.get_prompt()])
	if d.loop_sound != &"":
		await _wait(d.loop_delay + 0.1)
		check(d.get_loop_player() != null and d.is_loop_active() == d.is_on(), label + ": %s loop follows state" % d.loop_sound)
	for p in d.show_when_on:
		var n := d.get_node(p) as Node3D
		check(n.visible == d.is_on(), label + ": %s shown while on" % n.name)
	for p in d.targets:
		var t := Switchable.resolve(d.get_node(p))
		check(t != null and t.is_on() == d.is_on(), label + ": target follows")
	await _wait(0.7)
	d.interact(_player)
	check(d.is_on() == on0, label + ": device returns")
	check(d.get_prompt() == p0, label + ": prompt returns")
	if d.loop_sound != &"":
		check(not d.is_loop_active(), label + ": loop stops")
	await _wait(0.6)


func _cycle_jammed(j: JammedInteractable, label: String) -> void:
	var p0 := j.get_prompt()
	_lines.clear()
	j.interact(_player)
	check(j.get_tries() == 1, label + ": attempt registered")
	check(not _lines.is_empty(), label + ": says why it won't open")
	check(j.get_prompt() != p0, label + ": prompt changes (%s -> %s)" % [p0, j.get_prompt()])
	await _wait(0.6)
	j.interact(_player)
	check(j.get_tries() == 2, label + ": second attempt registered")


# --- doors -------------------------------------------------------------------

func _door(inst: Node3D) -> DoorInteractable:
	return (inst as DoorFixture).get_door()


func _test_door_ajar_and_interrupt() -> void:
	var inst := await _spawn("res://fixtures/door_interior.tscn", func(n: Node3D) -> void:
		(n as DoorFixture).start_state = DoorInteractable.StartState.AJAR)
	var d := _door(inst)
	check(absf(d.get_open_amount() - d.ajar_amount) < 0.01, "door: starts ajar (%.2f)" % d.get_open_amount())
	check(d.get_prompt() == d.open_prompt, "door: ajar prompt is '%s'" % d.open_prompt)
	d.snap_to(0.0)
	_place_player(inst.global_position + Vector3(0, 1, 1.5))
	d.interact(_player)
	await _wait(0.35)
	var mid := d.get_open_amount()
	check(mid > 0.05 and mid < 0.95, "door: mid-swing after 0.35 s (%.2f)" % mid)
	check(d.get_prompt() == d.close_prompt, "door: prompt is Close while opening")
	d.interact(_player)
	var peak := mid
	var start := Time.get_ticks_msec()
	while d.is_moving() and Time.get_ticks_msec() - start < 4000:
		await get_tree().physics_frame
		peak = maxf(peak, d.get_open_amount())
	check(peak < mid + 0.08, "door: reverses when interrupted (peak %.2f)" % peak)
	check(not d.is_open(), "door: interrupted swing returns shut")
	inst.queue_free()


func _test_door_flag_unlock() -> void:
	Game.set_flag(&"test_key", false)
	var inst := await _spawn("res://fixtures/door_front.tscn", func(n: Node3D) -> void:
		var f := n as DoorFixture
		f.required_flag = &"test_key"
		f.opened_flag = &"test_front_opened")
	var d := _door(inst)
	_place_player(inst.global_position + Vector3(0, 1, -1.5))
	check(d.is_locked(), "front door: locked by default")
	d.interact(_player)
	await _wait(0.5)
	check(not d.is_open(), "front door: refuses without the flag")
	Game.set_flag(&"test_key", true)
	d.interact(_player)
	await _settle(d)
	check(not d.is_locked(), "front door: unlocks with the flag")
	check(d.is_open(), "front door: opens after unlocking")
	check(Game.has_flag(&"test_front_opened"), "front door: sets opened_flag")
	d.interact(_player)
	await _settle(d)
	check(not d.is_open(), "front door: closes again")
	inst.queue_free()


func _test_door_away_from_player() -> void:
	var inst := await _spawn("res://fixtures/door_interior.tscn", func(n: Node3D) -> void:
		(n as DoorFixture).opens_away_from_player = true)
	var d := _door(inst)
	# Default swing goes to -Z. Stand on -Z: it must swing to +Z instead.
	_place_player(inst.global_position + Vector3(0.2, 1.0, -1.0))
	d.interact(_player)
	await _settle(d)
	var slab := d.get_parent() as Node3D
	var edge := slab.global_transform * Vector3(0.8, 1.0, 0.0)
	check(edge.z - inst.global_position.z > 0.3, "door: swings away from a player on -Z (edge z %.2f)" % (edge.z - inst.global_position.z))
	d.interact(_player)
	await _settle(d)
	_place_player(inst.global_position + Vector3(0.2, 1.0, 1.0))
	d.interact(_player)
	await _settle(d)
	edge = slab.global_transform * Vector3(0.8, 1.0, 0.0)
	check(edge.z - inst.global_position.z < -0.3, "door: swings away from a player on +Z (edge z %.2f)" % (edge.z - inst.global_position.z))
	inst.queue_free()


func _test_door_blocked_by_player() -> void:
	var inst := await _spawn("res://fixtures/door_interior.tscn")
	var d := _door(inst)
	var body := CharacterBody3D.new()
	body.collision_layer = 2
	body.collision_mask = 1 | 8
	var cs := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.3
	cap.height = 1.75
	cs.shape = cap
	body.add_child(cs)
	get_tree().root.add_child(body)
	# In the swing path on the -Z side, 0.7 m from the hinge.
	body.global_position = inst.global_position + Vector3(0.05, 0.875, -0.6)
	await _frames(3)
	var hit: Array[bool] = [false]
	d.blocked.connect(func(_c: Object) -> void: hit[0] = true)
	_place_player(body.global_position)
	d.interact(body)
	await _settle(d)
	check(hit[0], "door: reports blocked by the player")
	check(d.get_open_amount() > 0.05 and d.get_open_amount() < 0.9, "door: stops short of the player (%.2f)" % d.get_open_amount())
	var params := PhysicsShapeQueryParameters3D.new()
	params.shape = cap
	params.transform = body.global_transform
	params.collision_mask = 4
	var overlaps := body.get_world_3d().direct_space_state.intersect_shape(params, 4)
	check(overlaps.is_empty(), "door: slab never overlaps the player")
	check(body.global_position.distance_to(inst.global_position + Vector3(0.05, 0.875, -0.6)) < 0.01, "door: player not pushed")
	d.interact(body)
	await _settle(d)
	check(not d.is_open(), "door: closes away from the player")
	body.queue_free()
	inst.queue_free()


# --- switches and lights ---------------------------------------------------------

func _test_switch_drives_light() -> void:
	var holder := Node3D.new()
	holder.position = Vector3(float(_slot) * 25.0, 0, 0)
	_slot += 1
	var sw := (load("res://fixtures/light_switch.tscn") as PackedScene).instantiate() as LightSwitchFixture
	sw.name = "Switch"
	sw.targets = [^"../Ceiling"]
	var light := (load("res://fixtures/ceiling_light.tscn") as PackedScene).instantiate() as LightFixture
	light.name = "Ceiling"
	light.position = Vector3(0, 2.44, 1)
	holder.add_child(sw)
	holder.add_child(light)
	get_tree().root.add_child(holder)
	await _frames(3)
	var s := sw.get_switch()
	var power := light.get_power()
	var lamp := light.get_node(^"Body/Light") as OmniLight3D
	check(s.get_switchables().size() == 1 and s.get_switchables()[0] == power, "wall switch: resolves its target through the fixture root")
	check(not power.is_on() and not lamp.visible, "wall switch: light starts off")
	s.interact(_player)
	await _wait(0.05)
	var early := power.get_level()
	await _wait(0.6)
	check(power.is_on(), "wall switch: turns the light on")
	check(early < 0.98, "light: warms up rather than snapping on (%.2f after 50 ms)" % early)
	check(lamp.visible and lamp.light_energy > 1.0, "light: Light3D lit (energy %.2f)" % lamp.light_energy)
	var glass := light.get_node(^"Body/Glass") as MeshInstance3D
	var mat := glass.material_override as BaseMaterial3D
	check(mat != null and mat.emission_enabled and mat.emission_energy_multiplier > 1.0, "light: glass glows while lit")
	var col := lamp.light_color
	check(col.r > col.g and col.g > col.b, "light: warm incandescent colour")
	await _wait(0.3)
	s.interact(_player)
	await _wait(1.2)
	check(not power.is_on() and not lamp.visible, "wall switch: turns the light off")
	check(mat.emission_energy_multiplier < 0.01, "light: glass dark when off")
	holder.queue_free()


func _test_lamp_two_switches() -> void:
	var holder := Node3D.new()
	holder.position = Vector3(float(_slot) * 25.0, 0, 0)
	_slot += 1
	var sw := (load("res://fixtures/light_switch.tscn") as PackedScene).instantiate() as LightSwitchFixture
	sw.name = "Switch"
	sw.targets = [^"../Lamp/Power"]
	var lamp := (load("res://fixtures/table_lamp.tscn") as PackedScene).instantiate() as LightFixture
	lamp.name = "Lamp"
	holder.add_child(sw)
	holder.add_child(lamp)
	get_tree().root.add_child(holder)
	await _frames(3)
	var wall := sw.get_switch()
	var own := lamp.get_node(^"Body/Switch") as SwitchInteractable
	var power := lamp.get_power()
	wall.interact(_player)
	check(power.is_on() and own.is_on(), "lamp: wall switch turns it on; lamp switch agrees")
	check(own.get_prompt() == own.off_prompt, "lamp: lamp switch prompt follows (%s)" % own.get_prompt())
	await _wait(0.3)
	own.interact(_player)
	check(not power.is_on(), "lamp: its own switch turns it off")
	await _wait(0.3)
	own.interact(_player)
	check(power.is_on(), "lamp: its own switch turns it back on")
	await _wait(0.4)
	var knob := lamp.get_node(^"Body/Knob") as Node3D
	check(absf(knob.rotation_degrees.x - 90.0) < 1.0, "lamp: switch knob turned")
	holder.queue_free()


func _test_dead_bulb() -> void:
	var holder := Node3D.new()
	holder.position = Vector3(float(_slot) * 25.0, 0, 0)
	_slot += 1
	var sw := (load("res://fixtures/light_switch.tscn") as PackedScene).instantiate() as LightSwitchFixture
	sw.name = "Switch"
	sw.targets = [^"../Ceiling"]
	var light := (load("res://fixtures/ceiling_light.tscn") as PackedScene).instantiate() as LightFixture
	light.name = "Ceiling"
	light.dead_bulb = true
	holder.add_child(sw)
	holder.add_child(light)
	get_tree().root.add_child(holder)
	await _frames(3)
	_lines.clear()
	sw.get_switch().interact(_player)
	await _wait(0.5)
	var lamp := light.get_node(^"Body/Light") as OmniLight3D
	check(sw.get_switch().is_on() and light.get_power().is_on(), "dead bulb: switch still clicks on")
	check(not lamp.visible, "dead bulb: nothing lights")
	check(not _lines.is_empty() and _lines[0] == light.get_power().dead_observations[0], "dead bulb: says so (%s)" % (_lines[0] if not _lines.is_empty() else "-"))
	holder.queue_free()


func _test_fan() -> void:
	var inst := await _spawn("res://fixtures/ceiling_fan.tscn")
	var fan := inst as CeilingFanFixture
	var motor := fan.get_motor()
	var chain := inst.get_node(^"FanChainBody/Pull") as SwitchInteractable
	var rotor := inst.get_node(^"Rotor") as Node3D
	var r0 := rotor.rotation.y
	chain.interact(_player)
	await _wait(0.5)
	var early := motor.get_rpm()
	await _wait(2.0)
	var later := motor.get_rpm()
	check(motor.is_on(), "fan: chain starts the motor")
	check(early > 0.0 and early < later and later < motor.max_rpm, "fan: spins up slowly (%.0f -> %.0f rpm)" % [early, later])
	check(absf(rotor.rotation.y - r0) > 0.1, "fan: blades turn")
	chain.interact(_player)
	await _wait(1.0)
	var coast := motor.get_rpm()
	check(not motor.is_on() and coast > 0.0 and coast < later, "fan: coasts down (%.0f rpm a second later)" % coast)
	var light_chain := inst.get_node(^"LightChainBody/Pull") as SwitchInteractable
	light_chain.interact(_player)
	await _wait(0.5)
	check(fan.get_power().is_lit() and (inst.get_node(^"Body/Light") as Light3D).visible, "fan: light chain lights the kit")
	inst.queue_free()


# --- appliances ----------------------------------------------------------------

func _test_fridge() -> void:
	var inst := await _spawn("res://fixtures/fridge.tscn")
	var door := inst.get_node(^"FreshDoor/Hinge") as HingedPartInteractable
	var light := inst.get_node(^"InteriorLight") as PoweredLight
	var hum := inst.get_node(^"Hum") as LoopEmitter
	check(hum.is_active(), "fridge: hum loop running")
	check(not light.is_on(), "fridge: light off while shut")
	_place_player(inst.global_position + Vector3(-0.3, 1.0, 1.6))
	door.interact(_player)
	await _wait(0.1)
	check(light.is_on(), "fridge: light comes on as the door cracks")
	await _settle(door)
	door.interact(_player)
	await _wait(0.2)
	check(light.is_on(), "fridge: light stays on while the door swings shut")
	await _settle(door)
	check(not light.is_on(), "fridge: light off once shut")
	inst.queue_free()


func _test_tv() -> void:
	var inst := await _spawn("res://fixtures/tv_crt.tscn")
	var power := inst.get_node(^"Body/Power") as DeviceToggleInteractable
	var screen := inst.get_node(^"Screen") as CrtScreen
	var spill := inst.get_node(^"Body/Spill") as SpotLight3D
	var mesh := inst.get_node(^"Body/ScreenStatic") as MeshInstance3D
	check(not screen.is_on() and not mesh.visible, "tv: off by default")
	power.interact(_player)
	await _wait(0.1)
	check(screen.get_power() > 0.0 and screen.get_power() < 1.0, "tv: tube warms up (%.2f)" % screen.get_power())
	await _wait(1.0)
	check(screen.get_power() >= 1.0 and mesh.visible and spill.visible, "tv: static on screen and light spill")
	await _wait(0.6)
	power.interact(_player)
	await _wait(0.6)
	check(screen.get_power() <= 0.0 and not mesh.visible and not spill.visible, "tv: collapses to dark")
	inst.queue_free()


func _test_phone_and_faucet() -> void:
	var inst := await _spawn("res://fixtures/telephone.tscn")
	var phone := inst.get_node(^"Body/Phone") as DeviceToggleInteractable
	var handset := inst.get_node(^"Body/Handset") as Node3D
	check(handset.visible and phone.get_prompt() == "Pick up", "phone: receiver on the cradle")
	phone.interact(_player)
	await _wait(0.5)
	check(not handset.visible and phone.is_loop_active(), "phone: lifted, dial tone loop on")
	await _wait(0.3)
	phone.interact(_player)
	check(handset.visible and not phone.is_loop_active(), "phone: hung up, dial tone off")
	inst.queue_free()
	var sink := await _spawn("res://fixtures/kitchen_sink.tscn")
	var tap := sink.get_node(^"Faucet/Tap") as DeviceToggleInteractable
	var water := sink.get_node(^"Faucet/Water") as Node3D
	tap.interact(_player)
	check(water.visible and tap.is_loop_active(), "faucet: water runs")
	await _wait(0.6)
	tap.interact(_player)
	check(not water.visible and not tap.is_loop_active(), "faucet: water stops")
	sink.queue_free()


func _test_vcr() -> void:
	var inst := await _spawn("res://fixtures/vcr.tscn")
	var label := inst.get_node(^"Body/Clock") as Label3D
	var blink_seen: Array[bool] = [false, false]
	for i in 40:
		await _wait(0.05)
		blink_seen[0] = blink_seen[0] or label.visible
		blink_seen[1] = blink_seen[1] or not label.visible
	check(label.text == "12:00" and blink_seen[0] and blink_seen[1], "vcr: 12:00 blinks in standby")
	var power := inst.get_node(^"Body/Power") as DeviceToggleInteractable
	power.interact(_player)
	await _wait(0.2)
	check(label.text != "12:00" and label.visible, "vcr: display changes when switched on (%s)" % label.text)
	inst.queue_free()


func _test_sandbox_loads() -> void:
	var inst := await _spawn("res://tests/fixtures/fixtures_sandbox.tscn")
	check(inst != null and _interactables(inst).size() > 40, "sandbox: loads with every fixture (%d interactables)" % _interactables(inst).size())
	inst.queue_free()
	await _frames(2)
