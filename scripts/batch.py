"""Render + post-process many reels in one go.

    python scripts/batch.py "reels/*.json" --blender /path/to/blender --engine cycles
    python scripts/batch.py reels/a.json reels/b.json --fast --post "--glow --grain"

Each reel ends up in output/<name>/<name>_reel.mp4 (+ _cover.jpg). Reels whose MP4 already
exists are skipped, so you can re-run after adding new specs. A summary prints at the end.
"""
from __future__ import annotations

import argparse
import glob
import json
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("specs", nargs="+", help="spec files or globs, e.g. 'reels/*.json'")
    ap.add_argument("--blender", default=shutil.which("blender") or "blender", help="Blender executable")
    ap.add_argument("--engine", choices=["eevee", "cycles"], default="cycles")
    ap.add_argument("--fast", action="store_true", help="half-res lean render (for CPU / quick drafts)")
    ap.add_argument("--samples", type=int)
    ap.add_argument("--post", default="--glow --grain", help="extra flags for postprocess.py")
    ap.add_argument("--out", default=str(ROOT / "output"))
    ap.add_argument("--force", action="store_true", help="re-render even if the MP4 exists")
    args = ap.parse_args()

    specs = sorted({p for pattern in args.specs for p in (glob.glob(pattern) or [pattern])})
    results = []
    for spec in specs:
        name = json.loads(Path(spec).read_text())["name"]
        out_dir = Path(args.out) / name
        mp4 = out_dir / f"{name}_reel.mp4"
        if mp4.exists() and not args.force:
            print(f"[batch] skip {name} (already rendered)")
            results.append((name, "skipped", 0.0))
            continue
        if out_dir.exists():
            shutil.rmtree(out_dir / "frames", ignore_errors=True)
            shutil.rmtree(out_dir / "frames_overlay", ignore_errors=True)
        t0 = time.time()
        render = [args.blender, "-b", "-P", str(ROOT / "scripts" / "render_reel.py"), "--", spec,
                  "--engine", args.engine, "--out", str(out_dir)]
        if args.fast:
            render.append("--fast")
        if args.samples:
            render += ["--samples", str(args.samples)]
        print(f"[batch] rendering {name} ...", flush=True)
        ok = subprocess.run(render).returncode == 0
        if ok:
            post = [sys.executable, str(ROOT / "scripts" / "postprocess.py"), str(out_dir), *shlex.split(args.post)]
            ok = subprocess.run(post).returncode == 0
        results.append((name, "ok" if ok else "FAILED", time.time() - t0))

    print("\n[batch] summary")
    for name, status, secs in results:
        print(f"  {status:8} {name:40} {secs / 60:5.1f} min")
    if any(s == "FAILED" for _, s, _ in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
