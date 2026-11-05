"""AI Reels Studio - procedural Blender scenes for Instagram Reels.

Two ways in:
  * Headless:  blender -b -P scripts/render_reel.py -- reels/neon_orb.json
  * Via Blender MCP (Claude calls `execute_blender_code`):
        import sys; sys.path.insert(0, "/abs/path/to/ai-reels-studio")
        import studio; studio.build("reels/neon_orb.json")
"""
from __future__ import annotations

import importlib
import os
from pathlib import Path

from .spec import ReelSpec

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ("neon_orb", "kinetic_title", "crystal_loop")


def _resolve(spec_or_path) -> ReelSpec:
    if isinstance(spec_or_path, ReelSpec):
        return spec_or_path
    if isinstance(spec_or_path, dict):
        return ReelSpec.from_dict(spec_or_path)
    path = Path(spec_or_path)
    if not path.is_absolute():
        path = ROOT / path
    return ReelSpec.load(path)


def build(spec_or_path, output_dir: str | None = None, render: bool = False):
    """Build the reel scene in the current Blender session; optionally render frames."""
    import bpy

    from . import scene as sc

    spec = _resolve(spec_or_path)
    if spec.template not in TEMPLATES:
        raise ValueError(f"Unknown template {spec.template!r}; choose from {TEMPLATES}")
    output_dir = output_dir or str(ROOT / "output" / spec.name)
    os.makedirs(output_dir, exist_ok=True)

    scene = sc.reset_scene()
    sc.configure_render(scene, spec, output_dir)
    module = importlib.import_module(f".templates.{spec.template}", __name__)
    module.build(scene, spec)
    scene.frame_set(1)

    bpy.ops.wm.save_as_mainfile(filepath=str(Path(output_dir) / f"{spec.name}.blend"))
    if render:
        bpy.ops.render.render(animation=True)
    return spec
