extends SceneTree
## Several screenshots of one scene in a single run (software rendering is slow
## to start). Places the camera after the scene is in the tree.
##
##   xvfb-run -a godot --audio-driver Dummy --path . --resolution 640x360 \
##     -s res://tests/fixtures/capture_shots.gd -- --scene=res://tests/fixtures/fixtures_sandbox.tscn \
##     --shots="name@x,y,z@lx,ly,lz;name2@..." [--wait=1.5] [--fov=60] [--all-on] [--open-all]
##
## Shots are written to _shots/<name>.png.

func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var args := {}
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--") and a.contains("="):
			var kv := a.substr(2).split("=", true, 1)
			args[kv[0]] = kv[1]
	var packed := load(String(args.get("scene", "res://tests/fixtures/fixtures_sandbox.tscn"))) as PackedScene
	var scene := packed.instantiate()
	root.add_child(scene)
	current_scene = scene
	var cam := Camera3D.new()
	cam.fov = float(args.get("fov", "60"))
	root.add_child(cam)
	cam.make_current()
	await create_timer(float(args.get("wait", "1.5"))).timeout
	for shot in String(args.get("shots", "")).split(";", false):
		var parts := shot.split("@")
		if parts.size() < 3:
			continue
		cam.global_position = _vec(parts[1])
		cam.look_at(_vec(parts[2]), Vector3.UP)
		for i in 4:
			await process_frame
		await RenderingServer.frame_post_draw
		var out := ProjectSettings.globalize_path("res://").path_join("_shots/%s.png" % parts[0])
		DirAccess.make_dir_recursive_absolute(out.get_base_dir())
		var err := root.get_texture().get_image().save_png(out)
		print("shot %s: %s" % [parts[0], error_string(err)])
	quit(0)


func _vec(s: String) -> Vector3:
	var p := s.split(",")
	return Vector3(float(p[0]), float(p[1]), float(p[2]))
