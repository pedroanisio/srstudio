---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0026: Collage, paper cut-out people and one glossy porcelain toilet on painted sets

- Status: accepted; implemented 2026-10-29 (`srstudio.collage`, `srstudio.collage_sets`, the shared sketch build
  now in `srstudio.collage_sketch`, the `COLLAGE` style and the `PAPER` palette; `tests/test_collage.py`,
  `tests/test_collage_episodes.py`; twelve sketches in `episodes/`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md); builds on [ADR 0001](0001-signature.md) (the signature marks),
  [ADR 0010](0010-toon-style.md) (the Toon caption pill and pose runs), [ADR 0015](0015-toon-sketches.md) (a sketch
  as data) and [ADR 0020](0020-toon-lip-synced-cast.md) (visemes and blinks); the cast and world are carried on in
  [ADR 0036](0036-collage-series-bible.md)

## Context

The Collage style shipped on 2026-10-29 with its sets, props and twelve voiced sketches (commit `af3de57`), and its
style value followed the same morning (`3d63223`). From the first commit its modules cite this ADR, which had not
been written. This record states the decision as the code, the commit history and the README define it. The
reasons below are the ones those sources give, each cited where it is given.

## Decision

- **The comedy.** Every Collage sketch is about grown-ups losing to brainrot: adults who give up their dignity to
  *BOWLHEADS*, a kids' show whose star is Flush, a singing porcelain toilet with a paper head (README, *Collage
  style*; `styles.COLLAGE.summary`).
- **Mixed media, and why.** The people are flat construction paper with hand-cut edges, an ink outline and a drop
  shadow that lifts them off the set; the sets are painted in soft gradients over the whole frame; Flush is the one
  glossy "CGI" object, porcelain in gradients. The source of the comedy is the clash between them: "The joke is the
  clash" (`collage.py`, module docstring).
- **Originality.** *BOWLHEADS* and Flush are invented: "nothing here copies a real show's characters, songs or
  drawings" (`collage.py`, module docstring).
- **A style value, `COLLAGE`.** Portrait 1080×1920 at 24 fps on the episode's clock, the `PAPER` palette (ink
  `#1d1a22`, white `#fffaf0`, shade `#e94f37`, background `#f3e3c3`), Luckiest Guy 400 (Google Fonts, Apache-2.0,
  pinned), `script.json` dialogue ("timed caption cues, as the Toon sketches write them"), parts `collage`,
  `collage_photo` and `collage_sets`, and `c`-numbered ids (`styles.py`).
- **Silent figures, voiced lines.** The style is `silent`: "like the Toon: the expression is pose data, the voices
  are narration over the captions" (`styles.py`). Each character is lip-synced on `toon_cast.VISEMES` and blinks at
  its own pace (`collage.py`), and each speaks with one ElevenLabs premade voice, the same in every episode
  (`collage_sketch.SPEAKERS`).
- **Characters as data.** A character is a `collage.Look` (skin, hair, top, build, accents, blink), drawn waist-up at
  the bottom centre inside `collage.FIGURE_BOX`, below the Toon caption pill. The style has its own pose vocabulary
  (`EYES`, `MOUTHS`, `ARMS`), and `collage.CAST` hands it to `srstudio.sketch` so a sketch is checked against it.
  `figure_shapes` returns the drawing as data "so a test can measure it" (`collage.py`). The cast is ten looks.
- **Sets and props.** Eight painted rooms (`collage_sets.SETS`) and paper props: a sign, a chart, and a TV playing
  *BOWLHEADS* with a tiny Flush in it (`collage_sets.py`).
- **The signature on a shelf.** The cactus and the code (ADR 0001) sit on a shelf or sill above `FIGURE_BOX` and
  below the caption pill, "so neither the character nor a caption covers them" (`collage_sets.py`). A test records
  every placed card, chart and screen and asserts that each one clears `collage_sets.signature_box` (funny-reels
  skill, the signature rules).
- **The build.** One shot per appearance on its character's set, crash zooms on `zoom` beats, the sagging two-note
  sting and Kai's beep (`collage_sketch.py`). The recording is one ElevenLabs request per line, each heard back by
  speech-to-text, voices confirmed by name and nothing retried, and the build refuses a recording that does not
  agree with `narration.json` (`collage_sketch.py`; README, *Collage style*).

## Rejected alternatives

None are recorded. The commit that introduced the style (`af3de57`), the style's modules and the README state what
was built and, in the places cited above, why; none of them names an alternative that was considered.

## Consequences

- A Collage episode is `episodes/<name>_data.py` (lines, timed beats and the `Staging`), `episodes/<name>.py` (the
  build) and `episodes/<name>_audio.py` (the recording); its release is `episodes/posts/<name>.py` (README).
- The sketch build moved from `episodes/_collage_sketch.py` into the library as `srstudio.collage_sketch`
  (`36451f3`).
- Group shots (`srstudio.collage_group`), the family photo's props (`srstudio.collage_photo`) and the cast cards
  are decided in [ADR 0036](0036-collage-series-bible.md), which builds on this style.
