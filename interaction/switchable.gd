class_name Switchable
extends Node
## Something with an on/off state that switches and devices can drive:
## a light, a fan motor, a TV screen, an appliance bulb.
##
## Anything that toggles it (a wall SwitchInteractable, a lamp's own switch, a
## door's `lit_while_open`) goes through `set_on`, so several controls can
## share one target. Subclasses implement `_switched` for the visible effect.
## A Switchable can refuse to work (`is_working() == false`, e.g. a dead bulb):
## its state still follows the switch, nothing visible happens, and controls
## say `get_failure_line()`.

signal switched(on: bool)

@export var start_on: bool = false

var _on: bool = false
var _initialised: bool = false


func _ready() -> void:
	if not _initialised:
		_on = start_on
	_initialised = true
	_switched(_on, true)


func is_on() -> bool:
	return _on if _initialised else start_on


## Set the state. `instant` skips warm-up / spin-up (level setup, tests).
func set_on(on: bool, instant: bool = false) -> void:
	if _initialised and on == _on:
		return
	_on = on
	if not _initialised:
		# Before _ready: remember the state; _ready applies it.
		_initialised = true
		if not is_node_ready():
			return
	_switched(on, instant)
	switched.emit(on)


func toggle() -> void:
	set_on(not is_on())


## False when switching does nothing visible (dead bulb, unplugged).
func is_working() -> bool:
	return true


## Line a control says when it switches this on and nothing happens.
func get_failure_line() -> String:
	return ""


## Override: show the state. Called once from _ready with instant = true.
func _switched(_on_now: bool, _instant: bool) -> void:
	pass


## Finds the Switchable at `node` or among its direct children.
static func resolve(node: Node) -> Switchable:
	if node == null:
		return null
	if node is Switchable:
		return node
	for c in node.get_children():
		if c is Switchable:
			return c
	return null
