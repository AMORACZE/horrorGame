class_name FlickerLight
extends Switchable
## Unsteady light spill (a TV screen, a dial lamp). Lights keep their scene
## energy as the average; `flicker` sets how far it wanders frame to frame.

@export var lights: Array[NodePath] = []
@export_range(0.0, 1.0, 0.01) var flicker: float = 0.35
## Changes per second.
@export_range(1.0, 60.0, 0.5) var rate: float = 24.0
@export var flicker_color_a: Color = Color(0.75, 0.82, 1.0)
@export var flicker_color_b: Color = Color(0.9, 0.92, 1.0)

var _lights: Array[Light3D] = []
var _energies: Array[float] = []
var _accum: float = 0.0


func _ready() -> void:
	for p in lights:
		var l := get_node_or_null(p) as Light3D
		if l:
			_lights.append(l)
			_energies.append(l.light_energy)
	super._ready()


func _switched(on_now: bool, _instant: bool) -> void:
	for l in _lights:
		l.visible = on_now
	set_process(on_now)


func _process(delta: float) -> void:
	_accum += delta
	if _accum < 1.0 / rate:
		return
	_accum = 0.0
	var k := randf()
	for i in _lights.size():
		_lights[i].light_energy = _energies[i] * (1.0 - flicker * k) * _energy_scale()
		_lights[i].light_color = flicker_color_a.lerp(flicker_color_b, randf())


## Override to fade the spill (a tube warming up). 1 = full.
func _energy_scale() -> float:
	return 1.0
