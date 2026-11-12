class_name CrtScreen
extends FlickerLight
## A television tube: when switched on, the raster grows out of a bright
## horizontal line and settles into static; when switched off it collapses back
## to the line and goes dark. Light spill flickers (FlickerLight) while on.

## Mesh using crt_static.gdshader (driven through its `power` instance uniform).
@export var screen_mesh: NodePath
@export_range(0.05, 3.0, 0.01, "suffix:s") var warm_up_time: float = 0.55
@export_range(0.05, 2.0, 0.01, "suffix:s") var collapse_time: float = 0.18

var _screen: GeometryInstance3D = null
var _power: float = 0.0


func _ready() -> void:
	_screen = get_node_or_null(screen_mesh) as GeometryInstance3D
	super._ready()


## 0..1 how far the tube has come up.
func get_power() -> float:
	return _power


func _switched(on_now: bool, instant: bool) -> void:
	super._switched(on_now, instant)
	if instant:
		_power = 1.0 if on_now else 0.0
		_show()
	set_process(true)


func _process(delta: float) -> void:
	if _on:
		_power = minf(_power + delta / warm_up_time, 1.0)
		super._process(delta)
	else:
		_power = maxf(_power - delta / collapse_time, 0.0)
		if _power <= 0.0:
			set_process(false)
	_show()


func _energy_scale() -> float:
	return _power


func _show() -> void:
	if _screen:
		_screen.visible = _power > 0.0
		_screen.set_instance_shader_parameter(&"power", _power)
