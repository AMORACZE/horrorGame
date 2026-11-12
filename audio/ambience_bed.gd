class_name AmbienceBed
extends Node
## Non-positional stereo ambience: the room's tone and the afternoon outside.
##
## One per level (or per area). Each entry in `sound_ids` gets its own player on
## its library bus (Ambience), started at a random point and faded in.
## `volumes_db[i]` is added to the library mix level of `sound_ids[i]`.

@export var sound_ids: Array[StringName] = [&"room_tone", &"outside_afternoon"]
@export var volumes_db: Array[float] = [0.0, 0.0]
@export_range(0.0, 20.0, 0.1, "suffix:s") var fade_in_time: float = 3.0
@export var autoplay: bool = true

var players: Array[AudioStreamPlayer] = []
var _tweens: Dictionary = {}


func _ready() -> void:
	for i in sound_ids.size():
		var p := AudioStreamPlayer.new()
		p.name = "Bed_%s" % sound_ids[i]
		add_child(p)
		players.append(p)
	if autoplay:
		start(fade_in_time)


## Start every layer from a random point, fading in over `fade` seconds (-1 = fade_in_time).
func start(fade: float = -1.0) -> void:
	var f := fade_in_time if fade < 0.0 else fade
	for i in sound_ids.size():
		var id := sound_ids[i]
		var p := players[i]
		var s := Audio.get_stream(id)
		if s == null:
			continue
		p.stream = s
		p.bus = Audio.get_def(id).get(&"bus", &"Ambience")
		p.volume_db = -60.0 if f > 0.0 else _target_db(i)
		p.play(randf() * maxf(s.get_length() - 0.1, 0.0))
		_tween_to(i, f)


## Change one layer's offset (dB over its library level) over `time` seconds.
func set_layer_volume(index: int, offset_db: float, time: float = 1.0) -> void:
	if index < 0 or index >= players.size():
		return
	while volumes_db.size() <= index:
		volumes_db.append(0.0)
	volumes_db[index] = offset_db
	_tween_to(index, time)


func fade_out(time: float = 2.0) -> void:
	for i in players.size():
		var p := players[i]
		_kill_tween(i)
		var tw := create_tween()
		tw.tween_property(p, "volume_db", -60.0, time).set_trans(Tween.TRANS_SINE)
		tw.tween_callback(p.stop)
		_tweens[i] = tw


func _exit_tree() -> void:
	for p: AudioStreamPlayer in players:
		p.stop()  # release the playback before shutdown (see Audio._exit_tree)


func is_playing() -> bool:
	for p: AudioStreamPlayer in players:
		if p.playing:
			return true
	return false


func _tween_to(i: int, time: float) -> void:
	_kill_tween(i)
	var p := players[i]
	if time <= 0.0:
		p.volume_db = _target_db(i)
		return
	var tw := create_tween()
	tw.tween_property(p, "volume_db", _target_db(i), time).set_trans(Tween.TRANS_SINE)
	_tweens[i] = tw


func _kill_tween(i: int) -> void:
	if _tweens.has(i):
		var tw: Tween = _tweens[i]
		if tw != null and tw.is_valid():
			tw.kill()
		_tweens.erase(i)


func _target_db(i: int) -> float:
	var base := float(Audio.get_def(sound_ids[i]).get(&"volume_db", 0.0))
	return base + (volumes_db[i] if i < volumes_db.size() else 0.0)
