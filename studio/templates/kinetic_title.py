"""Kinetic title: punchy text lines pop in one by one over slowly drifting neon shapes.

The reel's `text` list is the script (first line = the hook). Text is kept inside
Instagram's safe zone automatically and scaled to fit the width.
params: stagger_s (seconds between lines, default 0.6), font (path to .ttf/.otf, optional)
"""
from __future__ import annotations

import math

import bpy

from .. import looks, scene as sc
from ..spec import REEL_HEIGHT, SAFE_BOTTOM_PX, SAFE_TOP_PX

ORTHO_H = 16.0  # world units across the full 1920px height
ORTHO_W = ORTHO_H * 9 / 16
MAX_TEXT_W = ORTHO_W * 0.84


def _px_to_units(px: float) -> float:
    return px / REEL_HEIGHT * ORTHO_H


def build(scene, spec):
    p = spec.params
    lines = spec.text or ["YOUR HOOK HERE", "say it in", "3 seconds"]
    bg, *accents = spec.palette
    sc.setup_world(scene, bg, 1.0)

    cam = sc.add_camera(scene, location=(0, -30, 0), target=(0, 0, 0))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = ORTHO_H

    font = None
    if p.get("font"):
        font = bpy.data.fonts.load(p["font"], check_existing=True)

    # Background: big slow neon rings, off-centre.
    shapes = []
    for i, (x, z, r) in enumerate([(-3.2, 4.5, 3.0), (3.6, -3.5, 3.8), (2.5, 6.5, 1.6)]):
        bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=0.05, location=(x, 8, z), rotation=(math.pi / 2, 0, 0))
        ring = bpy.context.active_object
        looks.assign(ring, looks.neon(f"BgRing{i}", accents[i % len(accents)], 1.5))
        shapes.append((ring, x, z, i))

    # Text block centred inside the safe zone.
    safe_top = ORTHO_H / 2 - _px_to_units(SAFE_TOP_PX)
    safe_bottom = -ORTHO_H / 2 + _px_to_units(SAFE_BOTTOM_PX)
    centre_z = (safe_top + safe_bottom) / 2
    texts = []
    for i, line in enumerate(lines):
        curve = bpy.data.curves.new(f"Line{i}", "FONT")
        curve.body = line
        curve.align_x = "CENTER"
        curve.align_y = "CENTER"
        curve.extrude = 0.06
        curve.bevel_depth = 0.01
        if font:
            curve.font = font
        obj = bpy.data.objects.new(f"Line{i}", curve)
        scene.collection.objects.link(obj)
        obj.rotation_euler = (math.pi / 2, 0, 0)
        hook = i == 0
        color = "#FFFFFF" if hook else accents[(i - 1) % len(accents)]
        looks.assign(obj, looks.neon(f"Text{i}", color, 3.0 if hook else 4.0))
        texts.append(obj)

    bpy.context.view_layer.update()
    sizes = []
    for i, obj in enumerate(texts):
        base = 2.2 if i == 0 else 1.5
        w = obj.dimensions.x * base
        sizes.append(base * min(1.0, MAX_TEXT_W / w) if w else base)

    gap = 0.45
    heights = [s * 1.0 + gap for s in sizes]
    total_h = sum(heights)
    z = centre_z + total_h / 2
    rest = []
    for obj, h in zip(texts, heights):
        z -= h / 2
        rest.append(z)
        z -= h / 2

    total = spec.frames
    fps = spec.fps
    stagger = max(1, round(float(p.get("stagger_s", 0.6)) * fps))
    pop = max(4, round(0.33 * fps))
    outro = max(4, round(0.4 * fps))
    outro_start = total - outro

    for f in range(1, total + 1):
        t = sc.loop_phase(f, total)
        for ring, x, zz, i in shapes:
            ring.location = (x + 0.4 * math.sin(t + i), 8, zz + 0.4 * math.cos(t + i * 2))
            ring.rotation_euler = (math.pi / 2 + 0.25 * math.sin(t + i), 0.25 * math.cos(t), 0)
            ring.keyframe_insert("location", frame=f)
            ring.keyframe_insert("rotation_euler", frame=f)
        for i, (obj, size, z_rest) in enumerate(zip(texts, sizes, rest)):
            start = 4 + i * stagger
            k = (f - start) / pop
            if k <= 0:
                s = 0.0
            elif k >= 1:
                s = 1.0
            else:
                s = _back_out(k)
            if f >= outro_start:
                s *= max(0.0, 1 - _ease_in((f - outro_start) / outro))
            obj.scale = [size * s] * 3
            obj.location = (0, 0, z_rest - 0.4 * (1 - min(1.0, max(0.0, k))))
            obj.rotation_euler = (math.pi / 2, 0.03 * math.sin(t * 2 + i), 0)
            obj.keyframe_insert("scale", frame=f)
            obj.keyframe_insert("location", frame=f)
            obj.keyframe_insert("rotation_euler", frame=f)
    sc.linearize(scene)


def _back_out(x: float, c: float = 1.9) -> float:
    """Overshoot easing - the 'pop' that makes kinetic type feel alive."""
    x -= 1
    return 1 + (c + 1) * x**3 + c * x**2


def _ease_in(x: float) -> float:
    return x * x * x
