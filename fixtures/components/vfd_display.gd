class_name VfdDisplay
extends Switchable
## A VCR's fluorescent display. Off (standby): the clock that was never set,
## blinking 12:00. On: the tuner channel, steady.

@export var label: NodePath
@export var standby_text: String = "12:00"
@export var on_text: String = "CH 03"
@export_range(0.1, 4.0, 0.05, "suffix:s") var blink_period: float = 1.0
@export var color: Color = Color(0.45, 1.0, 0.86)

var _label: Label3D = null
var _t: float = 0.0


func _ready() -> void:
	_label = get_node_or_null(label) as Label3D
	if _label:
		_label.modulate = color
	super._ready()
	set_process(true)


func _switched(on_now: bool, _instant: bool) -> void:
	if _label:
		_label.text = on_text if on_now else standby_text
		_label.visible = true
	_t = 0.0


## Whether the digits are lit this instant (they blink in standby).
func is_showing() -> bool:
	return _label != null and _label.visible


func _process(delta: float) -> void:
	if _label == null or _on:
		return
	_t = fmod(_t + delta, blink_period)
	_label.visible = _t < blink_period * 0.5
