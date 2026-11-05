# Story: "The AI that operated on a brain"

**Length:** ~35 s · **Format:** narrated story, a new shot every 2-4 s, word-by-word captions,
sound design on every action · **Accuracy:** everything below is as reported by Exin Therapeutics
(company claims, not peer-reviewed). Wording like "the company says" stays in the narration.

## Story arc
| # | Time | Narration (voice-over) | Shot (what we see) | Sound |
|---|------|------------------------|--------------------|-------|
| 1 | 0-3 s | **"This mouse just had brain surgery... and no human chose the treatment."** | Extreme close-up: a needle tip trembles above a glowing living brain. Snap cut to black on "treatment". | Low heartbeat, needle whine, hard cut to silence |
| 2 | 3-8 s | "A San Francisco startup gave an AI three things: an epileptic mouse, a list of 19 gene therapies, and control of a robotic needle." | Dark lab. Camera glides past a surgical rig to a mouse under a sterile drape. 19 glowing therapy cards fan out in the air. | Lab hum, card "flick" sounds |
| 3 | 8-11 s | "One instruction: stop the seizures." | Inside the mouse brain: a storm of red electrical flashes ripples across it. | Crackling electric bursts |
| 4 | 11-15 s | "The first Claude model they tried planned the surgery... then refused to guide the needle." | The needle descends, then a red HUD flashes **"DECLINED"** and it freezes mid-air. | Descending tone, hard error buzz |
| 5 | 15-20 s | "So they switched to another Claude model. It read the research, and picked one therapy: boost the brain's natural brakes." | 18 cards fade, 1 glows cyan (**"GABA BOOST"**). Fast push-in through the cortex. | Rising whoosh, selection "ding" |
| 6 | 20-24 s | "Its target: a region called the lateral entorhinal cortex." | X-ray cross-section of the brain; a small region lights up, and a targeting reticle locks on. | Lock-on beeps |
| 7 | 24-29 s | "A vet opened the skull. Then the AI steered the needle in, and slowly injected 250 nanoliters." | The needle slides in. Cyan therapy spreads through the tissue. Counter: **0 → 250 nL**. The red storm calms. | Soft hydraulic slide, liquid pulse, ticks |
| 8 | 29-32 s | "Here's the twist: two other AIs got the same task. Each picked a different treatment." | Three brains side by side, each lit in a different region, labelled **Claude · GPT · Grok**. | Three distinct chimes |
| 9 | 32-35 s | "The mouse recovered. Did it work? Nobody knows yet. No peer-reviewed results so far." | The mouse breathing calmly, slow pull-back. Text: **"Results: pending"**. | Calm pad, heartbeat returns |
| 10 | 35-37 s | **"Would you let an AI choose your treatment?"** | End card: @the.ai.gal + source. | Chime |

## Why this works (the formula for every reel)
1. **Hook = what happened + tension**, in under 3 seconds ("...and no human chose the treatment").
2. **Setup with stakes:** who, what they had, the one goal.
3. **Conflict / twist #1:** something went wrong or surprised us (the refusal).
4. **The key moment:** the decision or action, shown big, with the number as a visual.
5. **Twist #2:** a fact that reframes it (each AI chose differently).
6. **Reality check:** the honest caveat, said out loud, which builds trust.
7. **A question to the viewer:** drives comments, then the end card.

## What we need to build
| Asset | How |
|---|---|
| Mouse brain (smooth, with olfactory bulbs, cerebellum) | Procedural (extend `holo_brain` shapes); more accurate than the human brain used in v1 |
| Mouse under sterile drape | Free CC0/royalty-free mouse model (BlenderKit / Sketchfab CC-BY), mostly covered by the drape |
| Surgical rig + lab set | Procedural metal parts + dark lab with bokeh (already have the probe) |
| Seizure "storm", therapy spread, X-ray cut | Shader/emission effects (have the therapy glow; add electric crackle + cross-section) |
| 19 therapy cards, DECLINED HUD, 3-brain comparison | Overlay pass (have it) |
| Narration + word-by-word captions | Voice (your choice) -> word timestamps -> captions, cuts and SFX auto-timed |

## Sources
Exin Therapeutics, as reported by: hyper.ai, Medium/ModelDex, Digital Citizen, DEV Community (Fathom),
Martin Cid, Startup Fortune, Superpower Daily, Atlabyte (Nov 2026). Model names: Opus 5.5 (declined to
guide the needle, per most reports), agent built on Claude Sonnet 5; comparison runs with GPT-6.1 Sol
and Grok 4.7 (reported).
