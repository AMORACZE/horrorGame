class_name DisplaySettings
extends Node
## Applies video/fullscreen and video/vsync (the two settings the UI owns).
## Reads the stored values on _ready and follows Events.setting_changed.


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	Events.setting_changed.connect(_on_setting_changed)
	_apply_fullscreen(bool(Settings.get_value(&"video", &"fullscreen")))
	_apply_vsync(bool(Settings.get_value(&"video", &"vsync")))


func _on_setting_changed(section: StringName, key: StringName, value: Variant) -> void:
	if section != &"video":
		return
	match key:
		&"fullscreen": _apply_fullscreen(bool(value))
		&"vsync": _apply_vsync(bool(value))


static func _has_window() -> bool:
	return DisplayServer.get_name() != "headless"


static func _apply_fullscreen(on: bool) -> void:
	if not _has_window():
		return
	var mode := DisplayServer.window_get_mode()
	var is_full := mode == DisplayServer.WINDOW_MODE_FULLSCREEN or mode == DisplayServer.WINDOW_MODE_EXCLUSIVE_FULLSCREEN
	if on and not is_full:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)
	elif not on and is_full:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)


static func _apply_vsync(on: bool) -> void:
	if not _has_window():
		return
	var want := DisplayServer.VSYNC_ENABLED if on else DisplayServer.VSYNC_DISABLED
	if DisplayServer.window_get_vsync_mode() != want:
		DisplayServer.window_set_vsync_mode(want)
