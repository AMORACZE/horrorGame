extends Node3D
## Audio sandbox: audition every sound id and each helper scene.
##
## Run alone:  godot --path . res://tests/audio/audio_sandbox.tscn
## Click any id to play it 1.5 m in front of the camera (loops toggle on/off).
## Keys: 1-6 footstep on wood/carpet/linoleum/tile/concrete/rug, W toggles
## walking, K moves the listener-body into / out of the kitchen reverb zone,
## P pauses the tree (UI clicks still play, world sounds freeze), Z sweeps the zoom.

const SURFACES: Array[StringName] = [&"wood", &"carpet", &"linoleum", &"tile", &"concrete", &"rug"]

var _world: Node3D
var _camera: Camera3D
var _player_body: CharacterBody3D
var _loops: Dictionary = {}          # id -> Node (player)
var _loop_buttons: Dictionary = {}   # id -> Button
var _surface: StringName = &"wood"
var _intensity: float = 0.7
var _walking: bool = false
var _step_timer: float = 0.0
var _step_side: float = 1.0
var _zoom_sweep: float = -1.0
var _status: Label
var _bed: Node
var _emitters: Array[Node] = []
var _randoms: Array[Node] = []
var _in_kitchen: bool = false


func _ready() -> void:
	_build_world()
	_build_ui()


# --- world -----------------------------------------------------------------------

func _build_world() -> void:
	_world = Node3D.new()
	_world.name = "World"
	add_child(_world)
	var env := WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_COLOR
	e.background_color = Color(0.82, 0.78, 0.68)
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color(0.9, 0.85, 0.75)
	env.environment = e
	_world.add_child(env)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, 30, 0)
	_world.add_child(sun)
	var floor_mesh := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(10, 10)
	floor_mesh.mesh = plane
	_world.add_child(floor_mesh)

	_camera = Camera3D.new()
	_camera.position = Vector3(0, 1.6, 3.5)
	_camera.rotation_degrees = Vector3(-8, 0, 0)
	_world.add_child(_camera)

	# a stand-in player body so ReverbZone has something to detect
	_player_body = CharacterBody3D.new()
	_player_body.collision_layer = 2
	_player_body.collision_mask = 0
	var cs := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.3
	cap.height = 1.75
	cs.shape = cap
	_player_body.add_child(cs)
	_player_body.add_to_group(&"player")
	_player_body.position = Vector3(0, 0.9, 3.5)
	_world.add_child(_player_body)

	var zone := (load("res://audio/reverb_zone.tscn") as PackedScene).instantiate()
	zone.set(&"preset", 2)  # KITCHEN
	zone.set(&"size", Vector3(4, 2.44, 4))
	zone.position = Vector3(-6, 1.22, 3.5)
	_world.add_child(zone)

	_add_emitter(&"fridge_hum", Vector3(-3, 0.3, -2), 0.0)
	_add_emitter(&"clock_tick", Vector3(3, 2.0, -2), 0.0)
	_add_emitter(&"fly_buzz", Vector3(0.5, 1.4, -4), 0.0)

	var settle := (load("res://audio/random_oneshot_emitter.tscn") as PackedScene).instantiate()
	settle.set(&"sound_ids", [&"house_settle"] as Array[StringName])
	settle.set(&"min_gap", 6.0)
	settle.set(&"max_gap", 18.0)
	settle.set(&"box_size", Vector3(9, 2.4, 9))
	settle.position = Vector3(0, 1.2, 0)
	_world.add_child(settle)
	_randoms.append(settle)
	var far := (load("res://audio/random_oneshot_emitter.tscn") as PackedScene).instantiate()
	far.set(&"sound_ids", [&"distant_dog", &"distant_car", &"distant_mower"] as Array[StringName])
	far.set(&"min_gap", 15.0)
	far.set(&"max_gap", 40.0)
	far.set(&"area", 1)  # SPHERE
	far.set(&"radius", 25.0)
	far.position = Vector3(0, 0, -40)
	_world.add_child(far)
	_randoms.append(far)

	_bed = (load("res://audio/ambience_bed.tscn") as PackedScene).instantiate()
	_world.add_child(_bed)


func _add_emitter(id: StringName, pos: Vector3, drift: float) -> void:
	var em := (load("res://audio/ambient_emitter.tscn") as PackedScene).instantiate() as Node3D
	em.set(&"sound_id", id)
	em.set(&"pitch_drift", drift)
	em.position = pos
	_world.add_child(em)
	_emitters.append(em)
	var marker := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = Vector3(0.2, 0.2, 0.2)
	marker.mesh = box
	em.add_child(marker)
	var label := Label3D.new()
	label.text = String(id)
	label.position = Vector3(0, 0.25, 0)
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.pixel_size = 0.004
	em.add_child(label)


# --- UI -------------------------------------------------------------------------

func _build_ui() -> void:
	var layer := CanvasLayer.new()
	layer.process_mode = Node.PROCESS_MODE_ALWAYS
	add_child(layer)
	var panel := PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_LEFT_WIDE)
	panel.custom_minimum_size = Vector2(560, 0)
	layer.add_child(panel)
	var scroll := ScrollContainer.new()
	panel.add_child(scroll)
	var v := VBoxContainer.new()
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(v)

	_status = Label.new()
	v.add_child(_status)
	v.add_child(_heading("Footsteps (1-6, W walks)"))
	var fs := HBoxContainer.new()
	v.add_child(fs)
	for s: StringName in SURFACES:
		var b := Button.new()
		b.text = String(s)
		b.pressed.connect(_footstep.bind(s))
		fs.add_child(b)
	var walk := CheckButton.new()
	walk.text = "walk"
	walk.toggled.connect(_on_walk_toggled)
	fs.add_child(walk)
	v.add_child(_slider("intensity", 0.0, 1.0, _intensity, _on_intensity))

	v.add_child(_heading("Sound ids (loops toggle)"))
	var grid := GridContainer.new()
	grid.columns = 3
	v.add_child(grid)
	for id: StringName in SoundLibrary.ids():
		if String(id).begins_with("footstep_"):
			continue
		var b := Button.new()
		b.text = String(id) + (" (loop)" if SoundLibrary.is_loop(id) else "")
		b.pressed.connect(_audition.bind(id))
		grid.add_child(b)
		if SoundLibrary.is_loop(id):
			_loop_buttons[id] = b

	v.add_child(_heading("Helpers"))
	var h := HBoxContainer.new()
	v.add_child(h)
	h.add_child(_toggle("ambience bed", true, _on_bed_toggled))
	h.add_child(_toggle("emitters", true, _on_emitters_toggled))
	h.add_child(_toggle("random", true, _on_random_toggled))
	h.add_child(_toggle("camcorder layer", true, _on_layer_toggled))
	var h2 := HBoxContainer.new()
	v.add_child(h2)
	var settle := Button.new()
	settle.text = "trigger random now"
	settle.pressed.connect(_trigger_randoms)
	h2.add_child(settle)
	var kitchen := Button.new()
	kitchen.text = "enter/leave kitchen zone (K)"
	kitchen.pressed.connect(_toggle_kitchen)
	h2.add_child(kitchen)
	var pause := Button.new()
	pause.text = "pause tree (P)"
	pause.pressed.connect(_toggle_pause)
	h2.add_child(pause)
	v.add_child(_slider("camcorder zoom (Z sweeps)", 0.0, 1.0, 0.0, _on_zoom_slider))

	v.add_child(_heading("Settings (buses)"))
	for key: StringName in [&"master", &"world", &"ambience", &"ui"]:
		v.add_child(_slider(String(key), 0.0, 1.0, float(Settings.get_value(&"audio", key)),
			_on_bus_slider.bind(key)))


func _on_bed_toggled(on: bool) -> void:
	if on:
		_bed.call(&"start", 2.0)
	else:
		_bed.call(&"fade_out", 2.0)


func _on_emitters_toggled(on: bool) -> void:
	for em: Node in _emitters:
		if on:
			em.call(&"start", 1.0)
		else:
			em.call(&"stop", 1.0)


func _on_random_toggled(on: bool) -> void:
	for r: Node in _randoms:
		r.set(&"enabled", on)


func _on_layer_toggled(on: bool) -> void:
	Audio.set(&"camcorder_layer_enabled", on)


func _trigger_randoms() -> void:
	for r: Node in _randoms:
		r.call(&"trigger")


func _on_zoom_slider(x: float) -> void:
	Events.camera_zoom_changed.emit(x)


func _on_bus_slider(x: float, key: StringName) -> void:
	Settings.set_value(&"audio", key, x, false)


func _on_walk_toggled(on: bool) -> void:
	_walking = on


func _on_intensity(x: float) -> void:
	_intensity = x


func _heading(t: String) -> Label:
	var l := Label.new()
	l.text = t
	l.add_theme_color_override(&"font_color", Color(1.0, 0.85, 0.5))
	return l


func _slider(label: String, lo: float, hi: float, value: float, cb: Callable) -> HBoxContainer:
	var h := HBoxContainer.new()
	var l := Label.new()
	l.text = label
	l.custom_minimum_size = Vector2(190, 0)
	h.add_child(l)
	var s := HSlider.new()
	s.min_value = lo
	s.max_value = hi
	s.step = 0.01
	s.value = value
	s.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	s.value_changed.connect(cb)
	h.add_child(s)
	return h


func _toggle(label: String, on: bool, cb: Callable) -> CheckButton:
	var c := CheckButton.new()
	c.text = label
	c.button_pressed = on
	c.toggled.connect(cb)
	return c


# --- actions ----------------------------------------------------------------------

func _front() -> Vector3:
	return _camera.global_position - _camera.global_basis.z * 1.5


func _audition(id: StringName) -> void:
	var def: Dictionary = Audio.get_def(id)
	if def.get(&"bus") == &"UI":
		Audio.play(id)
		return
	if not SoundLibrary.is_loop(id):
		Audio.play_at(id, _front())
		return
	if _loops.has(id):
		(_loops[id] as Node).queue_free()
		_loops.erase(id)
		(_loop_buttons[id] as Button).modulate = Color.WHITE
		return
	# loops get their own player here (pooled players belong to Audio)
	var stream := Audio.get_stream(id)
	if stream == null:
		return
	var p: Node
	if def.get(&"bus") == &"Ambience":
		var p2 := AudioStreamPlayer.new()
		p2.stream = stream
		p2.bus = def[&"bus"]
		p2.volume_db = def[&"volume_db"]
		_world.add_child(p2)
		p2.play()
		p = p2
	else:
		var p3 := AudioStreamPlayer3D.new()
		Audio.configure_player_3d(p3, id)
		p3.stream = stream
		p3.volume_db = def[&"volume_db"]
		_world.add_child(p3)
		p3.global_position = _front()
		p3.play()
		p = p3
	_loops[id] = p
	(_loop_buttons[id] as Button).modulate = Color(0.6, 1.0, 0.6)


func _footstep(s: StringName) -> void:
	_surface = s
	_step_side = -_step_side
	var pos := _player_body.global_position + Vector3(0.12 * _step_side, -0.9, 0)
	Events.player_footstep.emit(s, pos, _intensity)


func _toggle_kitchen() -> void:
	_in_kitchen = not _in_kitchen
	_player_body.position = Vector3(-6, 0.9, 3.5) if _in_kitchen else Vector3(0, 0.9, 3.5)


func _toggle_pause() -> void:
	get_tree().paused = not get_tree().paused
	Audio.play(&"ui_open" if get_tree().paused else &"ui_close")


func _unhandled_input(event: InputEvent) -> void:
	var k := event as InputEventKey
	if k == null or not k.pressed or k.echo:
		return
	match k.keycode:
		KEY_1, KEY_2, KEY_3, KEY_4, KEY_5, KEY_6:
			_footstep(SURFACES[k.keycode - KEY_1])
		KEY_W:
			_walking = not _walking
		KEY_K:
			_toggle_kitchen()
		KEY_P:
			_toggle_pause()
		KEY_Z:
			_zoom_sweep = 0.0


func _process(delta: float) -> void:
	if _walking and not get_tree().paused:
		_step_timer -= delta
		if _step_timer <= 0.0:
			_step_timer = lerpf(0.65, 0.38, _intensity)
			_footstep(_surface)
	if _zoom_sweep >= 0.0:
		_zoom_sweep += delta * 0.5
		Events.camera_zoom_changed.emit(minf(_zoom_sweep, 1.0))
		if _zoom_sweep >= 1.0:
			_zoom_sweep = -1.0
	var r: Dictionary = Audio.call(&"get_reverb_target")
	_status.text = "surface %s  intensity %.2f  %s\nreverb: room %.2f damp %.2f wet %.2f%s" % [
		_surface, _intensity, "PAUSED" if get_tree().paused else "",
		r[&"room_size"], r[&"damping"], r[&"wet"], "  (kitchen zone)" if _in_kitchen else ""]
