# Audio

Everything you hear is addressed by **id** (`Audio.play(&"door_close")`), never by
path. The ids are listed in `docs/ARCHITECTURE.md` section 8. All current content
is synthesised by `tools/gen_audio.py`; any id can be replaced by a real
recording without touching code.

```
audio/
  default_bus_layout.tres    buses + effects (Master <- World <- SFX, Footsteps; Master <- Ambience; Master <- UI)
  sound_library.gd           id -> volume, pitch/volume jitter, loop flag, bus, 3D distances
  sounds/<id>/*.wav|ogg      one folder per id; every file in it is a variant
  ambient_emitter.tscn       looping positional source (fridge, clock, fly)
  ambience_bed.tscn          non-positional stereo beds (room tone + outside)
  random_oneshot_emitter.tscn  house settling / distant dog, car, mower at random
  reverb_zone.tscn           Area3D that sets the room reverb while the player is inside
core/audio_manager.gd        the `Audio` autoload
tools/gen_audio.py           generator (+ tools/audio_gen/*.py DSP and sound models)
tests/audio/analyze.py       objective checks: loudness, peaks, DC, loop seams, spectrograms
tests/audio/test_audio.gd    headless engine test
tests/audio/audio_sandbox.tscn  audition every id and helper
```

## Regenerate

```sh
pip install numpy scipy matplotlib        # matplotlib only for --png
python3 tools/gen_audio.py                 # all ids (~15 s on 3 cores), then analysis
python3 tools/gen_audio.py door_close fly_buzz   # just some ids
python3 tools/gen_audio.py --list          # registry: variants, loop, format, loudness target
godot --headless --audio-driver Dummy --path . --import
godot --headless --audio-driver Dummy --path . -s res://tests/audio/test_audio.gd
```

Output is deterministic (seeded per `id:variant`, bit-exact OGG muxing), so a
regenerate with no code change produces no git diff. ffmpeg with libvorbis is
needed for the `.ogg` files.

`python3 tests/audio/analyze.py [folders] [--png DIR]` prints per file: duration,
channels, peak, LUFS-ish integrated and momentary-max loudness, spectral
centroid and, for loops, the seam discontinuity (`seamJ` = jump at the seam /
99th-percentile sample step; `seamF` = high-frequency energy across the seam /
95th percentile elsewhere; both are about 1 or below for a clean loop). It exits
non-zero on clipping, DC offset, clicks at one-shot edges or a bad seam. OGGs
are decoded exactly as encoded, so seams are checked after the codec.

## How the sounds are made

No samples. Physical-ish models in numpy/scipy:

- **Impacts** (footsteps, doors, drawers, switches, putdown): a Hertzian contact
  pulse whose width sets hardness drives a bank of modal resonators (floor joists
  and boards, a hollow-core door, a cabinet panel, tile, plastic, small metal
  parts), plus a short noise transient for the contact itself and a low
  "weight" pulse. Every variant re-rolls mode frequencies, contact widths and
  timings: heel then toe, latch then frame rattle.
- **Friction**: stick-slip pulse trains through resonators for hinge creaks,
  faucet squeal, a shoe squeak on linoleum and wooden drawer judder; granular
  band-passed noise for sliding, cloth and paper (plus sparse crackle for
  fibres, grit and sticky linoleum).
- **Glass and bells**: high-Q inharmonic partials with doublets (beating).
- **Hums**: mains-locked tones (120 Hz magnetostriction, 57.5 Hz motor slip with
  wander, harmonics) plus mechanical noise modulated at the rotation rate and a
  loose-panel rattle that only fires when the vibration peaks (fridge);
  ballast buzz; CRT field buzz and 15.7 kHz flyback whine.
- **Fly**: wingbeat oscillator (~190-240 Hz, ~25 harmonics) with erratic pitch,
  distance and orientation; cruising flights, short bursts against the pane
  with glass ticks, silent landings.
- **Water**: Minnaert bubbles (van den Doel model) over turbulent splash noise.
- **Outside**: dog-day cicada songs (tymbal pulse trains), a constant insect
  drone, distant birds, a mourning dove, a crow, a far road and a mower, through
  a suburban outdoor response (slap echoes off houses) and then a closed
  single-pane window.
- **Rooms**: synthetic small-room impulse responses (image-source early
  reflections + frequency-dependent diffuse tail) convolved lightly into every
  one-shot; the World bus adds the rest.

Loops are built only from periodic material (FFT-shaped noise, integer-cycle
tones and LFOs, circular filtering/convolution, events placed with wrap-around),
so they are seamless by construction; the analyser verifies every seam.

## Formats and loudness

| Kind | Format | Target (file) |
|---|---|---|
| One-shots | WAV 16-bit 44.1 kHz mono | momentary-max (400 ms) LUFS-ish, per id, -16 (door slam) .. -30 (UI tick) |
| Long one-shots (>3 s) | OGG Vorbis q5 mono | -26 .. -27 momentary-max |
| Hum loops (8-15 s) | WAV 16-bit mono with `smpl` loop chunk | -24 .. -30 integrated |
| Ambience beds (40-60 s) | OGG Vorbis q5 stereo, `loop=true` in `.import` | -26 .. -30 integrated |

All files: peak <= -1 dBFS (one-shots pass a 1.5 ms look-ahead limiter, at most
6 dB of reduction, then a hard cap), no DC, edges faded, TPDF dither. The
per-id targets are in `SPECS` in `tools/gen_audio.py`. Files carry *natural
relative loudness* (a switch is quieter than a slammed door); the final mix
level of each id is `volume_db` in `audio/sound_library.gd` (beds and the
camcorder layer are turned well down there: room tone plays at -16 dB, tape hiss
at -22 dB).

## Replacing a sound with a recording (drop-in)

1. Put your file(s) in `audio/sounds/<id>/` (any names; `.wav`, `.ogg` or
   `.mp3`). Every audio file in the folder is a variant.
2. Delete the generated `<id>_NN.*` files in that folder (the generator only
   ever deletes/rewrites files with that prefix, so your files survive a
   regenerate; remove the id from `SPECS` in `tools/gen_audio.py` if you want
   it to stop producing them at all).
3. Mono for anything positional; stereo only for the three beds. 44.1 or 48 kHz.
   Match the file loudness of the generated version (`analyze.py` prints it) so
   the mix level in `sound_library.gd` still holds, or adjust `volume_db` there.
4. Re-import (open the editor, or `godot --headless --path . --import`).
   Looping is forced on load from the library's `loop` flag, so a loop works
   even if its import settings are wrong; seams are your recording's job
   (check with `analyze.py`).
5. Run `tests/audio/test_audio.gd`.

## Using it from code

```gdscript
Audio.play_attached(&"door_open", self)                 # follows the door
Audio.play_at(&"putdown", global_position, -3.0)        # extra dB, pitch
Audio.play(&"ui_tick")                                  # UI bus, plays while paused
var s := Audio.get_stream(&"fridge_hum")                # for your own looping player
Audio.configure_player_3d(my_player, &"fridge_hum")     # library bus + distances
```

Footsteps are automatic: emit `Events.player_footstep(surface, pos, intensity)`
(crouch ~0.4, walk ~0.7, hurry 1.0; level and pitch scale with it) and
`Events.player_landed(surface, pos, impact)`. Surfaces: wood, carpet, linoleum,
tile, concrete, rug (= carpet, softer). Unknown surfaces fall back to wood with
one warning.

The `Audio` autoload also runs the **camcorder layer** (very quiet tape hiss +
transport motor, non-positional, as if picked up by the camcorder's own mic) and
plays the **zoom motor** whenever `Events.camera_zoom_changed` keeps firing
(spins down ~0.1 s after the last change). `Audio.camcorder_layer_enabled`
turns the layer off. Bus volumes follow `Settings` `audio/master|world|ambience|ui`.

## Placement guide for the level builder

- **One `ambience_bed.tscn` per level**: defaults `room_tone` + `outside_afternoon`.
  Add `wind_light` only for rooms with an open window. Use `volumes_db` to
  lower `outside_afternoon` by ~4-6 dB for interior rooms with no windows.
- **`reverb_zone.tscn` in every room** (Area3D, layer 5). Set `preset`
  (LIVING_ROOM, BEDROOM, KITCHEN, BATHROOM, HALLWAY, CLOSET, GARAGE, BASEMENT,
  STAIRWELL, CUSTOM) and `size` to the room's interior. Default with no zone is
  a furnished living room.
- **`ambient_emitter.tscn`** at the physical source:
  - `fridge_hum`: at the bottom-back of the fridge (kick plate), ~0.3 m high.
  - `clock_tick`: on the clock face. One clock per house is plenty.
  - `fly_buzz`: on the inside of one sunny window pane, ~1.3-1.6 m high. One fly.
  - `light_buzz`: on a kitchen/garage fluorescent fixture, only while it is on
    (call `start(0.3)` / `stop(0.2)` from the switch).
  - `tv_static`, `faucet_run`, `phone_dial_tone`: owned by their fixtures; start
    and stop them from the fixture (`start(fade)`, `stop(fade)`).
  - Leave `pitch_drift` at 0 for anything mains-locked (fridge, ballast, TV);
    0.005-0.01 suits a fly or a fan.
- **`random_oneshot_emitter.tscn`**:
  - `house_settle`: one per floor, box covering the floor, gaps 20-90 s,
    volume -8..-2 dB. It is the house ticking as it heats: keep it sparse.
  - Outside life: one emitter 25-60 m outside the house (SPHERE, radius 20-30)
    with `distant_dog`, `distant_car`, `distant_mower`, gaps 40-150 s. These are
    already filtered as if heard through a closed wall, so do not put them inside.
  - Never use these for scares. No stingers anywhere.
- Interaction sounds: fixtures should prefer `play_attached` (the sound follows
  a swinging door) and `play_at` for things that stay put.
