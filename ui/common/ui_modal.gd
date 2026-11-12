class_name UIModal
extends Control
## Base for full-screen views that take input away from the player
## (examine view, document reader).
##
## - `begin_open()` shows the view and takes `Game.lock_input(self)`.
## - Interact (E / pad A) or a mouse click closes it, but only once "armed":
##   the press that opened the view has been released and a short delay has
##   passed, so the opening click can never close it again.
## - ui_back / pause are routed here by UIRoot, which also stops the same
##   Escape press from opening the pause menu.
## - `request_close()` hides at once; the input lock is released when the
##   buttons are let go (see UIInput.unlock_when_released).

signal opened
signal closed

## Ignore close presses for this long after opening.
@export var arm_delay: float = 0.2
## Fade time for the whole view.
@export var fade_time: float = 0.18

## A mouse press that moves less than this (px) before release is a "click".
const CLICK_SLOP := 6.0
const CLICK_MAX_MS := 350

var _open: bool = false
var _armed: bool = false
var _opened_at_ms: int = 0
var _click_start := Vector2.ZERO
var _click_start_ms: int = -1
var _fade: Tween


func _ready() -> void:
	visible = false
	modulate.a = 0.0
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP


func is_open() -> bool:
	return _open


func is_armed() -> bool:
	return _armed


func begin_open() -> void:
	_open = true
	_armed = false
	_click_start_ms = -1
	_opened_at_ms = Time.get_ticks_msec()
	Game.lock_input(self)
	visible = true
	_fade_to(1.0)
	opened.emit()


func request_close() -> void:
	if not _open:
		return
	_open = false
	_armed = false
	_on_close()
	_fade_to(0.0)
	closed.emit()
	UIInput.unlock_when_released(self)


## Override: stop sounds, emit the Events "closed" signal, free visuals.
func _on_close() -> void:
	pass


func _process(_delta: float) -> void:
	if _open and not _armed:
		if Time.get_ticks_msec() - _opened_at_ms >= int(arm_delay * 1000.0) \
				and not UIInput.any_guarded_held():
			_armed = true


func _input(event: InputEvent) -> void:
	if not _open:
		return
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_LEFT:
			if mb.pressed:
				_click_start = mb.position
				_click_start_ms = Time.get_ticks_msec() if _armed else -1
			elif _click_start_ms >= 0:
				var quick := Time.get_ticks_msec() - _click_start_ms <= CLICK_MAX_MS
				var still := mb.position.distance_to(_click_start) <= CLICK_SLOP
				_click_start_ms = -1
				if quick and still and _armed and _click_closes():
					get_viewport().set_input_as_handled()
					request_close()
			return
	if _armed and event.is_action_pressed(&"interact") and not event.is_echo():
		get_viewport().set_input_as_handled()
		request_close()


## Override to stop a plain click from closing (e.g. while over a scrollbar).
func _click_closes() -> bool:
	return true


func _fade_to(a: float) -> void:
	if _fade:
		_fade.kill()
	_fade = create_tween()
	_fade.tween_property(self, ^"modulate:a", a, fade_time)
	if a <= 0.0:
		_fade.tween_callback(func() -> void:
			if not _open:
				visible = false
				_on_hidden())


## Override: called once the close fade has finished.
func _on_hidden() -> void:
	pass
