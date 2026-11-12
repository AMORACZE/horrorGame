extends SceneTree
## Headless-friendly screenshot tool. Loads a scene, waits, saves a PNG, quits.
##
##   xvfb-run -a godot --path . --resolution 960x540 -s res://tools/capture.gd -- \
##       --scene=res://tests/foo.tscn --out=_shots/foo.png [--wait=2.0] \
##       [--pos=0,1.6,3 --look=0,1,0 --fov=68]
##
## --pos/--look add a free camera and make it current (otherwise the scene's own
## current camera is used). --out may be absolute or relative to the project.
## Software rendering is slow: keep the resolution small and --wait short.

func _initialize() -> void:
	var args := {}
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--") and a.contains("="):
			var kv := a.substr(2).split("=", true, 1)
			args[kv[0]] = kv[1]
	if not args.has("scene"):
		push_error("capture: --scene=res://... is required")
		quit(1)
		return

	var packed := load(args["scene"]) as PackedScene
	if packed == null:
		push_error("capture: cannot load %s" % args["scene"])
		quit(1)
		return
	var scene := packed.instantiate()
	root.add_child(scene)
	current_scene = scene

	if args.has("pos"):
		var cam := Camera3D.new()
		cam.fov = float(args.get("fov", "68"))
		# The root is not in the tree yet during _initialize, so place the camera
		# with local transforms (it is a direct child of the root: local == global).
		var pos := _vec(args["pos"])
		if args.has("look"):
			cam.look_at_from_position(pos, _vec(args["look"]), Vector3.UP)
		else:
			cam.position = pos
		root.add_child(cam)
		cam.make_current()

	await create_timer(float(args.get("wait", "1.5"))).timeout
	await RenderingServer.frame_post_draw

	var out: String = args.get("out", "_shots/capture.png")
	if not out.is_absolute_path():
		out = ProjectSettings.globalize_path("res://").path_join(out)
	DirAccess.make_dir_recursive_absolute(out.get_base_dir())
	var err := root.get_texture().get_image().save_png(out)
	print("capture: %s -> %s" % [error_string(err), out])
	quit(0 if err == OK else 1)


func _vec(s: String) -> Vector3:
	var p := s.split(",")
	return Vector3(float(p[0]), float(p[1]), float(p[2]))
