"""Time a story to YOUR narration: split the recording on pauses, one segment per script line.

    python scripts/voice_align.py stories/claude_brain_surgery.json voice/brain_surgery.m4a

Record the script in one take with a ~1 s pause between lines (re-say a line after a pause if you
stumble, then delete the bad take with --drop). Writes stories/<story>.voice.json; after that,
make_story.py renders shots, captions and sound effects on your timing:

    python scripts/make_story.py stories/claude_brain_surgery.json --voice voice/brain_surgery.m4a
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


def speech_segments(audio, noise_db=-35, min_pause=0.55):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(audio), "-af",
                          f"silencedetect=noise={noise_db}dB:d={min_pause}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    dur = float(re.search(r"Duration: (\d+):(\d+):([\d.]+)", out).groups()[2]) + \
        60 * float(re.search(r"Duration: (\d+):(\d+)", out).group(2)) + \
        3600 * float(re.search(r"Duration: (\d+)", out).group(1))
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    segs, t = [], 0.0
    for s, e in zip(starts, ends + [dur] * (len(starts) - len(ends))):
        if s - t > 0.15:
            segs.append([t, s])
        t = e
    if dur - t > 0.15:
        segs.append([t, dur])
    return segs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("story")
    ap.add_argument("audio")
    ap.add_argument("--noise-db", type=float, default=-35, help="silence threshold (raise to -30 for noisy rooms)")
    ap.add_argument("--min-pause", type=float, default=0.55, help="shortest pause (s) that separates lines")
    ap.add_argument("--drop", default="", help="comma-separated segment numbers to discard (bad takes)")
    args = ap.parse_args()

    story = json.loads(Path(args.story).read_text())
    n = len(story["lines"])
    segs = speech_segments(args.audio, args.noise_db, args.min_pause)
    drop = {int(x) for x in args.drop.split(",") if x}
    segs = [s for i, s in enumerate(segs, 1) if i not in drop]
    print(f"found {len(segs)} spoken segments for {n} script lines")
    while len(segs) > n:  # merge the pair with the shortest gap (a pause inside a line)
        k = min(range(len(segs) - 1), key=lambda i: segs[i + 1][0] - segs[i][1])
        segs[k] = [segs[k][0], segs[k + 1][1]]
        del segs[k + 1]
    if len(segs) < n:
        raise SystemExit(f"Only {len(segs)} segments for {n} lines - pause a little longer between lines, "
                         f"or lower --min-pause (now {args.min_pause}).")
    lines = []
    for i, (a, b) in enumerate(segs):
        lines.append({"line": i + 1, "start": round(a, 3), "end": round(b, 3), "text": story["lines"][i]["text"]})
        print(f"{i + 1:2}. {a:6.2f}-{b:6.2f}s  {story['lines'][i]['text']}")
    out = Path(args.story).with_suffix(".voice.json")
    out.write_text(json.dumps({"audio": str(args.audio), "lines": lines}, indent=1))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
