"""Tiny .tscn writer used by build_props.py.

Emits plain, hand-editable Godot 4 text scenes: one MeshInstance3D per visible
part, primitive meshes as sub-resources (deduplicated), palette materials as
external resources by path. Also tracks a root-space AABB of every visual part
so the catalogue can report footprints.
"""
from __future__ import annotations

import math
import os
from typing import Any, Iterable, Sequence

Vec3 = Sequence[float]
Mat3 = list[list[float]]

PALETTE = "res://art/materials/%s.tres"
PROP_MAT = "res://props/materials/%s.tres"
TEX = "res://props/textures/%s"
SCRIPTS = {
    "base": "res://interaction/interactable.gd",
    "exam": "res://interaction/examinable_interactable.gd",
    "read": "res://interaction/readable_interactable.gd",
}
READ_STYLE = {"paper": 0, "handwritten": 1, "typed": 2, "label": 3, "print": 4}

LAYER_WORLD = 1
LAYER_INTERACT = 4
LAYER_PHYS = 8


# --------------------------------------------------------------------------- math

def _rx(a: float) -> Mat3:
    c, s = math.cos(a), math.sin(a)
    return [[1, 0, 0], [0, c, -s], [0, s, c]]


def _ry(a: float) -> Mat3:
    c, s = math.cos(a), math.sin(a)
    return [[c, 0, s], [0, 1, 0], [-s, 0, c]]


def _rz(a: float) -> Mat3:
    c, s = math.cos(a), math.sin(a)
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


def mmul(a: Mat3, b: Mat3) -> Mat3:
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def mvec(a: Mat3, v: Vec3) -> list[float]:
    return [sum(a[i][k] * v[k] for k in range(3)) for i in range(3)]


def euler(rot_deg: Vec3) -> Mat3:
    """Godot's default YXZ Euler order."""
    rx, ry, rz = (math.radians(r) for r in rot_deg)
    return mmul(mmul(_ry(ry), _rx(rx)), _rz(rz))


def align_y(d: Vec3) -> Mat3:
    """Rotation taking +Y onto direction d."""
    l = math.sqrt(sum(c * c for c in d))
    x, y, z = (c / l for c in d)
    if y > 0.999999:
        return [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    if y < -0.999999:
        return _rx(math.pi)
    ax = [z, 0.0, -x]  # Y cross d
    al = math.sqrt(ax[0] ** 2 + ax[2] ** 2)
    ax = [ax[0] / al, 0.0, ax[2] / al]
    ang = math.acos(max(-1.0, min(1.0, y)))
    c, s, t = math.cos(ang), math.sin(ang), 1 - math.cos(ang)
    ux, uy, uz = ax
    return [
        [t * ux * ux + c, t * ux * uy - s * uz, t * ux * uz + s * uy],
        [t * ux * uy + s * uz, t * uy * uy + c, t * uy * uz - s * ux],
        [t * ux * uz - s * uy, t * uy * uz + s * ux, t * uz * uz + c],
    ]


def scale_m(b: Mat3, s: Vec3) -> Mat3:
    return [[b[i][j] * s[j] for j in range(3)] for i in range(3)]


IDENT: Mat3 = [[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0]]


# --------------------------------------------------------------------------- formatting

def f(x: float) -> str:
    if abs(x) < 5e-7:
        return "0"
    s = ("%.6f" % x).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def v3(v: Vec3) -> str:
    return "Vector3(%s, %s, %s)" % tuple(f(c) for c in v)


def v2(v: Sequence[float]) -> str:
    return "Vector2(%s, %s)" % tuple(f(c) for c in v)


def col(c: Sequence[float]) -> str:
    c = list(c) + [1.0] * (4 - len(c))
    return "Color(%s, %s, %s, %s)" % tuple(f(x) for x in c)


def qstr(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def xform(b: Mat3, o: Vec3) -> str:
    vals = [b[0][0], b[0][1], b[0][2], b[1][0], b[1][1], b[1][2], b[2][0], b[2][1], b[2][2], *o]
    return "Transform3D(%s)" % ", ".join(f(x) for x in vals)


class Raw(str):
    """A value already formatted as Godot text."""


def fmt(v: Any) -> str:
    if isinstance(v, Raw):
        return str(v)
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int,)):
        return str(v)
    if isinstance(v, float):
        return f(v)
    if isinstance(v, str):
        return qstr(v)
    raise TypeError(v)


def str_array(lines: Iterable[str]) -> Raw:
    return Raw("Array[String]([%s])" % ", ".join(qstr(l) for l in lines))


# --------------------------------------------------------------------------- scene

class Node:
    def __init__(self, name: str, typ: str | None, parent: str | None, props: list[tuple[str, Any]],
                 basis: Mat3, origin: Vec3, instance: str | None = None):
        self.name, self.typ, self.parent, self.props = name, typ, parent, props
        self.basis, self.origin, self.instance = basis, list(origin), instance


class Scene:
    def __init__(self, name: str, root_type: str = "StaticBody3D", prop_class: str = "furniture",
                 layer: int | None = None, mask: int | None = None, script: str | None = None,
                 root_props: list[tuple[str, Any]] | None = None):
        self.name = name
        self.prop_class = prop_class
        self.ext: list[tuple[str, str, str]] = []  # (type, path, id)
        self.subs: list[tuple[str, str, list[tuple[str, Any]]]] = []
        self._sub_keys: dict[tuple, str] = {}
        self.nodes: list[Node] = []
        self._paths: dict[str, Node] = {}
        self._used_names: dict[str, set[str]] = {}
        self.bounds: list[list[float]] | None = None  # [min, max]
        if layer is None:
            layer = {"furniture": LAYER_WORLD | LAYER_INTERACT,
                     "tabletop": LAYER_INTERACT, "wall": LAYER_INTERACT,
                     "loose": LAYER_INTERACT | LAYER_PHYS}[prop_class]
        props: list[tuple[str, Any]] = []
        if script:
            props.append(("script", self.ext_res("Script", script)))
        props.append(("collision_layer", layer))
        if root_type == "RigidBody3D":
            props.append(("collision_mask", mask if mask is not None else LAYER_WORLD | LAYER_PHYS))
        else:
            props.append(("collision_mask", mask if mask is not None else 0))
        props += root_props or []
        props.append(("metadata/prop_class", prop_class))
        root = Node(name, root_type, None, props, IDENT, (0, 0, 0))
        self.nodes.append(root)
        self._paths["."] = root
        self._used_names["."] = set()

    # ---- resources
    def ext_res(self, typ: str, path: str) -> Raw:
        for t, p, i in self.ext:
            if p == path:
                return Raw('ExtResource("%s")' % i)
        base = os.path.splitext(os.path.basename(path))[0]
        i = "%d_%s" % (len(self.ext) + 1, base[:24])
        self.ext.append((typ, path, i))
        return Raw('ExtResource("%s")' % i)

    def sub_res(self, typ: str, props: list[tuple[str, Any]]) -> Raw:
        key = (typ, tuple((k, fmt(v)) for k, v in props))
        if key in self._sub_keys:
            return Raw('SubResource("%s")' % self._sub_keys[key])
        i = "%s_%d" % (typ, len(self.subs) + 1)
        self.subs.append((typ, i, props))
        self._sub_keys[key] = i
        return Raw('SubResource("%s")' % i)

    def mat(self, m: Any) -> Raw:
        """'wood_dark' -> palette; 'p:amber' -> props/materials; dict -> textured sub-resource."""
        if isinstance(m, Raw):
            return m
        if isinstance(m, dict):
            props: list[tuple[str, Any]] = []
            if m.get("transparent"):
                props.append(("transparency", 1 if m["transparent"] is True else m["transparent"]))
            if m.get("cull_disabled"):
                props.append(("cull_mode", 2))
            props.append(("albedo_color", Raw(col(m.get("color", (1, 1, 1, 1))))))
            if "tex" in m:
                props.append(("albedo_texture", self.ext_res("Texture2D", TEX % m["tex"])))
            props.append(("roughness", float(m.get("roughness", 0.85))))
            if "uv_scale" in m:
                props.append(("uv1_scale", Raw(v3(list(m["uv_scale"]) + [1.0][: 3 - len(m["uv_scale"])]))))
            if "uv_offset" in m:
                props.append(("uv1_offset", Raw(v3(list(m["uv_offset"]) + [0.0][: 3 - len(m["uv_offset"])]))))
            return self.sub_res("StandardMaterial3D", props)
        if m.startswith("p:"):
            return self.ext_res("Material", PROP_MAT % m[2:])
        return self.ext_res("Material", PALETTE % m)

    # ---- nodes
    def _unique(self, parent: str, name: str) -> str:
        used = self._used_names.setdefault(parent, set())
        n, k = name, 2
        while n in used:
            n = "%s%d" % (name, k)
            k += 1
        used.add(n)
        return n

    def _world(self, parent: str, basis: Mat3, origin: Vec3) -> tuple[Mat3, list[float]]:
        if parent == ".":
            return basis, list(origin)
        p = self._paths[parent]
        pb, po = self._world(p.parent, p.basis, p.origin)
        return mmul(pb, basis), [a + b for a, b in zip(mvec(pb, origin), po)]

    def add(self, name: str, typ: str | None, parent: str = ".", props: list[tuple[str, Any]] | None = None,
            pos: Vec3 = (0, 0, 0), rot: Vec3 = (0, 0, 0), scale: Vec3 = (1, 1, 1),
            basis: Mat3 | None = None, instance: str | None = None) -> str:
        name = self._unique(parent, name)
        b = basis if basis is not None else euler(rot)
        b = scale_m(b, scale)
        props = list(props or [])
        if b != IDENT or any(abs(c) > 1e-9 for c in pos):
            props.insert(0, ("transform", Raw(xform(b, pos))))
        node = Node(name, typ, parent, props, b, pos, instance)
        self.nodes.append(node)
        path = name if parent == "." else parent + "/" + name
        self._paths[path] = node
        self._used_names[path] = set()
        return path

    def group(self, name: str, parent: str = ".", pos: Vec3 = (0, 0, 0), rot: Vec3 = (0, 0, 0),
              scale: Vec3 = (1, 1, 1), basis: Mat3 | None = None) -> str:
        return self.add(name, "Node3D", parent, [], pos, rot, scale, basis)

    def _grow(self, path: str, lo: Vec3, hi: Vec3) -> None:
        node = self._paths[path]
        wb, wo = self._world(node.parent, node.basis, node.origin)
        for cx in (lo[0], hi[0]):
            for cy in (lo[1], hi[1]):
                for cz in (lo[2], hi[2]):
                    p = [a + b for a, b in zip(mvec(wb, (cx, cy, cz)), wo)]
                    if self.bounds is None:
                        self.bounds = [list(p), list(p)]
                    else:
                        for i in range(3):
                            self.bounds[0][i] = min(self.bounds[0][i], p[i])
                            self.bounds[1][i] = max(self.bounds[1][i], p[i])

    def _mesh(self, name: str, mesh_type: str, mprops: list[tuple[str, Any]], half: Vec3,
              mat: Any, parent: str, pos: Vec3, rot: Vec3, scale: Vec3, basis: Mat3 | None,
              shadow: bool = True) -> str:
        mesh = self.sub_res(mesh_type, mprops)
        props: list[tuple[str, Any]] = [("mesh", mesh)]
        if not shadow:
            props.append(("cast_shadow", 0))
        props.append(("material_override", self.mat(mat)))
        path = self.add(name, "MeshInstance3D", parent, props, pos, rot, scale, basis)
        self._grow(path, [-h for h in half], half)
        return path

    def box(self, name: str, size: Vec3, pos: Vec3, mat: Any, rot: Vec3 = (0, 0, 0),
            parent: str = ".", scale: Vec3 = (1, 1, 1), basis: Mat3 | None = None, **kw) -> str:
        return self._mesh(name, "BoxMesh", [("size", Raw(v3(size)))], [s / 2 for s in size], mat,
                          parent, pos, rot, scale, basis, **kw)

    def cyl(self, name: str, r: float, h: float, pos: Vec3, mat: Any, rot: Vec3 = (0, 0, 0),
            r_bottom: float | None = None, segs: int = 24, parent: str = ".", scale: Vec3 = (1, 1, 1),
            basis: Mat3 | None = None, cap_top: bool = True, cap_bottom: bool = True, **kw) -> str:
        rb = r if r_bottom is None else r_bottom
        props: list[tuple[str, Any]] = [("top_radius", float(r)), ("bottom_radius", float(rb)),
                                        ("height", float(h)), ("radial_segments", segs), ("rings", 1)]
        if not cap_top:
            props.append(("cap_top", False))
        if not cap_bottom:
            props.append(("cap_bottom", False))
        rm = max(r, rb)
        return self._mesh(name, "CylinderMesh", props, (rm, h / 2, rm), mat, parent, pos, rot, scale,
                          basis, **kw)

    def rod(self, name: str, p0: Vec3, p1: Vec3, r: float, mat: Any, parent: str = ".", segs: int = 8,
            r1: float | None = None, **kw) -> str:
        d = [b - a for a, b in zip(p0, p1)]
        length = math.sqrt(sum(c * c for c in d))
        mid = [(a + b) / 2 for a, b in zip(p0, p1)]
        # CylinderMesh top is +Y (towards p1)
        return self.cyl(name, r if r1 is None else r1, length, mid, mat, r_bottom=r, segs=segs,
                        parent=parent, basis=align_y(d), **kw)

    def sphere(self, name: str, r: float, pos: Vec3, mat: Any, scale: Vec3 = (1, 1, 1),
               rot: Vec3 = (0, 0, 0), segs: int = 16, rings: int = 8, hemi: bool = False,
               parent: str = ".", basis: Mat3 | None = None, **kw) -> str:
        props: list[tuple[str, Any]] = [("radius", float(r)), ("height", float(r * (1 if hemi else 2))),
                                        ("radial_segments", segs), ("rings", rings)]
        if hemi:
            props.append(("is_hemisphere", True))
        return self._mesh(name, "SphereMesh", props, (r, r, r), mat, parent, pos, rot, scale, basis, **kw)

    def capsule(self, name: str, r: float, h: float, pos: Vec3, mat: Any, rot: Vec3 = (0, 0, 0),
                scale: Vec3 = (1, 1, 1), parent: str = ".", segs: int = 16, basis: Mat3 | None = None,
                **kw) -> str:
        props: list[tuple[str, Any]] = [("radius", float(r)), ("height", float(h)),
                                        ("radial_segments", segs), ("rings", 4)]
        return self._mesh(name, "CapsuleMesh", props, (r, h / 2, r), mat, parent, pos, rot, scale,
                          basis, **kw)

    def torus(self, name: str, inner: float, outer: float, pos: Vec3, mat: Any, rot: Vec3 = (0, 0, 0),
              scale: Vec3 = (1, 1, 1), parent: str = ".", rings: int = 24, ring_segs: int = 8,
              basis: Mat3 | None = None, **kw) -> str:
        props: list[tuple[str, Any]] = [("inner_radius", float(inner)), ("outer_radius", float(outer)),
                                        ("rings", rings), ("ring_segments", ring_segs)]
        return self._mesh(name, "TorusMesh", props, (outer, (outer - inner) / 2, outer), mat, parent, pos,
                          rot, scale, basis, **kw)

    def prism(self, name: str, size: Vec3, pos: Vec3, mat: Any, rot: Vec3 = (0, 0, 0),
              ltr: float = 0.5, parent: str = ".", scale: Vec3 = (1, 1, 1), basis: Mat3 | None = None,
              **kw) -> str:
        props: list[tuple[str, Any]] = [("left_to_right", float(ltr)), ("size", Raw(v3(size)))]
        return self._mesh(name, "PrismMesh", props, [s / 2 for s in size], mat, parent, pos, rot, scale,
                          basis, **kw)

    def quad(self, name: str, size: Sequence[float], pos: Vec3, mat: Any, rot: Vec3 = (0, 0, 0),
             parent: str = ".", basis: Mat3 | None = None, **kw) -> str:
        return self._mesh(name, "QuadMesh", [("size", Raw(v2(size)))], (size[0] / 2, size[1] / 2, 0.0005),
                          mat, parent, pos, rot, (1, 1, 1), basis, **kw)

    # ---- collision
    def col_box(self, size: Vec3, pos: Vec3 = (0, 0, 0), rot: Vec3 = (0, 0, 0), name: str = "Collision",
                parent: str = ".") -> str:
        shape = self.sub_res("BoxShape3D", [("size", Raw(v3(size)))])
        return self.add(name, "CollisionShape3D", parent, [("shape", shape)], pos, rot)

    def col_cyl(self, r: float, h: float, pos: Vec3 = (0, 0, 0), rot: Vec3 = (0, 0, 0),
                name: str = "Collision", parent: str = ".") -> str:
        shape = self.sub_res("CylinderShape3D", [("height", float(h)), ("radius", float(r))])
        return self.add(name, "CollisionShape3D", parent, [("shape", shape)], pos, rot)

    # ---- interaction
    def interactable(self, kind: str, display_name: str, observations: Sequence[str] = (),
                     prompt: str | None = None, **extra: Any) -> str:
        props: list[tuple[str, Any]] = [("script", self.ext_res("Script", SCRIPTS[kind])),
                                        ("display_name", display_name)]
        if prompt:
            props.append(("prompt", prompt))
        if observations:
            props.append(("observations", str_array(observations)))
        for k, v in extra.items():
            if k == "style":
                v = READ_STYLE[v]
            elif k == "examine_rotation_degrees":
                v = Raw(v3(v))
            props.append((k, v))
        return self.add("Interactable", "Node", ".", props)

    # ---- output
    def footprint(self) -> tuple[float, float, float]:
        if not self.bounds:
            return (0.0, 0.0, 0.0)
        lo, hi = self.bounds
        return (hi[0] - lo[0], hi[2] - lo[2], hi[1] - lo[1])

    def text(self) -> str:
        out = ["[gd_scene format=3]", ""]
        for typ, path, i in self.ext:
            out.append('[ext_resource type="%s" path="%s" id="%s"]' % (typ, path, i))
        if self.ext:
            out.append("")
        for typ, i, props in self.subs:
            out.append('[sub_resource type="%s" id="%s"]' % (typ, i))
            for k, v in props:
                out.append("%s = %s" % (k, fmt(v)))
            out.append("")
        for n in self.nodes:
            head = '[node name="%s"' % n.name
            if n.typ and not n.instance:
                head += ' type="%s"' % n.typ
            if n.parent is not None:
                head += ' parent="%s"' % n.parent
            if n.instance:
                head += " instance=%s" % n.instance
            out.append(head + "]")
            for k, v in n.props:
                out.append("%s = %s" % (k, fmt(v)))
            out.append("")
        return "\n".join(out).rstrip() + "\n"

    def write(self, root_dir: str, rel_path: str) -> None:
        p = os.path.join(root_dir, rel_path)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            fh.write(self.text())


def write_material(root_dir: str, name: str, props: list[tuple[str, Any]],
                   ext: list[tuple[str, str]] | None = None) -> None:
    p = os.path.join(root_dir, "props", "materials", name + ".tres")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    lines = ['[gd_resource type="StandardMaterial3D" format=3]', ""]
    for i, (typ, path) in enumerate(ext or [], start=1):
        lines.append('[ext_resource type="%s" path="%s" id="%d"]' % (typ, path, i))
    if ext:
        lines.append("")
    lines.append("[resource]")
    for k, v in props:
        lines.append("%s = %s" % (k, fmt(v)))
    with open(p, "w") as fh:
        fh.write("\n".join(lines) + "\n")
