---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# `legibilityCheck` times one text per layer, so a card carried across a cut fails `LEG-SHORT`

Draft for the scene-render issue tracker. Back to the [library README](../README.md).

## Summary

`LEG-SHORT` measures how long each text layer is drawn, not how long a text is on screen. When the same text continues
in another layer from one frame to the next, each layer is timed alone. A card that stays up for two seconds is reported
as 0.375 s, and `encode --strict` exits 1.

Two scenes that decode to identical frames get different verdicts, so the finding depends on how the document is
structured and not on anything a viewer sees.

## Environment

- Reproduced on `scene-render 0.8.0`, x86_64 Linux.
- Not run on 0.9.0. `crates/sr-deliver/src/legibility.rs` is unchanged from `v0.8.0` to `af179e4` (`v0.9.0`), so the code
  at fault is the same there.

## Reproduction

Beside each scene, put any TrueType font as `font.ttf`. The report below used DejaVu Sans Bold.

`one-layer.scene.xml`, the control:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<scene version="1.1">
  <project width="1080" height="1920" fps="24" duration="2" background="#ffffff"/>
  <metadata title="one layer">
    <accessibility description="A card." contrastCheck="warn" legibilityCheck="warn"/>
  </metadata>
  <assets>
    <font id="f" src="font.ttf" family="DejaVu Sans" weight="700"/>
    <text id="card" text="SAME CARD" width="700" height="200" size="76" color="#000000" align="center" fontAsset="f"/>
  </assets>
  <composition>
    <group id="shot" start="0" end="2"><layer id="card-layer" x="190" y="800" asset="card"/></group>
  </composition>
</scene>
```

`two-layers.scene.xml`, the same card cut at 0.35 s:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<scene version="1.1">
  <project width="1080" height="1920" fps="24" duration="2" background="#ffffff"/>
  <metadata title="two layers">
    <accessibility description="A card." contrastCheck="warn" legibilityCheck="warn"/>
  </metadata>
  <assets>
    <font id="f" src="font.ttf" family="DejaVu Sans" weight="700"/>
    <text id="card-a" text="SAME CARD" width="700" height="200" size="76" color="#000000" align="center" fontAsset="f"/>
    <text id="card-b" text="SAME CARD" width="700" height="200" size="76" color="#000000" align="center" fontAsset="f"/>
  </assets>
  <composition>
    <group id="shot-a" start="0" end="0.35"><layer id="card-a-layer" x="190" y="800" asset="card-a"/></group>
    <group id="shot-b" start="0.35" end="2"><layer id="card-b-layer" x="190" y="800" asset="card-b"/></group>
  </composition>
</scene>
```

```console
$ scene-render encode one-layer.scene.xml -o one-layer.mp4 --strict --report one-layer.json
$ echo $?
0
$ scene-render encode two-layers.scene.xml -o two-layers.mp4 --strict --report two-layers.json
error: --strict: two-layers.mp4: 1 finding(s) at warning or error severity (the render report's findings; information is not counted)
  accessibility: legibilityCheck: text "card-a-layer": drawn for 0.375 s (minimum 0.8333 s)
$ echo $?
1
```

The finding in `two-layers.json`:

```json
{"code": "LEG-SHORT", "severity": "warning", "path": "/scene/composition/group[1]/layer", "node": "card-a-layer",
 "time": [0.0, 0.375], "measured": 0.375, "limit": 0.8333, "unit": "s",
 "message": "text \"card-a-layer\": drawn for 0.375 s (minimum 0.8333 s)"}
```

## Expected and actual

The text is on screen for all 48 frames of both masters. The 48 frames decoded from each are identical by `framemd5`.
Given the same `title`, the two `.mp4` files are byte-identical, since only the metadata differs.

| | Control | Cut at 0.35 s |
|---|---|---|
| Frames with the text | 48 of 48 | 48 of 48 |
| Time on screen | 2.000 s | 2.000 s |
| Reported | no finding, exit 0 | `LEG-SHORT` 0.375 s, exit 1 |

Expected: no finding for either scene, since the text is on screen for 2 s against a minimum of 0.8333 s.

## Worked example from a real reel

A Collage reel carries a card reading "YES, MY FAMILY DESERVES LESS" through six shots. Each shot is its own group and
draws the text with its own layer. The card flips to face the viewer around 7.6 s, in the group from 7.55 to 7.9 s,
where the text is `c1849-layer`. `c2133-layer` takes over in the group from 7.9 to 10.058 s. The engine reports:

```json
{"code": "LEG-SHORT", "severity": "warning", "node": "c1849-layer", "time": [7.583333333333333, 7.916666666666667],
 "measured": 0.3333333333333333, "limit": 0.8333, "unit": "s",
 "message": "text \"c1849-layer\": drawn for 0.333 s (minimum 0.8333 s)"}
```

Measured on the encoded master by normalized correlation against the card at frame 186, in the card's box:

| Frame | 183 | 184 | 189 | 190 | 241 | 242 |
|---|---|---|---|---|---|---|
| Correlation | 0.316 | 0.998 | 0.998 | 0.998 | 0.995 | -0.002 |

The cut falls between frames 189 and 190, and the card does not move or change there. It is readable from frame 184 to
frame 241, 58 frames at 24 fps, 2.417 s, with no frame in that run under 0.9947. Frames 182 and 183 fall in the flip's
last keyframes and are not counted.

## Root cause

The check keys what it has seen on the node. In `crates/sr-deliver/src/legibility.rs` at `v0.9.0`:

- Line 211 declares `seen: BTreeMap<String, Seen>`.
- Line 226 takes `seen.entry(n.id.to_string())`, so each layer id has its own count, whatever it draws.
- Line 260 computes `let shown = v.frames as f64 / fps`, the frames of that one node.
- Line 275 tests `if shown < s.min_display_time` and raises `LEG-SHORT`.

Nothing joins two entries, so continuity between layers cannot be seen. The reproduction confirms this: the two scenes
differ only in how many layers carry the text, and the verdict follows that count.

The same `shown` divides the characters for `LEG-SPEED` at line 263, so a text split across layers should also read as
faster than it is. That follows from the source and has not been reproduced.

## Suggested fix

Measure a run of a text rather than a node: after the per-frame pass, join entries whose runs touch at a frame boundary
when they draw the same characters in the same place on the frame, and test the joined run. `first`, `last` and the
frame count are already kept per node. The drawn box would have to be kept as well.

"The same place" needs a tolerance the project should choose, since a card can move on a cut and still be the same card
to a reader. Keying on the text alone would be wrong: it would join two separate appearances of one word in different
places.

Regression tests to add:

- The two scenes above give the same result, no finding.
- A card genuinely up for 0.375 s still fails.
- The same text shown twice, apart in time, is two runs and does not add up.
- The same text in two places on one frame is two runs.

## Not covered

`LEG-CONTRAST` is a separate measurement and is not part of this report.
