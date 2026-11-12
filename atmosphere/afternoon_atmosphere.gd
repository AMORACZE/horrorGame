@tool
class_name AfternoonAtmosphere
extends Node3D
## Late-August, 3:45 pm lighting rig: sky, sun, GI, haze, grade and camcorder
## auto-exposure. A level instances afternoon_atmosphere.tscn once and tunes the
## handful of knobs below; everything else lives in
## atmosphere/environments/afternoon.tres and camcorder_exposure.tres.
##
## The knobs are applied to private copies of those resources, so tuning one
## level never edits the shared look (the originals are put back while the
## editor saves, so a level scene stores only the knob values).

const _ENV_NODE := ^"WorldEnvironment"
const _SUN_NODE := ^"Sun"

@export_group("Sun")
## Compass bearing the sunlight comes FROM, in degrees: 0 north (-Z), 90 east (+X),
## 180 south (+Z), 270 west (-X). Default is west-southwest.
@export_range(0.0, 360.0, 0.5, "degrees") var sun_azimuth: float = 250.0:
	set(v):
		sun_azimuth = v
		_apply()
## Height of the sun above the horizon, degrees. Lower = longer shafts.
@export_range(5.0, 85.0, 0.5, "degrees") var sun_elevation: float = 37.0:
	set(v):
		sun_elevation = v
		_apply()
## Direct sunlight energy. Shafts, floor patches and bounce all scale with it.
@export_range(0.0, 8.0, 0.05) var sun_energy: float = 3.2:
	set(v):
		sun_energy = v
		_apply()

@export_group("Air")
## Multiplies the volumetric haze (shaft visibility) and the distance haze.
## 0 = clear air, 1 = the tuned look, 2 = a very thick, dusty room.
@export_range(0.0, 3.0, 0.05) var haze_amount: float = 1.0:
	set(v):
		haze_amount = v
		_apply()

@export_group("Camera")
## Exposure offset in stops on top of the camcorder auto-iris. +1 = aim for twice
## the brightness. (Applied to the auto-exposure target: the auto-iris would
## simply cancel a plain exposure multiplier.)
@export_range(-3.0, 3.0, 0.05, "suffix:EV") var exposure_bias: float = 0.0:
	set(v):
		exposure_bias = v
		_apply()

@export_group("Quality")
## Volumetric fog froxel grid (global RenderingServer setting, applied at
## runtime). The engine default 64 x 64 makes shafts mushy and streaky in small
## rooms (streaks radiate from the view centre); 160 x 128 keeps them clean. Lower on weak GPUs.
@export_range(32, 256, 16) var fog_volume_size: int = 160:
	set(v):
		fog_volume_size = v
		_apply_quality()
@export_range(32, 256, 16) var fog_volume_depth: int = 128:
	set(v):
		fog_volume_depth = v
		_apply_quality()

var _base_env: Environment
var _base_cam: CameraAttributes
var _env: Environment
var _cam: CameraAttributes


func _ready() -> void:
	_ensure_resources()
	_apply()
	_apply_quality()


func _notification(what: int) -> void:
	if what == NOTIFICATION_EDITOR_PRE_SAVE:
		_restore_shared_resources()
	elif what == NOTIFICATION_EDITOR_POST_SAVE:
		_ensure_resources()
		_apply()


## The sun light. Levels may read it (e.g. to align a window) but should tune it
## through the exported knobs.
func get_sun() -> DirectionalLight3D:
	return get_node_or_null(_SUN_NODE) as DirectionalLight3D


func get_world_environment() -> WorldEnvironment:
	return get_node_or_null(_ENV_NODE) as WorldEnvironment


## Unit vector pointing from the scene towards the sun.
func get_sun_direction() -> Vector3:
	var az := deg_to_rad(sun_azimuth)
	var el := deg_to_rad(sun_elevation)
	return Vector3(sin(az) * cos(el), sin(el), -cos(az) * cos(el)).normalized()


func _ensure_resources() -> void:
	var we := get_world_environment()
	if we == null:
		return
	if _base_env == null:
		_base_env = we.environment
	if _base_cam == null:
		_base_cam = we.camera_attributes
	if _base_env != null and (_env == null or we.environment != _env):
		_env = _base_env.duplicate(true) as Environment
		we.environment = _env
	if _base_cam != null and (_cam == null or we.camera_attributes != _cam):
		_cam = _base_cam.duplicate(true) as CameraAttributes
		we.camera_attributes = _cam


func _restore_shared_resources() -> void:
	var we := get_world_environment()
	if we == null:
		return
	if _base_env != null:
		we.environment = _base_env
	if _base_cam != null:
		we.camera_attributes = _base_cam
	_env = null
	_cam = null


func _apply() -> void:
	if not is_node_ready():
		return
	var sun := get_sun()
	if sun != null:
		var to_sun := get_sun_direction()
		# A DirectionalLight3D shines along its local -Z.
		sun.global_basis = Basis.looking_at(-to_sun, Vector3.UP if absf(to_sun.y) < 0.999 else Vector3.FORWARD)
		sun.light_energy = sun_energy
	if _env != null and _base_env != null:
		_env.volumetric_fog_density = _base_env.volumetric_fog_density * haze_amount
		_env.fog_density = _base_env.fog_density * haze_amount
		_env.volumetric_fog_enabled = _base_env.volumetric_fog_enabled and haze_amount > 0.0
	if _cam != null and _base_cam != null:
		_cam.auto_exposure_scale = _base_cam.auto_exposure_scale * pow(2.0, exposure_bias)


func _apply_quality() -> void:
	if not is_node_ready():
		return
	RenderingServer.environment_set_volumetric_fog_volume_size(fog_volume_size, fog_volume_depth)
	RenderingServer.environment_set_volumetric_fog_filter_active(true)
