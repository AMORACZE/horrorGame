#!/usr/bin/env python3
"""Builds every prop scene under props/, the prop gallery and props/README.md.

    python3 props/_build/build_props.py

The emitted .tscn files are ordinary hand-editable scenes. This script is a
convenience for keeping sixty-odd scenes consistent; re-running it overwrites
hand edits to the generated scenes (the GDScript files are never touched).
Printed graphics come from tools/gen_prop_graphics.py.
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tscn import Scene, Raw, v3, col, mmul, euler, xform  # noqa: E402
from common import CATALOG, ROOT, write_prop_materials  # noqa: E402
import living  # noqa: E402
import media  # noqa: E402
import kitchen  # noqa: E402
import hallway  # noqa: E402


def look_basis(direction: tuple[float, float, float]) -> list[list[float]]:
    """Basis whose -Z points along direction (for a DirectionalLight3D)."""
    l = math.sqrt(sum(c * c for c in direction))
    z = [-c / l for c in direction]
    up = [0.0, 1.0, 0.0]
    x = [up[1] * z[2] - up[2] * z[1], up[2] * z[0] - up[0] * z[2], up[0] * z[1] - up[1] * z[0]]
    xl = math.sqrt(sum(c * c for c in x))
    x = [c / xl for c in x]
    y = [z[1] * x[2] - z[2] * x[1], z[2] * x[0] - z[0] * x[2], z[0] * x[1] - z[1] * x[0]]
    return [[x[0], y[0], z[0]], [x[1], y[1], z[1]], [x[2], y[2], z[2]]]


# --------------------------------------------------------------------------- gallery

def gallery() -> None:
    g = Scene("PropGallery", root_type="Node3D")
    g.nodes[0].props = []  # plain Node3D root, no physics props
    env = g.sub_res("ProceduralSkyMaterial", [
        ("sky_top_color", Raw(col((0.32, 0.5, 0.78)))), ("sky_horizon_color", Raw(col((0.78, 0.8, 0.8)))),
        ("ground_horizon_color", Raw(col((0.7, 0.66, 0.6)))), ("ground_bottom_color", Raw(col((0.3, 0.27, 0.22)))),
        ("sun_angle_max", 20.0)])
    sky = g.sub_res("Sky", [("sky_material", env)])
    environment = g.sub_res("Environment", [
        ("background_mode", 2), ("sky", sky), ("ambient_light_source", 3), ("ambient_light_energy", 0.45),
        ("reflected_light_source", 2), ("tonemap_mode", 2), ("tonemap_exposure", 0.75),
        ("ssao_enabled", True), ("glow_enabled", True), ("glow_intensity", 0.3)])
    g.add("WorldEnvironment", "WorldEnvironment", props=[("environment", environment)])
    sun_b = look_basis((0.18, -0.55, 0.82))
    g.add("Sun", "DirectionalLight3D", basis=sun_b, pos=(0, 6, 0), props=[
        ("light_color", Raw(col((1.0, 0.93, 0.8)))), ("light_energy", 1.6), ("shadow_enabled", True),
        ("directional_shadow_max_distance", 28.0)])

    # Room: floor, back wall with two window openings, side walls. No ceiling.
    room = g.add("Room", "StaticBody3D", props=[("collision_layer", 1), ("collision_mask", 0),
                                                 ("metadata/surface", Raw('&"wood"'))])
    X0, X1, ZB, ZF, WH, T = -9.5, 9.5, -6.0, 6.0, 2.44, 0.15
    g.box("Floor", (X1 - X0, 0.1, ZF - ZB + T), ((X0 + X1) / 2, -0.05, (ZB + ZF) / 2 - T / 2), "floor_hardwood",
          parent=room)
    g.col_box((X1 - X0, 0.1, ZF - ZB + T), ((X0 + X1) / 2, -0.05, (ZB + ZF) / 2 - T / 2), parent=room,
              name="FloorCollision")
    windows = [(-6.6, 0.9, 1.2, 0.9), (-3.6, 1.4, 1.45, 0.75)]  # (x, w, h, sill)
    # back wall pieces
    zc = ZB - T / 2
    segs = []
    cur = X0
    for x, w, h, sill in windows:
        segs.append((cur, x - w / 2, 0.0, WH))
        segs.append((x - w / 2, x + w / 2, 0.0, sill))
        segs.append((x - w / 2, x + w / 2, sill + h, WH))
        cur = x + w / 2
    segs.append((cur, X1, 0.0, WH))
    for a, b, y0, y1 in segs:
        g.box("BackWall", (b - a, y1 - y0, T), ((a + b) / 2, (y0 + y1) / 2, zc), "wall_plaster_cream", parent=room)
        g.col_box((b - a, y1 - y0, T), ((a + b) / 2, (y0 + y1) / 2, zc), parent=room, name="WallCollision")
    for x, w, h, sill in windows:
        g.box("Sill", (w + 0.1, 0.03, T + 0.06), (x, sill + 0.015, zc + 0.03), "trim_white", parent=room)
        g.box("Glass", (w, h, 0.006), (x, sill + h / 2, zc - 0.05), "glass_window", parent=room)
    for sx in (-1, 1):
        x = (X1 if sx > 0 else X0) + sx * T / 2
        g.box("SideWall", (T, WH, ZF - ZB), (x, WH / 2, (ZB + ZF) / 2), "wall_wood_paneling", parent=room)
        g.col_box((T, WH, ZF - ZB), (x, WH / 2, (ZB + ZF) / 2), parent=room, name="WallCollision")

    entries = {e.path: e for e in CATALOG}
    ext_ids: dict[str, Raw] = {}

    def inst(path: str, pos, rot=(0, 0, 0), label: str | None = None, label_pos=None, label_rot=(0, 0, 0),
             parent: str = ".", **props) -> str:
        if path not in ext_ids:
            ext_ids[path] = g.ext_res("PackedScene", "res://" + path)
        name = os.path.splitext(os.path.basename(path))[0]
        pname = "".join(p.capitalize() for p in name.split("_"))
        p = g.add(pname, None, parent=parent, pos=pos, rot=rot, instance=ext_ids[path],
                  props=list(props.items()))
        if label is not False:
            lp = label_pos if label_pos is not None else (pos[0], 0.06, pos[2] + 0.5)
            g.add("Label", "Label3D", pos=lp, rot=label_rot, props=[
                ("pixel_size", 0.0022), ("text", label or name), ("font_size", 36), ("outline_size", 8),
                ("modulate", Raw(col((0.1, 0.08, 0.06)))), ("outline_modulate", Raw(col((1, 1, 1, 0.8)))),
                ("double_sided", False)])
        return p

    def row(paths: list[str], z: float, y: float = 0.0, gap: float = 0.5, x_start: float | None = None,
            label_dz: float = 0.15, label_y: float = 0.06, stagger: bool = False, label_rot=(-35, 0, 0)) -> None:
        widths = [entries[p].scene.footprint()[0] for p in paths]
        total = sum(widths) + gap * (len(paths) - 1)
        x = -total / 2 if x_start is None else x_start
        for k, (p, w) in enumerate(zip(paths, widths)):
            e = entries[p]
            lo, hi = e.scene.bounds
            cx = x - lo[0]
            front = hi[2]
            ly = label_y + (0.05 if stagger and k % 2 else 0.0)
            inst(p, (cx, y, z), label_pos=(cx + (lo[0] + hi[0]) / 2, ly, z + front + label_dz), label_rot=label_rot)
            x += w + gap

    living_big = ["props/living/sofa_floral.tscn", "props/living/recliner_corduroy.tscn",
                  "props/living/entertainment_center_oak.tscn", "props/living/bookshelf.tscn",
                  "props/living/coffee_table_oak_glass.tscn", "props/living/end_table_oak.tscn",
                  "props/living/magazine_rack.tscn", "props/living/potted_plant_dry.tscn"]
    row(living_big, -3.9, gap=0.55)
    floor_misc = ["props/living/area_rug.tscn", "props/kitchen/dinette_table.tscn", "props/kitchen/dinette_chair.tscn",
                  "props/kitchen/trash_can.tscn", "props/hallway/coat_rack.tscn", "props/hallway/umbrella_stand.tscn",
                  "props/hallway/moving_box_closed.tscn", "props/hallway/moving_box_open.tscn",
                  "props/hallway/laundry_basket.tscn", "props/hallway/floor_fan.tscn",
                  "props/hallway/shoes_pair.tscn"]
    row(floor_misc, -1.2, gap=0.45)

    # Display plinths for small things
    small_media = [e.path for e in CATALOG if e.category == "media" and "calendar" not in e.path]
    small_kitchen = ["props/kitchen/mug.tscn", "props/kitchen/drinking_glass.tscn", "props/kitchen/plate.tscn",
                     "props/kitchen/ashtray_amber.tscn", "props/kitchen/cereal_box.tscn",
                     "props/kitchen/fruit_bowl.tscn", "props/kitchen/dish_rack.tscn",
                     "props/kitchen/percolator.tscn"]
    PH = 0.6
    for z, items, gap in ((1.0, small_media, 0.16), (2.6, small_kitchen, 0.3)):
        widths = [entries[p].scene.footprint()[0] for p in items]
        total = sum(widths) + gap * (len(items) - 1)
        pl = g.add("Plinth", "StaticBody3D", pos=(0, 0, z), props=[("collision_layer", 1), ("collision_mask", 0)])
        g.box("Top", (total + 0.4, PH, 0.75), (0, PH / 2, 0), "laminate_formica", parent=pl)
        g.col_box((total + 0.4, PH, 0.75), (0, PH / 2, 0), parent=pl)
        x = -total / 2
        for k, (p, w) in enumerate(zip(items, widths)):
            lo, hi = entries[p].scene.bounds
            cx = x - lo[0]
            inst(p, (cx, PH + 0.002, z - 0.1), label_pos=(cx + (lo[0] + hi[0]) / 2, PH - 0.12 - (k % 2) * 0.13,
                                                         z + 0.3751), label_rot=(0, 0, 0))
            x += w + gap

    # Wall items on the back wall, right of the windows
    wall_items = [("props/living/sunburst_clock.tscn", 1.75), ("props/living/framed_picture_lake.tscn", 1.55),
                  ("props/living/framed_picture_abstract.tscn", 1.5), ("props/living/framed_picture_barn.tscn", 1.55),
                  ("props/media/wall_calendar_aug_1993.tscn", 1.85), ("props/hallway/wall_mirror.tscn", 1.45),
                  ("props/hallway/key_hooks.tscn", 1.45), ("props/kitchen/paper_towel_holder.tscn", 1.3)]
    x = -1.2
    for p, y in wall_items:
        lo, hi = entries[p].scene.bounds
        cx = x - lo[0]
        inst(p, (cx, y, ZB), label_pos=(cx + (lo[0] + hi[0]) / 2, 0.7, ZB + 0.01), label_rot=(0, 0, 0))
        x += hi[0] - lo[0] + 0.45
    # Macrame from a little ceiling beam
    g.box("Beam", (0.6, 0.08, 0.1), (x + 0.3, 2.40, ZB + 0.5), "wood_dark", parent=room)
    inst("props/living/macrame_plant_hanger.tscn", (x + 0.3, 2.36, ZB + 0.5),
         label_pos=(x + 0.3, 0.7, ZB + 0.01), label_rot=(0, 0, 0))

    # Window dressing
    bx, bw, bh, bs = windows[0]
    inst("props/architecture/venetian_blinds.tscn", (bx, bs + bh, ZB - T + 0.01), label_pos=(bx, 0.6, ZB + 0.01),
         label_rot=(0, 0, 0), width=bw - 0.02, height=bh)
    cx_, cw, chh, cs = windows[1]
    inst("props/architecture/sheer_curtains.tscn", (cx_, cs + chh + 0.12, ZB), label=False,
         width=cw + 0.3, height=chh + 0.12 + cs - 0.05)
    inst("props/architecture/heavy_drapes.tscn", (cx_, cs + chh + 0.12, ZB),
         label="sheer_curtains + heavy_drapes", label_pos=(cx_, 0.5, ZB + 0.25), label_rot=(0, 0, 0),
         width=cw + 0.5, height=chh + 0.12 + cs - 0.05)

    cam_b = mmul(euler((-12, 0, 0)), [[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    g.add("Camera", "Camera3D", pos=(0, 1.75, 6.2), basis=cam_b,
          props=[("script", g.ext_res("Script", "res://tests/props/gallery_camera.gd")), ("current", True),
                 ("fov", 70.0)])
    g.write(ROOT, "tests/props/prop_gallery.tscn")


# --------------------------------------------------------------------------- README

README_HEAD = """# Props

Furniture and clutter for the house: things that sit there and answer when
looked at. Working fixtures (doors, lamps, switches, TV, VCR, fridge, sink,
cabinets, dresser, phone, stereo, windows) live in `fixtures/`, not here.

## Conventions

- **Root** is a `StaticBody3D` named in PascalCase (a `RigidBody3D` for a few
  loose, nudgeable items). **+Z is the front** (the side a person faces).
- **Origin**: bottom centre at the floor or table contact for standing items;
  back centre (the wall plane, z = 0) for wall-hung items; exceptions are noted.
- **Physics layers**: solid furniture on 1 + 3 (`collision_layer = 5`), small
  tabletop/floor clutter and wall items on 3 only (`= 4`, the player walks
  through them), loose rigid items on 3 + 4 (`= 12`, mask 1 + 4). Each root has
  `metadata/prop_class` = `furniture` / `tabletop` / `wall` / `loose`.
- **Everything answers**: every root has an `Interactable` (or subclass) as a
  direct child named `Interactable`. Small things are `ExaminableInteractable`,
  anything with words on it is `ReadableInteractable`.
- **Materials** come from the palette in `art/materials/` by path. Surfaces the
  palette has no name for live in `props/materials/` (amber glass, mustard
  vinyl, dried leaves, fruit, mirror, ...). Printed graphics are per-prop
  `StandardMaterial3D`s on quads using `props/textures/`, generated by
  `tools/gen_prop_graphics.py`.
- Rugs carry `metadata/surface = &"rug"` on their body.

## Regenerating

- Graphics: `python3 tools/gen_prop_graphics.py`, then
  `godot --headless --audio-driver Dummy --path . --import`.
- Scenes: `python3 props/_build/build_props.py` rebuilds every generated
  `.tscn`, the gallery (`tests/props/prop_gallery.tscn`) and this file. It
  overwrites hand edits to generated scenes; scripts are hand-written.
- Test: `godot --headless --audio-driver Dummy --path . -s res://tests/props/test_props.gd`.
- Gallery: run `tests/props/prop_gallery.tscn` (right-drag to look, WASD/QE to fly). Multi-view
  screenshots: `tests/props/shots.gd` (see its header).

## Catalogue

Footprint is width (X) x depth (Z) x height (Y) in metres, from the visual
bounds (scripted pieces: default size).

| Scene | Footprint W x D x H | Origin | Interactable | Placement notes |
|---|---|---|---|---|
"""

README_TAIL = """
## Scripted props

- `living/sunburst_clock.gd` (`SunburstClock`): `start_hour` 15, `start_minute`
  47, `start_second`, `stopped` (freezes the hands and swaps to stopped
  observations), `time_scale`, `follow_camcorder_clock` (reads
  `get_time_of_day_seconds()` from the first node in group `camcorder_clock`
  if one exists), `tick_sound` (plays `clock_tick` via `Audio` when available).
- `media/note.gd` (`PropNote`): `preset` (BACK_BY_4, SHOPPING_LIST, GUTTERS,
  DENTIST, CUSTOM), `custom_text`, `custom_title`.
- `architecture/venetian_blinds.gd` (`VenetianBlinds`, `@tool`): `width`,
  `height`, `raised`, `slat_angle`, `slat_width`, `slat_pitch`, `bent_slat`,
  `slat_material`, `cord_material`, `wand_material`.
- `architecture/curtain_panels.gd` (`CurtainPanels`, `@tool`): `width`,
  `height`, `rod_offset`, `open_amount`, `fullness`, `pleat_width`,
  `pinch_pleat_header`, `fabric_material`, `rod_material`, `show_rod`.

The two `@tool` scripts build their geometry and collision as internal
children, so nothing generated is saved into the level scene.
"""


def readme() -> None:
    lines = [README_HEAD.rstrip("\n")]
    for e in sorted(CATALOG, key=lambda e: e.path):
        w, d, h = e.scene.footprint()
        lines.append("| `%s` | %.2f x %.2f x %.2f | %s | %s | %s |" % (
            e.path, w, d, h, e.origin, e.kind, e.notes.replace("|", "/")))
    lines.append(README_TAIL)
    with open(os.path.join(ROOT, "props", "README.md"), "w") as fh:
        fh.write("\n".join(lines))


def main() -> None:
    write_prop_materials()
    living.build()
    media.build()
    kitchen.build()
    hallway.build()
    for e in CATALOG:
        e.scene.write(ROOT, e.path)
    gallery()
    readme()
    print("built %d prop scenes" % len(CATALOG))


if __name__ == "__main__":
    main()
