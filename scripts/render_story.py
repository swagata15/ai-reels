"""Render ONE shot of a story reel (runs inside Blender).

    blender -b -P scripts/render_story.py -- stories/claude_brain_surgery.json --shot storm [--fast] [--frames 10-12]

Usually called by scripts/make_story.py, which renders every shot and assembles the reel.
"""
import argparse
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import bpy  # noqa: E402

from studio import scene as sc, storytime  # noqa: E402
from render_reel import enable_gpu, tune_cycles  # noqa: E402


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("story")
    ap.add_argument("--shot", required=True)
    ap.add_argument("--out", help="output dir (default output/<story name>)")
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--engine", choices=["eevee", "cycles"], default="cycles")
    ap.add_argument("--samples", type=int)
    ap.add_argument("--frames", help="local frame range to render, e.g. 1-5")
    args = ap.parse_args(argv)

    story = storytime.load(args.story)
    shot = next(s for s in story["timed_shots"] if s["id"] == args.shot)
    out = Path(args.out or ROOT / "output" / story["name"])
    shot_dir = out / "shots" / f"{shot['index']:02d}_{shot['id']}"
    shot_dir.mkdir(parents=True, exist_ok=True)

    spec = SimpleNamespace(quality="draft" if args.fast else "final", fps=story["fps"], frames=shot["frames"])
    scene = sc.reset_scene()
    sc.configure_render(scene, spec, str(out), args.engine)
    scene.render.filepath = str(shot_dir / "frame_")
    scene.render.use_motion_blur = not args.fast

    cues = []
    ctx = SimpleNamespace(frames=shot["frames"], fps=story["fps"], lines=shot["lines_rel"],
                          cue=lambda t, kind, **kw: cues.append({"t": round(float(t), 3), "type": kind, **kw}))
    module = importlib.import_module(f"studio.stories.{story['module']}")
    module.SHOTS[shot["id"]](scene, ctx)
    (shot_dir / "cues.json").write_text(json.dumps(cues, indent=1))
    for obj in scene.objects:  # round props (spheres) should never look faceted
        if obj.type == "MESH" and obj.name.startswith(("Sphere", "Icosphere")) and hasattr(obj.data, "shade_smooth"):
            obj.data.shade_smooth()

    if args.engine == "cycles":
        device = enable_gpu()
        tune_cycles(scene, samples=args.samples or (10 if args.fast else 96), fast=args.fast, overlay=False, device=device)
    if args.frames:
        lo, _, hi = args.frames.partition("-")
        scene.frame_start, scene.frame_end = int(lo), int(hi or lo)
    print(f"[story] {story['name']} shot {shot['index']} '{shot['id']}': frames {scene.frame_start}-{scene.frame_end}", flush=True)
    bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
