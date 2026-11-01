---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0080: A reel's brief in episode.json, and giving back an unpublished claim

- Status: accepted (2026-11-01). arc4d3, Slack 1793530050.274539, the order for batch E.
- Deciders: arc4d3 for the field; written by Claude Opus 5.5 in Claude Code
- Amends [ADR 0074](0074-okayville-show-signature.md), decision 6 and *Numbers, and what they depend on*
- Back to the [library README](../../README.md)

## Context

Batch E is made to a new brief, and autopost and the inventory have to tell those reels from the others, holdouts
included: the holdouts are the measure, so nothing about their scripts can mark them. ADR 0074 fixed `episode.json` at
exactly three fields, and every reel already out has that file or none.

arc4d3 also ordered that E posts first and takes the next numbers from #193, with D renumbered after it or shipped
unnumbered. Batch D holds #193 to #216 on reels not delivered. ADR 0074 says a number is never reused, which was written
for a reel pulled from the feed. A claim on a reel that never left the repository leaves nothing on the feed to protect,
and it stands in the way of the reels that go ahead of it.

## Decision

1. **A claim may name a brief.** `srstudio number claim <slug> --brief send-v1`, lower-case words joined by hyphens,
   kept in the reel's entry in `generated/okayville/numbers.json` and refused when it does not match the shape.
2. **`episode.json` carries `brief` only when it is set,** after the three fields. A reel without one writes the same
   bytes as before, so nothing published or queued changes. The release does not repeat it: the brief is a record of the
   ledger, read at the push by `instagram_posts.numbers`.
3. **A claim keeps its brief.** Asking for another brief is refused, as another series is. Asking with none answers with
   the claim held.
4. **The ledger's schema is 1.1.0.** It reads 1.0.0 as well, and every write moves the file up. A row without a brief is
   the row it was.
5. **An unpublished claim is not a used number.** `srstudio number release <slug>` removes a claim on a reel never
   delivered, and refuses if a folder or a manifest entry in `generated/renders/ig`, or a folder in the outbox, shows
   that slug. If it cannot find either folder it refuses too, because a folder it cannot read clears nobody. ADR 0074's
   rule now reads: a number that was delivered is never reused.

## Consequences

- The next claim is still `max(base, highest held) + 1`. A number released from the top of the ledger is taken by the
  next claim; one released under a later claim stays a gap, since filling it would put a reel out of order on the feed.
- The check reads this repository's delivery and outbox, by the name of the video, which is the slug on a numbered reel.
  It does not read the feed or Drive.
- A release that declares the given-back number on its cover stays out of step with the ledger until it is rebuilt.
  `srstudio.show_gate` refuses it at first delivery, by the rule ADR 0074 already has.
- A checkout without this change refuses a ledger at 1.1.0, loudly, by the strict read ADR 0074 asked for.

## Alternatives rejected

- **The brief in the release's `Tags`.** A holdout must differ from the others only in its script, and the posting job
  reads the outbox. The ledger is already the record every session reads, and a claim is the moment the batch is known.
- **A `brief` written on every reel, empty by default.** It changes the bytes of every staged `episode.json`.
- **Filling gaps on the next claim.** It puts a later reel under an earlier number, and autopost posts lowest first.
- **Editing the ledger by hand.** The ledger is written whole under a lock, and a hand edit skips the delivered check.
