@tool
class_name HazeVolume
extends FogVolume
## Locally thicker air: a soft-edged box of extra volumetric fog density, added
## on top of the global haze. Put one just inside each sunlit window so the shaft
## is strongest where it enters and thins out across the room. A negative
## density thins the air instead (e.g. a draughty hallway).

## Extra fog density inside the volume (global haze is 0.02).
@export_range(-0.1, 0.3, 0.001) var haze_density: float = 0.012:
	set(v):
		haze_density = v
		_apply()
## 0 = hard box edges, 1 = density fades all the way from the centre.
@export_range(0.0, 1.0, 0.01) var softness: float = 0.6:
	set(v):
		softness = v
		_apply()
## Density falloff with WORLD height (FogMaterial.height_falloff); > 0 settles
## the haze towards y = 0. Keep 0 on upper floors or the haze vanishes there.
@export_range(0.0, 4.0, 0.05) var settle: float = 0.0:
	set(v):
		settle = v
		_apply()
@export var haze_albedo: Color = Color(0.96, 0.91, 0.84):
	set(v):
		haze_albedo = v
		_apply()


func _ready() -> void:
	var fm := material as FogMaterial
	if fm == null or not fm.resource_local_to_scene:
		fm = (fm.duplicate() as FogMaterial) if fm != null else FogMaterial.new()
		material = fm
	_apply()


func _apply() -> void:
	var fm := material as FogMaterial
	if fm == null:
		return
	fm.density = haze_density
	fm.edge_fade = maxf(softness * 2.0, 0.01)
	fm.height_falloff = settle
	fm.albedo = haze_albedo
