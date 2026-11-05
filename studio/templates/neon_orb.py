"""Neon orb: a glossy core wrapped in glowing gyroscope rings + orbiting sparks.

Perfect seamless loop - great as a hypnotic background for voice-over / text reels.
params: rings (int, default 3), sparks (int, default 40), spin (float turns per loop, default 1)
"""
from __future__ import annotations

import math
import random

import bpy

from .. import looks, scene as sc


def build(scene, spec):
    p = spec.params
    rng = random.Random(spec.seed)
    bg, *accents = spec.palette
    sc.setup_world(scene, bg, 0.6)
    sc.add_camera(scene, location=(0, -19, 0.5), target=(0, 0, 0), lens=55)
    sc.add_area_light(scene, "Key", (4, -6, 6), energy=800, size=6)
    sc.add_area_light(scene, "Rim", (-5, 5, 2), energy=600, size=4, color=(0.6, 0.7, 1.0))

    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.4, segments=64, ring_count=32)
    core = bpy.context.active_object
    bpy.ops.object.shade_smooth()
    looks.assign(core, looks.iridescent("Core", accents[0], accents[-1]))

    rings = []
    for i in range(int(p.get("rings", 3))):
        bpy.ops.mesh.primitive_torus_add(major_radius=2.2 + i * 0.55, minor_radius=0.04, major_segments=128)
        ring = bpy.context.active_object
        looks.assign(ring, looks.neon(f"Ring{i}", accents[i % len(accents)], 12))
        rings.append(ring)

    sparks = []
    spark_mat = looks.neon("Spark", accents[-1], 20)
    for i in range(int(p.get("sparks", 40))):
        bpy.ops.mesh.primitive_ico_sphere_add(radius=rng.uniform(0.03, 0.08), subdivisions=2)
        s = bpy.context.active_object
        looks.assign(s, spark_mat)
        sparks.append((s, rng.uniform(3.2, 5.0), rng.uniform(-1.2, 1.2), rng.uniform(0, 2 * math.pi), rng.choice([1, 2])))

    total = spec.frames
    spin = float(p.get("spin", 1))
    for f in range(1, total + 1):
        t = sc.loop_phase(f, total)
        core.rotation_euler = (0, 0, t * spin)
        core.scale = [1 + 0.04 * math.sin(2 * t)] * 3
        core.keyframe_insert("rotation_euler", frame=f)
        core.keyframe_insert("scale", frame=f)
        for i, ring in enumerate(rings):
            d = 1 if i % 2 == 0 else -1
            ring.rotation_euler = (t * d * (i + 1) * spin + i, 0.6 * i + t * d * spin, 0)
            ring.keyframe_insert("rotation_euler", frame=f)
        for s, radius, height, phase, speed in sparks:
            a = phase + t * speed
            s.location = (radius * math.cos(a), radius * math.sin(a), height + 0.3 * math.sin(t + phase))
            s.keyframe_insert("location", frame=f)
    sc.linearize(scene)
