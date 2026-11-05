"""Kinetic title: punchy text lines pop in one by one over slowly drifting neon shapes.

The reel's `text` list is the script (first line = the hook). Text is kept inside
Instagram's safe zone automatically and scaled to fit the width.
params: stagger_s (seconds between lines, default 0.6), font (path to .ttf/.otf, optional)
"""
from __future__ import annotations

import math

import bpy

from .. import looks, scene as sc
from ..text import TextBlock, ortho_camera


def build(scene, spec):
    p = spec.params
    lines = spec.text or ["YOUR HOOK HERE", "say it in", "3 seconds"]
    bg, *accents = spec.palette
    sc.setup_world(scene, bg, 1.0)
    ortho_camera(scene)

    # Background: big slow neon rings, off-centre.
    shapes = []
    for i, (x, z, r) in enumerate([(-3.2, 4.5, 3.0), (3.6, -3.5, 3.8), (2.5, 6.5, 1.6)]):
        bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=0.05, location=(x, 8, z), rotation=(math.pi / 2, 0, 0))
        ring = bpy.context.active_object
        looks.assign(ring, looks.neon(f"BgRing{i}", accents[i % len(accents)], 1.5))
        shapes.append((ring, x, z, i))

    text = TextBlock(scene, lines, ["#FFFFFF", *accents], font=p.get("font"))

    total, fps = spec.frames, spec.fps
    for f in range(1, total + 1):
        t = sc.loop_phase(f, total)
        for ring, x, zz, i in shapes:
            ring.location = (x + 0.4 * math.sin(t + i), 8, zz + 0.4 * math.cos(t + i * 2))
            ring.rotation_euler = (math.pi / 2 + 0.25 * math.sin(t + i), 0.25 * math.cos(t), 0)
            ring.keyframe_insert("location", frame=f)
            ring.keyframe_insert("rotation_euler", frame=f)
        text.animate(f, total, fps, t, stagger_s=float(p.get("stagger_s", 0.6)))
    sc.linearize(scene)
