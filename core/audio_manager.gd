extends Node
## Sound playback service (autoload: `Audio`).
##
## Sounds are addressed by id (StringName), never by file path, so content can be
## re-recorded or swapped without touching gameplay code. The id list lives in
## docs/ARCHITECTURE.md section 8; settings per id live in audio/sound_library.gd
## and the files in audio/sounds/<id>/. Unknown ids warn once and return null.
##
## Pause behaviour: this node runs PROCESS_MODE_ALWAYS. Players for the UI bus
## live under an always-processing holder, everything else under pausable
## holders, so world sounds freeze with get_tree().paused and UI clicks do not.
##
## Also owns two pieces of global sound design:
##  * the camcorder layer: tape hiss + transport motor, as if picked up by the
##    camcorder's own microphone, and the zoom motor while the zoom moves;
##  * the World bus room reverb, blended by ReverbZone volumes (audio/reverb_zone.gd).

## Emitted for every sound started through this service (id, the player node).
signal played(id: StringName, player: Node)

const POOL_2D_SIZE := 12
const POOL_UI_SIZE := 8
const POOL_3D_SIZE := 32

const BUS_FOR_SETTING := {
	&"master": &"Master",
	&"world": &"World",
	&"ambience": &"Ambience",
	&"ui": &"UI",
}

## Default room acoustics for the World bus reverb (a furnished, carpeted living room).
const DEFAULT_REVERB := {&"room_size": 0.32, &"damping": 0.72, &"wet": 0.09, &"predelay_msec": 10.0}

@export_group("Camcorder layer")
## Tape hiss + transport motor bed. Very quiet; it is the medium, not an effect.
@export var camcorder_layer_enabled: bool = true:
	set(v):
		camcorder_layer_enabled = v
		if is_inside_tree():
			_update_camcorder_layer()
@export var tape_hiss_db: float = 0.0
@export var camcorder_motor_db: float = 0.0
## Seconds without a zoom change before the zoom motor spins down.
@export var zoom_motor_hold: float = 0.12

@export_group("Reverb")
## Seconds to blend between reverb zone presets.
@export var reverb_blend_time: float = 0.8

var _streams: Dictionary = {}        # StringName -> Array[AudioStream]
var _last_variant: Dictionary = {}   # StringName -> int
var _warned: Dictionary = {}         # StringName -> true
var _defs: Dictionary = {}           # StringName -> Dictionary (cached SoundLibrary defs)

var _holder_world: Node
var _holder_ui: Node
var _holder_3d: Node3D
var _pool_2d: Array[AudioStreamPlayer] = []
var _pool_ui: Array[AudioStreamPlayer] = []
var _pool_3d: Array[AudioStreamPlayer3D] = []
var _started_at: Dictionary = {}     # player instance id -> ticks msec (for voice stealing)

var _hiss: AudioStreamPlayer
var _motor: AudioStreamPlayer
var _zoom: AudioStreamPlayer
var _zoom_last_amount: float = -1.0
var _zoom_last_change_ms: int = -100000
var _zoom_speed: float = 0.0

var _reverb: AudioEffectReverb
var _reverb_zones: Array[Dictionary] = []   # [{zone: Node, params: Dictionary}]
var _reverb_target: Dictionary = DEFAULT_REVERB.duplicate()


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_build_pools()
	_load_library()
	_find_reverb()
	_apply_all_settings()
	Events.setting_changed.connect(_on_setting_changed)
	Events.player_footstep.connect(_on_player_footstep)
	Events.player_landed.connect(_on_player_landed)
	Events.camera_zoom_changed.connect(_on_camera_zoom_changed)
	_build_camcorder_layer()


# =============================================================================
# Public API (signatures fixed by docs/ARCHITECTURE.md)
# =============================================================================

## Play a non-positional sound (UI, camcorder, player-internal). Returns the player or null.
func play(id: StringName, volume_db: float = 0.0, pitch: float = 1.0) -> AudioStreamPlayer:
	var stream := _pick(id)
	if stream == null:
		return null
	var def: Dictionary = _defs[id]
	var is_ui: bool = def[&"bus"] == &"UI"
	var p := _take_2d(_pool_ui if is_ui else _pool_2d)
	p.stream = stream
	p.bus = def[&"bus"]
	p.volume_db = _jitter_volume(def, volume_db)
	p.pitch_scale = _jitter_pitch(def, pitch)
	p.play()
	_started_at[p.get_instance_id()] = Time.get_ticks_msec()
	played.emit(id, p)
	return p


## Play a one-shot at a world position. Returns the player or null.
func play_at(id: StringName, position: Vector3, volume_db: float = 0.0, pitch: float = 1.0) -> AudioStreamPlayer3D:
	var stream := _pick(id)
	if stream == null:
		return null
	var p := _take_3d()
	_configure_3d(p, id, stream, volume_db, pitch)
	p.global_position = position
	p.play()
	_started_at[p.get_instance_id()] = Time.get_ticks_msec()
	played.emit(id, p)
	return p


## Play a one-shot that follows a node (door, drawer). Freed with the node.
func play_attached(id: StringName, node: Node3D, volume_db: float = 0.0, pitch: float = 1.0) -> AudioStreamPlayer3D:
	if node == null or not is_instance_valid(node) or not node.is_inside_tree():
		push_warning("Audio: play_attached('%s') needs a Node3D inside the tree" % id)
		return null
	var stream := _pick(id)
	if stream == null:
		return null
	var p := AudioStreamPlayer3D.new()
	p.name = "Sound_%s" % id
	_configure_3d(p, id, stream, volume_db, pitch)
	node.add_child(p)
	if not SoundLibrary.is_loop(id):
		p.finished.connect(p.queue_free)
	p.play()
	played.emit(id, p)
	return p


## Play a footstep for a surface id. Normally driven by Events.player_footstep.
func play_footstep(surface: StringName, position: Vector3, intensity: float = 1.0) -> void:
	var s := surface
	var vol := 0.0
	var pitch := 1.0
	if s == &"rug":
		# a rug over a hard floor: carpet, softer and a touch duller
		s = &"carpet"
		vol -= 3.0
		pitch = 0.96
	var id := StringName("footstep_%s" % s)
	if not SoundLibrary.has(id):
		_warn_once(StringName("surface:%s" % surface), "Audio: unknown footstep surface '%s', using wood" % surface)
		id = &"footstep_wood"
	var i := clampf(intensity, 0.0, 1.0)
	# crouch ~0.4 -> about -9 dB, walk ~0.7 -> about -4 dB, hurry 1.0 -> 0 dB
	vol += linear_to_db(0.12 + 0.88 * pow(i, 1.5))
	pitch *= 1.0 + (i - 0.7) * 0.05
	play_at(id, position, vol, pitch)


## Get the stream for an id (for looping emitters that own their own player). Null if unknown.
func get_stream(id: StringName) -> AudioStream:
	return _pick(id)


func has_sound(id: StringName) -> bool:
	return _streams.has(id) and not (_streams[id] as Array).is_empty()


# =============================================================================
# Extra public helpers (additive; used by the audio helper scenes)
# =============================================================================

## Library settings for an id with defaults filled in (empty if unknown).
func get_def(id: StringName) -> Dictionary:
	return _defs.get(id, {})


## Apply an id's bus / distance settings to a player owned by someone else.
func configure_player_3d(p: AudioStreamPlayer3D, id: StringName) -> void:
	var def: Dictionary = _defs.get(id, SoundLibrary.DEFAULTS)
	p.bus = def[&"bus"]
	p.unit_size = def[&"unit_size"]
	p.max_distance = def[&"max_distance"]
	p.attenuation_filter_cutoff_hz = def[&"filter_hz"]
	p.attenuation_filter_db = def[&"filter_db"]
	p.max_polyphony = def[&"polyphony"]


## A ReverbZone the player entered. The most recently entered zone wins.
func enter_reverb_zone(zone: Node, params: Dictionary) -> void:
	exit_reverb_zone(zone)
	_reverb_zones.append({&"zone": zone, &"params": params})
	_update_reverb_target()


func exit_reverb_zone(zone: Node) -> void:
	for i in range(_reverb_zones.size() - 1, -1, -1):
		if _reverb_zones[i][&"zone"] == zone:
			_reverb_zones.remove_at(i)
	_update_reverb_target()


## Current reverb target parameters (for debugging / tests).
func get_reverb_target() -> Dictionary:
	return _reverb_target.duplicate()


## Stop every pooled world sound (level change). UI and the camcorder layer keep going.
func stop_all_world() -> void:
	for p: AudioStreamPlayer in _pool_2d:
		p.stop()
	for p: AudioStreamPlayer3D in _pool_3d:
		p.stop()


# =============================================================================
# Internals
# =============================================================================

func _exit_tree() -> void:
	# Release every playback before the engine shuts down (otherwise the
	# AudioServer still holds them at exit and Godot reports leaks).
	stop_all_world()
	for p: AudioStreamPlayer in _pool_ui:
		p.stop()
	for p: AudioStreamPlayer in [_hiss, _motor, _zoom]:
		if p != null:
			p.stop()
	# The mixer drops stopped playbacks on its next pass; give it one before the
	# engine tears down (scene nodes exit before this autoload, so their
	# AmbientEmitter / AmbienceBed players are covered too).
	if get_tree() != null and get_tree().root != null:
		OS.delay_msec(60)


func _process(delta: float) -> void:
	_process_zoom(delta)
	_process_reverb(delta)


func _build_pools() -> void:
	_holder_world = Node.new()
	_holder_world.name = "World2D"
	_holder_world.process_mode = Node.PROCESS_MODE_PAUSABLE
	add_child(_holder_world)
	_holder_ui = Node.new()
	_holder_ui.name = "UI"
	_holder_ui.process_mode = Node.PROCESS_MODE_ALWAYS
	add_child(_holder_ui)
	_holder_3d = Node3D.new()
	_holder_3d.name = "World3D"
	_holder_3d.process_mode = Node.PROCESS_MODE_PAUSABLE
	add_child(_holder_3d)
	for i in POOL_2D_SIZE:
		var p := AudioStreamPlayer.new()
		p.name = "P2D_%d" % i
		_holder_world.add_child(p)
		_pool_2d.append(p)
	for i in POOL_UI_SIZE:
		var p := AudioStreamPlayer.new()
		p.name = "PUI_%d" % i
		_holder_ui.add_child(p)
		_pool_ui.append(p)
	for i in POOL_3D_SIZE:
		var p := AudioStreamPlayer3D.new()
		p.name = "P3D_%d" % i
		_holder_3d.add_child(p)
		_pool_3d.append(p)


func _load_library() -> void:
	for id: StringName in SoundLibrary.ids():
		_defs[id] = SoundLibrary.get_def(id)
		var variants := SoundLibrary.load_variants(id)
		if variants.is_empty():
			push_warning("Audio: no files for sound id '%s' in %s%s/" % [id, SoundLibrary.ROOT, id])
		_streams[id] = variants


func _pick(id: StringName) -> AudioStream:
	if not _streams.has(id):
		_warn_once(id, "Audio: unknown sound id '%s'" % id)
		return null
	var arr: Array = _streams[id]
	if arr.is_empty():
		_warn_once(id, "Audio: sound id '%s' has no loaded files" % id)
		return null
	if arr.size() == 1:
		return arr[0]
	var last: int = _last_variant.get(id, -1)
	var i := randi() % (arr.size() - 1) if last >= 0 else randi() % arr.size()
	if last >= 0 and i >= last:
		i += 1  # never the same variant twice in a row
	_last_variant[id] = i
	return arr[i]


func _warn_once(key: StringName, msg: String) -> void:
	if _warned.has(key):
		return
	_warned[key] = true
	push_warning(msg)


func _jitter_volume(def: Dictionary, extra_db: float) -> float:
	var v: float = def[&"volume_var_db"]
	return float(def[&"volume_db"]) + extra_db + randf_range(-v, v)


func _jitter_pitch(def: Dictionary, pitch: float) -> float:
	var v: float = def[&"pitch_var"]
	return maxf(0.05, pitch * (1.0 + randf_range(-v, v)))


func _configure_3d(p: AudioStreamPlayer3D, id: StringName, stream: AudioStream, volume_db: float, pitch: float) -> void:
	var def: Dictionary = _defs[id]
	configure_player_3d(p, id)
	p.stream = stream
	p.volume_db = _jitter_volume(def, volume_db)
	p.pitch_scale = _jitter_pitch(def, pitch)
	p.attenuation_model = AudioStreamPlayer3D.ATTENUATION_INVERSE_DISTANCE
	p.doppler_tracking = AudioStreamPlayer3D.DOPPLER_TRACKING_DISABLED


func _take_2d(pool: Array[AudioStreamPlayer]) -> AudioStreamPlayer:
	var oldest: AudioStreamPlayer = pool[0]
	var oldest_t := 1 << 62
	for p: AudioStreamPlayer in pool:
		if not p.playing:
			return p
		var t: int = _started_at.get(p.get_instance_id(), 0)
		if t < oldest_t:
			oldest_t = t
			oldest = p
	oldest.stop()
	return oldest


func _take_3d() -> AudioStreamPlayer3D:
	var oldest: AudioStreamPlayer3D = _pool_3d[0]
	var oldest_t := 1 << 62
	for p: AudioStreamPlayer3D in _pool_3d:
		if not p.playing:
			return p
		var t: int = _started_at.get(p.get_instance_id(), 0)
		if t < oldest_t:
			oldest_t = t
			oldest = p
	oldest.stop()
	return oldest


# --- footsteps ---------------------------------------------------------------

func _on_player_footstep(surface: StringName, position: Vector3, intensity: float) -> void:
	play_footstep(surface, position, intensity)


func _on_player_landed(surface: StringName, position: Vector3, impact: float) -> void:
	var k := clampf(impact, 0.0, 1.0)
	# both feet land: a heavier step, then the second foot a moment later
	play_footstep(surface, position, lerpf(0.75, 1.0, k))
	var second := get_tree().create_timer(lerpf(0.07, 0.04, k), false)
	second.timeout.connect(play_footstep.bind(surface, position + Vector3(0.18, 0.0, 0.0), lerpf(0.45, 0.8, k)))
	if k > 0.55:
		play_at(&"thud_soft", position, linear_to_db(k) - 9.0, 1.05)


# --- settings ----------------------------------------------------------------

func _apply_all_settings() -> void:
	for key: StringName in BUS_FOR_SETTING:
		_apply_bus_volume(key, Settings.get_value(&"audio", key))


func _on_setting_changed(section: StringName, key: StringName, value: Variant) -> void:
	if section == &"audio" and BUS_FOR_SETTING.has(key):
		_apply_bus_volume(key, value)


func _apply_bus_volume(key: StringName, value: Variant) -> void:
	var idx := AudioServer.get_bus_index(BUS_FOR_SETTING[key])
	if idx < 0:
		_warn_once(StringName("bus:%s" % key), "Audio: bus '%s' missing from the bus layout" % BUS_FOR_SETTING[key])
		return
	var lin := clampf(float(value) if value != null else 1.0, 0.0, 1.0)
	AudioServer.set_bus_volume_db(idx, linear_to_db(maxf(lin, 0.0001)))
	AudioServer.set_bus_mute(idx, lin <= 0.0001)


# --- camcorder layer -----------------------------------------------------------

func _build_camcorder_layer() -> void:
	_hiss = _make_layer_player("TapeHiss")
	_motor = _make_layer_player("CamcorderMotor")
	_zoom = _make_layer_player("ZoomMotor")
	_update_camcorder_layer()


func _make_layer_player(node_name: String) -> AudioStreamPlayer:
	var p := AudioStreamPlayer.new()
	p.name = node_name
	_holder_world.add_child(p)
	return p


func _update_camcorder_layer() -> void:
	if _hiss == null:
		return
	_set_layer(_hiss, &"tape_hiss", tape_hiss_db, camcorder_layer_enabled)
	_set_layer(_motor, &"camcorder_motor", camcorder_motor_db, camcorder_layer_enabled)


func _set_layer(p: AudioStreamPlayer, id: StringName, extra_db: float, on: bool) -> void:
	if not on:
		p.stop()
		return
	var s := _pick(id)
	if s == null:
		return
	var def: Dictionary = _defs[id]
	p.stream = s
	p.bus = def[&"bus"]
	p.volume_db = float(def[&"volume_db"]) + extra_db
	if not p.playing:
		p.play(randf() * maxf(s.get_length() - 0.1, 0.0))


func _on_camera_zoom_changed(amount: float) -> void:
	var now := Time.get_ticks_msec()
	if _zoom_last_amount >= 0.0 and is_equal_approx(amount, _zoom_last_amount):
		return
	var dt := maxf(float(now - _zoom_last_change_ms) / 1000.0, 0.008)
	if _zoom_last_amount >= 0.0 and dt < 0.5:
		_zoom_speed = lerpf(_zoom_speed, absf(amount - _zoom_last_amount) / dt, 0.3)
	_zoom_last_amount = amount
	_zoom_last_change_ms = now
	if _zoom.stream == null:
		_zoom.stream = _pick(&"camcorder_zoom")
		if _zoom.stream == null:
			return
		_zoom.bus = _defs[&"camcorder_zoom"][&"bus"]
	if not _zoom.playing:
		_zoom.volume_db = -40.0
		_zoom.play(randf() * maxf(_zoom.stream.get_length() - 0.1, 0.0))


func _process_zoom(delta: float) -> void:
	if _zoom == null or not _zoom.playing:
		return
	if get_tree().paused:
		return
	var moving := Time.get_ticks_msec() - _zoom_last_change_ms < int(zoom_motor_hold * 1000.0)
	var base: float = _defs[&"camcorder_zoom"][&"volume_db"]
	var target := base if moving else -60.0
	# spin-up is quick, spin-down a touch slower (motor inertia)
	var rate := 160.0 if moving else 90.0
	_zoom.volume_db = move_toward(_zoom.volume_db, target, rate * delta)
	var pitch_target := clampf(0.92 + _zoom_speed * 0.25, 0.92, 1.12) if moving else 0.85
	_zoom.pitch_scale = lerpf(_zoom.pitch_scale, pitch_target, minf(1.0, delta * 12.0))
	if not moving and _zoom.volume_db <= -59.0:
		_zoom.stop()
		_zoom_speed = 0.0


# --- room reverb ---------------------------------------------------------------

func _find_reverb() -> void:
	var idx := AudioServer.get_bus_index(&"World")
	if idx < 0:
		return
	for i in AudioServer.get_bus_effect_count(idx):
		var e := AudioServer.get_bus_effect(idx, i)
		if e is AudioEffectReverb:
			_reverb = e as AudioEffectReverb
			break
	if _reverb != null:
		_reverb.room_size = DEFAULT_REVERB[&"room_size"]
		_reverb.damping = DEFAULT_REVERB[&"damping"]
		_reverb.wet = DEFAULT_REVERB[&"wet"]
		_reverb.predelay_msec = DEFAULT_REVERB[&"predelay_msec"]


func _update_reverb_target() -> void:
	_reverb_target = DEFAULT_REVERB.duplicate()
	if not _reverb_zones.is_empty():
		_reverb_target.merge(_reverb_zones[-1][&"params"], true)


func _process_reverb(delta: float) -> void:
	if _reverb == null:
		return
	var k := 1.0 if reverb_blend_time <= 0.0 else minf(1.0, delta * 3.0 / reverb_blend_time)
	_reverb.room_size = lerpf(_reverb.room_size, float(_reverb_target[&"room_size"]), k)
	_reverb.damping = lerpf(_reverb.damping, float(_reverb_target[&"damping"]), k)
	_reverb.wet = lerpf(_reverb.wet, float(_reverb_target[&"wet"]), k)
	_reverb.predelay_msec = lerpf(_reverb.predelay_msec, float(_reverb_target[&"predelay_msec"]), k)
