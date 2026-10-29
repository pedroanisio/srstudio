---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0033: Every new release carries typed tags the account's analytics can count

- Status: accepted; implemented 2026-10-29 (`srstudio.releases.Tags`, `Release.tags`; `tests/test_releases.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md); extends [ADR 0032](0032-releases-recorders-and-discovery.md)

## Context

The operator's analytics review of the account's first reels found that how widely a premise is recognised is
the strongest predictor of a reel being promoted. Premises most adults live through were promoted far more often
than office-insider ones. It also left three questions it could not answer: whether "our own worst enemy" premises
work, whether alternating the emotion a reel leaves helps, and whether recurring characters turn reach into
follows. To answer them, the review asked for three tags on every episode (who causes the problem, the emotion it
leaves, whether a recurring character appears) and an A/B arm on every episode in a running test.

Nothing in an episode recorded any of these. The premise area lived only in the batch variety table an agent
writes during planning, which nobody keeps.

## Decision

- **A `Tags` value on the release.** `Release.tags` holds a frozen `Tags` with a `territory` (everyday tech, money
  and services, job hunting, relationships, family, our own worst enemy, epic world, office), a `cause`
  (institution, another person, the protagonist), an `emotion` (recognition, embarrassment, tension, relief,
  affection, triumph), the `recurring` characters by their registered short names, and an optional `test` (opening,
  rhythm, jargon) with its `arm` (a or b).
- **Closed sets, checked at construction.** Every value outside its set, a test without an arm or an arm without a
  test, a repeated or non-lowercase character name, and a mapping in place of `Tags` raise `ReleaseError`, so the
  tags can be counted without cleaning.
- **Optional for published releases.** `tags` defaults to `None`. Published content is frozen, so the releases of
  videos already out are not edited; the funny-reels skill (1.9.0) requires tags on every new release.
- **Delivery is unchanged.** Nothing new is written to the delivered bundle yet; the tags are read from the release
  files.

## Rejected alternatives

- **A free-form mapping** (`tags={"emotion": "joy"}`). It accepts typos and new spellings, so the counts split
  across variants. CLAUDE.md prefers typed schemas over free-form maps.
- **Only an `ab.json` file per video folder**, as the review suggested for test arms. It records the arm but not
  the other tags, and it lives in the generated delivery folder rather than in the repository. If the analysis
  tooling needs that file, delivery can write it from `Release.tags`.
- **Tags only in the skill's batch table.** The table is written during planning and not stored, so nothing could
  be counted later.

## Consequences

- An episode added after this decision states its territory, cause and emotion in its release file. A batch review
  can then count the office share or the emotion mix from those files instead of from memory.
- New territories, emotions or tests are a change to the closed sets in `srstudio.releases`, with a test.
