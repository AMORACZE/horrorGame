extends SceneTree
## Automated UI test. Instances the real ui_root.tscn, drives it only through
## the Events bus and simulated input, and asserts what ends up on screen.
##
##   godot --headless --audio-driver Dummy --path . -s res://tests/ui/test_ui.gd
##
## Prints PASS/FAIL per check; exits non-zero if anything failed.
## The checks live in test_ui_runner.gd: a script run with -s is compiled before
## the autoloads exist, so it cannot name Events / Game / Settings itself.


func _initialize() -> void:
	var runner: Node = (load("res://tests/ui/test_ui_runner.gd") as GDScript).new()
	runner.name = "TestUIRunner"
	root.add_child(runner)
