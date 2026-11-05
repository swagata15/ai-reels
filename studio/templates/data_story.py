"""Data story: research-backed stat reels. A sequence of "beats" (hook -> stat / bar chart ->
takeaway -> source + handle end card) rendered as a crisp overlay over a topical 3D background.

spec.text              hook lines (first line = biggest)
params.hook_s          [start, end] seconds for the hook (default [0, 2.8])
params.background      "network" | "brain" | "neon_orb" | "crystal_loop"   (+ params.bg_params)
params.dim             0..1 darkening of the background behind text (default 0.35)
params.beats           list of beats, each with "type" and "at": [start_s, end_s]:
  {"type": "stat", "kicker": "MIT MEDIA LAB · 2025", "value": 83, "suffix": "%", "decimals": 0,
   "prefix": "", "ring": 0.83, "label": ["couldn't quote", "their own essay"]}
  {"type": "bars", "kicker": "...", "items": [{"label": "...", "value": 83, "suffix": "%"}, ...],
   "label": ["optional caption line"]}
  {"type": "text", "lines": ["Takeaway line", "smaller line"], "sizes": [1.2, 0.8], "colors": [...]}
  {"type": "end", "handle": "@the.ai.gal", "tagline": "...", "source": ["Source: ...", "..."]}
"""
from __future__ import annotations

import dataclasses
import math
import random

import bpy
from mathutils import Vector

from .. import looks, scene as sc
from ..text import ORTHO_W, SAFE_BOTTOM_Z, SAFE_TOP_Z, back_out, overlay_scene

MAX_W = ORTHO_W * 0.86
_MATS: dict = {}


# ----------------------------------------------------------------------------- overlay helpers
def _mat(color, strength=1.0):
    key = (color, round(strength, 3))
    if key not in _MATS or _MATS[key].name not in bpy.data.materials:
        _MATS[key] = looks.neon(f"Ov{color}{strength}", color, strength)
    return _MATS[key]


def _text(ov, body, color, size, z, *, x=0.0, align="CENTER", strength=1.0, max_w=MAX_W, font=None):
    curve = bpy.data.curves.new("Txt", "FONT")
    curve.body = body
    curve.align_x = align
    curve.align_y = "CENTER"
    curve.extrude = 0.01
    if font:
        curve.font = font
    obj = bpy.data.objects.new("Txt", curve)
    ov.collection.objects.link(obj)
    obj.rotation_euler = (math.pi / 2, 0, 0)
    obj.location = (x, 0, z)
    looks.assign(obj, _mat(color, strength))
    bpy.context.view_layer.update()
    w = obj.dimensions.x
    scale = size * min(1.0, max_w / (w * size)) if w else size
    return obj, scale


def _plane(ov, name, color_rgba, alpha, size_xy, loc):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = color_rgba
    mx = nt.nodes.new("ShaderNodeMixShader")
    mx.inputs["Fac"].default_value = alpha
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs[0])
    mesh = bpy.data.meshes.new(name)
    sx, sz = size_xy[0] / 2, size_xy[1] / 2
    mesh.from_pydata([(-sx, 0, -sz), (sx, 0, -sz), (sx, 0, sz), (-sx, 0, sz)], [], [(0, 1, 2, 3)])
    obj = bpy.data.objects.new(name, mesh)
    ov.collection.objects.link(obj)
    obj.location = loc
    obj.data.materials.append(mat)
    return obj


def _ring(ov, color, dim_color, radius, z, thickness=0.13):
    holder = bpy.data.objects.new("RingHolder", None)
    ov.collection.objects.link(holder)
    holder.location = (0, 0, z)
    holder.rotation_euler = (math.pi / 2, 0, 0)
    curves = []
    for name, col, strength in (("RingTrack", dim_color, 0.35), ("RingFill", color, 1.0)):
        cu = bpy.data.curves.new(name, "CURVE")
        cu.dimensions = "3D"
        sp = cu.splines.new("POLY")
        n = 160
        sp.points.add(n - 1)
        for i, pt in enumerate(sp.points):  # start at 12 o'clock, run clockwise
            a = math.pi / 2 - 2 * math.pi * i / (n - 1)
            pt.co = (radius * math.cos(a), radius * math.sin(a), 0, 1)
        cu.bevel_depth = thickness
        cu.bevel_resolution = 3
        if hasattr(cu, "use_fill_caps"):
            cu.use_fill_caps = True
        obj = bpy.data.objects.new(name, cu)
        ov.collection.objects.link(obj)
        obj.parent = holder
        obj.location = (0, 0.05 if name == "RingTrack" else 0, 0)
        obj.data.materials.append(_mat(col, strength))
        curves.append(cu)
    return holder, curves[1]


def _fmt(v, decimals, prefix="", suffix=""):
    return f"{prefix}{v:,.{decimals}f}{suffix}"


def _ease_out(x):
    return 1 - (1 - x) ** 3


# ----------------------------------------------------------------------------- backgrounds
def _bg_network(scene, spec, p):
    rng = random.Random(spec.seed)
    bg, *acc = spec.palette
    sc.setup_world(scene, bg, 0.6)
    cam = sc.add_camera(scene, location=(0, -19, 0), target=(0, 0, 0), lens=38)
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = 19
    cam.data.dof.aperture_fstop = float(p.get("fstop", 1.4))

    n = int(p.get("nodes", 46))
    nodes = [Vector((rng.uniform(-5.5, 5.5), rng.uniform(-5, 5), rng.uniform(-9, 9))) for _ in range(n)]
    node_mats = [looks.neon(f"Node{i}", c, 5) for i, c in enumerate(acc)]
    edge_mat = looks.neon("Edge", acc[0], 0.7)
    for v in nodes:
        bpy.ops.mesh.primitive_ico_sphere_add(radius=rng.uniform(0.08, 0.2), subdivisions=2, location=v)
        looks.assign(bpy.context.active_object, rng.choice(node_mats))
    edges = set()
    for i, v in enumerate(nodes):
        near = sorted(range(n), key=lambda j: (nodes[j] - v).length)[1:4]
        for j in near:
            edges.add((min(i, j), max(i, j)))
    edges = sorted(edges)
    for i, j in edges:
        a, b = nodes[i], nodes[j]
        vec = b - a
        bpy.ops.mesh.primitive_cylinder_add(radius=0.012, depth=vec.length, vertices=8, location=a + vec / 2)
        e = bpy.context.active_object
        e.rotation_euler = vec.to_track_quat("Z", "Y").to_euler()
        looks.assign(e, edge_mat)

    pulse_mat = looks.neon("Pulse", acc[-1], 18)
    pulses = []
    for k in range(int(p.get("pulses", 28))):
        i, j = rng.choice(edges)
        if rng.random() < 0.5:
            i, j = j, i
        bpy.ops.mesh.primitive_ico_sphere_add(radius=0.07, subdivisions=2)
        s = bpy.context.active_object
        looks.assign(s, pulse_mat)
        pulses.append((s, nodes[i], nodes[j], rng.random(), rng.choice([2, 3, 4])))

    total = spec.frames
    for f in range(1, total + 1):
        t = sc.loop_phase(f, total)
        u = (f - 1) / total
        cam.location = (3.0 * math.sin(t), -19 + 1.0 * math.cos(t), 1.5 * math.sin(2 * t))
        sc.look_at(cam, (0, 0, 0))
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
        for s, a, b, ph, speed in pulses:
            k = (ph + u * speed) % 1.0
            s.location = a.lerp(b, k)
            s.keyframe_insert("location", frame=f)
    sc.linearize(scene)


def _bg_brain(scene, spec, p):
    from .holo_brain import _cerebellum, _cerebrum, _brainstem

    bg, *acc = spec.palette
    sc.setup_world(scene, bg, 0.3)
    pivot = bpy.data.objects.new("BrainPivot", None)
    scene.collection.objects.link(pivot)
    crease = "pointiness" if scene.render.engine == "CYCLES" else "ao"
    mat = looks.tissue("BgTissue", base_hex=p.get("tissue", "#C98A8E"), crease_hex="#3E1520", crease=crease)
    gyri = bpy.data.textures.new("BgGyri", "MARBLE")
    gyri.marble_type, gyri.noise_basis_2 = "SHARP", "SIN"
    gyri.noise_scale, gyri.turbulence, gyri.noise_depth = 0.28, 7.0, 2
    for obj in (_cerebrum("Cerebrum", 6), _cerebellum("Cerebellum"), _brainstem("Brainstem")):
        looks.assign(obj, mat)
        obj.parent = pivot
        for mod in obj.modifiers:
            if mod.type == "DISPLACE" and "Gyri" in mod.name:
                mod.texture, mod.strength, mod.texture_coords = gyri, 0.38, "LOCAL"
            if mod.type == "SMOOTH":
                mod.iterations = 3
    cam = sc.add_camera(scene, location=(0, -26, 0), target=(0, 0, 0), lens=50)
    sc.add_area_light(scene, "Key", (3, -8, 9), energy=6500, size=8)
    from ..spec import hex_to_rgba

    sc.add_area_light(scene, "RimA", (-9, 8, 3), energy=8000, size=5, color=hex_to_rgba(acc[0])[:3])
    sc.add_area_light(scene, "RimB", (9, 8, -2), energy=6000, size=5, color=hex_to_rgba(acc[1 % len(acc)])[:3])
    total = spec.frames
    for f in range(1, total + 1):
        t = sc.loop_phase(f, total)
        pivot.rotation_euler = (math.radians(8), 0, t)
        pivot.keyframe_insert("rotation_euler", frame=f)
    sc.linearize(scene)


def _background(scene, spec, p):
    kind = p.get("background", "network")
    if kind == "network":
        _bg_network(scene, spec, p.get("bg_params", {}))
    elif kind == "brain":
        _bg_brain(scene, spec, p.get("bg_params", {}))
    elif kind in ("neon_orb", "crystal_loop"):
        from . import crystal_loop, neon_orb

        sub = dataclasses.replace(spec, params=p.get("bg_params", {}), text=[])
        (neon_orb if kind == "neon_orb" else crystal_loop).build(scene, sub)
    else:
        raise ValueError(f"unknown background {kind!r}")


# ----------------------------------------------------------------------------- build
def build(scene, spec):
    p = spec.params
    bg, *acc = spec.palette
    primary, secondary = acc[0], acc[1 % len(acc)]
    fps, total = spec.fps, spec.frames
    font = bpy.data.fonts.load(p["font"], check_existing=True) if p.get("font") else None

    _background(scene, spec, p)
    ov = overlay_scene(scene)
    _plane(ov, "Dim", (0, 0, 0, 1), float(p.get("dim", 0.35)), (ORTHO_W * 1.2, 20), (0, 12, 0))

    cues = []  # sound-design cues -> sfx_cues.json (scripts/sfx.py turns them into audio)

    def cue(t, kind, **kw):
        cues.append({"t": round(float(t), 3), "type": kind, **kw})

    items = []  # (obj, scale, start_f, end_f)
    counters = []  # (objs_by_frame dict, start_f, end_f)
    rings = []  # (curve, fraction, start_f, count_frames, end_f)

    def F(s):
        return round(s * fps)

    def add(obj, scale, a, b, delay=0):
        items.append((obj, scale, F(a) + delay, min(F(b), total + 1)))

    # Hook
    ha, hb = p.get("hook_s", [0, 2.8])
    hook = spec.text or ["YOUR HOOK"]
    sizes = [float(p.get("hook_size", 3.2 if len(hook[0]) <= 6 else 1.55))] + [1.0] * (len(hook) - 1)
    z = 2.2 + (len(hook) - 1) * 0.75
    cue(ha + 0.08, "impact")
    for i, (line, size) in enumerate(zip(hook, sizes)):
        obj, s = _text(ov, line, "#FFFFFF" if i == 0 else primary, size, z, font=font)
        add(obj, s, ha, hb, delay=3 + i * 5)
        cue(ha + (3 + i * 5) / fps, "pop", freq=480 + 60 * i, gain=0.7)
        z -= size * 0.85 + 0.45

    for beat in p.get("beats", []):
        a, b = beat["at"]
        kind = beat["type"]
        cue(a, "whoosh", gain=0.55)
        if kind == "stat":
            ring_z = 0.9
            if beat.get("kicker"):
                obj, s = _text(ov, beat["kicker"], secondary, 0.5, ring_z + 3.6, font=font, strength=1.0)
                add(obj, s, a, b)
            frac = beat.get("ring")
            if frac is not None:
                holder, fill = _ring(ov, primary, primary, 2.5, ring_z)
                add(holder, 1.0, a, b)
                rings.append((fill, float(frac), F(a) + 6, F(1.3), min(F(b), total + 1)))
            count_s = float(beat.get("count_s", 1.3))
            cue(a + 6 / fps, "riser", dur=0.7, gain=0.6)
            cue(a + 6 / fps, "tick_run", dur=count_s)
            cue(a + 6 / fps + count_s, "ding")
            # one text object per distinct counter value, toggled by visibility
            value = float(beat["value"])
            dec = int(beat.get("decimals", 0))
            start = float(beat.get("count_from", 0))
            cnt = F(float(beat.get("count_s", 1.3)))
            strings = {}
            for f in range(F(a), F(a) + cnt + 8):  # +lead-in so the final value is reached
                k = _ease_out(min(1.0, max(0.0, (f - F(a) - 6) / cnt)))
                strings.setdefault(_fmt(start + (value - start) * k, dec, beat.get("prefix", ""), beat.get("suffix", "")), f)
            num_size = float(beat.get("size", 1.9 if frac is not None else 2.6))
            objs = {}
            for txt, f0 in strings.items():
                obj, s = _text(ov, txt, "#FFFFFF", num_size, ring_z, font=font, max_w=4.2 if frac is not None else MAX_W)
                add(obj, s, a, b)
                objs[f0] = obj
            counters.append((objs, F(a), min(F(b), total + 1)))
            lz = ring_z - 3.5
            for i, line in enumerate(beat.get("label", [])):
                obj, s = _text(ov, line, primary if i == 0 else "#FFFFFF", 0.82 if i == 0 else 0.62, lz, font=font)
                add(obj, s, a, b, delay=10 + i * 4)
                lz -= 0.95

        elif kind == "bars":
            items_ = beat["items"]
            top = 3.6
            if beat.get("kicker"):
                obj, s = _text(ov, beat["kicker"], secondary, 0.5, top + 0.9, font=font)
                add(obj, s, a, b)
            vmax = max(float(it["value"]) for it in items_)
            row_h = min(1.9, 6.4 / len(items_))
            x0, wmax = -MAX_W / 2, MAX_W * 0.78
            for r, it in enumerate(items_):
                rz = top - r * row_h
                col = it.get("color", primary if r == 0 else secondary)
                obj, s = _text(ov, it["label"], "#FFFFFF", 0.56, rz, x=x0, align="LEFT", font=font)
                add(obj, s, a, b, delay=r * 6)
                bar = bpy.data.objects.new("Bar", bpy.data.meshes.new("Bar"))
                bar.data.from_pydata([(0, 0, -0.22), (1, 0, -0.22), (1, 0, 0.22), (0, 0, 0.22)], [], [(0, 1, 2, 3)])
                bar.data.materials.append(_mat(col, 1.0))
                ov.collection.objects.link(bar)
                bar.location = (x0, -0.01, rz - 0.6)
                w = wmax * float(it["value"]) / vmax
                track = _plane(ov, f"Track{r}", (1, 1, 1, 1), 0.08, (wmax, 0.44), (x0 + wmax / 2, 0.02, rz - 0.6))
                add(track, 1.0, a, b, delay=r * 6)
                rings.append((bar, w, F(a) + 8 + r * 8, F(1.0), min(F(b), total + 1)))  # bars reuse grow list
                cue(a + (8 + r * 8) / fps, "pop", freq=420 + 90 * r, gain=0.6)
                cue(a + (8 + r * 8) / fps, "tick_run", dur=0.9, gain=0.5)
                val = _fmt(float(it["value"]), int(it.get("decimals", 0)), it.get("prefix", ""), it.get("suffix", ""))
                obj, s = _text(ov, val, col, 0.62, rz - 0.6, x=x0 + w + 0.2, align="LEFT", font=font, max_w=99)
                add(obj, s, a + (8 + r * 8 + F(1.0)) / fps, b)
            lz = top - len(items_) * row_h - 0.2
            for i, line in enumerate(beat.get("label", [])):
                obj, s = _text(ov, line, "#FFFFFF", 0.62, lz, font=font)
                add(obj, s, a, b, delay=20 + i * 4)
                lz -= 0.85

        elif kind == "text":
            lines = beat["lines"]
            sizes = beat.get("sizes", [1.15] + [0.75] * (len(lines) - 1))
            colors = beat.get("colors", ["#FFFFFF"] + [primary] * (len(lines) - 1))
            heights = [sz * 0.9 + 0.45 for sz in sizes]
            z = float(beat.get("center_z", 0.8)) + sum(heights) / 2
            for i, (line, sz, col) in enumerate(zip(lines, sizes, colors)):
                z -= heights[i] / 2
                obj, s = _text(ov, line, col, sz, z, font=font)
                add(obj, s, a, b, delay=i * 6)
                cue(a + i * 6 / fps, "pop", freq=500 + 40 * i, gain=0.45)
                z -= heights[i] / 2

        elif kind == "end":
            obj, s = _text(ov, beat.get("handle", "@the.ai.gal"), "#FFFFFF", 1.5, 1.6, font=font)
            add(obj, s, a, b)
            cue(a + 0.05, "chime")
            if beat.get("tagline"):
                obj, s = _text(ov, beat["tagline"], primary, 0.62, 0.5, font=font)
                add(obj, s, a, b, delay=5)
            if beat.get("cta"):
                obj, s = _text(ov, beat["cta"], secondary, 0.55, -0.5, font=font)
                add(obj, s, a, b, delay=9)
            z = SAFE_BOTTOM_Z + 1.3
            for i, line in enumerate(beat.get("source", [])):
                obj, s = _text(ov, line, "#B8C0CC", 0.4, z, font=font, strength=0.9)
                add(obj, s, a, b, delay=12 + i * 3)
                z -= 0.55
        else:
            raise ValueError(f"unknown beat type {kind!r}")

    # ------------------------------------------------------------------ animate overlay
    for f in range(1, total + 1):
        for obj, s, a, b in items:
            if f < a or f >= b:
                k = 0.0
            else:
                kin = (f - a) / 7
                k = back_out(kin) if kin < 1 else 1.0
                if f > b - 6:
                    k *= max(0.0, (b - f) / 6)
            obj.scale = [max(1e-4, s * k)] * 3
            obj.keyframe_insert("scale", frame=f)
        for target, amount, a, n, b in rings:
            k = _ease_out(min(1.0, max(0.0, (f - a) / n)))
            if isinstance(target, bpy.types.Curve):
                target.bevel_factor_end = max(0.0005, amount * k)
                target.keyframe_insert("bevel_factor_end", frame=f)
            else:  # bar object: grow along x
                target.scale = (max(1e-4, amount * k), 1, 1 if a - 8 <= f < b else 1e-4)
                target.keyframe_insert("scale", frame=f)

    # counters: show exactly one value object at a time
    for objs, a, b in counters:
        keys = sorted(objs)
        for idx, f0 in enumerate(keys):
            obj = objs[f0]
            f1 = keys[idx + 1] if idx + 1 < len(keys) else b
            keys_ = {1: True, f0: False, f1: True}
            if f0 > 1:
                keys_[f0 - 1] = True
            for frame, hidden in sorted(keys_.items()):
                obj.hide_render = hidden
                obj.keyframe_insert("hide_render", frame=frame)
    sc.linearize(ov)

    import json
    from pathlib import Path

    out_dir = Path(bpy.path.abspath(scene.render.filepath)).parent.parent
    (out_dir / "sfx_cues.json").write_text(json.dumps(
        {"duration": total / fps, "mood": p.get("mood", "calm"), "cues": sorted(cues, key=lambda c: c["t"])}, indent=1))
