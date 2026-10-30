---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0048: Caption looks are approved per style, and the frames are measured by the letters' counters

- Status: accepted and implemented for the gate, 2026-10-30 (`srstudio.caption_gate`, `episodes/posts/_grandfathered.py`,
  `Release.style`, `CaptionLook.published`, `episodes/instagram_posts.py`, `tests/test_caption_gate.py`); corrects
  [ADR 0031](0031-shared-look-and-caption-primitives.md). The new Gloss look (`gloss_reel.LOOK_SPLIT`,
  `CaptionLook.outline`) is proposed until the operator approves it from its proof
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

The operator read *Gloss 09: Saying no is a ping* and found its black captions very hard to read. The look was
deliberate, and the reason for it was wrong.

**How it happened.** From G8 the strict encode refused the Gloss house look (white letters, dark outline, gold sung
word) with `LEG-CONTRAST` at 1.00:1. ADR 0012 and ADR 0031 already said why that number means nothing for a stroked
caption: `contrast_of` in `sr-gpu` selects every pixel the caption changed by at least half the largest change,
whichever way, and averages them. Over a mid-tone floor the white letters brighten and the dark outline darkens, so
the mean lands on the floor and the ratio on 1.00:1. ADR 0031 wrote this down and left it "to the engine". G8 then
took the number as a verdict, and `gloss_reel.LOOK_INK` was built to raise it: solid dark letters with a 2 px stroke
in their own colour, which keeps the descenders inside the safe area. The strict encode passed. G8 and G9 shipped.

**Why the black look reads badly.** The stroke fattens a rounded bold face and shuts the counters of a, e and s, so
words turn to blobs. There is no halo, so the letters sit straight on the checker floor. `gloss_sets._caption_shade`
still darkens that floor, because it was built for white letters, and now works against dark ones.

**Why a contrast ratio cannot see this.** The ink against the ring of pixels around it measures a median 7.01:1 on
G9 and 6.25:1 on G8. Both pass 4.5:1 and are still hard to read. The defect is the shape of the letters, not their
tone against the floor.

## Decision

1. **A stroke in the letters' own colour is refused.** `native.CaptionLook` raises on one (on the sung word's colour
   too), and so does a look's record. `CaptionLook.published` exempts `LOOK_INK` alone, so G8 and G9 rebuild byte for
   byte; it draws nothing. A burned track stroked so in a scene is reported by name.
2. **Every style's caption look is a typed record.** `caption_gate.LOOKS` holds `ApprovedLook`s: style, colours,
   outline, the zone of the frame the captions start in, the proof, and an `Approval`. A look without an approval is
   proposed and a reel wearing it does not pass, so a proposal cannot ship by being merged.
3. **The look is read from the scene.** `Release.style` names the style; the gate reads what the scene actually
   burns (the track's text style, or the text layers painted so inside the zone) and compares it. A new look fails
   the gate until the operator approves it. Scene text gives the caption band too, so the band follows a reel's
   layout. Cel letters its captions as traced shapes, so its record is `drawn` and its zone is the band.
4. **The rendered frames are measured.** `measure_frames` takes one frame a second inside the band and finds the
   letters by the look's colours, dropping anything that reaches the band's edge (a floor tile, a shirt). It finds
   their enclosed counters, keeps those at least 3:1 from the letter's tone and no larger than a counter can be (a
   pill's interior is not one), and pools the pixels over the reel. The **counter ratio** is counter pixels over
   letter pixels; the minimum is `MIN_COUNTERS` = 0.025, in at least `MIN_FRAMES` = 3 frames with letters, so a reel
   where nothing was measured cannot pass.
5. **Published reels are grandfathered by a closed list.** `episodes/posts/_grandfathered.py` holds the 109 slugs
   published when the gate arrived; its digest is pinned in a test, and a new reel never joins it. Their pictures
   are frozen, so the gate does not judge them and the publish gate stays clean for them, the two black reels
   included.
6. **The path.** `instagram_posts.py deliver` refuses a video the gate refuses before it writes anything; `check`
   reports it as drift. The engine's strict contrast check is untouched and stays strict.

### The numbers

Measured on the 101 masters whose scenes are built here, plus the Cel reel in its zone. Only the two black reels
fall under the minimum:

| Reels | Counter ratio |
| --- | --- |
| G9 *gloss-notifications*, black | 0.0164 |
| G8 *gloss-fewer-meetings*, black | 0.0146 |
| Gloss G1–G7, white and outlined (7) | 0.0598 – 0.0754 |
| Saga (18) | 0.1007 – 0.1392 |
| Toon (20) | 0.1306 – 0.2961 |
| Cutout (12) | 0.0462 – 0.0847 |
| Stick (8) | 0.0701 – 0.1260 |
| Soft (8) | 0.0819 – 0.1099 |
| Ink (7) | 0.2608 – 0.3324 |
| Collage (19) | 0.0279 – 0.0414 |
| Cel (1) | 0.0637 |

The minimum sits between the worst passing reel and the black ones. Collage is the closest: its heavy lettering has
small counters, and it reads on its pale pill, so 0.025 is the bound that passes it and fails G8 and G9.

## The new Gloss look

The look the operator wants back is the house one: white letters, a dark outline, a gold sung word. The strict encode
has to pass it honestly, so the check must compare white with ink, which is the route ADR 0012 took for Stick: the
outline gets its own layer.

`native.CaptionLook(outline="layer")` keeps the white track, without its stroke, and draws the outline as text layers
under it, one to a cue, timed to the cue. Each layer is set in the same face, size, wrap and box as the track, so the
ink sits exactly behind the letters. The layers sit in a group marked `isolate`, for a reason the engine sets:

| Route tried on G9 | Strict contrast | Why |
| --- | --- | --- |
| Stroked track (the house look) | 1.00:1, refused | fill and outline averaged |
| Two burned tracks, ink under white | 1.00:1, refused | the deferred probe hides every caption track at once, so it still sees both, averaged |
| Ink text layers at the root, under the track | 1.00:1 on the layer | the layer's inline probe reads its "after" from the final frame, which holds the burned white |
| Ink text layers in an isolated group | passes, no findings | the layer is measured with and without its node: ink against the floor |

The isolated group is not a way round the check. Both pairs are measured, white against ink and ink against the floor,
and either can fail. A cover variant hides the group with the track, and `Episode.hide_on_cover` writes that override.
With white letters back, `gloss_sets._caption_shade` works for them again, as it was built to.

**Proof on all nine Gloss sets.** Each reel was rebuilt in the look in scratch and encoded with `--strict`. No finding
on any of the nine names the captions or the outline. Six exit 0. `gloss-joy-points`, `gloss-terms` and
`gloss-wellness` exit 1 on other text, their notice cards, up for under 0.83 s (and one card on joy-points
at 2.20:1 to 2.50:1): that text is in those published sets and nothing here changed it.

| Reel | Black | Split outline |
| --- | --- | --- |
| G9 *gloss-notifications* | 0.0164 | 0.0606 |
| G8 *gloss-fewer-meetings* | 0.0146 | 0.0665 |
| G1–G7, against their published 0.0598 – 0.0754 | | 0.0592 – 0.0744 |

The proof is `generated/character-proofs/gloss-captions/index.html`: the same lines, black and white, on the palest
and darkest tiles of both reels. The record in `caption_gate.LOOKS` carries no `Approval`, so until the operator
gives one, a new reel in this look is refused by name, and the proof is what the operator judges it on.

## Rejected alternatives

- **A second burned track for the outline.** Rejected: it still reads 1.00:1, as the table shows, and the engine hides
  both tracks together.
- **A caption box or a fill behind the letters.** Rejected: the engine has none, and a panel would change the house
  look the operator asked for.
- **Karaoke drawn by text layers, with no track at all.** Rejected: it gives up the native track, its sidecar and its
  timing for no gain over the outline layer.
- **Keeping the black look for new reels.** Rejected for the reasons above: it answers the measurement, not the
  reader, and the operator could not read it.
- **A contrast ratio on the frames.** Rejected: 7.01:1 and 6.25:1 on the two reels that fail. A control that passes
  the defect is not a control.
- **Fill against an immediate halo.** Rejected as the measure: it fails Toon, Collage and Ink, whose letters need no
  halo because they sit on a plain panel. Open counters hold for every style.
- **A stem-thickness measure.** Rejected: it would have to know each typeface. The counter ratio needs only colours.
- **Lowering or disabling the engine's check, or marking the look as a false positive.** Rejected: it stays strict.
- **Grandfathering by the delivery manifest.** Rejected: the manifest is generated and not in the repository, and a
  reel delivered by mistake would grandfather itself. A closed list cannot grow by accident.
- **Declaring the look on the release.** Rejected: a declaration can differ from the picture. The scene is the look.

## Consequences

- A new reel's release declares `style=` and its scene wears an approved look, or it cannot be delivered.
- Gloss has a proposed look and no approved one: until the operator approves `white-split-outline`, no new Gloss reel
  passes. Approving it is one `Approval` on its record.
- A split outline adds one text asset and one layer to a cue, and a look with `outline="layer"` needs the canvas it
  draws on, so `native_captions` passes it.
- `instagram_posts.py check` decodes a second of video per second of each reel not grandfathered, a few seconds each.
- A new style records its look, with the operator's approval, before its first reel ships.
- A releases branch that adds a reel after this list was closed must declare its style.
