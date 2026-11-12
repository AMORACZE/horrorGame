class_name SunburstClock
extends StaticBody3D
## 70s sunburst wall clock. The hands show the camcorder's afternoon time.
##
## Time source, in order: a node in group `camcorder_clock` that has a method
## `get_time_of_day_seconds() -> float` (seconds since midnight), if one exists;
## otherwise the clock keeps its own time starting at `start_hour:start_minute`.
## A stopped clock freezes at its start time and swaps to stopped observations.

const CLOCK_SOURCE_GROUP: StringName = &"camcorder_clock"
const CLOCK_SOURCE_METHOD: StringName = &"get_time_of_day_seconds"

@export_group("Time")
## Hour shown when the scene starts (24 h). 15 = 3 pm.
@export_range(0, 23) var start_hour: int = 15
@export_range(0, 59) var start_minute: int = 47
@export_range(0, 59) var start_second: int = 0
## Frozen hands. The second hand stops dead and the observations change.
@export var stopped: bool = false:
	set(value):
		stopped = value
		if is_node_ready():
			_apply_observations()
## Speed of the clock's own time when no camcorder clock exists (1 = real time).
@export_range(0.0, 60.0, 0.1) var time_scale: float = 1.0
## Follow the camcorder clock if one is present (ignored while stopped).
@export var follow_camcorder_clock: bool = true

@export_group("Sound")
## Play the `clock_tick` loop while running, if the audio library has it.
@export var tick_sound: bool = true

@export_group("Stopped text")
@export var stopped_observations: Array[String] = [
	"The second hand isn't moving.",
	"It says %s. The battery cover on the back is open.",
]

var _seconds: float = 0.0
var _shown_second: int = -1
var _running_observations: Array[String] = []
var _tick_player: AudioStreamPlayer3D

@onready var _hour_hand: Node3D = $Hands/HourHand
@onready var _minute_hand: Node3D = $Hands/MinuteHand
@onready var _second_hand: Node3D = $Hands/SecondHand
@onready var _interactable: Interactable = $Interactable


func _ready() -> void:
	_seconds = float(start_hour * 3600 + start_minute * 60 + start_second)
	_running_observations = _interactable.observations.duplicate()
	_apply_observations()
	_update_hands(true)
	if tick_sound and not stopped and Audio.has_sound(&"clock_tick"):
		_tick_player = AudioStreamPlayer3D.new()
		_tick_player.stream = Audio.get_stream(&"clock_tick")
		_tick_player.bus = &"SFX"
		_tick_player.unit_size = 1.5
		_tick_player.volume_db = -14.0
		add_child(_tick_player)
		_tick_player.play()


func _process(delta: float) -> void:
	if stopped:
		return
	var source := _clock_source() if follow_camcorder_clock else null
	if source != null:
		_seconds = float(source.call(CLOCK_SOURCE_METHOD))
	else:
		_seconds += delta * time_scale
	_update_hands(false)


## Seconds since midnight currently shown by the hands.
func get_shown_seconds() -> float:
	return _seconds


func _clock_source() -> Node:
	var n := get_tree().get_first_node_in_group(CLOCK_SOURCE_GROUP)
	if n != null and n.has_method(CLOCK_SOURCE_METHOD):
		return n
	return null


func _update_hands(force: bool) -> void:
	# Quartz movement: the second hand jumps once a second.
	var whole := int(floor(_seconds))
	if whole == _shown_second and not force:
		return
	_shown_second = whole
	var s := float(whole % 60)
	var m := fmod(float(whole) / 60.0, 60.0)
	var h := fmod(float(whole) / 3600.0, 12.0)
	_second_hand.rotation.z = -TAU * s / 60.0
	_minute_hand.rotation.z = -TAU * m / 60.0
	_hour_hand.rotation.z = -TAU * h / 12.0


func _apply_observations() -> void:
	if _interactable == null:
		return
	if stopped:
		var lines: Array[String] = []
		for line in stopped_observations:
			lines.append(line % _time_text() if line.contains("%s") else line)
		_interactable.observations = lines
	elif not _running_observations.is_empty():
		_interactable.observations = _running_observations.duplicate()


func _time_text() -> String:
	var total := int(_seconds) if _seconds > 0.0 else start_hour * 3600 + start_minute * 60
	var h := floori(total / 3600.0) % 12
	var m := floori(total / 60.0) % 60
	return "%d:%02d" % [12 if h == 0 else h, m]
