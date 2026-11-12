"""Tiny .tscn writer used by build_fixture_scenes.py.

Authoring aid only: the generated scenes are ordinary text scenes and are the
source of truth once someone edits them in the editor. Re-running the builder
overwrites them.
"""
import math
import os


class Raw:
    def __init__(self, s):
        self.s = s

    def __repr__(self):
        return self.s


def num(x):
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, int):
        return str(x)
    s = ("%.5f" % x).rstrip("0").rstrip(".")
    if s in ("-0", "", "-"):
        s = "0"
    return s


def qstr(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def fmt(v):
    if isinstance(v, Raw):
        return v.s
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return num(v)
    if isinstance(v, str):
        return qstr(v)
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(fmt(x) for x in v) + "]"
    raise TypeError(v)


def V3(x, y=None, z=None):
    if y is None:
        x, y, z = x
    return Raw("Vector3(%s, %s, %s)" % (num(x), num(y), num(z)))


def V2(x, y):
    return Raw("Vector2(%s, %s)" % (num(x), num(y)))


def C(r, g, b, a=1.0):
    return Raw("Color(%s, %s, %s, %s)" % (num(r), num(g), num(b), num(a)))


def SN(s):
    return Raw('&"%s"' % s)


def NP(s):
    return Raw('NodePath("%s")' % s)


def STRS(lst):
    return Raw("Array[String]([" + ", ".join(qstr(s) for s in lst) + "])")


def NPS(lst):
    return Raw("Array[NodePath]([" + ", ".join('NodePath("%s")' % s for s in lst) + "])")


# --- 3x3 matrices (row-major lists) -----------------------------------------

def mmul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def rx(d):
    t = math.radians(d)
    c, s = math.cos(t), math.sin(t)
    return [[1, 0, 0], [0, c, -s], [0, s, c]]


def ry(d):
    t = math.radians(d)
    c, s = math.cos(t), math.sin(t)
    return [[c, 0, s], [0, 1, 0], [-s, 0, c]]


def rz(d):
    t = math.radians(d)
    c, s = math.cos(t), math.sin(t)
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


def diag(x, y, z):
    return [[x, 0, 0], [0, y, 0], [0, 0, z]]


IDENT = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]


def euler(rot):
    """Godot's default YXZ order: R = Ry * Rx * Rz (degrees)."""
    return mmul(mmul(ry(rot[1]), rx(rot[0])), rz(rot[2]))


def XF(pos=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), basis=None):
    b = basis if basis is not None else mmul(euler(rot), diag(*scale))
    vals = [b[i][j] for i in range(3) for j in range(3)] + list(pos)
    return Raw("Transform3D(" + ", ".join(num(round(v, 6)) for v in vals) + ")")


def is_identity_xf(pos, rot, scale):
    return tuple(pos) == (0, 0, 0) and tuple(rot) == (0, 0, 0) and tuple(scale) == (1, 1, 1)


# --- Scene -------------------------------------------------------------------

class Scene:
    def __init__(self, root_name, root_type="Node3D", script=None, props=None):
        self.ext_list = []  # (type, path, id)
        self.ext_ids = {}
        self.subs = []  # (type, id, props)
        self.sub_keys = {}
        self.nodes = []  # (header, props)
        self.counter = 0
        hdr = '[node name="%s" type="%s"]' % (root_name, root_type)
        p = dict(props or {})
        if script:
            p = {"script": self.ext(script, "Script"), **p}
        self.nodes.append((hdr, p))

    def ext(self, path, typ):
        if path in self.ext_ids:
            return Raw('ExtResource("%s")' % self.ext_ids[path])
        self.counter += 1
        rid = "%d_%s" % (self.counter, os.path.splitext(os.path.basename(path))[0][:20])
        self.ext_ids[path] = rid
        self.ext_list.append((typ, path, rid))
        return Raw('ExtResource("%s")' % rid)

    def mat(self, name):
        if name.startswith("res://"):
            return self.ext(name, "Material")
        if name.startswith("fx:"):
            return self.ext("res://fixtures/materials/%s.tres" % name[3:], "Material")
        return self.ext("res://art/materials/%s.tres" % name, "Material")

    def sub(self, typ, **props):
        key = (typ, tuple(sorted((k, fmt(v)) for k, v in props.items())))
        if key in self.sub_keys:
            return Raw('SubResource("%s")' % self.sub_keys[key])
        self.counter += 1
        rid = "%s_%d" % (typ, self.counter)
        self.sub_keys[key] = rid
        self.subs.append((typ, rid, props))
        return Raw('SubResource("%s")' % rid)

    def node(self, name, typ, parent=".", props=None, instance=None, groups=None):
        if instance is not None:
            hdr = '[node name="%s" parent="%s" instance=%s]' % (name, parent, fmt(instance))
        else:
            hdr = '[node name="%s" type="%s" parent="%s"' % (name, typ, parent)
            if groups:
                hdr += " groups=[%s]" % ", ".join(qstr(g) for g in groups)
            hdr += "]"
        self.nodes.append((hdr, dict(props or {})))
        return name if parent == "." else parent + "/" + name

    def write(self, relpath):
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        out = []
        out.append("[gd_scene format=3]\n")
        for typ, path, rid in self.ext_list:
            out.append('[ext_resource type="%s" path="%s" id="%s"]' % (typ, path, rid))
        if self.ext_list:
            out.append("")
        for typ, rid, props in self.subs:
            out.append('[sub_resource type="%s" id="%s"]' % (typ, rid))
            for k, v in props.items():
                out.append("%s = %s" % (k, fmt(v)))
            out.append("")
        for hdr, props in self.nodes:
            out.append(hdr)
            for k, v in props.items():
                out.append("%s = %s" % (k, fmt(v)))
            out.append("")
        path = os.path.join(root, relpath)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write("\n".join(out).rstrip() + "\n")
        print("wrote", relpath)


# --- Geometry helpers ---------------------------------------------------------

def _mesh_node(sc, parent, name, mesh, mat, pos, rot, scale, cast, visible, basis=None, extra=None):
    props = {}
    if basis is not None or not is_identity_xf(pos, rot, scale):
        props["transform"] = XF(pos, rot, scale, basis)
    if cast is not None:
        props["cast_shadow"] = cast
    if visible is not None:
        props["visible"] = visible
    props["mesh"] = mesh
    if mat:
        props["surface_material_override/0"] = sc.mat(mat)
    if extra:
        props.update(extra)
    return sc.node(name, "MeshInstance3D", parent, props)


def box(sc, parent, name, size, pos=(0, 0, 0), mat=None, rot=(0, 0, 0), scale=(1, 1, 1), cast=None, visible=None, basis=None):
    mesh = sc.sub("BoxMesh", size=V3(size))
    return _mesh_node(sc, parent, name, mesh, mat, pos, rot, scale, cast, visible, basis)


def cyl(sc, parent, name, r_top, r_bot, h, pos=(0, 0, 0), mat=None, rot=(0, 0, 0), scale=(1, 1, 1), segs=24, cast=None, visible=None, caps=True, basis=None):
    props = dict(top_radius=r_top, bottom_radius=r_bot, height=h, radial_segments=segs, rings=1)
    if not caps:
        props["cap_top"] = False
        props["cap_bottom"] = False
    mesh = sc.sub("CylinderMesh", **props)
    return _mesh_node(sc, parent, name, mesh, mat, pos, rot, scale, cast, visible, basis)


def sphere(sc, parent, name, r, h=None, pos=(0, 0, 0), mat=None, rot=(0, 0, 0), scale=(1, 1, 1), segs=20, rings=10, cast=None, visible=None, hemi=False):
    props = dict(radius=r, height=h if h is not None else 2 * r, radial_segments=segs, rings=rings)
    if hemi:
        props["is_hemisphere"] = True
    mesh = sc.sub("SphereMesh", **props)
    return _mesh_node(sc, parent, name, mesh, mat, pos, rot, scale, cast, visible)


def prism(sc, parent, name, size, ltr, pos=(0, 0, 0), mat=None, rot=(0, 0, 0), cast=None):
    mesh = sc.sub("PrismMesh", left_to_right=ltr, size=V3(size))
    return _mesh_node(sc, parent, name, mesh, mat, pos, rot, (1, 1, 1), cast, None)


def res_mesh(sc, parent, name, path, pos=(0, 0, 0), mat=None, rot=(0, 0, 0), scale=(1, 1, 1), cast=None, visible=None):
    mesh = sc.ext(path, "ArrayMesh")
    return _mesh_node(sc, parent, name, mesh, mat, pos, rot, scale, cast, visible)


def col_box(sc, body, name, size, pos=(0, 0, 0), rot=(0, 0, 0)):
    props = {}
    if not is_identity_xf(pos, rot, (1, 1, 1)):
        props["transform"] = XF(pos, rot)
    props["shape"] = sc.sub("BoxShape3D", size=V3(size))
    return sc.node(name, "CollisionShape3D", body, props)


def col_cyl(sc, body, name, r, h, pos=(0, 0, 0), rot=(0, 0, 0)):
    props = {}
    if not is_identity_xf(pos, rot, (1, 1, 1)):
        props["transform"] = XF(pos, rot)
    props["shape"] = sc.sub("CylinderShape3D", radius=r, height=h)
    return sc.node(name, "CollisionShape3D", body, props)


def col_sphere(sc, body, name, r, pos=(0, 0, 0)):
    props = {}
    if tuple(pos) != (0, 0, 0):
        props["transform"] = XF(pos)
    props["shape"] = sc.sub("SphereShape3D", radius=r)
    return sc.node(name, "CollisionShape3D", body, props)


def n3d(sc, parent, name, pos=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), extra=None):
    props = {}
    if not is_identity_xf(pos, rot, scale):
        props["transform"] = XF(pos, rot, scale)
    if extra:
        props.update(extra)
    return sc.node(name, "Node3D", parent, props)


LAYER_WORLD = 1
LAYER_INTERACT = 4  # bit for layer 3
SOLID_INTERACT = LAYER_WORLD | LAYER_INTERACT


def static_body(sc, parent, name, layer=SOLID_INTERACT, pos=(0, 0, 0), rot=(0, 0, 0)):
    props = {}
    if not is_identity_xf(pos, rot, (1, 1, 1)):
        props["transform"] = XF(pos, rot)
    props["collision_layer"] = layer
    props["collision_mask"] = 0
    return sc.node(name, "StaticBody3D", parent, props)


def anim_body(sc, parent, name, layer=SOLID_INTERACT, pos=(0, 0, 0), rot=(0, 0, 0)):
    props = {}
    if not is_identity_xf(pos, rot, (1, 1, 1)):
        props["transform"] = XF(pos, rot)
    props["collision_layer"] = layer
    props["collision_mask"] = 0
    return sc.node(name, "AnimatableBody3D", parent, props)


def omni(sc, parent, name, pos, energy, rng, color=(1, 0.75, 0.5), shadow=True, size=0.03, atten=1.0, extra=None):
    props = {"transform": XF(pos), "light_color": C(*color), "light_energy": energy,
             "light_size": size, "shadow_enabled": shadow, "omni_range": rng,
             "omni_attenuation": atten}
    if shadow:
        props["omni_shadow_mode"] = 1
        props["shadow_bias"] = 0.05
        props["shadow_normal_bias"] = 1.5
    if extra:
        props.update(extra)
    return sc.node(name, "OmniLight3D", parent, props)
