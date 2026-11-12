@tool
class_name DustMotes
extends GPUParticles3D
## A box of slowly drifting dust. Motes are lit only by direct light, so they
## show inside sun shafts (and near practical lamps) and disappear in shadow.
## Place one per sunlit window, covering the volume the shaft passes through.

## Size of the dust volume in metres (centred on this node).
@export var box_size: Vector3 = Vector3(2.0, 2.2, 2.0):
	set(v):
		box_size = v.max(Vector3(0.1, 0.1, 0.1))
		_rebuild()
## Motes per cubic metre. 25–60 reads as "dusty house"; above 100 it looks like smoke.
@export_range(1.0, 200.0, 1.0) var density: float = 40.0:
	set(v):
		density = v
		_rebuild()
## Brightness of a mote in direct sun.
@export_range(0.0, 4.0, 0.05) var mote_brightness: float = 1.6:
	set(v):
		mote_brightness = v
		_rebuild()
## Mote diameter in metres.
@export_range(0.001, 0.03, 0.0005) var mote_size: float = 0.006:
	set(v):
		mote_size = v
		_rebuild()
## Drift speed multiplier (1 = still, warm air).
@export_range(0.0, 4.0, 0.05) var drift: float = 1.0:
	set(v):
		drift = v
		_rebuild()

const MAX_MOTES := 12000


func _ready() -> void:
	# Each instance tunes its own copy of the process material.
	if process_material != null and not process_material.resource_local_to_scene:
		process_material = process_material.duplicate()
	_rebuild()


## Number of motes this volume will spawn for its size and density.
func get_mote_count() -> int:
	var vol := box_size.x * box_size.y * box_size.z
	return clampi(int(round(vol * density)), 1, MAX_MOTES)


func _rebuild() -> void:
	if not is_node_ready():
		return
	var n := get_mote_count()
	if amount != n:
		amount = n
	var half := box_size * 0.5
	visibility_aabb = AABB(-half - Vector3.ONE * 0.25, box_size + Vector3.ONE * 0.5)
	var pm := process_material as ParticleProcessMaterial
	if pm != null:
		pm.emission_box_extents = half
		pm.initial_velocity_min = 0.004 * drift
		pm.initial_velocity_max = 0.016 * drift
		pm.gravity = Vector3(0.0, -0.0007, 0.0) * drift
		pm.turbulence_noise_speed = Vector3(0.015, 0.004, 0.01) * drift
	set_instance_shader_parameter(&"mote_size", mote_size)
	set_instance_shader_parameter(&"brightness", mote_brightness)
