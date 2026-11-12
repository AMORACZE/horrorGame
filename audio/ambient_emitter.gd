@tool
class_name AmbientEmitter
extends Node3D
## A looping positional sound source: fridge, clock, fly at a window, ballast hum.
##
## Drop audio/ambient_emitter.tscn into a level, set `sound_id`, place it at the
## sound's source (the fridge's kick plate, the clock face, the window pane).
## Distance settings come from audio/sound_library.gd unless overridden here.

@export var sound_id: StringName = &"fridge_hum":
	set(v):
		sound_id = v
		update_configuration_warnings()
## Added to the library's mix level for this id.
@export_range(-40.0, 12.0, 0.5, "suffix:dB") var volume_db: float = 0.0
## Audible range in metres; 0 = library default for the id.
@export_range(0.0, 100.0, 0.5, "suffix:m") var max_distance: float = 0.0
## Distance at which the sound plays at full level; 0 = library default.
@export_range(0.0, 20.0, 0.1, "suffix:m") var unit_size: float = 0.0
@export var autoplay: bool = true
## Start somewhere random in the loop so two identical emitters never phase.
@export var random_start_offset: bool = true

@export_group("Pitch drift")
## Slow random pitch wander as a fraction (0.01 = +-1 %). Mains hums: keep 0.
@export_range(0.0, 0.1, 0.001) var pitch_drift: float = 0.0
## Rough period of the wander in seconds.
@export_range(0.5, 60.0, 0.5, "suffix:s") var pitch_drift_period: float = 9.0
@export_range(0.25, 4.0, 0.01) var base_pitch: float = 1.0

var player: AudioStreamPlayer3D
var _t: float = 0.0
var _phase_a: float = 0.0
var _phase_b: float = 0.0
var _fade_tween: Tween
var _resume_on_enter: bool = false


func _ready() -> void:
	if Engine.is_editor_hint():
		return
	player = AudioStreamPlayer3D.new()
	player.name = "Player"
	add_child(player)
	_phase_a = randf() * TAU
	_phase_b = randf() * TAU
	if autoplay:
		start()


func _get_configuration_warnings() -> PackedStringArray:
	if not SoundLibrary.has(sound_id):
		return PackedStringArray(["Unknown sound_id '%s' (see audio/sound_library.gd)" % sound_id])
	return PackedStringArray()


## Start (or restart) the loop, optionally fading in over `fade` seconds.
func start(fade: float = 0.0) -> void:
	if player == null:
		return
	var s := Audio.get_stream(sound_id)
	if s == null:
		return
	Audio.configure_player_3d(player, sound_id)
	if max_distance > 0.0:
		player.max_distance = max_distance
	if unit_size > 0.0:
		player.unit_size = unit_size
	player.stream = s
	var target := float(Audio.get_def(sound_id).get(&"volume_db", 0.0)) + volume_db
	player.pitch_scale = base_pitch
	var from := randf() * maxf(s.get_length() - 0.05, 0.0) if random_start_offset else 0.0
	if _fade_tween:
		_fade_tween.kill()
	if fade > 0.0:
		player.volume_db = -60.0
		_fade_tween = create_tween()
		_fade_tween.tween_property(player, "volume_db", target, fade).set_trans(Tween.TRANS_SINE)
	else:
		player.volume_db = target
	player.play(from)


## Stop, optionally fading out (an appliance switching off should not cut dead).
func stop(fade: float = 0.0) -> void:
	if player == null or not player.playing:
		return
	if _fade_tween:
		_fade_tween.kill()
	if fade <= 0.0:
		player.stop()
		return
	_fade_tween = create_tween()
	_fade_tween.tween_property(player, "volume_db", -60.0, fade).set_trans(Tween.TRANS_SINE)
	_fade_tween.tween_callback(player.stop)


func _enter_tree() -> void:
	if _resume_on_enter and player != null:
		_resume_on_enter = false
		start()


func _exit_tree() -> void:
	if player != null and player.playing:
		_resume_on_enter = true  # re-parenting keeps it going
		player.stop()  # release the playback before shutdown (see Audio._exit_tree)


func is_playing() -> bool:
	return player != null and player.playing


func _process(delta: float) -> void:
	if Engine.is_editor_hint() or player == null or pitch_drift <= 0.0 or not player.playing:
		return
	_t += delta
	var w := TAU / pitch_drift_period
	# two incommensurate sines: smooth, never visibly periodic
	var d := 0.6 * sin(_t * w + _phase_a) + 0.4 * sin(_t * w * 0.37 + _phase_b)
	player.pitch_scale = base_pitch * (1.0 + pitch_drift * d)
