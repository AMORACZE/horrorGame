class_name UIRoot
extends CanvasLayer
## Root of all game UI (CanvasLayer 10, instanced once by main.gd).
##
##   UIRoot (layer 10)
##   ├─ InputGlyphs        last-used device + glyph text
##   ├─ DisplaySettings    applies fullscreen / vsync
##   ├─ HUD                reticle + prompt
##   ├─ ExamineView        modal: object in hand
##   ├─ DocumentReader     modal: notes, labels, pages
##   ├─ ObservationLine    one-line thoughts (above the modals)
##   ├─ ScreenFade         CanvasLayer 30: fades, arrival on level_ready
##   └─ PauseMenu          CanvasLayer 100: pause + settings
##
## Everything is driven by Events / Settings / Game. This script only arbitrates
## the shared "back" keys: Escape is bound to both ui_back and pause, so one
## press must close the open modal OR back out of the pause menu OR open the
## pause menu, never two of those.

static var current: UIRoot = null

@onready var hud: HUD = $HUD
@onready var examine_view: ExamineView = $ExamineView
@onready var document_reader: DocumentReader = $DocumentReader
@onready var observation_line: ObservationLine = $ObservationLine
@onready var screen_fade: ScreenFade = $ScreenFade
@onready var pause_menu: PauseMenu = $PauseMenu


func _enter_tree() -> void:
	current = self


func _exit_tree() -> void:
	if current == self:
		current = null


func _ready() -> void:
	layer = 10
	# Needs to see the pause key while the tree is paused; children that should
	# freeze with the game set PROCESS_MODE_PAUSABLE themselves.
	process_mode = Node.PROCESS_MODE_ALWAYS


## True while the examine view or the reader is up.
func is_modal_open() -> bool:
	return examine_view.is_open() or document_reader.is_open()


func _input(event: InputEvent) -> void:
	if event.is_echo():
		return
	var back := event.is_action_pressed(&"ui_back")
	var pause := event.is_action_pressed(&"pause")
	if not (back or pause):
		return
	if pause_menu.is_open():
		pause_menu.handle_back()
	elif examine_view.is_open():
		examine_view.request_close()
	elif document_reader.is_open():
		document_reader.request_close()
	elif pause and not get_tree().paused:
		pause_menu.open()
	else:
		return
	get_viewport().set_input_as_handled()
