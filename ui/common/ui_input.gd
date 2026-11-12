class_name UIInput
extends RefCounted
## Input helpers shared by the modal UI.
##
## The same physical press can mean "close this view" to the UI and "use the
## thing in front of me" to the player (E / LMB / pad A), or "back" to the UI
## and "crouch" to the player (pad B). So a modal never hands control back
## while one of those buttons is still held: it hides at once, but keeps its
## input lock until the buttons are released.

const GUARDED_ACTIONS: Array[StringName] = [&"interact", &"ui_back", &"pause", &"ui_accept", &"crouch"]


static func any_guarded_held() -> bool:
	for a: StringName in GUARDED_ACTIONS:
		if InputMap.has_action(a) and Input.is_action_pressed(a):
			return true
	return false


## Releases `owner`'s input lock once no guarded button is held (or after
## `timeout` seconds, so a stuck axis can never trap the player).
static func unlock_when_released(owner: Node, timeout: float = 1.5) -> void:
	if not is_instance_valid(owner) or not owner.is_inside_tree():
		Game.unlock_input(owner)
		return
	var tree := owner.get_tree()
	var deadline := Time.get_ticks_msec() + int(timeout * 1000.0)
	while any_guarded_held() and Time.get_ticks_msec() < deadline:
		await tree.process_frame
		if not is_instance_valid(owner):
			return
	# A modal may have reopened while we waited; it owns the lock again.
	if owner.has_method(&"is_open") and owner.call(&"is_open"):
		return
	Game.unlock_input(owner)


## Plays a UI sound if the Audio service has one (the stub returns null).
static func sound(id: StringName) -> void:
	if id != &"":
		Audio.play(id)
