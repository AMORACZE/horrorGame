class_name PauseMenu
extends CanvasLayer
## Pause menu on CanvasLayer 100 (above the camcorder post-process, drawn clean).
##
## UIRoot opens it on the "pause" action when no modal is open and routes
## ui_back / pause to `handle_back()` while it is open. Opening pauses the tree,
## takes an input lock and emits Events.pause_changed. Pages: main (Resume,
## Settings, Quit to desktop) and Settings, which lists every key in
## Settings.DEFAULTS and writes through Settings.set_value.

signal opened
signal closed

enum Page { MAIN, SETTINGS }

@onready var _root: Control = %Root
@onready var _main: Control = %MainPage
@onready var _settings: Control = %SettingsPage
@onready var _resume: Button = %Resume
@onready var _settings_button: Button = %SettingsButton
@onready var _quit: Button = %Quit
@onready var _rows_box: VBoxContainer = %Rows
@onready var _scroll: ScrollContainer = %SettingsScroll
@onready var _reset: Button = %Reset
@onready var _back: Button = %Back
@onready var _back_hint: Label = %BackHint

var _open: bool = false
var _page: Page = Page.MAIN
var _rows: Array[SettingRow] = []
## Suppresses the focus tick while focus is moved by code.
var _quiet: bool = false
var _fade: Tween


func _ready() -> void:
	layer = 100
	process_mode = Node.PROCESS_MODE_ALWAYS
	_root.visible = false
	_build_settings_rows()
	_resume.pressed.connect(close)
	_settings_button.pressed.connect(show_page.bind(Page.SETTINGS))
	_quit.pressed.connect(_quit_to_desktop)
	_reset.pressed.connect(_reset_defaults)
	_back.pressed.connect(show_page.bind(Page.MAIN))
	_chain([_resume, _settings_button, _quit])
	for b: Button in [_resume, _settings_button, _quit, _reset, _back]:
		_wire_button(b)


func is_open() -> bool:
	return _open


func get_page() -> Page:
	return _page


func get_rows() -> Array[SettingRow]:
	return _rows


func find_row(section: StringName, key: StringName) -> SettingRow:
	for r in _rows:
		if r.section == section and r.key == key:
			return r
	return null


func open() -> void:
	if _open:
		return
	_open = true
	get_tree().paused = true
	Game.lock_input(self)
	_root.visible = true
	if _fade:
		_fade.kill()
	_root.modulate.a = 0.0
	_fade = create_tween()
	_fade.tween_property(_root, ^"modulate:a", 1.0, 0.12)
	show_page(Page.MAIN, false)
	UIInput.sound(&"ui_open")
	Events.pause_changed.emit(true)
	opened.emit()


func close() -> void:
	if not _open:
		return
	_open = false
	if _fade:
		_fade.kill()
	_root.visible = false
	var focus_owner := _root.get_viewport().gui_get_focus_owner()
	if focus_owner:
		focus_owner.release_focus()
	get_tree().paused = false
	UIInput.sound(&"ui_close")
	Events.pause_changed.emit(false)
	closed.emit()
	UIInput.unlock_when_released(self)


## Escape / B / Start while open: back out of Settings, else resume.
func handle_back() -> void:
	if _page == Page.SETTINGS:
		show_page(Page.MAIN)
	else:
		close()


func show_page(page: Page, sound: bool = true) -> void:
	_page = page
	_main.visible = page == Page.MAIN
	_settings.visible = page == Page.SETTINGS
	_quiet = true
	if page == Page.MAIN:
		_back_hint.text = "Resume"
		_resume.grab_focus()
	else:
		_back_hint.text = "Back"
		for r in _rows:
			r.refresh()
		_scroll.scroll_vertical = 0
		if not _rows.is_empty():
			_rows[0].get_focus_control().grab_focus()
	_quiet = false
	if sound:
		UIInput.sound(&"ui_tick")


func _build_settings_rows() -> void:
	for c in _rows_box.get_children():
		c.queue_free()
	_rows.clear()
	var focusables: Array[Control] = []
	for section: StringName in Settings.DEFAULTS:
		var heading := Label.new()
		heading.theme_type_variation = &"SectionLabel"
		heading.text = SettingsSchema.section_label(section).to_upper()
		heading.custom_minimum_size.y = 40.0
		heading.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
		var hpad := MarginContainer.new()
		hpad.add_theme_constant_override(&"margin_left", 16)
		hpad.add_child(heading)
		_rows_box.add_child(hpad)
		var keys: Dictionary = Settings.DEFAULTS[section]
		for key: StringName in keys:
			var row := SettingRow.new()
			row.setup(section, key, keys[key])
			_rows_box.add_child(row)
			_rows.append(row)
			row.focus_gained.connect(_on_row_focus)
			focusables.append(row.get_focus_control())
	focusables.append(_reset)
	focusables.append(_back)
	_chain(focusables)
	# Footer buttons sit side by side: left/right moves between them.
	_reset.focus_neighbor_right = _reset.get_path_to(_back)
	_back.focus_neighbor_left = _back.get_path_to(_reset)
	var last_row: Control = focusables[focusables.size() - 3]
	_back.focus_neighbor_top = _back.get_path_to(last_row)
	_reset.focus_neighbor_bottom = _reset.get_path_to(focusables[0])


## Vertical focus order with wrap-around; left/right stay put.
func _chain(items: Array) -> void:
	var n := items.size()
	for i in n:
		var c: Control = items[i]
		var up: Control = items[(i - 1 + n) % n]
		var down: Control = items[(i + 1) % n]
		c.focus_neighbor_top = c.get_path_to(up)
		c.focus_neighbor_bottom = c.get_path_to(down)
		c.focus_neighbor_left = c.get_path_to(c)
		c.focus_neighbor_right = c.get_path_to(c)
		c.focus_previous = c.get_path_to(up)
		c.focus_next = c.get_path_to(down)


func _wire_button(b: Button) -> void:
	b.mouse_entered.connect(func() -> void: b.grab_focus())
	b.focus_entered.connect(_on_focus_moved)


func _on_row_focus(row: SettingRow) -> void:
	_on_focus_moved()
	_scroll.ensure_control_visible(row)


func _on_focus_moved() -> void:
	if not _quiet:
		UIInput.sound(&"ui_tick")


func _reset_defaults() -> void:
	Settings.reset_to_defaults()
	for r in _rows:
		r.refresh()
	UIInput.sound(&"ui_tick")


func _quit_to_desktop() -> void:
	_root.visible = false
	UIInput.sound(&"ui_close")
	if ScreenFade.current:
		await ScreenFade.current.fade_out(0.5)
	get_tree().quit()
