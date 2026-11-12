# Architecture

Godot 4.7 · Forward+ · GDScript · Jolt physics · 1 unit = 1 metre.

This document is the contract every system is built against. If code and this
file disagree, fix one of them in the same change.

## 1. What we are making (for now)

A first-person walking-and-touching game set in an aging American house on a
hot, bright afternoon in the summer of 1993. Nobody is home. Nothing jumps out.
The story is deliberately undecided; the foundation must not assume one.

### Pillars

1. **Daylight dread.** Sun through dusty glass, blown-out windows, hazy air.
   Nothing hides in the dark, so the wrongness has to come from stillness,
   framing and sound. Brightness is the mood, not a relief from it.
2. **A camcorder is watching.** The whole game is seen through a consumer VHS
   camcorder: soft image, chroma bleed, tape noise, auto-exposure that hunts,
   a date stamp, a zoom you can hear. Found footage, played live.
3. **Everything answers.** Every object can be looked at, and most can be
   opened, switched, read or picked up and turned over. An object with nothing
   to do still gets a one-line observation. No combat, no inventory puzzles yet.
4. **Three decades in layers.** The house was built in the early 70s (wood
   panelling, shag, harvest gold), refurnished in the 80s (florals, brass,
   oak-and-glass), and last lived in during the early 90s (beige plastic, VHS
   tapes, a cordless phone, a 1993 calendar). Rooms should show all three.
5. **Sound carries the house.** Room tone, a refrigerator, a clock, a fly at a
   window, a lawnmower two streets away. Footsteps change with the floor.
6. **Always playable.** Every change leaves `main.tscn` runnable and worth
   walking around in.

Tone references are inspirations only (late-90s psychological horror, found
footage). The setting, house, objects and text are original.

## 2. Layout

```
core/         autoloads: Events, Settings, Game, Audio
interaction/  Interactable base + behaviours (door, drawer, switch, ...)
player/       player.tscn: body, camcorder camera rig, reticle ray
ui/           ui_root.tscn: HUD prompt, observation line, examine view, reader, pause
atmosphere/   environment, sun rig, dust, VHS post-process (post_fx.tscn), OSD
audio/        bus layout, sound library, generated wav/ogg, ambient emitters
art/          materials/ (named palette), textures/ (generated)
fixtures/     things that DO something: door, lamp, switch, TV, cabinet, phone
props/        things that sit there: furniture, clutter, books, tapes
levels/       house/house.tscn (+ room sub-scenes)
tools/        capture.gd, gen_audio.py, gen_textures.py
tests/        per-system sandbox scenes; never referenced by the game
docs/         this file
main.tscn     game root: composes level + player + UI + post-fx
```

A scene and the script that drives it live side by side with the same base name.
Files and folders are `snake_case`; nodes are `PascalCase`; classes are
`PascalCase` with `class_name`.

## 3. Runtime composition

`main.tscn` (script `main.gd`) is the only place the pieces meet:

```
Main
├─ World            ← level instance, then the player placed at the spawn marker
├─ ui_root.tscn     CanvasLayer 10   HUD prompt, observation line, examine view, reader
│                   CanvasLayer 30   ScreenFade (inside ui_root; fades read as tape)
│                   CanvasLayer 100  pause menu (inside ui_root; drawn clean on top)
└─ post_fx.tscn     CanvasLayer 40   camcorder OSD (date stamp, counter, zoom bar)
                    CanvasLayer 50   VHS shader over everything below it
```

- The UI owns the `pause` and `ui_back` actions (`ui/ui_root.gd` is the single
  router). The player never handles them.
- Fades: `await ScreenFade.current.fade_out(t)` / `fade_in(t)` / `set_covered(bool)`.

- A level is a `Node3D` scene containing geometry, lights, its own
  `WorldEnvironment`/sun (by instancing an atmosphere rig), emitters and props,
  plus exactly one `Marker3D` in group `player_spawn`. Levels never instance the
  player, UI or post-fx.
- The player adds itself to group `player` and sets `Game.player`.
- Systems never fetch each other by node path. They use the `Events` bus, the
  autoload APIs below, or groups.

## 4. Autoloads

| Name | File | Role |
|---|---|---|
| `Events` | `core/events.gd` | Signal bus. Signals only. See the file for the full list. |
| `Settings` | `core/settings.gd` | `get_value(section, key)`, `set_value(...)`; emits `Events.setting_changed`; persists to `user://settings.cfg`. |
| `Game` | `core/game.gd` | World flags (`set_flag/get_flag/has_flag`), `Game.player`, input-lock stack (`lock_input(self)` / `unlock_input(self)` / `is_input_locked()`). |
| `Audio` | `core/audio_manager.gd` | `play(id)`, `play_at(id, pos)`, `play_attached(id, node)`, `play_footstep(surface, pos, intensity)`, `get_stream(id)`, `has_sound(id)`. |

`Audio` also offers `played(id, player)` (signal), `get_def(id)`,
`configure_player_3d(player, id)`, `enter_reverb_zone` / `exit_reverb_zone`
(used by `audio/reverb_zone.tscn`) and `stop_all_world()`.

The camcorder's on-screen clock is the game clock. It lives in group
`camcorder_clock` and answers `get_time_of_day_seconds()`; wall clocks follow it.

Rules:

- **Modal UI** (examine, reader, pause) calls `Game.lock_input(self)` when it
  opens and `Game.unlock_input(self)` when it closes. `Game` handles mouse
  capture. The player only checks `Game.is_input_locked()`.
- **Pausing** uses `get_tree().paused`. Gameplay nodes keep the default process
  mode; UI that must run while paused sets `PROCESS_MODE_ALWAYS`.
- **Settings** are applied by listening to `Events.setting_changed` and reading
  the initial value in `_ready`. Nobody polls.

## 5. Interaction

`Interactable` (`interaction/interactable.gd`) is a **component**: a plain
`Node` added as a child of a `CollisionObject3D` that sits on physics layer 3.
The player's reticle ray hits the body and resolves the component with
`Interactable.find_for(collider)`.

- Base `Interactable`: prompt + `observations` (lines that advance on each use).
  This alone satisfies "everything answers".
- `ExaminableInteractable`: emits `Events.examine_requested(self)`; the UI calls
  `create_examine_visual()` and shows the copy in an isolated viewport.
- `ReadableInteractable`: emits `Events.document_requested(self)`; has `title`,
  `body`, `style`.
- Behaviours in `interaction/` subclass `Interactable`:
  `MovingPartInteractable` (shared open/close motion, locks, flags, never
  pushes the player) with `HingedPartInteractable`, `SlidingPartInteractable`
  and `DoorInteractable` on top; `SwitchInteractable` driving `Switchable`
  components (`PoweredLight`, `FanMotor`, `FlickerLight`);
  `DeviceToggleInteractable` (TV, faucet, phone); `JammedInteractable`
  (things that only rattle). `LoopEmitter` owns a fixture's looping sound.

Player-side contract: reach 2.0 m from the camera; ray mask = layers 1 + 3 +
4 so walls occlude; on focus change call `unfocus/focus` and emit
`Events.interaction_focus_changed(interactable_or_null)`; on `interact` action
call `interactable.interact(player)`. The HUD reads `get_prompt()` and
`get_display_name()` from the focused component every time focus changes or an
interaction happens (prompts are dynamic: Open ↔ Close).

Observation text voice: first person, present tense, plain, short. It reports
what is there, not what it means. ("The receiver is warm." not "Something
terrible happened here.")

## 6. Physics layers

| Layer | Name | Who |
|---|---|---|
| 1 | world | walls, floors, static furniture |
| 2 | player | the player body |
| 3 | interactable | any body carrying an `Interactable` (usually also on 1 or 4 if solid) |
| 4 | physics_props | loose rigid bodies |
| 5 | triggers | Area3D volumes (reverb zones, surface zones) |

Player body: layer 2, mask 1 + 4.

## 7. Surfaces and footsteps

Walkable colliders carry metadata `surface` (StringName). The player reads it
from the floor collider (`get_meta(&"surface", &"wood")`, walking up parents
until found) and emits `Events.player_footstep(surface, position, intensity)`.
`Audio` listens and plays. Valid ids:

`wood` · `carpet` · `linoleum` · `tile` · `concrete` · `rug` (plays as carpet, softer)

## 8. Sound ids

Addressed by id, never by path. One-shots have several variants chosen at random.

- **Footsteps:** via `play_footstep`, per surface above.
- **Interaction:** `door_open` `door_close` `door_locked` `door_creak`
  `drawer_open` `drawer_close` `cabinet_open` `cabinet_close` `switch_on`
  `switch_off` `lamp_click` `button_press` `pickup` `putdown` `paper_rustle`
  `tv_on` `tv_off` `phone_pickup` `phone_hangup` `fridge_open` `fridge_close`
  `tape_insert` `glass_clink` `book_slide` `cloth_rustle` `thud_soft`
  `window_rattle` `faucet_squeak`
- **Loops:** `room_tone` `outside_afternoon` `wind_light` `fridge_hum`
  `clock_tick` `tv_static` `light_buzz` `fly_buzz` `phone_dial_tone`
  `faucet_run` `camcorder_motor` `camcorder_zoom` `tape_hiss`
- **Random ambient one-shots:** `house_settle` (wood ticking as it heats),
  `distant_dog` `distant_car` `distant_mower`
- **UI:** `ui_tick` `ui_open` `ui_close`

Buses: `Master` ← `World` ← (`SFX`, `Footsteps`), `Master` ← `Ambience`,
`Master` ← `UI`. Room reverb lives on `World`. Settings keys `audio/master`,
`audio/world`, `audio/ambience`, `audio/ui` map to those buses.

## 9. Materials

`art/materials/<name>.tres` is a fixed, named palette. Scenes reference these
files and never embed one-off materials for common surfaces, so the art pass can
upgrade the whole house by editing the palette. Run `ls art/materials` for the
list. New names may be added; existing names are never renamed.

Architecture dimensions: ceiling 2.44 m · interior door 0.81 × 2.03 m ·
interior wall 0.15 m thick · exterior wall 0.30 m · counter 0.91 m ·
table 0.74 m · seat 0.45 m · light switch at 1.2 m · player eye 1.6 m,
capsule radius 0.3 m, height 1.75 m.

## 10. Lighting and look

- Time of day: about 3:45 pm, late August. Sun low enough to rake across floors.
- One `DirectionalLight3D` sun with shadows, a procedural or panorama sky, SDFGI
  for bounce (no baking, so levels stay text-authorable), volumetric fog for
  shafts, SSAO, filmic/AgX tonemap, mild glow so windows bloom.
- Interiors are lit by the sun and by practical lamps the player can switch.
  No invisible fill lights unless a room is unreadable without one.
- The VHS pass is one full-screen shader on CanvasLayer 50, driven by
  `Settings` `video/vhs_enabled` and `video/vhs_intensity`. It must be
  comfortable for an hour of play at intensity 1.0.

## 11. Working rules

- GDScript with static types everywhere (`var x: int`, typed arrays, typed
  signals). No `get_node("../../..")` reaching across systems.
- Exported properties for anything a designer would tune; group them with
  `@export_group`.
- Each system keeps a sandbox scene in `tests/<system>/` that runs on its own.
- Check before committing:
  `godot --headless --path . --import` then
  `godot --headless --path . --quit-after 120` must print no errors, and a
  screenshot via `tools/capture.gd` should look right.
- Generated content (audio, textures) is produced by a script in `tools/` that
  is committed alongside its output, so anything can be regenerated or replaced.
