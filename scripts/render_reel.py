"""Headless render entry point.

    blender -b -P scripts/render_reel.py -- reels/neon_orb.json [--draft] [--frames 1-30] [--out DIR] [--engine cycles]

Then run scripts/postprocess.py to produce the Instagram-ready MP4.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import bpy  # noqa: E402

import studio  # noqa: E402
from studio.spec import ReelSpec  # noqa: E402


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser(description="Render a reel spec to PNG frames")
    ap.add_argument("spec", help="path to a reels/*.json spec")
    ap.add_argument("--draft", action="store_true", help="half resolution, fewer samples")
    ap.add_argument("--frames", help="render only a range, e.g. 1-30 or 45")
    ap.add_argument("--out", help="output directory (default output/<name>)")
    ap.add_argument("--engine", choices=["eevee", "cycles"], default="eevee",
                    help="cycles works on CPU-only machines (slower)")
    args = ap.parse_args(argv)

    spec = ReelSpec.load(args.spec)
    if args.draft:
        spec.quality = "draft"
    studio.build(spec, output_dir=args.out)

    scene = bpy.context.scene
    if args.engine == "cycles":
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = 24 if spec.quality == "draft" else 128
        scene.cycles.use_denoising = True
    if args.frames:
        lo, _, hi = args.frames.partition("-")
        scene.frame_start = int(lo)
        scene.frame_end = int(hi or lo)
    print(f"[reels] rendering {spec.name}: frames {scene.frame_start}-{scene.frame_end} -> {scene.render.filepath}")
    bpy.ops.render.render(animation=True)
    print("[reels] done")


if __name__ == "__main__":
    main()
