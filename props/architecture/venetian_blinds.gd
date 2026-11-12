@tool
class_name VenetianBlinds
extends StaticBody3D
## Horizontal slat blinds built from real slats, so the sun throws striped
## shadows across the room.
##
## Origin: top centre of the head rail, at the back (the surface it is screwed
## to). The blind hangs down -Y and its front faces +Z. Size it to the window
## opening with `width` / `height`; tilt with `slat_angle`.
##
## All geometry and collision is generated (internal children, never saved), so
## the scene stays a single node plus its Interactable.

@export_group("Size")
## Overall width of the head rail and slats.
@export_range(0.2, 4.0, 0.01, "suffix:m") var width: float = 0.9:
	set(v):
		width = v
		_queue_rebuild()
## Drop from the top of the head rail to the bottom of the bottom rail when fully lowered.
@export_range(0.2, 3.0, 0.01, "suffix:m") var height: float = 1.2:
	set(v):
		height = v
		_queue_rebuild()
## 0 = fully lowered, 1 = pulled all the way up (slats stack under the head rail).
@export_range(0.0, 1.0, 0.01) var raised: float = 0.0:
	set(v):
		raised = v
		_queue_rebuild()

@export_group("Slats")
## Tilt in degrees. 0 = slats level (most light), +/-80 = closed.
@export_range(-85.0, 85.0, 0.5, "suffix:deg") var slat_angle: float = 30.0:
	set(v):
		slat_angle = v
		_queue_rebuild()
## Depth of each slat (front to back). 0.025 = 1" mini blind, 0.05 = 2".
@export_range(0.015, 0.09, 0.001, "suffix:m") var slat_width: float = 0.05:
	set(v):
		slat_width = v
		_queue_rebuild()
## Vertical spacing between slats.
@export_range(0.012, 0.08, 0.001, "suffix:m") var slat_pitch: float = 0.043:
	set(v):
		slat_pitch = v
		_queue_rebuild()
## Index (counted from the bottom) of one slat bent out of line. -1 = none.
@export var bent_slat: int = 4:
	set(v):
		bent_slat = v
		_queue_rebuild()

@export_group("Look")
@export var slat_material: Material = preload("res://art/materials/metal_painted_white.tres"):
	set(v):
		slat_material = v
		_queue_rebuild()
@export var cord_material: Material = preload("res://art/materials/paper_white.tres"):
	set(v):
		cord_material = v
		_queue_rebuild()
@export var wand_material: Material = preload("res://art/materials/glass_dusty.tres"):
	set(v):
		wand_material = v
		_queue_rebuild()

const RAIL_HEIGHT := 0.03
const RAIL_DEPTH := 0.055
const SLAT_THICKNESS := 0.0018
const STACK_PITCH := 0.0055

var _built: Array[Node] = []
var _rebuild_queued: bool = false


func _ready() -> void:
	_rebuild()


func _queue_rebuild() -> void:
	if not is_inside_tree() or _rebuild_queued:
		return
	_rebuild_queued = true
	_rebuild.call_deferred()


func _rebuild() -> void:
	_rebuild_queued = false
	for n in _built:
		if is_instance_valid(n):
			n.queue_free()
	_built.clear()

	var z_mid := RAIL_DEPTH * 0.5 + 0.005
	# Head rail
	_add_box(Vector3(width, RAIL_HEIGHT, RAIL_DEPTH), Vector3(0.0, -RAIL_HEIGHT * 0.5, z_mid), slat_material)
	# Slats
	var usable := height - RAIL_HEIGHT * 2.0 - 0.01
	var count := maxi(1, floori(usable / slat_pitch))
	# Raising a blind gathers slats from the bottom up into a tight stack that
	# rides on the bottom rail; the slats above it keep hanging at full pitch.
	var hanging := count - roundi(count * raised)
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	var slat_mesh := BoxMesh.new()
	slat_mesh.size = Vector3(width - 0.012, SLAT_THICKNESS, slat_width)
	mm.mesh = slat_mesh
	mm.instance_count = count
	var y := -RAIL_HEIGHT - 0.008
	var bottom_y := y
	for j in count:
		var stacked := j >= hanging
		if j > 0:
			y -= STACK_PITCH if stacked else slat_pitch
		var angle := deg_to_rad(75.0 if stacked else slat_angle)
		var basis := Basis(Vector3.RIGHT, angle)
		if count - 1 - j == bent_slat and not stacked:
			basis = Basis(Vector3.RIGHT, angle + deg_to_rad(28.0)) * Basis(Vector3.FORWARD, deg_to_rad(1.5))
		mm.set_instance_transform(j, Transform3D(basis, Vector3(0.0, y, z_mid)))
		bottom_y = minf(bottom_y, y)
	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	mmi.material_override = slat_material
	_attach(mmi)
	# Bottom rail
	var rail_y := bottom_y - 0.016
	_add_box(Vector3(width - 0.008, 0.016, slat_width * 0.8), Vector3(0.0, rail_y, z_mid), slat_material)
	# Ladder strings, front and back of the slats
	var ladders := maxi(2, ceili(width / 0.55))
	var ladder_len := -RAIL_HEIGHT - rail_y
	for k in ladders:
		var x := lerpf(-width * 0.5 + 0.08, width * 0.5 - 0.08, float(k) / float(ladders - 1))
		for side: float in [-1.0, 1.0]:
			_add_cyl(0.0009, ladder_len, Vector3(x, -RAIL_HEIGHT - ladder_len * 0.5, z_mid + side * slat_width * 0.5 * cos(deg_to_rad(slat_angle))), cord_material)
	# Lift cords with tassels (right), tilt wand (left)
	var cord_len := clampf(height * 0.65, 0.3, 1.6)
	for k in 2:
		var x := width * 0.5 - 0.05 - k * 0.012
		_add_cyl(0.0013, cord_len, Vector3(x, -RAIL_HEIGHT - cord_len * 0.5, z_mid + RAIL_DEPTH * 0.5 + 0.004), cord_material)
		_add_cyl(0.006, 0.03, Vector3(x, -RAIL_HEIGHT - cord_len - 0.012 - k * 0.02, z_mid + RAIL_DEPTH * 0.5 + 0.004), slat_material, 0.0035)
	var wand_len := clampf(height * 0.55, 0.3, 1.2)
	_add_cyl(0.0045, wand_len, Vector3(-width * 0.5 + 0.05, -RAIL_HEIGHT - wand_len * 0.5, z_mid + RAIL_DEPTH * 0.5 + 0.006), wand_material)

	# Collision: one thin slab over the lowered part
	var col := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	var drop := -rail_y + 0.01
	shape.size = Vector3(width, drop, maxf(RAIL_DEPTH, slat_width) + 0.01)
	col.shape = shape
	col.position = Vector3(0.0, -drop * 0.5, z_mid)
	_attach(col)


func _add_box(size: Vector3, pos: Vector3, mat: Material) -> void:
	var mi := MeshInstance3D.new()
	var m := BoxMesh.new()
	m.size = size
	mi.mesh = m
	mi.material_override = mat
	mi.position = pos
	_attach(mi)


func _add_cyl(r: float, h: float, pos: Vector3, mat: Material, r_top: float = -1.0) -> void:
	var mi := MeshInstance3D.new()
	var m := CylinderMesh.new()
	m.bottom_radius = r
	m.top_radius = r if r_top < 0.0 else r_top
	m.height = h
	m.radial_segments = 6
	m.rings = 1
	mi.mesh = m
	mi.material_override = mat
	mi.position = pos
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF if r < 0.002 else GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	_attach(mi)


func _attach(n: Node) -> void:
	add_child(n, false, Node.INTERNAL_MODE_BACK)
	_built.append(n)
