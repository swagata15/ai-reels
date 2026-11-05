"""Holo brain: a holographic brain under an MRI scan ring while a robotic probe needle
moves in, injects a glowing "therapy" that spreads, and pulls back out. Data particles
drift up and kinetic text sits in the top safe zone.

Made for AI x medicine / biotech news reels. Seamless loop.
params: stagger_s (default 0.7), particles (default 60), sway_deg (default 10),
        font (optional .ttf/.otf)
"""
from __future__ import annotations

import math
import random

import bpy
from mathutils import Matrix, Vector

from .. import looks, scene as sc
from ..spec import hex_to_rgba
from ..text import ORTHO_H, ORTHO_W, SAFE_TOP_Z, TextBlock, ortho_camera

# Cerebrum ellipsoid (long axis = X; camera sees the left side profile, front = +X).
A, B, C = 2.9, 2.1, 2.0
CENTRE = Vector((0.0, 0.0, -1.5))
TILT = math.radians(10)


def _smooth(edge0, edge1, x):
    k = min(1.0, max(0.0, (x - edge0) / (edge1 - edge0)))
    return k * k * (3 - 2 * k)


def _folds(name, scale, depth):
    tex = bpy.data.textures.new(name, "CLOUDS")
    tex.noise_basis = "VORONOI_CRACKLE"
    tex.noise_scale = scale
    tex.noise_depth = depth
    return tex


def _cerebrum(name, subdiv):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv, radius=1.0)
    obj = bpy.context.active_object
    obj.name = name
    for v in obj.data.vertices:
        x, y, z = v.co  # unit sphere
        # Back of the brain slightly narrower and lifted (occipital), front rounder.
        taper = 1 - 0.12 * _smooth(0.0, -1.0, x)
        y *= taper
        z = z * taper + 0.08 * _smooth(-0.3, -1.0, x)
        # Flat-ish underside with the temporal lobe bulging down at the front-middle.
        if z < -0.25:
            temporal = _smooth(-0.6, 0.05, x) * _smooth(0.85, 0.35, x)
            z = -0.25 + (z + 0.25) * (0.45 + 0.5 * temporal)
        # Midline fissure along the top.
        z -= 0.09 * math.exp(-((y / 0.08) ** 2)) * _smooth(0.2, 0.8, z)
        v.co = (x * A, y * B, z * C)
    for tex, strength in ((_folds(f"{name}Gyri", 0.7, 0), -0.32), (_folds(f"{name}Fine", 0.3, 0), -0.06)):
        disp = obj.modifiers.new(tex.name, "DISPLACE")
        disp.texture = tex
        disp.strength = strength
        disp.mid_level = 0.5
    smooth = obj.modifiers.new("RoundGyri", "SMOOTH")  # turns crackle ridges into soft gyri
    smooth.factor = 0.9
    smooth.iterations = 8
    bpy.ops.object.shade_smooth()
    return obj


def _cerebellum(name):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, segments=64, ring_count=32)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (0.85, 1.25, 0.6)
    obj.location = (-A * 0.62, 0, -C * 0.55)
    tex = bpy.data.textures.new(f"{name}Folia", "MARBLE")
    tex.marble_type = "SHARPER"
    tex.noise_scale = 0.12
    tex.turbulence = 1.0
    disp = obj.modifiers.new("Folia", "DISPLACE")
    disp.texture = tex
    disp.strength = 0.06
    disp.direction = "NORMAL"
    bpy.ops.object.shade_smooth()
    return obj


def _brainstem(name):
    bpy.ops.mesh.primitive_cone_add(radius1=0.2, radius2=0.36, depth=4.0, vertices=32)
    obj = bpy.context.active_object
    obj.name = name
    obj.location = (-A * 0.22, 0, -C * 1.45)
    obj.rotation_euler = (0, math.radians(-18), 0)
    bpy.ops.object.shade_smooth()
    return obj


def build(scene, spec):
    p = spec.params
    rng = random.Random(spec.seed)
    bg, *accents = spec.palette
    brain_col, therapy_col, probe_col = (accents * 3)[:3]

    sc.setup_world(scene, bg, 1.0)
    ortho_camera(scene)

    pivot = bpy.data.objects.new("BrainPivot", None)
    scene.collection.objects.link(pivot)
    pivot.location = CENTRE

    holo = looks.hologram("BrainHolo", brain_col, 6.0, 0.42)
    holo_soft = looks.hologram("BrainHoloSoft", brain_col, 3.0, 0.55)
    parts = [(_cerebrum("Cerebrum", 6), holo), (_cerebellum("Cerebellum"), holo), (_brainstem("Brainstem"), holo_soft)]
    for obj, mat in parts:
        looks.assign(obj, mat)
        obj.parent = pivot

    # MRI scan: glowing elliptical ring + faint filled slice sweeping front-to-back.
    bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.016, major_segments=160, minor_segments=8)
    scan = bpy.context.active_object
    looks.assign(scan, looks.neon("Scan", therapy_col, 14))
    bpy.ops.mesh.primitive_circle_add(radius=1.0, vertices=96, fill_type="NGON")
    scan_fill = bpy.context.active_object
    looks.assign(scan_fill, looks.neon("ScanFill", therapy_col, 0.25))
    for obj in (scan, scan_fill):
        obj.parent = pivot

    # Injection site on the temporal lobe (local brain space).
    site_dir = Vector((0.35, -0.85, -0.25)).normalized()
    s = 1 / math.sqrt((site_dir.x / A) ** 2 + (site_dir.y / B) ** 2 + (site_dir.z / C) ** 2)
    site_surface = site_dir * s
    entry_origin = Vector((ORTHO_W / 2 + 1.5, -5.0, CENTRE.z + 4.2))

    # Probe needle: chrome-ish shaft + glowing tip; built along +Z then aimed every frame.
    bpy.ops.mesh.primitive_cone_add(radius1=0.1, radius2=0.02, depth=2.0, vertices=24)
    needle = bpy.context.active_object
    looks.assign(needle, looks.glossy("Needle", "#E8ECF5", 0.1, 1.0))
    bpy.ops.mesh.primitive_cylinder_add(radius=0.012, depth=2.0, vertices=12)
    guide = bpy.context.active_object
    looks.assign(guide, looks.neon("ProbeLine", probe_col, 16))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, segments=16, ring_count=8)
    tip = bpy.context.active_object
    looks.assign(tip, looks.neon("ProbeTip", "#FFFFFF", 40))

    # Therapy glow spreading from the injection site + ripple rings.
    bpy.ops.mesh.primitive_ico_sphere_add(radius=1.0, subdivisions=4)
    glow = bpy.context.active_object
    looks.assign(glow, looks.hologram("Therapy", therapy_col, 12.0, 0.6))
    glow.parent = pivot
    ripples = []
    for i in range(3):
        bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.02, major_segments=96, minor_segments=6)
        r = bpy.context.active_object
        looks.assign(r, looks.neon(f"Ripple{i}", therapy_col, 8))
        r.parent = pivot
        ripples.append(r)
    glow_light_data = bpy.data.lights.new("TherapyLight", "POINT")
    glow_light_data.color = hex_to_rgba(therapy_col)[:3]
    glow_light = bpy.data.objects.new("TherapyLight", glow_light_data)
    scene.collection.objects.link(glow_light)
    glow_light.parent = pivot

    # Data particles drifting upward.
    particles = []
    dot_mats = [looks.neon(f"Dot{i}", c, 10) for i, c in enumerate(accents)]
    for _ in range(int(p.get("particles", 60))):
        bpy.ops.mesh.primitive_ico_sphere_add(radius=rng.uniform(0.025, 0.06), subdivisions=1)
        d = bpy.context.active_object
        looks.assign(d, rng.choice(dot_mats))
        particles.append((d, rng.uniform(-ORTHO_W / 2, ORTHO_W / 2), rng.uniform(-2, 4), rng.random(), rng.choice([1, 2])))

    text = TextBlock(scene, spec.text or ["CLAUDE JUST DID", "BRAIN SURGERY"],
                     ["#FFFFFF", therapy_col, probe_col, brain_col], z_top=SAFE_TOP_Z,
                     z_bottom=CENTRE.z + C + 0.7, y=-7.0, sizes=(2.0, 1.4), font=p.get("font"))

    total, fps = spec.frames, spec.fps
    sway = math.radians(float(p.get("sway_deg", 10)))
    lo_z = -ORTHO_H / 2 - 0.5
    span = (SAFE_TOP_Z + 1.0) - lo_z

    def phase(a, b, u):  # 0..1 progress of u through [a, b] (fractions of the loop), eased
        return _smooth(a, b, u)

    for f in range(1, total + 1):
        t = sc.loop_phase(f, total)
        u = (f - 1) / total

        pivot.rotation_euler = (TILT, 0, sway * math.sin(t))
        pivot.location = CENTRE + Vector((0, 0, 0.1 * math.sin(2 * t)))
        for prop in ("rotation_euler", "location"):
            pivot.keyframe_insert(prop, frame=f)
        m = Matrix.Translation(pivot.location) @ pivot.rotation_euler.to_matrix().to_4x4()

        # Scan slice at x; cross-section radii shrink toward the ends of the ellipsoid.
        x = A * 0.8 * math.sin(t)
        k = math.sqrt(max(0.0, 1 - (x / A) ** 2))
        for obj in (scan, scan_fill):
            obj.location = (x, 0, 0)
            obj.rotation_euler = (0, math.pi / 2, 0)
            obj.scale = (C * k * 1.03, B * k * 1.03, 1)
            for prop in ("location", "rotation_euler", "scale"):
                obj.keyframe_insert(prop, frame=f)

        # Needle timeline: approach -> insert -> hold (inject) -> retract.
        approach = phase(0.06, 0.28, u)
        insert = phase(0.28, 0.36, u)
        retract = phase(0.84, 0.97, u)
        depth = (-3.5 + 3.0 * approach + 0.95 * insert) * (1 - retract) + (-3.5) * retract
        site_world = m @ site_surface
        direction = (site_world - entry_origin).normalized()
        tip_pos = site_world + direction * depth
        start = tip_pos - direction * 9.0
        vec = tip_pos - start
        mid = start + vec / 2
        aim = vec.to_track_quat("Z", "Y").to_euler()
        needle.location, needle.rotation_euler, needle.scale = mid, aim, (1, 1, vec.length / 2)
        guide.location, guide.rotation_euler, guide.scale = mid, aim, (3.0, 3.0, vec.length / 2)
        tip.location = tip_pos
        tip.scale = [1 + 0.3 * insert * (1 - retract) * (1 + math.sin(16 * t))] * 3
        for obj in (needle, guide):
            for prop in ("location", "rotation_euler", "scale"):
                obj.keyframe_insert(prop, frame=f)
        tip.keyframe_insert("location", frame=f)
        tip.keyframe_insert("scale", frame=f)

        # Therapy spreads while the needle is in, fades as the loop closes.
        spread = phase(0.36, 0.7, u) * (1 - phase(0.88, 1.0, u))
        inside = site_surface + (-site_dir) * 0.55
        glow.location = inside
        glow.scale = [max(0.001, 0.75 * spread * (1 + 0.06 * math.sin(6 * t)))] * 3
        glow.keyframe_insert("location", frame=f)
        glow.keyframe_insert("scale", frame=f)
        glow_light.location = inside
        glow_light_data.energy = 600 * spread
        glow_light.keyframe_insert("location", frame=f)
        glow_light_data.keyframe_insert("energy", frame=f)
        face = site_dir.to_track_quat("Z", "Y").to_euler()
        for i, r in enumerate(ripples):
            ring_u = ((u - 0.38) * 3 - i / 3) % 1.0 if 0.38 <= u <= 0.85 else 0.0
            radius = 0.2 + 1.3 * ring_u
            r.location = site_surface + site_dir * 0.02
            r.rotation_euler = face
            r.scale = [max(0.001, radius * (1 - ring_u) ** 0.3 if ring_u > 0 else 0.001)] * 3
            for prop in ("location", "rotation_euler", "scale"):
                r.keyframe_insert(prop, frame=f)

        for d, px, py, ph, speed in particles:
            pu = (ph + u * speed) % 1.0
            d.location = (px + 0.15 * math.sin(t + ph * 6), py, lo_z + pu * span)
            d.keyframe_insert("location", frame=f)

        text.animate(f, total, fps, t, stagger_s=float(p.get("stagger_s", 0.7)))

    sc.linearize(scene)
    for block in (glow_light_data,):
        ad = block.animation_data
        if ad and ad.action:
            for fc in sc._fcurves(ad.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
