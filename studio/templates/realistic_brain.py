"""Realistic brain: a wet, subsurface-scattered brain in a dark lab, a chrome probe
needle injecting a glowing therapy, cinematic depth of field and a slow push-in.
Title + HUD captions render in a separate overlay pass, so they stay razor sharp.

Built for science / AI-in-medicine news reels (Cycles recommended; EEVEE works).
spec.text  -> title lines (first = hook, last can be a small footnote)
params.hud -> list of [text, start_s, end_s] status lines shown in the lower third
params.timeline -> {"insert_s", "inject_end_s", "retract_s"} needle timing
"""
from __future__ import annotations

import math
import random

import bpy
from mathutils import Matrix, Vector

from .. import looks, scene as sc
from ..spec import hex_to_rgba
from ..text import ORTHO_W, SAFE_BOTTOM_Z, SAFE_TOP_Z, TextBlock, back_out, overlay_scene
from .holo_brain import A, B, C, _brainstem, _cerebellum, _cerebrum, _smooth

DEFAULT_HUD = [
    ["ANALYZING 19 GENE THERAPIES...", 0.3, 2.3],
    ["SELECTED: GABA-BOOSTING THERAPY", 2.4, 4.4],
    ["TARGET: LATERAL ENTORHINAL CORTEX", 4.5, 6.4],
    ["INJECTING 250 nL", 6.5, 8.1],
    ["PROCEDURE COMPLETE", 8.2, 99],
]


def _ease(u):
    return u * u * (3 - 2 * u)


def build(scene, spec):
    p = spec.params
    rng = random.Random(spec.seed)
    bg, *accents = spec.palette
    therapy_col, rim_a, rim_b = (accents * 3)[:3]
    fps, total = spec.fps, spec.frames
    tl = {"insert_s": 4.4, "inject_end_s": 7.8, "retract_s": 8.2, **p.get("timeline", {})}

    sc.setup_world(scene, bg, 0.35)
    scene.render.use_motion_blur = spec.quality == "final"

    # --- Brain -----------------------------------------------------------------
    pivot = bpy.data.objects.new("BrainPivot", None)
    scene.collection.objects.link(pivot)
    crease = "pointiness" if scene.render.engine == "CYCLES" else "ao"
    brain_mat = looks.tissue("BrainTissue", base_hex="#D58D8B", crease_hex="#4A1520", crease=crease)
    stem_mat = looks.tissue("StemTissue", base_hex="#C98C8C", vein_scale=2.5, crease=crease)
    for obj, mat in ((_cerebrum("Cerebrum", 6), brain_mat), (_cerebellum("Cerebellum"), brain_mat),
                     (_brainstem("Brainstem"), stem_mat)):
        looks.assign(obj, mat)
        obj.parent = pivot
    # Realistic gyri: turbulent marble bands give long, winding ridges (not cells).
    gyri = bpy.data.textures.new("Gyri", "MARBLE")
    gyri.marble_type = "SHARP"
    gyri.noise_basis_2 = "SIN"
    gyri.noise_scale = float(p.get("gyri_scale", 0.28))
    gyri.turbulence = float(p.get("gyri_turbulence", 7.0))
    gyri.noise_depth = 2
    for obj in pivot.children:
        for mod in obj.modifiers:
            if mod.type == "DISPLACE" and "Gyri" in mod.name:
                mod.texture = gyri
                mod.strength = float(p.get("gyri_depth", 0.38))
                mod.texture_coords = "LOCAL"
            if mod.type == "SMOOTH":
                mod.iterations = 3
    pivot.rotation_euler = (math.radians(8), 0, math.radians(-12))

    # --- Camera: 50mm, slow push-in, shallow focus on the injection site ---------
    site_dir = Vector((0.35, -0.85, -0.25)).normalized()
    s = 1 / math.sqrt((site_dir.x / A) ** 2 + (site_dir.y / B) ** 2 + (site_dir.z / C) ** 2)
    site_local = site_dir * s
    pivot_m = Matrix.Translation(pivot.location) @ pivot.rotation_euler.to_matrix().to_4x4()
    site_world = pivot_m @ site_local
    focus = bpy.data.objects.new("Focus", None)
    scene.collection.objects.link(focus)
    focus.location = site_world

    cam = sc.add_camera(scene, location=(0, -30, 1.0), target=(0, 0, 1.6), lens=50)
    cam.data.dof.use_dof = True
    cam.data.dof.focus_object = focus
    cam.data.dof.aperture_fstop = float(p.get("fstop", 0.5))
    cam.data.dof.aperture_blades = 7

    # --- Lighting: surgical key, cool + magenta rims, warm fill ---------------------
    sc.add_area_light(scene, "SurgicalKey", (2, -8, 11), energy=3600, size=8, color=(1.0, 0.96, 0.9))
    sc.add_area_light(scene, "RimCool", (-9, 9, 4), energy=6000, size=5, color=hex_to_rgba(rim_a)[:3])
    sc.add_area_light(scene, "RimWarm", (9, 8, -1), energy=4200, size=5, color=hex_to_rgba(rim_b)[:3])
    sc.add_area_light(scene, "Fill", (-7, -10, -3), energy=700, size=8, color=(1.0, 0.8, 0.75))

    # --- Lab bokeh far behind ---------------------------------------------------
    bokeh_mats = [looks.neon(f"Bokeh{i}", c, 1.6) for i, c in enumerate([rim_a, rim_b, therapy_col, "#FFFFFF"])]
    bokeh = []
    for _ in range(int(p.get("bokeh", 34))):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=rng.uniform(0.3, 0.8), segments=16, ring_count=8)
        b = bpy.context.active_object
        looks.assign(b, rng.choice(bokeh_mats))
        base = Vector((rng.uniform(-22, 22), rng.uniform(25, 55), rng.uniform(-16, 24)))
        bokeh.append((b, base, rng.uniform(0, 6.28)))

    # --- Probe: chrome needle + dark holder + glowing collar ---------------------
    entry_origin = Vector((ORTHO_W / 2 + 4.0, -9.0, 9.5))
    direction = (site_world - entry_origin).normalized()
    aim = direction.to_track_quat("Z", "Y").to_euler()
    probe = bpy.data.objects.new("Probe", None)
    scene.collection.objects.link(probe)
    probe.rotation_euler = aim
    chrome = looks.glossy("Chrome", "#DDE3EC", 0.08, 1.0)
    dark = looks.glossy("Anodized", "#1B1E26", 0.3, 0.9)
    pieces = [
        ("Needle", lambda: bpy.ops.mesh.primitive_cone_add(radius1=0.045, radius2=0.006, depth=3.0, vertices=32), chrome, -1.5),
        ("Barrel", lambda: bpy.ops.mesh.primitive_cylinder_add(radius=0.16, depth=4.0, vertices=48), chrome, -5.0),
        ("Holder", lambda: bpy.ops.mesh.primitive_cylinder_add(radius=0.32, depth=6.0, vertices=48), dark, -10.0),
    ]
    for name, op, mat, z in pieces:
        op()
        o = bpy.context.active_object
        o.name = name
        looks.assign(o, mat)
        o.parent = probe
        o.location = (0, 0, z)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.34, minor_radius=0.04, major_segments=64, minor_segments=12)
    collar = bpy.context.active_object
    looks.assign(collar, looks.neon("Collar", therapy_col, 12))
    collar.parent = probe
    collar.location = (0, 0, -7.0)

    # --- Therapy glow, surface ripples, targeting reticle -------------------------
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, segments=48, ring_count=24)
    glow = bpy.context.active_object
    looks.assign(glow, looks.hologram("Therapy", therapy_col, 10.0, 0.55))
    glow.location = site_world
    glow_light_data = bpy.data.lights.new("TherapyLight", "POINT")
    glow_light_data.color = hex_to_rgba(therapy_col)[:3]
    glow_light_data.shadow_soft_size = 0.6
    glow_light = bpy.data.objects.new("TherapyLight", glow_light_data)
    scene.collection.objects.link(glow_light)
    glow_light.location = site_world - site_dir * -0.6

    normal_rot = (pivot_m.to_3x3() @ site_dir).to_track_quat("Z", "Y").to_euler()
    ripples = []
    for i in range(3):
        bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.012, major_segments=96, minor_segments=6)
        r = bpy.context.active_object
        looks.assign(r, looks.neon(f"Ripple{i}", therapy_col, 10))
        r.location = site_world
        r.rotation_euler = normal_rot
        ripples.append(r)

    cam_dir = (cam.location - site_world).normalized()
    reticle_rot = cam_dir.to_track_quat("Z", "Y").to_euler()
    reticle = bpy.data.objects.new("Reticle", None)
    scene.collection.objects.link(reticle)
    reticle.location = site_world + cam_dir * 0.8
    reticle.rotation_euler = reticle_rot
    for i, (rad, thick) in enumerate(((0.55, 0.009), (0.72, 0.005))):
        bpy.ops.mesh.primitive_torus_add(major_radius=rad, minor_radius=thick, major_segments=128, minor_segments=6)
        ring = bpy.context.active_object
        looks.assign(ring, looks.neon(f"Reticle{i}", therapy_col, 6))
        ring.parent = reticle
    for k in range(4):
        bpy.ops.mesh.primitive_cube_add(size=1)
        tick = bpy.context.active_object
        tick.scale = (0.009, 0.12, 0.009)
        a = k * math.pi / 2
        tick.location = (0.82 * math.cos(a), 0.82 * math.sin(a), 0)
        tick.rotation_euler = (0, 0, a + math.pi / 2)
        looks.assign(tick, looks.neon(f"Tick{k}", therapy_col, 6))
        tick.parent = reticle

    # --- MRI scan ring (hologram) sweeping through ------------------------------
    bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.014, major_segments=160, minor_segments=8)
    scan = bpy.context.active_object
    looks.assign(scan, looks.neon("Scan", rim_a, 10))
    scan.parent = pivot

    # --- Overlay pass: title + HUD ----------------------------------------------
    ov = overlay_scene(scene)
    title_lines = spec.text or ["CLAUDE JUST DID", "BRAIN SURGERY*"]
    title = TextBlock(ov, title_lines, ["#FFFFFF", therapy_col, "#FFD27A"], z_top=SAFE_TOP_Z,
                      z_bottom=SAFE_TOP_Z - 3.6, sizes=(1.9, 1.35), emission=(1.0, 1.0), font=p.get("font"))
    hud_items = []
    for i, (txt, a_s, b_s) in enumerate(p.get("hud", DEFAULT_HUD)):
        blk = TextBlock(ov, [txt], [therapy_col], z_top=SAFE_BOTTOM_Z + 1.3, z_bottom=SAFE_BOTTOM_Z + 0.3,
                        sizes=(0.62, 0.62), emission=(1.0, 1.0), font=p.get("hud_font"))
        hud_items.append((blk, a_s * fps, min(b_s * fps, total + 1)))
    # dark glass panel behind the HUD for legibility
    panel_mat = bpy.data.materials.new("HudPanel")
    panel_mat.use_nodes = True
    pnt = panel_mat.node_tree
    pnt.nodes.clear()
    tr = pnt.nodes.new("ShaderNodeBsdfTransparent")
    em = pnt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.0, 0.004, 0.008, 1)
    mx = pnt.nodes.new("ShaderNodeMixShader")
    mx.inputs["Fac"].default_value = 0.62
    out = pnt.nodes.new("ShaderNodeOutputMaterial")
    pnt.links.new(tr.outputs[0], mx.inputs[1])
    pnt.links.new(em.outputs[0], mx.inputs[2])
    pnt.links.new(mx.outputs[0], out.inputs[0])
    bpy.ops.mesh.primitive_plane_add(size=1)
    panel = bpy.context.active_object
    bpy.context.collection.objects.unlink(panel)
    ov.collection.objects.link(panel)
    panel.rotation_euler = (math.pi / 2, 0, 0)
    panel.scale = (ORTHO_W * 0.86, 1.1, 1)
    panel.location = (0, 2.0, SAFE_BOTTOM_Z + 0.8)
    looks.assign(panel, panel_mat)
    # thin bracket lines framing the HUD
    for side in (-1, 1):
        bpy.ops.mesh.primitive_cube_add(size=1)
        bar = bpy.context.active_object
        bpy.context.collection.objects.unlink(bar)
        ov.collection.objects.link(bar)
        bar.scale = (ORTHO_W * 0.86, 0.01, 0.012)
        bar.location = (0, 0, SAFE_BOTTOM_Z + 0.8 + side * 0.55)
        looks.assign(bar, looks.neon(f"HudBar{side}", therapy_col, 0.7))

    # --- Animate ----------------------------------------------------------------
    ins, inj_end, ret = tl["insert_s"] * fps, tl["inject_end_s"] * fps, tl["retract_s"] * fps
    for f in range(1, total + 1):
        u = (f - 1) / max(1, total - 1)
        t = 2 * math.pi * u

        # camera push-in with a slight drift
        e = _ease(u)
        cam.location = (0.8 * math.sin(t * 0.5) - 0.4, -30 + 5.5 * e, 1.0 + 0.4 * e)
        sc.look_at(cam, (0.15, 0, 1.6 - 0.35 * e))
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)

        # brain breathing
        pivot.scale = [1 + 0.006 * math.sin(t * 3)] * 3
        pivot.keyframe_insert("scale", frame=f)

        # probe: approach -> insert -> hold -> retract
        approach = _smooth(0.5 * fps, ins - 0.4 * fps, f)
        insert = _smooth(ins - 0.4 * fps, ins + 0.3 * fps, f)
        retract = _smooth(ret, ret + 0.6 * fps, f)
        depth = (-9.0 + 8.4 * approach + 0.85 * insert) * (1 - retract) - 9.0 * retract
        probe.location = site_world + direction * depth
        probe.keyframe_insert("location", frame=f)
        collar.scale = [1 + 0.15 * insert * (1 - retract) * (1 + math.sin(f * 0.5))] * 3
        collar.keyframe_insert("scale", frame=f)

        # therapy spread
        spread = _smooth(ins + 0.3 * fps, inj_end, f)
        glow.scale = [max(0.001, 0.55 * spread * (1 + 0.05 * math.sin(f * 0.4)))] * 3
        glow.keyframe_insert("scale", frame=f)
        glow_light_data.energy = 900 * spread
        glow_light_data.keyframe_insert("energy", frame=f)
        for i, r in enumerate(ripples):
            active = ins + 0.3 * fps <= f <= inj_end + fps
            ru = ((f - ins) / (1.2 * fps) - i / 3) % 1.0 if active else 0.0
            r.scale = [max(0.001, (0.15 + 1.5 * ru)) if active else 0.001] * 3
            r.keyframe_insert("scale", frame=f)

        # reticle locks on as the target is announced
        lock = _smooth(ins - 1.2 * fps, ins - 0.2 * fps, f)
        reticle.scale = [max(0.001, (2.0 - 1.0 * lock) * (lock if lock > 0 else 0.001))] * 3
        reticle.rotation_euler = (reticle_rot.x, reticle_rot.y, reticle_rot.z + 1.5 * (1 - lock) + 0.15 * t)
        reticle.keyframe_insert("scale", frame=f)
        reticle.keyframe_insert("rotation_euler", frame=f)

        # MRI scan sweeps front->back once, early in the reel
        x = A * 0.95 * math.cos(math.pi * _smooth(0.2 * fps, 3.8 * fps, f))
        kx = math.sqrt(max(0.0, 1 - (x / A) ** 2))
        visible = 0.2 * fps < f < 3.9 * fps
        scan.location = (x, 0, 0)
        scan.rotation_euler = (0, math.pi / 2, 0)
        scan.scale = (C * kx * 1.05, B * kx * 1.05, 1) if visible else (0.001, 0.001, 0.001)
        for prop in ("location", "rotation_euler", "scale"):
            scan.keyframe_insert(prop, frame=f)

        for b, base, ph in bokeh:
            b.location = base + Vector((0.6 * math.sin(t + ph), 0, 0.5 * math.cos(t * 0.7 + ph)))
            b.keyframe_insert("location", frame=f)

        # overlay
        title.animate(f, total, fps, t, start_s=0.1, stagger_s=0.45, outro_s=0)
        for blk, a_f, b_f in hud_items:
            obj = blk.objects[0]
            k_in = (f - a_f) / 6
            k_out = (f - (b_f - 4)) / 4
            sc_in = 0 if k_in <= 0 else 1 if k_in >= 1 else back_out(k_in)
            sc_out = 1 if k_out <= 0 else max(0.0, 1 - k_out)
            obj.scale = [blk.sizes[0] * sc_in * sc_out] * 3
            obj.location = (0, 0, blk.rest[0])
            obj.keyframe_insert("scale", frame=f)
            obj.keyframe_insert("location", frame=f)

    sc.linearize(scene)
    sc.linearize(ov)
    if bpy.context.window:
        bpy.context.window.scene = scene
