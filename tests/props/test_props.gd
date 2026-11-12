extends SceneTree
## Headless check of every prop scene under res://props/.
##
##   godot --headless --audio-driver Dummy --path . -s res://tests/props/test_props.gd
##
## The checks live in prop_test_runner.gd. It is loaded at runtime rather than
## referenced here, because a `-s` script compiles before the autoloads (Events,
## Game) exist, and the interaction scripts depend on them.


func _initialize() -> void:
	var script := load("res://tests/props/prop_test_runner.gd") as GDScript
	var runner := script.new() as Node
	runner.name = "PropTestRunner"
	root.add_child.call_deferred(runner)
