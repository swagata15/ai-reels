"""Render all shots of a story reel and assemble the final video (captions + SFX + your voice).

    python scripts/make_story.py stories/claude_brain_surgery.json --blender /path/to/blender
    python scripts/make_story.py stories/claude_brain_surgery.json --post-only --voice voice/brain.m4a

Finished shots are skipped (use --force or --only to re-render). Output: output/<name>/<name>.mp4
"""
from __future__ import annotations

import argparse
import glob
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from studio import storytime  # noqa: E402


def ass_time(t):
    t = max(0.0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def write_captions(story, path):
    lines = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1080", "PlayResY: 1920", "WrapStyle: 0", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding",
        "Style: Cap,Inter ExtraBold,92,&H00FFFFFF,&H00FFFFFF,&H00141414,&H78000000,0,0,0,0,100,100,0,0,1,4,5,2,70,70,500,1",
        "Style: Src,Inter ExtraBold,30,&H00F0F0F0,&H00F0F0F0,&H00202020,&H64000000,0,0,0,0,100,100,0,0,1,2,2,2,90,90,250,1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    pop = r"{\fscx82\fscy82\t(0,90,\fscx106\fscy106)\t(90,170,\fscx100\fscy100)}"
    for line in story["timed_lines"]:
        for a, b, text in storytime.caption_chunks(line):
            lines.append(f"Dialogue: 0,{ass_time(a)},{ass_time(b)},Cap,,0,0,0,,{pop}{text}")
    last = story["timed_shots"][-1]
    src = story.get("source", "")
    if src:
        wrapped = src if len(src) < 70 else src[: src.rfind(" ", 0, 70)] + r"\N" + src[src.rfind(" ", 0, 70) + 1:]
        lines.append(f"Dialogue: 0,{ass_time(last['start'] + 0.4)},{ass_time(story['duration'])},Src,,0,0,0,,{wrapped}")
    path.write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("story")
    ap.add_argument("--blender", default=shutil.which("blender") or "blender")
    ap.add_argument("--engine", choices=["eevee", "cycles"], default="cycles")
    ap.add_argument("--fast", action="store_true", help="half-res lean render (CPU / previews)")
    ap.add_argument("--samples", type=int)
    ap.add_argument("--only", help="comma-separated shot ids to (re)render")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--post-only", action="store_true")
    ap.add_argument("--voice", help="your narration (wav/m4a/mp3); stories/<name>.voice.json sets the timing")
    ap.add_argument("--music", help="optional music bed")
    ap.add_argument("--out")
    args = ap.parse_args()

    story = storytime.load(args.story)
    out = Path(args.out or ROOT / "output" / story["name"])
    fps = story["fps"]
    only = set(args.only.split(",")) if args.only else None

    if not args.post_only:
        for shot in story["timed_shots"]:
            d = out / "shots" / f"{shot['index']:02d}_{shot['id']}"
            done = len(glob.glob(str(d / "frame_*.png"))) >= shot["frames"]
            if (only and shot["id"] not in only) or (done and not args.force and not only):
                continue
            shutil.rmtree(d, ignore_errors=True)
            cmd = [args.blender, "-b", "-P", str(ROOT / "scripts" / "render_story.py"), "--", args.story,
                   "--shot", shot["id"], "--out", str(out), "--engine", args.engine]
            if args.fast:
                cmd.append("--fast")
            if args.samples:
                cmd += ["--samples", str(args.samples)]
            print(f"[story] rendering shot {shot['index']}/{len(story['timed_shots'])}: {shot['id']} ({shot['frames']} frames)", flush=True)
            subprocess.run(cmd, check=True)

    # ---- assemble
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-stats"]
    for shot in story["timed_shots"]:
        d = out / "shots" / f"{shot['index']:02d}_{shot['id']}"
        cmd += ["-framerate", str(fps), "-i", str(d / "frame_%04d.png")]
    n = len(story["timed_shots"])
    captions = out / "captions.ass"
    write_captions(story, captions)
    fonts = ROOT / "assets" / "fonts"
    graph = "".join(f"[{i}:v]scale=1080:1920:flags=lanczos,setsar=1[s{i}];" for i in range(n))
    graph += "".join(f"[s{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0,"
    graph += f"subtitles='{captions}':fontsdir='{fonts}',noise=alls=3:allf=t,format=yuv420p[v]"

    # sound: shot cues -> absolute timeline
    cues = []
    for shot in story["timed_shots"]:
        f = out / "shots" / f"{shot['index']:02d}_{shot['id']}" / "cues.json"
        if f.exists():
            t0 = (shot["frame_start"] - 1) / fps
            cues += [{**c, "t": c["t"] + t0} for c in json.loads(f.read_text())]
    import sfx

    (out / "sfx_cues.json").write_text(json.dumps({"duration": story["duration"], "mood": story.get("mood", "calm"),
                                                    "cues": sorted(cues, key=lambda c: c["t"])}))
    wav = sfx.render(out / "sfx_cues.json", out / "sfx.wav")
    idx = n
    cmd += ["-i", str(wav)]
    audio = [f"[{idx}:a]volume={0.5 if args.voice else 1.0}[sfx]"]
    labels = ["[sfx]"]
    if args.voice:
        idx += 1
        cmd += ["-i", args.voice]
        audio.append(f"[{idx}:a]highpass=f=80,afftdn=nf=-25,acompressor=threshold=-18dB:ratio=3:attack=5:release=80,"
                     f"equalizer=f=3500:t=q:w=1:g=2,aresample=48000[vox]")
        labels.append("[vox]")
    if args.music:
        idx += 1
        cmd += ["-i", args.music]
        audio.append(f"[{idx}:a]volume=0.25,aresample=48000[mus]")
        labels.append("[mus]")
    graph += ";" + ";".join(audio) + ";" + "".join(labels) + \
        f"amix=inputs={len(labels)}:duration=first:normalize=0,alimiter=limit=0.95[a]"
    mp4 = out / f"{story['name']}.mp4"
    cmd += ["-filter_complex", graph, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-profile:v", "high",
            "-preset", "slow", "-crf", "18", "-r", str(fps), "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", "-t", f"{story['duration']:.3f}", str(mp4)]
    subprocess.run(cmd, check=True)
    print(f"[story] done: {mp4}")


if __name__ == "__main__":
    main()
