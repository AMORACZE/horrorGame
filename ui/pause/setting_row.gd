class_name SettingRow
extends HBoxContainer
## One line of the settings page: label, control (slider or On/Off), readout.
## Writes through Settings.set_value and follows Events.setting_changed, so a
## "Reset to defaults" or a change made elsewhere shows up immediately.

signal focus_gained(row: SettingRow)

const MARKER_WIDTH := 2.0
const LABEL_WIDTH := 300.0
const CONTROL_WIDTH := 240.0
const VALUE_WIDTH := 70.0

var section: StringName
var key: StringName
var info: Dictionary = {}
var is_toggle: bool = false

var _label: Label
var _slider: HSlider
var _toggle: Button
var _value: Label
var _focused: bool = false
var _dragging: bool = false
var _last_tick_ms: int = 0


func setup(p_section: StringName, p_key: StringName, default_value: Variant) -> void:
	section = p_section
	key = p_key
	info = SettingsSchema.describe(section, key, default_value)
	is_toggle = default_value is bool
	name = "%s_%s" % [section, key]


func _ready() -> void:
	add_theme_constant_override(&"separation", 0)
	custom_minimum_size.y = 34.0
	mouse_filter = Control.MOUSE_FILTER_PASS

	var pad := Control.new()
	pad.custom_minimum_size.x = 16.0
	pad.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(pad)

	_label = Label.new()
	_label.theme_type_variation = &"SettingLabel"
	_label.text = info.get("label", String(key))
	_label.custom_minimum_size.x = LABEL_WIDTH
	_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	add_child(_label)

	if is_toggle:
		_toggle = Button.new()
		_toggle.theme_type_variation = &"SettingToggle"
		_toggle.toggle_mode = true
		_toggle.alignment = HORIZONTAL_ALIGNMENT_LEFT
		_toggle.custom_minimum_size.x = CONTROL_WIDTH + VALUE_WIDTH
		_toggle.focus_mode = Control.FOCUS_ALL
		_toggle.toggled.connect(_on_toggled)
		_toggle.gui_input.connect(_on_toggle_gui_input)
		add_child(_toggle)
		_wire_focus(_toggle)
	else:
		_slider = HSlider.new()
		_slider.min_value = float(info["min"])
		_slider.max_value = float(info["max"])
		_slider.step = float(info["step"])
		_slider.custom_minimum_size = Vector2(CONTROL_WIDTH, 20.0)
		_slider.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		_slider.focus_mode = Control.FOCUS_ALL
		_slider.value_changed.connect(_on_slider_changed)
		_slider.drag_started.connect(func() -> void: _dragging = true)
		_slider.drag_ended.connect(_on_drag_ended)
		add_child(_slider)
		_wire_focus(_slider)
		_value = Label.new()
		_value.theme_type_variation = &"SettingValue"
		_value.custom_minimum_size.x = VALUE_WIDTH
		_value.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		_value.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		add_child(_value)
	# Room for the scroll bar on the right.
	var tail := Control.new()
	tail.custom_minimum_size.x = 24.0
	tail.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(tail)

	mouse_entered.connect(func() -> void: get_focus_control().grab_focus())
	Events.setting_changed.connect(_on_setting_changed)
	refresh()


## The control that takes keyboard / pad focus.
func get_focus_control() -> Control:
	return _toggle if is_toggle else _slider


func get_slider() -> HSlider:
	return _slider


func get_toggle() -> Button:
	return _toggle


func get_value_text() -> String:
	if is_toggle:
		return _toggle.text
	return _value.text


## Re-read the stored value without writing it back.
func refresh() -> void:
	var v: Variant = Settings.get_value(section, key)
	if is_toggle:
		_toggle.set_pressed_no_signal(bool(v))
		_toggle.text = "On" if bool(v) else "Off"
	else:
		_slider.set_value_no_signal(float(v))
		_value.text = SettingsSchema.format_value(float(v), String(info.get("fmt", "num")))
	_update_colors()


func _wire_focus(c: Control) -> void:
	c.focus_entered.connect(func() -> void:
		_focused = true
		_update_colors()
		focus_gained.emit(self))
	c.focus_exited.connect(func() -> void:
		_focused = false
		_update_colors())
	c.mouse_entered.connect(func() -> void: c.grab_focus())


func _update_colors() -> void:
	var c := UIStyle.TEXT if _focused else UIStyle.TEXT_DIM
	_label.add_theme_color_override(&"font_color", c)
	if _value:
		_value.add_theme_color_override(&"font_color", c)
	if _toggle:
		var on := _toggle.button_pressed
		var tc := c if on else Color(c, c.a * 0.7)
		for n: StringName in [&"font_color", &"font_hover_color", &"font_focus_color",
				&"font_pressed_color", &"font_hover_pressed_color"]:
			_toggle.add_theme_color_override(n, tc)
	queue_redraw()


func _draw() -> void:
	if _focused:
		draw_rect(Rect2(0.0, 5.0, MARKER_WIDTH, size.y - 10.0), Color(UIStyle.TEXT, 0.9))


func _on_toggled(on: bool) -> void:
	_toggle.text = "On" if on else "Off"
	UIInput.sound(&"ui_tick")
	Settings.set_value(section, key, on)
	_update_colors()


func _on_toggle_gui_input(event: InputEvent) -> void:
	if event.is_action_pressed(&"ui_left") or event.is_action_pressed(&"ui_right"):
		_toggle.button_pressed = not _toggle.button_pressed
		_toggle.accept_event()


func _on_slider_changed(v: float) -> void:
	var stored: Variant = Settings.get_value(section, key)
	var out: Variant = int(round(v)) if stored is int else v
	_value.text = SettingsSchema.format_value(v, String(info.get("fmt", "num")))
	Settings.set_value(section, key, out, not _dragging)
	var now := Time.get_ticks_msec()
	if now - _last_tick_ms > 70:
		_last_tick_ms = now
		UIInput.sound(&"ui_tick")


func _on_drag_ended(_changed: bool) -> void:
	_dragging = false
	Settings.save()


func _on_setting_changed(p_section: StringName, p_key: StringName, _value_v: Variant) -> void:
	if p_section == section and p_key == key:
		refresh()
