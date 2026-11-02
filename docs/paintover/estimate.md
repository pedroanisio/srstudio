---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
date: 2026-11-01
data: estimate.data.json
---

# 3D paintover pilot: cost estimate

Sizes are XS to XL. A token figure counts input, cache read and cache write, as `govern usage` does. "Measured" numbers come from a named source. Every other token figure is an estimate.

## Conclusion

Once a set is built and approved, a reel on it costs about the same as a Toon reel on an existing 2D set, and possibly slightly more. The estimate is 12M to 16M build tokens, against a measured 12.6M to 12.9M. It is cheaper only against a reel that would otherwise need a new 2D set (18.3M measured, one example).

The upfront cost is the real price. The scope as asked is an estimated 88M to 171M tokens, size XL, equal to 4 to 8 of today's reels at 20.3M each all-in. That is roughly USD 56 to 152 at list rates. Without the car it is 61M to 116M.

Render is not where the cost sits. A final encode ran 6 to 51 s, and plates add a small one-off render and none on repeat. ElevenLabs does not change. The cost sits in model tokens: first the Toon look and the bridge into reels, then the sets.

So the pilot will not repay itself in tokens. At the 5.4M difference in that one example, repaying it would take 16 to 32 reels that each needed a new 2D set, and Toon already has 32 locations. The case for it is continuity, grounding and framing, which only EXP-017 can measure.

**Recommendation:** run the proof below first (size S). If it passes, build the flat with the medium two-shot and close-up, then the café. Hold the car and the over-the-shoulder preset until the first results are in. They cost the most and add the least.

## Cost per set

| Set | Blockout | Final-style path | First reel, build tokens | Repeat reel, build tokens | Today, build tokens |
|---|---|---|---|---|---|
| Shared, paid once | none | L (30M to 55M) | included below | none | none |
| Flat: sofa | S (4M to 8M) | S (3M to 6M) | M (18M to 30M) | M (12M to 16M) | 12.6M, existing set (`texts-back`) |
| Flat: kitchen | S (5M to 10M) | S (3M to 6M) | M (14M to 20M) | M (12M to 16M) | 12.9M, existing set (`home-anyway`) |
| Flat: bedroom | S (4M to 8M) | S (3M to 6M) | M (14M to 20M) | M (12M to 16M) | 18.3M, new set (`nine-alarms`) |
| Café | S (5M to 9M) | S (4M to 8M) | M (14M to 22M) | M (12M to 16M) | not in the batch; `toon-restaurant` and `toon-counter` exist |
| Car | M (15M to 30M) | M (12M to 25M) | M (20M to 30M) | M (14M to 20M) | not in the batch; `toon-car-inside` exists |

The set figures in the first four columns are estimates, and the Today column is measured. The shared cost is a Toon look (M, 15M to 30M) and the bridge from a location into a reel (M, 15M to 25M). The sofa's first reel carries the first use of that bridge. The gap between `nine-alarms` and `home-anyway` is one pair of reels, confounded by speaker count (3 against 2), and `home-anyway` also added one prop. For a reel's full cost, add the measured 7.1M per reel for writing, review, library work and orchestration to any build figure.

The size ladder is anchored to measured work. XS is under 3M (Pedro rebase, 2.9M). S is 3M to 10M (`extra-hour`, 8.8M). M is 10M to 30M (Bento port, 18.0M; `toon-rooms`, 16.1M; car-vibe kit, 23.1M). L is 30M to 80M (wire car and jet, 31.3M; the srlocations SDK, 79.2M). XL is over 80M (host pilot, 108.5M).

Assumptions:
- Three presets per room, so nine for the flat. If the three are for the whole flat, take the low end of the flat rows.
- A café, not an office: the batch mix (1793494182.421979) rules office life out.
- Toon only, since Mae and Bruno are Toon. Each further style needs its own look, size S to M.

## Today's reels, measured

| Reel | Style | Video (s) | Final encode (s) | Master runs | Build tokens | Build USD | TTS characters |
|---|---|---:|---:|---:|---:|---:|---:|
| only-your-aunt | Cutout | 25.6 | 15.3 | 7 | 16.9M | 14.38 | 281 |
| nine-alarms | Toon | 27.8 | 27.4 | 8 | 18.3M | 15.95 | 278 |
| whats-new | Soft | 26.7 | 7.1 | 9 | 18.3M | 16.01 | 337 |
| practice-round | Stick | 29.0 | 44.4 | 3 | 20.0M | 15.96 | 300 |
| extra-hour | Stick | 14.5 | 30.5 | 5 | 8.8M | 7.38 | 167 |
| home-anyway | Toon | 27.4 | 12.7 | 4 | 12.9M | 11.54 | 380 |
| thought-of-you | Collage | 24.0 | 51.4 | 5 | 18.4M | 16.37 | 247 |
| texts-back | Toon | 24.5 | 18.9 | 2 | 12.6M | 10.77 | 311 |
| cant-afford-to-save | Stick | 14.4 | 18.1 | see below | 8.1M, divided | 6.74, divided | 197 |
| it-autoplayed | Toon | 25.3 | 11.1 | see below | 8.1M, divided | 6.74, divided | 276 |
| nobody-died | Cutout | 22.1 | 7.0 | see below | 8.1M, divided | 6.74, divided | 280 |
| wrong-door | Soft | 23.2 | 6.0 | see below | 8.1M, divided | 6.74, divided | 231 |

| Figure | Value | Source |
|---|---|---|
| Build tokens, first eight reels | Measured per reel: each had its own agent | Agent transcripts, `message.usage`, deduplicated by message id |
| Build tokens, last four reels | 32.5M divided by 4 | One agent built all four (`agent-a688d88986a0b640f`) |
| All-in per reel | 20.3M, USD 18.03 | 13.2M build, 7.1M the rest; division in `estimate.data.json` |
| Tokens that are cache reads | 94.6% | Same transcripts |
| USD basis | List-rate estimate | `super-tools/tools/govern/prices.json`; on a subscription this is plan use, not spending |
| Final encode | 6.04 to 51.43 s, median 16.68 s, 11.3 to 138.3 frames/s, RTX 3050 | `generated/episodes/<slug>/encode.log`, last run only |
| Master runs | Runs over 10 s: 43 on the first eight reels, 21 on the last four; 390 s per reel, build and queue included | Tool call timestamps in the same transcripts |
| ElevenLabs | 150 TTS requests, 3,285 characters; 150 speech-to-text requests | `generated/episodes/<slug>/assets/elevenlabs/*.json` |
| Plate-built reels | 27.55 to 28.09 s with 107 or 108 image layers | `generated/episodes/unwritten-rules-*/encode.log` |
| Path-traced 1080x1920 frame | 2.74 s, 634 MB | ADR 0068 |

`govern usage` holds no token figures for these lanes: `okay-e` has no segments and `okay-oct31` shows zero calls.

Plates are a small, one-off render. The flat needs about 36 stills: nine presets, back and front layers, two lighting states. Stills on file took 1 to 8 s at 1280x720, so the estimate is at most 650 s once, about two reels' master runs. A warm rebuild ran the engine zero times (ADR 0091). Encode should stay inside today's range, as the plate-built reels above did with far more image layers.

## What exists, and what the characters allow

**srlocations gives the blockout nearly free.** It has rooms in metres, marks, shots, wireframe and shaded review, mannequins with collision checks, café and car examples, and srstudio's cast standing on marks with furniture hiding them correctly.

**It does not give a reel:**
- Shots are stills, and cast figures are single-pose pictures, not animated rigs.
- No portrait render is on file; all are landscape.
- It has no kitchen or bed prefabs, and its car interior is a left-hand-drive luxury cabin.
- The engine has no custom surface shaders, so "shaders" here means stacked passes and 2D effects.

**srstudio holds the other half:** `proxy.layers` cuts back and front layers with a rig between them, and `plates` caches them. Neither reads a location yet, which is why the bridge is an M.

**Mae and Bruno constrain the sets:**
- **Contact:** they are front-facing busts with no legs, so they cannot stand on a floor. Every preset needs a near edge that hides their base, such as a table, ledge or sofa back. A contact shadow is painted, not cast.
- **Scale:** their cartoon heights are not metres, so each preset sets scale by hand.
- **Depth:** a figure counts as one distance, to within 15 cm. A hand on a set prop stays a 2D overlap placed by projection.
- **Occlusion:** back plate, rig, front plate. This is the part that already works.
- **Camera:** the medium two-shot and close-up fit, and `texts-back` already holds exactly those. The over-the-shoulder does not, because the rigs have no back view.

## After the first set

Reusable: the Toon look, the bridge, the gates, the blockout approval step, the preset pattern, and any furniture and props. Not reusable: looks for other styles, per-preset scale and marks, any back views, and each preset's foreground layer.

## Hardest unknown per set

| Set | Unknown | Would a small probe settle it? |
|---|---|---|
| Flat | Does a set drawn through passes sit beside hand-inked approved rigs? | Yes, the proof below |
| Café | A hand on a cup at a fixed preset | Mostly settled by the flat's proof |
| Car | Road moving behind glass, with an SDK that makes stills | Yes, one still with clear windows over `toon_world.road` (S) |
| Car | Whether 3D adds anything: the two drawable views already exist in `toon-car-inside` | No probe needed, this is a decision |

## Risks that could change the answer

1. **The look.** Current Cel and Ink output has thin uneven lines and plain boxes. Approved Toon has heavy clean ink, bevels and tile. If passes cannot reach it, each set needs painted detail, adding an estimated 30M to 60M across the scope.
2. **Over-the-shoulder.** It needs a new back view per character, size S (3M to 8M) each, with approval. This is not in the totals. A soft foreground shoulder shape is a cheaper substitute.
3. **Too few presets.** `home-anyway` used six framings. `nine-alarms` and `texts-back` used three. Each extra preset is a small cost, and it adds up on reels like `home-anyway`.
4. **A narrow defect benefit.** The four finished reviews of these 12 reels list 20 blockers. By my classification, 1 is set grounding, 2 are props lost between shots and 5 are signature marks out of frame. Those 8 are the most a set can help. The other 12 are hands, captions, encoding, acting, editing and approval, and they stay.
5. **No 3D-set reel exists.** Every set figure rests on comparable work, not on this work. The proof gives the first real number.
6. **Two toolchains.** The SDK has no remote, and it runs engine 0.9.0 here while reels use 0.8.0. The bridge has to pin this.
7. **Camera moves.** Presets are held. A push on a plate is a 2D scale with no parallax, and real camera moves are unproven.

## Cheapest proof

Re-stage 6 to 8 s of `it-autoplayed`, where Mae and Bruno already sit on a sofa in `toon-lounge`, using its existing audio. Render a back plate and a sofa-back front plate from srlocations at 1080x1920, keep the rigs live, and show it beside the approved shot as an animated clip. It is a study, never a release, and needs no paid audio.

Size S, an estimated 3M to 8M tokens. It settles the biggest unknown, the look, and tests the bridge. It also gives the first measured token figure for this work. If the look fails, the pilot stops at that cost.

## Not measured

| Cost | Why not | What would measure it |
|---|---|---|
| ElevenLabs money | Characters and requests only; plan rate not read | The provider's usage history |
| Tokens by stage within a reel | Transcripts total per agent | Stage marks in `govern work` |
| Build time alone | `build.log` has no timing, and a master run includes the queue | A timer around the build in `master.sh` |
| Encode figures for earlier runs | `encode.log` is overwritten; only count and wall time survive | Keeping a log per run |
| Orchestrator share | Calls naming the batch were taken as its share (49.1M, divided by 16) | Lane segments in `govern` |
| Any 1080x1920 plate render, any 3D-set reel | None exists | The proof |
| Codex-built composition and plate work | Not in these transcripts | Codex's own usage records |
| Defects on 3D sets, shares, % watched | No such reel | EXP-017 |
