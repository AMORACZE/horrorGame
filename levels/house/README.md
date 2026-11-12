# House level: 1418 Wren Hollow Rd (ground floor slice)

`levels/house/house.tscn` is **generated** by `levels/house/_build/build_house.py`.
Hand edits to the scene are overwritten on the next build: change the data and
helpers in the builder instead.

```sh
python3 levels/house/_build/build_house.py           # writes house.tscn
godot --headless --audio-driver Dummy --path . --import
godot --headless --audio-driver Dummy --path . -s res://tests/level/test_house.gd
xvfb-run -a godot --audio-driver Dummy --path . --resolution 960x540 \
    -s res://tests/level/shots.gd                      # views -> _shots/level/*.png
```

`tests/level/shots.gd` plays through `main.tscn` (real player camera, UI and
post-process) and takes a default set of eye-height views; pass
`--shots="name@x,z@yaw,pitch;..."` for others. Committed reference frames are
in `tests/level/reference/`.

## Plan

North is up (-Z). Interior faces in metres; walls are drawn on their faces.
Ceiling 2.44 everywhere; floor at y = 0 on a 0.40 m foundation above the lawn.

```
 x: 0         1.0    2.27   3.83    4.67  5.53 6.0 6.15     7.87 8.73      10.35
z -0.80              +--------------+                      .            .
                     |  coat closet |   (bedroom wing)     .  basement  .   (mass)
z 0.0  +----[FRONT]--+==[sliding]===+----[BEDROOM]---+      .   (mass)   +--------+
       |(mirror)  S                        thermostat |                   | pantry |
       |  HALL  (oak strip, wood)          coat rack  [BASEMENT]          |shelves |
z 1.5  +---+=====  cased opening  =====+--[phone]-----+------+------------+[PANTRY]+--+
z 1.65 |   0.45                       2.95  shelf   boxes   | trash       ajar   fridge|
       |W                                                   | switch               (cal)|
       |W   end    +-------rug-------+                      [ cased  ]                 |
       |W   table  | coffee table    |           TV in oak  [ opening]  dinette        |
       |W  [SOFA]  |                 |         ent. centre  |    table + 4 chairs [BACK]|
       |W   end    +-----------------+   recliner           |                   (box)  |
       |   table  plant   stereo  mag rack                  |       base  sink  base   |
z 6.25 +------[S win]-----------------[S win]---------------+--[win]------[win]--------+
                1.6       (clock 3.0)  4.4                    7.0        8.975
```

| Room | Interior (W x D) | Floor (`surface`) | Walls |
|---|---|---|---|
| Entry hall | 6.00 x 1.50 (+ closet 1.60 x 0.65) | oak strip, `wood` | 80s stripe wallpaper |
| Living room | 6.00 x 4.60 | gold shag, `carpet` (rug: `rug`) | walnut panelling (east), floral paper (north), yellowed plaster (west, south) |
| Kitchen / dinette | 4.20 x 4.60 (+ pantry 0.90 x 0.55) | patterned sheet vinyl, `linoleum` | yellowed plaster |

Openings: hall -> living cased opening 2.50 wide (x 0.45..2.95), living ->
kitchen cased opening 1.40 wide (z 2.60..4.00), both 2.10 high. West wall:
three double-hung windows side by side (a picture-window group, 0.07 m
mullions) at z 3.43 / 4.40 / 5.37. South wall: living windows at x 1.6 and
4.4, dinette window at x 7.0, sink window at x 8.975 (sill raised to 0.95 to
clear the counter).

## What is locked, and why (in level terms)

The slice is the hall, living room and kitchen. Everything else is closed so
the playable space stays small and finished; nothing behind a locked door is
modelled (solid mass sits behind each one).

| Door | State | Level reason |
|---|---|---|
| Front door (north, hall) | locked | Bounds the slice; the player starts inside it. |
| Bedroom hall door (north, hall) | locked | Bedroom wing not built yet. |
| Basement door (east end of hall) | locked | Basement not built yet. |
| Back door (east, kitchen) | locked | Bounds the slice; its glass shows the side yard. |
| Coat closet (hall) | opens | Sliding doors, coats, a box on the shelf. |
| Pantry door (kitchen) | unlocked, starts **ajar** | The one door that is slightly open. |

Locked lines are plain ("It's locked.", "The knob turns a little and stops.").
The hall ceiling light has a dead bulb; every lamp starts off.

## Sound

All from `audio/` helpers, under `House/Audio`:

- `AmbienceBed` (room tone + outside afternoon), at the house centre.
- `reverb_zone` per room: hall HALLWAY, living LIVING_ROOM, kitchen KITCHEN,
  coat closet and pantry CLOSET.
- `Fly`: `fly_buzz` on the inside of the southern pane of the west window
  group (the sunniest glass), x -0.06, y 1.48.
- `HouseSettle`: `house_settle`, a box over the whole floor, 20-90 s gaps.
- `Neighbourhood`: `distant_dog` / `distant_car` / `distant_mower`, a 22 m
  sphere centred 45 m south-west of the house, 40-150 s gaps.
- The fridge hum and the sunburst clock tick come from those objects.

No wind (the windows are painted shut) and nothing that reads as an event.

## Outside

Brick shell with eaves and a low roof; lawn at grade; a low hedge and the
neighbour's concrete drive and stucco house to the west; a board fence, a
clothesline and the next house to the south; a tree south-west of the west
windows, placed so its leaf clusters break the sun on the southern pane of the
group into patches; a second tree out back; garbage cans by the back step.

## Next

- Bedroom wing and basement behind the locked doors, built the same way.
- Replace the box-built phone table, coats and pantry shelves with real props.
- A wall phone fixture for the kitchen; a kitchen faucet drip loop.
- Proper roof geometry (hip) and gutters if any view ever shows them.
- More 90s layer: a cordless phone base, a computer in the bedroom wing.
