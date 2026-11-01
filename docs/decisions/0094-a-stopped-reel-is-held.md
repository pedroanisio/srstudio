---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0094: A reel stopped before its first delivery is held

- Status: accepted (2026-11-01)

## Context

The publish gate treats every release as owed a delivery. When arc4d3 stopped batch A (Slack 1793546229.202829),
its 24 built reels stayed as releases, so `test_the_published_delivery_has_not_drifted` reported each as
"never delivered". The check then failed on every commit, and a failing check that everyone reads past hides the
row that matters.

## Decision

`episodes/posts/_held.py` maps each stopped reel to its reason and ruling. `releases.held` reads it and refuses a
slug that is no release or a blank reason. `check_delivery` owes a held video nothing, and reports one that was
delivered all the same. `publish` passes over a held video in a full delivery and refuses one named with `--only`.

The Drive stage does not read the list. A held reel stays in its "held back" listing, because that listing is where
stock is counted.

A line leaves the map in the commit that delivers the reel, on a ruling that releases it.

## Rejected

- **Relaxing the drift test** to ignore "never delivered". A reel someone forgot would then pass.
- **Deleting the 24 releases.** They are finished work a later ruling may release.
- **Delivering them with `--only` skipped.** Delivery is what the ruling stopped.
