class_name DocumentReader
extends UIModal
## Full-screen reader for notes, labels and printed pages.
##
## On Events.document_requested the readable's title and body are laid out on a
## sheet dressed per ReadableInteractable.Style (see ReaderStyles). Long text
## scrolls with the wheel, W/S or arrows, or either stick. Interact or back
## closes it; Events.document_closed is emitted.

## Scroll speed for keys / sticks, pixels per second at full tilt.
@export var scroll_speed: float = 700.0
## Space kept free above and below the sheet.
@export var screen_margin: float = 56.0

@onready var _dim: ColorRect = %Dim
@onready var _sheet: PanelContainer = %Sheet
@onready var _margin: MarginContainer = %Margin
@onready var _scroll: ScrollContainer = %Scroll
@onready var _page: RuledPage = %Page
@onready var _title: Label = %Title
@onready var _rule: ColorRect = %Rule
@onready var _body: Label = %Body
@onready var _more: Label = %More

var _readable: ReadableInteractable = null
var _style: int = ReadableInteractable.Style.PAPER
var _look: ReaderStyles.Look
var _scroll_pos: float = 0.0


func _ready() -> void:
	super._ready()
	process_mode = Node.PROCESS_MODE_PAUSABLE
	_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	get_viewport().size_changed.connect(_layout_sheet)
	Events.document_requested.connect(open)


func get_readable() -> ReadableInteractable:
	return _readable


func get_style() -> int:
	return _style


func get_title_text() -> String:
	return _title.text


func get_body_text() -> String:
	return _body.text


## True when the body is longer than the sheet and can scroll.
func is_scrollable() -> bool:
	return _scroll.get_v_scroll_bar().max_value > _scroll.size.y + 1.0


func open(readable: ReadableInteractable) -> void:
	if readable == null:
		return
	_readable = readable
	_style = readable.style
	_look = ReaderStyles.for_style(_style)
	var t := readable.title.strip_edges()
	if t == "":
		t = readable.get_display_name()
	_title.text = t.to_upper() if _look.title_uppercase else t
	_title.visible = _title.text != ""
	_body.text = readable.body.strip_edges()
	_apply_look()
	_scroll_pos = 0.0
	_scroll.scroll_vertical = 0
	UIInput.sound(readable.open_sound)
	begin_open()
	_layout_sheet()


func _on_close() -> void:
	UIInput.sound(&"ui_close")
	Events.document_closed.emit()


func _on_hidden() -> void:
	_readable = null


func _apply_look() -> void:
	var l := _look
	var box := StyleBoxFlat.new()
	box.bg_color = l.paper
	box.border_color = l.paper.darkened(0.12)
	box.set_border_width_all(1)
	box.shadow_color = Color(0, 0, 0, 0.45)
	box.shadow_size = 22
	box.shadow_offset = Vector2(5, 9)
	_sheet.add_theme_stylebox_override(&"panel", box)
	for side: String in ["left", "right"]:
		_margin.add_theme_constant_override("margin_" + side, l.margin_h)
	for side: String in ["top", "bottom"]:
		_margin.add_theme_constant_override("margin_" + side, l.margin_v)
	_ink(_title, l.title_font, l.title_size, l.title_ink, l.line_spacing)
	_ink(_body, l.body_font, l.body_size, l.ink, l.line_spacing)
	_title.horizontal_alignment = l.title_align
	_body.horizontal_alignment = l.align
	_rule.visible = l.rule and _title.visible
	_rule.color = Color(l.ink, 0.55)
	_page.ruled = l.ruled
	_page.rule_color = Color(0.3, 0.42, 0.68, 0.28)
	_sheet.rotation_degrees = l.tilt_degrees
	_more.add_theme_color_override(&"font_color", UIStyle.TEXT_DIM)


static func _ink(label: Label, font: Font, size: int, color: Color, spacing: int) -> void:
	label.add_theme_font_override(&"font", font)
	label.add_theme_font_size_override(&"font_size", size)
	label.add_theme_color_override(&"font_color", color)
	label.add_theme_constant_override(&"outline_size", 0)
	label.add_theme_constant_override(&"shadow_outline_size", 0)
	label.add_theme_constant_override(&"shadow_offset_y", 0)
	label.add_theme_color_override(&"font_shadow_color", Color(0, 0, 0, 0))
	label.add_theme_constant_override(&"line_spacing", spacing)


func _layout_sheet() -> void:
	if _look == null:
		return
	var screen := get_viewport_rect().size
	var w := minf(_look.sheet_size.x, screen.x - screen_margin * 2.0)
	var h := minf(_look.sheet_size.y, screen.y - screen_margin * 2.0)
	# A label is as tall as its text needs (up to its card size); pages are fixed.
	if _style == ReadableInteractable.Style.LABEL:
		h = _look.sheet_size.y
	_sheet.offset_left = -w * 0.5
	_sheet.offset_right = w * 0.5
	_sheet.offset_top = -h * 0.5 - 10.0
	_sheet.offset_bottom = h * 0.5 - 10.0
	_sheet.pivot_offset = Vector2(w, h) * 0.5
	_page.queue_redraw()


func _input(event: InputEvent) -> void:
	if _open and event is InputEventMouseButton and (event as InputEventMouseButton).pressed:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_WHEEL_DOWN or mb.button_index == MOUSE_BUTTON_WHEEL_UP:
			var dir := 1.0 if mb.button_index == MOUSE_BUTTON_WHEEL_DOWN else -1.0
			_scroll_pos = _clamp_scroll(_scroll_pos + dir * 60.0 * maxf(mb.factor, 1.0))
			get_viewport().set_input_as_handled()
			return
	super._input(event)


func _click_closes() -> bool:
	var bar := _scroll.get_v_scroll_bar()
	return not (bar.visible and bar.get_global_rect().grow(12.0).has_point(get_global_mouse_position()))


func _process(delta: float) -> void:
	super._process(delta)
	if not _open:
		return
	var axis := Input.get_axis(&"move_forward", &"move_back") + Input.get_axis(&"look_up", &"look_down")
	if Input.is_action_pressed(&"ui_down"):
		axis += 1.0
	if Input.is_action_pressed(&"ui_up"):
		axis -= 1.0
	axis = clampf(axis, -1.0, 1.0)
	if absf(axis) > 0.05:
		_scroll_pos = _clamp_scroll(_scroll_pos + axis * scroll_speed * delta)
	# Follow a scrollbar drag, otherwise glide to the target.
	var bar := _scroll.get_v_scroll_bar()
	var cur := float(_scroll.scroll_vertical)
	if Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
		_scroll_pos = cur
	else:
		var nxt := lerpf(cur, _scroll_pos, clampf(delta * 14.0, 0.0, 1.0))
		if absf(nxt - _scroll_pos) < 2.5:
			nxt = _scroll_pos
		_scroll.scroll_vertical = roundi(nxt)
	var max_scroll := maxf(bar.max_value - _scroll.size.y, 0.0)
	_more.visible = max_scroll > 1.0 and float(_scroll.scroll_vertical) < max_scroll - 4.0


func _clamp_scroll(v: float) -> float:
	var bar := _scroll.get_v_scroll_bar()
	return clampf(v, 0.0, maxf(bar.max_value - _scroll.size.y, 0.0))
