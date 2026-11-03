---
generated-by: Claude Code (Claude Opus 5.5)
---

# ADR 0222: The News Compiler's words keep inside the declared safe area

- Status: proposed (2026-11-03)
- Back to the [library README](../../README.md)

## Context

ADR 0218 has every new scene declare its style's safe area, and the engine enforces it: a text layer that crosses the
region is error `SA01`, and `--strict` writes no master.

News is the second-wave News Compiler look (`news_inked`). It lays its words between `news_kit.TEXT_LEFT` (80) and
`news_kit.TEXT_RIGHT` (1000). `layout.VERTICAL`, the area every 1080 × 1920 style declares, ends at x 920. The first
real-story reel to declare it, `top-that` on 2026-11-03, failed its encode with fifteen `SA01` errors:

- the lower-thirds' line boxes (920 wide from x 80) crossed the right edge by 80 px;
- the source card's date and headline crossed by 76 px;
- the corner credit crossed by 80 px;
- five caption panels crossed by 4 to 74 px.

With those fixed, three more crossings were left:

- the source card's headline began its rise 37 px under the area's foot;
- a caption panel crossed by 3 px, because a panel is its widest row plus padding plus 12, and the wrap measured
  without the 12;
- the ticker crossed. The ticker is a crawl wider than the frame, so it crosses both edges by thousands of pixels and
  passes under them by design.

Every News reel built since ADR 0218 therefore either fails `--strict` or, built without a declared area, is refused by
`publish_pilots.undeclared`.

## Decision

1. **The kit's text overlays take the scene's area.** These overlays take `safe: SafeArea | None = None`:
   `news_inked.lower_third`, `source_card`, `parody_tag`, `captions` and `ticker`.
   - With an area, every word keeps inside its region on every frame, a whole pixel in, because a text box's width is
     rounded.
   - The lower-third's line and the source card's column end at the area's right edge.
   - The corner credit and the PARODY tag end there too.
   - Caption panels centre on the area's column, and the wrap leaves room for the panel's extra 12.
   - The source card's rise starts no lower than the area's foot.
2. **No area draws what went out.** `safe=None`, the default, draws byte for byte what the reels delivered before ADR
   0218 drew. They are frozen, and the contract baseline hashes hold it.
3. **An area the column cannot keep to is refused, never clamped.** `news_inked.safe_box` raises `NewsKitError` when:
   - the area's left edge lies past x 80;
   - its right edge lies short of `TEXT_RIGHT_LEAST` (720);
   - its foot lies above the source card's headline.
4. **The ticker crawl is a declared exception.** Under a declared area, the ticker's group carries `safeAreaForce`.
   The engine's `validate` then lists it as `info[SA02]` on every run, so the exception is never silent. It is the
   only News element so marked: everything that stays still is held to the area.
5. **The News story passes the area.** `episodes/pilots/news_story.Story` in srstudio-episodes gains `safe`, and a reel
   passes the same area it declares on its Staging. Its captions get the area too, through
   `partial(news_inked.captions, safe=...)`.

## Rejected alternatives

- **Move `TEXT_RIGHT` to 920.** That changes every delivered News reel's rebuild, and published content is frozen.
- **Declare a looser custom area for News.** That makes the check pass without keeping the words clear of the
  platform's buttons: a look changed to quiet a check.
- **Leave News reels undeclared.** ADR 0218 refuses that at first delivery, and the ruling is that every scene declares
  one.
- **Clamp an area the kit cannot fit to the nearest width that works.** A silent clamp hides the conflict from the
  reel's author. A refusal names it.
- **Hold the ticker to the area by clipping the crawl.** The engine measures a text layer by its layout box, not by
  what a clip leaves visible, so a clipped crawl still crosses. A crawl of the visible width would need the ticker
  redrawn as a different element, which is a look change for the reviewer, not a layout fix.

## Consequences

- A new News reel that declares `layout.VERTICAL` and passes it to its story and captions renders under `--strict`.
  `top-that` did, with `info[SA02]: news-ticker forced outside the safe area` as its only safe-area line.
- A new reel's lower-third line, source card and captions are 80 px narrower than on the delivered reels. A long
  headline or caption fits at a smaller size, or is refused, earlier than before.
- The other News overlays (`missing_card`, `phone_insert`, `money_app`, `oven_clock`, `route_insert`, `live_door`) do
  not take an area yet. A reel that uses one under a declared area still meets `SA01` on it, and needs the same change.
