class_name MovingPartInteractable
extends Interactable
## Shared base for parts that travel between a closed and an open pose:
## doors, cabinet doors, lids, drawers, sliding panels.
##
## Add as a child of the moving body (usually an AnimatableBody3D on layer 3,
## plus 1 if solid). The body's transform at _ready is the CLOSED pose; the
## subclass turns a 0..1 travel value into an offset from it (`_pose_for`).
##
## Motion is eased per direction, can be reversed mid-travel (the new move
## starts from wherever the part is), and stops short instead of pushing into
## anything on `block_mask` (the player by default), so a closing door never
## traps or launches anybody.

signal motion_started(opening: bool)
signal motion_finished(is_open: bool)
signal blocked(collider: Object)
signal unlocked

## Motion curves. PUSH: fast start, coasts to a stop (a door given a shove).
## LATCH: accelerates and arrives with speed, then rebounds by `stop_bump`
## (a drawer hitting its stop, a door catching its latch). SMOOTH: ease in-out.
enum Profile { SMOOTH, PUSH, LATCH, LINEAR }

@export_group("Motion")
## Node that moves. Empty = the parent body.
@export var target: NodePath
@export_range(0.05, 6.0, 0.01, "suffix:s") var open_duration: float = 0.6
@export_range(0.05, 6.0, 0.01, "suffix:s") var close_duration: float = 0.5
@export var open_profile: Profile = Profile.LATCH
@export var close_profile: Profile = Profile.LATCH
## Rebound at the end of a LATCH move, as a fraction of full travel.
@export_range(0.0, 0.1, 0.001) var stop_bump: float = 0.012
## Travel value at start: 0 = closed, 1 = fully open.
@export_range(0.0, 1.0, 0.01) var start_open_amount: float = 0.0
## Whether interacting during travel reverses it. Off = ignore until settled.
@export var interruptible: bool = true
## Spring-loaded parts (a VCR flap): close by themselves this long after opening. 0 = never.
@export_range(0.0, 10.0, 0.05, "suffix:s") var auto_close_after: float = 0.0

@export_group("Prompts")
@export var open_prompt: String = "Open"
@export var close_prompt: String = "Close"
@export var locked_prompt: String = "Try"

@export_group("Lock")
@export var locked: bool = false
## If set and Game.has_flag(required_flag), a locked part unlocks when used.
@export var required_flag: StringName = &""
## World flag set the first time this part is opened.
@export var opened_flag: StringName = &""
## Lines said on each locked attempt (advance, last repeats).
@export var locked_observations: Array[String] = []
## Small shake when trying a locked part, as a fraction of full travel.
@export_range(0.0, 0.05, 0.001) var locked_rattle: float = 0.006

@export_group("Sound")
@export var open_sound: StringName = &"drawer_open"
## Played when a closing move arrives (latch / bump), not when it starts.
@export var close_sound: StringName = &"drawer_close"
@export var locked_sound: StringName = &"door_locked"
@export var unlock_sound: StringName = &""
@export var blocked_sound: StringName = &"thud_soft"
@export var sound_volume_db: float = 0.0

@export_group("Safety")
## Physics layers the part refuses to move into (2 = player).
@export_flags_3d_physics var block_mask: int = 2

@export_group("Links")
## Switchables turned on while the part is open at all (fridge light).
@export var lit_while_open: Array[NodePath] = []
## Say each `observations` line once, on successive openings, then stay quiet.
@export var observe_on_open: bool = true

var _body: Node3D = null
var _rest: Transform3D = Transform3D.IDENTITY
var _value: float = 0.0
var _goal: float = 0.0
var _from: float = 0.0
var _elapsed: float = 0.0
var _move_time: float = 0.0
var _moving: bool = false
var _moving_profile: Profile = Profile.LATCH
var _rattle_t: float = -1.0
var _locked_index: int = 0
var _fresh_index: int = 0
var _was_opened: bool = false
var _shapes: Array[CollisionShape3D] = []
var _query: PhysicsShapeQueryParameters3D = null
var _move_serial: int = 0
## Set when a move was stopped short: the next use reverses it.
var _stopped_opening: bool = false


func _ready() -> void:
	_body = (get_node_or_null(target) if not target.is_empty() else get_parent()) as Node3D
	if _body == null:
		push_warning("%s: no target body to move" % get_path())
		set_physics_process(false)
		return
	_rest = _body.transform
	for c in _body.get_children():
		if c is CollisionShape3D and (c as CollisionShape3D).shape != null:
			_shapes.append(c)
	_value = start_open_amount
	_goal = _value
	_apply(_value)
	_update_links()
	set_physics_process(false)


# --- Public API ----------------------------------------------------------------

## True while the part is physically away from closed.
func is_open() -> bool:
	return _value > 0.01


## True while travelling.
func is_moving() -> bool:
	return _moving or _rattle_t >= 0.0


## Current travel 0..1.
func get_open_amount() -> float:
	return _value


## Where the current/last move is heading, 0..1.
func get_goal() -> float:
	return _goal


func is_locked() -> bool:
	return locked


func set_locked(value: bool) -> void:
	locked = value


func open() -> void:
	move_to(1.0)


func close() -> void:
	move_to(0.0)


## Start travelling to `amount` (0..1) from wherever the part is now.
func move_to(amount: float) -> void:
	amount = clampf(amount, 0.0, 1.0)
	if _body == null:
		return
	var opening := amount > _value
	_from = _value
	_goal = amount
	_elapsed = 0.0
	var base_time := open_duration if opening else close_duration
	_move_time = maxf(base_time * sqrt(absf(_goal - _from)), 0.05)
	_moving_profile = open_profile if opening else close_profile
	_moving = not is_equal_approx(_goal, _from)
	_move_serial += 1
	_stopped_opening = false
	if opening:
		_on_open_started()
	motion_started.emit(opening)
	_update_links()
	set_physics_process(true)


## Jump to a travel value with no motion or sound (level setup, tests).
func snap_to(amount: float) -> void:
	_value = clampf(amount, 0.0, 1.0)
	_goal = _value
	_moving = false
	_apply(_value)
	_update_links()


func get_prompt() -> String:
	if locked and _locked_index > 0 and not _can_unlock():
		return locked_prompt
	return close_prompt if _next_is_close() else open_prompt


func can_interact(interactor: Node) -> bool:
	if not super.can_interact(interactor):
		return false
	return interruptible or not _moving


# --- Interaction ---------------------------------------------------------------

func _interact(interactor: Node) -> void:
	if locked:
		if _can_unlock():
			locked = false
			_play(unlock_sound)
			unlocked.emit()
		else:
			_try_locked()
			return
	if _next_is_close():
		close()
	else:
		_prepare_open(interactor)
		open()


## What using the part does next: full open / blocked mid-opening -> close;
## shut / ajar / blocked mid-closing -> open.
func _next_is_close() -> bool:
	if _goal >= 0.999:
		return true
	if _goal <= 0.001:
		return false
	return _stopped_opening


## Hook for subclasses to pick a swing direction before opening.
func _prepare_open(_interactor: Node) -> void:
	pass


func _can_unlock() -> bool:
	return required_flag != &"" and Game.has_flag(required_flag)


func _try_locked() -> void:
	_play(locked_sound)
	if not locked_observations.is_empty():
		say(locked_observations[mini(_locked_index, locked_observations.size() - 1)])
	_locked_index += 1
	if locked_rattle > 0.0 and not _moving:
		_rattle_t = 0.0
		set_physics_process(true)


func _on_open_started() -> void:
	if not _was_opened or _from < 0.01:
		_play(open_sound)
	if opened_flag != &"" and not _was_opened:
		Game.set_flag(opened_flag, true)
	_was_opened = true
	if observe_on_open and _fresh_index < observations.size():
		var line := observations[_fresh_index]
		_fresh_index += 1
		if line.strip_edges() != "":
			say(line)


# --- Motion --------------------------------------------------------------------

func _physics_process(delta: float) -> void:
	if _moving:
		_elapsed += delta
		var u := clampf(_elapsed / _move_time, 0.0, 1.0)
		var next := lerpf(_from, _goal, _curve(_moving_profile, u))
		if _would_block(next):
			_stop_blocked()
			return
		var before := _value
		_value = next
		_apply(_value)
		_on_travel(before, _value, u)
		if u >= 1.0:
			_value = _goal
			_apply(_value)
			_moving = false
			_arrive()
	elif _rattle_t >= 0.0:
		_rattle_t += delta
		var k := _rattle_t / 0.3
		if k >= 1.0:
			_rattle_t = -1.0
			_apply(_value)
		else:
			var off := locked_rattle * sin(_rattle_t * 55.0) * (1.0 - k)
			_apply(clampf(_value + absf(off), 0.0, 1.0))
	if not _moving and _rattle_t < 0.0:
		set_physics_process(false)


func _arrive() -> void:
	if _goal <= 0.001:
		_play(close_sound)
	elif _goal >= 0.999 and auto_close_after > 0.0 and is_inside_tree():
		var serial := _move_serial
		get_tree().create_timer(auto_close_after, false).timeout.connect(func() -> void:
			if serial == _move_serial and is_inside_tree():
				close())
	_update_links()
	motion_finished.emit(is_open())


## Called every motion step; subclasses add mid-travel sounds (creaks).
func _on_travel(_before: float, _after: float, _u: float) -> void:
	pass


func _stop_blocked() -> void:
	_stopped_opening = _goal > _from
	_moving = false
	_goal = _value
	_play(blocked_sound, -6.0)
	_update_links()
	blocked.emit(null)
	motion_finished.emit(is_open())


func _would_block(next_value: float) -> bool:
	if block_mask == 0 or _shapes.is_empty() or not _body.is_inside_tree():
		return false
	var parent := _body.get_parent() as Node3D
	var parent_xf := parent.global_transform if parent else Transform3D.IDENTITY
	var body_xf := parent_xf * (_rest * _pose_for(next_value))
	var space := _body.get_world_3d().direct_space_state
	if _query == null:
		_query = PhysicsShapeQueryParameters3D.new()
		_query.collide_with_areas = false
		_query.collide_with_bodies = true
		var co := _body as CollisionObject3D
		if co:
			_query.exclude = [co.get_rid()]
	_query.collision_mask = block_mask
	for cs in _shapes:
		if cs.disabled:
			continue
		_query.shape = cs.shape
		_query.transform = body_xf * cs.transform
		if not space.intersect_shape(_query, 1).is_empty():
			return true
	return false


func _apply(value: float) -> void:
	if _body:
		_body.transform = _rest * _pose_for(value)


## Override: the offset from the closed pose (body-local) at travel `value`.
func _pose_for(_v: float) -> Transform3D:
	return Transform3D.IDENTITY


func _update_links() -> void:
	var lit := _value > 0.01 or _goal > 0.01
	for p in lit_while_open:
		var s := Switchable.resolve(get_node_or_null(p))
		if s:
			s.set_on(lit)


func _play(id: StringName, extra_db: float = 0.0) -> void:
	if id == &"" or _body == null or not _body.is_inside_tree():
		return
	Audio.play_attached(id, _body, sound_volume_db + extra_db, randf_range(0.96, 1.04))


func _curve(profile: Profile, u: float) -> float:
	match profile:
		Profile.LINEAR:
			return u
		Profile.SMOOTH:
			return u * u * (3.0 - 2.0 * u)
		Profile.PUSH:
			var a := u * u * (3.0 - 2.0 * u)
			var b := 1.0 - pow(1.0 - u, 3.0)
			return lerpf(a, b, u)
		_:
			const IMPACT := 0.86
			if u < IMPACT:
				var v := u / IMPACT
				return v * v * (2.0 - v)
			var w := (u - IMPACT) / (1.0 - IMPACT)
			# Rebound back toward the start by stop_bump of the move, then settle.
			var span := maxf(absf(_goal - _from), 0.0001)
			return 1.0 - (stop_bump / span) * sin(PI * w) * (1.0 - w)
