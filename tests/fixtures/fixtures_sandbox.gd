extends Node3D
## Fixtures sandbox: every fixture in one lit room. Runs on its own.
##
## Command-line options (after `--`), handy with tools/capture.gd:
##   --all-on    switch on every light, fan and device shortly after load
##   --open-all  open every door, drawer and lid

var _all_on: bool = false
var _open_all: bool = false


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a == "--all-on":
			_all_on = true
		elif a == "--open-all":
			_open_all = true
	if _all_on or _open_all:
		_apply.call_deferred()


func _apply() -> void:
	await get_tree().physics_frame
	for n in _all_interactables(self):
		if _all_on:
			if n is SwitchInteractable and (n as SwitchInteractable).mode == SwitchInteractable.Mode.SET:
				(n as SwitchInteractable).set_on(true)
			elif n is SwitchInteractable and not (n as SwitchInteractable).is_on():
				(n as SwitchInteractable).set_on(true)
			elif n is DeviceToggleInteractable:
				(n as DeviceToggleInteractable).set_on(true)
		if _open_all and n is MovingPartInteractable:
			var m := n as MovingPartInteractable
			if not m.is_locked():
				m.snap_to(1.0)


static func _all_interactables(node: Node) -> Array[Interactable]:
	var out: Array[Interactable] = []
	for c in node.get_children():
		if c is Interactable:
			out.append(c)
		out.append_array(_all_interactables(c))
	return out
