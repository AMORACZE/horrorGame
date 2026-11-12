class_name RuledPage
extends VBoxContainer
## Scroll content of the reader. Optionally draws faint ruled lines that sit
## under the body text's baselines (legal pad / notebook paper).

@export var body_path: NodePath
var ruled: bool = false:
	set(v):
		ruled = v
		queue_redraw()
var rule_color := Color(0.35, 0.45, 0.7, 0.25)


func _ready() -> void:
	resized.connect(queue_redraw)


func _draw() -> void:
	if not ruled:
		return
	var body := get_node_or_null(body_path) as Label
	if body == null or body.text == "":
		return
	var font := body.get_theme_font(&"font")
	var fsize := body.get_theme_font_size(&"font_size")
	var lh := font.get_height(fsize) + float(body.get_theme_constant(&"line_spacing"))
	var y := body.position.y + font.get_ascent(fsize) + 4.0
	# Run on past the text; the scroll container clips at the sheet edge.
	var bottom := maxf(size.y, body.position.y + body.size.y) + 1200.0
	while y < bottom:
		draw_line(Vector2(-8.0, y), Vector2(size.x + 8.0, y), rule_color, 1.0, true)
		y += lh
