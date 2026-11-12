extends SceneTree
## Headless test for the house level, played through the real main.tscn.
##
##   godot --headless --audio-driver Dummy --path . -s res://tests/level/test_house.gd
##
## Checks: no errors on load, one spawn, the player stands at the spawn, floor
## surfaces per room, a driven walk spawn -> living room -> kitchen -> back with
## 0.9 m clear along the route, every Interactable has a prompt and a name, the
## front door refuses, and a closet door, drawer, lamp, TV and fridge respond.
## Prints PASS/FAIL per check and exits non-zero on any failure.
##
## The checks live in house_test_runner.gd, loaded at run time: a `-s` script is
## compiled before the autoloads (Game, Events, Audio) exist, so it must not
## reference them, or any class that does, directly.

const RUNNER := "res://tests/level/house_test_runner.gd"


func _initialize() -> void:
	var script := load(RUNNER) as GDScript
	if script == null:
		push_error("test_house: cannot load %s" % RUNNER)
		quit(1)
		return
	var runner := script.new() as Node
	runner.name = "HouseTestRunner"
	root.add_child(runner)
