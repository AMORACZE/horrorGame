extends SceneTree
## Headless audio test. Run:
##   godot --headless --audio-driver Dummy --path . -s res://tests/audio/test_audio.gd
## Prints PASS/FAIL per check; exits non-zero if anything failed.

const DOC_ONESHOTS: Array[StringName] = [
	&"door_open", &"door_close", &"door_locked", &"door_creak", &"drawer_open", &"drawer_close",
	&"cabinet_open", &"cabinet_close", &"switch_on", &"switch_off", &"lamp_click", &"button_press",
	&"pickup", &"putdown", &"paper_rustle", &"tv_on", &"tv_off", &"phone_pickup", &"phone_hangup",
	&"fridge_open", &"fridge_close", &"tape_insert", &"glass_clink", &"book_slide", &"cloth_rustle",
	&"thud_soft", &"window_rattle", &"faucet_squeak",
	&"house_settle", &"distant_dog", &"distant_car", &"distant_mower",
	&"ui_tick", &"ui_open", &"ui_close",
]
const DOC_LOOPS: Array[StringName] = [
	&"room_tone", &"outside_afternoon", &"wind_light", &"fridge_hum", &"clock_tick", &"tv_static",
	&"light_buzz", &"fly_buzz", &"phone_dial_tone", &"faucet_run", &"camcorder_motor",
	&"camcorder_zoom", &"tape_hiss",
]
const SURFACES: Array[StringName] = [&"wood", &"carpet", &"linoleum", &"tile", &"concrete", &"rug"]

var _fails: int = 0
var _passes: int = 0
var _audio: Node
var _events: Node
var _settings: Node
var _played: Array[Dictionary] = []


func _initialize() -> void:
	_run.call_deferred()


func check(name: String, ok: bool, detail: String = "") -> void:
	if ok:
		_passes += 1
		printerr("PASS  ", name)
	else:
		_fails += 1
		printerr("FAIL  ", name, ("  -- " + detail) if detail != "" else "")


func _on_played(id: StringName, player: Node) -> void:
	_played.append({&"id": id, &"player": player})


func _run() -> void:
	await process_frame
	_audio = root.get_node_or_null(^"Audio")
	_events = root.get_node_or_null(^"Events")
	_settings = root.get_node_or_null(^"Settings")
	check("autoloads present", _audio != null and _events != null and _settings != null)
	if _audio == null:
		_finish()
		return
	_audio.connect(&"played", _on_played)

	# --- bus layout ------------------------------------------------------------
	var expected := {&"Master": &"", &"World": &"Master", &"SFX": &"World", &"Footsteps": &"World",
		&"Ambience": &"Master", &"UI": &"Master"}
	var bus_ok := true
	var bus_detail := ""
	for b: StringName in expected:
		var i := AudioServer.get_bus_index(b)
		if i < 0 or (b != &"Master" and AudioServer.get_bus_send(i) != expected[b]):
			bus_ok = false
			bus_detail += "%s " % b
	check("bus names and routing match the doc", bus_ok, bus_detail)
	check("World bus has a room reverb", _bus_has(&"World", "AudioEffectReverb"))
	check("Master bus has a limiter", _bus_has(&"Master", "AudioEffectHardLimiter"))

	# --- every id resolves --------------------------------------------------------
	var missing: Array[String] = []
	for id: StringName in DOC_ONESHOTS + DOC_LOOPS:
		if not _audio.call(&"has_sound", id) or _audio.call(&"get_stream", id) == null:
			missing.append(String(id))
	for s: StringName in SURFACES:
		if s == &"rug":
			continue
		var fid := StringName("footstep_%s" % s)
		if not _audio.call(&"has_sound", fid):
			missing.append(String(fid))
	check("every doc sound id resolves to a loaded stream", missing.is_empty(), ", ".join(missing))

	# --- variant counts -------------------------------------------------------------
	var thin: Array[String] = []
	for id: StringName in DOC_ONESHOTS:
		if SoundLibrary.variant_paths(id).size() < 3:
			thin.append(String(id))
	for s: StringName in SURFACES:
		if s != &"rug" and SoundLibrary.variant_paths(StringName("footstep_%s" % s)).size() < 3:
			thin.append("footstep_%s" % s)
	check("one-shots and footsteps have >= 3 variants", thin.is_empty(), ", ".join(thin))

	# --- loop flags (runtime-configured streams) ---------------------------------
	var bad_loops: Array[String] = []
	for id: StringName in DOC_LOOPS:
		for s: AudioStream in SoundLibrary.load_variants(id):
			if not SoundLibrary.is_stream_looping(s):
				bad_loops.append(String(id))
	check("loops are flagged looping", bad_loops.is_empty(), ", ".join(bad_loops))
	var bad_once: Array[String] = []
	for id: StringName in DOC_ONESHOTS:
		for s: AudioStream in SoundLibrary.load_variants(id):
			if SoundLibrary.is_stream_looping(s):
				bad_once.append(String(id))
	check("one-shots are not looping", bad_once.is_empty(), ", ".join(bad_once))

	# --- loop flags as imported (before any runtime fix-up) -----------------------
	var bad_import: Array[String] = []
	for id: StringName in DOC_LOOPS:
		for p: String in SoundLibrary.variant_paths(id):
			var raw := ResourceLoader.load(p, "", ResourceLoader.CACHE_MODE_IGNORE) as AudioStream
			if raw == null or not SoundLibrary.is_stream_looping(raw):
				bad_import.append(p.get_file())
	check("loops already loop as imported (.import / WAV smpl chunk)", bad_import.is_empty(), ", ".join(bad_import))

	# --- play / play_at / play_attached -----------------------------------------
	var p2 := _audio.call(&"play", &"ui_tick") as AudioStreamPlayer
	check("play() returns a playing AudioStreamPlayer", p2 != null and p2.playing)
	check("play() routes UI ids to the UI bus", p2 != null and p2.bus == &"UI")
	var p3 := _audio.call(&"play_at", &"door_close", Vector3(1, 1, 1)) as AudioStreamPlayer3D
	check("play_at() returns a playing AudioStreamPlayer3D at the position",
		p3 != null and p3.playing and p3.global_position.is_equal_approx(Vector3(1, 1, 1)))
	check("play_at() routes interaction to the SFX bus", p3 != null and p3.bus == &"SFX")
	var holder := Node3D.new()
	root.add_child(holder)
	var pa := _audio.call(&"play_attached", &"drawer_open", holder) as AudioStreamPlayer3D
	check("play_attached() parents the player to the node", pa != null and pa.get_parent() == holder and pa.playing)
	holder.queue_free()
	await process_frame
	check("play_attached() player is freed with its node", not is_instance_valid(pa))

	# --- unknown id ---------------------------------------------------------------
	var before := _played.size()
	var u1: Variant = _audio.call(&"play", &"no_such_sound_xyz")
	var u2: Variant = _audio.call(&"play_at", &"no_such_sound_xyz", Vector3.ZERO)
	var u3: Variant = _audio.call(&"get_stream", &"no_such_sound_xyz")
	check("unknown id returns null and plays nothing",
		u1 == null and u2 == null and u3 == null and not _audio.call(&"has_sound", &"no_such_sound_xyz") and _played.size() == before)

	# --- no immediate repeats ------------------------------------------------------
	var prev: AudioStream = null
	var repeats := 0
	for i in 40:
		var s := _audio.call(&"get_stream", &"door_close") as AudioStream
		if s == prev:
			repeats += 1
		prev = s
	check("random variants never repeat back to back", repeats == 0, "%d repeats" % repeats)

	# --- footsteps via Events -------------------------------------------------------
	for s: StringName in SURFACES:
		_played.clear()
		_events.emit_signal(&"player_footstep", s, Vector3(0, 0, 2), 0.7)
		var ok := _played.size() == 1
		var bus := &""
		var played_id := &""
		if ok:
			var pl := _played[0][&"player"] as AudioStreamPlayer3D
			ok = pl != null and pl.playing
			bus = pl.bus if pl else &""
			played_id = _played[0][&"id"]
		var want := &"footstep_carpet" if s == &"rug" else StringName("footstep_%s" % s)
		check("Events.player_footstep(%s) plays %s on the Footsteps bus" % [s, want],
			ok and bus == &"Footsteps" and played_id == want, "played=%s bus=%s" % [played_id, bus])
	_played.clear()
	_events.emit_signal(&"player_footstep", &"wood", Vector3.ZERO, 0.4)
	var soft := (_played[0][&"player"] as AudioStreamPlayer3D).volume_db if _played.size() > 0 else 0.0
	_played.clear()
	_events.emit_signal(&"player_footstep", &"wood", Vector3.ZERO, 1.0)
	var loud := (_played[0][&"player"] as AudioStreamPlayer3D).volume_db if _played.size() > 0 else -99.0
	check("footstep level scales with intensity", loud > soft + 3.0, "soft=%.1f loud=%.1f" % [soft, loud])
	_played.clear()
	_events.emit_signal(&"player_landed", &"tile", Vector3.ZERO, 0.9)
	check("Events.player_landed plays a footstep (+ thud on hard landings)",
		_played.size() >= 1 and _played[0][&"id"] == &"footstep_tile")

	# --- settings drive bus volumes ---------------------------------------------------
	var world_idx := AudioServer.get_bus_index(&"World")
	_settings.call(&"set_value", &"audio", &"world", 0.5, false)
	check("Settings audio/world changes the World bus volume",
		absf(AudioServer.get_bus_volume_db(world_idx) - linear_to_db(0.5)) < 0.01,
		"%.2f dB" % AudioServer.get_bus_volume_db(world_idx))
	_settings.call(&"set_value", &"audio", &"ui", 0.0, false)
	check("Settings audio/ui = 0 mutes the UI bus", AudioServer.is_bus_mute(AudioServer.get_bus_index(&"UI")))
	_settings.call(&"set_value", &"audio", &"world", 1.0, false)
	_settings.call(&"set_value", &"audio", &"ui", 1.0, false)
	check("Settings restore to unity gain", absf(AudioServer.get_bus_volume_db(world_idx)) < 0.01
		and not AudioServer.is_bus_mute(AudioServer.get_bus_index(&"UI")))

	# --- pause behaviour ----------------------------------------------------------------
	var ui_p := _audio.call(&"play", &"ui_open") as AudioStreamPlayer
	var w_p := _audio.call(&"play_at", &"clock_tick", Vector3.ZERO) as AudioStreamPlayer3D
	paused = true
	check("while paused: UI players keep processing, world players pause",
		ui_p != null and ui_p.can_process() and w_p != null and not w_p.can_process())
	paused = false
	w_p.stop()

	# --- camcorder layer ------------------------------------------------------------------
	var hiss := _audio.get_node_or_null(^"World2D/TapeHiss") as AudioStreamPlayer
	var motor := _audio.get_node_or_null(^"World2D/CamcorderMotor") as AudioStreamPlayer
	check("camcorder layer (tape_hiss + camcorder_motor) is running",
		hiss != null and hiss.playing and motor != null and motor.playing)
	var zoom := _audio.get_node_or_null(^"World2D/ZoomMotor") as AudioStreamPlayer
	_events.emit_signal(&"camera_zoom_changed", 0.1)
	await process_frame
	_events.emit_signal(&"camera_zoom_changed", 0.2)
	await process_frame
	check("camera_zoom_changed starts the zoom motor", zoom != null and zoom.playing)
	var t0 := Time.get_ticks_msec()
	while zoom.playing and Time.get_ticks_msec() - t0 < 3000:
		await process_frame
	check("zoom motor spins down when the zoom stops", not zoom.playing)

	# --- helper scenes ----------------------------------------------------------------
	# helper scripts are used untyped here: in -s mode their class names compile
	# before the autoloads exist, so the test must not reference them statically
	var em: Node = (load("res://audio/ambient_emitter.tscn") as PackedScene).instantiate() 
	em.set(&"sound_id", &"fridge_hum")
	em.set(&"pitch_drift", 0.01)
	root.add_child(em)
	await process_frame
	var em_player := em.get(&"player") as AudioStreamPlayer3D
	check("ambient_emitter plays its looping id", em.call(&"is_playing") and em_player != null
		and SoundLibrary.is_stream_looping(em_player.stream))
	var bed: Node = (load("res://audio/ambience_bed.tscn") as PackedScene).instantiate() 
	root.add_child(bed)
	await process_frame
	var bed_players: Array = bed.get(&"players")
	check("ambience_bed plays room_tone + outside_afternoon on Ambience",
		bed_players.size() == 2 and bed.call(&"is_playing") and (bed_players[0] as AudioStreamPlayer).bus == &"Ambience")
	var ro: Node3D = (load("res://audio/random_oneshot_emitter.tscn") as PackedScene).instantiate() 
	ro.set(&"sound_ids", [&"house_settle", &"distant_dog"] as Array[StringName])
	ro.position = Vector3(10, 0, 0)
	root.add_child(ro)
	var inside := true
	var box: Vector3 = ro.get(&"box_size")
	for i in 50:
		var pt: Vector3 = ro.call(&"random_point")
		var lp := pt - ro.global_position
		if absf(lp.x) > box.x * 0.5 + 0.001 or absf(lp.y) > box.y * 0.5 + 0.001 or absf(lp.z) > box.z * 0.5 + 0.001:
			inside = false
	var rp := ro.call(&"trigger") as AudioStreamPlayer3D
	check("random_oneshot_emitter plays from points inside its box", inside and rp != null and rp.playing)

	var zone: Area3D = (load("res://audio/reverb_zone.tscn") as PackedScene).instantiate() 
	var zone_script: Script = zone.get_script()
	var presets: Dictionary = zone_script.get_script_constant_map()[&"PRESETS"]
	var bathroom: int = (zone_script.get_script_constant_map()[&"Preset"] as Dictionary)[&"BATHROOM"]
	zone.set(&"preset", bathroom)
	root.add_child(zone)
	check("reverb_zone is on layer 5 and watches layer 2", zone.collision_layer == 16 and zone.collision_mask == 2)
	var body := CharacterBody3D.new()
	body.collision_layer = 2
	var cs := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cs.shape = cap
	body.add_child(cs)
	body.add_to_group(&"player")
	body.position = Vector3(50, 0, 0)
	root.add_child(body)
	await physics_frame
	await physics_frame
	body.position = Vector3.ZERO
	var entered := false
	for i in 30:
		await physics_frame
		if is_equal_approx(float((_audio.call(&"get_reverb_target") as Dictionary)[&"wet"]), float(presets[bathroom][&"wet"])):
			entered = true
			break
	check("reverb_zone sets the World reverb target when the player enters", entered)
	body.position = Vector3(50, 0, 0)
	var left := false
	for i in 30:
		await physics_frame
		if is_equal_approx(float((_audio.call(&"get_reverb_target") as Dictionary)[&"wet"]), 0.09):
			left = true
			break
	check("reverb_zone restores the default reverb when the player leaves", left)

	em.queue_free()
	bed.queue_free()
	ro.queue_free()
	zone.queue_free()
	body.queue_free()
	_audio.call(&"stop_all_world")
	_audio.set(&"camcorder_layer_enabled", false)
	for p: AudioStreamPlayer in [p2, ui_p]:
		if is_instance_valid(p):
			p.stop()
	for i in 5:
		await process_frame
	_finish()


func _bus_has(bus: StringName, cls: String) -> bool:
	var i := AudioServer.get_bus_index(bus)
	if i < 0:
		return false
	for e in AudioServer.get_bus_effect_count(i):
		if AudioServer.get_bus_effect(i, e).is_class(cls):
			return true
	return false


func _finish() -> void:
	print("\n%d passed, %d failed" % [_passes, _fails])
	quit(1 if _fails > 0 else 0)
