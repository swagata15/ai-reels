---
name: story-reel
description: Turn any topic, news story or study into a narrated, Zack-D-Films-style 3D story reel for the Instagram page @the.ai.gal - research and fact-check, write a hook-driven ~30 s script, build the shots in Blender with studio/storykit.py, test-render every shot, then render with captions, sound effects and the user's own voice. Use whenever the user gives a topic and wants a reel, a story, or "the same style" for something new.
---

# Story reel: topic in, Zack-D-level reel out

You are producing a short narrated 3D explainer for **@the.ai.gal** (research-backed AI and psychology,
authentic, no hype). The quality bar is Zack D. Films. Read `stories/STYLE_GUIDE.md` first, every time.
The finished example to copy from is `stories/claude_brain_surgery.json` + `studio/stories/brain_surgery.py`.

Work through the steps in order. Do not skip the test-render step; it is where quality comes from.

## 1. Research and verify (never skip)
- Search for the topic (WebSearch, `mode: "extended"` for news). Prefer primary sources: the paper,
  the company post, the university press release. Note every number with its source.
- For each claim, record: exact number, who reported it, peer-reviewed or not, the honest caveat.
- Company claims stay "the company says / reportedly". Correlations are never written as causes.
  If a number can't be confirmed, drop it. Never invent statistics, quotes or details.
- Tell the user in 3-5 lines what is solid, what is shaky, and the story angle you suggest.

## 2. Find the story (the 7-beat formula)
1. **Hook = what happened + tension**, under 3 s ("This tiny mouse just had brain surgery... and no human chose the treatment.")
2. **Setup with stakes**: who, what they had, the one goal.
3. **Ask the viewer**: "Which one would you pick? This one, right?" (voice the obvious wrong answer).
4. **Twist #1**: what went wrong or surprised.
5. **The key moment, shown big**: the number becomes a physical measurement (counter + red dimension line)
   with an **everyday comparison** (a pinhead, a grain of rice, a swimming pool). Check the comparison maths.
6. **Twist #2 / reality check**: the caveat said out loud. It builds trust.
7. **Question to the viewer** (drives comments), then the end card.

Script rules: 10-13 lines, ~30-35 s total, max ~11 words per line, conversational, read-aloud test.
One line = one visual idea. Show the user the script and get a thumbs-up before building.

## 3. Shot plan
- Map lines to shots: a **new visual every 2-4 s**. Alternate looks: `K.studio()` (bright cyan explainer,
  floating props, no floor), `K.lab()` (dark, warm surgical light, bokeh), `K.dark()` (drama, inside views).
- Start on a tangible object at human scale, escalate scale or drama, explain in the bright studio.
- Use the 3D annotation language: `K.red_arrow`, `K.dimension_line` + `K.Counter`, `K.question_mark`,
  `K.red_x`, `K.label3d`. Put numbers *in* the scene.
- Write the storyboard table (line | look | shot | annotation | SFX) into `stories/<slug>.md` together
  with the recording script and sources.

## 4. Build
Scaffold with `python scripts/new_story.py <slug> "<title>"`, then fill in:
- `stories/<slug>.json`: `name`, `module`, `fps` (24), `lines`, `shots` (`{"id", "lines": [n, ...]}`),
  `handle`, `source` (shown small on the end card).
- `studio/stories/<slug>.py`: one `builder(scene, ctx)` per shot + a `SHOTS` dict. `ctx.frames`,
  `ctx.fps`, `ctx.lines` (local frame range of each narration line in the shot) and `ctx.cue(t, type)`.
  Drive every event from `ctx.lines` so the timing follows the user's voice later.
- Reuse the kit in `studio/storykit.py`: `lab_mouse`, `surgical_drape`, `mouse_brain`, `storm_material`,
  `vial`, `sewing_pin`, `droplet`, `needle_rig`, `gloved_hand`, `label3d`, `pop_scale`, `cam_move`, `key`.
  New props go into the kit (reusable), built from primitives + `K.organic()` for smooth shapes.
- SFX cue types: impact, whoosh, pop, tick_run, ding, riser, chime, chime_one, heartbeat, thud, tap,
  glint, buzz, servo, beep, slide, drip, crackle, rustle. Put one on every visible action.

### Framing rules (portrait 9:16; this is where most bugs come from)
- Visible **width** at distance d = d x 13.5 / lens; visible **height** = d x 24 / lens.
  Compute it for every shot so nothing important is cropped. Leave about 10% margin each side.
- 3D labels: size ~0.25 fits ~12 characters across a 3.5-unit-wide view. Keep labels in the middle 80%.
- Keep the lower 25% of the frame calm: captions sit there (~74% down).
- Code-built hands look like blobs. Use red arrows to point, and only show hands as small partial
  elements (pinch from below). Use real hand assets if the user provides them.
- Spheres are smoothed automatically; glass needs >= 6 samples with denoise.

## 5. Test render (mandatory, iterate until clean)
For every shot, render 1-2 key frames (mid-action) quickly and **look at them**:
```bash
blender -b -P scripts/render_story.py -- stories/<slug>.json --shot <id> --fast --samples 4 --frames <n> --out /tmp/test
ffmpeg -i shotA.png -i shotB.png ... -filter_complex "hstack=N,scale=1800:-1" sheet.png   # then view it
```
Fix cropping, clutter, unreadable labels, wrong scale and dull compositions. Repeat until every shot
reads clearly at phone size. Check one frame with captions burned in.

## 6. Voice, render, deliver
- The user narrates (their own voice): one take, ~1 s pause between lines. Then
  `python scripts/voice_align.py stories/<slug>.json <audio>`; the timing now follows their voice.
- Preview on CPU: `python scripts/make_story.py stories/<slug>.json --fast --samples 6` (~5-10 s/frame).
  Final on a GPU (RunPod): `STORIES=stories/<slug>.json bash scripts/runpod.sh`, or
  `make_story.py ... --voice <audio>` without `--fast`.
- Write `captions/<slug>.md`: hook line, 3-5 lines of facts, the caveat, a question, "Follow @the.ai.gal",
  source line, 6-8 hashtags.
- Send the MP4 + caption to the user and push the new files to GitHub.
