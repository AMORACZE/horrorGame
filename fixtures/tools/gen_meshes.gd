extends SceneTree
## Generates the few fixture meshes that primitive meshes cannot make:
## a pleated lampshade, double-sided dome shades, an arc-lamp pole and a
## coiled phone cord. Output: fixtures/meshes/*.res (binary ArrayMesh).
##
##   godot --headless --path . -s res://fixtures/tools/gen_meshes.gd
##
## Re-run after changing a parameter here; the scenes reference the files by path.

const OUT := "res://fixtures/meshes/"
const ORDER_OUT: Array[int] = [0, 2, 1, 0, 3, 2]
const ORDER_IN: Array[int] = [0, 1, 2, 0, 2, 3]


func _initialize() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT))
	_save(_pleated_shade(0.205, 0.125, 0.26, 40, 0.007), "pleated_shade")
	_save(_dome(0.2, 0.17, 24, 10), "dome_shade")
	_save(_dome(0.115, 0.09, 24, 8), "bowl_glass")
	_save(_dome(0.155, 0.085, 28, 8), "ceiling_dome")
	_save(_tube(_arc_pole_points(), 0.011, 10), "arc_lamp_pole")
	_save(_coil(_phone_cord_points(), 0.0045, 0.0017, 22.0, 5), "phone_cord")
	_save(_crt_face(0.37, 0.28, 0.02, 24, 18), "crt_face")
	quit(0)


func _save(mesh: ArrayMesh, name: String) -> void:
	var err := ResourceSaver.save(mesh, OUT + name + ".res")
	print("gen_meshes: %s -> %s" % [name, error_string(err)])


## A CRT tube face: a rectangle w x h with a cushion bulge toward +Z.
## Origin at the rectangle's centre on the rim plane; the edges sit at z ~ 0.
func _crt_face(w: float, h: float, bulge: float, nx: int, ny: int) -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for j in ny:
		for i in nx:
			var q: Array[Vector3] = []
			var ns: Array[Vector3] = []
			var uvs: Array[Vector2] = []
			for c: Vector2i in [Vector2i(i, j), Vector2i(i, j + 1), Vector2i(i + 1, j + 1), Vector2i(i + 1, j)]:
				var u := float(c.x) / float(nx) * 2.0 - 1.0
				var v := float(c.y) / float(ny) * 2.0 - 1.0
				var fu := 1.0 - 0.9 * u * u
				var fv := 1.0 - 0.9 * v * v
				q.append(Vector3(u * w * 0.5, v * h * 0.5, bulge * fu * fv))
				var dzdx := bulge * (-1.8 * u) * fv / (w * 0.5)
				var dzdy := bulge * fu * (-1.8 * v) / (h * 0.5)
				ns.append(Vector3(-dzdx, -dzdy, 1.0).normalized())
				uvs.append(Vector2((u + 1.0) * 0.5, 1.0 - (v + 1.0) * 0.5))
			for k in ORDER_IN:
				st.set_normal(ns[k])
				st.set_uv(uvs[k])
				st.add_vertex(q[k])
	st.index()
	return st.commit()


## Truncated cone with a zig-zag (pleated) wall, outer and inner faces.
## Origin at the shade's vertical centre. bottom/top are radii in metres.
func _pleated_shade(r_bottom: float, r_top: float, height: float, pleats: int, depth: float) -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var n := pleats * 2
	for side in 2:
		var inner := side == 1
		for i in n:
			var a0 := TAU * float(i) / float(n)
			var a1 := TAU * float(i + 1) / float(n)
			# Ridges on even vertices, valleys on odd: depth scales with radius.
			var d0 := 0.0 if i % 2 == 0 else depth
			var d1 := 0.0 if (i + 1) % 2 == 0 else depth
			var s := -0.002 if inner else 0.0
			var b0 := _ring(a0, r_bottom - d0 + s, -height * 0.5)
			var b1 := _ring(a1, r_bottom - d1 + s, -height * 0.5)
			var t0 := _ring(a0, r_top - d0 * (r_top / r_bottom) + s, height * 0.5)
			var t1 := _ring(a1, r_top - d1 * (r_top / r_bottom) + s, height * 0.5)
			var nrm := (t0 - b0).cross(b1 - b0).normalized()
			if inner:
				nrm = -nrm
			var u0 := float(i) / float(n)
			var u1 := float(i + 1) / float(n)
			var quad: Array[Vector3] = [b0, t0, t1, b1]
			var uvs: Array[Vector2] = [Vector2(u0, 1), Vector2(u0, 0), Vector2(u1, 0), Vector2(u1, 1)]
			var order: Array[int] = ORDER_IN if inner else ORDER_OUT
			for k in order:
				st.set_normal(nrm)
				st.set_uv(uvs[k])
				st.add_vertex(quad[k])
	st.generate_tangents()
	st.index()
	return st.commit()


func _ring(a: float, r: float, y: float) -> Vector3:
	return Vector3(cos(a) * r, y, sin(a) * r)


## Hemispherical shell, open at the bottom (y = 0 rim, apex at +height).
## Double-sided so the inside is visible and it shadows from any side.
func _dome(radius: float, height: float, segs: int, rings: int) -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for side in 2:
		var inner := side == 1
		var r := radius - (0.0015 if inner else 0.0)
		var h := height - (0.0015 if inner else 0.0)
		for j in rings:
			var p0 := float(j) / float(rings) * PI * 0.5
			var p1 := float(j + 1) / float(rings) * PI * 0.5
			for i in segs:
				var a0 := TAU * float(i) / float(segs)
				var a1 := TAU * float(i + 1) / float(segs)
				var v: Array[Vector3] = [
					Vector3(cos(a0) * cos(p0) * r, sin(p0) * h, sin(a0) * cos(p0) * r),
					Vector3(cos(a1) * cos(p0) * r, sin(p0) * h, sin(a1) * cos(p0) * r),
					Vector3(cos(a1) * cos(p1) * r, sin(p1) * h, sin(a1) * cos(p1) * r),
					Vector3(cos(a0) * cos(p1) * r, sin(p1) * h, sin(a0) * cos(p1) * r),
				]
				var order: Array[int] = ORDER_IN if inner else ORDER_OUT
				for k in order:
					var nrm := Vector3(v[k].x / (r * r), v[k].y / (h * h), v[k].z / (r * r)).normalized()
					st.set_normal(-nrm if inner else nrm)
					st.set_uv(Vector2(float(i) / float(segs), float(j) / float(rings)))
					st.add_vertex(v[k])
	st.index()
	return st.commit()


## The 70s arc lamp pole: up from the base, then a long arc over to the shade.
## In the lamp's local space (origin at floor, arc reaching toward +X).
func _arc_pole_points() -> PackedVector3Array:
	var pts := PackedVector3Array()
	pts.append(Vector3(0, 0.06, 0))
	pts.append(Vector3(0, 0.7, 0))
	var c := Vector2(0.72, 1.18)
	var r := 0.72
	for i in 33:
		var a := lerpf(PI, deg_to_rad(18.0), float(i) / 32.0)
		pts.append(Vector3(c.x + cos(a) * r, c.y + sin(a) * r * 0.95, 0))
	return pts


## Telephone handset cord: from the base's left side, a loop on the desk,
## up to the handset's mouthpiece end. Telephone-local coordinates.
func _phone_cord_points() -> PackedVector3Array:
	var ctrl := PackedVector3Array([
		Vector3(-0.094, 0.018, 0.06),
		Vector3(-0.13, 0.008, 0.075),
		Vector3(-0.19, 0.006, 0.05),
		Vector3(-0.21, 0.006, -0.02),
		Vector3(-0.17, 0.02, -0.075),
		Vector3(-0.125, 0.06, -0.055),
		Vector3(-0.112, 0.082, -0.045),
	])
	var pts := PackedVector3Array()
	var steps := 48
	for i in steps + 1:
		var t := float(i) / float(steps) * float(ctrl.size() - 1)
		var k := mini(int(t), ctrl.size() - 2)
		var f := t - float(k)
		var p0 := ctrl[maxi(k - 1, 0)]
		var p1 := ctrl[k]
		var p2 := ctrl[k + 1]
		var p3 := ctrl[mini(k + 2, ctrl.size() - 1)]
		pts.append(p1.cubic_interpolate(p2, p0, p3, f))
	return pts


## A round tube along a polyline.
func _tube(path: PackedVector3Array, radius: float, sides: int) -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var frames := _frames(path)
	for i in path.size() - 1:
		for s in sides:
			var a0 := TAU * float(s) / float(sides)
			var a1 := TAU * float(s + 1) / float(sides)
			var q: Array[Vector3] = []
			var nq: Array[Vector3] = []
			for pair: Array in [[i, a0], [i, a1], [i + 1, a1], [i + 1, a0]]:
				var idx: int = pair[0]
				var ang: float = pair[1]
				var b: Basis = frames[idx]
				var nrm := (b.x * cos(ang) + b.y * sin(ang)).normalized()
				nq.append(nrm)
				q.append(path[idx] + nrm * radius)
			for k: int in [0, 2, 1, 0, 3, 2]:
				st.set_normal(nq[k])
				st.add_vertex(q[k])
	st.index()
	return st.commit()


## A coiled cord: a thin tube wound helically around `path`.
func _coil(path: PackedVector3Array, coil_radius: float, wire_radius: float, turns_per_10cm: float, sides: int) -> ArrayMesh:
	var frames := _frames(path)
	var length := 0.0
	var helix := PackedVector3Array()
	var dense := 6
	for i in path.size() - 1:
		var seg := path[i].distance_to(path[i + 1])
		for d in dense:
			var f := float(d) / float(dense)
			var l := length + seg * f
			var ang := l / 0.1 * turns_per_10cm * TAU
			var b: Basis = frames[i]
			var c := path[i].lerp(path[i + 1], f)
			helix.append(c + (b.x * cos(ang) + b.y * sin(ang)) * coil_radius)
		length += seg
	helix.append(path[path.size() - 1])
	return _tube(helix, wire_radius, sides)


## Parallel-transport frames along a path (x, y perpendicular to the tangent).
func _frames(path: PackedVector3Array) -> Array[Basis]:
	var out: Array[Basis] = []
	var up := Vector3.UP
	for i in path.size():
		var t: Vector3
		if i == 0:
			t = path[1] - path[0]
		elif i == path.size() - 1:
			t = path[i] - path[i - 1]
		else:
			t = path[i + 1] - path[i - 1]
		t = t.normalized()
		if absf(t.dot(up)) > 0.95:
			up = Vector3.BACK if absf(t.dot(Vector3.BACK)) < 0.95 else Vector3.RIGHT
		var x := up.cross(t).normalized()
		var y := t.cross(x).normalized()
		up = y
		out.append(Basis(x, y, t))
	return out
