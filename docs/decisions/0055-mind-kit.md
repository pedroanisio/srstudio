---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0055: The mind kit is a library module on the Toon stage, with the channel's own look

- Status: accepted (2026-10-31), in the operator's words: "mind kit approved."
- Deciders: the operator (pedroanisio), recorded by Claude Opus 5.5 in Claude Code
- Applies [ADR 0047](0047-character-versions.md) to new parts, and does not extend
  [ADR 0053](0053-automatic-flow-new-parts.md): that flow covered the broad batch only
- Back to the [library README](../../README.md)

## Context

"There's a Name for That" is a series about how people think: a behaviour, the name for it, one mechanism, one study and
a turn. Each pilot needs the same cards, the same four mechanism visuals, the same sting and the same copy limits. The
series is not @tuxmeme: a pilot must not be able to reach the publishing path by accident.

## Decision

1. `srstudio.mind_kit` holds the channel's look and its registered parts: the stage, the name card, the evidence card,
   captions, and the four mechanism visuals (a spotlight, a memory shelf, two lines, a lens). Its palette, its grade and
   its type (Fraunces 800, from Google Fonts) are its own. The sting is a function, because the registry holds drawings.
2. Faces and lip sync stay Toon's. `MIND` is a `Style` built from Toon's frame, so a pilot uses the approved rigs and adds
   no character look. `Mix(loudness="-14")` and `fps=30` are fields of that style.
3. `toon_sketch.Staging` gains options whose defaults change nothing: `style`, `bare`, `captions`, `finish`, `output` and
   `crf`. A rebuild of a shipped Toon reel at these defaults is byte-identical to the commit before.
4. `check_copy` refuses clinical words, bait and "science proves" on any word a pilot puts on screen, and `Evidence`
   refuses a card that cannot be read in about two seconds.
5. A pilot lives in `episodes/pilots/`, has no release and no post, and renders to `renders/pilots/`. Its cover and
   caption are written next to its sources by `InstagramPost.deliver`, not by the publishing command.
6. An evidence card's paper is the size of what is on it at each moment. A result held back for the narration grows the
   card downwards by a cut as it lands, so nothing already on the card moves and no blank paper waits for it.
7. A worn thing is placed from `toon_head.chest`, in the figure's own coordinates and inside the figure's own transform,
   so one placement holds at every scale a shot gives that figure. The anchor comes from the rig: the neck's line, under
   the lowest the head can reach.
8. The narrator is one constant, `mind_kit.NARRATOR`, ElevenLabs premade Bella, and no pilot's cast shares her voice. The
   operator chose Bella over Roger and Lily from the same lines recorded in each.

## Rejected alternatives

- **A new drawing style.** The operator decided against new character looks for this series, and the Toon rigs already
  carry faces and lip sync.
- **The pilot drawing its own cards.** Every pilot would repeat the same copy limits and the same timing rules, and a
  limit kept in one episode is not kept in the next.
- **A release for each pilot.** Anything with a release can reach ready-to-publish and post to @tuxmeme.
- **Daniel as the narrator.** The first five pilots used this premade broadcaster voice; the operator did not approve it.
- **The held-back result as a strip of its own.** It adds a second object to read beside the card, and the card would
  need a layout rule for it. Growing one paper keeps one thing on screen.
- **Bars without figures on the evidence card.** A bar's length is a claim, so `two_lines` draws to scale from values
  that come from the pilot's sources.

## Consequences

- New Toon reels are unaffected. `srstudio.mind_kit` joins the Toon parts list so the catalog can show its parts.
- A pilot's parts cannot be pinned by a release until the operator approves them, which is the intended stop.
