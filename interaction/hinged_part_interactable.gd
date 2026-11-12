class_name HingedPartInteractable
extends MovingPartInteractable
## A part that swings on a hinge: cabinet door, fridge door, lid, flap.
##
## The hinge line runs along `axis` through `pivot`, both in the moving body's
## local space at its closed pose. Positive `open_angle_degrees` follows the
## right-hand rule about `axis` (axis UP: counter-clockwise seen from above).

@export_group("Hinge")
@export var axis: Vector3 = Vector3.UP
## Point on the hinge line, body-local. Leave at zero if the body origin is on the hinge.
@export var pivot: Vector3 = Vector3.ZERO
@export_range(-180.0, 180.0, 0.5, "suffix:°") var open_angle_degrees: float = 100.0

## +1 or -1 multiplier on open_angle_degrees, chosen per opening by subclasses.
var _swing_sign: float = 1.0


func _init() -> void:
	open_sound = &"cabinet_open"
	close_sound = &"cabinet_close"
	open_profile = Profile.PUSH
	close_profile = Profile.LATCH


## Current hinge angle in degrees (signed).
func get_angle_degrees() -> float:
	return open_angle_degrees * _swing_sign * _value


func _pose_for(v: float) -> Transform3D:
	var ax := axis.normalized() if axis.length_squared() > 0.0 else Vector3.UP
	var rot := Basis(ax, deg_to_rad(open_angle_degrees * _swing_sign * v))
	var to_pivot := Transform3D(Basis.IDENTITY, pivot)
	return to_pivot * Transform3D(rot, Vector3.ZERO) * to_pivot.affine_inverse()
