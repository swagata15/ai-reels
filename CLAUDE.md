# AI Reels Studio - instructions for Claude

This project makes short vertical 3D reels for an Instagram AI page, using Blender
driven through the **Blender MCP** server (`blender-mcp`, configured in `.mcp.json`).

## Hard rules for every reel
- Canvas **1080x1920 (9:16)**, **30 fps**, 5-15 s for most reels (hooks die after ~3 s).
- Keep text and the main subject **out of the top 250 px and bottom 420 px**; Instagram's UI covers them.
- **Hook in the first 1 s**: something moves or a line of text lands by frame ~15.
- Prefer **seamless loops** (last frame flows into the first); use `studio.scene.loop_phase(frame, total)`.
- Dark backgrounds plus 2-3 saturated accent colours read best on phones. One palette per reel.
- Text: 3-6 words per line, max ~3 lines on screen, high contrast, no thin fonts.

## How to build a reel
1. Write or edit a spec in `reels/<name>.json` (`template`, `duration_s`, `palette`, `text`, `params`).
   Templates: `realistic_brain`, `holo_brain`, `neon_orb`, `kinetic_title`, `crystal_loop`
   (see docstrings in `studio/templates/`). Put text/HUD in an overlay scene (`studio.text.overlay_scene`)
   when the main shot uses depth of field.
2. Build it live in the user's open Blender through MCP with `execute_blender_code`:
   ```python
   import sys, importlib
   ROOT = r"<absolute path to ai-reels-studio>"
   sys.path.insert(0, ROOT)
   import studio; importlib.reload(studio)
   studio.build(ROOT + "/reels/<name>.json")
   ```
   Then use `get_viewport_screenshot` to check composition, and iterate on the spec or params.
3. For bespoke scenes, write new bpy code via `execute_blender_code`. If it works well,
   turn it into a new template in `studio/templates/` (a `build(scene, spec)` function, added to
   `TEMPLATES` in `studio/__init__.py`).
4. Render headless and post-process (or let the user run these):
   ```
   blender -b -P scripts/render_reel.py -- reels/<name>.json
   python scripts/postprocess.py output/<name> --glow --music music/<track>.mp3
   ```
   Use `--draft --frames 1-60` for quick previews.

## Blender MCP tips
- Send small, focused `execute_blender_code` calls; large scripts can time out the socket.
- Poly Haven / Sketchfab / Hyper3D asset tools only work if the user enabled them in the
  BlenderMCP sidebar panel. Check with `get_polyhaven_status` before using them.
- Always confirm the scene with `get_scene_info` and a viewport screenshot before rendering.
- Don't use copyrighted characters, logos or music. Use original designs only.

## Data-story reels (`data_story` template)
- 20-30 s: hook (0-3 s) -> study setup -> stat (ring counter) / bars -> meaning + caveat -> takeaway -> end card.
- Every number must come from a primary source; put the source on the end card and the caveat on screen or in the caption.
- Sound effects are generated automatically from beat cues (`sfx_cues.json`); `--no-sfx` disables them.
- Handle for end cards: @the.ai.gal

## Accuracy
News-style reels must match what actually happened. Use footnotes ("*on a mouse"), put caveats
in the caption, cite the source, and never present speculation as fact.

## Deliver with every reel
Give the user a caption (hook line + 2-3 lines of value + call to action) and 5-8 relevant hashtags.
