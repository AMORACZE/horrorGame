class_name SoundLibrary
extends RefCounted
## The sound table: id -> playback settings. Files are discovered, not listed.
##
## Every id has a folder `res://audio/sounds/<id>/`; every audio file in it
## (.wav / .ogg / .mp3) is a variant. To replace a sound with a recording, put
## your files in the folder (any names) and delete the generated `<id>_NN` ones.
## Footsteps use ids `footstep_<surface>`.
##
## Keys per entry (all optional; DEFAULTS fill the rest):
##   volume_db      base mix level applied on every play
##   volume_var_db  random +- spread per play (one-shots)
##   pitch_var      random +- pitch spread per play (fraction, 0.05 = 5 %)
##   loop           true for loops: the stream is forced to loop at load
##   bus            SFX | Footsteps | Ambience | UI
##   unit_size      AudioStreamPlayer3D.unit_size (metres at which it plays at volume_db)
##   max_distance   AudioStreamPlayer3D.max_distance
##   filter_hz      AudioStreamPlayer3D.attenuation_filter_cutoff_hz
##   filter_db      AudioStreamPlayer3D.attenuation_filter_db
##   polyphony      max_polyphony for the player (overlapping plays of one emitter)

const ROOT := "res://audio/sounds/"
const EXTENSIONS: PackedStringArray = ["wav", "ogg", "mp3"]

const DEFAULTS := {
	&"volume_db": 0.0,
	&"volume_var_db": 1.0,
	&"pitch_var": 0.04,
	&"loop": false,
	&"bus": &"SFX",
	&"unit_size": 2.5,
	&"max_distance": 20.0,
	&"filter_hz": 9000.0,
	&"filter_db": -12.0,
	&"polyphony": 1,
}

const FOOTSTEP_SURFACES: Array[StringName] = [&"wood", &"carpet", &"linoleum", &"tile", &"concrete", &"rug"]

const SOUNDS := {
	# --- footsteps (played through Audio.play_footstep) -------------------------
	&"footstep_wood": {&"bus": &"Footsteps", &"volume_db": -3.0, &"pitch_var": 0.06, &"volume_var_db": 1.5, &"unit_size": 2.0, &"max_distance": 16.0},
	&"footstep_carpet": {&"bus": &"Footsteps", &"volume_db": -2.0, &"pitch_var": 0.06, &"volume_var_db": 1.5, &"unit_size": 2.0, &"max_distance": 10.0},
	&"footstep_linoleum": {&"bus": &"Footsteps", &"volume_db": -3.0, &"pitch_var": 0.05, &"volume_var_db": 1.5, &"unit_size": 2.0, &"max_distance": 16.0},
	&"footstep_tile": {&"bus": &"Footsteps", &"volume_db": -4.0, &"pitch_var": 0.05, &"volume_var_db": 1.5, &"unit_size": 2.0, &"max_distance": 16.0},
	&"footstep_concrete": {&"bus": &"Footsteps", &"volume_db": -3.0, &"pitch_var": 0.05, &"volume_var_db": 1.5, &"unit_size": 2.0, &"max_distance": 16.0},

	# --- interaction -------------------------------------------------------------
	&"door_open": {},
	&"door_close": {&"max_distance": 30.0},
	&"door_locked": {},
	&"door_creak": {&"pitch_var": 0.06},
	&"drawer_open": {},
	&"drawer_close": {},
	&"cabinet_open": {},
	&"cabinet_close": {},
	&"switch_on": {&"pitch_var": 0.03},
	&"switch_off": {&"pitch_var": 0.03},
	&"lamp_click": {&"pitch_var": 0.03},
	&"button_press": {&"pitch_var": 0.03},
	&"pickup": {&"pitch_var": 0.06},
	&"putdown": {&"pitch_var": 0.06},
	&"paper_rustle": {&"pitch_var": 0.05},
	&"tv_on": {&"pitch_var": 0.01},
	&"tv_off": {&"pitch_var": 0.01},
	&"phone_pickup": {},
	&"phone_hangup": {},
	&"fridge_open": {},
	&"fridge_close": {&"max_distance": 25.0},
	&"tape_insert": {&"pitch_var": 0.02},
	&"glass_clink": {&"pitch_var": 0.03},
	&"book_slide": {&"pitch_var": 0.06},
	&"cloth_rustle": {&"pitch_var": 0.06},
	&"thud_soft": {&"pitch_var": 0.06, &"max_distance": 25.0},
	&"window_rattle": {&"pitch_var": 0.04},
	&"faucet_squeak": {&"pitch_var": 0.05},

	# --- loops: beds (non-positional, stereo) ----------------------------------------
	&"room_tone": {&"loop": true, &"bus": &"Ambience", &"volume_db": -16.0, &"pitch_var": 0.0, &"volume_var_db": 0.0},
	&"outside_afternoon": {&"loop": true, &"bus": &"Ambience", &"volume_db": -14.0, &"pitch_var": 0.0, &"volume_var_db": 0.0},
	&"wind_light": {&"loop": true, &"bus": &"Ambience", &"volume_db": -16.0, &"pitch_var": 0.0, &"volume_var_db": 0.0},
	# --- loops: positional (mono) -------------------------------------------------
	&"fridge_hum": {&"loop": true, &"volume_db": -10.0, &"pitch_var": 0.0, &"volume_var_db": 0.0, &"unit_size": 1.5, &"max_distance": 14.0},
	&"clock_tick": {&"loop": true, &"volume_db": -6.0, &"pitch_var": 0.0, &"volume_var_db": 0.0, &"unit_size": 1.5, &"max_distance": 12.0},
	&"tv_static": {&"loop": true, &"volume_db": -10.0, &"pitch_var": 0.0, &"volume_var_db": 0.0, &"unit_size": 2.0, &"max_distance": 18.0},
	&"light_buzz": {&"loop": true, &"volume_db": -14.0, &"pitch_var": 0.0, &"volume_var_db": 0.0, &"unit_size": 1.0, &"max_distance": 8.0},
	&"fly_buzz": {&"loop": true, &"volume_db": -6.0, &"pitch_var": 0.0, &"volume_var_db": 0.0, &"unit_size": 0.8, &"max_distance": 9.0},
	&"phone_dial_tone": {&"loop": true, &"volume_db": -14.0, &"pitch_var": 0.0, &"volume_var_db": 0.0, &"unit_size": 0.5, &"max_distance": 5.0},
	&"faucet_run": {&"loop": true, &"volume_db": -6.0, &"pitch_var": 0.0, &"volume_var_db": 0.0, &"unit_size": 2.0, &"max_distance": 16.0},
	# --- loops: the camcorder itself (non-positional, mono) ----------------------------
	&"camcorder_motor": {&"loop": true, &"bus": &"Ambience", &"volume_db": -24.0, &"pitch_var": 0.0, &"volume_var_db": 0.0},
	&"camcorder_zoom": {&"loop": true, &"bus": &"Ambience", &"volume_db": -18.0, &"pitch_var": 0.0, &"volume_var_db": 0.0},
	&"tape_hiss": {&"loop": true, &"bus": &"Ambience", &"volume_db": -22.0, &"pitch_var": 0.0, &"volume_var_db": 0.0},

	# --- random ambient one-shots (texture, never a scare) ---------------------------
	&"house_settle": {&"volume_db": -4.0, &"pitch_var": 0.08, &"volume_var_db": 3.0, &"unit_size": 3.0, &"max_distance": 25.0},
	&"distant_dog": {&"bus": &"Ambience", &"volume_db": -8.0, &"pitch_var": 0.05, &"volume_var_db": 3.0, &"unit_size": 6.0, &"max_distance": 80.0, &"filter_hz": 20500.0, &"filter_db": 0.0},
	&"distant_car": {&"bus": &"Ambience", &"volume_db": -8.0, &"pitch_var": 0.04, &"volume_var_db": 3.0, &"unit_size": 6.0, &"max_distance": 80.0, &"filter_hz": 20500.0, &"filter_db": 0.0},
	&"distant_mower": {&"bus": &"Ambience", &"volume_db": -9.0, &"pitch_var": 0.03, &"volume_var_db": 3.0, &"unit_size": 6.0, &"max_distance": 80.0, &"filter_hz": 20500.0, &"filter_db": 0.0},

	# --- UI ------------------------------------------------------------------------
	&"ui_tick": {&"bus": &"UI", &"volume_db": -4.0, &"pitch_var": 0.02, &"volume_var_db": 0.5},
	&"ui_open": {&"bus": &"UI", &"volume_db": -4.0, &"pitch_var": 0.02, &"volume_var_db": 0.5},
	&"ui_close": {&"bus": &"UI", &"volume_db": -4.0, &"pitch_var": 0.02, &"volume_var_db": 0.5},
}


static func has(id: StringName) -> bool:
	return SOUNDS.has(id)


static func ids() -> Array[StringName]:
	var out: Array[StringName] = []
	for k: StringName in SOUNDS:
		out.append(k)
	return out


## Settings for an id with DEFAULTS filled in. Empty if unknown.
static func get_def(id: StringName) -> Dictionary:
	if not SOUNDS.has(id):
		return {}
	var d: Dictionary = DEFAULTS.duplicate()
	d.merge(SOUNDS[id], true)
	return d


static func is_loop(id: StringName) -> bool:
	return bool(get_def(id).get(&"loop", false))


## Resource paths of every variant file for an id (works in the editor and in exports).
static func variant_paths(id: StringName) -> PackedStringArray:
	var dir := ROOT + String(id)
	var out := PackedStringArray()
	if not DirAccess.dir_exists_absolute(dir):
		return out
	for f: String in ResourceLoader.list_directory(dir):
		if f.ends_with("/"):
			continue
		if EXTENSIONS.has(f.get_extension().to_lower()):
			out.append(dir + "/" + f)
	out.sort()
	return out


## Load every variant of an id, configuring looping on the stream itself.
static func load_variants(id: StringName) -> Array[AudioStream]:
	var out: Array[AudioStream] = []
	var loop := is_loop(id)
	for p: String in variant_paths(id):
		var s := ResourceLoader.load(p) as AudioStream
		if s == null:
			push_warning("SoundLibrary: could not load %s" % p)
			continue
		configure_loop(s, loop)
		out.append(s)
	return out


## Force the loop mode on a stream (import settings can be wrong for drop-in files).
static func configure_loop(s: AudioStream, loop: bool) -> void:
	if s is AudioStreamWAV:
		var w := s as AudioStreamWAV
		if loop:
			var frames := _wav_frames(w)
			if w.loop_mode == AudioStreamWAV.LOOP_DISABLED or w.loop_end <= w.loop_begin:
				w.loop_mode = AudioStreamWAV.LOOP_FORWARD
				w.loop_begin = 0
				w.loop_end = frames
			elif w.loop_end >= frames - 1:
				# a 'smpl' chunk stores an inclusive end; Godot's loop_end is exclusive
				w.loop_end = frames
		else:
			w.loop_mode = AudioStreamWAV.LOOP_DISABLED
	elif s is AudioStreamOggVorbis:
		(s as AudioStreamOggVorbis).loop = loop
	elif s is AudioStreamMP3:
		(s as AudioStreamMP3).loop = loop


static func is_stream_looping(s: AudioStream) -> bool:
	if s is AudioStreamWAV:
		return (s as AudioStreamWAV).loop_mode != AudioStreamWAV.LOOP_DISABLED
	if s is AudioStreamOggVorbis:
		return (s as AudioStreamOggVorbis).loop
	if s is AudioStreamMP3:
		return (s as AudioStreamMP3).loop
	return false


static func _wav_frames(w: AudioStreamWAV) -> int:
	return int(round(w.get_length() * w.mix_rate))
