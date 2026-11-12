#!/usr/bin/env python3
"""Generates tests/atmosphere/sunroom.tscn (a box-built test room).

Usage: python3 tests/atmosphere/tools/gen_sunroom.py tests/atmosphere/sunroom.tscn
"""
import sys

OUT = sys.argv[1]

mats = ["floor_hardwood", "wall_wood_paneling", "wall_plaster_cream", "ceiling_popcorn",
        "trim_white", "glass_window", "glass_dusty", "plant_green", "brick_red",
        "fabric_floral_sofa", "wood_medium", "wood_dark", "cardboard", "carpet_beige",
        "plastic_beige", "fabric_curtain_sheer"]
ext = []
for i, m in enumerate(mats):
    ext.append(f'[ext_resource type="Material" path="res://art/materials/{m}.tres" id="m_{m}"]')

ext.append('[ext_resource type="PackedScene" path="res://atmosphere/afternoon_atmosphere.tscn" id="s_atmo"]')
ext.append('[ext_resource type="PackedScene" path="res://atmosphere/dust_motes.tscn" id="s_dust"]')
ext.append('[ext_resource type="PackedScene" path="res://atmosphere/haze_volume.tscn" id="s_haze"]')
ext.append('[ext_resource type="PackedScene" path="res://atmosphere/post_fx.tscn" id="s_post"]')
ext.append('[ext_resource type="Script" path="res://tests/atmosphere/sunroom.gd" id="sc_room"]')

subs = []
nodes = []
mesh_ids = {}


def box_mesh(size):
    key = tuple(round(s, 4) for s in size)
    if key in mesh_ids:
        return mesh_ids[key]
    mid = f"Box_{len(mesh_ids)}"
    subs.append(f'[sub_resource type="BoxMesh" id="{mid}"]\nsize = Vector3({key[0]}, {key[1]}, {key[2]})\n')
    sid = f"Shape_{len(mesh_ids)}"
    subs.append(f'[sub_resource type="BoxShape3D" id="{sid}"]\nsize = Vector3({key[0]}, {key[1]}, {key[2]})\n')
    mesh_ids[key] = (mid, sid)
    return mesh_ids[key]


def box(name, parent, mn, mx, mat, collide=True, shadow=True, gi=True, surface=None):
    size = [mx[i] - mn[i] for i in range(3)]
    c = [(mx[i] + mn[i]) / 2 for i in range(3)]
    mid, sid = box_mesh(size)
    t = f"Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, {c[0]:.4f}, {c[1]:.4f}, {c[2]:.4f})"
    if collide:
        nodes.append(f'[node name="{name}" type="StaticBody3D" parent="{parent}"]\ntransform = {t}\n'
                     + (f'metadata/surface = &"{surface}"\n' if surface else ""))
        nodes.append(f'[node name="Mesh" type="MeshInstance3D" parent="{parent}/{name}"]\nmesh = SubResource("{mid}")\n'
                     f'surface_material_override/0 = ExtResource("m_{mat}")\n')
        nodes.append(f'[node name="Shape" type="CollisionShape3D" parent="{parent}/{name}"]\nshape = SubResource("{sid}")\n')
    else:
        extra = ""
        if not shadow:
            extra += "cast_shadow = 0\n"
        if not gi:
            extra += "gi_mode = 0\n"
        nodes.append(f'[node name="{name}" type="MeshInstance3D" parent="{parent}"]\ntransform = {t}\n{extra}'
                     f'mesh = SubResource("{mid}")\nsurface_material_override/0 = ExtResource("m_{mat}")\n')


# --- Room -------------------------------------------------------------------
X0, X1 = -2.5, 2.5    # interior, west .. east
Z0, Z1 = -2.0, 2.0    # interior, north .. south
H = 2.44
T = 0.30              # exterior wall
FT = 0.30             # floor / ceiling slab

nodes.append('[node name="Room" type="Node3D" parent="."]\n')
R = "Room"
box("Floor", R, (X0 - T, -FT, Z0 - T), (X1 + T, 0.0, Z1 + T), "floor_hardwood", surface="wood")
box("Ceiling", R, (X0 - T, H, Z0 - T), (X1 + T, H + FT, Z1 + T), "ceiling_popcorn")
# North and east walls: solid.
box("WallNorth", R, (X0 - T, -FT, Z0 - T), (X1 + T, H + FT, Z0), "wall_wood_paneling")
box("WallEast", R, (X1, -FT, Z0), (X1 + T, H + FT, Z1), "wall_plaster_cream")

# West wall with one window: z in [WZ0, WZ1], sill..head
WZ0, WZ1, SILL, HEAD = -0.75, 0.45, 0.80, 2.08
box("WallWest_N", R, (X0 - T, -FT, Z0), (X0, H + FT, WZ0), "wall_wood_paneling")
box("WallWest_S", R, (X0 - T, -FT, WZ1), (X0, H + FT, Z1), "wall_wood_paneling")
box("WallWest_Sill", R, (X0 - T, -FT, WZ0), (X0, SILL, WZ1), "wall_wood_paneling")
box("WallWest_Head", R, (X0 - T, HEAD, WZ0), (X0, H + FT, WZ1), "wall_wood_paneling")

# South wall with one window: x in [SX0, SX1]
SX0, SX1 = -1.55, -0.35
box("WallSouth_W", R, (X0 - T, -FT, Z1), (SX0, H + FT, Z1 + T), "wall_wood_paneling")
box("WallSouth_E", R, (SX1, -FT, Z1), (X1 + T, H + FT, Z1 + T), "wall_wood_paneling")
box("WallSouth_Sill", R, (SX0, -FT, Z1), (SX1, SILL, Z1 + T), "wall_wood_paneling")
box("WallSouth_Head", R, (SX0, HEAD, Z1), (SX1, H + FT, Z1 + T), "wall_wood_paneling")

# --- Window frames, muntins, glass -------------------------------------------
nodes.append('[node name="Windows" type="Node3D" parent="."]\n')
W = "Windows"
f = 0.05   # frame width
gx = X0 - T * 0.5   # glass plane in the wall middle
# West window frame (inner trim, flush with interior face)
box("WestSillBoard", W, (X0 - T, SILL - 0.02, WZ0 - 0.04), (X0 + 0.04, SILL + 0.02, WZ1 + 0.04), "trim_white", collide=False)
box("WestJambN", W, (X0 - T, SILL, WZ0), (X0 + 0.01, HEAD, WZ0 + f), "trim_white", collide=False)
box("WestJambS", W, (X0 - T, SILL, WZ1 - f), (X0 + 0.01, HEAD, WZ1), "trim_white", collide=False)
box("WestHeadTrim", W, (X0 - T, HEAD - f, WZ0), (X0 + 0.01, HEAD, WZ1), "trim_white", collide=False)
mz = (WZ0 + WZ1) / 2
my = (SILL + HEAD) / 2
box("WestMuntinV", W, (gx - 0.02, SILL, mz - 0.018), (gx + 0.02, HEAD, mz + 0.018), "trim_white", collide=False)
box("WestMuntinH", W, (gx - 0.02, my - 0.025, WZ0), (gx + 0.02, my + 0.025, WZ1), "trim_white", collide=False)
box("WestGlass", W, (gx - 0.003, SILL, WZ0), (gx + 0.003, HEAD, WZ1), "glass_dusty", collide=False, shadow=False, gi=False)

gz = Z1 + T * 0.5
box("SouthSillBoard", W, (SX0 - 0.04, SILL - 0.02, Z1 - 0.04), (SX1 + 0.04, SILL + 0.02, Z1 + T), "trim_white", collide=False)
box("SouthJambW", W, (SX0, SILL, Z1 - 0.01), (SX0 + f, HEAD, Z1 + T), "trim_white", collide=False)
box("SouthJambE", W, (SX1 - f, SILL, Z1 - 0.01), (SX1, HEAD, Z1 + T), "trim_white", collide=False)
box("SouthHeadTrim", W, (SX0, HEAD - f, Z1 - 0.01), (SX1, HEAD, Z1 + T), "trim_white", collide=False)
box("SouthMuntinH", W, (SX0, my - 0.025, gz - 0.02), (SX1, my + 0.025, gz + 0.02), "trim_white", collide=False)
box("SouthGlass", W, (SX0, SILL, gz - 0.003), (SX1, HEAD, gz + 0.003), "glass_window", collide=False, shadow=False, gi=False)

# --- Furniture ---------------------------------------------------------------
nodes.append('[node name="Furniture" type="Node3D" parent="."]\n')
F = "Furniture"
box("Rug", F, (-1.0, 0.0, -1.1), (1.4, 0.012, 0.9), "carpet_beige", collide=False)
box("SofaBase", F, (-0.6, 0.0, -2.0), (1.5, 0.45, -1.15), "fabric_floral_sofa")
box("SofaBack", F, (-0.6, 0.45, -2.0), (1.5, 0.85, -1.78), "fabric_floral_sofa")
box("SofaArmW", F, (-0.6, 0.45, -1.78), (-0.42, 0.62, -1.15), "fabric_floral_sofa")
box("SofaArmE", F, (1.32, 0.45, -1.78), (1.5, 0.62, -1.15), "fabric_floral_sofa")
box("CoffeeTable", F, (-0.2, 0.36, -0.55), (0.9, 0.42, 0.05), "wood_medium")
box("CoffeeTableBase", F, (-0.1, 0.0, -0.45), (0.8, 0.36, -0.05), "wood_dark")
box("Shelf", F, (2.1, 0.0, -1.6), (2.5, 1.85, -0.5), "wood_dark")
box("BoxA", F, (1.5, 0.0, 0.9), (2.05, 0.45, 1.5), "cardboard")
box("BoxB", F, (1.6, 0.45, 1.0), (2.0, 0.8, 1.4), "cardboard")
box("BoxC", F, (2.0, 0.0, 1.55), (2.45, 0.38, 1.95), "cardboard")
box("SideTable", F, (-2.45, 0.0, 1.2), (-1.95, 0.6, 1.7), "wood_medium")
box("Lamp", F, (-2.3, 0.6, 1.35), (-2.1, 0.95, 1.55), "plastic_beige", collide=False)

# --- Outside -----------------------------------------------------------------
nodes.append('[node name="Outside" type="Node3D" parent="."]\n')
O = "Outside"
box("Lawn", O, (-30, -0.6, -30), (30, -0.3, 30), "plant_green")
box("NeighbourWall", O, (-14, -0.3, -9), (-13.4, 4.5, 9), "brick_red")
box("Fence", O, (-8, -0.3, 6), (8, 1.6, 6.08), "wood_medium")

head = f'[gd_scene format=3]\n\n' + "\n".join(ext) + "\n\n" + "\n".join(subs) + "\n"
root = '[node name="Sunroom" type="Node3D"]\nscript = ExtResource("sc_room")\n\n'
root += '[node name="Atmosphere" parent="." instance=ExtResource("s_atmo")]\n\n'
root += ('[node name="DustWest" parent="." instance=ExtResource("s_dust")]\n'
         'transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, -1.3, 1.2, -0.2)\n'
         'box_size = Vector3(2.3, 2.3, 2.4)\n\n')
root += ('[node name="DustSouth" parent="." instance=ExtResource("s_dust")]\n'
         'transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0.3, 1.2, 1.4)\n'
         'box_size = Vector3(3.0, 2.3, 1.1)\n\n')
root += ('[node name="HazeWest" parent="." instance=ExtResource("s_haze")]\n'
         'transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, -1.6, 1.25, -0.15)\n'
         'size = Vector3(1.9, 2.5, 2.2)\n\n')
root += ('[node name="HazeSouth" parent="." instance=ExtResource("s_haze")]\n'
         'transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, -0.4, 1.25, 1.45)\n'
         'size = Vector3(2.4, 2.5, 1.2)\n\n')
root += ('[node name="ReflectionProbe" type="ReflectionProbe" parent="."]\n'
         'transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1.22, 0)\n'
         'size = Vector3(5.0, 2.44, 4.0)\nbox_projection = true\ninterior = true\n'
         'ambient_mode = 0\n\n')
root += ('[node name="Camera" type="Camera3D" parent="."]\n'
         'transform = Transform3D(0.2971, -0.0808, 0.9514, 0.0000, 0.9964, 0.0846, -0.9549, -0.0251, 0.2960, 2.0, 1.6, 1.2)\n'
         'current = true\nfov = 68.0\n\n')
root += '[node name="PostFx" parent="." instance=ExtResource("s_post")]\n\n'

open(OUT, "w").write(head + root + "\n".join(nodes))
print("wrote", OUT)
