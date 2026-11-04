---
generated-by: Claude Code (Claude Opus 5.5)
---

# ADR 0233: A show named in more words

- Status: accepted (2026-11-04, for Juno & Pip, the Okayville series)
- Back to the [library README](../../README.md)
- Builds on [ADR 0074](0074-okayville-show-signature.md) (the show's cover and the numbers ledger) and
  [ADR 0080](0080-a-brief-in-episode-json-and-giving-a-claim-back.md) (a claim's brief)

## Context

The series brief for Juno & Pip says that every episode carries `"series": "juno-and-pip", "series_number": n` in
`episode.json`, and the tag `JUNO & PIP · EP n` on its cover. Its caption's description opens with
"Juno & Pip, episode n." Until now a series was one capitalised word, `Saga` or `Gloss`, in three places:

- the ledger (`show_numbers._SERIES`);
- the cover (`ShowCover.problems`);
- `episode.json`, as the name in lower case.

So the brief could not be met: `Juno & Pip` was refused, and `episode.json` could not carry a hyphenated slug. The
first two episodes were claimed without a series (#215, #216) for that reason. On the band's top row, the tag
`JUNO & PIP · EP 2` does not fit beside `OKAYVILLE #216` at the label's 60 px floor (it is 384 px in Anton at 60 px
against 379 px of room). Every published record and cover had to stay as it was.

## Decision

1. **A series has a display name and a slug.**
   - The display name is what a cover says: capitalised words, with at most an `&` between two of them (`Saga`,
     `Juno & Pip`).
   - The slug is what `episode.json` says: `show_numbers.series_slug` lower-cases each word and turns `&` into `and`
     (`saga`, `juno-and-pip`).
   - An empty name, or a name with other characters, has no slug and is refused.
2. **The ledger keeps a one-word series under its name and a longer one under its slug** (`series_key`).
   - `Saga` and `Gloss` keep the keys their records already hold.
   - `Juno & Pip` is kept as `juno-and-pip`.
   - The ledger's schema stays 1.3.0: the file's shape is unchanged, so a session on an older pin still reads it.
   - `episode_document` writes the slug for either kind of key, and refuses a key that is neither kind.
3. **A claim gets its place after it was taken** (`show_numbers.place`, `srstudio number place SLUG --series NAME
   --series-number N`).
   - A reel can be claimed before its show is settled.
   - The place is given explicitly, never as the next one free: the brief fixes episode n by the order of its table,
     and builders work in parallel.
   - The reel's number never moves.
   - These are refused, and the ledger is left untouched:
     - a reel with no claim;
     - a reel already placed somewhere else;
     - a delivered reel (its cover went out without the tag);
     - a series with no base;
     - a place that is taken, or at or under the base;
     - a place that is not a whole number from 1.
4. **The cover gives a show named in more words a row of its own** (`ShowCover.episodic`).
   - The tag `JUNO & PIP · EP 2` sits at y 1394 in 60 px, under the top row and at the left margin.
   - The premise starts below it and keeps its 84 px floor.
   - A one-word series keeps `SAGA #19` on the top row, drawn exactly as before.
   - No field is added to `ShowCover`, so no published fingerprint moves.
5. **The show gate matches the cover against the ledger through `series_key`.** For a show, it asks that the
   description open with "Juno & Pip, episode 2.", which is the brief's line. A one-word series still asks for the
   question and then the tag on the first line.
6. **The bible check reads a cover's world through the slug**, which is the lower-cased name for a one-word series, as
   before.

Every release's composed cover and caption text in `srstudio-episodes` (219 releases at 57b5df0) digest identically
before and after this change.

## Alternatives rejected

- **Store the display name in the ledger.** The brief asks for the slug in `episode.json` and in the ledger. A
  display name with spaces and `&` is a poor key, and the posting job reads the slug.
- **Store every series by its slug, `Saga` included.** That rewrites the keys of published records, and a session on
  an older pin would then refuse its own claims.
- **Shrink the series label below 60 px, or shrink `OKAYVILLE #N`, to keep one row.** That puts a label under 10 px on
  the grid, or changes the approved template on every reel.
- **A new `ShowCover` field for the tag's form.** A thumbnail's fields are part of a delivered cover's fingerprint, so
  a new field drifts every published cover.
- **Let `claim` re-name a held claim's series.** `claim` refuses another series because the first one may already be
  on a render; giving a place is a separate, explicit act that checks delivery.
