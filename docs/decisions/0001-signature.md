# ADR 0001: Signing every episode with a recurring code and a recurring prop

- Status: accepted and implemented, 2026-10-28 (`srstudio.signature`, `EpisodeSpec.signature`,
  `tests/test_signature.py`; first signed episode: 06 `five-years`)
- Amended by [ADR 0039](0039-the-signature-cactus-may-perform.md): the cactus may perform, opt-in per episode
- Deciders: the operator (pedroanisio), proposals drafted by Claude Fable 5.1 in Claude Code
- Back to the [library README](../../README.md)

## Context

The library builds every episode of the series, in two visual families, from registered parts. The operator wants
each video to carry a mark that identifies the work as theirs without breaking the fiction, the palette of either
family or the engine's accessibility checks, and that a test can assert on every build.

Five candidates were considered. All are feasible with the current SDK and engine; they differ in visibility, cost
and how they prove authorship.

## Decision

Adopt two marks, both drawn by the location builders so that no episode script can omit them:

1. **A recurring code, `SR-1028`** (the library's creation date, 2026-10-28), set as diegetic text in each location:
   the desk papers, the café menu board, the park sign, the printer's model plate. Helper
   `srstudio.signature.code(cv, parent, x, y, scale)`; group id `sig-code`; value from `EpisodeSpec.signature_code`.
2. **A recurring prop, a small potted cactus**, redrawn per palette: gradients in the interview family, pen stroke in
   the hand-drawn family. Helper `srstudio.signature.cactus(cv, parent, x, y, scale)`; group id `sig-cactus`;
   registered as a `prop` so it is listed by `srstudio catalog`.

`EpisodeSpec.signature` (default `True`) enables both. Fidelity tests pass `signature=False`: the six shipped
packages predate this decision and must keep reproducing element for element. Signing them means cutting new
package versions, which is a separate, operator-initiated task.

## Rejected alternatives

| Candidate | Why not now |
|---|---|
| Blinks in Morse code spelling the author's initials | Strongest proof of authorship and invisible to the eye, but it replaces the natural blink timing in both rigs and the doodle's blink is a pupil squash whose durations are already tuned per take; kept as a possible third mark |
| One-frame monogram on the last frame | Easy to add in `Episode.finish()`, but it is a non-diegetic overlay, and a single frame is lost to any re-encode that drops or blends frames |
| Three-note audio ident under the last half second | Requires a shared WAV asset in every package and interferes with the different masters (−16 and −14 LUFS); also invisible in the catalog's SVG player |
| Document-level marks only (metadata, marker, seed) | Already partly true (`generator` in `<metadata>`) and not an easter egg: nobody watching the video can find it |

## Consequences

- Each location builder gains two calls; a new location is not complete until it places both marks (the README's
  *Extending* section and `tests/test_signature.py` enforce this).
- The code is a project-wide constant. Changing it later changes every new build, which is the point: one code, one
  author.
- The marks are excluded from story logic: they never carry a plot beat, never sit on a face or inside a caption box,
  stay inside the safe area and respect `minTextSize` so the engine's legibility check stays silent.
