extends Node
## User settings (autoload: `Settings`). Persisted to user://settings.cfg.
##
## Read with `Settings.get_value(&"video", &"fov")`, write with `set_value`.
## Every write emits `Events.setting_changed`, so systems apply changes live.
## Add a new setting by adding it to DEFAULTS; nothing else is required.

const PATH := "user://settings.cfg"

const DEFAULTS := {
	&"controls": {
		&"mouse_sensitivity": 1.0,   # multiplier, 1.0 = default feel
		&"gamepad_sensitivity": 1.0, # multiplier
		&"invert_y": false,
		&"toggle_crouch": true,
	},
	&"video": {
		&"fov": 68.0,                # degrees, vertical
		&"fullscreen": false,
		&"vsync": true,
		&"render_scale": 1.0,        # 3D resolution scale 0.5..1.0
		&"vhs_enabled": true,        # camcorder post-process
		&"vhs_intensity": 1.0,       # 0..1.5
		&"osd_enabled": true,        # camcorder on-screen display (date stamp etc.)
	},
	&"comfort": {
		&"head_bob": 1.0,            # 0..1 multiplier
		&"camera_sway": 1.0,         # handheld sway 0..1 multiplier
	},
	&"audio": {
		&"master": 1.0,              # linear 0..1 per bus
		&"world": 1.0,
		&"ambience": 1.0,
		&"ui": 1.0,
	},
}

var _values: Dictionary = {}


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_values = DEFAULTS.duplicate(true)
	_load()


func get_value(section: StringName, key: StringName) -> Variant:
	var s: Dictionary = _values.get(section, {})
	if s.has(key):
		return s[key]
	push_warning("Settings: unknown setting %s/%s" % [section, key])
	return null


func set_value(section: StringName, key: StringName, value: Variant, persist: bool = true) -> void:
	if not _values.has(section):
		_values[section] = {}
	if _values[section].get(key) == value:
		return
	_values[section][key] = value
	Events.setting_changed.emit(section, key, value)
	if persist:
		save()


func reset_to_defaults() -> void:
	for section: StringName in DEFAULTS:
		for key: StringName in DEFAULTS[section]:
			set_value(section, key, DEFAULTS[section][key], false)
	save()


func save() -> void:
	var cfg := ConfigFile.new()
	for section: StringName in _values:
		for key: StringName in _values[section]:
			cfg.set_value(section, key, _values[section][key])
	var err := cfg.save(PATH)
	if err != OK:
		push_warning("Settings: could not save (%s)" % error_string(err))


func _load() -> void:
	var cfg := ConfigFile.new()
	if cfg.load(PATH) != OK:
		return
	for section: StringName in DEFAULTS:
		for key: StringName in DEFAULTS[section]:
			if cfg.has_section_key(section, key):
				var v: Variant = cfg.get_value(section, key)
				# Ignore values whose type no longer matches the default.
				if typeof(v) == typeof(DEFAULTS[section][key]):
					_values[section][key] = v
