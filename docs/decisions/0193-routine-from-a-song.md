---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0193: A routine is choreographed from a song's levels, one move a phrase, the same for one seed

- Status: proposed (2026-11-02)
- Back to the [library README](../../README.md)

## Context

A `dance.Routine` ([ADR 0186](0186-dance-moves-on-the-beat.md)) is written by hand: bars, a move, a face. `dance.song_map`
already reads a recorded track into phrases and louder and quieter parts, and [ADR 0192](0192-dance-arm-gestures.md)
added arm gestures for the loud parts. Placing moves by hand on every song repeats the same choices: small moves where
the song is quiet, gestures where it is loud, a change on a phrase, the same face across a phrase, nothing that makes a
seated character stand. A reel also needs the same routine every time it is rendered.

## Decision

`srstudio.choreograph` turns a song into a routine:

- `choreograph(song, *, support, seed, transition_beats=2.0, max_repeat=2, palette=None, library=None)` reads a
  `dance.SongMap` and writes one `Entry` per phrase, from bar 0 to the song's last bar; a short last phrase keeps the
  bars it has. `choreograph_track(path, groove, ...)` maps a recorded track with `dance.song_map` first.
- A `low` phrase draws from `Palette.low` (by default `seat-groove`, `bob`, `sway`, `head-nod`, `shoulder-roll`,
  `shoulder-shimmy`, `hip-sway`), a `high` phrase from `Palette.high` (`arm-pump`, `raise-the-roof`, `point-up`,
  `clap`, `hand-wave-side`, `arm-wave-overhead`, `bounce`), and an `even` track, which has no louder part, from both.
- `support` is `seat` or `feet`. Only moves it allows are drawn: `seat` and `either` moves for a seated character,
  `feet` and `either` for a standing one, so a seated routine never stands.
- A move runs at most `max_repeat` phrases in a row (1 to 64), and every second phrase of a run is mirrored.
- Each entry crossfades in over `transition_beats`; a phrase shorter than that takes its own length.
- Each phrase holds one face from a typed palette of four (`EXPRESSIONS`: `eyes-closed`, `smirk`, `grin`,
  `open-grin`), the first two for low phrases and the last two for high.
- The draw is `random.Random(seed)` over the palette in its written order, so a seed and a song give the same routine.
  Every loop runs over the song's phrases, which are bounded (at most 512 phrases and 4096 bars) before the first draw.

It refuses, with `ChoreographyError` (a `DanceError`): a song shorter than one phrase, parts that do not tile the song
from bar 0 on its phrase grid or carry an unknown level, a move name the library lacks, a level whose pool is empty
once the support filter has run, a pool that cannot change move before `max_repeat` (a one-move pool with
`max_repeat` below the run it needs), faces outside `EXPRESSIONS`, and a support, seed, transition or repeat outside
its range.

`dance.dump_routine` writes a routine as `srstudio.dance-routine/1.0.0` JSON that `dance.parse_routine` reads back, and
`srstudio choreograph AUDIO --support seat --seed 7` reads the track's grid as `srstudio beat` does and prints the
routine. The routine schema is unchanged.

The tests render a quiet, full, quiet track with `music.render` and check, for both supports and several seeds, that
entries start on the phrases and cover the track, that each phrase's move comes from its level's pool and its support,
that a seated routine never stands, that one seed gives one routine and the CLI one output, that no run passes
`max_repeat`, that repeats are mirrored, and that the routine danced on the `realistic`, `cartoon` and `stick`
presets stays within their limits without clamping.

## Rejected alternatives

- **Moves picked by the song's section names (verse, chorus).** `song_map` reports louder and quieter parts, never
  which one is the chorus; a name the measure cannot prove would be guessed.
- **A choice weighted by measured beat level inside a part.** Levels inside a part move with the mix, so the routine
  would change with a remaster; a part's level is the claim `song_map` checks.
- **Unseeded randomness, or a fixed move order.** Unseeded output breaks a reel's re-render; a fixed order makes every
  song dance the same.
- **Choosing intensity per character.** The choreographer does not know the character, so intensity stays at 1; a
  cartoon's clap that needs intensity 2 (ADR 0192) is set on its entry by the author.

## Consequences

- A routine for a song is one call or one command, and a reel can keep the routine as JSON beside its episode.
- A seated routine drawn only from `either` moves reports its support as `either`; the support the author passed is not stored on the routine.
- The default palette names preset moves; a palette naming other moves passes them in `library`.
- None of the routines has been judged on a drawn body yet; the tests prove timing, support and limits.
