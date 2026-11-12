class_name LoopEmitter
extends Node3D
## A positional looping sound owned by a fixture (fridge hum, faucet, static).
##
## Uses `Audio.get_stream(id)` on bus "SFX". Null-safe: with no stream the
## emitter still tracks whether it *should* be playing, so behaviour and tests
## do not depend on audio content existing. Re-triggers on `finished`, so a
## stream that was not imported as looping still loops.

@export var sound_id: StringName = &""
@export var autoplay_loop: bool = false
@export var volume_db: float = -6.0
@export_range(0.1, 20.0, 0.1) var unit_size: float = 2.0
@export_range(0.0, 100.0, 0.5, "suffix:m") var max_distance: float = 18.0

var _player: AudioStreamPlayer3D = null


func _ready() -> void:
	_player = create_player(self, sound_id, volume_db, unit_size, max_distance)
	if autoplay_loop:
		play()


func play() -> void:
	if _player:
		set_playing(_player, true)


func stop() -> void:
	if _player:
		set_playing(_player, false)


## Whether the loop has been asked to play (true even with no stream loaded).
func is_active() -> bool:
	return _player != null and bool(_player.get_meta(&"loop_wanted", false))


func get_player() -> AudioStreamPlayer3D:
	return _player


## Make an AudioStreamPlayer3D child of `parent` for a looping id.
static func create_player(parent: Node, id: StringName, vol_db: float = -6.0,
		unit: float = 2.0, max_dist: float = 18.0) -> AudioStreamPlayer3D:
	var p := AudioStreamPlayer3D.new()
	p.name = "Loop_%s" % String(id)
	p.bus = &"SFX"
	p.volume_db = vol_db
	p.unit_size = unit
	p.max_distance = max_dist
	p.stream = Audio.get_stream(id) if id != &"" else null
	p.set_meta(&"loop_wanted", false)
	p.finished.connect(func() -> void:
		if bool(p.get_meta(&"loop_wanted", false)) and p.stream and p.is_inside_tree():
			p.play())
	# Start a loop that was asked for before the player reached the tree.
	p.tree_entered.connect(func() -> void:
		if bool(p.get_meta(&"loop_wanted", false)) and p.stream and not p.playing:
			p.play.call_deferred(randf() * maxf(p.stream.get_length() - 0.1, 0.0)))
	if parent.is_node_ready() or not parent.is_inside_tree():
		parent.add_child(p)
	else:
		# Called from a child's _ready while the parent is still adding children.
		parent.add_child.call_deferred(p)
	return p


static func set_playing(p: AudioStreamPlayer3D, on: bool) -> void:
	p.set_meta(&"loop_wanted", on)
	if on:
		if p.stream and p.is_inside_tree() and not p.playing:
			p.play(randf() * maxf(p.stream.get_length() - 0.1, 0.0))
	elif p.playing:
		p.stop()


static func is_wanted(p: AudioStreamPlayer3D) -> bool:
	return p != null and bool(p.get_meta(&"loop_wanted", false))
