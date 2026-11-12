# Horror Game (working title)

A first-person walking-and-touching horror foundation in Godot 4.7.

It is about 3:45 pm on a hot Saturday in August 1993. You are standing just
inside the front door of an aging house with a camcorder. Nobody is home.

There is no story yet, on purpose. This repository is the foundation: a person
in a house, alone, with light, sound and objects that answer when touched.

## Run it

1. Install [Godot 4.7](https://godotengine.org/download) (standard build, not .NET).
2. Open `project.godot` and press **F5**. The first open takes a minute while
   Godot imports textures and audio.

| Action | Keyboard / mouse | Gamepad |
|---|---|---|
| Move | W A S D | Left stick |
| Look | Mouse | Right stick |
| Interact | E or left click | A |
| Zoom (camcorder) | Hold right click | Left trigger |
| Hurry | Shift | Left stick click |
| Crouch | Ctrl or C | B |
| Pause / settings | Esc | Start |

The VHS look, date stamp, head bob, camera sway, field of view and volumes are
all adjustable in the pause menu.

## What is here

- **Design and contracts:** [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) —
  pillars, folder layout, how systems talk, naming, sound ids, materials.
- **Systems,** each with its own README where it has rules of its own:
  `player/`, `interaction/`, `ui/`, `atmosphere/`, `audio/`, `art/`,
  `fixtures/`, `props/`, `levels/`.
- **Sandboxes and tests:** `tests/<system>/`. Each system has a scene you can
  run on its own (F6) and a headless test.

## Checking a change

```sh
godot --headless --audio-driver Dummy --path . --import
godot --headless --audio-driver Dummy --path . --quit-after 120      # must print no errors
godot --headless --audio-driver Dummy --path . res://tests/player/test_player.tscn
godot --headless --audio-driver Dummy --path . -s res://tests/ui/test_ui.gd
godot --headless --audio-driver Dummy --path . -s res://tests/audio/test_audio.gd
godot --headless --audio-driver Dummy --path . -s res://tests/fixtures/test_fixtures.gd
godot --headless --audio-driver Dummy --path . -s res://tests/props/test_props.gd
godot --headless --audio-driver Dummy --path . -s res://tests/level/test_house.gd
```

Screenshot from the command line (needs a display or `xvfb-run`):

```sh
godot --path . --resolution 960x540 -s res://tools/capture.gd -- \
    --scene=res://main.tscn --out=_shots/view.png --wait=4 --pos=0,1.6,0 --look=2,1.2,2
```

## Generated content

All audio, textures and printed graphics are original and produced by scripts
committed in `tools/` (and the `_build/` folders next to generated scenes), so
any of it can be regenerated or replaced with real recordings and scans
without touching gameplay code. See `audio/README.md` and `art/README.md`.
