extends Node
## UI sandbox: the real ui_root.tscn over a bright backdrop, driven by fake
## interactables through the Events bus, exactly as the game would.
##
## Keys (also on-screen buttons):
##   1 focus door   2 use focused   3 clear focus   4 observation line
##   5 examine      6-0 documents (paper, handwritten, typed, label, print)
##   G toggle gamepad glyphs   F fade out+in   Esc pause / close
##
## Screenshot states: pass `-- --state=<name>` (hud, observation, examine,
## paper, handwritten, typed, label, print, pause, settings, fade).

const Fakes := preload("res://tests/ui/ui_fakes.gd")
const UI_SCENE := preload("res://ui/ui_root.tscn")

var ui: UIRoot
var door: Interactable
var phone: ExaminableInteractable
var readables: Array[ReadableInteractable] = []
var _line := 0
var _player := Node.new()


func _ready() -> void:
	Fakes.make_backdrop(self)
	var world := Node3D.new()
	world.name = "World"
	add_child(world)
	door = Fakes.make_door(world)
	phone = Fakes.make_examinable(world)
	for s in 5:
		readables.append(Fakes.make_readable(world, s))
	_player.name = "FakePlayer"
	add_child(_player)
	ui = UI_SCENE.instantiate()
	add_child(ui)
	_build_buttons()
	# Without a player, keep the cursor usable after a modal closes.
	Events.input_lock_changed.connect(func(_l: bool) -> void:
		(func() -> void: Input.mouse_mode = Input.MOUSE_MODE_VISIBLE).call_deferred())
	Events.level_ready.emit(self)
	var state := ""
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--state="):
			state = a.substr(8)
	if state != "":
		_buttons_layer.visible = false
		ui.screen_fade.set_covered(false)
		_apply_state.call_deferred(state)


func _apply_state(state: String) -> void:
	match state:
		"hud":
			Events.interaction_focus_changed.emit(door)
		"hud_pad":
			InputGlyphs.current.set_gamepad(true)
			Events.interaction_focus_changed.emit(door)
		"observation":
			Events.interaction_focus_changed.emit(door)
			Events.observation_requested.emit(Fakes.LINES[2])
		"examine":
			phone.interact(_player)
		"paper", "handwritten", "typed", "label", "print":
			var idx := ["paper", "handwritten", "typed", "label", "print"].find(state)
			readables[idx].interact(_player)
		"pause":
			ui.pause_menu.open()
		"settings":
			ui.pause_menu.open()
			ui.pause_menu.show_page(PauseMenu.Page.SETTINGS)
		"fade":
			ui.screen_fade.set_covered(true)
			ui.screen_fade.fade_in(3.0)


var _buttons_layer: CanvasLayer


func _build_buttons() -> void:
	_buttons_layer = CanvasLayer.new()
	_buttons_layer.layer = 5
	add_child(_buttons_layer)
	var box := VBoxContainer.new()
	box.position = Vector2(12, 12)
	_buttons_layer.add_child(box)
	var items := [
		["1  Focus door", _focus_door], ["2  Use focused", _use],
		["3  Clear focus", _clear_focus], ["4  Observation", _observe],
		["5  Examine phone", _examine], ["6  Paper", _read.bind(0)],
		["7  Handwritten", _read.bind(1)], ["8  Typed", _read.bind(2)],
		["9  Label", _read.bind(3)], ["0  Print", _read.bind(4)],
		["G  Gamepad glyphs", _toggle_pad], ["F  Fade", _fade],
	]
	for it: Array in items:
		var b := Button.new()
		b.text = it[0]
		b.focus_mode = Control.FOCUS_NONE
		b.add_theme_font_size_override(&"font_size", 13)
		b.pressed.connect(it[1])
		box.add_child(b)


func _unhandled_key_input(event: InputEvent) -> void:
	var k := event as InputEventKey
	if k == null or not k.pressed or k.echo or Game.is_input_locked():
		return
	match k.physical_keycode:
		KEY_1: _focus_door()
		KEY_2: _use()
		KEY_3: _clear_focus()
		KEY_4: _observe()
		KEY_5: _examine()
		KEY_6: _read(0)
		KEY_7: _read(1)
		KEY_8: _read(2)
		KEY_9: _read(3)
		KEY_0: _read(4)
		KEY_G: _toggle_pad()
		KEY_F: _fade()


func _focus_door() -> void:
	Events.interaction_focus_changed.emit(door)


func _use() -> void:
	if ui.hud.get_focused():
		ui.hud.get_focused().interact(_player)


func _clear_focus() -> void:
	Events.interaction_focus_changed.emit(null)


func _observe() -> void:
	Events.observation_requested.emit(Fakes.LINES[_line % Fakes.LINES.size()])
	_line += 1


func _examine() -> void:
	phone.interact(_player)


func _read(i: int) -> void:
	readables[i].interact(_player)


func _toggle_pad() -> void:
	InputGlyphs.current.set_gamepad(not InputGlyphs.using_gamepad)


func _fade() -> void:
	await ui.screen_fade.fade_out(0.8)
	await ui.screen_fade.fade_in(1.2)
