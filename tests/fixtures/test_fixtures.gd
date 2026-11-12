extends SceneTree
## Headless test for the fixture scenes and interaction behaviours.
##
##   godot --headless --audio-driver Dummy --path . -s res://tests/fixtures/test_fixtures.gd
##
## Instantiates every fixture, uses each interactable twice and checks that the
## state changes and comes back, prompts follow, locks hold, flags unlock,
## switches drive their targets, lights warm up, and doors never push into the
## player. Prints PASS/FAIL per check; exits non-zero on any failure.
##
## The checks live in fixture_test_runner.gd, loaded at run time: a `-s` script
## is compiled before the autoloads (Game, Events, Audio) are registered, so it
## must not reference them, or any class that does, directly.

const RUNNER := "res://tests/fixtures/fixture_test_runner.gd"


func _initialize() -> void:
	var script := load(RUNNER) as GDScript
	if script == null:
		push_error("test_fixtures: cannot load %s" % RUNNER)
		quit(1)
		return
	var runner := script.new() as Node
	runner.name = "FixtureTestRunner"
	root.add_child(runner)
