---
generated-by: Claude Code (Claude Opus 5.5)
---

# ADR 0218: Every scene declares its safe area

- Status: proposed (2026-11-03)
- Back to the [library README](../../README.md)

## Context

arc4d3 ruled in Slack 1793678456.387679: "Every scene declares its safe area, not only multi-character dances, and
the overlay check refuses a scene without one."

A safe area was opt-in. `EpisodeSpec.safe_area` defaulted to `None`, and only `srstudio.series` and episodes that
named `layout.VERTICAL` declared one. `layout.check_overlays` already refused a document with no safe area, but with
an untyped `LayoutError`, and only fifteen episode scripts ran it. A dance scene with no safe area let a figure's hand
and foot into the right inset and nothing noticed.

On 2026-11-03, 65 of the 245 built scenes in `generated/episodes` declared a safe area. Of the published ones, 134
Okayville videos and 25 pilots had scenes with none, as did the six packaged reels.

Published reels are frozen. Declaring a safe area changes a scene's bytes: it adds `project/@safeArea` and a
`<safeAreas>` element. With the published reel taken off the list below, `the-exit` built as
`06c50902…` instead of `443cb570…`, which is the scene that went out. Declaring one by default for every episode
would therefore rebuild published reels differently.

## Decision

1. **Every style has a safe area of its own.** `Style.safe_area` defaults to `layout.VERTICAL`, the region already
   used for 1080 × 1920 reels. Ink, the one square style, has `layout.SQUARE`: the SMPTE ST 2046-1 title-safe area,
   the middle 90 % of each side.
2. **A library episode declares its style's safe area.** `EpisodeSpec.safe_area` defaults to the style's, and
   `toon_sketch.Staging` leaves it to the style too. `series.Series` keeps its `VERTICAL` default. An episode can
   still name its own. If an episode passes `safe_area=None`, it is refused with
   `layout.UndeclaredSafeAreaError` unless it is on the published list.
3. **Published reels stay as they went out.** `srstudio.safe_areas.PUBLISHED_WITHOUT` is the closed list of the 164
   scene slugs that were delivered before this rule and declared no safe area. A slug on the list still builds with
   no declaration, so its build is byte for byte what develop built before. The list can only shrink, and a test
   holds its length.
4. **The overlay check refuses a scene without one, with a typed error.** `UndeclaredSafeAreaError` subclasses
   `LayoutError`, so existing handlers still catch it. `layout.declared_safe_area` reads a document's area.
5. **A first delivery is refused when its scene declares none.** `srstudio.safe_area_gate.undeclared` runs among
   the Instagram delivery's first-delivery gates. `publish_pilots.undeclared` does the same for a pilot's packed
   scene. Like ADR 0078's gates, they read only reels on their first delivery: a delivered video is never read. A
   reel with no scene to read is refused too. The gate does not honour the published list, so a reel on the list
   that was never delivered cannot slip through.
6. **Scenes that are never posted are listed explicitly.** `srstudio.safe_areas.UNDELIVERED` lists every file
   that writes a scene project outside `Episode` and declares no area. Each entry has a kind (`still`, `catalog`,
   `proof`, `example`, `fixture` or `intermediate`) and a reason. A test scans `src`, `episodes`, `examples` and
   `tools` and holds the list to the code both ways. The two Pedro drive pilots are deliverable, so they declare
   `VERTICAL` and are not on the list.

## Rejected alternatives

- **Declare by default with no list, and accept that published rebuilds change.** Published content is frozen, and
  the rebuild of `the-exit` proves the bytes would change.
- **Keep the default at `None` and only gate delivery.** That holds new reels at the last step, after a render, and
  leaves library builders that do not declare. The ruling says every scene declares one.
- **Mark published episodes with `safe_area=None` in their scripts.** That edits more than a hundred frozen scripts,
  and the result is the same as a list a reviewer can read in one place.
- **Hold catalog specimens, stills and examples to the rule.** A cover, a catalog page or an SDK example has no
  platform interface laid over a moving picture. A typed, listed exemption keeps the rule whole for everything that
  is posted.

## Consequences

- A new episode, or a reel that has not been delivered, now declares its style's safe area when it is built. The
  engine then enforces it (SA01), and native captions centre on it. A held or unposted reel that was built without
  one changes when it is rebuilt, which is the ruling's intent: unposted work is fixed, not frozen.
- A reel delivered after this rule cannot be added to `PUBLISHED_WITHOUT`. The list only shrinks.
- `tests/test_layout.py::test_episode_without_a_safe_area_declares_none` asserted the old opt-in behaviour. It is
  now `test_episode_that_names_no_safe_area_declares_its_styles`.
