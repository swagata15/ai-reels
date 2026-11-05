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
    ap.add_argument("--samples", type=int, help="override Cycles samples for the main pass")
    ap.add_argument("--skip-main", action="store_true", help="only render overlay (text/HUD) passes")
    args = ap.parse_args(argv)

    spec = ReelSpec.load(args.spec)
    if args.draft:
        spec.quality = "draft"
    studio.build(spec, output_dir=args.out)

    scene = bpy.context.scene
    passes = [scene] + [s for s in bpy.data.scenes if s.get("reel_pass") == "overlay"]
    for sc in passes:
        overlay = sc is not scene
        if args.engine == "cycles" or sc.render.engine == "CYCLES":
            sc.render.engine = "CYCLES"
            sc.cycles.device = "CPU"
            sc.cycles.samples = 4 if overlay else (args.samples or (32 if spec.quality == "draft" else 128))
            sc.cycles.use_denoising = not overlay
        if args.frames:
            lo, _, hi = args.frames.partition("-")
            sc.frame_start = int(lo)
            sc.frame_end = int(hi or lo)
    if args.skip_main:
        passes = passes[1:]
    for sc in passes:
        print(f"[reels] rendering {spec.name} [{sc.name}]: frames {sc.frame_start}-{sc.frame_end} -> {sc.render.filepath}", flush=True)
        bpy.ops.render.render(animation=True, scene=sc.name)
    print("[reels] done")


if __name__ == "__main__":
    main()
