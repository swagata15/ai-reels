"""Kinetic text block for orthographic reel cameras: lines pop in one by one, auto-fit to width."""
from __future__ import annotations

import math

import bpy

from . import looks
from .spec import REEL_HEIGHT, SAFE_BOTTOM_PX, SAFE_TOP_PX

ORTHO_H = 16.0  # world units across the full 1920px height when using ortho_camera()
ORTHO_W = ORTHO_H * 9 / 16
SAFE_TOP_Z = ORTHO_H / 2 - SAFE_TOP_PX / REEL_HEIGHT * ORTHO_H
SAFE_BOTTOM_Z = -ORTHO_H / 2 + SAFE_BOTTOM_PX / REEL_HEIGHT * ORTHO_H


def ortho_camera(scene, distance: float = 30.0):
    """Front-facing ortho camera (looking +Y) whose frame is ORTHO_W x ORTHO_H units."""
    from . import scene as sc

    cam = sc.add_camera(scene, location=(0, -distance, 0), target=(0, 0, 0))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = ORTHO_H
    cam.data.clip_end = distance * 3
    return cam


class TextBlock:
    """Stack of text lines between z_top and z_bottom, centred, facing an ortho camera at -Y."""

    def __init__(self, scene, lines, colors, *, z_top=SAFE_TOP_Z, z_bottom=SAFE_BOTTOM_Z,
                 y=0.0, sizes=(2.2, 1.5), max_width=ORTHO_W * 0.84, gap=0.45, font=None,
                 emission=(3.0, 4.0)):
        self.y = y
        self.objects = []
        font_data = bpy.data.fonts.load(font, check_existing=True) if font else None
        for i, line in enumerate(lines):
            curve = bpy.data.curves.new(f"Line{i}", "FONT")
            curve.body = line
            curve.align_x = "CENTER"
            curve.align_y = "CENTER"
            curve.extrude = 0.06
            curve.bevel_depth = 0.01
            if font_data:
                curve.font = font_data
            obj = bpy.data.objects.new(f"Line{i}", curve)
            scene.collection.objects.link(obj)
            obj.rotation_euler = (math.pi / 2, 0, 0)
            strength = emission[0] if i == 0 else emission[1]
            looks.assign(obj, looks.neon(f"Text{i}", colors[i % len(colors)], strength))
            self.objects.append(obj)

        bpy.context.view_layer.update()
        self.sizes = []
        for i, obj in enumerate(self.objects):
            base = sizes[0] if i == 0 else sizes[1]
            w = obj.dimensions.x * base
            self.sizes.append(base * min(1.0, max_width / w) if w else base)

        heights = [s + gap for s in self.sizes]
        z = (z_top + z_bottom) / 2 + sum(heights) / 2
        self.rest = []
        for h in heights:
            z -= h / 2
            self.rest.append(z)
            z -= h / 2

    def animate(self, frame, total, fps, t, *, start_s=0.13, stagger_s=0.6, outro_s=0.4):
        """Key one frame. Call for every frame 1..total. `t` is the loop phase."""
        stagger = max(1, round(stagger_s * fps))
        pop = max(4, round(0.33 * fps))
        outro = max(4, round(outro_s * fps)) if outro_s > 0 else 0
        outro_start = total - outro
        for i, (obj, size, z_rest) in enumerate(zip(self.objects, self.sizes, self.rest)):
            k = (frame - (round(start_s * fps) + i * stagger)) / pop
            s = 0.0 if k <= 0 else 1.0 if k >= 1 else back_out(k)
            if outro > 0 and frame >= outro_start:
                s *= max(0.0, 1 - ((frame - outro_start) / outro) ** 3)
            obj.scale = [size * s] * 3
            obj.location = (0, self.y, z_rest - 0.4 * (1 - min(1.0, max(0.0, k))))
            obj.rotation_euler = (math.pi / 2, 0.03 * math.sin(t * 2 + i), 0)
            obj.keyframe_insert("scale", frame=frame)
            obj.keyframe_insert("location", frame=frame)
            obj.keyframe_insert("rotation_euler", frame=frame)


def back_out(x: float, c: float = 1.9) -> float:
    """Overshoot easing - the 'pop' that makes kinetic type feel alive."""
    x -= 1
    return 1 + (c + 1) * x**3 + c * x**2


def overlay_scene(main_scene, name: str = "Overlay"):
    """A second scene for crisp 2D text/HUD, rendered with a transparent background.

    scripts/render_reel.py renders it to frames_overlay/ and postprocess.py composites
    it over the main frames - so depth of field / motion blur never soften the text.
    """
    ov = bpy.data.scenes.new(name)
    r, mr = ov.render, main_scene.render
    ov.render.engine = mr.engine
    for attr in ("resolution_x", "resolution_y", "resolution_percentage", "fps", "fps_base"):
        setattr(r, attr, getattr(mr, attr))
    ov.frame_start, ov.frame_end = main_scene.frame_start, main_scene.frame_end
    r.film_transparent = True
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    r.filepath = mr.filepath.replace("/frames/", "/frames_overlay/")
    ov.view_settings.view_transform = "Standard"
    ov["reel_pass"] = "overlay"
    ortho_camera(ov)
    return ov
