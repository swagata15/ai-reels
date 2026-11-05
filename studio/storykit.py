"""Reusable building blocks for narrated story reels (Zack-D-style; see stories/STYLE_GUIDE.md).

Looks:        studio() bright gradient backdrop, lab() dark lab with bokeh, dark() near-black space
Props:        gloved_hand(pose), lab_mouse(), mouse_brain(), vial(), sewing_pin(), droplet(), needle_rig()
Annotations:  red_arrow(), red_x(), question_mark(), label3d(), dimension_line(), Counter
Animation:    key(), ease(), pop_scale(), cam_move()
All units are arbitrary but consistent per shot; every builder returns plain Blender objects.
"""
from __future__ import annotations

import math
from pathlib import Path

import bpy
from mathutils import Euler, Matrix, Vector

from . import looks, scene as sc
from .spec import hex_to_rgba

ROOT = Path(__file__).resolve().parent.parent
FONT_PATH = ROOT / "assets" / "fonts" / "Inter-ExtraBold.otf"
RED = "#E5322D"
YELLOW = "#FFC531"


# ============================================================================ utilities
def font():
    return bpy.data.fonts.load(str(FONT_PATH), check_existing=True) if FONT_PATH.exists() else None


def ease(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def ease_out(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def back_out(x: float, c: float = 1.7) -> float:
    x = min(1.0, max(0.0, x)) - 1
    return 1 + (c + 1) * x**3 + c * x**2


def key(obj, frame, **props):
    for name, value in props.items():
        setattr(obj, name, value)
        obj.keyframe_insert(name, frame=frame)


def active():
    return bpy.context.active_object


def join(objs, name):
    objs = [o for o in objs if o]
    with bpy.context.temp_override(active_object=objs[0], object=objs[0],
                                   selected_objects=objs, selected_editable_objects=objs):
        bpy.ops.object.join()
    obj = objs[0]
    obj.name = name
    return obj


def apply_all(obj):
    with bpy.context.temp_override(active_object=obj, object=obj, selected_objects=[obj]):
        for mod in list(obj.modifiers):
            bpy.ops.object.modifier_apply(modifier=mod.name)


def organic(obj, voxel=0.02, smooth=6):
    """Fuse overlapping primitives into one smooth organic surface (voxel remesh + smooth)."""
    rm = obj.modifiers.new("Fuse", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    sm = obj.modifiers.new("Soften", "SMOOTH")
    sm.factor, sm.iterations = 0.8, smooth
    apply_all(obj)
    if hasattr(obj.data, "shade_smooth"):
        obj.data.shade_smooth()
    else:
        for p in obj.data.polygons:
            p.use_smooth = True
    return obj


def capsule(a, b, r1, r2=None):
    """Cylinder from a to b with spheres at both ends (fused later by organic())."""
    a, b = Vector(a), Vector(b)
    r2 = r1 if r2 is None else r2
    v = b - a
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=v.length, vertices=24, location=a + v / 2)
    c = active()
    c.rotation_euler = v.to_track_quat("Z", "Y").to_euler()
    parts = [c]
    for p, r in ((a, r1), (b, r2)):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=24, ring_count=12, location=p)
        parts.append(active())
    return parts


def aim(obj, direction, up="Y"):
    obj.rotation_euler = Vector(direction).to_track_quat("Z", up).to_euler()


# ============================================================================ looks / sets
def studio(scene, center="#A6EEF7", edge="#2AAFD0", key_energy=900):
    """Bright radial-gradient backdrop (the clean 'explainer' look). Objects float; no floor."""
    world = bpy.data.worlds.new("StudioWorld")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = hex_to_rgba("#BFEFF6")
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    scene.world = world

    mat = bpy.data.materials.new("Backdrop")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (0.11, 0.11, 0.11)
    grad = nt.nodes.new("ShaderNodeTexGradient")
    grad.gradient_type = "SPHERICAL"
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = hex_to_rgba(edge)
    ramp.color_ramp.elements[1].color = hex_to_rgba(center)
    ramp.color_ramp.elements[1].position = 0.75
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Strength"].default_value = 1.0
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], grad.inputs["Vector"])
    nt.links.new(grad.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], emit.inputs["Color"])
    nt.links.new(emit.outputs[0], out.inputs[0])
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 14, 0), rotation=(math.pi / 2, 0, 0))
    bd = active()
    bd.name = "Backdrop"
    bd.data.materials.append(mat)
    bd.visible_shadow = False
    sc.add_area_light(scene, "Key", (-4, -9, 7), energy=key_energy, size=8)
    sc.add_area_light(scene, "Fill", (6, -7, 1), energy=key_energy * 0.45, size=8)
    sc.add_area_light(scene, "Rim", (0, 6, 6), energy=key_energy * 0.6, size=6)
    return bd


def lab(scene, rng_seed=3, table=True):
    """Dark surgical lab: steel table, warm overhead surgical light, cool rim, bokeh behind."""
    import random

    rng = random.Random(rng_seed)
    sc.setup_world(scene, "#07090D", 0.4)
    if table:
        bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, -0.5))
        t = active()
        t.name = "Table"
        looks.assign(t, looks.glossy("Steel", "#5A616B", 0.28, 0.9))
    sc.add_area_light(scene, "SurgicalLight", (0.5, -1.5, 7), energy=1400, size=3.5, color=(1.0, 0.95, 0.86))
    sc.add_area_light(scene, "RimCool", (-6, 6, 3), energy=900, size=4, color=(0.55, 0.8, 1.0))
    sc.add_area_light(scene, "Fill", (5, -6, 1), energy=180, size=6)
    mats = [looks.neon(f"LabBokeh{i}", c, 2.2) for i, c in enumerate(["#59C3FF", "#FFFFFF", "#7CF2C8", "#FFB15C"])]
    for _ in range(26):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=rng.uniform(0.15, 0.4), segments=12, ring_count=6,
                                             location=(rng.uniform(-14, 14), rng.uniform(18, 30), rng.uniform(-2, 12)))
        looks.assign(active(), rng.choice(mats))


def dark(scene, color="#05060C"):
    sc.setup_world(scene, color, 0.3)


def camera(scene, loc, target, lens=50, dof_target=None, fstop=2.8):
    cam = sc.add_camera(scene, location=loc, target=target, lens=lens)
    if dof_target is not None:
        cam.data.dof.use_dof = True
        if isinstance(dof_target, bpy.types.Object):
            cam.data.dof.focus_object = dof_target
        else:
            cam.data.dof.focus_distance = float(dof_target)
        cam.data.dof.aperture_fstop = fstop
    return cam


def cam_move(cam, f0, f1, loc0, loc1, tgt0, tgt1, curve=ease, step=1):
    for f in range(f0, f1 + 1, step):
        u = curve((f - f0) / max(1, f1 - f0))
        cam.location = Vector(loc0).lerp(Vector(loc1), u)
        sc.look_at(cam, Vector(tgt0).lerp(Vector(tgt1), u))
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)


# ============================================================================ materials
def nitrile(color="#4F86D9"):
    mat, bsdf = looks._principled("Nitrile")
    nt = mat.node_tree
    coord = nt.nodes.new("ShaderNodeTexCoord")
    crinkle = nt.nodes.new("ShaderNodeTexNoise")  # fine latex crinkles for a real-glove sheen breakup
    crinkle.inputs["Scale"].default_value = 60.0
    crinkle.inputs["Detail"].default_value = 8.0
    nt.links.new(coord.outputs["Object"], crinkle.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.12
    nt.links.new(crinkle.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    looks._set(bsdf, "Base Color", hex_to_rgba(color))
    looks._set(bsdf, "Roughness", 0.32)
    looks._set(bsdf, ["Subsurface Weight", "Subsurface"], 0.15)
    looks._set(bsdf, ["Sheen Weight", "Sheen"], 0.3)
    looks._set(bsdf, ["Coat Weight", "Clearcoat"], 0.15)
    return mat


def fur(color="#E8E4DE"):
    mat, bsdf = looks._principled("MouseFur")
    looks._set(bsdf, "Base Color", hex_to_rgba(color))
    looks._set(bsdf, "Roughness", 0.75)
    looks._set(bsdf, ["Sheen Weight", "Sheen"], 1.0)
    looks._set(bsdf, ["Subsurface Weight", "Subsurface"], 0.25)
    looks._set(bsdf, "Subsurface Radius", (1.0, 0.4, 0.3))
    return mat


def skin_pink(color="#F2A7A9"):
    mat, bsdf = looks._principled("PinkSkin")
    looks._set(bsdf, "Base Color", hex_to_rgba(color))
    looks._set(bsdf, "Roughness", 0.45)
    looks._set(bsdf, ["Subsurface Weight", "Subsurface"], 0.4)
    looks._set(bsdf, "Subsurface Radius", (1.0, 0.3, 0.25))
    return mat


def glass(tint="#FFFFFF"):
    mat, bsdf = looks._principled("Glass")
    looks._set(bsdf, "Base Color", hex_to_rgba(tint))
    looks._set(bsdf, "Roughness", 0.04)
    looks._set(bsdf, ["Transmission Weight", "Transmission"], 1.0)
    looks._set(bsdf, "IOR", 1.45)
    return mat


def glossy_red():
    mat = looks.glossy("AnnotRed", RED, 0.25)
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    looks._set(bsdf, ["Emission Color", "Emission"], hex_to_rgba(RED))
    looks._set(bsdf, "Emission Strength", 0.35)
    return mat


# ============================================================================ props
FINGERS = {  # x offset at knuckle, segment lengths
    "index": (-0.15, (0.21, 0.13, 0.10), 0.047),
    "middle": (-0.05, (0.23, 0.14, 0.11), 0.048),
    "ring": (0.05, (0.21, 0.13, 0.10), 0.045),
    "pinky": (0.15, (0.16, 0.10, 0.08), 0.04),
}
POSES = {  # curl angles (deg) per finger segment; thumb: direction + curl
    "point": {"index": (2, 2, 0), "middle": (85, 95, 60), "ring": (85, 95, 60), "pinky": (80, 90, 60),
              "thumb": ((-0.35, -0.75, 0.55), (25, 20))},
    "pinch": {"index": (35, 45, 25), "middle": (55, 70, 40), "ring": (70, 85, 50), "pinky": (75, 85, 55),
              "thumb": ((-0.55, -0.62, 0.55), (10, 10))},
    "open": {"index": (8, 8, 4), "middle": (8, 8, 4), "ring": (10, 10, 5), "pinky": (12, 12, 6),
             "thumb": ((0.75, -0.25, 0.55), (5, 5))},
}


def gloved_hand(pose="point", color="#4F86D9", cuff_len=1.4):
    """Nitrile-gloved hand. Local space: wrist at origin, fingers along +Z, palm faces -Y.
    Returns (object, tips) where tips maps finger name -> fingertip position in local space."""
    spec = POSES[pose]
    parts, tips = [], {}
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=32, ring_count=16, location=(0, 0, 0.26))
    palm = active()
    palm.scale = (0.23, 0.075, 0.27)
    parts.append(palm)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=32, ring_count=16, location=(-0.07, -0.02, 0.1))
    heel = active()  # thenar pad at the base of the thumb
    heel.scale = (0.13, 0.08, 0.13)
    parts.append(heel)
    for name, (x, segs, r) in FINGERS.items():
        p = Vector((x, -0.005, 0.47))
        d = Vector((0, 0, 1))
        ang = 0.0
        for seg_len, curl in zip(segs, spec[name]):
            ang += math.radians(curl)
            d = Vector((0, -math.sin(ang), math.cos(ang)))
            q = p + d * seg_len
            parts += capsule(p, q, r, r * 0.93)
            p = q
            r *= 0.93
        tips[name] = p.copy()
    tdir, tcurl = spec["thumb"]
    p = Vector((-0.2, -0.04, 0.12))
    d = Vector(tdir).normalized()
    for seg_len, curl in zip((0.17, 0.13), tcurl):
        d = (Matrix.Rotation(math.radians(curl), 3, "Y") @ d).normalized()
        q = p + d * seg_len
        parts += capsule(p, q, 0.055, 0.05)
        p = q
    tips["thumb"] = p.copy()
    parts += capsule((0, 0, 0.05), (0, 0, -cuff_len), 0.125, 0.16)  # wrist / forearm in the glove cuff
    hand = organic(join(parts, f"Glove_{pose}"), voxel=0.01, smooth=10)
    looks.assign(hand, nitrile(color))
    return hand, tips


def lab_mouse():
    """White lab mouse, nose toward +X, ~2.2 units long, resting on z = -0.5. Returns dict of parts."""
    parts = []
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=48, ring_count=24, location=(0, 0, 0))
    body = active()
    body.scale = (1.0, 0.58, 0.48)
    parts.append(body)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=48, ring_count=24, location=(0.95, 0, 0.08))
    head = active()
    head.scale = (0.55, 0.4, 0.37)
    parts.append(head)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=32, ring_count=16, location=(1.36, 0, 0.0))
    snout = active()
    snout.scale = (0.32, 0.21, 0.19)
    parts.append(snout)
    m = organic(join(parts, "MouseBody"), voxel=0.025, smooth=8)
    looks.assign(m, fur())
    pink = skin_pink()
    out = {"body": m}
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.065, location=(1.66, 0, 0.0))
    looks.assign(active(), pink)
    out["nose"] = active()
    for side in (-1, 1):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=32, ring_count=16, location=(0.72, side * 0.3, 0.45))
        ear = active()
        ear.scale = (0.07, 0.26, 0.27)
        ear.rotation_euler = (side * 0.35, 0.25, side * -0.5)
        looks.assign(ear, pink)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=16, ring_count=8, location=(1.18, side * 0.25, 0.2))
        eye = active()  # closed eye: a soft dark slit
        eye.scale = (0.07, 0.02, 0.012)
        eye.rotation_euler = (0, 0, side * 0.5)
        looks.assign(eye, looks.glossy("EyeLid", "#3A2A2A", 0.4))
        for k in range(3):
            a, b = Vector((1.5, side * 0.12, 0.02)), Vector((1.75, side * (0.55 + 0.08 * k), 0.12 - 0.08 * k))
            bpy.ops.mesh.primitive_cylinder_add(radius=0.004, depth=(b - a).length, vertices=6, location=(a + b) / 2)
            w = active()
            aim(w, b - a)
            looks.assign(w, looks.glossy("Whisker", "#F4F1EC", 0.3))
    # tail
    cu = bpy.data.curves.new("Tail", "CURVE")
    cu.dimensions = "3D"
    sp = cu.splines.new("BEZIER")
    pts = [(-0.9, 0, -0.25), (-1.6, 0.35, -0.42), (-2.3, -0.1, -0.46), (-2.9, 0.45, -0.47)]
    sp.bezier_points.add(len(pts) - 1)
    for bp, co in zip(sp.bezier_points, pts):
        bp.co = co
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    cu.bevel_depth = 0.055
    cu.bevel_resolution = 4
    tail = bpy.data.objects.new("Tail", cu)
    bpy.context.scene.collection.objects.link(tail)
    sp.bezier_points[-1].radius = 0.25
    tail.data.materials.append(pink)
    out["tail"] = tail
    return out


def surgical_drape(color="#3F86A8"):
    """Drape molded over the mouse body (leaves the head clear)."""
    import random

    rng = random.Random(4)
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=90, y_subdivisions=70, size=1, location=(0, 0, 0))
    d = active()
    d.name = "Drape"
    for v in d.data.vertices:
        x = -0.55 + v.co.x * 3.4  # spans x -2.25 .. 1.15
        y = v.co.y * 3.0
        inside = 1 - (x / 1.08) ** 2 - (y / 0.66) ** 2
        if inside > 0:  # over the body (body centre z=0, radius_z 0.48)
            z = 0.5 * math.sqrt(inside) + 0.03
        else:  # hangs from the body's widest point down to the table
            z = -0.48 + 0.51 * math.exp(-3.0 * -inside)
        z += 0.025 * math.sin(x * 9 + rng.random()) * math.cos(y * 7)
        if x > 0.62:  # fold back edge behind the neck
            z -= (x - 0.62) * 0.9
        v.co = (x, y, max(z, -0.49))
    d.modifiers.new("Thick", "SOLIDIFY").thickness = 0.02
    sub = d.modifiers.new("Sub", "SUBSURF")
    sub.levels = sub.render_levels = 1
    for p in d.data.polygons:
        p.use_smooth = True
    mat, bsdf = looks._principled("Drape")
    looks._set(bsdf, "Base Color", hex_to_rgba(color))
    looks._set(bsdf, "Roughness", 0.8)
    looks._set(bsdf, ["Sheen Weight", "Sheen"], 0.6)
    looks.assign(d, mat)
    return d


def mouse_brain(material=None):
    """Smooth (lissencephalic) mouse brain: two hemispheres, olfactory bulbs, ridged cerebellum.
    Front = +X, ~3 units long, centred near the origin."""
    parts = []
    for side in (-1, 1):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=48, ring_count=24, location=(0, side * 0.43, 0))
        h = active()
        h.scale = (1.25, 0.5, 0.62)
        parts.append(h)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=32, ring_count=16, location=(1.3, side * 0.2, -0.12))
        b = active()
        b.scale = (0.36, 0.19, 0.22)
        parts.append(b)
    bpy.ops.mesh.primitive_cone_add(radius1=0.28, radius2=0.4, depth=1.0, location=(-0.85, 0, -0.75), rotation=(0, -0.6, 0))
    parts.append(active())
    brain = organic(join(parts, "MouseCerebrum"), voxel=0.02, smooth=6)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=64, ring_count=32, location=(-1.35, 0, -0.18))
    cb = active()
    cb.name = "Cerebellum"
    cb.scale = (0.42, 0.72, 0.5)
    tex = bpy.data.textures.new("Folia", "MARBLE")
    tex.marble_type, tex.noise_scale, tex.turbulence = "SHARPER", 0.09, 0.6
    disp = cb.modifiers.new("Folia", "DISPLACE")
    disp.texture, disp.strength = tex, 0.05
    for p in cb.data.polygons:
        p.use_smooth = True
    mat = material or looks.tissue("MouseTissue", base_hex="#E2A3A3", crease_hex="#9A4A55", vein_scale=3.0)
    looks.assign(brain, mat)
    looks.assign(cb, mat)
    pivot = bpy.data.objects.new("MouseBrain", None)
    bpy.context.scene.collection.objects.link(pivot)
    brain.parent = cb.parent = pivot
    return pivot, brain, cb


def storm_material(name="BrainStorm", base="#E2A3A3", storm="#FF2A1A"):
    """Tissue with animated red electrical 'seizure' veins. Animate nodes['StormW'] and ['StormGain']."""
    mat = looks.tissue(name, base_hex=base, crease_hex="#9A4A55", vein_scale=3.0)
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    out = nt.nodes.get("Material Output")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.noise_dimensions = "4D"
    noise.inputs["Scale"].default_value = 2.2
    noise.inputs["Detail"].default_value = 4
    w = nt.nodes.new("ShaderNodeValue")
    w.name = "StormW"
    nt.links.new(w.outputs[0], noise.inputs["W"])
    nt.links.new(coord.outputs["Object"], noise.inputs["Vector"])
    sub = nt.nodes.new("ShaderNodeMath")
    sub.operation = "SUBTRACT"
    sub.inputs[1].default_value = 0.5
    nt.links.new(noise.outputs["Fac"], sub.inputs[0])
    ab = nt.nodes.new("ShaderNodeMath")
    ab.operation = "ABSOLUTE"
    nt.links.new(sub.outputs[0], ab.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
    ramp.color_ramp.elements[1].position = 0.03
    ramp.color_ramp.elements[1].color = (0, 0, 0, 1)
    nt.links.new(ab.outputs[0], ramp.inputs["Fac"])
    gain = nt.nodes.new("ShaderNodeValue")
    gain.name = "StormGain"
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    nt.links.new(ramp.outputs["Color"], mul.inputs[0])
    nt.links.new(gain.outputs[0], mul.inputs[1])
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = hex_to_rgba(storm)
    nt.links.new(mul.outputs[0], emit.inputs["Strength"])
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(bsdf.outputs[0], add.inputs[0])
    nt.links.new(emit.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs["Surface"])
    return mat


def animate_value(mat, node_name, frames_values):
    node = mat.node_tree.nodes[node_name]
    for f, v in frames_values:
        node.outputs[0].default_value = v
        node.outputs[0].keyframe_insert("default_value", frame=f)


def vial(liquid="#59D8FF", height=1.0, glow=0.0, cap="#E9EEF3"):
    """Small glass vial with liquid + cap. Base at origin, up = +Z. Returns (pivot, liquid_obj)."""
    pivot = bpy.data.objects.new("Vial", None)
    bpy.context.scene.collection.objects.link(pivot)
    r = 0.17
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=height, vertices=40, location=(0, 0, height / 2))
    g = active()
    bev = g.modifiers.new("Round", "BEVEL")
    bev.width, bev.segments = 0.03, 3
    looks.assign(g, glass())
    lh = height * 0.62
    bpy.ops.mesh.primitive_cylinder_add(radius=r * 0.86, depth=lh, vertices=40, location=(0, 0, lh / 2 + 0.03))
    liq = active()
    mat, bsdf = looks._principled("Liquid")
    looks._set(bsdf, "Base Color", hex_to_rgba(liquid))
    looks._set(bsdf, "Roughness", 0.1)
    looks._set(bsdf, ["Transmission Weight", "Transmission"], 0.6)
    looks._set(bsdf, ["Emission Color", "Emission"], hex_to_rgba(liquid))
    looks._set(bsdf, "Emission Strength", glow)
    looks.assign(liq, mat)
    bpy.ops.mesh.primitive_cylinder_add(radius=r * 1.08, depth=0.16, vertices=40, location=(0, 0, height + 0.06))
    c = active()
    looks.assign(c, looks.glossy("Cap", cap, 0.35))
    for o in (g, liq, c):
        o.parent = pivot
    return pivot, liq


def sewing_pin(length=3.0, head_r=0.16, head="#E5322D"):
    """Pin pointing down (-Z) with a ball head at the top; tip at origin."""
    pivot = bpy.data.objects.new("Pin", None)
    bpy.context.scene.collection.objects.link(pivot)
    bpy.ops.mesh.primitive_cone_add(radius1=0.0, radius2=0.035, depth=length, vertices=24, location=(0, 0, length / 2))
    s = active()
    looks.assign(s, looks.glossy("PinSteel", "#D8DDE3", 0.12, 1.0))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=head_r, segments=32, ring_count=16, location=(0, 0, length + head_r * 0.6))
    h = active()
    looks.assign(h, looks.glossy("PinHead", head, 0.15))
    s.parent = h.parent = pivot
    return pivot, h


def droplet(radius=0.1, color="#3FD7FF"):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, segments=48, ring_count=24)
    d = active()
    d.scale = (1, 1, 0.85)
    for p in d.data.polygons:
        p.use_smooth = True
    mat, bsdf = looks._principled("Droplet")
    looks._set(bsdf, "Base Color", hex_to_rgba(color))
    looks._set(bsdf, "Roughness", 0.02)
    looks._set(bsdf, ["Transmission Weight", "Transmission"], 0.85)
    looks._set(bsdf, ["Emission Color", "Emission"], hex_to_rgba(color))
    looks._set(bsdf, "Emission Strength", 0.6)
    looks.assign(d, mat)
    return d


def needle_rig():
    """Stereotaxic-style robotic needle. Needle tip at local origin pointing -Z.
    Returns (pivot, status_light_material)."""
    pivot = bpy.data.objects.new("Rig", None)
    bpy.context.scene.collection.objects.link(pivot)
    chrome = looks.glossy("RigChrome", "#DDE3EC", 0.08, 1.0)
    dark = looks.glossy("RigDark", "#22262E", 0.35, 0.8)
    objs = []
    bpy.ops.mesh.primitive_cone_add(radius1=0.006, radius2=0.03, depth=1.2, vertices=24, location=(0, 0, 0.6))
    looks.assign(active(), chrome)
    objs.append(active())
    bpy.ops.mesh.primitive_cylinder_add(radius=0.09, depth=1.2, vertices=32, location=(0, 0, 1.8))
    looks.assign(active(), chrome)
    objs.append(active())
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 3.3))
    blk = active()
    blk.scale = (0.5, 0.42, 1.9)
    blk.modifiers.new("Bev", "BEVEL").width = 0.05
    looks.assign(blk, dark)
    objs.append(blk)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0.75, 4.4))
    arm = active()
    arm.scale = (0.3, 1.6, 0.3)
    arm.modifiers.new("Bev", "BEVEL").width = 0.04
    looks.assign(arm, dark)
    objs.append(arm)
    status = looks.neon("RigStatus", "#FF2D2D", 6)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.07, location=(0, -0.22, 3.9))
    looks.assign(active(), status)
    objs.append(active())
    bpy.ops.mesh.primitive_torus_add(major_radius=0.12, minor_radius=0.02, location=(0, 0, 2.45))
    looks.assign(active(), looks.neon("RigRing", "#5CE1FF", 5))
    objs.append(active())
    for o in objs:
        o.parent = pivot
    return pivot, status


# ============================================================================ annotations
def red_arrow(length=1.6, radius=0.07):
    """Glossy red 3D arrow along +Z from the origin (tail) to the tip."""
    pivot = bpy.data.objects.new("Arrow", None)
    bpy.context.scene.collection.objects.link(pivot)
    mat = glossy_red()
    shaft = length - radius * 4
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=shaft, vertices=32, location=(0, 0, shaft / 2))
    looks.assign(active(), mat)
    active().parent = pivot
    bpy.ops.mesh.primitive_cone_add(radius1=radius * 2.6, radius2=0, depth=radius * 4, vertices=32,
                                    location=(0, 0, shaft + radius * 2))
    looks.assign(active(), mat)
    active().parent = pivot
    return pivot


def red_x(size=1.0):
    pivot = bpy.data.objects.new("RedX", None)
    bpy.context.scene.collection.objects.link(pivot)
    mat = glossy_red()
    for a in (math.pi / 4, -math.pi / 4):
        bpy.ops.mesh.primitive_cube_add(size=1)
        b = active()
        b.scale = (size * 1.2, size * 0.22, size * 0.22)
        b.rotation_euler = (math.pi / 2, a, 0)
        b.modifiers.new("Bev", "BEVEL").width = size * 0.05
        looks.assign(b, mat)
        b.parent = pivot
    return pivot


def label3d(text, color="#FFFFFF", size=0.5, extrude=0.05, emission=0.0, align="CENTER", material=None):
    """Extruded, bevelled 3D text facing -Y (toward a camera on the -Y side)."""
    cu = bpy.data.curves.new("Label", "FONT")
    cu.body = text
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.extrude = extrude
    cu.bevel_depth = extrude * 0.35
    cu.bevel_resolution = 3
    f = font()
    if f:
        cu.font = f
    obj = bpy.data.objects.new("Label", cu)
    bpy.context.scene.collection.objects.link(obj)
    obj.rotation_euler = (math.pi / 2, 0, 0)
    obj.scale = (size, size, size)
    if material is None:
        material = looks.glossy(f"Label{color}", color, 0.3)
        if emission:
            bsdf = material.node_tree.nodes.get("Principled BSDF")
            looks._set(bsdf, ["Emission Color", "Emission"], hex_to_rgba(color))
            looks._set(bsdf, "Emission Strength", emission)
    obj.data.materials.append(material)
    return obj


def question_mark(size=2.0):
    q = label3d("?", RED, size, extrude=0.12, material=glossy_red())
    return q


def dimension_line(a, b, color=RED, thickness=0.025, tick=0.25):
    """Measurement line between a and b (with end ticks), drawn in the XZ plane facing -Y."""
    a, b = Vector(a), Vector(b)
    pivot = bpy.data.objects.new("Dimension", None)
    bpy.context.scene.collection.objects.link(pivot)
    mat = glossy_red() if color == RED else looks.neon("Dim", color, 1.0)
    v = b - a
    bpy.ops.mesh.primitive_cylinder_add(radius=thickness, depth=v.length, vertices=16, location=(a + b) / 2)
    aim(active(), v)
    looks.assign(active(), mat)
    active().parent = pivot
    perp = Vector((0, 0, 1)) if abs(v.z) < abs(v.x) else Vector((1, 0, 0))
    for p in (a, b):
        bpy.ops.mesh.primitive_cylinder_add(radius=thickness, depth=tick, vertices=16, location=p)
        aim(active(), perp)
        looks.assign(active(), mat)
        active().parent = pivot
    return pivot


class Counter:
    """Counting number as 3D text: one object per distinct value, toggled by visibility keys."""

    def __init__(self, location, start, end, f0, frames, fmt="{:.0f}", size=0.6, color=RED, material=None):
        self.objs = {}
        for f in range(f0, f0 + frames + 1):
            u = ease_out((f - f0) / frames)
            txt = fmt.format(start + (end - start) * u)
            if txt not in [o.data.body for o in self.objs.values()]:
                o = label3d(txt, color, size, material=material or (glossy_red() if color == RED else None))
                o.location = location
                self.objs[f] = o
        keys = sorted(self.objs)
        for i, f in enumerate(keys):
            o = self.objs[f]
            nxt = keys[i + 1] if i + 1 < len(keys) else 10**6
            for frame, hidden in sorted({1: True, max(1, f - 1): True, f: False, nxt: True}.items()):
                o.hide_render = hidden
                o.keyframe_insert("hide_render", frame=frame)

    def all(self):
        return list(self.objs.values())


def pop_scale(obj, f_in, f_out=None, scale=1.0, dur=8, total=None):
    """Bouncy pop-in at f_in (and quick shrink-out at f_out)."""
    s0 = obj.scale.copy() if hasattr(obj.scale, "copy") else Vector((scale, scale, scale))
    base = Vector(s0) * scale if scale != 1.0 else Vector(s0)
    frames = sorted({1, f_in - 1, *range(f_in, f_in + dur + 1)} | ({f_out - 6, f_out} if f_out else set()))
    for f in frames:
        if f < f_in:
            k = 0.0
        else:
            k = back_out((f - f_in) / dur)
            if f_out and f >= f_out - 6:
                k *= max(0.0, (f_out - f) / 6)
        obj.scale = base * max(k, 1e-4)
        obj.keyframe_insert("scale", frame=max(1, f))
