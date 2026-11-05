"""Scene, camera, world and render setup for vertical reels."""
from __future__ import annotations

import math

import bpy

from .spec import REEL_HEIGHT, REEL_WIDTH, ReelSpec, hex_to_rgba


def reset_scene() -> bpy.types.Scene:
    """Start from an empty scene (keeps the Blender UI usable when run via MCP)."""
    scene = bpy.context.scene
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.curves, bpy.data.cameras, bpy.data.lights):
        for block in list(coll):
            if block.users == 0:
                coll.remove(block)
    return scene


def _pick_eevee(scene: bpy.types.Scene) -> None:
    engines = scene.render.bl_rna.properties["engine"].enum_items.keys()
    # Blender 4.2-4.x calls it EEVEE_NEXT, 3.x and 5.x call it EEVEE.
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        if engine in engines:
            scene.render.engine = engine
            return
    scene.render.engine = "CYCLES"


def configure_render(scene: bpy.types.Scene, spec: ReelSpec, output_dir: str) -> None:
    draft = spec.quality == "draft"
    _pick_eevee(scene)
    r = scene.render
    r.resolution_x = REEL_WIDTH
    r.resolution_y = REEL_HEIGHT
    r.resolution_percentage = 50 if draft else 100
    r.fps = spec.fps
    r.fps_base = 1.0
    scene.frame_start = 1
    scene.frame_end = spec.frames
    r.film_transparent = False

    # Frames as PNG; scripts/postprocess.py turns them into an Instagram-ready MP4.
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    r.filepath = f"{output_dir.rstrip('/')}/frames/frame_"

    eevee = scene.eevee
    if hasattr(eevee, "taa_render_samples"):
        eevee.taa_render_samples = 16 if draft else 64
    for attr in ("use_raytracing", "use_gtao"):
        if hasattr(eevee, attr):
            setattr(eevee, attr, not draft)

    # Filmic/AgX look with a little punch.
    vs = scene.view_settings
    transforms = vs.bl_rna.properties["view_transform"].enum_items.keys()
    vs.view_transform = "AgX" if "AgX" in transforms else "Filmic"
    looks = [l for l in vs.bl_rna.properties["look"].enum_items.keys()]
    for look in ("AgX - Punchy", "AgX - Medium High Contrast", "Medium High Contrast"):
        if look in looks:
            vs.look = look
            break


def setup_world(scene: bpy.types.Scene, color_hex: str, strength: float = 1.0) -> None:
    world = bpy.data.worlds.get("ReelWorld") or bpy.data.worlds.new("ReelWorld")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg is None:
        bg = world.node_tree.nodes.new("ShaderNodeBackground")
        out = world.node_tree.nodes.get("World Output") or world.node_tree.nodes.new("ShaderNodeOutputWorld")
        world.node_tree.links.new(bg.outputs[0], out.inputs[0])
    bg.inputs["Color"].default_value = hex_to_rgba(color_hex)
    bg.inputs["Strength"].default_value = strength
    scene.world = world


def add_camera(scene, location=(0, -12, 0), target=(0, 0, 0), lens=50.0) -> bpy.types.Object:
    cam_data = bpy.data.cameras.new("ReelCam")
    cam_data.lens = lens
    cam_data.sensor_fit = "VERTICAL"
    cam = bpy.data.objects.new("ReelCam", cam_data)
    scene.collection.objects.link(cam)
    cam.location = location
    look_at(cam, target)
    scene.camera = cam
    return cam


def look_at(obj: bpy.types.Object, target) -> None:
    from mathutils import Vector

    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_area_light(scene, name, location, energy=500.0, size=5.0, color=(1, 1, 1)) -> bpy.types.Object:
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.size = size
    data.color = color
    light = bpy.data.objects.new(name, data)
    scene.collection.objects.link(light)
    light.location = location
    look_at(light, (0, 0, 0))
    return light


def loop_phase(frame: int, total: int) -> float:
    """0..2π across the reel so animations loop seamlessly (frame total+1 == frame 1)."""
    return 2 * math.pi * (frame - 1) / total


def _fcurves(action):
    curves = list(getattr(action, "fcurves", []) or [])
    # Blender 4.4+/5.x layered actions keep curves in channelbags.
    for layer in getattr(action, "layers", []):
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", []):
                curves.extend(bag.fcurves)
    return curves


def linearize(scene) -> None:
    """Linear interpolation on all keys, so per-frame baked motion doesn't ease."""
    for obj in scene.objects:
        ad = obj.animation_data
        if ad and ad.action:
            for fc in _fcurves(ad.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
