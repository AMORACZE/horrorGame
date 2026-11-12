extends Node3D
## Material gallery: builds a test bed for every material in art/materials.
##
## * Architecture bays (x = 0 .. ~26): a 3 x 2.4 m wall (+ trim_white baseboard)
##   and a 3 x 2 m floor strip per bay, lit by the low raking sun. Bay 0 also
##   has an X-facing side wall to check that panel grooves stay vertical.
## * Ceiling bay: a slab at 2.44 m with a practical lamp under it.
## * Window bay (z < -6): wall with an opening, glass, sheer curtain and a
##   blown-out backdrop card outside, sun shining in through it.
## * Prop grid (z >= 5): a 1 m cube and a 1 m sphere per remaining material.
##
## Run: godot --path . res://tests/art/material_gallery.tscn  (WASD-free; use
## tools/capture.gd with --pos/--look for screenshots, see art/README.md).

const MAT_DIR := "res://art/materials/"

const WALLS: Array[String] = [
	"wall_wood_paneling", "wall_plaster_cream", "wallpaper_floral", "wallpaper_stripe",
	"brick_red", "tile_bathroom", "trim_white", "concrete",
]
const FLOORS: Array[String] = [
	"carpet_shag_gold", "floor_hardwood", "carpet_beige", "linoleum_kitchen",
	"floor_hardwood_dusty", "tile_bathroom", "linoleum_kitchen", "concrete",
]
const CEILINGS: Array[String] = ["ceiling_popcorn", "ceiling_popcorn_stained"]
const SKIP_IN_GRID: Array[String] = ["window_blown_out", "glass_window"]

const BAY_W := 3.0
const BAY_STEP := 3.4
const GRID_COLS := 4
const GRID_DX := 3.0
const GRID_DZ := 5.0
const GRID_Z0 := 6.0

@export var build_architecture: bool = true
@export var build_grid: bool = true
@export var build_window: bool = true


var _only: Array[String] = []


func _ready() -> void:
	# --gonly=a,b,c : build just those materials in the grid (fast screenshots)
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--gonly="):
			for n in a.substr(8).split(","):
				_only.append(n)
			build_architecture = false
			build_window = false
	if build_architecture:
		_build_bays()
		_build_ceiling_bay()
	if build_window:
		_build_window_bay()
	if build_grid:
		_build_grid()
	_setup_camera()


## Optional view for screenshots: --gcam=px,py,pz,lx,ly,lz[,fov] in the user args.
func _setup_camera() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--gcam="):
			var p := a.substr(7).split(",")
			var cam := Camera3D.new()
			cam.fov = float(p[6]) if p.size() > 6 else 62.0
			add_child(cam)
			cam.look_at_from_position(Vector3(float(p[0]), float(p[1]), float(p[2])),
				Vector3(float(p[3]), float(p[4]), float(p[5])), Vector3.UP)
			cam.make_current()
			_force_current.call_deferred(cam)


func _force_current(cam: Camera3D) -> void:
	await get_tree().process_frame
	cam.make_current()


func _mat(mat_name: String) -> Material:
	var m := load(MAT_DIR + mat_name + ".tres") as Material
	if m == null:
		push_error("material_gallery: missing material %s" % mat_name)
	return m


func _box(size: Vector3, pos: Vector3, mat_name: String, parent: Node3D = self) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	mi.material_override = _mat(mat_name)
	mi.position = pos
	parent.add_child(mi)
	return mi


func _label(text: String, pos: Vector3, size: int = 40) -> void:
	var l := Label3D.new()
	l.text = text
	l.font_size = size
	l.pixel_size = 0.004
	l.outline_size = 10
	l.modulate = Color(1, 1, 1)
	l.outline_modulate = Color(0, 0, 0)
	l.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	l.position = pos
	add_child(l)


func _build_bays() -> void:
	for i in WALLS.size():
		var x := i * BAY_STEP
		# back wall: Z-facing, 3 x 2.4 m, 0.15 thick, front face at z = 0
		_box(Vector3(BAY_W, 2.4, 0.15), Vector3(x, 1.2, -0.075), WALLS[i])
		# baseboard
		_box(Vector3(BAY_W, 0.09, 0.02), Vector3(x, 0.045, 0.01), "trim_white")
		# floor strip 3 x 2 m, top at y = 0
		_box(Vector3(BAY_W, 0.05, 2.0), Vector3(x, -0.025, 1.0), FLOORS[i])
		_label("%s\n%s (floor)" % [WALLS[i], FLOORS[i]], Vector3(x, 2.65, 0.3), 36)
	# X-facing side wall at the left of bay 0 (checks groove orientation on X faces)
	_box(Vector3(0.15, 2.4, 2.0), Vector3(-BAY_W * 0.5 - 0.075, 1.2, 1.0), WALLS[0])


func _build_ceiling_bay() -> void:
	# ceiling slabs are 2.4 m and aligned to the 2.4 m world grid so the
	# stained variant shows its single, centred stain
	var x0 := ceilf((WALLS.size() * BAY_STEP) / 2.4) * 2.4 + 1.2
	for j in CEILINGS.size():
		var x := x0 + j * 4.8
		_box(Vector3(2.4, 0.1, 2.4), Vector3(x, 2.49, 1.2), CEILINGS[j])
		_box(Vector3(BAY_W, 2.44, 0.15), Vector3(x, 1.22, -0.075), "wall_plaster_cream")
		_box(Vector3(BAY_W, 0.05, 2.4), Vector3(x, -0.025, 1.2), "carpet_beige")
		var lamp := OmniLight3D.new()
		lamp.position = Vector3(x, 1.7, 1.2)
		lamp.light_color = Color(1.0, 0.82, 0.6)
		lamp.light_energy = 1.6
		lamp.omni_range = 4.0
		lamp.shadow_enabled = true
		add_child(lamp)
		# lampshade around the bulb (open cylinder, two-sided, backlit)
		var shade := MeshInstance3D.new()
		var cyl := CylinderMesh.new()
		cyl.top_radius = 0.16
		cyl.bottom_radius = 0.24
		cyl.height = 0.3
		cyl.cap_top = false
		cyl.cap_bottom = false
		shade.mesh = cyl
		shade.material_override = _mat("fabric_lampshade")
		shade.position = Vector3(x, 1.7, 1.2)
		shade.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(shade)
		_label(CEILINGS[j] + "\n(lamp-lit, viewed from below)", Vector3(x, 2.2, 2.3), 32)


func _build_window_bay() -> void:
	# Room interior on the -z side of a wall at z = -6; the sun (travelling -z)
	# shines in through the opening. Opening 1.2 x 1.2 m, sill at 0.9 m.
	var z := -6.0
	var cx := -14.0
	var mat := "wall_plaster_cream"
	_box(Vector3(4.0, 0.9, 0.15), Vector3(cx, 0.45, z), mat)
	_box(Vector3(4.0, 0.34, 0.15), Vector3(cx, 2.27, z), mat)
	_box(Vector3(1.4, 1.2, 0.15), Vector3(cx - 1.3, 1.5, z), mat)
	_box(Vector3(1.4, 1.2, 0.15), Vector3(cx + 1.3, 1.5, z), mat)
	# frame / muntins in trim
	_box(Vector3(1.2, 0.04, 0.05), Vector3(cx, 1.5, z), "trim_white")
	_box(Vector3(0.04, 1.2, 0.05), Vector3(cx, 1.5, z), "trim_white")
	# glass: alpha pass, no shadow; gi off so SDFGI does not see a wall
	var glass := _box(Vector3(1.2, 1.2, 0.006), Vector3(cx, 1.5, z + 0.03), "glass_window")
	glass.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	glass.gi_mode = GeometryInstance3D.GI_MODE_DISABLED
	# sheer curtain covering the left half, just inside the room
	var sheer := _box(Vector3(0.75, 1.5, 0.01), Vector3(cx - 0.35, 1.45, z - 0.15), "fabric_curtain_sheer")
	sheer.gi_mode = GeometryInstance3D.GI_MODE_DISABLED
	# heavy drape on the right
	_box(Vector3(0.45, 2.1, 0.06), Vector3(cx + 0.85, 1.2, z - 0.15), "fabric_curtain_heavy")
	# floor inside the room
	_box(Vector3(9.0, 0.05, 5.0), Vector3(cx - 2.5, -0.025, z - 2.6), "floor_hardwood")
	# blown-out exterior card 3 m outside (alpha pass: never blocks the sun)
	var card := _box(Vector3(8.0, 5.0, 0.02), Vector3(cx, 2.5, z + 3.0), "window_blown_out")
	card.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	card.gi_mode = GeometryInstance3D.GI_MODE_DISABLED
	_label("window bay: glass_window, fabric_curtain_sheer,\nfabric_curtain_heavy, window_blown_out", Vector3(cx, 2.75, z - 0.4), 30)


func _build_grid() -> void:
	var names: Array[String] = []
	var dir := DirAccess.open(MAT_DIR)
	if dir == null:
		push_error("material_gallery: cannot open %s" % MAT_DIR)
		return
	for f in dir.get_files():
		var fname := f.trim_suffix(".remap")
		if fname.ends_with(".tres"):
			var n := fname.get_basename()
			if n in SKIP_IN_GRID:
				continue
			names.append(n)
	names.sort()
	if not _only.is_empty():
		names = _only
	var sphere := SphereMesh.new()
	sphere.radius = 0.5
	sphere.height = 1.0
	sphere.radial_segments = 48
	sphere.rings = 24
	for i in names.size():
		var col := i % GRID_COLS
		var row := i / GRID_COLS
		var base := Vector3(col * GRID_DX, 0.0, GRID_Z0 + row * GRID_DZ)
		_box(Vector3(1, 1, 1), base + Vector3(-0.6, 0.5, 0), names[i])
		var s := MeshInstance3D.new()
		s.mesh = sphere
		s.material_override = _mat(names[i])
		s.position = base + Vector3(0.65, 0.5, 0)
		add_child(s)
		_label(names[i], base + Vector3(0, 1.3, 0.3), 36)
	# ground for the grid
	var ground := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(GRID_COLS * GRID_DX + 4, (names.size() / GRID_COLS + 2) * GRID_DZ + 2)
	ground.mesh = pm
	var gm := StandardMaterial3D.new()
	gm.albedo_color = Color(0.32, 0.32, 0.31)
	gm.roughness = 0.95
	ground.material_override = gm
	ground.position = Vector3((GRID_COLS - 1) * GRID_DX * 0.5, -0.001, GRID_Z0 + (names.size() / GRID_COLS) * GRID_DZ * 0.5)
	add_child(ground)
