class_name LightSwitchFixture
extends Node3D
## Root of light_switch.tscn. `targets` are paths FROM THIS ROOT to the
## lights / fans it controls (a PoweredLight, a FanMotor, or a fixture root
## whose direct child is one, e.g. "../CeilingLight/Power" or "../CeilingLight").
##
## Convention: origin at the wall surface, centred on the switch; the plate
## extends toward local +Z. Mount the origin at 1.2 m.

@export var targets: Array[NodePath] = []
@export var start_on: bool = false
@export var display_name: String = "Light switch"
@export var switch_path: NodePath = ^"Body/Switch"

var _pushed: bool = false


func _enter_tree() -> void:
	if _pushed:
		return
	_pushed = true
	var sw := get_switch()
	if sw == null:
		return
	sw.start_on = start_on
	sw.display_name = display_name
	if targets.is_empty():
		return
	var prefix := ""
	for _i in NodePath(switch_path).get_name_count():
		prefix += "../"
	var out: Array[NodePath] = []
	for p in targets:
		var resolved := _resolve_target(p)
		out.append(p if p.is_absolute() else NodePath(prefix + resolved))
	sw.targets = out


## Accept a fixture root as a target: point at its Switchable child instead.
func _resolve_target(p: NodePath) -> String:
	var n := get_node_or_null(p)
	if n == null or n is Switchable:
		return String(p)
	for c in n.get_children():
		if c is Switchable:
			return String(p) + "/" + String(c.name)
	return String(p)


func get_switch() -> SwitchInteractable:
	return get_node_or_null(switch_path) as SwitchInteractable
