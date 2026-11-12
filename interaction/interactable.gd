class_name Interactable
extends Node
## Makes a physics body something the player can look at and use.
##
## Usage: add this node (or a subclass) as a CHILD of a CollisionObject3D
## (StaticBody3D, AnimatableBody3D, RigidBody3D, Area3D) and put that body on
## physics layer 3 ("interactable"). The player's reticle ray finds the body and
## resolves the component with `Interactable.find_for(collider)`.
##
## The base class is already useful on its own: it shows a prompt and, when used,
## prints its `observations` one after another. That is the default way every
## object in the house "answers" the player. Subclasses override `_interact`
## (and optionally `get_prompt` / `can_interact`) for real behaviour.

signal interacted(interactor: Node)
signal focus_entered(interactor: Node)
signal focus_exited(interactor: Node)

## Name shown next to the prompt ("Telephone"). Empty = prompt only.
@export var display_name: String = ""
## Verb shown in the HUD ("Look", "Open", "Turn on").
@export var prompt: String = "Look"
## Disabled interactables are ignored by the reticle entirely.
@export var enabled: bool = true
## First-person lines shown when used. Each use advances to the next; the last one repeats.
@export var observations: Array[String] = []

var _observation_index: int = 0


func get_prompt() -> String:
	return prompt


func get_display_name() -> String:
	return display_name


## The physics body this component is attached to.
func get_body() -> CollisionObject3D:
	return get_parent() as CollisionObject3D


## Where prompts / sounds should be anchored in the world.
func get_focus_position() -> Vector3:
	var body := get_parent() as Node3D
	return body.global_position if body else Vector3.ZERO


func can_interact(_interactor: Node) -> bool:
	return enabled


## Called by the player. Do not override; override `_interact`.
func interact(interactor: Node) -> void:
	if not can_interact(interactor):
		return
	_interact(interactor)
	interacted.emit(interactor)
	Events.interacted.emit(self, interactor)


## Called by the player when the reticle enters / leaves this object.
func focus(interactor: Node) -> void:
	focus_entered.emit(interactor)


func unfocus(interactor: Node) -> void:
	focus_exited.emit(interactor)


## Override in subclasses. Default: say the next observation.
func _interact(_interactor: Node) -> void:
	say_next_observation()


## Emits the next observation line, if any. Returns true if something was said.
func say_next_observation() -> bool:
	if observations.is_empty():
		return false
	var line := observations[min(_observation_index, observations.size() - 1)]
	_observation_index = min(_observation_index + 1, observations.size() - 1)
	if line.strip_edges() != "":
		Events.observation_requested.emit(line)
	return true


## Convenience for subclasses: say one specific line.
func say(line: String) -> void:
	Events.observation_requested.emit(line)


## Resolve the Interactable for a collider returned by a ray/shape query.
## Looks at the collider's children first, then up to three ancestors, so a
## compound prop (cabinet body + door bodies) can share or override components.
static func find_for(collider: Object) -> Interactable:
	var node := collider as Node
	var depth := 0
	while node != null and depth < 4:
		for child in node.get_children():
			if child is Interactable and (child as Interactable).enabled:
				return child
		node = node.get_parent()
		depth += 1
	return null
