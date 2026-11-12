class_name ObservationLine
extends Control
## One short first-person line, low on screen: typed on quickly, held for a time
## scaled by its length, then faded. Never takes input.
##
## Queueing: a new line while one is up shortens the current line's hold to a
## minimum read time, then follows it. At most `max_queue` lines wait; older
## waiting lines are dropped (only the latest thoughts matter). Repeating the
## line that is already up just restarts its hold.

enum State { IDLE, TYPING, HOLD, FADING }

@export var chars_per_second: float = 75.0
@export var hold_base: float = 1.4
@export var hold_per_char: float = 0.055
@export var hold_min: float = 2.0
@export var hold_max: float = 7.5
## When something is waiting, the current line stays at least this long once fully typed.
@export var min_read_when_queued: float = 0.9
@export var fade_time: float = 0.7
@export var fade_time_queued: float = 0.18
@export var max_queue: int = 2

@onready var _label: Label = %Text
## Soft dark patch behind the text; follows the text's opacity.
@onready var _scrim: Control = %Scrim

var _state: State = State.IDLE
var _queue: PackedStringArray = []
var _shown_chars: float = 0.0
var _hold_left: float = 0.0
var _held_for: float = 0.0
var _fade_left: float = 0.0
var _fade_total: float = 1.0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_PAUSABLE
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_label.text = ""
	_label.modulate.a = 0.0
	_scrim.modulate.a = 0.0
	Events.observation_requested.connect(show_line)


## The line currently on screen ("" when idle).
func get_current_text() -> String:
	return "" if _state == State.IDLE else _label.text


func is_showing() -> bool:
	return _state != State.IDLE


func get_queue() -> PackedStringArray:
	return _queue.duplicate()


func show_line(text: String) -> void:
	text = text.strip_edges()
	if text == "":
		return
	if _state == State.IDLE:
		_start(text)
		return
	if text == _label.text and _state != State.FADING:
		_hold_left = maxf(_hold_left, _hold_for(text))
		return
	if not _queue.is_empty() and _queue[_queue.size() - 1] == text:
		return
	_queue.append(text)
	while _queue.size() > max_queue:
		_queue.remove_at(0)
	if _state == State.FADING and _fade_total > fade_time_queued:
		# Already on its way out: finish quickly so the new line is not kept waiting.
		var a := _label.modulate.a
		_fade_total = fade_time_queued
		_fade_left = a * _fade_total


## Drop everything immediately.
func clear() -> void:
	_queue.clear()
	_state = State.IDLE
	_label.text = ""
	_label.modulate.a = 0.0


func _hold_for(text: String) -> float:
	return clampf(hold_base + hold_per_char * text.length(), hold_min, hold_max)


func _start(text: String) -> void:
	_label.text = text
	_label.visible_characters = 0
	_label.modulate.a = 1.0
	# Fit the scrim to the text (one line, or the wrap width for longer ones).
	var font := _label.get_theme_font(&"font")
	var fsize := _label.get_theme_font_size(&"font_size")
	var tw := minf(font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, fsize).x, _label.size.x)
	var lines := maxi(_label.get_line_count(), 1)
	_scrim.offset_left = -(tw * 0.5 + 110.0)
	_scrim.offset_right = tw * 0.5 + 110.0
	_scrim.offset_top = -78.0 - float(lines) * 28.0 - 40.0
	_shown_chars = 0.0
	_hold_left = _hold_for(text)
	_held_for = 0.0
	_state = State.TYPING


func _process(delta: float) -> void:
	_scrim.modulate.a = _label.modulate.a if _state != State.IDLE else 0.0
	match _state:
		State.TYPING:
			_shown_chars += chars_per_second * delta
			var total := _label.get_total_character_count()
			_label.visible_characters = int(_shown_chars)
			if _shown_chars >= total:
				_label.visible_characters = -1
				_state = State.HOLD
		State.HOLD:
			_held_for += delta
			_hold_left -= delta
			if not _queue.is_empty():
				_hold_left = minf(_hold_left, maxf(min_read_when_queued - _held_for, 0.0))
			if _hold_left <= 0.0:
				_fade_total = fade_time if _queue.is_empty() else fade_time_queued
				_fade_left = _fade_total
				_state = State.FADING
		State.FADING:
			_fade_left -= delta
			_label.modulate.a = clampf(_fade_left / _fade_total, 0.0, 1.0)
			if _fade_left <= 0.0:
				if _queue.is_empty():
					_state = State.IDLE
					_label.text = ""
				else:
					var next := _queue[0]
					_queue.remove_at(0)
					_start(next)
