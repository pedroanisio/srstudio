---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0195: Small Print, an explainer format on Rafa's plates

- **Status:** proposed (2026-11-02). arc4d3 requested three pilots; the watch gate is Pedro's, after delivery.
- **Deciders:** arc4d3 (requests and approvals), Pedro (operator: Rafa's look, the watch gate)
- Back to the [library README](../../README.md)

## Context

Small Print (@smallprint.tv) is a new channel of 20–30 s explainers. Each reel answers one question people type into a
search box: the host tries it, a sourced finding lands, and a button answers the opening another way before the reel
cuts back to its first frame. The brief fixes the rules: the typed question on screen within 2 s, the host trying it by
3–5 s, the finding as one stamped line of evidence over a moving picture, no dark still slide over 2 s, the last frame
cutting back to the first, no quiet over 1 s in the first 5 s, captions readable muted inside the safe area, and every
fact on screen traceable to a named source with its year.

Rafa (ADR 0068) is the host. His look is the operator's and cannot change. The Unwritten Rules format (`rafa_show`)
enforces a different show: a "Nobody tells you" hook, three numbered rules and a sign-off. Its props stand still under
his hand, and none of them falls, folds or gets chopped.

## Decision

- `srstudio.smallprint` is the format. A `Show` holds the typed `question`, the `Beat`s, the measured takes and the
  post. A `Beat` names his mood and framing, plus the worktop prop and its state. It also carries `steps` (states it
  moves through, in seconds into the line), a `panel` that takes the frame, a `Stamp` (finding and source), and whether
  he is crying. `Show.validate` refuses the following scripts:
  - a question that is not a typed question;
  - a stamp off a panel, or a stamp with no source;
  - a step that lands after its beat;
  - a reel that opens or closes on a panel;
  - a last beat that is not the first beat's picture;
  - a script whose estimate or whose measured takes fall outside 20–30 s.
- **Worktop states are replacement plates.** This is how the plate pipeline already animates him. `smallprint_props`
  draws four props in his clay world: a stepped tower with a penny (top, three tumbles, landed), a sheet folded 1–7
  times, a tissue roll whose sheet runs out of frame, and an onion under a knife (whole, halved or chopped; knife up or
  down). For the onion his frame-right hand closes round the handle. That hand is `rafa.hold` turned on its side, so it
  is his own drawing. `smallprint.states` maps every state and step to the frames it covers, and those spans tile the
  reel.
- **Tears are a patch.** They are cut against his pose plate, as his eyes and mouth are, from a plate of him with
  only the tears on. The beads lie on the front of his skin's own surface and turn with his head. Nothing about his
  face, body or materials changes.
- **The marks stand apart from the show.** `srstudio.smallprint_kit` holds the channel's colours, the typed-question
  card and the finding stamp. It depends on nothing of the show, so importing the library registers both graphics
  without loading the plate pipeline. `smallprint_props.part_plates` gives the catalog each prop's plate in its first
  state, as `rafa_host.part_plates` does for his own props.
- **Findings are full-frame paper panels.** Each panel is a 2D page in the channel's colours that keeps moving while
  it is up: a tumbling coin with a speed bar, a bolt and tally marks, doubling layers beside a ledger of counts, an
  endless strip, cells breaking into a gas, a falling thermometer, and a blunt knife spraying more droplets than a
  sharp one. The `Stamp` lands on the panel with its source printed under it. Every word on a panel stays up at least
  0.8333 s, reads at 4.5:1 or better on paper, and stays inside the safe width at the top of its pop.
- **The channel's colours are paper `#F4F0E6`, ink `#1C2A4A`, stamp `#A82E22` and ruled blue `#9AA6BF`.** Okayville is
  warm and dark, and News Compiler is a lit screen; this channel is a printed page. The stamp red is dark enough to
  keep 4.5:1 on paper under the grade: a brighter `#C73A2B` measured 4.06:1 on a master's own frames. Captions are the
  engine's karaoke track on an ink band, with the spoken word in `#FF9F7A`. A line too long for the band becomes the
  fewest cues that fit, a sentence or more each, so a one-word sentence never flashes past on its own.
- `episodes/publish_pilots.py` gains the `smallprint` series. The series is in `NOT_COMEDY` because the channel is an
  explainer, not a comedy channel; its craft is scored and reported in `notes.md` without the floor.

## Rejected alternatives

- **Extending `rafa_show`.** Its validator encodes the rules show. Loosening it would remove the checks that keep that
  show's format, so a separate show module is cleaner than a flag.
- **Moving the props in 2D over his plates.** A flat penny or onion over a path-traced worktop reads as a sticker.
  Replacement plates keep one camera and one light, and the plates the reels share are cached by digest.
- **Drawing the findings over him.** The stamp and its source need the frame's width to read on a phone, and his face
  fills the middle of the frame. A full-frame page keeps every word inside the safe area and above the captions.
- **A new host.** The brief names Rafa. Measured plate costs are reported per reel in each pilot's `notes.md`.

## Consequences

- Each new state of a prop is a new plate, and each pose he cries at is a new tear plate. This cost is paid once per
  digest, because the cache keeps them.
- Every part here is `proposed` until the operator has seen it on a rendered clip.
