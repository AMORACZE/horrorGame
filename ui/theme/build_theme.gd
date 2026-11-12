extends SceneTree
## Generates res://ui/theme.tres from code, so the theme is reviewable as text
## and can be rebuilt after a font or colour change:
##
##   godot --headless --path . -s res://ui/theme/build_theme.gd
##
## Fonts come from UIFonts, colours from UIStyle. Do not hand-edit theme.tres.

const OUT := "res://ui/theme.tres"


func _initialize() -> void:
	var t := build()
	var err := ResourceSaver.save(t, OUT)
	print("build_theme: %s -> %s" % [error_string(err), OUT])
	quit(0 if err == OK else 1)


static func build() -> Theme:
	var t := Theme.new()
	t.default_font = UIFonts.SANS
	t.default_font_size = UIStyle.FONT_SIZE_HUD

	var empty := StyleBoxEmpty.new()

	# --- Label: warm white with a soft dark edge --------------------------------
	t.set_color(&"font_color", &"Label", UIStyle.TEXT)
	t.set_color(&"font_outline_color", &"Label", UIStyle.OUTLINE)
	t.set_color(&"font_shadow_color", &"Label", UIStyle.SHADOW)
	t.set_constant(&"outline_size", &"Label", 2)
	t.set_constant(&"shadow_offset_x", &"Label", 0)
	t.set_constant(&"shadow_offset_y", &"Label", 1)
	t.set_constant(&"shadow_outline_size", &"Label", 4)
	t.set_constant(&"line_spacing", &"Label", 2)

	_label_variation(t, &"HudPrompt", UIStyle.FONT_SIZE_HUD, UIStyle.TEXT)
	_label_variation(t, &"HudSeparator", UIStyle.FONT_SIZE_HUD, UIStyle.TEXT_DIM)
	_label_variation(t, &"Observation", UIStyle.FONT_SIZE_OBSERVATION, UIStyle.TEXT)
	_label_variation(t, &"Caption", 24, UIStyle.TEXT)
	_label_variation(t, &"CaptionBody", 17, Color(UIStyle.TEXT, 0.82))
	_label_variation(t, &"Hint", UIStyle.FONT_SIZE_SMALL, UIStyle.TEXT_DIM)
	_label_variation(t, &"SettingLabel", 18, UIStyle.TEXT_DIM)
	_label_variation(t, &"SettingValue", 16, UIStyle.TEXT_DIM)
	_label_variation(t, &"SectionLabel", 13, UIStyle.TEXT_FAINT)

	var spaced := FontVariation.new()
	spaced.base_font = UIFonts.SANS
	spaced.spacing_glyph = 4
	_label_variation(t, &"MenuTitle", 14, UIStyle.TEXT_DIM)
	t.set_font(&"font", &"MenuTitle", spaced)
	t.set_font(&"font", &"SectionLabel", spaced)
	# Titles line up with button text (buttons leave 16 px for the focus bar).
	var indent := StyleBoxEmpty.new()
	indent.content_margin_left = 16
	t.set_stylebox(&"normal", &"MenuTitle", indent)

	# Key / button glyphs ("E", "LMB", "A").
	_label_variation(t, &"GlyphText", 12, UIStyle.TEXT)
	t.set_font(&"font", &"GlyphText", UIFonts.SANS_BOLD)
	t.set_constant(&"outline_size", &"GlyphText", 0)
	t.set_constant(&"shadow_outline_size", &"GlyphText", 0)
	t.set_constant(&"shadow_offset_y", &"GlyphText", 0)

	var key := StyleBoxFlat.new()
	key.bg_color = Color(0.05, 0.045, 0.04, 0.5)
	key.border_color = Color(UIStyle.TEXT, 0.85)
	key.set_border_width_all(1)
	key.content_margin_left = 5
	key.content_margin_right = 5
	key.content_margin_top = 0
	key.content_margin_bottom = 0
	key.shadow_color = Color(0, 0, 0, 0.25)
	key.shadow_size = 2
	t.set_type_variation(&"KeyCap", &"PanelContainer")
	t.set_stylebox(&"panel", &"KeyCap", key)
	var pad := key.duplicate() as StyleBoxFlat
	pad.set_corner_radius_all(9)
	pad.corner_detail = 6
	pad.content_margin_left = 5
	pad.content_margin_right = 5
	t.set_type_variation(&"PadCap", &"PanelContainer")
	t.set_stylebox(&"panel", &"PadCap", pad)

	# --- Containers: no chrome ----------------------------------------------------
	t.set_stylebox(&"panel", &"PanelContainer", empty)
	t.set_stylebox(&"panel", &"Panel", empty)
	t.set_stylebox(&"panel", &"ScrollContainer", empty)
	t.set_stylebox(&"focus", &"ScrollContainer", empty)

	var bar := StyleBoxFlat.new()
	bar.bg_color = Color(UIStyle.TEXT, 0.10)
	bar.content_margin_left = 1
	bar.content_margin_right = 1
	var grab := StyleBoxFlat.new()
	grab.bg_color = Color(UIStyle.TEXT, 0.45)
	grab.content_margin_left = 1
	grab.content_margin_right = 1
	var grab_hi := grab.duplicate() as StyleBoxFlat
	grab_hi.bg_color = Color(UIStyle.TEXT, 0.75)
	t.set_stylebox(&"scroll", &"VScrollBar", bar)
	t.set_stylebox(&"scroll_focus", &"VScrollBar", bar)
	t.set_stylebox(&"grabber", &"VScrollBar", grab)
	t.set_stylebox(&"grabber_highlight", &"VScrollBar", grab_hi)
	t.set_stylebox(&"grabber_pressed", &"VScrollBar", grab_hi)

	# --- Button: text only; focus is a thin bar at the left edge -------------------
	var btn := StyleBoxEmpty.new()
	btn.content_margin_left = 16
	btn.content_margin_right = 8
	btn.content_margin_top = 3
	btn.content_margin_bottom = 3
	var focus := StyleBoxFlat.new()
	focus.draw_center = false
	focus.border_width_left = 2
	focus.border_color = Color(UIStyle.TEXT, 0.9)
	focus.content_margin_left = 16
	for s: StringName in [&"normal", &"hover", &"pressed", &"disabled", &"hover_pressed",
			&"normal_mirrored", &"hover_mirrored", &"pressed_mirrored", &"disabled_mirrored",
			&"hover_pressed_mirrored"]:
		t.set_stylebox(s, &"Button", btn)
	t.set_stylebox(&"focus", &"Button", focus)
	t.set_font_size(&"font_size", &"Button", UIStyle.FONT_SIZE_MENU)
	t.set_color(&"font_color", &"Button", Color(UIStyle.TEXT, 0.58))
	t.set_color(&"font_hover_color", &"Button", UIStyle.TEXT)
	t.set_color(&"font_focus_color", &"Button", UIStyle.TEXT)
	t.set_color(&"font_pressed_color", &"Button", UIStyle.TEXT)
	t.set_color(&"font_hover_pressed_color", &"Button", UIStyle.TEXT)
	t.set_color(&"font_disabled_color", &"Button", UIStyle.TEXT_FAINT)
	t.set_color(&"font_outline_color", &"Button", UIStyle.OUTLINE)
	t.set_constant(&"outline_size", &"Button", 0)

	# Small toggle used inside settings rows ("On" / "Off"); the row marks focus.
	var plain := StyleBoxEmpty.new()
	plain.content_margin_left = 0
	plain.content_margin_right = 0
	plain.content_margin_top = 2
	plain.content_margin_bottom = 2
	t.set_type_variation(&"SettingToggle", &"Button")
	for s: StringName in [&"normal", &"hover", &"pressed", &"disabled", &"hover_pressed",
			&"focus", &"normal_mirrored", &"hover_mirrored", &"pressed_mirrored",
			&"disabled_mirrored", &"hover_pressed_mirrored"]:
		t.set_stylebox(s, &"SettingToggle", plain)
	t.set_font_size(&"font_size", &"SettingToggle", 18)

	# --- HSlider: a hairline with a short vertical tick -----------------------------
	var track := StyleBoxFlat.new()
	track.bg_color = Color(UIStyle.TEXT, 0.22)
	track.content_margin_top = 1
	track.content_margin_bottom = 1
	var fill := StyleBoxFlat.new()
	fill.bg_color = Color(UIStyle.TEXT, 0.70)
	fill.content_margin_top = 1
	fill.content_margin_bottom = 1
	var fill_hi := fill.duplicate() as StyleBoxFlat
	fill_hi.bg_color = Color(UIStyle.TEXT, 0.95)
	t.set_stylebox(&"slider", &"HSlider", track)
	t.set_stylebox(&"grabber_area", &"HSlider", fill)
	t.set_stylebox(&"grabber_area_highlight", &"HSlider", fill_hi)
	t.set_stylebox(&"focus", &"HSlider", empty)
	t.set_icon(&"grabber", &"HSlider", _tick_texture(Color(UIStyle.TEXT, 0.85)))
	t.set_icon(&"grabber_highlight", &"HSlider", _tick_texture(UIStyle.TEXT))
	t.set_icon(&"grabber_disabled", &"HSlider", _tick_texture(UIStyle.TEXT_FAINT))
	t.set_constant(&"center_grabber", &"HSlider", 1)
	return t


static func _label_variation(t: Theme, name: StringName, size: int, color: Color) -> void:
	t.set_type_variation(name, &"Label")
	t.set_font_size(&"font_size", name, size)
	t.set_color(&"font_color", name, color)


## A 3x16 solid bar, stored as a GradientTexture2D so the theme stays one text file.
static func _tick_texture(color: Color) -> Texture2D:
	var g := Gradient.new()
	g.set_color(0, color)
	g.set_color(1, color)
	var tex := GradientTexture2D.new()
	tex.gradient = g
	tex.width = 3
	tex.height = 16
	return tex
