class_name ExaminableInteractable
extends Interactable
## An object the player can pick up and turn over in their hands.
##
## Interacting emits `Events.examine_requested(self)`. The UI's examine view asks
## this component for a visual copy (`create_examine_visual`) and shows it in an
## isolated viewport, so the real object never leaves the world.

## Node whose meshes are shown in the examine view. Empty = the parent body.
@export var visual_root: NodePath
## Shown under the object's name in the examine view. Keep it short and concrete.
@export_multiline var description: String = ""
## Starting orientation in the examine view (degrees).
@export var examine_rotation_degrees: Vector3 = Vector3(-15.0, 30.0, 0.0)
## Extra scale applied in the examine view (the view auto-fits to bounds first).
@export var examine_scale: float = 1.0
## Sound ids played when the view opens / closes.
@export var pickup_sound: StringName = &"pickup"
@export var putdown_sound: StringName = &"putdown"


func _init() -> void:
	prompt = "Examine"


func _interact(_interactor: Node) -> void:
	Events.examine_requested.emit(self)


func get_visual_root() -> Node3D:
	if not visual_root.is_empty():
		var n := get_node_or_null(visual_root) as Node3D
		if n:
			return n
	return get_parent() as Node3D


## Builds a render-only copy of the object: just its meshes, centred on the
## origin, with no physics, scripts or components. Caller owns the result.
func create_examine_visual() -> Node3D:
	var src := get_visual_root()
	var out := Node3D.new()
	out.name = "ExamineVisual"
	if src == null:
		return out
	var inv := src.global_transform.affine_inverse()
	var bounds := AABB()
	var first := true
	for mi: MeshInstance3D in _collect_meshes(src):
		if mi.mesh == null or not mi.visible:
			continue
		var copy := MeshInstance3D.new()
		copy.mesh = mi.mesh
		copy.material_override = mi.material_override
		for s in mi.get_surface_override_material_count():
			copy.set_surface_override_material(s, mi.get_surface_override_material(s))
		copy.transform = inv * mi.global_transform
		out.add_child(copy)
		var box := copy.transform * mi.mesh.get_aabb()
		bounds = box if first else bounds.merge(box)
		first = false
	# Re-centre on the bounds so the object rotates about its middle.
	var centre := bounds.get_center()
	for c in out.get_children():
		(c as Node3D).position -= centre
	out.set_meta(&"bounds_radius", max(bounds.size.length() * 0.5, 0.01))
	return out


func _collect_meshes(node: Node) -> Array[MeshInstance3D]:
	var found: Array[MeshInstance3D] = []
	if node is MeshInstance3D:
		found.append(node)
	for child in node.get_children():
		found.append_array(_collect_meshes(child))
	return found
