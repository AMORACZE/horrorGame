class_name ScreenFade
extends CanvasLayer
## Full-screen fade (layer 30: above the HUD, below the camcorder post-process,
## so a fade still reads as "the tape" rather than a menu).
##
## Any system can use it without a node path:
##   await ScreenFade.current.fade_out(1.0)      # to black
##   await ScreenFade.current.fade_in(2.0)
##   ScreenFade.current.set_covered(true)
## On Events.level_ready it holds black briefly, then fades in (the arrival).

signal fade_finished

static var current: ScreenFade = null

## Start fully black so the very first frame is already covered.
@export var start_covered: bool = true
## Arrival on Events.level_ready.
@export var arrival_hold: float = 0.35
@export var arrival_duration: float = 2.6
## If no level_ready arrives (sandbox, missing level), uncover anyway after this.
@export var safety_timeout: float = 4.0

@onready var _rect: ColorRect = $Cover

var _tween: Tween
var _arrived: bool = false


func _enter_tree() -> void:
	current = self


func _exit_tree() -> void:
	if current == self:
		current = null


func _ready() -> void:
	layer = 30
	process_mode = Node.PROCESS_MODE_ALWAYS
	_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_rect.color = Color.BLACK
	set_covered(start_covered)
	Events.level_ready.connect(_on_level_ready)
	if start_covered and safety_timeout > 0.0:
		get_tree().create_timer(safety_timeout, true).timeout.connect(func() -> void:
			if not _arrived and get_alpha() >= 0.999:
				fade_in(1.0))


## Current cover opacity, 0 (clear) .. 1 (covered).
func get_alpha() -> float:
	return _rect.color.a


func is_covered() -> bool:
	return _rect.color.a > 0.001


func set_covered(covered: bool, color: Color = Color.BLACK) -> void:
	if _tween:
		_tween.kill()
	_rect.color = Color(color, 1.0 if covered else 0.0)
	_rect.visible = covered


## Fade to `color` over `duration` seconds. Await it to continue afterwards.
func fade_out(duration: float = 0.6, color: Color = Color.BLACK) -> void:
	_rect.color = Color(color, _rect.color.a)
	await fade_to(1.0, duration)


## Fade from the current cover to clear.
func fade_in(duration: float = 0.6) -> void:
	await fade_to(0.0, duration)


func fade_to(alpha: float, duration: float, delay: float = 0.0) -> void:
	if _tween:
		_tween.kill()
	_rect.visible = true
	_tween = create_tween()
	_tween.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	if delay > 0.0:
		_tween.tween_interval(delay)
	_tween.tween_property(_rect, ^"color:a", alpha, maxf(duration, 0.0))
	await _tween.finished
	_rect.visible = _rect.color.a > 0.001
	fade_finished.emit()


func _on_level_ready(_level: Node) -> void:
	_arrived = true
	set_covered(true)
	await fade_to(0.0, arrival_duration, arrival_hold)
