extends Control
## VHS test card: colour bars, grey steps, a dark ramp, fine lines and text,
## under the real post_fx.tscn. Use it to judge chroma bleed, ringing, noise
## and the OSD without waiting for 3D lighting.
##   --zoom=1.0 emits a zoom change (autofocus hunt + zoom bar)
##   --intensity=1.5  --vhs=0

const BARS: Array[Color] = [
	Color(0.75, 0.75, 0.75), Color(0.75, 0.75, 0.0), Color(0.0, 0.75, 0.75), Color(0.0, 0.75, 0.0),
	Color(0.75, 0.0, 0.75), Color(0.75, 0.0, 0.0), Color(0.0, 0.0, 0.75),
]


func _ready() -> void:
	for a: String in OS.get_cmdline_user_args():
		if not a.contains("="):
			continue
		var kv := a.substr(2).split("=", true, 1)
		match kv[0]:
			"zoom":
				Events.camera_zoom_changed.emit(float(kv[1]))
			"intensity":
				Settings.set_value(&"video", &"vhs_intensity", float(kv[1]), false)
			"vhs":
				Settings.set_value(&"video", &"vhs_enabled", kv[1] != "0", false)
	resized.connect(queue_redraw)


func _draw() -> void:
	var w := size.x
	var h := size.y
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.02, 0.02, 0.02))
	# Colour bars, top half.
	var bw := w / BARS.size()
	for i: int in BARS.size():
		draw_rect(Rect2(i * bw, 0.0, bw + 1.0, h * 0.45), BARS[i])
	# Grey steps.
	for i: int in 10:
		var v := float(i) / 9.0
		draw_rect(Rect2(i * w / 10.0, h * 0.45, w / 10.0 + 1.0, h * 0.12), Color(v, v, v))
	# Dark ramp (where tape noise lives).
	for i: int in 64:
		var v := float(i) / 63.0 * 0.25
		draw_rect(Rect2(i * w / 64.0, h * 0.57, w / 64.0 + 1.0, h * 0.13), Color(v, v * 0.95, v * 0.9))
	# Fine vertical lines and a red/cyan edge.
	for i: int in 40:
		draw_rect(Rect2(w * 0.05 + i * 6.0, h * 0.72, 2.0, h * 0.12), Color(0.9, 0.9, 0.9))
	draw_rect(Rect2(w * 0.5, h * 0.72, w * 0.12, h * 0.12), Color(0.8, 0.1, 0.08))
	draw_rect(Rect2(w * 0.62, h * 0.72, w * 0.12, h * 0.12), Color(0.1, 0.7, 0.75))
	draw_string(ThemeDB.fallback_font, Vector2(w * 0.05, h * 0.93), "THE QUICK BROWN FOX 0123456789",
			HORIZONTAL_ALIGNMENT_LEFT, -1, int(h * 0.05), Color(0.95, 0.95, 0.95))
