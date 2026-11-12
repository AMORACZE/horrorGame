"""Material palette definitions -> art/materials/<name>.tres (StandardMaterial3D).

Every material maps textures with triplanar projection and a real-world
``uv1_scale`` (1 / metres-per-tile), so texel density is the same on any box:

* ``world``  - uv1_world_triplanar: architecture. Adjacent wall/floor boxes line
  up seamlessly and wall textures are anchored to world height (y = 0 is the
  ground floor), which some sets use for height-dependent wear.
* ``object`` - object-space triplanar: props, furniture, fixtures. The texture
  sticks to the mesh, so doors, drawers and physics props do not "swim" when
  they move, and rotated furniture keeps its grain. Node *scale* stretches it:
  size primitives with their mesh size, not node scale.
* ``none``   - untextured (glass, mirror, CRT): parameters only.

Image axes: on side faces the image's vertical axis is world/local +Y, so
vertical grain/grooves/stripes stay vertical on both X- and Z-facing walls. On
floors/tops the image vertical axis is the Z axis (floor planks run along Z).
"""
from __future__ import annotations

import os

T = 'res://art/textures/{0}/{0}_{1}.png'

# Sets whose normal map is shared with another set (not written separately)
SHARED_NORMAL = {'floor_hardwood_dusty'}


def M(desc, mapping, tile, albedo=None, normal=None, orm=None, color=(1, 1, 1, 1), **kw):
    return dict(desc=desc, map=mapping, tile=tile, albedo=albedo, normal=normal, orm=orm,
                color=color, **kw)


# fmt: off
MATERIALS = {
    # ---------------------------------------------------------------- architecture (world)
    'wall_wood_paneling': M('1970s random-groove walnut-look plywood panelling, satin; one 4x8 ft sheet per tile, grooves vertical',
        'world', (1.22, 2.44), 'wall_wood_paneling', 'wall_wood_paneling', 'wall_wood_paneling',
        normal_scale=1.0, ao_light_affect=0.25, notes='Tile is one full sheet: 1.22 m wide, 2.44 m tall (= ceiling), anchored at y=0; scuffs near the floor, smudges at hand height.'),
    'carpet_shag_gold': M('Deep gold/orange shag pile with matted traffic areas',
        'world', (0.75, 0.75), 'carpet_shag_gold', 'carpet_shag_gold', 'carpet_shag_gold',
        normal_scale=0.75, ao_light_affect=0.35, specular=0.3, rim=0.25, notes='Floors only. Rim term fakes fibre sheen at grazing angles.'),
    'carpet_beige': M('Beige cut-pile wall-to-wall carpet (1990s bedrooms/halls)',
        'world', (0.5, 0.5), 'carpet_beige', 'carpet_beige', 'carpet_beige',
        normal_scale=0.6, ao_light_affect=0.25, specular=0.3, rim=0.2),
    'floor_hardwood': M('2-1/4" red-oak strip floor, amber finish worn in traffic paths',
        'world', (1.2, 1.2), 'floor_hardwood', 'floor_hardwood', 'floor_hardwood',
        normal_scale=1.0, ao_light_affect=0.1, notes='Strips run along world Z. Build rooms so the long axis is Z, or use it as is (strips across the room are also period-correct).'),
    'floor_hardwood_dusty': M('Same strip floor under a film of dust (unused rooms, attic, under furniture)',
        'world', (1.2, 1.2), 'floor_hardwood_dusty', 'floor_hardwood', 'floor_hardwood_dusty',
        normal_scale=1.0, ao_light_affect=0.1),
    'linoleum_kitchen': M('1970s sheet vinyl: gold eight-point star medallions, brown/cream, 12" repeat, worn gloss',
        'world', (0.61, 0.61), 'linoleum_kitchen', 'linoleum_kitchen', 'linoleum_kitchen',
        normal_scale=1.0, specular=0.5, notes='2 x 2 motifs per tile.'),
    'tile_bathroom': M('4-1/4" glazed seafoam ceramic wall/floor tile with dingy grout',
        'world', (0.864, 0.864), 'tile_bathroom', 'tile_bathroom', 'tile_bathroom',
        normal_scale=1.0, specular=0.5, notes='8 x 8 tiles per tile; grout lines align to world 0, so tile edges line up across walls.'),
    'ceiling_popcorn': M('Sprayed "popcorn" acoustic ceiling, nicotine-yellowed',
        'world', (0.6, 0.6), 'ceiling_popcorn', 'ceiling_popcorn', 'ceiling_popcorn',
        normal_scale=1.4, ao_light_affect=0.3, specular=0.3),
    'ceiling_popcorn_stained': M('Popcorn ceiling with old water-leak tide marks and smoke',
        'world', (2.4, 2.4), 'ceiling_popcorn_stained', 'ceiling_popcorn_stained', 'ceiling_popcorn_stained',
        normal_scale=1.4, ao_light_affect=0.3, specular=0.3, notes='One stain per 2.4 m tile, centred, clean edges: use on a 2.4 x 2.4 m patch aligned to multiples of 2.4 m (or accept a stain every 2.4 m on a whole ceiling). Coarser spray than ceiling_popcorn.'),
    'wall_plaster_cream': M('Painted drywall, roller stipple, cream paint yellowed by smoke',
        'world', (1.22, 2.44), 'wall_plaster_cream', 'wall_plaster_cream', 'wall_plaster_cream',
        normal_scale=1.0, notes='Height-anchored (y=0 floor): darker near the ceiling, scuffs near the floor, hand smudges ~1.1 m.'),
    'wallpaper_floral': M('1980s small floral wallpaper: dusty-rose sprigs, sage leaves on cream, half-drop',
        'world', (0.533, 0.533), 'wallpaper_floral', 'wallpaper_floral', 'wallpaper_floral',
        normal_scale=1.0, notes='Tile = one 21" roll width; roll seam at tile edge.'),
    'wallpaper_stripe': M('1980s pastel regency stripe (rose / cream / sage-blue) with pearl-glaze cream bands',
        'world', (0.533, 0.533), 'wallpaper_stripe', 'wallpaper_stripe', 'wallpaper_stripe',
        normal_scale=1.0),
    'brick_red': M('Common red brick, running bond, recessed grey mortar (fireplace, exterior)',
        'world', (0.852, 0.804), 'brick_red', 'brick_red', 'brick_red',
        normal_scale=1.0, ao_light_affect=0.2, notes='4 bricks x 12 courses per tile (203 x 57 mm brick, 10 mm joints).'),
    'trim_white': M('Baseboards, casings, doors: oil gloss enamel gone ivory',
        'world', (0.5, 0.5), 'trim_white', 'trim_white', 'trim_white', normal_scale=1.0),
    'concrete': M('Cast concrete slab: garage, basement, steps, foundation',
        'world', (1.5, 1.5), 'concrete', 'concrete', 'concrete', normal_scale=1.0),
    'glass_window': M('Clean window glass (alpha blend: no shadow, sun passes)',
        'none', None, color=(0.86, 0.9, 0.9, 0.1), roughness=0.04, specular=0.5, transparent='alpha',
        notes='Alpha-blended surfaces do not render into the shadow map, so sunlight passes and casts the window frame shadow only. Set cast_shadow = OFF and gi_mode = Disabled on the glass MeshInstance3D anyway (SDFGI would otherwise treat it as a wall).'),
    'window_blown_out': M('Over-exposed exterior backdrop card (sky, hedge, lawn) for outside windows',
        'world', (4.0, 4.88), 'window_blown_out', None, None, emission='window_blown_out',
        notes='Emissive, alpha-pass (casts no shadow, so it can sit in the sun path). Anchored to y=0 = ground. Place 1-3 m outside the glass; glow blooms it.'),

    # ---------------------------------------------------------------- woods (object)
    'wood_dark': M('Dark walnut-stained furniture wood (70s case goods, frames)',
        'object', (0.5, 0.5), 'wood_dark', 'wood_furniture', 'wood_furniture', normal_scale=1.0, specular=0.5,
        notes='Grain runs along local Y on sides and local Z on tops.'),
    'wood_medium': M('Medium "fruitwood/pecan" stained furniture wood',
        'object', (0.5, 0.5), 'wood_medium', 'wood_furniture', 'wood_furniture', normal_scale=1.0),
    'wood_light': M('Light maple/pine furniture wood',
        'object', (0.5, 0.5), 'wood_light', 'wood_furniture', 'wood_furniture', normal_scale=1.0),
    'wood_oak_cabinet': M('1980s golden-oak cabinet doors and boxes, open-pore grain, satin',
        'object', (0.6, 0.6), 'wood_oak_cabinet', 'wood_oak_cabinet', 'wood_oak_cabinet', normal_scale=1.0),
    'laminate_formica': M('Beige gold-fleck laminate countertop, knife marks',
        'object', (0.3, 0.3), 'laminate_formica', 'laminate_formica', 'laminate_formica', normal_scale=1.0),

    # ---------------------------------------------------------------- plastics (object)
    'plastic_beige': M('Yellowed beige ABS (computers, phones, VCR, radios) with moulded stipple',
        'object', (0.2, 0.2), 'plastic_beige', 'plastic', 'plastic', normal_scale=1.0),
    'plastic_white': M('Off-white moulded plastic', 'object', (0.2, 0.2), 'plastic', 'plastic', 'plastic',
        color=(0.86, 0.85, 0.81, 1)),
    'plastic_grey': M('Mid grey moulded plastic', 'object', (0.2, 0.2), 'plastic', 'plastic', 'plastic',
        color=(0.4, 0.4, 0.4, 1)),
    'plastic_black': M('Black moulded plastic (TV, VCR, tape cases)', 'object', (0.2, 0.2), 'plastic', 'plastic', 'plastic',
        color=(0.05, 0.05, 0.05, 1), roughness=0.9),

    # ---------------------------------------------------------------- metals (object)
    'metal_brass': M('Lacquered brass gone slightly tarnished (lamps, knobs, fireplace tools)',
        'object', (0.3, 0.3), 'metal_brass', 'metal_brass', 'metal_brass', metallic=1.0, normal_scale=1.0),
    'metal_chrome': M('Chrome plate with smudges and fingerprints (taps, toaster, chair legs)',
        'object', (0.3, 0.3), 'metal_chrome', None, 'metal_chrome', metallic=1.0),
    'metal_dark': M('Dark cast iron / blued steel with rust specks', 'object', (0.3, 0.3),
        'metal_dark', 'metal_dark', 'metal_dark', metallic=1.0, normal_scale=1.0),
    'metal_painted_white': M('White baked enamel on steel (fridge sides, radiators, washer)',
        'object', (0.4, 0.4), 'enamel', 'enamel', 'enamel', color=(0.86, 0.85, 0.8, 1), clearcoat=0.4),
    'appliance_harvest_gold': M('Harvest Gold appliance enamel, glossy with orange-peel',
        'object', (0.4, 0.4), 'enamel', 'enamel', 'enamel', color=(0.8, 0.6, 0.22, 1), clearcoat=0.6),
    'appliance_avocado': M('Avocado Green appliance enamel, glossy with orange-peel',
        'object', (0.4, 0.4), 'enamel', 'enamel', 'enamel', color=(0.44, 0.47, 0.2, 1), clearcoat=0.6),

    # ---------------------------------------------------------------- fabrics (object)
    'fabric_floral_sofa': M('1980s floral upholstery: dusty rose/mauve blooms, teal-sage leaves, oatmeal basket weave',
        'object', (0.6, 0.6), 'fabric_floral_sofa', 'fabric_floral_sofa', 'fabric_floral_sofa',
        normal_scale=1.0, specular=0.35, rim=0.3),
    'fabric_corduroy_brown': M('Brown wide-wale corduroy (4 mm wales, vertical on sides)',
        'object', (0.2, 0.2), 'fabric_corduroy_brown', 'fabric_corduroy_brown', 'fabric_corduroy_brown',
        normal_scale=1.0, specular=0.35, rim=0.35),
    'fabric_plaid': M('Brown / rust / mustard / cream tartan in 2/2 twill (recliner, blanket)',
        'object', (0.25, 0.25), 'fabric_plaid', 'fabric_plaid', 'fabric_plaid',
        normal_scale=1.0, specular=0.35, rim=0.25),
    'fabric_lampshade': M('Slubby cream linen lampshade, glows when lit from inside',
        'object', (0.15, 0.15), 'fabric_lampshade', 'fabric_lampshade', 'fabric_lampshade',
        normal_scale=0.8, specular=0.3, cull='disabled', backlight=(0.75, 0.62, 0.42),
        notes='Two-sided with backlight: a lamp inside lights the outside. Use an open cylinder (no caps).'),
    'fabric_curtain_sheer': M('Ivory voile sheer curtain: soft vertical folds, light passes through',
        'object', (0.6, 0.6), 'fabric_curtain_sheer', 'fabric_curtain_sheer', 'fabric_curtain_sheer',
        normal_scale=1.0, specular=0.2, cull='disabled', backlight=(0.85, 0.8, 0.68), transparent='alpha',
        notes='Alpha blend + backlight: glows warmly with the sun behind it; casts no shadow (alpha pass), so the sun shaft still reaches the floor. Avoid stacking several sheers in a row (blend sorting).'),
    'fabric_curtain_heavy': M('Lined harvest-gold slub-weave drapes with deep pleats',
        'object', (0.6, 0.6), 'fabric_curtain_heavy', 'fabric_curtain_heavy', 'fabric_curtain_heavy',
        normal_scale=1.0, specular=0.3, backlight=(0.22, 0.16, 0.05), rim=0.2,
        notes='Opaque (casts full shadow). Faint warm backlight for sun bleeding through the edges.'),
    'leather_brown': M('Brown leather (recliner, belt, wallet): pebble grain, creases, rubbed patina',
        'object', (0.25, 0.25), 'leather_brown', 'leather_brown', 'leather_brown', normal_scale=1.0),
    'rubber_black': M('Black rubber with grey bloom (feet, hoses, cords)', 'object', (0.15, 0.15),
        'rubber_black', 'rubber_black', 'rubber_black', normal_scale=1.0, specular=0.35),
    'dust_sheet': M('Unbleached muslin drop cloth thrown over furniture', 'object', (0.5, 0.5),
        'dust_sheet', 'dust_sheet', 'dust_sheet', normal_scale=1.0, specular=0.3, rim=0.2, cull='disabled'),

    # ---------------------------------------------------------------- glass & screens
    'glass_dusty': M('Grimy glass (cabinet doors, picture frames, garage window)', 'object', (0.5, 0.5),
        'glass_dusty', None, 'glass_dusty', transparent='alpha', specular=0.5,
        notes='Alpha blend; no shadow. Dust film modulates both opacity and roughness.'),
    'crt_screen_off': M('Switched-off CRT: dark grey-green phosphor glass with a soft reflection',
        'none', None, color=(0.045, 0.055, 0.05, 1), roughness=0.22, specular=0.6, clearcoat=1.0,
        clearcoat_roughness=0.04),
    'mirror': M('Silvered mirror glass', 'none', None, color=(0.86, 0.88, 0.86, 1), roughness=0.02,
        metallic=1.0, notes='Needs a ReflectionProbe (or SSR) in the room to reflect anything but the sky.'),

    # ---------------------------------------------------------------- misc (object)
    'ceramic_white': M('Glazed white ceramic (mugs, sink, toilet, lamp base) with faint crazing',
        'object', (0.2, 0.2), 'ceramic_white', 'ceramic_white', 'ceramic_white', normal_scale=1.0, specular=0.5),
    'paper_white': M('White paper (letters, notes, mail)', 'object', (0.3, 0.3), 'paper_white', 'paper', 'paper',
        normal_scale=0.6),
    'paper_yellowed': M('Yellowed, foxed paper (old books, newspapers)', 'object', (0.3, 0.3),
        'paper_yellowed', 'paper', 'paper', normal_scale=0.6),
    'cardboard': M('Kraft corrugated cardboard, flutes along local X (ridges every 8 mm)', 'object', (0.3, 0.3),
        'cardboard', 'cardboard', 'cardboard', normal_scale=1.0),
    'plant_green': M('Dense houseplant foliage (pothos/philodendron) for sphere/blob plants', 'object', (0.3, 0.3),
        'plant_green', 'plant_green', 'plant_green', normal_scale=1.0, specular=0.45),
    'book_cover_a': M('Cloth-bound book: oxblood', 'object', (0.1, 0.1), 'book_cloth', 'book_cloth', 'book_cloth',
        color=(0.46, 0.14, 0.11, 1)),
    'book_cover_b': M('Cloth-bound book: navy', 'object', (0.1, 0.1), 'book_cloth', 'book_cloth', 'book_cloth',
        color=(0.13, 0.2, 0.34, 1)),
    'book_cover_c': M('Cloth-bound book: bottle green', 'object', (0.1, 0.1), 'book_cloth', 'book_cloth', 'book_cloth',
        color=(0.17, 0.31, 0.19, 1)),
    'book_cover_d': M('Cloth-bound book: tan', 'object', (0.1, 0.1), 'book_cloth', 'book_cloth', 'book_cloth',
        color=(0.6, 0.49, 0.28, 1)),
}
# fmt: on

NEW_MATERIALS = ['floor_hardwood_dusty', 'ceiling_popcorn_stained', 'concrete', 'window_blown_out',
                 'mirror', 'dust_sheet']


def _c(c):
    return 'Color(%g, %g, %g, %g)' % (tuple(c) + ((1,) if len(c) == 3 else ()))


def _v3(v):
    return 'Vector3(%g, %g, %g)' % v


def render(name: str, m: dict) -> str:
    ext = []
    props = []

    def tex(path):
        for i, (p, _) in enumerate(ext):
            if p == path:
                return f'ExtResource("{i + 1}")'
        ext.append((path, None))
        return f'ExtResource("{len(ext)}")'

    props.append(f'resource_name = "{name}"')
    tr = m.get('transparent')
    if tr == 'alpha':
        props.append('transparency = 1')
    cull = m.get('cull')
    if cull == 'disabled':
        props.append('cull_mode = 2')
    if m.get('albedo') or m.get('normal') or m.get('orm') or m.get('emission'):
        props.append('texture_filter = 5')   # linear, mipmaps, anisotropic (raking views)
    color = m['color']
    if m.get('emission'):
        color = (0, 0, 0, 1)
        props.append('specular_mode = 2')
        props.append('disable_receive_shadows = true')
        props.append('transparency = 1')
    props.append(f'albedo_color = {_c(color)}')
    if m.get('albedo') and not m.get('emission'):
        props.append(f'albedo_texture = {tex(T.format(m["albedo"], "albedo"))}')
    if 'metallic' in m:
        props.append(f'metallic = {m["metallic"]:g}')
    props.append(f'metallic_specular = {m.get("specular", 0.5):g}')
    if m.get('orm') and m.get('metallic'):
        props.append(f'metallic_texture = {tex(T.format(m["orm"], "orm"))}')
        props.append('metallic_texture_channel = 2')
    if m.get('orm'):
        props.append(f'roughness = {m.get("roughness", 1.0):g}')
        props.append(f'roughness_texture = {tex(T.format(m["orm"], "orm"))}')
        props.append('roughness_texture_channel = 1')
    else:
        props.append(f'roughness = {m.get("roughness", 1.0):g}')
    if m.get('emission'):
        props.append('emission_enabled = true')
        props.append('emission = Color(1, 1, 1, 1)')
        props.append(f'emission_energy_multiplier = {m.get("emission_energy", 2.2):g}')
        props.append(f'emission_texture = {tex(T.format(m["emission"], "albedo"))}')
    if m.get('normal'):
        props.append('normal_enabled = true')
        props.append(f'normal_scale = {m.get("normal_scale", 1.0):g}')
        props.append(f'normal_texture = {tex(T.format(m["normal"], "normal"))}')
    if m.get('rim'):
        props.append('rim_enabled = true')
        props.append(f'rim = {m["rim"]:g}')
        props.append('rim_tint = 0.6')
    if m.get('clearcoat'):
        props.append('clearcoat_enabled = true')
        props.append(f'clearcoat = {m["clearcoat"]:g}')
        props.append(f'clearcoat_roughness = {m.get("clearcoat_roughness", 0.12):g}')
    if m.get('orm') and m.get('ao', True) and not m.get('emission'):
        props.append('ao_enabled = true')
        props.append(f'ao_light_affect = {m.get("ao_light_affect", 0.0):g}')
        props.append(f'ao_texture = {tex(T.format(m["orm"], "orm"))}')
        props.append('ao_texture_channel = 0')
    if m.get('backlight'):
        props.append('backlight_enabled = true')
        props.append(f'backlight = {_c(m["backlight"])}')
    if m['map'] in ('world', 'object') and m['tile']:
        wx, hy = m['tile']
        props.append(f'uv1_scale = {_v3((round(1 / wx, 5), round(1 / hy, 5), round(1 / wx, 5)))}')
        props.append('uv1_triplanar = true')
        props.append('uv1_triplanar_sharpness = 8.0')
        if m['map'] == 'world':
            props.append('uv1_world_triplanar = true')
    head = '[gd_resource type="StandardMaterial3D" format=3]\n\n'
    for i, (p, _) in enumerate(ext):
        head += f'[ext_resource type="Texture2D" path="{p}" id="{i + 1}"]\n'
    if ext:
        head += '\n'
    return head + '[resource]\n' + '\n'.join(props) + '\n'


def write_all(root: str) -> None:
    out = os.path.join(root, 'art', 'materials')
    os.makedirs(out, exist_ok=True)
    for name, m in MATERIALS.items():
        txt = render(name, m)
        for line in txt.splitlines():
            if line.startswith('[ext_resource'):
                p = line.split('path="')[1].split('"')[0].replace('res://', '')
                if not os.path.exists(os.path.join(root, p)):
                    raise SystemExit(f'{name}: missing texture {p}')
        open(os.path.join(out, name + '.tres'), 'w').write(txt)
    existing = {f[:-5] for f in os.listdir(out) if f.endswith('.tres')}
    missing = existing - set(MATERIALS)
    if missing:
        raise SystemExit(f'materials on disk not defined in the palette: {sorted(missing)}')
    print(f'wrote {len(MATERIALS)} materials to art/materials/')


def palette_markdown() -> str:
    rows = ['| Material | What it is | Mapping | Metres per tile (W x H) | Notes |',
            '|---|---|---|---|---|']
    for name, m in MATERIALS.items():
        tile = '-' if not m['tile'] else ('%g' % m['tile'][0] if m['tile'][0] == m['tile'][1]
                                          else '%g x %g' % m['tile'])
        mp = {'world': 'world triplanar', 'object': 'object triplanar', 'none': 'untextured'}[m['map']]
        new = ' **(new)**' if name in NEW_MATERIALS else ''
        rows.append(f'| `{name}`{new} | {m["desc"]} | {mp} | {tile} | {m.get("notes", "")} |')
    return '\n'.join(rows)
