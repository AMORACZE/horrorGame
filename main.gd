extends Node
## Game root. Composes the persistent pieces (player, UI, camcorder post-process)
## around a level. Levels never instance the player or UI themselves, so any
## level can be swapped in here, or run through tests/ with a different rig.

@export_file("*.tscn") var level_scene: String = "res://levels/house/house.tscn"
@export_file("*.tscn") var player_scene: String = "res://player/player.tscn"
@export_file("*.tscn") var ui_scene: String = "res://ui/ui_root.tscn"
@export_file("*.tscn") var post_fx_scene: String = "res://atmosphere/post_fx.tscn"

@onready var _world: Node3D = $World


func _ready() -> void:
	var level := _instance(level_scene)
	if level:
		_world.add_child(level)
		Game.level = level

	var player := _instance(player_scene) as Node3D
	if player:
		_world.add_child(player)
		var spawn := get_tree().get_first_node_in_group(&"player_spawn") as Node3D
		if spawn:
			player.global_transform = spawn.global_transform
			if player.has_method(&"reset_view"):
				player.call(&"reset_view")

	for path: String in [ui_scene, post_fx_scene]:
		var layer := _instance(path)
		if layer:
			add_child(layer)

	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	if level:
		Events.level_ready.emit(level)


func _instance(path: String) -> Node:
	if path.is_empty() or not ResourceLoader.exists(path):
		push_warning("Main: missing scene '%s'" % path)
		return null
	return (load(path) as PackedScene).instantiate()
