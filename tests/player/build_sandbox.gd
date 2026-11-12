extends SceneTree
## Generates tests/player/player_sandbox.tscn. Re-run after changing the layout:
##
##   godot --headless --audio-driver Dummy --path . -s res://tests/player/build_sandbox.gd
##
## Layout (metres, player spawns at (0, 0, 7) facing -Z):
##   z  2..10  wood floor; stairs (0.18 m risers) at x 6..8; ramp at x -8..-6
##   z -4..2   carpet (x < 0, with a rug zone) | tile (x > 0, pushable box, radio)
##   z -10..-4 linoleum (x < 0)                | concrete (x > 0, low ceiling)

const OUT := "res://tests/player/player_sandbox.tscn"
const MAT := "res://art/materials/%s.tres"

const L_WORLD := 1 << 0
const L_INTERACT := 1 << 2
const L_PROPS := 1 << 3
const L_TRIGGERS := 1 << 4

var _root: Node3D


func _initialize() -> void:
	_root = Node3D.new()
	_root.name = "PlayerSandbox"
	_environment()
	_room()
	_stairs()
	_ramp()
	_low_ceiling()
	_interactables()
	_props()
	_player()

	var packed := PackedScene.new()
	var err := packed.pack(_root)
	if err == OK:
		err = ResourceSaver.save(packed, OUT)
	if err == OK:
		_strip_player_overrides()
	print("build_sandbox: %s -> %s" % [error_string(err), OUT])
	_root.free()
	quit(0 if err == OK else 1)


## The packer stores redundant overrides on the player instance (its script and
## layers, identical to player.tscn). Drop them so player.tscn stays the source.
func _strip_player_overrides() -> void:
	var text := FileAccess.get_file_as_string(OUT)
	var lines := text.split("\n")
	var out: PackedStringArray = []
	var in_player := false
	for line in lines:
		if line.begins_with("[node "):
			in_player = line.contains("name=\"Player\"")
		elif in_player and (line.begins_with("script = ") or line.begins_with("collision_layer = ") or line.begins_with("collision_mask = ")):
			continue
		out.append(line)
	text = "\n".join(out)
	var re := RegEx.create_from_string("\\[ext_resource type=\"Script\" path=\"res://player/player.gd\"[^\\n]*\\n")
	text = re.sub(text, "")
	var f := FileAccess.open(OUT, FileAccess.WRITE)
	f.store_string(text)
	f.close()


func _own(n: Node, parent: Node = null) -> Node:
	(parent if parent else _root).add_child(n)
	n.owner = _root
	return n


func _mat(name: String) -> Material:
	return load(MAT % name) as Material


func _box(name: String, size: Vector3, center: Vector3, material: String, surface: StringName = &"",
		layer: int = L_WORLD, basis: Basis = Basis.IDENTITY, parent: Node = null) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.name = name
	body.collision_layer = layer
	body.collision_mask = 0
	body.transform = Transform3D(basis, center)
	if surface != &"":
		body.set_meta(&"surface", surface)
	_own(body, parent)
	var shape := BoxShape3D.new()
	shape.size = size
	var col := CollisionShape3D.new()
	col.name = "Shape"
	col.shape = shape
	_own(col, body)
	var mesh := BoxMesh.new()
	mesh.size = size
	var mi := MeshInstance3D.new()
	mi.name = "Mesh"
	mi.mesh = mesh
	mi.material_override = _mat(material)
	_own(mi, body)
	return body


func _group(name: String) -> Node3D:
	var n := Node3D.new()
	n.name = name
	_own(n)
	return n


func _interactable(body: Node, display_name: String, prompt: String, lines: Array[String]) -> void:
	# Loaded at runtime: under -s, scripts that reference autoloads cannot be
	# compiled before the autoloads exist, so no static Interactable reference here.
	var script := load("res://interaction/interactable.gd") as GDScript
	var it := script.new() as Node
	it.name = "Interactable"
	it.set(&"display_name", display_name)
	it.set(&"prompt", prompt)
	it.set(&"observations", lines)
	_own(it, body)


func _environment() -> void:
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.36, 0.55, 0.82)
	sky_mat.sky_horizon_color = Color(0.85, 0.82, 0.74)
	sky_mat.ground_horizon_color = Color(0.7, 0.66, 0.58)
	var sky := Sky.new()
	sky.sky_material = sky_mat
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.7
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.ssao_enabled = true
	var we := WorldEnvironment.new()
	we.name = "WorldEnvironment"
	we.environment = env
	_own(we)

	var sun := DirectionalLight3D.new()
	sun.name = "Sun"
	sun.light_energy = 1.6
	sun.light_color = Color(1.0, 0.93, 0.8)
	sun.shadow_enabled = true
	sun.transform = Transform3D(Basis.from_euler(Vector3(deg_to_rad(-38.0), deg_to_rad(35.0), 0.0)), Vector3(0, 8, 0))
	_own(sun)


func _room() -> void:
	var g := _group("Room")
	_box("FloorWood", Vector3(20, 0.2, 8), Vector3(0, -0.1, 6), "floor_hardwood", &"wood", L_WORLD, Basis.IDENTITY, g)
	_box("FloorCarpet", Vector3(10, 0.2, 6), Vector3(-5, -0.1, -1), "carpet_beige", &"carpet", L_WORLD, Basis.IDENTITY, g)
	_box("FloorTile", Vector3(10, 0.2, 6), Vector3(5, -0.1, -1), "tile_bathroom", &"tile", L_WORLD, Basis.IDENTITY, g)
	_box("FloorLinoleum", Vector3(10, 0.2, 6), Vector3(-5, -0.1, -7), "linoleum_kitchen", &"linoleum", L_WORLD, Basis.IDENTITY, g)
	_box("FloorConcrete", Vector3(10, 0.2, 6), Vector3(5, -0.1, -7), "plastic_grey", &"concrete", L_WORLD, Basis.IDENTITY, g)
	_box("WallNorth", Vector3(20.6, 3, 0.3), Vector3(0, 1.5, -10.15), "wall_plaster_cream", &"", L_WORLD, Basis.IDENTITY, g)
	_box("WallSouth", Vector3(20.6, 3, 0.3), Vector3(0, 1.5, 10.15), "wall_plaster_cream", &"", L_WORLD, Basis.IDENTITY, g)
	_box("WallWest", Vector3(0.3, 3, 20), Vector3(-10.15, 1.5, 0), "wall_wood_paneling", &"", L_WORLD, Basis.IDENTITY, g)
	_box("WallEast", Vector3(0.3, 3, 20), Vector3(10.15, 1.5, 0), "wall_wood_paneling", &"", L_WORLD, Basis.IDENTITY, g)

	# A rug with no collider of its own: an Area3D on the triggers layer
	# overrides the floor's surface while the player stands on it.
	var rug_mesh := MeshInstance3D.new()
	rug_mesh.name = "RugMesh"
	var plane := BoxMesh.new()
	plane.size = Vector3(2.4, 0.01, 1.6)
	rug_mesh.mesh = plane
	rug_mesh.material_override = _mat("carpet_shag_gold")
	rug_mesh.position = Vector3(-2.5, 0.005, 0.5)
	_own(rug_mesh, g)
	var rug := Area3D.new()
	rug.name = "RugZone"
	rug.collision_layer = L_TRIGGERS
	rug.collision_mask = 0
	rug.monitoring = false
	rug.position = Vector3(-2.5, 0.1, 0.5)
	rug.set_meta(&"surface", &"rug")
	_own(rug, g)
	var rug_shape := BoxShape3D.new()
	rug_shape.size = Vector3(2.4, 0.3, 1.6)
	var rc := CollisionShape3D.new()
	rc.name = "Shape"
	rc.shape = rug_shape
	_own(rc, rug)


func _stairs() -> void:
	# Up six 0.18 m risers (0.28 m treads) toward -Z, a landing at 1.08 m, down five.
	var g := _group("Stairs")
	g.set_meta(&"surface", &"wood")  # steps inherit it by walking up parents
	var rise := 0.18
	var run := 0.28
	for i in range(1, 7):
		var h := i * rise
		_box("Up%d" % i, Vector3(2, h, run), Vector3(7, h * 0.5, 8.0 - (i - 0.5) * run), "wood_light", &"", L_WORLD, Basis.IDENTITY, g)
	var top := 6 * rise
	var landing_start := 8.0 - 6 * run
	_box("Landing", Vector3(2, top, landing_start - 4.5), Vector3(7, top * 0.5, (landing_start + 4.5) * 0.5), "wood_medium", &"", L_WORLD, Basis.IDENTITY, g)
	for j in range(1, 6):
		var h := top - j * rise
		_box("Down%d" % j, Vector3(2, h, run), Vector3(7, h * 0.5, 4.5 - (j - 0.5) * run), "wood_light", &"", L_WORLD, Basis.IDENTITY, g)


func _ramp() -> void:
	var g := _group("Ramp")
	var height := 0.8
	var length := 4.0
	var a := atan2(height, length)
	var n := Vector3(0, cos(a), sin(a))
	var slab := sqrt(height * height + length * length) + 0.06
	_box("Slope", Vector3(2, 0.2, slab), Vector3(-7, height * 0.5, 6) - n * 0.1, "wood_medium", &"wood", L_WORLD, Basis(Vector3.RIGHT, a), g)
	_box("Top", Vector3(2, height, 1.5), Vector3(-7, height * 0.5, 3.25), "wood_medium", &"wood", L_WORLD, Basis.IDENTITY, g)


func _low_ceiling() -> void:
	# Underside at 1.35 m: too low to stand (1.75), fine crouched (1.15).
	var g := _group("LowCeiling")
	_box("Slab", Vector3(4, 0.15, 4), Vector3(4, 1.35 + 0.075, -7), "ceiling_popcorn", &"", L_WORLD, Basis.IDENTITY, g)
	for x: float in [2.05, 5.95]:
		for z: float in [-8.95, -5.05]:
			_box("Post", Vector3(0.1, 1.35, 0.1), Vector3(x, 0.675, z), "trim_white", &"", L_WORLD, Basis.IDENTITY, g)


func _interactables() -> void:
	var g := _group("Interactables")
	var wardrobe := _box("Wardrobe", Vector3(1.2, 2.0, 0.6), Vector3(-5, 1.0, -2.2), "wood_dark", &"", L_WORLD | L_INTERACT, Basis.IDENTITY, g)
	_interactable(wardrobe, "Wardrobe", "Look", ["The doors are painted shut.", "Still painted shut."])
	_box("Table", Vector3(1.2, 0.74, 0.6), Vector3(3, 0.37, -2.5), "laminate_formica", &"", L_WORLD, Basis.IDENTITY, g)
	var radio := _box("Radio", Vector3(0.36, 0.2, 0.16), Vector3(3, 0.84, -2.5), "plastic_black", &"", L_WORLD | L_INTERACT, Basis.IDENTITY, g)
	_interactable(radio, "Radio", "Look", ["The dial is set between stations."])
	var calendar := _box("Calendar", Vector3(0.4, 0.55, 0.02), Vector3(-2, 1.55, -9.99), "paper_yellowed", &"", L_WORLD | L_INTERACT, Basis.IDENTITY, g)
	_interactable(calendar, "Calendar", "Look", ["August 1993. Nothing written on it."])


func _props() -> void:
	var box := RigidBody3D.new()
	box.name = "PushBox"
	box.mass = 6.0
	var phys := PhysicsMaterial.new()
	phys.friction = 0.6
	box.physics_material_override = phys
	box.collision_layer = L_PROPS | L_INTERACT
	box.collision_mask = L_WORLD | L_PROPS
	box.position = Vector3(5, 0.26, 0.5)
	_own(box)
	var shape := BoxShape3D.new()
	shape.size = Vector3(0.5, 0.5, 0.5)
	var col := CollisionShape3D.new()
	col.name = "Shape"
	col.shape = shape
	_own(col, box)
	var mesh := BoxMesh.new()
	mesh.size = shape.size
	var mi := MeshInstance3D.new()
	mi.name = "Mesh"
	mi.mesh = mesh
	mi.material_override = _mat("cardboard")
	_own(mi, box)
	_interactable(box, "Box", "Look", ["Empty. It slides when I lean on it."])


func _player() -> void:
	var spawn := Marker3D.new()
	spawn.name = "PlayerSpawn"
	spawn.position = Vector3(0, 0, 7)
	spawn.add_to_group(&"player_spawn", true)
	_own(spawn)
	var player := (load("res://player/player.tscn") as PackedScene).instantiate() as Node3D
	player.position = spawn.position
	_own(player)
	var hud := Label.new()
	hud.name = "DebugHud"
	hud.set_script(load("res://tests/player/sandbox_hud.gd"))
	hud.position = Vector2(12, 8)
	_own(hud)
