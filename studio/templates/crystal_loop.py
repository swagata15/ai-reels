"""Crystal loop: a grid of iridescent bevelled blocks rippling in a wave while the camera orbits.

Oddly-satisfying, perfectly seamless loop.
params: grid (int, default 9), wave (float wave count across the grid, default 1.5),
        amplitude (float, default 1.2), orbit (bool, default true)
"""
from __future__ import annotations

import math

import bpy

from .. import looks, scene as sc


def build(scene, spec):
    p = spec.params
    n = int(p.get("grid", 9))
    wave = float(p.get("wave", 1.5))
    amp = float(p.get("amplitude", 1.2))
    orbit = bool(p.get("orbit", True))
    bg, *accents = spec.palette

    sc.setup_world(scene, bg, 0.8)
    cam = sc.add_camera(scene, location=(0, -21, 15), target=(0, 0, 0), lens=45)
    sc.add_area_light(scene, "Key", (6, -6, 10), energy=1500, size=8)
    sc.add_area_light(scene, "Fill", (-8, 2, 5), energy=700, size=6, color=(0.7, 0.8, 1.0))
    sc.add_area_light(scene, "Back", (0, 10, 4), energy=900, size=6, color=(1.0, 0.6, 0.9))

    mats = [looks.iridescent(f"Crystal{i}", accents[i % len(accents)], accents[(i + 1) % len(accents)]) for i in range(len(accents))]
    spacing = 1.05
    blocks = []
    for ix in range(n):
        for iy in range(n):
            x = (ix - (n - 1) / 2) * spacing
            y = (iy - (n - 1) / 2) * spacing
            bpy.ops.mesh.primitive_cube_add(size=0.9, location=(x, y, 0))
            b = bpy.context.active_object
            bev = b.modifiers.new("Bevel", "BEVEL")
            bev.width = 0.08
            bev.segments = 3
            looks.assign(b, mats[(ix + iy) % len(mats)])
            dist = math.hypot(x, y) / (n * spacing / 2)
            blocks.append((b, x, y, dist))

    total = spec.frames
    for f in range(1, total + 1):
        t = sc.loop_phase(f, total)
        for b, x, y, dist in blocks:
            h = math.sin(t - dist * wave * 2 * math.pi)
            b.location = (x, y, amp * h)
            b.scale = (1, 1, 1 + 0.6 * (h + 1))
            b.rotation_euler = (0, 0, 0.25 * math.pi * (h + 1) / 2)
            b.keyframe_insert("location", frame=f)
            b.keyframe_insert("scale", frame=f)
            b.keyframe_insert("rotation_euler", frame=f)
        if orbit:
            r = 21
            cam.location = (r * math.sin(t), -r * math.cos(t), 15)
            sc.look_at(cam, (0, 0, 0))
            cam.keyframe_insert("location", frame=f)
            cam.keyframe_insert("rotation_euler", frame=f)
    sc.linearize(scene)
