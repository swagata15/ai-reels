"""Scaffold a new story reel: stories/<slug>.json, stories/<slug>.md and studio/stories/<slug>.py.

    python scripts/new_story.py ai_lie_detector "The AI that caught a liar"

Then fill in the script lines, the shot list and each shot builder (see .claude/skills/story-reel).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    slug = re.sub(r"[^a-z0-9_]", "_", sys.argv[1].lower())
    title = sys.argv[2]
    story = ROOT / "stories" / f"{slug}.json"
    module = ROOT / "studio" / "stories" / f"{slug}.py"
    board = ROOT / "stories" / f"{slug}.md"
    for p in (story, module, board):
        if p.exists():
            sys.exit(f"{p} already exists")
    shots = ["hook", "setup", "question", "twist", "key_moment", "reality_check", "end"]
    story.write_text(json.dumps({
        "name": f"{slug}_story", "module": slug, "fps": 24, "lead_in": 0.3, "tail": 1.5,
        "handle": "@the.ai.gal", "source": "Source: ...",
        "lines": [{"text": f"Line {i + 1} ({s})"} for i, s in enumerate(shots)],
        "shots": [{"id": s, "lines": [i + 1]} for i, s in enumerate(shots)],
    }, indent=2) + "\n")
    board.write_text(f"# Story: \"{title}\"\n\n## Recording script\n" +
                     "".join(f"{i + 1}. ...\n" for i in range(len(shots))) +
                     "\n## Shot list\n| Line | Look | Shot | 3D annotation | SFX |\n|---|---|---|---|---|\n\n## Sources\n")
    funcs = "\n\n".join(f'''def {s}(scene, ctx):
    (a, b), = ctx.lines[:1]
    K.studio(scene)
    lbl = K.label3d("{s.upper()}", "#0E2A47", 0.25)
    K.pop_scale(lbl, a + 2, dur=8)
    ctx.cue(a / ctx.fps, "pop")
    cam = K.camera(scene, (0, -8, 0.5), (0, 0, 0.3), lens=40)
    K.cam_move(cam, 1, ctx.frames, (0.3, -8.4, 0.6), (-0.2, -7.4, 0.5), (0, 0, 0.3), (0, 0, 0.3))''' for s in shots)
    module.write_text(f'''"""Shot builders for stories/{slug}.json - "{title}". See .claude/skills/story-reel/SKILL.md."""
from __future__ import annotations

import math

import bpy
from mathutils import Vector

from .. import looks, scene as sc
from .. import storykit as K


{funcs}


SHOTS = {{f.__name__: f for f in ({", ".join(shots)})}}
''')
    print(f"created:\n  {story}\n  {board}\n  {module}")


if __name__ == "__main__":
    main()
