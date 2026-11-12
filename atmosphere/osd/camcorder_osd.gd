@tool
class_name CamcorderOsd
extends Control
## Camcorder viewfinder display: date/time stamp (bottom-right), tape counter
## (top-right), battery (top-left) and a W–T zoom bar that appears while zooming.
## Sits on CanvasLayer 40 under the VHS pass so it is degraded with the picture.
## Shown/hidden by Settings video/osd_enabled.

@export_group("Clock")
## Camcorder clock at the moment the scene starts (24 h). Advances in real time.
@export_range(1980, 2010) var start_year: int = 1993
@export_range(1, 12) var start_month: int = 8
@export_range(1, 31) var start_day: int = 21
@export_range(0, 23) var start_hour: int = 15
@export_range(0, 59) var start_minute: int = 47
## Show time and date on two lines (time above date) instead of one.
@export var stamp_two_lines: bool = true

@export_group("Tape")
## Tape counter reading at start, in seconds.
@export var tape_counter_start: int = 754
## Battery charge at start, 0..1.
@export_range(0.0, 1.0) var battery_start: float = 0.82
## Minutes for a full battery to run flat.
@export var battery_minutes: float = 75.0

@export_group("Look")
@export var text_color: Color = Color(0.96, 0.96, 0.93)
@export var edge_color: Color = Color(0.03, 0.03, 0.035)
## Title-safe margin as a fraction of the screen.
@export var safe_margin: Vector2 = Vector2(0.075, 0.08)
## Seconds the zoom bar stays after the last zoom change.
@export var zoom_bar_hold: float = 1.4

const MONTHS: PackedStringArray = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
		"JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
const ZOOM_SEGMENTS := 12

var zoom_amount: float = 0.0
var zoom_bar_alpha: float = 0.0

var _start_unix: int = 0
var _start_ticks_ms: int = 0
var _time_line: String = ""
var _date_line: String = ""
var _counter_line: String = ""
var _battery_bars: int = 3
var _battery_blink: bool = true
var _zoom_hold_left: float = 0.0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_preset(Control.PRESET_FULL_RECT)
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	reset_clock()
	resized.connect(queue_redraw)
	if Engine.is_editor_hint():
		return
	_apply_enabled(bool(Settings.get_value(&"video", &"osd_enabled")))
	Events.setting_changed.connect(_on_setting_changed)
	Events.camera_zoom_changed.connect(show_zoom)


## Restart the clock and counter from the exported start values.
func reset_clock() -> void:
	_start_unix = Time.get_unix_time_from_datetime_dict({
		"year": start_year, "month": start_month, "day": start_day,
		"hour": start_hour, "minute": start_minute, "second": 0,
	})
	_start_ticks_ms = Time.get_ticks_msec()
	_update_text(true)


## Show the zoom bar at `amount` (0 wide .. 1 tele); it fades after a moment.
func show_zoom(amount: float) -> void:
	zoom_amount = clampf(amount, 0.0, 1.0)
	_zoom_hold_left = zoom_bar_hold
	zoom_bar_alpha = 1.0
	queue_redraw()


func get_time_text() -> String:
	return _time_line


func get_date_text() -> String:
	return _date_line


func get_stamp_text() -> String:
	return "%s  %s" % [_time_line, _date_line]


func get_counter_text() -> String:
	return _counter_line


func _process(delta: float) -> void:
	_update_text(false)
	if _zoom_hold_left > 0.0:
		_zoom_hold_left -= delta
	elif zoom_bar_alpha > 0.0:
		zoom_bar_alpha = maxf(0.0, zoom_bar_alpha - delta * 2.5)
		queue_redraw()


func _elapsed_seconds() -> float:
	return float(Time.get_ticks_msec() - _start_ticks_ms) / 1000.0


func _update_text(force: bool) -> void:
	var elapsed := _elapsed_seconds()
	var dt := Time.get_datetime_dict_from_unix_time(_start_unix + int(elapsed))
	var hour: int = dt["hour"]
	var ampm := "AM" if hour < 12 else "PM"
	var h12 := hour % 12
	if h12 == 0:
		h12 = 12
	var time_line := "%s %d:%02d" % [ampm, h12, int(dt["minute"])]
	var date_line := "%s %d %d" % [MONTHS[int(dt["month"]) - 1], int(dt["day"]), int(dt["year"])]

	var c := tape_counter_start + int(elapsed)
	var counter_line := "%d:%02d:%02d" % [floori(c / 3600.0), floori(c / 60.0) % 60, c % 60]

	var charge := battery_start - elapsed / maxf(battery_minutes * 60.0, 1.0)
	var bars := clampi(ceili(charge * 3.0), 0, 3)
	var blink := bars > 0 or fmod(elapsed, 1.0) < 0.5

	if force or time_line != _time_line or date_line != _date_line \
			or counter_line != _counter_line or bars != _battery_bars or blink != _battery_blink:
		_time_line = time_line
		_date_line = date_line
		_counter_line = counter_line
		_battery_bars = bars
		_battery_blink = blink
		queue_redraw()


func _cell() -> float:
	# Whole pixels per font cell, so the glyphs stay crisp before the VHS pass.
	return maxf(1.0, roundf(size.y / 220.0))


func _draw() -> void:
	var s := _cell()
	var edge := maxf(1.0, roundf(s * 0.4))
	var m := (size * safe_margin).round()
	var line_h := (OsdFont.H + 3) * s

	# Date/time stamp, bottom-right.
	var bottom := size.y - m.y - OsdFont.H * s
	if stamp_two_lines:
		_draw_right(_date_line, Vector2(size.x - m.x, bottom), s, edge)
		_draw_right(_time_line, Vector2(size.x - m.x, bottom - line_h), s, edge)
	else:
		_draw_right(get_stamp_text(), Vector2(size.x - m.x, bottom), s, edge)

	# Tape counter, top-right.
	_draw_right(_counter_line, Vector2(size.x - m.x, m.y), s, edge)

	# Battery, top-left.
	if _battery_blink:
		var b := Vector2(m.x, m.y)
		OsdFont.draw_cells(self, b, OsdFont.BATTERY, s, text_color, edge_color, edge)
		for i: int in _battery_bars:
			draw_rect(Rect2(b.x + (2 + i * 2.5) * s, b.y + 2 * s, 2 * s, 3 * s), text_color)

	# Zoom bar, top centre: W [segments] T
	if zoom_bar_alpha > 0.0:
		var a := zoom_bar_alpha
		var tc := Color(text_color, text_color.a * a)
		var ec := Color(edge_color, edge_color.a * a)
		var seg_w := 2.0 * s
		var gap := 1.0 * s
		var bar_w := ZOOM_SEGMENTS * (seg_w + gap) - gap
		var total := OsdFont.ADVANCE * s * 2.0 + bar_w + 2.0 * s
		var x := roundf((size.x - total) * 0.5)
		var y := m.y
		OsdFont.draw_text(self, Vector2(x, y), "W", s, tc, ec, edge)
		x += OsdFont.ADVANCE * s + s
		var lit := int(roundf(zoom_amount * ZOOM_SEGMENTS))
		for i: int in ZOOM_SEGMENTS:
			var r := Rect2(x + i * (seg_w + gap), y + 1.0 * s, seg_w, 5.0 * s)
			draw_rect(r.grow(edge), ec)
			if i < lit:
				draw_rect(r, tc)
			else:
				draw_rect(r.grow(-maxf(1.0, s * 0.5)), Color(tc, tc.a * 0.25))
		x += bar_w + s * 2.0
		OsdFont.draw_text(self, Vector2(x, y), "T", s, tc, ec, edge)


func _draw_right(text: String, right_top: Vector2, s: float, edge: float) -> void:
	var w := OsdFont.text_width(text) * s
	OsdFont.draw_text(self, Vector2(right_top.x - w, right_top.y), text, s, text_color, edge_color, edge)


func _apply_enabled(on: bool) -> void:
	visible = on


func _on_setting_changed(section: StringName, key: StringName, value: Variant) -> void:
	if section == &"video" and key == &"osd_enabled":
		_apply_enabled(bool(value))
