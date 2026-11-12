extends Node
## Global signal bus (autoload: `Events`).
##
## Systems talk to each other through these signals instead of holding references
## to one another. Emit from wherever the thing happens; connect from whoever cares.
## Keep this file declarative: signals only, no state, no logic.

# --- Interaction -------------------------------------------------------------

## The interactable under the player's reticle changed. `interactable` is null when nothing is focused.
@warning_ignore("unused_signal")
signal interaction_focus_changed(interactable: Interactable)

## An interaction succeeded.
@warning_ignore("unused_signal")
signal interacted(interactable: Interactable, interactor: Node)

## Show a short first-person observation line ("It's locked.", "Still warm.").
@warning_ignore("unused_signal")
signal observation_requested(text: String)

## Open the close-up examine view for an object.
@warning_ignore("unused_signal")
signal examine_requested(examinable: ExaminableInteractable)
@warning_ignore("unused_signal")
signal examine_closed

## Open the document reader for a note / label / page.
@warning_ignore("unused_signal")
signal document_requested(readable: ReadableInteractable)
@warning_ignore("unused_signal")
signal document_closed

# --- Player ------------------------------------------------------------------

## One footfall. `surface` is a surface id (see docs/ARCHITECTURE.md), `intensity` 0..1 (crouch ≈ 0.4, walk ≈ 0.7, hurry = 1).
@warning_ignore("unused_signal")
signal player_footstep(surface: StringName, position: Vector3, intensity: float)

## Player landed after being airborne (stairs, ledges). `impact` 0..1.
@warning_ignore("unused_signal")
signal player_landed(surface: StringName, position: Vector3, impact: float)

## Camcorder zoom changed. `amount` 0 (wide) .. 1 (full tele).
@warning_ignore("unused_signal")
signal camera_zoom_changed(amount: float)

# --- Game flow / UI ----------------------------------------------------------

## Player input was locked or released (modal UI, cutscene). Mirrors Game.is_input_locked().
@warning_ignore("unused_signal")
signal input_lock_changed(locked: bool)

@warning_ignore("unused_signal")
signal pause_changed(paused: bool)

## A persistent world flag changed (Game.set_flag).
@warning_ignore("unused_signal")
signal flag_changed(flag: StringName, value: Variant)

## A level finished loading and the player has been placed.
@warning_ignore("unused_signal")
signal level_ready(level: Node)

# --- Settings ----------------------------------------------------------------

## A setting changed (Settings.set_value). Listen and apply; never poll.
@warning_ignore("unused_signal")
signal setting_changed(section: StringName, key: StringName, value: Variant)
