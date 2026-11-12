# Atmosphere

Late-August afternoon light, hazy air, dust, and the camcorder that sees it.
Reference renders (software Vulkan, 960x540): `tests/atmosphere/reference/`.

| File | What |
|---|---|
| `afternoon_atmosphere.tscn` | The lighting rig. Root `Atmosphere` (`AfternoonAtmosphere`): `WorldEnvironment` + `Sun`. One per level. |
| `environments/afternoon.tres` | The shared Environment (sky, GI, fog, glow, grade). |
| `environments/camcorder_exposure.tres` | CameraAttributesPractical: the camcorder auto-iris. |
| `dust_motes.tscn` | `DustMotes` (GPUParticles3D): a box of drifting dust lit only by direct light. |
| `haze_volume.tscn` | `HazeVolume` (FogVolume): locally thicker air. |
| `post_fx.tscn` | `PostFx` CanvasLayer 50: VHS shader over everything + OSD (CanvasLayer 40). Instanced by `main.gd`. |
| `shaders/vhs.gdshader` | The tape. |
| `shaders/dust_mote.gdshader` | Mote billboards. |
| `osd/camcorder_osd.gd`, `osd/osd_font.gd` | Viewfinder display and its original 5x7 character set (drawn as rects). |

Sandbox: `tests/atmosphere/sunroom.tscn` (5 x 4 m room, west + south windows,
regenerate with `tests/atmosphere/tools/gen_sunroom.py`) and
`tests/atmosphere/vhs_pattern.tscn` (test card under the real post-fx).
Automated check: `godot --headless --audio-driver Dummy --path . -s res://tests/atmosphere/test_atmosphere.gd`.

## Using it in a level

```
House (Node3D)
├─ Atmosphere      ← instance afternoon_atmosphere.tscn (exactly one)
├─ Geometry ...
├─ DustLivingWest  ← dust_motes.tscn, box covering the west window's shaft
├─ HazeLivingWest  ← haze_volume.tscn, just inside the same window
└─ ...
```

Knobs on the `Atmosphere` root (all live in the editor; they edit private
copies, so the shared `.tres` files are never dirtied by a level):

| Knob | Default | Notes |
|---|---|---|
| `sun_azimuth` | 250 | Compass bearing the light comes FROM (0 N/-Z, 90 E/+X, 180 S/+Z, 270 W/-X). |
| `sun_elevation` | 37 | Degrees. Lower = longer shafts, more raking floor light. |
| `sun_energy` | 3.2 | Everything (patches, shafts, bounce) scales with it. |
| `haze_amount` | 1.0 | Multiplies global volumetric haze and distance haze. 0 clear .. 2 dusty. |
| `exposure_bias` | 0 EV | Shifts the auto-iris target. (A plain exposure multiplier would just be cancelled by auto-exposure.) |
| `fog_volume_size/depth` | 160 / 128 | Global froxel grid, applied at runtime. Lower on weak GPUs. |

The sun node is the DirectionalLight3D named `Sun` (`get_sun()`); the rig sets
its rotation from the knobs, so do not rotate it by hand.

## Final values and why

**Sun.** Colour (1, .88, .72), energy 3.2, angular size 0.6 deg (soft but
still sharp-edged window patches), PSSM 4 splits at 6/15/35 % of 40 m with
blend, bias .04 / normal bias .8. 40 m max distance keeps the first split
(2.4 m) dense enough for muntin shadows on the floor.

**GI: SDFGI**, min cell **0.10 m**, 4 cascades (6.4 m .. 51 m), Y scale 100 %,
occlusion on, bounce feedback .8, energy 2.5, **read sky light off**.
- 0.125 m cells gave bright seams along wall/ceiling junctions; 0.10 m fixed
  them for 0.30 m walls (3 cells).
- Reading sky light let a thin bright band leak along one wall/ceiling
  junction no matter the bias settings. With it off, interiors are lit by the
  sun's bounce (floor patches, the sunlit lawn outside the window), which is
  what the reference light looks like anyway: warm bounce, deep shade.
  Consequence: a room with no sunlit surface in or near it is dark (see
  guidance below).
- Y scale 75 % produced large green leaks from the lawn: keep 100 %.

**Haze.** Volumetric fog density .02, albedo warm (.95, .90, .82),
anisotropy .4, GI inject .08 (a little thick air in the shade, more makes
the room milky), ambient inject 0, sky affect 0, length **14 m** (concentrates
froxels inside the house), temporal reprojection .9. Sun volumetric energy 4.
The default 64 x 64 froxel grid draws visible streaks radiating from the view
centre in small rooms; 160 x 128 is clean. Distance haze outside uses depth
fog starting at 14 m (exponential fog washed out the whole interior).

**Exposure / camcorder iris.** Auto exposure on, target scale 2.2, speed .5
(about a 2 s time constant), sensitivity 8 .. 3200 (internally a luminance
clamp of .01 .. 4). The low end lets a shaded room open up; the high end lets
a window shot darken the room so the window holds a little detail. Godot's
auto-exposure measures after `exposure_multiplier` and `tonemap_exposure`, so
those do almost nothing while it is on; tune `auto_exposure_scale` instead.

**Tone.** AgX, white 8 (the default 16.3 compresses so much that exposure
changes barely show), contrast 1.1, then adjustments: contrast .97, saturation
.92 and a 1D grade (`Tex_grade`): blacks lifted a hair and slightly cool,
highlights cream (.985, .955, .89).

**SSAO** radius .9, intensity 1.6, light affect .15. **SSIL** radius 2.5,
intensity .7. **Glow** levels 3–5, intensity .18, HDR threshold 1.5: windows
and sun patches bloom; at .25+ together with the forward-scattering haze the
window wall turns to milk.

**Dust.** 40 motes/m3, 6 mm, 18 s lifetime, pre-warmed, fades in/out over
15 % of life (no popping), never drawn smaller than 1.75 px (fades instead, so
far dust does not crawl), additive, lit only by direct light with a
forward-scattering phase (bright looking toward the sun, gone in shade).

**VHS** (`shaders/vhs.gdshader`, every term scaled by `intensity`): luma blur
sigma .09 % of width + .45 halo, chroma blur .5 % of width shifted right .22 %
and averaged with the line above, line-wise luma noise .045 weighted to the
shadows, chroma noise .022, line wander .045 %, scanlines 3 % on a pixel-locked
grid (no moire), head-switching tear in the bottom 1.1 %, dropouts about one
every 11 s, blacks at .045, highlight knee .78, saturation .9, a slight warm
cast with cool/magenta shadows, 22 % lens vignette. Zoom: an autofocus hunt
(blur that overshoots and settles in ~1 s) and up to +80 % tape noise at full
tele. All exposed as uniforms in the `tuning` group.

## Guidance for the level builder

- **Walls 0.30 m (exterior), floors/ceilings 0.30 m.** SDFGI needs at least
  ~3 cells (0.3 m) to stop light. 0.15 m interior walls are fine between two
  interior rooms but do not put a sunlit exterior directly behind one.
- **Let walls overlap the floor and ceiling slabs** rather than just touch
  them, and avoid hairline gaps: SDFGI sees cracks.
- **Glass:** `cast_shadow = off` and `gi_mode = disabled` on every pane, or
  the window blocks the sun and the GI. Muntins/frames should cast shadows:
  they make the patterned floor patches.
- **Build some outside.** A sunlit ground plane (and a fence or the
  neighbour's wall) outside every window: it is what fills north-facing rooms
  with bounce now that GI does not read the sky, and it is what blows out in
  the glass.
- **Dust:** one `DustMotes` per sunlit window, box covering the volume the
  shaft crosses (from the window to where the patch lands, ~2–3 m into the
  room). Density 30–50. Nothing elsewhere: motes in shade are invisible
  anyway, and each box costs particles.
- **Haze:** one `HazeVolume` just inside each sunlit window, about the size of
  the shaft's first 2 m. `haze_density` .01–.02. Use a negative density to
  clear a corridor you want crisp. Keep `settle` 0 above the ground floor.
- **Reflection probes:** SDFGI already gives rough reflections. Add a
  `ReflectionProbe` (update once, box projection, interior on, ambient
  disabled) only in rooms with glossy floors (kitchen lino, bathroom tile),
  sized to the room.
- **Practical lamps** (OmniLight3D/SpotLight3D) light dust too. Give them
  `light_volumetric_fog_energy` .3–.6 or shades glow like fog lamps.
- **Avoid:** extra fill lights (the look depends on contrast), a second
  WorldEnvironment, a Camera3D `attributes` override (it would replace the
  camcorder iris), DirectionalLight3D other than `Sun`, huge FogVolumes with
  high density (the room turns to milk), very thin (< 0.2 m) roofs over lit
  rooms.
