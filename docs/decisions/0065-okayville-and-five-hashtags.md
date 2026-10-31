---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0065: Okayville, and five hashtags from the first delivery

- Status: proposed (2026-10-31), on the publishing side's setup message of that day: "@tuxmeme is now *Okayville*,
  handle *@okayville.tv*", "*At most 5 hashtags per caption*", applied "to everything not yet delivered".
- Deciders: arc4d3, the publishing side, for the name and the limit; written by Claude Opus 5.5 in Claude Code
- Follows [ADR 0056](0056-auto-enhance.md) and [ADR 0064](0064-comedy-floor.md)
- Back to the [library README](../../README.md)

## Context

The account changed its name and its handle, and its brand is now everyday life, animated, not office cartoons.
The same message reports that Instagram cut its hashtag cap from 30 to 5 on 18 December 2025, and
`social.HASHTAG_LIMIT` still said 30.

133 releases are delivered, and 128 of them carry 6 to 8 hashtags. Published content is frozen. A post's fingerprint
holds its caption, so trimming one of those posts would drift it, and the next delivery would rewrite it.

`InstagramPost.problems()` runs each time a build writes `ig.txt`, and it cannot tell a published post from a new one.

## Decision

1. `HASHTAG_LIMIT` is 5. `PUBLISHED_HASHTAG_LIMIT` keeps the old 30, and `problems()` holds only that one, so a
   published episode still rebuilds.
2. The first delivery holds the limit, by the test ADR 0056 and ADR 0064 use: a video in the delivery manifest owes
   nothing, a pilot already on Drive owes nothing, and `check` asks nothing. The refusal is a typed `HashtagError`
   naming each slug, before anything is written.
3. `hashtag_excess` counts the tags in the caption's whole text, not the `hashtags` field, because Instagram counts the
   text: a tag in the description is a tag. On a pilot it reads `ig.txt`, the only form of the caption that exists there.
4. Every pilot series owes the limit: it is Instagram's, not the comedy channels'. Like the comedy floor it has no mode.
5. The shared `SERIES` tags in `episodes/posts/_interview.py` stay at six: delivered posts draw on them, so trimming
   them would change those posts' fingerprints. No unreleased release existed to trim.
6. The name changes in live text only: the skill, the references, the tools' descriptions, and comments, docstrings and
   refusals. A past ADR, a test that quotes the old name and the skill's changelog keep it. The Drive folders,
   `ready-to-publish`, `outbox.json` and `.ignore` do not change.
7. `tests/test_okayville.py` fails if the old name appears in a source a reel is built from, in a guide an author copies
   from, or in a release's caption, cover spec or extras.

## Alternatives rejected

- **Lowering the limit inside `problems()`.** Every rebuild of a published episode would raise, and 128 posts would have
  to be trimmed or listed.
- **Trimming the published captions.** They are frozen, and each would drift and be delivered again.
- **A closed list of exempt reels.** The manifest already says what has been delivered, as in ADR 0056.
- **A `published` flag on `InstagramPost` or on `Release`.** It would repeat the manifest in 133 files and could
  disagree with it.
- **Refusing the old name at delivery.** The name is gone from the sources, and a test finds it sooner than a refused
  delivery would.

## Consequences

- A new post with too many tags builds, and is refused at its first delivery. The fix is the caption alone.
- Branches holding unreleased reels with six or more tags are refused until they trim them.
- A published post that is edited can still go out with up to 30 tags. Published posts are not edited.
- The test reads text, not pixels. Lettering inside an image, or a string put together at run time, is outside it.
