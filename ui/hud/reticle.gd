class_name Reticle
extends Control
## The centre dot. Barely there while idle, firmer when something is focused.

@export var idle_radius: float = 1.4
@export var focus_radius: float = 2.3
@export var idle_alpha: float = 0.22
@export var focus_alpha: float = 0.9

## 0 = idle, 1 = focused. Tweened by the HUD.
var focus_amount: float = 0.0:
	set(v):
		focus_amount = v
		queue_redraw()


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _draw() -> void:
	var c := size * 0.5
	var r := lerpf(idle_radius, focus_radius, focus_amount)
	var a := lerpf(idle_alpha, focus_alpha, focus_amount)
	# Dark halo first so the dot survives a white wall or a blown-out window.
	draw_circle(c, r + 1.2, Color(UIStyle.OUTLINE, UIStyle.OUTLINE.a * a * 0.8), true, -1.0, true)
	draw_circle(c, r, Color(UIStyle.TEXT, a), true, -1.0, true)
