class_name InputGlyphs
extends Node
## Tracks whether the player last used keyboard/mouse or a gamepad, and turns
## input actions into short glyph strings ("E", "LMB", "A", "✕").
##
## One instance lives in ui_root.tscn. UI pieces read `InputGlyphs.using_gamepad`
## and connect to `InputGlyphs.current.device_changed` (see InputGlyph).

signal device_changed(gamepad: bool)

## The live instance (null until ui_root is in the tree).
static var current: InputGlyphs = null
## True when the most recent meaningful input came from a gamepad.
static var using_gamepad: bool = false

## Stick deflection that counts as "the player picked up the pad".
const AXIS_THRESHOLD := 0.45
## Mouse motion (pixels) that counts as "back on the mouse".
const MOUSE_THRESHOLD := 6.0


func _enter_tree() -> void:
	current = self
	process_mode = Node.PROCESS_MODE_ALWAYS


func _exit_tree() -> void:
	if current == self:
		current = null


func _input(event: InputEvent) -> void:
	var pad: Variant = null
	if event is InputEventJoypadButton:
		pad = true
	elif event is InputEventJoypadMotion:
		if absf((event as InputEventJoypadMotion).axis_value) > AXIS_THRESHOLD:
			pad = true
	elif event is InputEventKey or event is InputEventMouseButton:
		pad = false
	elif event is InputEventMouseMotion:
		if (event as InputEventMouseMotion).relative.length() > MOUSE_THRESHOLD:
			pad = false
	if pad != null:
		set_gamepad(pad)


func set_gamepad(pad: bool) -> void:
	if pad == using_gamepad:
		return
	using_gamepad = pad
	device_changed.emit(pad)


# --- Glyph text ----------------------------------------------------------------

## Short label for the first binding of `action` on the current device.
static func label_for(action: StringName, gamepad: bool = using_gamepad) -> String:
	if not InputMap.has_action(action):
		return "?"
	for ev: InputEvent in InputMap.action_get_events(action):
		if gamepad and (ev is InputEventJoypadButton or ev is InputEventJoypadMotion):
			return _pad_label(ev)
		if not gamepad and (ev is InputEventKey or ev is InputEventMouseButton):
			return _kbm_label(ev)
	return "?"


static func _kbm_label(ev: InputEvent) -> String:
	if ev is InputEventMouseButton:
		match (ev as InputEventMouseButton).button_index:
			MOUSE_BUTTON_LEFT: return "LMB"
			MOUSE_BUTTON_RIGHT: return "RMB"
			MOUSE_BUTTON_MIDDLE: return "MMB"
			MOUSE_BUTTON_WHEEL_UP, MOUSE_BUTTON_WHEEL_DOWN: return "Wheel"
		return "Mouse"
	var k := ev as InputEventKey
	var code: Key = k.keycode
	if code == KEY_NONE and k.physical_keycode != KEY_NONE:
		# Show what the key says on this keyboard layout (AZERTY "Z" for QWERTY "W").
		# The headless display server has no layout; fall back to the US key.
		if DisplayServer.get_name() != "headless":
			code = DisplayServer.keyboard_get_keycode_from_physical(k.physical_keycode)
		if code == KEY_NONE:
			code = k.physical_keycode
	match code:
		KEY_ESCAPE: return "Esc"
		KEY_SPACE: return "Space"
		KEY_ENTER, KEY_KP_ENTER: return "Enter"
		KEY_SHIFT: return "Shift"
		KEY_CTRL: return "Ctrl"
		KEY_TAB: return "Tab"
	return OS.get_keycode_string(code)


static func _is_sony() -> bool:
	var pads := Input.get_connected_joypads()
	if pads.is_empty():
		return false
	var n := Input.get_joy_name(pads[0]).to_lower()
	return n.contains("ps4") or n.contains("ps5") or n.contains("playstation") \
		or n.contains("dualshock") or n.contains("dualsense") or n.contains("sony")


static func _pad_label(ev: InputEvent) -> String:
	if ev is InputEventJoypadMotion:
		match (ev as InputEventJoypadMotion).axis:
			JOY_AXIS_LEFT_X, JOY_AXIS_LEFT_Y: return "L stick"
			JOY_AXIS_RIGHT_X, JOY_AXIS_RIGHT_Y: return "R stick"
			JOY_AXIS_TRIGGER_LEFT: return "L2" if _is_sony() else "LT"
			JOY_AXIS_TRIGGER_RIGHT: return "R2" if _is_sony() else "RT"
		return "Stick"
	var b := (ev as InputEventJoypadButton).button_index
	var sony := _is_sony()
	match b:
		JOY_BUTTON_A: return "✕" if sony else "A"
		JOY_BUTTON_B: return "○" if sony else "B"
		JOY_BUTTON_X: return "□" if sony else "X"
		JOY_BUTTON_Y: return "△" if sony else "Y"
		JOY_BUTTON_LEFT_SHOULDER: return "L1" if sony else "LB"
		JOY_BUTTON_RIGHT_SHOULDER: return "R1" if sony else "RB"
		JOY_BUTTON_BACK: return "Select" if sony else "Back"
		JOY_BUTTON_START: return "Options" if sony else "Start"
		JOY_BUTTON_LEFT_STICK: return "L3" if sony else "LS"
		JOY_BUTTON_RIGHT_STICK: return "R3" if sony else "RS"
		JOY_BUTTON_DPAD_UP: return "D-pad ↑"
		JOY_BUTTON_DPAD_DOWN: return "D-pad ↓"
		JOY_BUTTON_DPAD_LEFT: return "D-pad ←"
		JOY_BUTTON_DPAD_RIGHT: return "D-pad →"
	return "Btn %d" % b


## True for glyphs that read as a round face button rather than a key cap.
static func is_round_glyph(text: String) -> bool:
	return text.length() <= 1 and using_gamepad
