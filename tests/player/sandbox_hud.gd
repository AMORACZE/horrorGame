extends Label
## Sandbox-only readout: speed, surface, crouch, zoom, focus, last observation
## and last footstep. Stands in for the real HUD, which lives in ui/.

var _focus_text: String = "-"
var _observation: String = ""
var _step_text: String = "-"


func _ready() -> void:
	add_theme_font_size_override(&"font_size", 13)
	add_theme_color_override(&"font_shadow_color", Color(0, 0, 0, 0.8))
	Events.interaction_focus_changed.connect(_on_focus)
	Events.observation_requested.connect(func(t: String) -> void: _observation = t)
	Events.player_footstep.connect(_on_footstep)
	Events.player_landed.connect(func(s: StringName, _p: Vector3, i: float) -> void: _step_text = "landed %s %.2f" % [s, i])


func _process(_delta: float) -> void:
	var p := Game.player as Player
	if p == null:
		text = "no player"
		return
	text = "speed %.2f m/s  y %.2f  %s\ncrouch %.2f  zoom %.2f  fov %.1f\nfocus: %s\nstep: %s\n%s" % [
		p.get_ground_speed(), p.global_position.y, "grounded" if p.is_grounded() else "air",
		p.get_crouch_amount(), p.get_zoom_amount(), p.get_camera().fov,
		_focus_text, _step_text, _observation]


func _on_focus(it: Interactable) -> void:
	_focus_text = "-" if it == null else "%s %s" % [it.get_prompt(), it.get_display_name()]


func _on_footstep(surface: StringName, _pos: Vector3, intensity: float) -> void:
	_step_text = "%s %.2f" % [surface, intensity]
