# Story v2: "The AI that chose a brain treatment"

~33 s, narrated by @the.ai.gal. Style rules: see `STYLE_GUIDE.md`.
Accuracy: everything is as reported by Exin Therapeutics (company claims, not peer-reviewed).

## Recording script (30 s cut; read in one take, ~1 s pause between lines)
1. This tiny mouse just had brain surgery.
2. And no human chose the treatment.
3. An AI got nineteen gene therapies,
4. and one goal: stop the seizures.
5. Which one would you pick? This one, right?
6. The AI picked this one: a brain-calming therapy.
7. Twist: the first Claude model refused to steer the needle.
8. So another Claude model steered it in,
9. injecting a droplet smaller than a pinhead.
10. Two other AIs each picked a different treatment.
11. Did it work? Nobody knows yet.
12. Would you let an AI choose your treatment?

## Shot list
| Line | Look | Shot | 3D annotation / effect | SFX |
|------|------|------|-------------------------|-----|
| 1 | Lab, warm soft light | Gloved hand settles a sleeping mouse under a blue surgical drape; robotic needle rig above | - | soft lab hum, gentle rustle |
| 2 | Lab, dramatic | Snap push-in to the needle tip, glint, hard cut to black on "treatment" | - | needle whine, cut to silence |
| 3 | **Bright cyan studio** | 19 small glowing vials pop into a row one by one | vial labels blur past | rapid pop cascade |
| 4 | Dark, inside the brain | Fly into the mouse brain: red electrical storm crackling across it | red pulses | electric crackle |
| 5 | Bright studio | The 19 vials; **giant red 3D question mark** drops in | ? bounce | thud + boing |
| 6 | Bright studio | A realistic hand points at the biggest, brightest vial | - | tap |
| 7 | Bright studio | Hand pulls away; a small plain vial lights up cyan instead; label **"GABA BOOST"** | cyan glow ring | selection ding |
| 8 | Dark | Quick zoom on the needle above the brain | - | tension riser |
| 9 | Dark, red | Needle descends... freezes. A red 3D **X** slams in: "DECLINED" | red X | hard error buzz |
| 10 | Lab | Robot rig re-arms, status light turns from red to green | - | servo whir, beep |
| 11 | X-ray brain | Cross-section of the brain; red dimension arrow shows the needle path to the target (lateral entorhinal cortex), needle slides in | red path arrow, target reticle | hydraulic slide |
| 12 | **Bright studio** | A hand holds a sewing pin; a tiny cyan droplet sits next to the pinhead, smaller than it. Counter: **0 → 250 nL** | dimension line around the droplet | liquid drip, ticks |
| 13 | Bright studio | Three vials on three pedestals labelled **Claude · GPT · Grok** | - | three distinct chimes |
| 14 | Bright studio | Three small brains above them, each lit in a different region | red arrows to each region | whoosh x3 |
| 15 | Lab, calm | Mouse breathing calmly, slow pull-back; text **"Results: pending"** | - | soft pad, heartbeat |
| 16 | End card | @the.ai.gal + source | - | chime |

Droplet maths for line 12: 250 nL = 0.25 mm³ = a sphere ~0.78 mm wide; a sewing pinhead is ~1-2 mm.

## Assets needed
- Realistic hands (pointing, holding a pin, gloved): free CC0 / BlenderKit hand models, posed with Rigify
- Mouse (sleeping, mostly under a drape): free CC0/CC-BY mouse model
- Mouse brain (smooth, olfactory bulbs, cerebellum): procedural
- Vials, pin, robot rig, lab, studio backdrop: procedural
- 3D annotation kit (red arrow, dimension line + counter, question mark, X): procedural, reusable

## Sources
Exin Therapeutics, as reported by hyper.ai, Medium/ModelDex, Digital Citizen, DEV Community (Fathom),
Martin Cid, Startup Fortune, Superpower Daily, Atlabyte (Nov 2026). First model: Opus 5.5 (planned,
then declined to guide the needle, per most reports); agent built on Claude Sonnet 5; comparison runs
with GPT-6.1 Sol and Grok 4.7 (reported).
