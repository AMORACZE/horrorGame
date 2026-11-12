extends Node
## Sound playback service (autoload: `Audio`).
##
## PHASE-0 STUB: this file fixes the public API that every other system codes
## against. The audio pass replaces the bodies; the signatures must not change.
##
## Sounds are addressed by id (StringName), never by file path, so content can be
## re-recorded or swapped without touching gameplay code. The id list lives in
## docs/ARCHITECTURE.md. Unknown ids must warn once and return null, never crash.


## Play a non-positional sound (UI, camcorder, player-internal). Returns the player or null.
func play(_id: StringName, _volume_db: float = 0.0, _pitch: float = 1.0) -> AudioStreamPlayer:
	return null


## Play a one-shot at a world position. Returns the player or null.
func play_at(_id: StringName, _position: Vector3, _volume_db: float = 0.0, _pitch: float = 1.0) -> AudioStreamPlayer3D:
	return null


## Play a one-shot that follows a node (door, drawer). Freed with the node.
func play_attached(_id: StringName, _node: Node3D, _volume_db: float = 0.0, _pitch: float = 1.0) -> AudioStreamPlayer3D:
	return null


## Play a footstep for a surface id. Normally driven by Events.player_footstep.
func play_footstep(_surface: StringName, _position: Vector3, _intensity: float = 1.0) -> void:
	pass


## Get the stream for an id (for looping emitters that own their own player). Null if unknown.
func get_stream(_id: StringName) -> AudioStream:
	return null


func has_sound(_id: StringName) -> bool:
	return false
