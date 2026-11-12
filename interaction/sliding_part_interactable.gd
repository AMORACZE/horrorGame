class_name SlidingPartInteractable
extends MovingPartInteractable
## A part that slides along a straight line: drawer, sliding closet door, tray.
##
## `axis` is in the moving body's local space at its closed pose; the part
## travels `distance` metres along it.

@export_group("Slide")
@export var axis: Vector3 = Vector3.BACK
@export_range(0.0, 3.0, 0.005, "suffix:m") var distance: float = 0.35


func _init() -> void:
	open_sound = &"drawer_open"
	close_sound = &"drawer_close"
	open_profile = Profile.LATCH
	close_profile = Profile.LATCH


func _pose_for(v: float) -> Transform3D:
	var ax := axis.normalized() if axis.length_squared() > 0.0 else Vector3.BACK
	return Transform3D(Basis.IDENTITY, ax * distance * v)
