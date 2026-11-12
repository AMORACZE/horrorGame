# art/ - material palette and generated textures

`art/materials/<name>.tres` is the house's fixed palette (see docs/ARCHITECTURE.md
section 9). Every file is a text `StandardMaterial3D`. Scenes reference these
paths; names are never renamed or removed, new ones may be added.
`art/textures/<set>/` holds the procedurally generated maps they use.

Everything here is produced by `tools/gen_textures.py` (numpy + Pillow, no
external images): the textures **and** the `.tres` files. Edit material
parameters in `tools/texture_gen/materials.py`, not in the `.tres` files, or
the next regeneration will overwrite your change.

## Palette

Mapping: **world triplanar** = `uv1_triplanar` + `uv1_world_triplanar`, for
architecture. **object triplanar** = `uv1_triplanar` in mesh space, for props,
furniture and fixtures. `uv1_scale` is `1 / metres-per-tile`, so a texture
means "this many metres per repeat" on any box regardless of its size.

| Material | What it is | Mapping | Metres per tile (W x H) | Notes |
|---|---|---|---|---|
| `wall_wood_paneling` | 1970s random-groove walnut-look plywood panelling, satin; one 4x8 ft sheet per tile, grooves vertical | world triplanar | 1.22 x 2.44 | Tile is one full sheet: 1.22 m wide, 2.44 m tall (= ceiling), anchored at y=0; scuffs near the floor, smudges at hand height. |
| `carpet_shag_gold` | Deep gold/orange shag pile with matted traffic areas | world triplanar | 0.75 | Floors only. Rim term fakes fibre sheen at grazing angles. |
| `carpet_beige` | Beige cut-pile wall-to-wall carpet (1990s bedrooms/halls) | world triplanar | 0.5 |  |
| `floor_hardwood` | 2-1/4" red-oak strip floor, amber finish worn in traffic paths | world triplanar | 1.2 | Strips run along world Z. Build rooms so the long axis is Z, or use it as is (strips across the room are also period-correct). |
| `floor_hardwood_dusty` **(new)** | Same strip floor under a film of dust (unused rooms, attic, under furniture) | world triplanar | 1.2 |  |
| `linoleum_kitchen` | 1970s sheet vinyl: gold eight-point star medallions, brown/cream, 12" repeat, worn gloss | world triplanar | 0.61 | 2 x 2 motifs per tile. |
| `tile_bathroom` | 4-1/4" glazed seafoam ceramic wall/floor tile with dingy grout | world triplanar | 0.864 | 8 x 8 tiles per tile; grout lines align to world 0, so tile edges line up across walls. |
| `ceiling_popcorn` | Sprayed "popcorn" acoustic ceiling, nicotine-yellowed | world triplanar | 0.6 |  |
| `ceiling_popcorn_stained` **(new)** | Popcorn ceiling with old water-leak tide marks and smoke | world triplanar | 2.4 | One stain per 2.4 m tile, centred, clean edges: use on a 2.4 x 2.4 m patch aligned to multiples of 2.4 m (or accept a stain every 2.4 m on a whole ceiling). Coarser spray than ceiling_popcorn. |
| `wall_plaster_cream` | Painted drywall, roller stipple, cream paint yellowed by smoke | world triplanar | 1.22 x 2.44 | Height-anchored (y=0 floor): darker near the ceiling, scuffs near the floor, hand smudges ~1.1 m. |
| `wallpaper_floral` | 1980s small floral wallpaper: dusty-rose sprigs, sage leaves on cream, half-drop | world triplanar | 0.533 | Tile = one 21" roll width; roll seam at tile edge. |
| `wallpaper_stripe` | 1980s pastel regency stripe (rose / cream / sage-blue) with pearl-glaze cream bands | world triplanar | 0.533 |  |
| `brick_red` | Common red brick, running bond, recessed grey mortar (fireplace, exterior) | world triplanar | 0.852 x 0.804 | 4 bricks x 12 courses per tile (203 x 57 mm brick, 10 mm joints). |
| `trim_white` | Baseboards, casings, doors: oil gloss enamel gone ivory | world triplanar | 0.5 |  |
| `concrete` **(new)** | Cast concrete slab: garage, basement, steps, foundation | world triplanar | 1.5 |  |
| `glass_window` | Clean window glass (alpha blend: no shadow, sun passes) | untextured | - | Alpha-blended surfaces do not render into the shadow map, so sunlight passes and casts the window frame shadow only. Set cast_shadow = OFF and gi_mode = Disabled on the glass MeshInstance3D anyway (SDFGI would otherwise treat it as a wall). |
| `window_blown_out` **(new)** | Over-exposed exterior backdrop card (sky, hedge, lawn) for outside windows | world triplanar | 4 x 4.88 | Emissive, alpha-pass (casts no shadow, so it can sit in the sun path). Anchored to y=0 = ground. Place 1-3 m outside the glass; glow blooms it. |
| `wood_dark` | Dark walnut-stained furniture wood (70s case goods, frames) | object triplanar | 0.5 | Grain runs along local Y on sides and local Z on tops. |
| `wood_medium` | Medium "fruitwood/pecan" stained furniture wood | object triplanar | 0.5 |  |
| `wood_light` | Light maple/pine furniture wood | object triplanar | 0.5 |  |
| `wood_oak_cabinet` | 1980s golden-oak cabinet doors and boxes, open-pore grain, satin | object triplanar | 0.6 |  |
| `laminate_formica` | Beige gold-fleck laminate countertop, knife marks | object triplanar | 0.3 |  |
| `plastic_beige` | Yellowed beige ABS (computers, phones, VCR, radios) with moulded stipple | object triplanar | 0.2 |  |
| `plastic_white` | Off-white moulded plastic | object triplanar | 0.2 |  |
| `plastic_grey` | Mid grey moulded plastic | object triplanar | 0.2 |  |
| `plastic_black` | Black moulded plastic (TV, VCR, tape cases) | object triplanar | 0.2 |  |
| `metal_brass` | Lacquered brass gone slightly tarnished (lamps, knobs, fireplace tools) | object triplanar | 0.3 |  |
| `metal_chrome` | Chrome plate with smudges and fingerprints (taps, toaster, chair legs) | object triplanar | 0.3 |  |
| `metal_dark` | Dark cast iron / blued steel with rust specks | object triplanar | 0.3 |  |
| `metal_painted_white` | White baked enamel on steel (fridge sides, radiators, washer) | object triplanar | 0.4 |  |
| `appliance_harvest_gold` | Harvest Gold appliance enamel, glossy with orange-peel | object triplanar | 0.4 |  |
| `appliance_avocado` | Avocado Green appliance enamel, glossy with orange-peel | object triplanar | 0.4 |  |
| `fabric_floral_sofa` | 1980s floral upholstery: dusty rose/mauve blooms, teal-sage leaves, oatmeal basket weave | object triplanar | 0.6 |  |
| `fabric_corduroy_brown` | Brown wide-wale corduroy (4 mm wales, vertical on sides) | object triplanar | 0.2 |  |
| `fabric_plaid` | Brown / rust / mustard / cream tartan in 2/2 twill (recliner, blanket) | object triplanar | 0.25 |  |
| `fabric_lampshade` | Slubby cream linen lampshade, glows when lit from inside | object triplanar | 0.15 | Two-sided with backlight: a lamp inside lights the outside. Use an open cylinder (no caps). |
| `fabric_curtain_sheer` | Ivory voile sheer curtain: soft vertical folds, light passes through | object triplanar | 0.6 | Alpha blend + backlight: glows warmly with the sun behind it; casts no shadow (alpha pass), so the sun shaft still reaches the floor. Avoid stacking several sheers in a row (blend sorting). |
| `fabric_curtain_heavy` | Lined harvest-gold slub-weave drapes with deep pleats | object triplanar | 0.6 | Opaque (casts full shadow). Faint warm backlight for sun bleeding through the edges. |
| `leather_brown` | Brown leather (recliner, belt, wallet): pebble grain, creases, rubbed patina | object triplanar | 0.25 |  |
| `rubber_black` | Black rubber with grey bloom (feet, hoses, cords) | object triplanar | 0.15 |  |
| `dust_sheet` **(new)** | Unbleached muslin drop cloth thrown over furniture | object triplanar | 0.5 |  |
| `glass_dusty` | Grimy glass (cabinet doors, picture frames, garage window) | object triplanar | 0.5 | Alpha blend; no shadow. Dust film modulates both opacity and roughness. |
| `crt_screen_off` | Switched-off CRT: dark grey-green phosphor glass with a soft reflection | untextured | - |  |
| `mirror` **(new)** | Silvered mirror glass | untextured | - | Needs a ReflectionProbe (or SSR) in the room to reflect anything but the sky. |
| `ceramic_white` | Glazed white ceramic (mugs, sink, toilet, lamp base) with faint crazing | object triplanar | 0.2 |  |
| `paper_white` | White paper (letters, notes, mail) | object triplanar | 0.3 |  |
| `paper_yellowed` | Yellowed, foxed paper (old books, newspapers) | object triplanar | 0.3 |  |
| `cardboard` | Kraft corrugated cardboard, flutes along local X (ridges every 8 mm) | object triplanar | 0.3 |  |
| `plant_green` | Dense houseplant foliage (pothos/philodendron) for sphere/blob plants | object triplanar | 0.3 |  |
| `book_cover_a` | Cloth-bound book: oxblood | object triplanar | 0.1 |  |
| `book_cover_b` | Cloth-bound book: navy | object triplanar | 0.1 |  |
| `book_cover_c` | Cloth-bound book: bottle green | object triplanar | 0.1 |  |
| `book_cover_d` | Cloth-bound book: tan | object triplanar | 0.1 |  |


**New in this pass:** `floor_hardwood_dusty`, `ceiling_popcorn_stained`,
`concrete`, `window_blown_out`, `mirror`, `dust_sheet`.

## Texture sets

Each set in `art/textures/<set>/` has up to three 8-bit PNGs:

| file | content |
|---|---|
| `<set>_albedo.png` | sRGB base colour (RGBA where the material is alpha-blended) |
| `<set>_normal.png` | tangent-space normal map, **OpenGL convention** (green = +Y up), as Godot expects |
| `<set>_orm.png` | R = ambient occlusion, G = roughness, B = metallic |

Materials use the ORM file three times (`ao_texture` channel R,
`roughness_texture` channel G, `metallic_texture` channel B), so it is one
texture in memory. Large surfaces are 1024 px, props 512 px. Variants share
maps: `wood_dark/medium/light` share `wood_furniture` normal+ORM, the plastics
share `plastic`, the enamels share `enamel`, the books share `book_cloth`,
paper shares `paper`, `floor_hardwood_dusty` reuses the `floor_hardwood`
normal. Total: 117 PNGs, about 54 MB.

Every PNG has a committed `.import` asking for VRAM compression (S3TC/BPTC),
mipmaps, and the normal-map flag on normals. Heights are modelled in
millimetres against the real pixel size, so normal maps are physically scaled
and most materials use `normal_scale = 1`.

### How the generator works (tools/texture_gen/)

* `core.py` - periodic primitives: lattice value noise / fBm with integer
  cell counts, FFT (circular) gaussian blur, 1/f spectral noise, periodic Worley,
  domain warp, height -> normal (OpenGL), cavity AO, and the low-frequency
  `age()` overlay (nicotine yellowing, sun fade, grime; 2-3 cells per tile so
  repeats do not show). Because every operation wraps, every texture is
  seamless by construction.
* `draw.py` - wrapped SDF stamping (leaves, petals, ellipses, segments),
  z-buffered capsule strands (shag and cut-pile carpet tufts, curled in
  segments, frayed tips) and a weave synthesiser (plain, 2/2 twill, basket;
  per-thread colours make tartan the way a loom does).
* `wood.py` - grain from a virtual log: each board is a plane sliced at a depth
  from the pith, ring radius `sqrt((u-uc)^2 + d^2)` + taper + warp, with an
  irregular ring-width table, giving straight grain at the edges and cathedral
  arches over the heart. Used by panelling, strip floor, furniture woods and oak.
* `arch.py` - architectural sets; `props.py` - prop sets; `materials.py` - the
  palette (descriptions, metres per tile, shading parameters) and the `.tres`
  writer.

## Regenerating

```
python3 tools/gen_textures.py                    # everything (~3.5 min), deterministic
python3 tools/gen_textures.py --only carpet_beige,linoleum_kitchen --preview
python3 tools/gen_textures.py --materials-only   # rewrite the .tres files only
python3 tools/gen_textures.py --check            # seam test on every PNG + total size
godot --headless --audio-driver Dummy --path . --import
```

`--preview` writes a lit 3x3 tiled preview and a 1:1 crop per set to
`_shots/tex/` (ignored by git). Each set has its own named seed, so
regenerating one set never changes another, and a full run reproduces the
committed PNGs bit for bit.

`--check` compares the mean jump across the wrap seam with the largest jump
between neighbouring interior rows/columns. Three sets are allowed a seam by
design: `window_blown_out` (sky above, lawn below: only tiles horizontally),
and the wallpapers (a roll seam is drawn at the tile edge, i.e. every 533 mm,
like real paper).

## Gallery

`tests/art/material_gallery.tscn` builds a test bed at runtime: wall + floor
bays for the architectural materials under a low raking sun (bay 0 adds an
X-facing panelled side wall), two lamp-lit ceiling slabs, a window bay
(sun through glass, sheer and heavy curtains, blown-out card outside) and a
cube + sphere per material in a grid. Screenshots:

```
xvfb-run -a godot --audio-driver Dummy --path . --resolution 960x540 \
  -s res://tools/capture.gd -- --scene=res://tests/art/material_gallery.tscn \
  --out=_shots/m.png --wait=2 --gcam=1.2,1.6,3.0,-0.6,1.0,0.2,60
```

`--gcam=px,py,pz,lx,ly,lz[,fov]` places the gallery's own camera;
`--gonly=a,b,c` builds only those materials in the grid (much faster).
Reference shots are in `tests/art/reference/`.

## Guidance for prop and level builders

* **Architecture (walls, floors, ceilings, trim, brick, tile)**: world
  triplanar. Adjacent boxes line up seamlessly, and you can make walls any
  size. Build wall boxes axis-aligned and size them with `BoxMesh.size` /
  CSG size rather than rotating a box by 90 degrees: the triplanar tangent
  frame comes from the mesh's local axes, so a wall rotated by -90 degrees
  gets its normal-map lighting mirrored (grooves look lit from the wrong side).
* **Wall height anchoring**: `wall_wood_paneling` and `wall_plaster_cream`
  tile once per 2.44 m vertically and assume the ground floor is at y = 0
  (scuffs near the floor, hand smudges around 1.1 m, more nicotine near the
  ceiling). The ramps fade out at the tile boundary, so a stairwell wall that
  runs through two storeys has no seam, just a repeat. If a floor level sits
  at a height that is not a multiple of 2.44 m the wear bands shift; it is
  subtle, but a different storey can use its own copy of the material with
  `uv1_offset.y` set.
* **Floors**: `floor_hardwood` strips and `carpet_*` are designed for the top
  faces. Strip flooring runs along world Z.
* **Props, furniture, fixtures**: object triplanar, so textures stay glued to
  the object when it moves (drawers, doors, picked-up props) or is rotated.
  Do **not** use node `scale` to size a prop: it stretches the texture. Use
  the mesh size. Wood grain runs along local Y on side faces and along local Z
  on top faces: model long boards (table tops, shelves) along Z, or rotate
  the node; vertical members (legs, uprights) are always right.
* **Sofa and chairs**: `fabric_floral_sofa` has 18 cm blooms (one repeat per
  0.6 m), so a seat cushion shows one or two flowers. Use `fabric_corduroy_brown`
  / `fabric_plaid` for the 70s recliner, `leather_brown` for the 80s one.
* **Windows**: glass box with `glass_window`, `cast_shadow = OFF`,
  `gi_mode = DISABLED`. Alpha-blended materials never cast shadows in Godot,
  so the sun passes through glass, sheers and the backdrop card: only the
  frame, muntins and opaque curtains cast shadows. Put a `window_blown_out`
  box 1-3 m outside each window (also `cast_shadow = OFF`, `gi_mode =
  DISABLED`); it is emissive and alpha-pass, so it blooms and never blocks
  the sun.
* **Curtains**: `fabric_curtain_sheer` is alpha-blended, two-sided and
  backlit (glows with the sun behind it; no shadow). Do not put two sheers
  behind each other along a view direction (blend sorting is per object).
  `fabric_curtain_heavy` is opaque with pleats baked into the normal map;
  use flat boxes about 5 cm thick.
* **Lamps**: `fabric_lampshade` is two-sided and backlit; use an open
  `CylinderMesh` (no caps) around the lamp's light, and turn the shade's
  `cast_shadow` off if you want the bulb's light to leave the shade.
* **Mirror / CRT**: untextured, glossy. They show the sky unless the room has
  a `ReflectionProbe` (recommended for the bathroom mirror and the TV).
* **Stained ceiling**: one leak stain per 2.4 m tile, centred: place a
  2.4 x 2.4 m patch box aligned to multiples of 2.4 m in X and Z (e.g. centred
  at x = 1.2 + 2.4 k), just below the main ceiling surface.
* **Tints**: the shared-map materials (plastics, enamels, books) take their
  colour from `albedo_color`; a new colour variant is a new `.tres` entry in
  `materials.py` with a different `color`, no new textures needed.

## Swapping in scanned / painted textures later

Keep the file names and channel layout and nothing else needs to change:

1. Replace `art/textures/<set>/<set>_albedo.png` (sRGB), `_normal.png`
   (OpenGL / +Y green; flip green on DirectX maps, or set
   `process/normal_map_invert_y=true` in its `.import`) and `_orm.png`
   (AO, roughness, metallic in R, G, B). Keep the `.import` files.
2. If the scan covers a different real-world size, change that material's
   `tile` (metres per repeat) in `tools/texture_gen/materials.py` and run
   `python3 tools/gen_textures.py --materials-only`, or edit `uv1_scale`
   (= 1 / metres) in the `.tres` directly.
3. Remove the set from `REGISTRY` in `tools/texture_gen/arch.py` / `props.py`
   so a regeneration does not overwrite the scan.
4. Re-import: `godot --headless --audio-driver Dummy --path . --import`.

A scan with non-tileable lighting should be made seamless and de-lit first;
triplanar mapping repeats it on every face.
