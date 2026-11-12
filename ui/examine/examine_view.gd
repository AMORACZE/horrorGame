class_name ExamineView
extends UIModal
## Close-up view of an object held in the hands.
##
## On Events.examine_requested the object's render-only copy
## (`create_examine_visual()`) is placed in a SubViewport with its own World3D,
## camera and soft studio lighting, so it reads the same in any room. The world
## behind is dimmed and blurred. Drag / right stick turns it, wheel / triggers
## zoom, interact or back puts it down.

@export_group("Framing")
## Vertical field of view of the examine camera (narrow = less distortion).
@export var camera_fov: float = 30.0
## Extra room around the object's bounding sphere when fitting.
@export var fit_margin: float = 1.45
## Fraction of the camera distance the object is lifted above screen centre,
## so the caption has room underneath.
@export var lift: float = 0.035
@export_group("Control")
@export var mouse_turn_speed: float = 0.008     ## radians per pixel
@export var stick_turn_speed: float = 3.0       ## radians per second at full tilt
@export var spin_damping: float = 6.0           ## how fast a flicked object settles
@export var zoom_min: float = 0.55              ## multiplier on fitted distance (closer)
@export var zoom_max: float = 1.6
@export var wheel_step: float = 0.1
@export var trigger_zoom_speed: float = 1.2     ## zoom units per second

@onready var _dim: ColorRect = %Dim
@onready var _viewport: SubViewport = %Viewport
@onready var _pivot: Node3D = %Pivot
@onready var _camera: Camera3D = %Camera
@onready var _title: Label = %Title
@onready var _description: Label = %Description

var _examinable: ExaminableInteractable = null
var _visual: Node3D = null
var _fit_distance: float = 1.0
var _zoom: float = 1.0
var _zoom_target: float = 1.0
var _spin := Vector2.ZERO
var _dragging: bool = false
var _putdown_sound: StringName = &""
var _intro: float = 1.0


func _ready() -> void:
	super._ready()
	process_mode = Node.PROCESS_MODE_PAUSABLE
	_viewport.own_world_3d = true
	_viewport.transparent_bg = true
	_viewport.render_target_update_mode = SubViewport.UPDATE_DISABLED
	_camera.fov = camera_fov
	_camera.environment = _make_environment()
	# Soft three-point light: warm key upper left, cool fill right, rim behind.
	_aim(%KeyLight, Vector3(-1.0, 1.25, 1.4))
	_aim(%FillLight, Vector3(1.4, 0.2, 0.9))
	_aim(%RimLight, Vector3(0.4, 0.9, -1.4))
	Events.examine_requested.connect(open)


static func _aim(light: Node3D, from: Vector3) -> void:
	light.basis = Basis.looking_at(-from.normalized(), Vector3.UP if absf(from.normalized().y) < 0.99 else Vector3.FORWARD)


static func _make_environment() -> Environment:
	var env := Environment.new()
	env.background_mode = Environment.BG_CLEAR_COLOR
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.86, 0.82, 0.76)
	env.ambient_light_energy = 0.42
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_exposure = 1.05
	return env


func get_examinable() -> ExaminableInteractable:
	return _examinable


func get_visual() -> Node3D:
	return _visual


func get_title_text() -> String:
	return _title.text


func open(examinable: ExaminableInteractable) -> void:
	if examinable == null:
		return
	if _open:
		_clear_visual()
	_examinable = examinable
	_visual = examinable.create_examine_visual()
	_pivot.add_child(_visual)
	_visual.scale = Vector3.ONE * maxf(examinable.examine_scale, 0.01)
	var radius: float = float(_visual.get_meta(&"bounds_radius", 0.25))
	_fit_distance = radius * fit_margin / sin(deg_to_rad(camera_fov) * 0.5)
	_camera.near = maxf(_fit_distance * 0.02, 0.005)
	_camera.far = _fit_distance * 6.0 + radius * 4.0
	_pivot.basis = Basis.from_euler(examine_rotation(examinable))
	_zoom = 1.12
	_zoom_target = 1.0
	_spin = Vector2.ZERO
	_intro = 0.0
	_place_camera()

	_title.text = examinable.get_display_name()
	_title.visible = _title.text != ""
	_description.text = examinable.description.strip_edges()
	_description.visible = _description.text != ""
	_putdown_sound = examinable.putdown_sound

	_viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	UIInput.sound(examinable.pickup_sound)
	begin_open()


static func examine_rotation(examinable: ExaminableInteractable) -> Vector3:
	var d := examinable.examine_rotation_degrees
	return Vector3(deg_to_rad(d.x), deg_to_rad(d.y), deg_to_rad(d.z))


func _on_close() -> void:
	_dragging = false
	UIInput.sound(_putdown_sound)
	Events.examine_closed.emit()


func _on_hidden() -> void:
	_clear_visual()
	_viewport.render_target_update_mode = SubViewport.UPDATE_DISABLED


func _clear_visual() -> void:
	if is_instance_valid(_visual):
		_visual.queue_free()
	_visual = null
	_examinable = null


func _input(event: InputEvent) -> void:
	if not _open:
		return
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_LEFT:
			_dragging = mb.pressed
		elif mb.pressed and mb.button_index == MOUSE_BUTTON_WHEEL_UP:
			_zoom_target = clampf(_zoom_target - wheel_step, zoom_min, zoom_max)
			get_viewport().set_input_as_handled()
		elif mb.pressed and mb.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			_zoom_target = clampf(_zoom_target + wheel_step, zoom_min, zoom_max)
			get_viewport().set_input_as_handled()
	elif event is InputEventMouseMotion and _dragging:
		var mm := event as InputEventMouseMotion
		_turn(mm.relative * mouse_turn_speed)
		# Remember the flick so the object keeps turning a little after release.
		_spin = _spin.lerp(mm.relative * mouse_turn_speed * 60.0, 0.5)
	super._input(event)


func _process(delta: float) -> void:
	super._process(delta)
	if not _open:
		return
	# Right stick (look_*) or WASD / left stick turn the object.
	var look := Input.get_vector(&"look_left", &"look_right", &"look_up", &"look_down")
	var move := Input.get_vector(&"move_left", &"move_right", &"move_forward", &"move_back")
	var stick := look if look.length() > move.length() else move
	if stick != Vector2.ZERO:
		_turn(stick * stick_turn_speed * delta)
		_spin = Vector2.ZERO
	elif not _dragging:
		_turn(_spin * delta)
		_spin = _spin.lerp(Vector2.ZERO, clampf(spin_damping * delta, 0.0, 1.0))
	# Triggers zoom: right = closer, left = further.
	var zoom_axis := 0.0
	for pad in Input.get_connected_joypads():
		zoom_axis += Input.get_joy_axis(pad, JOY_AXIS_TRIGGER_LEFT) - Input.get_joy_axis(pad, JOY_AXIS_TRIGGER_RIGHT)
	if absf(zoom_axis) > 0.1:
		_zoom_target = clampf(_zoom_target + zoom_axis * trigger_zoom_speed * delta, zoom_min, zoom_max)
	_zoom = lerpf(_zoom, _zoom_target, clampf(delta * 10.0, 0.0, 1.0))
	_intro = minf(_intro + delta * 4.0, 1.0)
	_place_camera()


func _turn(amount: Vector2) -> void:
	# Turn about the camera's axes, so "drag right" always spins it right.
	_pivot.basis = (Basis(Vector3.UP, amount.x) * Basis(Vector3.RIGHT, amount.y) * _pivot.basis).orthonormalized()


func _place_camera() -> void:
	var d := _fit_distance * _zoom
	_camera.position = Vector3(0.0, -d * lift, d)
	_camera.rotation = Vector3.ZERO
	_dim.material.set(&"shader_parameter/amount", _intro)
