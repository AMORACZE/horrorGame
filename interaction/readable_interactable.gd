class_name ReadableInteractable
extends Interactable
## Something with words on it: a note, a label, a calendar page, a tape spine.
##
## Interacting emits `Events.document_requested(self)`; the UI's reader shows
## `title` and `body` styled by `style`.

## How the reader should dress the text.
enum Style { PAPER, HANDWRITTEN, TYPED, LABEL, PRINT }

@export var title: String = ""
@export_multiline var body: String = ""
@export var style: Style = Style.PAPER
## World flag set the first time this is read (optional). Lets later systems know.
@export var read_flag: StringName = &""
@export var open_sound: StringName = &"paper_rustle"


func _init() -> void:
	prompt = "Read"


func _interact(_interactor: Node) -> void:
	if read_flag != &"":
		Game.set_flag(read_flag, true)
	Events.document_requested.emit(self)
