"""Story timing: narration lines -> absolute times -> shot frame ranges (pure Python, no bpy).

Line durations come from the recorded voice when stories/<name>.voice.json exists
(written by scripts/voice_align.py), otherwise from a words-per-second estimate.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

WPS = 3.1  # narration speed estimate (words per second)
PAUSE = 0.25


def load(story_path):
    story = json.loads(Path(story_path).read_text())
    story["_path"] = str(story_path)
    voice = Path(story_path).with_suffix(".voice.json")
    times = json.loads(voice.read_text())["lines"] if voice.exists() else None
    t = float(story.get("lead_in", 0.3))
    lines = []
    for i, line in enumerate(story["lines"]):
        if times:
            start, end = times[i]["start"], times[i]["end"]
        else:
            words = len(line["text"].split())
            dur = float(line.get("dur", words / WPS + PAUSE))
            start, end = t, t + dur
        lines.append({"n": i + 1, "text": line["text"], "start": start, "end": end})
        t = end
    story["timed_lines"] = lines
    story["duration"] = lines[-1]["end"] + float(story.get("tail", 1.5))
    fps = story.get("fps", 24)
    shots, prev_end = [], 0
    for k, shot in enumerate(story["shots"]):
        ls = [lines[n - 1] for n in shot["lines"]]
        start = 0.0 if k == 0 else ls[0]["start"]
        end = story["duration"] if k == len(story["shots"]) - 1 else lines[story["shots"][k + 1]["lines"][0] - 1]["start"]
        f0 = prev_end + 1
        f1 = max(f0, round(end * fps))
        shots.append({**shot, "index": k + 1, "start": start, "end": end, "frame_start": f0, "frame_end": f1,
                      "frames": f1 - f0 + 1,
                      "lines_rel": [(max(1, round((l["start"] - start) * fps) + 1),
                                     max(1, round((l["end"] - start) * fps) + 1)) for l in ls]})
        prev_end = f1
    story["timed_shots"] = shots
    return story


def caption_chunks(line, max_words=3):
    """Split a line into 1-3 word chunks with times proportional to their length."""
    words = line["text"].split()
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= max_words or w[-1] in ",.?!:":
            chunks.append(" ".join(cur))
            cur = []
    if cur:
        chunks.append(" ".join(cur))
    weights = [len(c) + 2 for c in chunks]
    total = sum(weights)
    t, out = line["start"], []
    span = line["end"] - line["start"] - 0.12
    for c, w in zip(chunks, weights):
        d = span * w / total
        out.append((t, t + d, c))
        t += d
    return out
