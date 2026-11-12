extends SceneTree
## Multi-shot screenshot helper for the prop gallery (one scene load, many views).
##
##   xvfb-run -a godot --audio-driver Dummy --path . --resolution 960x540 \
##       -s res://tests/props/shots.gd -- --scene=res://tests/props/prop_gallery.tscn \
##       --out=_shots --wait=1.5 --fov=60 \
##       --shots="name:px,py,pz:lx,ly,lz;name2:..."

func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var args := {}
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--") and a.contains("="):
			var kv := a.substr(2).split("=", true, 1)
			args[kv[0]] = kv[1]
	var packed := load(String(args.get("scene", "res://tests/props/prop_gallery.tscn"))) as PackedScene
	var scene := packed.instantiate()
	root.add_child(scene)
	current_scene = scene
	var cam := Camera3D.new()
	cam.fov = float(args.get("fov", "60"))
	root.add_child(cam)
	cam.make_current()
	var out_dir: String = args.get("out", "_shots")
	if not out_dir.is_absolute_path():
		out_dir = ProjectSettings.globalize_path("res://").path_join(out_dir)
	DirAccess.make_dir_recursive_absolute(out_dir)
	await create_timer(float(args.get("wait", "1.5"))).timeout
	for shot in String(args.get("shots", "")).split(";", false):
		var parts := shot.split(":")
		cam.global_position = _vec(parts[1])
		cam.look_at(_vec(parts[2]), Vector3.UP)
		for i in 4:
			await process_frame
		await RenderingServer.frame_post_draw
		var path := out_dir.path_join(parts[0] + ".png")
		var err := root.get_texture().get_image().save_png(path)
		print("shot: %s -> %s" % [error_string(err), path])
	quit(0)


func _vec(s: String) -> Vector3:
	var p := s.split(",")
	return Vector3(float(p[0]), float(p[1]), float(p[2]))
