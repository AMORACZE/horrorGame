class_name SettingsSchema
extends RefCounted
## Presentation for each key in Settings.DEFAULTS: label, range, step, readout.
## Keys missing here still appear in the menu with a generic control, so a new
## setting added to core/settings.gd is never hidden.

const SECTION_LABELS := {
	&"controls": "Controls",
	&"video": "Video",
	&"comfort": "Comfort",
	&"audio": "Sound",
}

## fmt: "mult" 1.00×, "deg" 68°, "pct" 100% (value*100), "num" 0.00
const KEYS := {
	&"controls": {
		&"mouse_sensitivity": {"label": "Mouse sensitivity", "min": 0.1, "max": 3.0, "step": 0.05, "fmt": "mult"},
		&"gamepad_sensitivity": {"label": "Gamepad sensitivity", "min": 0.1, "max": 3.0, "step": 0.05, "fmt": "mult"},
		&"invert_y": {"label": "Invert look"},
		&"toggle_crouch": {"label": "Toggle crouch"},
	},
	&"video": {
		&"fov": {"label": "Field of view", "min": 50.0, "max": 90.0, "step": 1.0, "fmt": "deg"},
		&"fullscreen": {"label": "Fullscreen"},
		&"vsync": {"label": "Vertical sync"},
		&"render_scale": {"label": "Resolution scale", "min": 0.5, "max": 1.0, "step": 0.05, "fmt": "pct"},
		&"vhs_enabled": {"label": "Tape effect"},
		&"vhs_intensity": {"label": "Tape effect strength", "min": 0.0, "max": 1.5, "step": 0.05, "fmt": "pct"},
		&"osd_enabled": {"label": "Camera display"},
	},
	&"comfort": {
		&"head_bob": {"label": "Head bob", "min": 0.0, "max": 1.0, "step": 0.05, "fmt": "pct"},
		&"camera_sway": {"label": "Hand sway", "min": 0.0, "max": 1.0, "step": 0.05, "fmt": "pct"},
	},
	&"audio": {
		&"master": {"label": "Master volume", "min": 0.0, "max": 1.0, "step": 0.01, "fmt": "pct"},
		&"world": {"label": "Effects", "min": 0.0, "max": 1.0, "step": 0.01, "fmt": "pct"},
		&"ambience": {"label": "Ambience", "min": 0.0, "max": 1.0, "step": 0.01, "fmt": "pct"},
		&"ui": {"label": "Interface", "min": 0.0, "max": 1.0, "step": 0.01, "fmt": "pct"},
	},
}


static func section_label(section: StringName) -> String:
	return SECTION_LABELS.get(section, String(section).capitalize())


## Merged description for one key, with fallbacks derived from the default value.
static func describe(section: StringName, key: StringName, default_value: Variant) -> Dictionary:
	var d: Dictionary = {}
	var s: Dictionary = KEYS.get(section, {})
	if s.has(key):
		d = (s[key] as Dictionary).duplicate()
	if not d.has("label"):
		d["label"] = String(key).capitalize()
	if default_value is float or default_value is int:
		var dv := float(default_value)
		if not d.has("min"):
			d["min"] = 0.0
		if not d.has("max"):
			d["max"] = maxf(1.0, dv * 2.0)
		if not d.has("step"):
			d["step"] = 1.0 if default_value is int else 0.05
		if not d.has("fmt"):
			d["fmt"] = "num"
	return d


static func format_value(value: float, fmt: String) -> String:
	match fmt:
		"mult": return "%.2f×" % value
		"deg": return "%d°" % roundi(value)
		"pct": return "%d%%" % roundi(value * 100.0)
	return "%.2f" % value
