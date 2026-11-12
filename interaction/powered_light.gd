class_name PoweredLight
extends Switchable
## A practical light: lamp, ceiling dome, fan light kit, appliance bulb.
##
## Drives one or more Light3D nodes and the emissive look of the bulb and
## shade meshes together, so the glass glows exactly when the room is lit.
## Incandescent behaviour: the filament warms up over `warm_up_time` (colour
## rises from deep orange to `temperature_kelvin`) and fades on a slightly
## longer afterglow when switched off. The energy each Light3D has in the scene
## is its full brightness.

@export_group("Lights")
@export var lights: Array[NodePath] = []
## Multiplier on every light's scene energy.
@export_range(0.0, 8.0, 0.01) var brightness: float = 1.0

@export_group("Bulb")
@export_range(1000.0, 10000.0, 50.0, "suffix:K") var temperature_kelvin: float = 2700.0
## Filament colour when it first glows.
@export_range(800.0, 4000.0, 50.0, "suffix:K") var cold_kelvin: float = 1500.0
@export_range(0.0, 2.0, 0.01, "suffix:s") var warm_up_time: float = 0.12
@export_range(0.0, 3.0, 0.01, "suffix:s") var cool_down_time: float = 0.3
## Burnt out: switches click, nothing lights.
@export var dead_bulb: bool = false
@export var dead_observations: Array[String] = ["Nothing. The bulb must be gone."]

@export_group("Emissive")
## Meshes that glow hot (the bulb itself, frosted glass).
@export var bulb_meshes: Array[NodePath] = []
@export_range(0.0, 40.0, 0.1) var bulb_emission_energy: float = 6.0
## Meshes that glow softly by transmission (fabric shade).
@export var glow_meshes: Array[NodePath] = []
@export_range(0.0, 10.0, 0.05) var glow_emission_energy: float = 0.8

@export_group("Sound")
## Optional loop while lit (fluorescent `light_buzz`). Empty = silent.
@export var hum_sound: StringName = &""
@export var hum_volume_db: float = -14.0

var _level: float = 0.0
var _energies: Array[float] = []
var _lights: Array[Light3D] = []
var _bulb_mats: Array[Material] = []
var _glow_mats: Array[Material] = []
var _hum: AudioStreamPlayer3D = null
var _dead_index: int = 0


func _ready() -> void:
	for p in lights:
		var l := get_node_or_null(p) as Light3D
		if l:
			_lights.append(l)
			_energies.append(l.light_energy)
	for p in bulb_meshes:
		var m := _make_emissive(get_node_or_null(p) as GeometryInstance3D)
		if m:
			_bulb_mats.append(m)
	for p in glow_meshes:
		var m := _make_emissive(get_node_or_null(p) as GeometryInstance3D)
		if m:
			_glow_mats.append(m)
	if hum_sound != &"":
		var anchor := get_parent() as Node3D
		if anchor:
			_hum = LoopEmitter.create_player(anchor, hum_sound, hum_volume_db)
	super._ready()


func is_working() -> bool:
	return not dead_bulb


func get_failure_line() -> String:
	if dead_observations.is_empty():
		return ""
	var line := dead_observations[mini(_dead_index, dead_observations.size() - 1)]
	_dead_index += 1
	return line


## 0..1 filament level right now (1 = fully lit).
func get_level() -> float:
	return _level


## True when the light is actually emitting (on and working).
func is_lit() -> bool:
	return _on and not dead_bulb


func set_dead_bulb(dead: bool) -> void:
	dead_bulb = dead
	_switched(_on, false)


func _switched(_on_now: bool, instant: bool) -> void:
	var target := 1.0 if is_lit() else 0.0
	if instant:
		_level = target
		_show(_level)
		set_process(false)
	else:
		set_process(true)
	if _hum:
		LoopEmitter.set_playing(_hum, is_lit())


func _process(delta: float) -> void:
	var target := 1.0 if is_lit() else 0.0
	var tau := warm_up_time if target > _level else cool_down_time
	if tau <= 0.0:
		_level = target
	else:
		_level = lerpf(_level, target, 1.0 - exp(-delta * 3.0 / tau))
	if absf(_level - target) < 0.002:
		_level = target
		set_process(false)
	_show(_level)


func _show(level: float) -> void:
	# Filament: brightness rises steeply with temperature, so energy ~ level^2.
	var k := lerpf(cold_kelvin, temperature_kelvin, sqrt(level))
	var col := kelvin_to_color(k)
	var e := level * level
	for i in _lights.size():
		_lights[i].light_color = col
		_lights[i].light_energy = _energies[i] * brightness * e
		_lights[i].visible = level > 0.001
	for m in _bulb_mats:
		_set_emission(m, col, bulb_emission_energy * e)
	for m in _glow_mats:
		_set_emission(m, col, glow_emission_energy * e)


func _make_emissive(gi: GeometryInstance3D) -> Material:
	if gi == null:
		return null
	var src: Material = gi.material_override
	var mi := gi as MeshInstance3D
	if src == null and mi and mi.mesh and mi.mesh.get_surface_count() > 0:
		src = mi.get_active_material(0)
	var mat: Material = src.duplicate() if src else StandardMaterial3D.new()
	if mat is BaseMaterial3D:
		var bm := mat as BaseMaterial3D
		bm.emission_enabled = true
		bm.emission_energy_multiplier = 0.0
	gi.material_override = mat
	return mat


static func _set_emission(m: Material, col: Color, energy: float) -> void:
	if m is BaseMaterial3D:
		var bm := m as BaseMaterial3D
		bm.emission = col
		bm.emission_energy_multiplier = energy
	elif m is ShaderMaterial:
		(m as ShaderMaterial).set_shader_parameter(&"emission_color", col)
		(m as ShaderMaterial).set_shader_parameter(&"emission_energy", energy)


## Approximate black-body colour for a temperature in kelvin (1000..12000).
static func kelvin_to_color(kelvin: float) -> Color:
	var t := clampf(kelvin, 1000.0, 12000.0) / 100.0
	var r: float
	var g: float
	var b: float
	if t <= 66.0:
		r = 255.0
		g = 99.4708025861 * log(t) - 161.1195681661
	else:
		r = 329.698727446 * pow(t - 60.0, -0.1332047592)
		g = 288.1221695283 * pow(t - 60.0, -0.0755148492)
	if t >= 66.0:
		b = 255.0
	elif t <= 19.0:
		b = 0.0
	else:
		b = 138.5177312231 * log(t - 10.0) - 305.0447927307
	return Color(clampf(r, 0.0, 255.0) / 255.0, clampf(g, 0.0, 255.0) / 255.0, clampf(b, 0.0, 255.0) / 255.0)
