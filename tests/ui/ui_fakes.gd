extends RefCounted
## Stand-in interactables for the UI sandbox and tests. Not used by the game.


## A door whose prompt flips Open <-> Close each use, like the real one will.
class FakeDoor extends Interactable:
	var is_open: bool = false

	func _init() -> void:
		display_name = "Front door"
		prompt = "Open"

	func get_prompt() -> String:
		return "Close" if is_open else "Open"

	func _interact(_interactor: Node) -> void:
		is_open = not is_open


const LINES: PackedStringArray = [
	"It's locked.",
	"The receiver is warm.",
	"Someone left the fan on. It turns the same way it always has, slow, back and forth, as if the room still needs it.",
	"Dust on the glass.",
]

const DOCS := {
	ReadableInteractable.Style.PAPER: ["Note on the counter", "Back by four. Don't let the dog in, she's been in the creek again.\n\nThe man about the gutters may call. Tell him Tuesday is fine, but not before ten.\n\n— M."],
	ReadableInteractable.Style.HANDWRITTEN: ["Grocery list", "milk (2%)\neggs\ncoffee filters\nbatteries — the square ones\nTab\nsomething for Sunday\n\ncall Dr. Hale re: Thursday"],
	ReadableInteractable.Style.TYPED: ["Notice", "To the occupant of 1418 Larkin Road:\n\nThis is to inform you that the water service at the above address will be interrupted on Monday, August 30, between the hours of 9:00 a.m. and 3:00 p.m. while repairs are made to the main on Larkin Road.\n\nWe regret any inconvenience.\n\nCounty Water Department\nService Division"],
	ReadableInteractable.Style.LABEL: ["Tape 3", "Lake — July 4\nSP mode. Do not tape over."],
	ReadableInteractable.Style.PRINT: ["Operating your new answering machine", "Thank you for choosing the TA-2200. Before you begin, please read these instructions completely and keep them for future reference.\n\nSetting the clock. Press and hold DAY until the display flashes. Use the + and – keys to select the current day, then press DAY again to confirm. Repeat for the hour and minute.\n\nRecording your greeting. Press and hold GREETING. Wait for the tone, then speak clearly at a normal distance from the unit. Release GREETING when you have finished. The machine will play your greeting back automatically.\n\nPlaying messages. When the MESSAGE light is flashing, press PLAY. Messages are played in the order they were received. Press SKIP to advance to the next message, or REPEAT to hear the current message again.\n\nRemote access. From any touch-tone telephone, call your number and enter your two-digit security code during the greeting. You may then use the keypad to play, save or erase messages.\n\nCare of your machine. Keep the unit away from heat, moisture and direct sunlight. Do not place heavy objects on top of the cassette door. If the unit does not operate correctly, unplug it for one minute and try again.\n\nIf you continue to have difficulty, consult your dealer. Do not attempt to open the cabinet; there are no user-serviceable parts inside."],
}


static func make_door(parent: Node) -> FakeDoor:
	var body := StaticBody3D.new()
	body.name = "Door"
	parent.add_child(body)
	var d := FakeDoor.new()
	body.add_child(d)
	return d


static func make_plain(parent: Node, name: String, lines: PackedStringArray) -> Interactable:
	var body := StaticBody3D.new()
	body.name = name.to_pascal_case()
	parent.add_child(body)
	var i := Interactable.new()
	i.display_name = name
	var arr: Array[String] = []
	arr.assign(lines)
	i.observations = arr
	body.add_child(i)
	return i


## A beige cordless phone handset: box body, keypad face, stub antenna.
static func make_examinable(parent: Node) -> ExaminableInteractable:
	var body := StaticBody3D.new()
	body.name = "Phone"
	parent.add_child(body)
	body.position = Vector3(3.0, 0.8, -2.0)
	body.rotation_degrees = Vector3(0, 35, 0)
	var beige: Material = load("res://art/materials/plastic_beige.tres")
	var dark: Material = load("res://art/materials/plastic_black.tres")
	var grey: Material = load("res://art/materials/plastic_grey.tres")
	_box(body, Vector3(0.055, 0.2, 0.03), Vector3.ZERO, beige)
	_box(body, Vector3(0.04, 0.035, 0.004), Vector3(0, 0.06, 0.016), dark)        # display
	for r in 4:
		for c in 3:
			_box(body, Vector3(0.011, 0.008, 0.004), Vector3(-0.014 + c * 0.014, 0.018 - r * 0.014, 0.016), grey)
	var ant := MeshInstance3D.new()
	var cyl := CylinderMesh.new()
	cyl.top_radius = 0.004
	cyl.bottom_radius = 0.005
	cyl.height = 0.07
	ant.mesh = cyl
	ant.material_override = dark
	ant.position = Vector3(0.018, 0.13, -0.004)
	body.add_child(ant)
	var e := ExaminableInteractable.new()
	e.display_name = "Cordless phone"
	e.description = "Beige plastic, warm from the sun. The battery light is still on."
	body.add_child(e)
	return e


static func _box(parent: Node3D, size: Vector3, pos: Vector3, mat: Material) -> void:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	mi.material_override = mat
	mi.position = pos
	parent.add_child(mi)


static func make_readable(parent: Node, style: int) -> ReadableInteractable:
	var body := StaticBody3D.new()
	body.name = "Readable%d" % style
	parent.add_child(body)
	var r := ReadableInteractable.new()
	var d: Array = DOCS[style]
	r.title = d[0]
	r.body = d[1]
	r.style = style as ReadableInteractable.Style
	r.display_name = d[0]
	body.add_child(r)
	return r


## A bright, blown-out "afternoon room" backdrop for screenshots: warm wall,
## a window that clips to white, a darker floor band. Pure 2D, cheap to render.
static func make_backdrop(parent: Node) -> CanvasLayer:
	var layer := CanvasLayer.new()
	layer.layer = -10
	parent.add_child(layer)
	var wall := TextureRect.new()
	var g := Gradient.new()
	g.set_color(0, Color(0.93, 0.86, 0.72))
	g.set_color(1, Color(0.78, 0.66, 0.5))
	var tex := GradientTexture2D.new()
	tex.gradient = g
	tex.fill_from = Vector2(0.3, 0.0)
	tex.fill_to = Vector2(0.6, 1.0)
	wall.texture = tex
	wall.stretch_mode = TextureRect.STRETCH_SCALE
	wall.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	wall.set_anchors_preset(Control.PRESET_FULL_RECT)
	layer.add_child(wall)
	var window := ColorRect.new()
	window.color = Color(1.0, 0.99, 0.96)
	window.anchor_left = 0.36
	window.anchor_right = 0.66
	window.anchor_top = 0.12
	window.anchor_bottom = 0.62
	layer.add_child(window)
	for x: float in [0.505]:
		var mullion := ColorRect.new()
		mullion.color = Color(0.82, 0.78, 0.7)
		mullion.anchor_left = x
		mullion.anchor_right = x
		mullion.offset_right = 8
		mullion.anchor_top = 0.12
		mullion.anchor_bottom = 0.62
		layer.add_child(mullion)
	var floor_band := ColorRect.new()
	floor_band.color = Color(0.55, 0.4, 0.26)
	floor_band.anchor_top = 0.8
	floor_band.anchor_bottom = 1.0
	floor_band.anchor_right = 1.0
	layer.add_child(floor_band)
	return layer
