extends Node
## Checks for tests/ui/test_ui.gd (see there). Runs as a node so it can use
## the autoloads by name.

const Fakes := preload("res://tests/ui/ui_fakes.gd")

var _failed: int = 0
var _passed: int = 0
var _events: Dictionary = {}
var _settings_backup: Dictionary = {}
var ui: UIRoot
var player: Node


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_run.call_deferred()


func check(label: String, ok: bool, detail: String = "") -> void:
	if ok:
		_passed += 1
		print("PASS  ", label)
	else:
		_failed += 1
		print("FAIL  ", label, ("   (" + detail + ")") if detail != "" else "")


func frames(n: int = 2) -> void:
	for i in n:
		await get_tree().process_frame


func seconds(t: float) -> void:
	await get_tree().create_timer(t, true).timeout


func key(code: Key, pressed: bool) -> void:
	var ev := InputEventKey.new()
	ev.physical_keycode = code
	ev.keycode = code
	ev.pressed = pressed
	Input.parse_input_event(ev)
	Input.flush_buffered_events()


func tap(code: Key) -> void:
	key(code, true)
	await frames(2)
	key(code, false)
	await frames(2)


func _count(sig: String) -> void:
	_events[sig] = int(_events.get(sig, 0)) + 1


func _run() -> void:
	await frames(1)
	_backup_settings()
	Events.examine_closed.connect(_count.bind("examine_closed"))
	Events.document_closed.connect(_count.bind("document_closed"))
	Events.pause_changed.connect(func(p: bool) -> void: _count("pause_%s" % p))

	var world := Node3D.new()
	get_tree().root.add_child(world)
	player = Node.new()
	get_tree().root.add_child(player)
	var door := Fakes.make_door(world)
	var phone := Fakes.make_examinable(world)
	var note := Fakes.make_readable(world, ReadableInteractable.Style.HANDWRITTEN)
	var manual := Fakes.make_readable(world, ReadableInteractable.Style.PRINT)

	ui = (load("res://ui/ui_root.tscn") as PackedScene).instantiate()
	get_tree().root.add_child(ui)
	await frames(3)

	# --- Structure ---------------------------------------------------------------
	check("ui_root is CanvasLayer 10", ui.layer == 10)
	check("pause menu is CanvasLayer 100", ui.pause_menu.layer == 100)
	check("pause menu processes while paused", ui.pause_menu.process_mode == Node.PROCESS_MODE_ALWAYS)
	check("fade layer sits between HUD and post-fx", ui.screen_fade.layer > 10 and ui.screen_fade.layer < 40)
	check("starts with nothing modal", not ui.is_modal_open() and not ui.pause_menu.is_open())

	# --- Fade --------------------------------------------------------------------
	Events.level_ready.emit(world)
	await frames(2)
	check("level_ready covers the screen first", ui.screen_fade.get_alpha() > 0.95)
	await seconds(3.2)
	check("arrival fade clears within ~3 s", not ui.screen_fade.is_covered(), "alpha=%.2f" % ui.screen_fade.get_alpha())
	await ui.screen_fade.fade_out(0.1)
	check("fade_out API covers", ui.screen_fade.get_alpha() > 0.99)
	await ui.screen_fade.fade_in(0.1)
	check("fade_in API clears", not ui.screen_fade.is_covered())

	# --- HUD -----------------------------------------------------------------------
	InputGlyphs.current.set_gamepad(false)
	check("no prompt without focus", not ui.hud.is_prompt_shown())
	Events.interaction_focus_changed.emit(door)
	await frames(2)
	check("prompt shown on focus", ui.hud.is_prompt_shown())
	check("prompt text (keyboard)", ui.hud.get_prompt_text() == "E  Open  ·  Front door", ui.hud.get_prompt_text())
	door.interact(player)
	await frames(2)
	check("prompt refreshes on interacted (Open -> Close)", ui.hud.get_prompt_text() == "E  Close  ·  Front door", ui.hud.get_prompt_text())
	InputGlyphs.current.set_gamepad(true)
	await frames(1)
	check("glyph follows gamepad", ui.hud.get_prompt_text() == "A  Close  ·  Front door", ui.hud.get_prompt_text())
	# A real pad event switches back and forth too.
	var kev := InputEventKey.new()
	kev.physical_keycode = KEY_W
	kev.pressed = true
	Input.parse_input_event(kev)
	Input.flush_buffered_events()
	kev = kev.duplicate()
	kev.pressed = false
	Input.parse_input_event(kev)
	Input.flush_buffered_events()
	await frames(1)
	check("keyboard press switches glyphs back", ui.hud.get_prompt_text().begins_with("E  "), ui.hud.get_prompt_text())
	Events.interaction_focus_changed.emit(null)
	await frames(2)
	check("prompt cleared on focus null", not ui.hud.is_prompt_shown())
	Events.interaction_focus_changed.emit(door)
	await frames(1)

	# --- Observation -----------------------------------------------------------------
	Events.observation_requested.emit("It's locked.")
	await frames(2)
	check("observation shows", ui.observation_line.is_showing() and ui.observation_line.get_current_text() == "It's locked.")
	check("observation does not lock input", not Game.is_input_locked())
	Events.observation_requested.emit("Dust on the glass.")
	await frames(1)
	check("second observation queues", ui.observation_line.get_queue().size() == 1)
	await seconds(1.6)
	check("queued observation follows promptly", ui.observation_line.get_current_text() == "Dust on the glass.", ui.observation_line.get_current_text())
	ui.observation_line.clear()

	# --- Examine -----------------------------------------------------------------------
	phone.interact(player)
	await frames(2)
	check("examine opens on examine_requested", ui.examine_view.is_open() and ui.examine_view.visible)
	check("examine takes the input lock", Game.is_input_locked())
	check("HUD hidden while modal", not ui.hud.visible)
	check("examine shows a visual copy", ui.examine_view.get_visual() != null and ui.examine_view.get_visual().get_child_count() > 0)
	check("examine shows display name", ui.examine_view.get_title_text() == "Cordless phone")
	# The press that opened it must not close it: E held right now, then released.
	key(KEY_E, true)
	await frames(3)
	check("opening press cannot close examine", ui.examine_view.is_open())
	key(KEY_E, false)
	await seconds(0.3)
	check("examine arms after release", ui.examine_view.is_armed())
	key(KEY_E, true)
	await frames(2)
	check("interact closes examine", not ui.examine_view.is_open())
	check("examine_closed emitted", int(_events.get("examine_closed", 0)) == 1)
	check("lock kept while E still held", Game.is_input_locked())
	key(KEY_E, false)
	await frames(3)
	check("lock released after close", not Game.is_input_locked())
	await seconds(0.3)
	check("examine hidden after fade", not ui.examine_view.visible and ui.examine_view.get_visual() == null)
	check("HUD back after modal", ui.hud.visible)

	# --- Reader + Escape does not open pause ------------------------------------------
	note.interact(player)
	await frames(2)
	check("reader opens on document_requested", ui.document_reader.is_open() and ui.document_reader.visible)
	check("reader takes the input lock", Game.is_input_locked())
	check("reader shows title/body", ui.document_reader.get_title_text() == "Grocery list" and ui.document_reader.get_body_text().begins_with("milk"))
	check("reader style applied", ui.document_reader.get_style() == ReadableInteractable.Style.HANDWRITTEN)
	await tap(KEY_ESCAPE)
	check("Escape closes the reader", not ui.document_reader.is_open())
	check("document_closed emitted", int(_events.get("document_closed", 0)) == 1)
	check("same Escape did not open pause", not ui.pause_menu.is_open() and not get_tree().paused)
	await frames(2)
	check("lock released after reader", not Game.is_input_locked())

	manual.interact(player)
	await frames(4)
	check("long document can scroll", ui.document_reader.is_scrollable())
	await seconds(0.3)
	await tap(KEY_E)
	check("interact closes the reader", not ui.document_reader.is_open())
	await frames(2)

	# --- Pause ---------------------------------------------------------------------------
	await tap(KEY_ESCAPE)
	check("Escape opens pause when nothing is open", ui.pause_menu.is_open())
	check("pause sets tree paused", get_tree().paused)
	check("pause takes the input lock", Game.is_input_locked())
	check("pause_changed(true) emitted", int(_events.get("pause_true", 0)) == 1)
	check("HUD hidden while paused", not ui.hud.visible)
	var focus := get_viewport().gui_get_focus_owner()
	check("pause menu has visible keyboard focus", focus != null and focus.name == "Resume", str(focus))

	# Keyboard navigation reaches Settings.
	await tap(KEY_DOWN)
	focus = get_viewport().gui_get_focus_owner()
	check("down arrow moves focus", focus != null and focus.name == "SettingsButton", str(focus))
	await tap(KEY_ENTER)
	check("Enter opens Settings page", ui.pause_menu.get_page() == PauseMenu.Page.SETTINGS)
	var total_keys := 0
	for s: StringName in Settings.DEFAULTS:
		total_keys += (Settings.DEFAULTS[s] as Dictionary).size()
	check("every Settings key has a row", ui.pause_menu.get_rows().size() == total_keys,
		"%d rows / %d keys" % [ui.pause_menu.get_rows().size(), total_keys])
	var row := ui.pause_menu.find_row(&"audio", &"master")
	row.get_slider().value = 0.4
	check("slider writes through Settings", is_equal_approx(float(Settings.get_value(&"audio", &"master")), 0.4))
	check("slider readout updates", row.get_value_text() == "40%", row.get_value_text())
	var inv := ui.pause_menu.find_row(&"controls", &"invert_y")
	var before := bool(Settings.get_value(&"controls", &"invert_y"))
	inv.get_toggle().grab_focus()
	await tap(KEY_ENTER)
	check("toggle writes through Settings", bool(Settings.get_value(&"controls", &"invert_y")) == not before)
	var fov := ui.pause_menu.find_row(&"video", &"fov")
	fov.get_slider().grab_focus()
	var fov_before := float(Settings.get_value(&"video", &"fov"))
	await tap(KEY_RIGHT)
	check("right arrow adjusts focused slider", float(Settings.get_value(&"video", &"fov")) > fov_before)
	Settings.set_value(&"audio", &"master", 0.7)
	await frames(1)
	check("row follows external setting change", row.get_value_text() == "70%", row.get_value_text())
	await tap(KEY_ESCAPE)
	check("Escape backs out of Settings first", ui.pause_menu.is_open() and ui.pause_menu.get_page() == PauseMenu.Page.MAIN)
	await tap(KEY_ESCAPE)
	check("Escape resumes", not ui.pause_menu.is_open() and not get_tree().paused)
	check("pause_changed(false) emitted", int(_events.get("pause_false", 0)) == 1)
	await frames(2)
	check("lock released after resume", not Game.is_input_locked())

	# Pause key ignored? No: Start/Escape while a modal is open closes the modal only.
	phone.interact(player)
	await frames(2)
	await tap(KEY_ESCAPE)
	check("Escape closes examine without pausing", not ui.examine_view.is_open() and not ui.pause_menu.is_open() and not get_tree().paused)
	await frames(2)

	_restore_settings()
	ui.queue_free()
	await frames(2)
	print("\n%d passed, %d failed" % [_passed, _failed])
	get_tree().quit(1 if _failed > 0 else 0)


func _backup_settings() -> void:
	for s: StringName in Settings.DEFAULTS:
		for k: StringName in Settings.DEFAULTS[s]:
			_settings_backup[[s, k]] = Settings.get_value(s, k)


func _restore_settings() -> void:
	for sk: Array in _settings_backup:
		Settings.set_value(sk[0], sk[1], _settings_backup[sk], false)
	Settings.save()
