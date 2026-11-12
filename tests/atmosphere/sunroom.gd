extends Node3D
## Atmosphere sandbox: a 5 x 4 m room with a west and a south window.
##
## Command-line overrides (after `--`) make tuning renders quick:
##   --eye=x,y,z --at=x,y,z   place the room camera (tools/capture.gd's --pos
##                            camera is created outside the tree, so use these)
##   --vhs=0|1  --osd=0|1  --intensity=0.8  --zoom=1.0  --render_scale=0.75
##   --rig.<export>=value      e.g. --rig.haze_amount=1.5  --rig.exposure_bias=0.5
##   --env.<property>=value    e.g. --env.volumetric_fog_density=0.03
##   --cam.<property>=value    camera attributes, e.g. --cam.auto_exposure_scale=0.3
##   --sun.<property>=value    e.g. --sun.light_volumetric_fog_energy=2.0
##   --vhsp.<uniform>=value    VHS shader uniform, e.g. --vhsp.luma_noise=0.05
## Values are parsed with str_to_var (so Color(...) / Vector3(...) work).

@onready var _rig: AfternoonAtmosphere = $Atmosphere
@onready var _post: PostFx = $PostFx
@onready var _camera: Camera3D = $Camera


func _ready() -> void:
	for a: String in OS.get_cmdline_user_args():
		if not a.begins_with("--") or not a.contains("="):
			continue
		var kv := a.substr(2).split("=", true, 1)
		_apply_arg(kv[0], kv[1])


func _apply_arg(key: String, raw: String) -> void:
	var value: Variant = str_to_var(raw)
	if value == null:
		value = raw
	match key:
		"eye":
			_camera.global_position = _vec(raw)
			return
		"at":
			_camera.look_at(_vec(raw), Vector3.UP)
			return
		"vhs":
			Settings.set_value(&"video", &"vhs_enabled", raw != "0", false)
			return
		"osd":
			Settings.set_value(&"video", &"osd_enabled", raw != "0", false)
			return
		"intensity":
			Settings.set_value(&"video", &"vhs_intensity", float(raw), false)
			return
		"render_scale":
			Settings.set_value(&"video", &"render_scale", float(raw), false)
			return
		"zoom":
			Events.camera_zoom_changed.emit(float(raw))
			return
	var dot := key.find(".")
	if dot < 0:
		return
	var target: Object = null
	match key.substr(0, dot):
		"rig":
			target = _rig
		"env":
			target = _rig.get_world_environment().environment
		"cam":
			target = _rig.get_world_environment().camera_attributes
		"sun":
			target = _rig.get_sun()
		"haze", "dust":
			# Every HazeVolume / DustMotes in the room.
			var want_haze := key.begins_with("haze")
			for n: Node in find_children("*", "", true, false):
				if (want_haze and n is HazeVolume) or (not want_haze and n is DustMotes):
					n.set(key.substr(dot + 1), value)
			return
		"node":
			# --node.<ChildName>.<property>=value
			var rest := key.substr(dot + 1)
			var d2 := rest.find(".")
			var n := get_node_or_null(NodePath(rest.substr(0, d2)))
			if n != null and d2 > 0:
				n.set(rest.substr(d2 + 1), value)
			return
		"vhsp":
			_post.get_vhs_material().set_shader_parameter(StringName(key.substr(dot + 1)), value)
			return
	if target != null:
		target.set(key.substr(dot + 1), value)


func _vec(s: String) -> Vector3:
	var p := s.split(",")
	return Vector3(float(p[0]), float(p[1]), float(p[2]))
