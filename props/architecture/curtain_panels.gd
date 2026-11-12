@tool
class_name CurtainPanels
extends StaticBody3D
## A pair of pleated curtain panels on a rod: sheer or heavy 70s drapes.
##
## Origin: top centre at the wall surface. The rod sits `rod_offset` in front
## of the wall at y = 0 and the fabric hangs down to y = -height. Front is +Z.
## `width` is the span the panels cover when closed (usually window width plus
## 0.2 m); `open_amount` gathers each panel toward its end of the rod.
##
## Fabric is a generated double-sided pleated mesh; collision is one thin box
## per panel, so an opened pair does not block the window between them.

@export_group("Size")
@export_range(0.4, 6.0, 0.01, "suffix:m") var width: float = 1.6:
	set(v):
		width = v
		_queue_rebuild()
@export_range(0.3, 3.0, 0.01, "suffix:m") var height: float = 1.7:
	set(v):
		height = v
		_queue_rebuild()
## Distance from the wall to the rod.
@export_range(0.03, 0.3, 0.005, "suffix:m") var rod_offset: float = 0.12:
	set(v):
		rod_offset = v
		_queue_rebuild()

@export_group("Drape")
## 0 = closed (panels meet in the middle), 1 = drawn fully to the sides.
@export_range(0.0, 1.0, 0.01) var open_amount: float = 0.0:
	set(v):
		open_amount = v
		_queue_rebuild()
## Fabric width per panel relative to the half-span it covers when closed.
@export_range(1.0, 3.0, 0.05) var fullness: float = 1.8:
	set(v):
		fullness = v
		_queue_rebuild()
## Width of one fold.
@export_range(0.04, 0.3, 0.005, "suffix:m") var pleat_width: float = 0.11:
	set(v):
		pleat_width = v
		_queue_rebuild()
## Pinch-pleated header band and rings (heavy drapes) or a plain rod pocket (sheers).
@export var pinch_pleat_header: bool = false:
	set(v):
		pinch_pleat_header = v
		_queue_rebuild()

@export_group("Look")
@export var fabric_material: Material:
	set(v):
		fabric_material = v
		_queue_rebuild()
@export var rod_material: Material = preload("res://art/materials/metal_brass.tres"):
	set(v):
		rod_material = v
		_queue_rebuild()
@export var show_rod: bool = true:
	set(v):
		show_rod = v
		_queue_rebuild()

const COLS_PER_PLEAT := 6
const ROWS := 10

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

	var half := width * 0.5
	var fabric_w := half * fullness
	# Covered width per panel: from closed (half span) down to fully gathered.
	var gathered := maxf(0.12, fabric_w * 0.16)
	var covered := lerpf(half, gathered, open_amount)
	var top_y := -0.035 if pinch_pleat_header else -0.012
	for side: float in [-1.0, 1.0]:
		var outer_x := side * half
		var inner_x := side * (half - covered)
		_build_panel(minf(outer_x, inner_x), maxf(outer_x, inner_x), fabric_w, top_y, side)
		var col := CollisionShape3D.new()
		var shape := BoxShape3D.new()
		shape.size = Vector3(covered, height, 0.08)
		col.shape = shape
		col.position = Vector3((outer_x + inner_x) * 0.5, -height * 0.5, rod_offset)
		_attach(col)
	if show_rod:
		_build_rod()


func _build_panel(x0: float, x1: float, fabric_w: float, top_y: float, side: float) -> void:
	var covered := x1 - x0
	var pleats := maxi(2, roundi(fabric_w / pleat_width))
	var wavelength := covered / float(pleats)
	# Amplitude so the folded length roughly matches the fabric width.
	var ratio := maxf(fabric_w / covered, 1.0)
	var amp := clampf(wavelength * sqrt(2.0 * (ratio * ratio - 1.0)) / TAU, 0.004, 0.09)
	var cols := pleats * COLS_PER_PLEAT
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var verts: Array[Vector3] = []
	var norms: Array[Vector3] = []
	for r in ROWS + 1:
		var v := float(r) / float(ROWS)
		var y := lerpf(top_y, -height, v)
		# Folds open up a little toward the hem, and the hem swings slightly.
		var a := amp * (0.85 + 0.35 * v)
		var sway := sin(v * PI * 0.5) * 0.012 * side
		for c in cols + 1:
			var u := float(c) / float(cols)
			var x := lerpf(x0, x1, u)
			var phase := TAU * (x - x0) / wavelength
			var z := rod_offset + a * sin(phase) + sway * u
			var dz := a * cos(phase) * TAU / wavelength
			verts.append(Vector3(x, y, z))
			norms.append(Vector3(-dz, 0.0, 1.0).normalized())
	var stride := cols + 1
	# Front faces then back faces (offset slightly, reversed winding).
	for pass_i in 2:
		var back := pass_i == 1
		var base := (ROWS + 1) * stride * pass_i
		for i in verts.size():
			var n := -norms[i] if back else norms[i]
			st.set_normal(n)
			st.set_uv(Vector2(verts[i].x, -verts[i].y))
			st.add_vertex(verts[i] - norms[i] * (0.0015 if back else 0.0))
		for r in ROWS:
			for c in cols:
				var i0 := base + r * stride + c
				var i1 := i0 + 1
				var i2 := i0 + stride
				var i3 := i2 + 1
				# Godot treats clockwise (seen from the viewer) as front-facing.
				if back:
					st.add_index(i0); st.add_index(i2); st.add_index(i1)
					st.add_index(i1); st.add_index(i2); st.add_index(i3)
				else:
					st.add_index(i0); st.add_index(i1); st.add_index(i2)
					st.add_index(i1); st.add_index(i3); st.add_index(i2)
	var mi := MeshInstance3D.new()
	mi.mesh = st.commit()
	mi.material_override = fabric_material
	_attach(mi)
	if pinch_pleat_header:
		# Stiff header band with a pinch at every second fold, hung from rings.
		var band := BoxMesh.new()
		band.size = Vector3(covered, 0.09, amp * 1.2 + 0.01)
		_add_mesh(band, Vector3((x0 + x1) * 0.5, top_y - 0.045, rod_offset), fabric_material)
		var pinch := CylinderMesh.new()
		pinch.top_radius = 0.012
		pinch.bottom_radius = 0.008
		pinch.height = 0.1
		pinch.radial_segments = 8
		pinch.rings = 1
		var ring := TorusMesh.new()
		ring.inner_radius = 0.016
		ring.outer_radius = 0.021
		ring.rings = 12
		ring.ring_segments = 6
		for k in pleats + 1:
			var x := lerpf(x0, x1, float(k) / float(pleats))
			if k % 2 == 0:
				_add_mesh(pinch, Vector3(x, top_y - 0.045, rod_offset + amp * 0.6 + 0.006), fabric_material)
			_add_mesh(ring, Vector3(x, 0.0, rod_offset), rod_material, Vector3(PI * 0.5, 0.0, 0.0))


func _build_rod() -> void:
	var rod_len := width + 0.16
	var rod := CylinderMesh.new()
	rod.top_radius = 0.011 if pinch_pleat_header else 0.007
	rod.bottom_radius = rod.top_radius
	rod.height = rod_len
	rod.radial_segments = 12
	rod.rings = 1
	_add_mesh(rod, Vector3(0.0, 0.0, rod_offset), rod_material, Vector3(0.0, 0.0, PI * 0.5))
	var finial := SphereMesh.new()
	finial.radius = 0.026 if pinch_pleat_header else 0.014
	finial.height = finial.radius * 2.0
	finial.radial_segments = 12
	finial.rings = 6
	var bracket := BoxMesh.new()
	bracket.size = Vector3(0.012, 0.02, rod_offset)
	for side: float in [-1.0, 1.0]:
		_add_mesh(finial, Vector3(side * (rod_len * 0.5 + finial.radius * 0.8), 0.0, rod_offset), rod_material)
		_add_mesh(bracket, Vector3(side * (width * 0.5 + 0.04), 0.0, rod_offset * 0.5), rod_material)


func _add_mesh(mesh: Mesh, pos: Vector3, mat: Material, rot: Vector3 = Vector3.ZERO) -> void:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = mat
	mi.position = pos
	mi.rotation = rot
	_attach(mi)


func _attach(n: Node) -> void:
	add_child(n, false, Node.INTERNAL_MODE_BACK)
	_built.append(n)
