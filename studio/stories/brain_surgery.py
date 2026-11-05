"""Shot builders for stories/claude_brain_surgery.json (see stories/claude_brain_surgery.md).

Each builder(scene, ctx) builds ONE shot into an empty scene. ctx has:
  frames  - shot length in frames (local frames 1..frames)
  fps
  lines   - [(start_f, end_f), ...] local frame ranges of the narration lines in this shot
  cue(t_seconds_local, type, **kw) - add a sound-effect cue
"""
from __future__ import annotations

import math
import random

import bpy
from mathutils import Vector

from .. import looks, scene as sc
from .. import storykit as K

CYAN = "#3FD7FF"
NAVY = "#0E2A47"
VIAL_COLORS = ["#FF6B6B", "#FFB347", "#FFE066", "#9BE15D", "#4CD3C2", "#5DADEC", "#8C7AE6", "#E86FD0",
               "#FF8FA3", "#C0E06B", "#62D2FF", "#FFA24C", "#B98BFF", "#7EE8A2", "#FF7A59", "#6FC3FF",
               "#F7D44C", "#A3A8FF", "#FF9AD5"]


def _grid_positions():
    """19 vials on a stepped 'amphitheatre': rows of 5,5,5,4."""
    pos = []
    for r, n in enumerate((5, 5, 5, 4)):
        for i in range(n):
            x = (i - (n - 1) / 2) * 0.55
            pos.append((x, r * 0.55, r * 0.42 - 0.6))
    return pos


def _vials(big_index=None):
    vials = []
    for i, p in enumerate(_grid_positions()):
        h = 1.55 if i == big_index else 1.0
        glow = 1.2 if i == big_index else 0.15
        piv, liq = K.vial(VIAL_COLORS[i % len(VIAL_COLORS)] if i != big_index else "#FF8A3D", h, glow)
        piv.location = p
        vials.append((piv, liq))
    return vials


# --------------------------------------------------------------------------- 1. lab intro
def lab_intro(scene, ctx):
    K.lab(scene)
    m = K.lab_mouse()
    K.surgical_drape()
    rig, status = K.needle_rig()
    tip = Vector((0.98, 0.0, 0.95))
    rig.location = tip
    glint = looks.neon("Glint", "#FFFFFF", 30)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.008, location=tip)
    g = K.active()
    looks.assign(g, glint)
    (a1, b1), (a2, b2) = ctx.lines
    F = ctx.frames
    cam = K.camera(scene, (5.2, -5.6, 1.7), (0.5, 0, 0.3), lens=45, dof_target=6.5, fstop=2.0)
    K.cam_move(cam, 1, a2, (5.2, -5.6, 1.7), (4.0, -4.2, 1.5), (0.5, 0, 0.3), (0.8, 0, 0.45))
    K.cam_move(cam, a2, min(F, a2 + 12), (4.0, -4.2, 1.5), (2.3, -1.5, 1.3), (0.8, 0, 0.45), tip, curve=K.ease_out)
    for f, v in ((1, 7.0), (a2, 5.6), (a2 + 12, 1.95)):
        cam.data.dof.focus_distance = v
        cam.data.dof.keyframe_insert("focus_distance", frame=f)
    K.pop_scale(g, a2 + 10, scale=1.0, dur=4)
    ctx.cue(0.05, "heartbeat")
    ctx.cue((a1 + 10) / ctx.fps, "rustle")
    ctx.cue(a2 / ctx.fps, "whoosh")
    ctx.cue((a2 + 10) / ctx.fps, "glint")


# --------------------------------------------------------------------------- 2. vials row
def vials_row(scene, ctx):
    K.studio(scene)
    vials = _vials()
    (a, b), = ctx.lines
    for i, (piv, _) in enumerate(vials):
        f = 2 + int(i * (b - a) * 0.55 / len(vials))
        K.pop_scale(piv, f, dur=7)
        if i % 3 == 0:
            ctx.cue(f / ctx.fps, "pop", freq=520 + 25 * i, gain=0.45)
    lbl = K.label3d("19 GENE THERAPIES", NAVY, 0.25)
    lbl.location = (0, -0.6, 2.35)
    K.pop_scale(lbl, int(b * 0.62), dur=8)
    ctx.cue(b * 0.62 / ctx.fps, "thud", gain=0.6)
    cam = K.camera(scene, (-1.2, -7.5, 1.4), (0, 0.4, 0.7), lens=30)
    K.cam_move(cam, 1, ctx.frames, (-1.0, -7.6, 1.3), (0.8, -6.8, 1.7), (0, 0.4, 0.7), (0, 0.4, 0.9))


# --------------------------------------------------------------------------- 3. seizure storm
def storm(scene, ctx):
    K.dark(scene, "#090306")
    mat = K.storm_material()
    pivot, brain, cb = K.mouse_brain(mat)
    pivot.rotation_euler = (0.25, 0, -0.5)
    sc.add_area_light(scene, "Key", (3, -5, 5), energy=700, size=5)
    sc.add_area_light(scene, "RimRed", (-4, 4, 2), energy=900, size=4, color=(1, 0.25, 0.2))
    rng = random.Random(9)
    F = ctx.frames
    K.animate_value(mat, "StormW", [(1, 0.0), (F, 6.0)])
    K.animate_value(mat, "StormGain", [(f, 18 * (0.4 + 0.6 * rng.random())) for f in range(1, F + 1, 2)])
    light = bpy.data.lights.new("Flash", "POINT")
    lo = bpy.data.objects.new("Flash", light)
    scene.collection.objects.link(lo)
    light.color = (1, 0.2, 0.15)
    for f in range(1, F + 1, 2):
        lo.location = (rng.uniform(-1, 1), -1.6, rng.uniform(0.2, 1.0))
        light.energy = rng.choice([0, 0, 150, 400])
        lo.keyframe_insert("location", frame=f)
        light.keyframe_insert("energy", frame=f)
    cam = K.camera(scene, (2.0, -5.2, 2.6), (0, 0, 0), lens=55, dof_target=5.4, fstop=2.8)
    K.cam_move(cam, 1, F, (2.4, -6.4, 3.2), (1.0, -4.0, 1.6), (0, 0, 0), (0.2, 0, 0))
    for k in range(0, F, max(6, ctx.fps // 3)):
        ctx.cue(k / ctx.fps, "crackle", gain=0.5)


# --------------------------------------------------------------------------- 4. question
def question(scene, ctx):
    K.studio(scene)
    big = 12
    chosen = 6
    vials = _vials(big_index=big)
    if len(ctx.lines) == 3:
        (a5, b5), (a6, b6), (a7, b7) = ctx.lines
    else:  # "Which one would you pick? This one, right?" + "The AI picked this one..."
        (a5, b5), (a7, b7) = ctx.lines
        a6 = a5 + int((b5 - a5) * 0.6)
    F = ctx.frames
    q = K.question_mark(2.4)
    for f, z in ((a5 + 1, 6.0), (a5 + 8, 2.3), (a5 + 12, 2.75), (a5 + 16, 2.45)):
        q.location = (0, -0.3, z)
        q.keyframe_insert("location", frame=f)
    K.key(q, a7 + 6, scale=(2.4, 2.4, 2.4))
    K.key(q, a7 + 12, scale=(0.001, 0.001, 0.001))
    ctx.cue(a5 / ctx.fps, "whoosh")
    ctx.cue((a5 + 8) / ctx.fps, "thud")
    big_pos = Vector(_grid_positions()[big]) + Vector((0, 0, 1.0))
    pointer = K.red_arrow(1.3, 0.07)
    start = big_pos + Vector((2.4, -0.6, 2.2))
    near = big_pos + Vector((0.9, -0.4, 0.75))
    for f, loc in ((1, start), (a6 - 2, start), (a6 + 7, near), (a6 + 11, near + Vector((0.12, 0, 0.1))),
                   (a6 + 15, near), (a7 + 2, near), (a7 + 10, start)):
        pointer.location = loc
        K.aim(pointer, big_pos - loc)
        pointer.keyframe_insert("location", frame=f)
        pointer.keyframe_insert("rotation_euler", frame=f)
    K.pop_scale(pointer, a6 - 1, a7 + 10, dur=6)
    ctx.cue((a6 + 8) / ctx.fps, "tap")
    piv, liq = vials[chosen]
    bsdf = liq.active_material.node_tree.nodes.get("Principled BSDF")
    sock = bsdf.inputs["Emission Strength"]
    for f, v in ((1, 0.15), (a7 + 8, 0.15), (a7 + 16, 8.0)):
        sock.default_value = v
        sock.keyframe_insert("default_value", frame=f)
    col = bsdf.inputs["Emission Color"] if "Emission Color" in bsdf.inputs else None
    if col is not None:
        col.default_value = (0.1, 0.8, 1.0, 1)
    base_loc = piv.location.copy()
    for f, dz, rz in ((a7 + 8, 0, 0), (a7 + 22, 0.9, 1.5), (F, 1.0, 3.2)):
        piv.location = base_loc + Vector((0, -0.8 * min(1, dz), dz))
        piv.rotation_euler = (0, 0, rz)
        piv.keyframe_insert("location", frame=f)
        piv.keyframe_insert("rotation_euler", frame=f)
    for i, (p, _) in enumerate(vials):
        if i != chosen:
            K.key(p, a7 + 8, location=p.location.copy())
            K.key(p, a7 + 22, location=p.location + Vector((0, 0.6, -0.45)))
    ring = None
    bpy.ops.mesh.primitive_torus_add(major_radius=0.45, minor_radius=0.025)
    ring = K.active()
    looks.assign(ring, looks.neon("ChosenRing", CYAN, 6))
    ring.rotation_euler = (math.pi / 2, 0, 0)
    for f in range(a7 + 8, F + 1, 2):
        ring.location = piv.location + Vector((0, -0.25, 0.55))
        ring.keyframe_insert("location", frame=f)
    K.pop_scale(ring, a7 + 18, dur=8)
    lbl = K.label3d("GABA BOOST", NAVY, 0.26)
    lbl.location = Vector((base_loc.x, -1.3, base_loc.z + 1.95))
    K.pop_scale(lbl, a7 + 24, dur=8)
    ctx.cue((a7 + 16) / ctx.fps, "ding")
    ctx.cue((a7 + 24) / ctx.fps, "pop")
    cam = K.camera(scene, (0, -8.2, 1.6), (0, 0.4, 1.0), lens=30)
    K.cam_move(cam, 1, a7, (0.3, -8.4, 1.7), (-0.3, -7.6, 1.6), (0, 0.4, 1.0), (0, 0.4, 1.0))
    K.cam_move(cam, a7, F, (-0.3, -7.6, 1.6), (base_loc.x - 0.2, -4.2, base_loc.z + 1.6),
               (0, 0.4, 1.0), base_loc + Vector((0, -0.8, 1.2)))


# --------------------------------------------------------------------------- 5. refusal
def refusal(scene, ctx):
    K.dark(scene, "#06070C")
    pivot, brain, cb = K.mouse_brain()
    pivot.rotation_euler = (0, 0, -0.3)
    sc.add_area_light(scene, "Key", (2, -4, 6), energy=650, size=5)
    sc.add_area_light(scene, "Rim", (-4, 4, 3), energy=600, size=4, color=(0.6, 0.8, 1))
    rig, status = K.needle_rig()
    target = Vector((-0.4, -0.55, 0.62))
    if len(ctx.lines) == 2:
        (a8, b8), (a9, b9) = ctx.lines
    else:
        (a9, b9), = ctx.lines
        a8 = a9
    F = ctx.frames
    stop = a9 + int((b9 - a9) * 0.55)
    for f, z in ((1, 3.2), (a9 + 4, 3.2), (stop, 1.05), (F, 1.05)):
        rig.location = target + Vector((0, 0, z))
        rig.keyframe_insert("location", frame=f)
    ctx.cue((a9 + 4) / ctx.fps, "servo")
    x = K.red_x(0.7)
    x.location = target + Vector((0, -1.4, 2.0))
    K.pop_scale(x, stop + 2, dur=6)
    lbl = K.label3d("DECLINED", "#FFFFFF", 0.3, emission=0.8)
    lbl.location = target + Vector((0, -1.5, 1.05))
    K.pop_scale(lbl, stop + 6, dur=8)
    ctx.cue((stop + 2) / ctx.fps, "buzz")
    flash = bpy.data.lights.new("Alarm", "AREA")
    fl = bpy.data.objects.new("Alarm", flash)
    scene.collection.objects.link(fl)
    fl.location = (0, -5, 4)
    sc.look_at(fl, (0, 0, 0))
    flash.color, flash.size = (1, 0.1, 0.08), 6
    for f in range(1, F + 1):
        on = f >= stop + 2 and ((f - stop) // 5) % 2 == 0
        flash.energy = 900 if on else 0
        flash.keyframe_insert("energy", frame=f)
    cam = K.camera(scene, (2.0, -10.5, 4.6), target, lens=45, dof_target=10.5, fstop=4.0)
    K.cam_move(cam, 1, a9, (3.0, -12.0, 5.4), (2.0, -10.0, 4.4), (0, 0, 0.9), target + Vector((0, 0, 1.2)))
    # impact shake on the slam
    for f in range(stop + 2, min(F, stop + 10)):
        cam.location = Vector((2.0, -10.0, 4.4)) + Vector((random.uniform(-0.08, 0.08), 0, random.uniform(-0.08, 0.08)))
        cam.keyframe_insert("location", frame=f)
    cam.location = (2.0, -10.0, 4.4)
    cam.keyframe_insert("location", frame=min(F, stop + 10))
    ctx.cue(a8 / ctx.fps, "riser", dur=1.0)


# --------------------------------------------------------------------------- 6. switch model
def switch(scene, ctx):
    K.lab(scene, table=False)
    rig, status = K.needle_rig()
    rig.location = (0, 0, -2.0)
    (a, b), = ctx.lines
    F = ctx.frames
    em = status.node_tree.nodes.get("Emission")
    for f, c in ((1, (1, 0.12, 0.1, 1)), (a + int((b - a) * 0.5), (1, 0.12, 0.1, 1)), (a + int((b - a) * 0.5) + 3, (0.1, 1, 0.35, 1))):
        em.inputs["Color"].default_value = c
        em.inputs["Color"].keyframe_insert("default_value", frame=f)
    for f, rz in ((1, -0.4), (F, 0.4)):
        K.key(rig, f, rotation_euler=(0, 0, rz))
    lbl = K.label3d("MODEL 2: ONLINE", "#7CF2A0", 0.24, emission=1.5)
    lbl.location = (0, -1.0, 3.0)
    K.pop_scale(lbl, a + int((b - a) * 0.5) + 4, dur=8)
    ctx.cue((a + int((b - a) * 0.5)) / ctx.fps, "servo")
    ctx.cue((a + int((b - a) * 0.5) + 3) / ctx.fps, "beep")
    cam = K.camera(scene, (3.0, -9.5, 2.0), (0, 0, 0.8), lens=50, dof_target=9.8, fstop=4.0)
    K.cam_move(cam, 1, F, (3.2, -10.0, 2.6), (2.0, -8.6, 2.2), (0, 0, 1.2), (0, 0, 1.6))


# --------------------------------------------------------------------------- 7. x-ray injection
def xray_inject(scene, ctx):
    K.dark(scene, "#050B16")
    holo = looks.hologram("XRay", "#7FD6FF", 4.0, 0.35)
    pivot, brain, cb = K.mouse_brain(holo)
    target = Vector((-0.55, -0.78, -0.22))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, location=target)
    region = K.active()
    looks.assign(region, looks.neon("Target", "#FF9A3D", 6))
    (a, b), = ctx.lines
    F = ctx.frames
    entry = target + Vector((0.35, -1.6, 2.6))
    path = target - entry
    arrow = K.red_arrow(path.length * 0.92, 0.035)
    arrow.location = entry
    K.aim(arrow, path)
    K.pop_scale(arrow, a + 4, dur=10)
    rig, status = K.needle_rig()
    K.aim(rig, -path)
    mid = a + int((b - a) * 0.45)
    for f, u in ((1, -0.6), (mid, -0.6), (b - 6, 1.0), (F, 1.0)):
        rig.location = entry + path * u
        rig.keyframe_insert("location", frame=f)
    lbl = K.label3d("LATERAL ENTORHINAL", "#FFB067", 0.17, emission=1.2)
    lbl.location = target + Vector((0.45, -1.0, -0.8))
    lbl2 = K.label3d("CORTEX", "#FFB067", 0.17, emission=1.2)
    lbl2.location = target + Vector((0.45, -1.0, -1.05))
    K.pop_scale(lbl2, a + 16, dur=8)
    K.pop_scale(lbl, a + 14, dur=8)
    for f, s in ((1, 0.6), (b - 6, 0.6), (b, 1.5), (F, 1.2)):
        K.key(region, f, scale=(s, s, s))
    ctx.cue((a + 4) / ctx.fps, "whoosh", gain=0.5)
    ctx.cue(mid / ctx.fps, "slide")
    ctx.cue((b - 6) / ctx.fps, "ding", gain=0.6)
    cam = K.camera(scene, (1.2, -8.0, 1.6), (0, 0, 0), lens=32)
    K.cam_move(cam, 1, F, (1.6, -9.6, 2.6), (0.8, -8.0, 1.4), (0, 0, 0.4), target + Vector((0.5, 0, 0.6)))


# --------------------------------------------------------------------------- 8. pinhead
def pinhead(scene, ctx):
    K.studio(scene, key_energy=700)
    hand, tips = K.gloved_hand("pinch")
    hand.location = (0.9, 0.25, -2.6)
    hand.rotation_euler = (math.radians(15), math.radians(-35), math.radians(15))
    bpy.context.view_layer.update()
    mw = hand.matrix_world
    grip = (mw @ tips["index"] + mw @ tips["thumb"]) / 2
    pin, head = K.sewing_pin(length=3.0, head_r=0.16)
    pin.location = grip - Vector((0, 0, 1.6))
    head_z = pin.location.z + 3.0 + 0.1
    head_c = Vector((pin.location.x, pin.location.y, head_z))
    drop = K.droplet(0.078)
    drop.location = head_c + Vector((0.5, -0.05, 0.0))
    (a, b), = ctx.lines
    F = ctx.frames
    K.pop_scale(drop, a + 6, dur=8)
    dl = K.dimension_line(drop.location + Vector((-0.12, -0.15, 0.2)), drop.location + Vector((0.12, -0.15, 0.2)),
                          thickness=0.008, tick=0.07)
    K.pop_scale(dl, a + 14, dur=6)
    counter = K.Counter(drop.location + Vector((0, -0.2, 0.42)), 0, 250, a + 14, int(ctx.fps * 0.9),
                        fmt="{:.0f} nL", size=0.16)
    hl = K.dimension_line(head_c + Vector((-0.17, -0.2, -0.26)), head_c + Vector((0.17, -0.2, -0.26)),
                          thickness=0.008, tick=0.07)
    K.pop_scale(hl, a + 26, dur=6)
    lbl = K.label3d("PINHEAD", NAVY, 0.11)
    lbl.location = head_c + Vector((0, -0.2, -0.42))
    K.pop_scale(lbl, a + 28, dur=6)
    ctx.cue((a + 6) / ctx.fps, "drip")
    ctx.cue((a + 14) / ctx.fps, "tick_run", dur=0.9)
    ctx.cue((a + 14) / ctx.fps + 0.9, "ding", gain=0.6)
    focus = head_c + Vector((0.25, 0, 0.05))
    p0, p1 = focus + Vector((0.3, -6.0, 0.4)), focus + Vector((0.1, -4.6, 0.1))
    cam = K.camera(scene, p0, focus, lens=50, dof_target=6.0, fstop=4.0)
    K.cam_move(cam, 1, F, p0, p1, focus, focus)
    for f, pos in ((1, p0), (F, p1)):
        cam.data.dof.focus_distance = (pos - focus).length
        cam.data.dof.keyframe_insert("focus_distance", frame=f)


# --------------------------------------------------------------------------- 9. three AIs
def three_ais(scene, ctx):
    K.studio(scene)
    if len(ctx.lines) == 2:
        (a13, b13), (a14, b14) = ctx.lines
    else:
        (a13, b14), = ctx.lines
        a14 = a13 + int((b14 - a13) * 0.3)
    F = ctx.frames
    names = [("CLAUDE", "#3FD7FF", (-0.5, -0.75, -0.2)), ("GPT", "#9BE15D", (0.6, -0.5, 0.35)),
             ("GROK", "#FF8A3D", (-1.0, 0.0, 0.45))]
    pedestal = looks.glossy("Pedestal", "#F4F7FA", 0.3)
    src = K.mouse_brain()
    src_objs = [src[0], src[1], src[2]]
    for i, (name, col, spot) in enumerate(names):
        x = (i - 1) * 1.3
        bpy.ops.mesh.primitive_cylinder_add(radius=0.42, depth=1.2, vertices=48, location=(x, 0, -1.6))
        looks.assign(K.active(), pedestal)
        piv, liq = K.vial(col, 1.0, 1.0)
        piv.location = (x, 0, -1.0)
        K.pop_scale(piv, 2 + i * 6, dur=7)
        ctx.cue((2 + i * 6) / ctx.fps, "pop", freq=500 + 80 * i)
        lbl = K.label3d(name, NAVY, 0.22)
        lbl.location = (x, -0.7, -1.75)
        K.pop_scale(lbl, 6 + i * 6, dur=7)
        # brain copy above
        bp = src_objs[0].copy()
        scene.collection.objects.link(bp)
        for child in src_objs[1:]:
            c = child.copy()
            scene.collection.objects.link(c)
            c.parent = bp
        bp.location = (x, 0, 1.25)
        bp.scale = (0.3, 0.3, 0.3)
        bp.rotation_euler = (0.35, 0, -0.35)
        f_in = a14 + i * 7
        K.pop_scale(bp, f_in, dur=8)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.3, location=spot)
        glow = K.active()
        looks.assign(glow, looks.neon(f"Spot{i}", col, 8))
        glow.parent = bp
        K.pop_scale(glow, f_in + 8, dur=6)
        arrow = K.red_arrow(0.6, 0.03)
        arrow.location = (x + 0.35, -0.5, 2.2)
        K.aim(arrow, Vector((x, 0, 1.25)) + Vector(spot) * 0.3 - arrow.location)
        K.pop_scale(arrow, f_in + 10, dur=6)
        ctx.cue(f_in / ctx.fps, "whoosh", gain=0.4)
        ctx.cue((f_in + 8) / ctx.fps, "chime_one", gain=0.5, freq=660 + 220 * i)
    for o in src_objs:  # hide the source brain
        o.hide_render = True
    src[0].location = (0, 50, 0)
    cam = K.camera(scene, (0, -12.0, 0.6), (0, 0, -0.2), lens=38)
    K.cam_move(cam, 1, a14, (0, -12.6, 0.2), (0, -12.0, 0.3), (0, 0, -0.9), (0, 0, -0.6))
    K.cam_move(cam, a14, F, (0, -12.0, 0.3), (0, -11.0, 1.0), (0, 0, -0.6), (0, 0, 0.3))


# --------------------------------------------------------------------------- 10. recovery
def recovery(scene, ctx):
    K.lab(scene)
    m = K.lab_mouse()
    drape = K.surgical_drape()
    F = ctx.frames
    (a, b), = ctx.lines
    body = m["body"]
    for f in range(1, F + 1, 3):
        s = 1 + 0.025 * math.sin(f / ctx.fps * 2 * math.pi * 0.9)
        K.key(drape, f, scale=(1, s, s))
    lbl = K.label3d("RESULTS: PENDING", "#FFD66B", 0.2, emission=1.6)
    lbl.location = (0.6, -0.4, 1.5)
    K.pop_scale(lbl, a + int((b - a) * 0.45), dur=8)
    ctx.cue(0.1, "heartbeat")
    ctx.cue((a + (b - a) * 0.45) / ctx.fps, "pop")
    cam = K.camera(scene, (2.2, -4.2, 1.6), (0.3, 0, 0.1), lens=45, dof_target=4.6, fstop=2.4)
    K.cam_move(cam, 1, F, (2.0, -3.8, 1.4), (3.6, -6.8, 2.6), (0.4, 0, 0.1), (0.2, 0, 0.4))


# --------------------------------------------------------------------------- 11. end card
def end(scene, ctx):
    K.studio(scene, center="#B8F2FA", edge="#36B8D6")
    piv, liq = K.vial(CYAN, 1.3, 5.0)
    piv.location = (0, 0, -0.4)
    F = ctx.frames
    for f, rz in ((1, 0), (F, 2.5)):
        K.key(piv, f, rotation_euler=(0, 0, rz))
    q = K.question_mark(0.9)
    q.location = (0.32, -0.4, 1.0)
    q.rotation_euler = (math.pi / 2, 0, -0.25)
    K.pop_scale(q, 4, dur=8)
    handle = K.label3d("@the.ai.gal", NAVY, 0.38)
    handle.location = (0, -0.4, -1.3)
    K.pop_scale(handle, int(F * 0.35), dur=8)
    ctx.cue(4 / ctx.fps, "thud", gain=0.5)
    ctx.cue(int(F * 0.35) / ctx.fps, "chime")
    cam = K.camera(scene, (0, -6.5, 0.3), (0, 0, 0.1), lens=50)
    K.cam_move(cam, 1, F, (0, -6.8, 0.2), (0, -5.8, 0.35), (0, 0, 0.1), (0, 0, 0.15))


SHOTS = {f.__name__: f for f in (lab_intro, vials_row, storm, question, refusal, switch, xray_inject, pinhead,
                                 three_ais, recovery, end)}
