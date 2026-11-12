class_name CeilingFanFixture
extends LightFixture
## Root of ceiling_fan.tscn: the light kit's state (from LightFixture) plus
## the motor's. Wall switches can target "Motor" and/or "Power".

@export var fan_start_on: bool = false
@export var motor_path: NodePath = ^"Motor"


func _enter_tree() -> void:
	var first := not _pushed
	super._enter_tree()
	if first:
		var m := get_motor()
		if m:
			m.start_on = fan_start_on


func get_motor() -> FanMotor:
	return get_node_or_null(motor_path) as FanMotor
