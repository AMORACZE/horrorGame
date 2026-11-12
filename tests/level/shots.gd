extends SceneTree
## Several views of the house through the real game (main.tscn: player camera,
## UI, camcorder post-process) in one run.
##
##   xvfb-run -a godot --audio-driver Dummy --path . --resolution 960x540 \
##     -s res://tests/level/shots.gd -- [--shots=name@x,z@yaw,pitch;...] [--wait=6] [--settle=2.5]
##
## Each shot teleports the player to (x, 0, z) and looks at yaw/pitch degrees
## (yaw 0 = north / -Z, 90 = west, 180 = south, -90 = east). The eye is the
## player's own (1.6 m). Without --shots the default reference set is taken.
## Frames go to _shots/level/<name>.png (gitignored).

const DEFAULT_SHOTS := "spawn@1.0,0.5@180,-6;" \
	+ "hall_east@0.7,0.9@-90,-4;" \
	+ "living_from_opening@1.7,2.1@150,-12;" \
	+ "living_tv@1.2,3.4@-80,-10;" \
	+ "living_west@4.6,3.0@100,-10;" \
	+ "living_sofa_sun@3.8,5.6@50,-22;" \
	+ "kitchen_from_living@4.2,3.3@-90,-8;" \
	+ "kitchen_dinette@9.4,3.0@140,-18;" \
	+ "kitchen_sink@8.0,3.0@175,-25;" \
	+ "pantry@7.4,3.2@-15,-6"


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var args := {}
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--") and a.contains("="):
			var kv := a.substr(2).split("=", true, 1)
			args[kv[0]] = kv[1]
	var packed := load("res://main.tscn") as PackedScene
	var main := packed.instantiate()
	root.add_child(main)
	current_scene = main
	await create_timer(0.5).timeout
	_uncover()
	var player := _find_player()
	if player == null:
		push_error("shots: no player")
		quit(1)
		return
	var shots := String(args.get("shots", DEFAULT_SHOTS)).split(";", false)
	var first := true
	for shot in shots:
		var parts := shot.split("@")
		if parts.size() < 3:
			continue
		var xz := parts[1].split(",")
		var yp := parts[2].split(",")
		var xf := Transform3D(Basis.IDENTITY, Vector3(float(xz[0]), 0.0, float(xz[1])))
		player.call(&"teleport", xf)
		player.call(&"set_look", deg_to_rad(float(yp[0])), deg_to_rad(float(yp[1])), true)
		var wait := float(args.get("wait", "6")) if first else float(args.get("settle", "2.5"))
		first = false
		var t := 0.0
		while t < wait:
			await create_timer(0.1).timeout
			t += 0.1
			player.call(&"set_look", deg_to_rad(float(yp[0])), deg_to_rad(float(yp[1])), true)
			_uncover()
		await RenderingServer.frame_post_draw
		var out := ProjectSettings.globalize_path("res://").path_join("_shots/level/%s.png" % parts[0])
		DirAccess.make_dir_recursive_absolute(out.get_base_dir())
		var err := root.get_texture().get_image().save_png(out)
		print("shot %s: %s" % [parts[0], error_string(err)])
	quit(0)


func _uncover() -> void:
	var fade_script := load("res://ui/fade/screen_fade.gd") as GDScript
	if fade_script == null:
		return
	var cur: Variant = fade_script.get(&"current")
	if cur is Object and is_instance_valid(cur):
		(cur as Object).call(&"set_covered", false)


func _find_player() -> Node3D:
	for n in root.get_tree().get_nodes_in_group(&"player"):
		return n as Node3D
	return null
