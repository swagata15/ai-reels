"""Turn rendered PNG frames into an Instagram-Reels-ready MP4 (+ cover image).

    python scripts/postprocess.py output/neon_orb --music music/track.mp3 --glow --loops 2

Output spec (what Instagram recommends): 1080x1920, H.264 High, yuv420p, constant
frame rate, AAC 48 kHz stereo, faststart. Needs ffmpeg on PATH.
"""
from __future__ import annotations

import argparse
import glob
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> None:
    print("[post]", " ".join(cmd))
    subprocess.run(cmd, check=True)


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    return float(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("render_dir", help="directory containing frames/frame_####.png (e.g. output/neon_orb)")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--music", help="audio file to lay under the reel (trimmed + faded to fit)")
    ap.add_argument("--music-start", type=float, default=0.0, help="seconds into the track to start")
    ap.add_argument("--glow", action="store_true", help="add a soft bloom over bright areas")
    ap.add_argument("--grain", action="store_true", help="add subtle film grain (helps against IG banding)")
    ap.add_argument("--loops", type=int, default=1, help="repeat a seamless loop N times")
    ap.add_argument("--cover-frame", type=int, help="frame number for the cover image (default: middle)")
    ap.add_argument("--crf", type=int, default=17)
    ap.add_argument("--no-sfx", action="store_true", help="skip the generated sound effects track")
    ap.add_argument("--sfx-gain", type=float, default=1.0, help="sound-effects volume (with --music, try 0.8)")
    ap.add_argument("--music-gain", type=float, default=0.55, help="music volume under the sound effects")
    ap.add_argument("--out", help="output mp4 path (default <render_dir>/<name>_reel.mp4)")
    args = ap.parse_args()

    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found - install it (brew install ffmpeg / winget install ffmpeg / apt install ffmpeg)")

    render_dir = Path(args.render_dir)
    frames = sorted(glob.glob(str(render_dir / "frames" / "frame_*.png")))
    if not frames:
        sys.exit(f"No frames in {render_dir / 'frames'} - render first")
    first = int(Path(frames[0]).stem.split("_")[-1])
    name = render_dir.name
    out = Path(args.out) if args.out else render_dir / f"{name}_reel.mp4"

    overlay_dir = render_dir / "frames_overlay"
    has_overlay = bool(glob.glob(str(overlay_dir / "frame_*.png")))

    # Video filter chain. Frames may be draft (540x960); always deliver 1080x1920.
    vf = ["scale=1080:1920:flags=lanczos"]
    if args.glow:
        vf.append("split[gb][gg];[gg]curves=all='0/0 0.6/0 1/1',gblur=sigma=28[bloom];[gb][bloom]blend=all_mode=screen")
    if args.grain:
        vf.append("noise=alls=4:allf=t")
    vf.append("format=yuv420p")

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-stats"]
    if args.loops > 1:
        cmd += ["-stream_loop", str(args.loops - 1)]
    cmd += ["-framerate", str(args.fps), "-start_number", str(first), "-i", str(render_dir / "frames" / "frame_%04d.png")]
    video_in = "[0:v]"
    pre = ""
    if has_overlay:
        # Text/HUD pass: composited after glow on the 3D, then given its own soft glow.
        if args.loops > 1:
            cmd += ["-stream_loop", str(args.loops - 1)]
        cmd += ["-framerate", str(args.fps), "-start_number", str(first), "-i", str(overlay_dir / "frame_%04d.png")]
        pre = "[1:v]scale=1080:1920:flags=lanczos,split[ov][ovg];[ovg]gblur=sigma=10[ovb];"
    audio_idx = 2 if has_overlay else 1

    duration = len(frames) / args.fps * args.loops
    fmt = vf.pop()  # keep format=yuv420p last
    graph = f"{pre}[0:v]{','.join(vf)}[base]"
    if has_overlay:
        graph += ";[base][ovb]overlay[b1];[b1][ov]overlay"
    else:
        graph += ";[base]null"
    graph += f",{fmt}[v]"
    maps = ["-map", "[v]"]

    # Audio: generated SFX (if the template wrote cues) and/or a music bed.
    audio_labels = []
    cues = render_dir / "sfx_cues.json"
    if cues.exists() and not args.no_sfx:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import sfx

            wav = sfx.render(cues, render_dir / "sfx.wav")
            offset = (first - 1) / args.fps  # partial renders start later in the timeline
            cmd += ["-i", str(wav)]
            graph += (f";[{audio_idx}:a]atrim={offset:.3f}:{offset + duration:.3f},asetpts=PTS-STARTPTS,"
                      f"volume={args.sfx_gain}[sfx]")
            audio_labels.append("[sfx]")
            audio_idx += 1
        except ImportError:
            print("[post] numpy not installed - skipping sound effects (pip install numpy)")
    if args.music:
        cmd += ["-ss", str(args.music_start), "-i", args.music]
        fade = min(1.5, duration / 4)
        graph += (f";[{audio_idx}:a]atrim=0:{duration:.3f},afade=t=in:d=0.3,"
                  f"afade=t=out:st={duration - fade:.3f}:d={fade:.3f},aresample=48000,"
                  f"volume={args.music_gain if audio_labels else 1.0}[mus]")
        audio_labels.append("[mus]")
    if audio_labels:
        if len(audio_labels) == 2:
            graph += f";{''.join(audio_labels)}amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]"
        else:
            graph += f";{audio_labels[0]}anull[a]"
        maps += ["-map", "[a]", "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-ar", "48000"]
    cmd += ["-filter_complex", graph, *maps]

    cmd += ["-c:v", "libx264", "-profile:v", "high", "-preset", "slow", "-crf", str(args.crf),
            "-r", str(args.fps), "-g", str(args.fps * 2), "-movflags", "+faststart",
            "-t", f"{duration:.3f}", str(out)]
    run(cmd)

    cover_idx = (args.cover_frame - first) if args.cover_frame else len(frames) // 2
    cover_src = frames[max(0, min(cover_idx, len(frames) - 1))]
    cover = out.with_name(f"{name}_cover.jpg")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", cover_src, "-vf", "scale=1080:1920:flags=lanczos", "-q:v", "2", str(cover)])

    print(f"\n[post] reel : {out}  ({probe_duration(out):.1f}s)")
    print(f"[post] cover: {cover}")


if __name__ == "__main__":
    main()
