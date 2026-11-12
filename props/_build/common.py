"""Shared registry and small helpers for the prop builders."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from tscn import Scene, Raw, write_material, PROP_MAT, TEX

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class Entry:
    path: str
    scene: Scene
    origin: str
    kind: str
    notes: str
    category: str = ""
    extra: dict = field(default_factory=dict)


CATALOG: list[Entry] = []

ORIGIN_FLOOR = "bottom centre (floor)"
ORIGIN_TABLE = "bottom centre (tabletop)"
ORIGIN_WALL = "back centre (wall)"


def register(path: str, scene: Scene, origin: str, kind: str, notes: str = "", **extra) -> Scene:
    CATALOG.append(Entry(path, scene, origin, kind, notes, path.split("/")[1], extra))
    return scene


# Prop-specific materials (surfaces the shared palette has no name for).
PROP_MATERIALS: dict[str, list[tuple[str, object]]] = {
    "glass_amber": [("transparency", 1), ("albedo_color", Raw("Color(0.72, 0.38, 0.07, 0.78)")),
                    ("metallic_specular", 0.7), ("roughness", 0.08)],
    "vinyl_mustard": [("albedo_color", Raw("Color(0.72, 0.53, 0.18, 1)")), ("roughness", 0.35)],
    "plastic_red": [("albedo_color", Raw("Color(0.6, 0.08, 0.06, 1)")), ("roughness", 0.4)],
    "jute": [("albedo_color", Raw("Color(0.68, 0.56, 0.38, 1)")), ("roughness", 1.0)],
    "dried_leaf": [("albedo_color", Raw("Color(0.52, 0.4, 0.22, 1)")), ("roughness", 0.9)],
    "dried_leaf_dark": [("albedo_color", Raw("Color(0.36, 0.25, 0.13, 1)")), ("roughness", 0.9)],
    "soil_dry": [("albedo_color", Raw("Color(0.32, 0.24, 0.17, 1)")), ("roughness", 1.0)],
    "fruit_red": [("albedo_color", Raw("Color(0.55, 0.08, 0.06, 1)")), ("roughness", 0.45)],
    "fruit_orange": [("albedo_color", Raw("Color(0.85, 0.45, 0.08, 1)")), ("roughness", 0.65)],
    "banana_brown": [("albedo_color", Raw("Color(0.34, 0.23, 0.1, 1)")), ("roughness", 0.75)],
    "coffee_dried": [("albedo_color", Raw("Color(0.13, 0.08, 0.04, 1)")), ("roughness", 0.15)],
    "glaze_brown": [("albedo_color", Raw("Color(0.36, 0.18, 0.08, 1)")), ("roughness", 0.3)],
    "packing_tape": [("transparency", 1), ("albedo_color", Raw("Color(0.72, 0.58, 0.36, 0.85)")),
                     ("roughness", 0.3)],
    "mirror_dull": [("albedo_color", Raw("Color(0.66, 0.67, 0.64, 1)")), ("metallic", 1.0),
                    ("roughness", 0.07)],
    "smoked_plastic": [("transparency", 1), ("albedo_color", Raw("Color(0.1, 0.08, 0.07, 0.62)")),
                       ("roughness", 0.12)],
    "towel_blue": [("albedo_color", Raw("Color(0.36, 0.52, 0.6, 1)")), ("roughness", 1.0)],
    "umbrella_navy": [("albedo_color", Raw("Color(0.1, 0.13, 0.24, 1)")), ("roughness", 0.8)],
    "ir_window": [("albedo_color", Raw("Color(0.22, 0.02, 0.03, 1)")), ("roughness", 0.1)],
    "plastic_teal": [("albedo_color", Raw("Color(0.2, 0.5, 0.5, 1)")), ("roughness", 0.45)],
}
# Newsprint: the newspaper texture mapped triplanar, for wrapped items.
NEWSPRINT = ("newsprint", [("albedo_texture", Raw('ExtResource("1")')), ("roughness", 0.95),
                           ("uv1_scale", Raw("Vector3(3, 3, 3)")), ("uv1_triplanar", True)],
             [("Texture2D", TEX % "newspaper_front.png")])


def write_prop_materials() -> None:
    for name, props in PROP_MATERIALS.items():
        write_material(ROOT, name, props)
    write_material(ROOT, NEWSPRINT[0], NEWSPRINT[1], NEWSPRINT[2])


def tex(name: str, **kw) -> dict:
    d = {"tex": name, "roughness": kw.pop("roughness", 0.85)}
    d.update(kw)
    return d
