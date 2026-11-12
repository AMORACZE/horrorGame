class_name FanMotor
extends Switchable
## Spins a rotor (ceiling fan blades) up and down slowly, like a real motor:
## a few seconds to come up to speed, much longer to coast down.

@export_group("Rotor")
@export var rotor: NodePath
## Rotation axis in the rotor's parent space.
@export var axis: Vector3 = Vector3.UP
@export_range(0.0, 400.0, 1.0, "suffix:rpm") var max_rpm: float = 95.0
@export_range(0.1, 20.0, 0.1, "suffix:s") var spin_up_time: float = 5.0
@export_range(0.1, 40.0, 0.1, "suffix:s") var spin_down_time: float = 14.0
## -1 or 1: summer (counter-clockwise from below) or winter direction.
@export var direction: float = 1.0

@export_group("Sound")
@export var hum_sound: StringName = &""
@export var hum_volume_db: float = -20.0

var _rpm: float = 0.0
var _rotor: Node3D = null
var _hum: AudioStreamPlayer3D = null


func _ready() -> void:
	_rotor = get_node_or_null(rotor) as Node3D
	if hum_sound != &"" and get_parent() is Node3D:
		_hum = LoopEmitter.create_player(get_parent(), hum_sound, hum_volume_db)
	super._ready()


func get_rpm() -> float:
	return _rpm


func _switched(on_now: bool, instant: bool) -> void:
	if instant:
		_rpm = max_rpm if on_now else 0.0
	set_process(on_now or _rpm > 0.0)
	if _hum:
		LoopEmitter.set_playing(_hum, on_now)


func _process(delta: float) -> void:
	if _on:
		# Torque falls off as it nears speed.
		var gain := max_rpm * 3.0 / spin_up_time
		_rpm = move_toward(_rpm, max_rpm, maxf(gain * (1.0 - _rpm / maxf(max_rpm, 0.01)), max_rpm * 0.05) * delta)
	else:
		# Drag: proportional to speed, plus a little bearing friction.
		_rpm = maxf(_rpm - (_rpm * 2.5 / spin_down_time + max_rpm * 0.02) * delta, 0.0)
		if _rpm <= 0.0:
			set_process(false)
	if _rotor:
		var ax := axis.normalized() if axis.length_squared() > 0.0 else Vector3.UP
		_rotor.rotate(ax, -direction * _rpm / 60.0 * TAU * delta)
