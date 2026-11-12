class_name PropNote
extends StaticBody3D
## A small handwritten note (sticky-note size). Pick a preset, or choose CUSTOM
## and write your own text; the paper then shows an illegible scribble and the
## reader shows `custom_text`.
##
## Lies flat with its origin at the bottom centre. To stick it to a wall or the
## fridge, rotate the instance +90 degrees about X (its face then points +Z).

enum Preset { BACK_BY_4, SHOPPING_LIST, GUTTERS, DENTIST, CUSTOM }

const PRESETS: Dictionary = {
	Preset.BACK_BY_4: {
		"title": "Note",
		"body": "Back by 4.",
		"texture": preload("res://props/textures/note_back_by_4.png"),
		"look": "A sticky note. Three words in blue ballpoint.",
	},
	Preset.SHOPPING_LIST: {
		"title": "List",
		"body": "milk\neggs\nD batteries\nfilm 24 exp\nfoil?",
		"texture": preload("res://props/textures/note_shopping.png"),
		"look": "A shopping list. Nothing on it is crossed off.",
	},
	Preset.GUTTERS: {
		"title": "Note",
		"body": "Call about\ngutters - Tues\nask for Wes",
		"texture": preload("res://props/textures/note_gutters.png"),
		"look": "A reminder about the gutters, pressed hard into the paper.",
	},
	Preset.DENTIST: {
		"title": "Note",
		"body": "Dr. Amsel\nmoved to Thurs\n10:15",
		"texture": preload("res://props/textures/note_dentist.png"),
		"look": "An appointment, moved. It doesn't say which Thursday.",
	},
	Preset.CUSTOM: {
		"title": "Note",
		"body": "",
		"texture": preload("res://props/textures/note_blank.png"),
		"look": "A note in blue ballpoint.",
	},
}

## Which note this is.
@export var preset: Preset = Preset.BACK_BY_4:
	set(value):
		preset = value
		if is_node_ready():
			apply()
## Text shown in the reader when preset is CUSTOM.
@export_multiline var custom_text: String = "":
	set(value):
		custom_text = value
		if is_node_ready():
			apply()
## Reader title when preset is CUSTOM.
@export var custom_title: String = "Note"

@onready var _paper: MeshInstance3D = $Face
@onready var _readable: ReadableInteractable = $Interactable


func _ready() -> void:
	apply()


## Pushes the chosen preset (or custom text) into the face texture and reader.
func apply() -> void:
	var data: Dictionary = PRESETS[preset]
	var mat := (_paper.material_override as StandardMaterial3D).duplicate() as StandardMaterial3D
	mat.albedo_texture = data["texture"]
	_paper.material_override = mat
	if preset == Preset.CUSTOM:
		_readable.title = custom_title
		_readable.body = custom_text
	else:
		_readable.title = data["title"]
		_readable.body = data["body"]
	var obs: Array[String] = [data["look"]]
	_readable.observations = obs
