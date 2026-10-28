# ADR 0002: Naming the styles, and making a style a value

- Status: accepted and implemented, 2026-10-28 (`srstudio.styles`, `EpisodeSpec.style`, `srstudio styles`,
  `tests/test_styles.py`)
- Deciders: the operator (pedroanisio), proposals drafted by Claude Fable 5.1 in Claude Code
- Back to the [library README](../../README.md)

## Context

The library drew two looks without naming either. The README called them "the interview family" and "the hand-drawn
family"; the code spread each one over a palette constant (`OFFICE`, `CAFE`, `MONO`), a mouth model
(`OFFICE_MOUTH`, `CAFE_MOUTH`, `INK_MOUTH`), the defaults of `EpisodeSpec` (which were the portrait family's) and, for
the square cartoons, a module named after its main character (`doodle`). A square episode had to restate seventeen
fields to undo the portrait defaults, and nothing stopped an episode from mixing a palette with parts that were never
drawn for it. The operator asked for names for the styles and for the library to improve around them.

## Decision

1. **A style is a value.** `srstudio.styles.Style` holds what a look decides before any part is placed: frame and
   rate, clock (`clock` or `sequence`), input file, caption font, the palettes it is drawn in with a mouth model
   per palette, the id scheme, accessibility defaults, and the modules that hold its parts. `EpisodeSpec(style=…)`
   resolves every unset field from it; an explicit field still wins; a palette the style is not drawn in raises
   `StyleError`. A new style is `dataclasses.replace` of an existing one, or a new `Style`.
2. **Two names.** The styles are named after their drawing technique, not after the sets, characters or formats
   they were first used for, because a style outlives all three:
   - **Cutout** (`CUTOUT`): flat vector shapes, soft gradients, bold outlines, like paper cut-outs. Portrait
     1080×1920 at 30 fps on the project clock. Palettes `office` (cool) and `cafe` (warm). Parts in `cast`,
     `locations`, `props`, `graphics`, `camera`.
   - **Ink** (`INK`): pen stroke, one ink and one grey on white paper. Square 1080×1080 at 24 fps as a sequence of
     shots on their own clocks. Palette `mono`. Parts in `ink` (renamed from `doodle`; the round-headed character keeps
     the name `doodle`) and `subtitles`.
3. **Palettes are named and carry their stage.** `Palette.name` is how a style and an episode refer to a palette;
   `Palette.background` is the colour an episode in that palette starts from, so `EpisodeSpec.background` is optional.
4. **The registry knows the style of a part**, from the module it lives in or from `register(..., style=)`;
   parts that adapt to any palette, such as the signature marks, carry none and are listed for every style.
   `srstudio catalog --style ink` filters; `srstudio styles` lists the styles with their facts.

## Alternatives rejected

| Alternative | Why not |
|---|---|
| Name the styles after their first sets: *Office* and *Printer* | A set is one location of a style; the café episode is already Office-style in a café, and the Ink style will outlive the printer |
| Name them after the genre: *Sitcom* and *Doodle* | Genre says nothing about how the frame is drawn; *Doodle* is also the name of the Ink style's character |
| Name them after the format: *Portrait* and *Square* | The frame is one field of a style and the first thing a new episode may change |
| Keep the families implicit and add a `square=True` switch | The square cartoons differ in clock, input, font, ids and mouth model, not only in frame; a switch per difference is what the seventeen fields already were |
| Put the style on the `Canvas` instead of the spec | The canvas draws; it should not know about input files, fonts or audio. The spec is where an episode is described |

## Consequences

- `EpisodeSpec` fields the style decides default to `FROM_STYLE`; `background` and `palette` are optional. Every
  shipped script still builds the same document (`tests/test_fidelity.py`), and the square script lost its seventeen
  restated fields.
- `srstudio.doodle` is now `srstudio.ink`; the registered part names `doodle-*` are `ink-*`. There is no alias: the
  library has one consumer, this repository, and it was updated in the same change.
- A third style starts as a `Style` value and a module of parts; the README's *Styles* section is the checklist.
