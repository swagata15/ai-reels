# How to make a new Zack-D-style reel (for @the.ai.gal)

## The short version
1. Open **Claude Code** on this repo (claude.ai/code -> pick `swagata15/ai-reels`, or run `claude` inside the folder).
2. Type: **`/story-reel <your topic>`** - e.g. `/story-reel AI chatbots rated more empathetic than doctors`.
   Or to build one of the ready scripts: `/story-reel build stories/drafts/psych_01_essay_memory.md`.
3. Approve the facts + script Claude shows you (reply with changes if you want).
4. Claude builds the shots and test-renders them; it shows you a contact sheet of frames.
5. **Record your voice**: read the numbered lines in one take, ~1 second pause between lines
   (phone voice memo is fine). Upload it in the chat.
6. Claude syncs everything to your voice and renders:
   - quick preview on the cloud CPU (~1 hour for 30 s), or
   - final quality on RunPod (minutes) - see below.
7. Post the MP4 with the caption from `captions/<name>.md`. Add trending audio quietly under your voice if you like.

## What makes it "Zack D" (the formula Claude follows)
Hook with tension in < 3 s -> setup with stakes -> "which would you pick?" -> twist -> the key number
shown as a physical thing with an everyday comparison -> honest caveat -> a question to the viewer.
A new visual every 2-4 s, bright studio for explaining, dark/lab for drama, red 3D arrows / question
marks / measurement lines, word-by-word captions, a sound on every action. Full rules: `stories/STYLE_GUIDE.md`.

## Rendering on RunPod (fast, final quality)
1. Make sure everything is pushed to GitHub (Claude does this).
2. RunPod -> Deploy GPU Pod (RTX 4090, "RunPod PyTorch" template) -> open the web terminal.
3. Story reels:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/swagata15/ai-reels/main/scripts/runpod.sh | STORIES="stories/*.json" bash
   ```
   Data reels (the 12 in `reels/`) render with the same command without `STORIES=`.
4. Download the zip from the Jupyter file browser, then **stop the pod**.

## What's ready right now
| Reel | Script | Shots built | Voice |
|---|---|---|---|
| Claude brain surgery | `stories/claude_brain_surgery.md` | yes | record it |
| 12 "Your Brain on AI" stories | `stories/drafts/*.md` | not yet (use `/story-reel build ...`) | record them |
| 12 data reels (old style, no voice needed) | `reels/*.json` | yes | - |

## Tips for recording your voice
- Quiet room, phone 15-20 cm from your mouth, speak a little slower than normal and smile on the hook.
- If you stumble, pause 1 second and say the line again; tell Claude which take to drop.
- Record all scripts in one sitting - your voice stays consistent across the series.
