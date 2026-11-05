"""Headless render entry point.

    blender -b -P scripts/render_reel.py -- reels/examples/neon_orb.json [--fast | --draft] [--frames 1-30]
                                            [--out DIR] [--engine eevee|cycles] [--samples N]

Speed guide (9 s reel, 270 frames):
  * EEVEE on a GPU (default)            ~1-3 min at full 1080x1920
  * Cycles on a GPU (--engine cycles)   ~5-15 min, most realistic
  * Cycles on CPU only + --fast         ~3-4 s/frame at half res (cloud / laptops without GPU)

Then run scripts/postprocess.py (or scripts/batch.py does both for many reels).
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import bpy  # noqa: E402

import studio  # noqa: E402
from studio.spec import ReelSpec  # noqa: E402


def enable_gpu() -> str:
    """Turn on the best available Cycles GPU backend; returns the device used."""
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
    except KeyError:
        return "CPU"
    for backend in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
        try:
            prefs.compute_device_type = backend
            prefs.get_devices()
        except TypeError:
            continue
        gpus = [d for d in prefs.devices if d.type == backend]
        if gpus:
            for d in prefs.devices:
                d.use = d.type == backend
            return "GPU"
    return "CPU"


def tune_cycles(sc, *, samples: int, fast: bool, overlay: bool, device: str) -> None:
    c = sc.cycles
    c.device = device
    c.samples = 4 if overlay else samples
    c.use_denoising = not overlay
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.05 if fast else 0.01
    if fast or overlay:
        c.max_bounces, c.diffuse_bounces, c.glossy_bounces = 4, 2, 2
        c.transmission_bounces, c.volume_bounces, c.transparent_max_bounces = 4, 0, 8
        c.caustics_reflective = c.caustics_refractive = False
        sc.render.use_motion_blur = False


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser(description="Render a reel spec to PNG frames")
    ap.add_argument("spec", help="path to a reels/*.json spec")
    ap.add_argument("--draft", action="store_true", help="half resolution, fewer samples")
    ap.add_argument("--fast", action="store_true", help="draft + lean light paths: quickest previews/CPU renders")
    ap.add_argument("--frames", help="render only a range, e.g. 1-30 or 45")
    ap.add_argument("--out", help="output directory (default output/<name>)")
    ap.add_argument("--engine", choices=["eevee", "cycles"], default="eevee",
                    help="eevee = fast (needs a GPU); cycles = most realistic, also works on CPU")
    ap.add_argument("--samples", type=int, help="override samples for the main pass")
    ap.add_argument("--skip-main", action="store_true", help="only render overlay (text/HUD) passes")
    args = ap.parse_args(argv)

    spec = ReelSpec.load(args.spec)
    if args.draft or args.fast:
        spec.quality = "draft"
    studio.build(spec, output_dir=args.out, engine=args.engine)

    scene = bpy.context.scene
    passes = [scene] + [s for s in bpy.data.scenes if s.get("reel_pass") == "overlay"]
    device = enable_gpu() if args.engine == "cycles" else "CPU"
    default_samples = 10 if args.fast else (32 if spec.quality == "draft" else 128)
    for sc in passes:
        overlay = sc is not scene
        if args.engine == "cycles":
            sc.render.engine = "CYCLES"
            tune_cycles(sc, samples=args.samples or default_samples, fast=args.fast, overlay=overlay, device=device)
        elif hasattr(sc.eevee, "taa_render_samples"):
            sc.eevee.taa_render_samples = 4 if overlay else (args.samples or (16 if args.fast else sc.eevee.taa_render_samples))
        if args.frames:
            lo, _, hi = args.frames.partition("-")
            sc.frame_start = int(lo)
            sc.frame_end = int(hi or lo)
    if args.skip_main:
        passes = passes[1:]
    for sc in passes:
        print(f"[reels] rendering {spec.name} [{sc.name}, {sc.render.engine}/{device}]: "
              f"frames {sc.frame_start}-{sc.frame_end} -> {sc.render.filepath}", flush=True)
        bpy.ops.render.render(animation=True, scene=sc.name)
    print("[reels] done")


if __name__ == "__main__":
    main()
