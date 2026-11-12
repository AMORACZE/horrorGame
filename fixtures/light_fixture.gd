class_name LightFixture
extends Node3D
## Root of a light scene (lamps, ceiling light, fan light kit). Exposes the
## bulb's level-facing state on the instance root; pushed to the PoweredLight
## in _enter_tree, before it reads them in _ready.

@export var start_on: bool = false
@export var dead_bulb: bool = false
@export_range(0.0, 8.0, 0.01) var brightness: float = 1.0
@export var power_path: NodePath = ^"Power"

var _pushed: bool = false


func _enter_tree() -> void:
	if _pushed:
		return
	_pushed = true
	var p := get_power()
	if p:
		p.start_on = start_on
		p.dead_bulb = dead_bulb
		p.brightness = brightness


func get_power() -> PoweredLight:
	return get_node_or_null(power_path) as PoweredLight
