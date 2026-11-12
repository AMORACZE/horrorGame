class_name HUD
extends Control
## Reticle dot + interaction prompt ("E  Open  ·  Front door").
##
## Driven only by Events: interaction_focus_changed sets the focused component,
## interacted refreshes its text (prompts change: Open <-> Close), and
## input_lock_changed hides everything while a modal / cutscene has control.

const SEPARATOR := "·"

@export var fade_in_time: float = 0.12
@export var fade_out_time: float = 0.2

@onready var _reticle: Reticle = %Reticle
@onready var _prompt: Control = %Prompt
@onready var _glyph: InputGlyph = %Glyph
@onready var _verb: Label = %Verb
@onready var _sep: Label = %Separator
@onready var _name: Label = %Name
@onready var _scrim: Control = %Scrim

var _focused: Interactable = null
var _prompt_tween: Tween
var _reticle_tween: Tween
var _hud_tween: Tween


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_PAUSABLE
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_sep.text = SEPARATOR
	_prompt.modulate.a = 0.0
	_scrim.modulate.a = 0.0
	Events.interaction_focus_changed.connect(_on_focus_changed)
	Events.interacted.connect(_on_interacted)
	Events.input_lock_changed.connect(_on_input_lock_changed)
	_apply_lock(Game.is_input_locked(), true)
	_refresh()


func get_focused() -> Interactable:
	return _focused if is_instance_valid(_focused) else null


## Whether a prompt is currently meant to be on screen.
func is_prompt_shown() -> bool:
	return visible and get_focused() != null and _prompt.visible


## The prompt as one string, e.g. "E  Open  ·  Front door" (for tests / logs).
func get_prompt_text() -> String:
	if get_focused() == null:
		return ""
	var parts: PackedStringArray = [_glyph.get_text()]
	if _verb.visible:
		parts.append(_verb.text)
	if _name.visible:
		if _verb.visible:
			parts.append(SEPARATOR)
		parts.append(_name.text)
	return "  ".join(parts)


func _on_focus_changed(interactable: Interactable) -> void:
	_focused = interactable
	_refresh()


func _on_interacted(interactable: Interactable, _interactor: Node) -> void:
	if interactable == _focused:
		_refresh()
		# Some behaviours flip their state a frame later (tweens, deferred calls).
		_refresh.call_deferred()


func _on_input_lock_changed(_locked: bool) -> void:
	_apply_lock(Game.is_input_locked(), false)


func _apply_lock(locked: bool, instant: bool) -> void:
	if _hud_tween:
		_hud_tween.kill()
	if locked:
		modulate.a = 0.0
		visible = false
		return
	visible = true
	if instant:
		modulate.a = 1.0
	else:
		_hud_tween = create_tween()
		_hud_tween.tween_property(self, ^"modulate:a", 1.0, 0.35)
	_refresh()


func _refresh() -> void:
	var it := get_focused()
	var has := it != null
	if has:
		var verb := it.get_prompt().strip_edges()
		var nm := it.get_display_name().strip_edges()
		_verb.text = verb
		_name.text = nm
		_verb.visible = verb != ""
		_name.visible = nm != ""
		_sep.visible = _verb.visible and _name.visible
		_glyph.refresh()
		_prompt.visible = _verb.visible or _name.visible
		_fit_scrim.call_deferred()
	_tween_focus(has)


## Soft dark patch behind the prompt, sized to its text: invisible on a dark
## wall, enough to hold white type over a blown-out window.
func _fit_scrim() -> void:
	var w := _prompt.get_combined_minimum_size().x + 140.0
	_scrim.offset_left = -w * 0.5
	_scrim.offset_right = w * 0.5


func _tween_focus(has: bool) -> void:
	if _reticle_tween:
		_reticle_tween.kill()
	_reticle_tween = create_tween()
	_reticle_tween.tween_property(_reticle, ^"focus_amount", 1.0 if has else 0.0,
		fade_in_time if has else fade_out_time)
	if _prompt_tween:
		_prompt_tween.kill()
	_prompt_tween = create_tween()
	_prompt_tween.set_parallel(true)
	_prompt_tween.tween_property(_prompt, ^"modulate:a", 1.0 if has else 0.0,
		fade_in_time if has else fade_out_time)
	_prompt_tween.tween_property(_scrim, ^"modulate:a", 1.0 if has else 0.0,
		fade_in_time if has else fade_out_time)
