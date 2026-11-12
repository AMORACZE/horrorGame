class_name InputGlyph
extends PanelContainer
## A small key-cap ("E") or pad button ("A") for an input action. Follows the
## last-used device automatically. Use `keyboard_text` / `gamepad_text` for
## hints that are not a single action ("Drag", "R stick").

@export var action: StringName = &"interact":
	set(v):
		action = v
		refresh()
@export var keyboard_text: String = "":
	set(v):
		keyboard_text = v
		refresh()
@export var gamepad_text: String = "":
	set(v):
		gamepad_text = v
		refresh()

var _label: Label


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	size_flags_vertical = Control.SIZE_SHRINK_CENTER
	_ensure_label()
	if InputGlyphs.current:
		InputGlyphs.current.device_changed.connect(_on_device_changed)
	refresh()


func _ensure_label() -> void:
	if _label:
		return
	_label = Label.new()
	_label.theme_type_variation = &"GlyphText"
	_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_label.custom_minimum_size = Vector2(9, 18)
	_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_label, false, Node.INTERNAL_MODE_FRONT)


func _on_device_changed(_pad: bool) -> void:
	refresh()


func get_text() -> String:
	return _label.text if _label else ""


func refresh() -> void:
	if not is_inside_tree():
		return
	_ensure_label()
	var pad := InputGlyphs.using_gamepad
	var text := ""
	if pad and gamepad_text != "":
		text = gamepad_text
	elif not pad and keyboard_text != "":
		text = keyboard_text
	else:
		text = InputGlyphs.label_for(action, pad)
	_label.text = text
	theme_type_variation = &"PadCap" if InputGlyphs.is_round_glyph(text) else &"KeyCap"
