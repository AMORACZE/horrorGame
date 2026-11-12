extends SceneTree
## Automated check for the atmosphere system. Prints PASS/FAIL per check and
## exits non-zero on any failure.
##
##   godot --headless --audio-driver Dummy --path . -s res://tests/atmosphere/test_atmosphere.gd
##
## Headless uses the dummy renderer, which still parses shaders, so shader
## syntax errors are caught here (they arrive through the error logger).
## PostFx / CamcorderOsd are used untyped: they reference autoloads, and this
## script is compiled before autoloads exist.


class ErrorCatcher extends Logger:
	var errors: PackedStringArray = []
	var warnings: PackedStringArray = []
	var _mutex := Mutex.new()

	func _log_error(function: String, file: String, line: int, code: String, rationale: String,
			_editor_notify: bool, error_type: int, _script_backtraces: Array[ScriptBacktrace]) -> void:
		var msg := "%s (%s:%d %s) %s" % [code, file, line, function, rationale]
		_mutex.lock()
		if error_type == ERROR_TYPE_WARNING:
			warnings.append(msg)
		else:
			errors.append(msg)
		_mutex.unlock()

	func _log_message(_message: String, _error: bool) -> void:
		pass


const RIG := "res://atmosphere/afternoon_atmosphere.tscn"
const DUST := "res://atmosphere/dust_motes.tscn"
const HAZE := "res://atmosphere/haze_volume.tscn"
const POST := "res://atmosphere/post_fx.tscn"
const ROOM := "res://tests/atmosphere/sunroom.tscn"
const SHADERS: PackedStringArray = [
	"res://atmosphere/shaders/vhs.gdshader",
	"res://atmosphere/shaders/dust_mote.gdshader",
]

var _failures: int = 0
var _catcher := ErrorCatcher.new()


func _initialize() -> void:
	OS.add_logger(_catcher)
	_run.call_deferred()


func _check(ok: bool, what: String) -> void:
	if ok:
		print("PASS  ", what)
	else:
		_failures += 1
		print("FAIL  ", what)


func _frames(n: int) -> void:
	for i: int in n:
		await process_frame


func _instance(path: String) -> Node:
	var packed := load(path) as PackedScene
	_check(packed != null, "load %s" % path)
	if packed == null:
		return null
	var node := packed.instantiate()
	_check(node != null, "instantiate %s" % path)
	return node


func _run() -> void:
	var settings: Node = root.get_node(^"Settings")
	var events: Node = root.get_node(^"Events")
	var saved := {}
	for key: StringName in [&"vhs_enabled", &"vhs_intensity", &"osd_enabled", &"render_scale"]:
		saved[key] = settings.call(&"get_value", &"video", key)

	# --- Shaders compile --------------------------------------------------------
	for path: String in SHADERS:
		var before := _catcher.errors.size()
		var sh := load(path) as Shader
		_check(sh != null, "load shader %s" % path)
		if sh != null:
			var uniforms := sh.get_shader_uniform_list()
			_check(uniforms.size() > 0 and _catcher.errors.size() == before,
					"shader compiles %s (%d uniforms)" % [path.get_file(), uniforms.size()])

	# --- Rig ------------------------------------------------------------------
	var rig := _instance(RIG) as AfternoonAtmosphere
	if rig != null:
		root.add_child(rig)
		await _frames(2)
		_check(rig.name == &"Atmosphere", "rig root is named Atmosphere")
		var sun := rig.get_node_or_null(^"Sun") as DirectionalLight3D
		_check(sun != null and sun.shadow_enabled, "rig has shadowed DirectionalLight3D 'Sun'")
		var we := rig.get_world_environment()
		_check(we != null and we.environment != null and we.camera_attributes != null,
				"rig has WorldEnvironment with environment + camera attributes")
		if we != null and we.environment != null and sun != null:
			var env := we.environment
			var shared := load("res://atmosphere/environments/afternoon.tres") as Environment
			_check(env.sdfgi_enabled and env.volumetric_fog_enabled and env.ssao_enabled
					and env.glow_enabled and env.background_mode == Environment.BG_SKY,
					"environment: SDFGI, volumetric fog, SSAO, glow, sky")
			_check(we.camera_attributes.auto_exposure_enabled, "camera attributes: auto exposure on")
			# Sun direction: light travels down and towards the east (+X).
			var travel := -sun.global_basis.z
			_check(travel.y < -0.5 and travel.x > 0.5, "sun shines down from the west-southwest (%s)" % travel)
			rig.haze_amount = 2.0
			_check(is_equal_approx(env.volumetric_fog_density, shared.volumetric_fog_density * 2.0),
					"haze_amount scales fog density")
			_check(is_equal_approx(shared.volumetric_fog_density, 0.02) and env != shared,
					"knobs never touch the shared afternoon.tres")
			var base_scale: float = (load("res://atmosphere/environments/camcorder_exposure.tres") as CameraAttributes).auto_exposure_scale
			rig.exposure_bias = 1.0
			_check(is_equal_approx(we.camera_attributes.auto_exposure_scale, base_scale * 2.0),
					"exposure_bias +1 doubles the auto-exposure target")
			rig.sun_elevation = 20.0
			_check(absf(rad_to_deg(asin(-(-sun.global_basis.z).y)) - 20.0) < 0.5, "sun_elevation moves the sun")
		rig.queue_free()

	# --- Dust and haze --------------------------------------------------------------
	var dust := _instance(DUST) as DustMotes
	if dust != null:
		root.add_child(dust)
		await _frames(1)
		dust.box_size = Vector3(2, 2, 2)
		dust.density = 30.0
		_check(dust.amount == 240 and dust.get_mote_count() == 240, "dust amount follows box size x density")
		var pm := dust.process_material as ParticleProcessMaterial
		_check(pm != null and pm.emission_box_extents.is_equal_approx(Vector3.ONE), "dust emission box follows box_size")
		_check(dust.emitting and dust.preprocess >= dust.lifetime * 0.9, "dust is pre-warmed (no pop-in)")
		dust.queue_free()
	var haze := _instance(HAZE) as HazeVolume
	if haze != null:
		root.add_child(haze)
		await _frames(1)
		haze.haze_density = 0.05
		_check(is_equal_approx((haze.material as FogMaterial).density, 0.05), "haze_density drives the FogMaterial")
		haze.queue_free()

	# --- Post FX ----------------------------------------------------------------------
	settings.call(&"set_value", &"video", &"vhs_enabled", true, false)
	settings.call(&"set_value", &"video", &"vhs_intensity", 1.0, false)
	settings.call(&"set_value", &"video", &"osd_enabled", true, false)
	var post := _instance(POST) as CanvasLayer
	if post != null:
		root.add_child(post)
		await _frames(2)
		var mat := post.call(&"get_vhs_material") as ShaderMaterial
		var vhs := post.get_node(^"Vhs") as CanvasItem
		var osd := post.call(&"get_osd") as Control
		var osd_layer := post.get_node(^"OsdLayer") as CanvasLayer
		_check(post.layer == 50 and osd_layer.layer == 40, "post fx on layer 50, OSD on layer 40")
		_check(mat != null and mat.shader != null, "VHS material present")
		_check(vhs.visible and is_equal_approx(float(mat.get_shader_parameter(&"intensity")), 1.0),
				"VHS on at intensity 1.0 from Settings")
		settings.call(&"set_value", &"video", &"vhs_intensity", 0.4, false)
		_check(is_equal_approx(float(mat.get_shader_parameter(&"intensity")), 0.4),
				"video/vhs_intensity reaches the shader")
		settings.call(&"set_value", &"video", &"vhs_enabled", false, false)
		_check(not vhs.visible, "video/vhs_enabled=false hides the VHS pass")
		settings.call(&"set_value", &"video", &"vhs_enabled", true, false)
		_check(vhs.visible, "video/vhs_enabled=true shows it again")
		settings.call(&"set_value", &"video", &"osd_enabled", false, false)
		_check(not osd.visible, "video/osd_enabled=false hides the OSD")
		settings.call(&"set_value", &"video", &"osd_enabled", true, false)
		_check(osd.visible, "video/osd_enabled=true shows the OSD")
		settings.call(&"set_value", &"video", &"render_scale", 0.75, false)
		_check(is_equal_approx(root.scaling_3d_scale, 0.75), "video/render_scale reaches the 3D viewport")

		_check(str(osd.call(&"get_time_text")) == "PM 3:47" and str(osd.call(&"get_date_text")) == "AUG 21 1993",
				"OSD stamp starts at '%s'" % osd.call(&"get_stamp_text"))
		var counter := str(osd.call(&"get_counter_text"))
		_check(counter.count(":") == 2, "OSD tape counter '%s'" % counter)

		var blur_before := float(post.call(&"get_focus_blur"))
		events.emit_signal(&"camera_zoom_changed", 1.0)
		await _frames(3)
		var blur_after := float(post.call(&"get_focus_blur"))
		_check(blur_after > blur_before + 0.05, "zoom signal starts the autofocus hunt (blur %.2f)" % blur_after)
		_check(float(mat.get_shader_parameter(&"tele")) > 0.0, "zoom signal reaches the shader tele noise")
		_check(is_equal_approx(float(osd.get(&"zoom_amount")), 1.0) and float(osd.get(&"zoom_bar_alpha")) > 0.0,
				"zoom signal shows the OSD zoom bar")
		# The hunt settles.
		await create_timer(2.5).timeout
		var blur_end := float(post.call(&"get_focus_blur"))
		_check(blur_end < 0.02, "autofocus settles (blur %.3f)" % blur_end)
		post.queue_free()

	# --- The test room instantiates with everything inside -------------------------------
	var room := _instance(ROOM)
	if room != null:
		root.add_child(room)
		await _frames(3)
		room.queue_free()

	await _frames(2)
	for key: StringName in saved:
		settings.call(&"set_value", &"video", key, saved[key], false)

	var own_warnings: PackedStringArray = []
	for w: String in _catcher.warnings:
		if w.contains("atmosphere"):
			own_warnings.append(w)
	for e: String in _catcher.errors:
		print("  error: ", e)
	for w: String in own_warnings:
		print("  warning: ", w)
	_check(_catcher.errors.is_empty(), "no errors logged (%d)" % _catcher.errors.size())
	_check(own_warnings.is_empty(), "no warnings from atmosphere code (%d)" % own_warnings.size())

	print("")
	print("atmosphere tests: %s (%d failure(s))" % ["PASS" if _failures == 0 else "FAIL", _failures])
	OS.remove_logger(_catcher)
	quit(0 if _failures == 0 else 1)
