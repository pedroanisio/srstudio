---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0066: The Unwritten Rules: a talking-head host kit

- Status: proposed; the host is superseded by [ADR 0068](0068-rafa-clay-host-on-plates.md)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Builds on [ADR 0020](0020-toon-lip-synced-cast.md) (lip sync), [ADR 0021](0021-engine-native-features.md) (native
  captions) and [ADR 0050](0050-organic-head-motion.md) (head motion)
- Back to the [library README](../../README.md)

> Superseded in part. The operator's decision: "Rafa will replace Lint on the talking head pilot". The show, its bible
> and its kit stand. The host below is now a parameter, Rafa takes the pilot, and Lint takes no new work.

## Context

The channel brief asks for a new animated non-human presenter who talks straight to camera for 20 to 30 seconds, in a
medium close-up, and changes the picture every 2 to 4 seconds without leaving the face. One character fills the frame
for the whole reel, so the mouth and the eyes carry it. The Toon cast's mouth set has four readings, which is too few
for a face this large, and the brief asks for a wholly new character.

## Decision

`srstudio.host_kit` holds the show. As with `mind_kit`, a show is not a style of its own: `HOST` is Toon's frame and
recording road on its own clock, master and letters (Fraunces 800 from Google Fonts, 30 fps, -14 LUFS).

**The host.** Lint, a clothes moth in your wardrobe, is a new rig family, `host-lint`. `perform` draws him from a `Pose`
per beat, a viseme track and a `head_motion.HeadPlan` that nods on accents, glances, breathes and idles. A lit screen
pulls him: `Pose.pull` leans him at the phone and his wings flutter, which is the show's physical joke.

**Series bible.** Every episode is a Nobody Tells You hook, three rules each topping the last, and Lint breaking rule 1
in the closing seconds, then the sign-off "You know what you did." on the last frame, which cuts back to the first. He
wants everyone to keep the rules, cannot not go to a lit screen, and reads everything and answers nothing. He never
writes a rule down, never admits he is eating the cardigan, and never replies first.

**The mouth.** `PhonemeStyle.fine` reads two more poses from the spelling, `wide` (e, i, y) and `lip` (f, v), and treats
the u of *just* as open. It is off by default, so no recorded reel changes. `Cast.visemes` names the poses a cast has.

**The framings.** `punch` is a hold on the cut, about `PIVOT_Y`, set high so that a punch-in grows him downward and his
crown clears the label at every framing. `Staging.overlay` draws the labels and the phone over every shot and under the
captions, and `Staging.safe_area` declares the Reels safe area the engine then checks.

**Captions.** The engine's karaoke track on ink bands, built by `host_kit.captions` from `ep.native_captions`. Each word
is timed by the take. The ink bands keep the cream and amber at contrast over the amber cardigan.

## Consequences

- The new parts stay `proposed`; none is approved by this record.
- The character families cap in `tests/test_specimens.py` rises from 13 to 14 for the new rig.
- The whole cue shows at once and the sung words turn amber, so a caption has a moving emphasis, not one fixed word.
  Punchlines get a cue of their own to compensate ("laugh.", "Everyone.").
- The voice is a premade human voice. Disclosure rests on the moth on screen and on the caption's line.

## Rejected alternatives

- **One layer per word, each shown as it is said.** This was built first, and it gives one amber word at a time. The
  engine's legibility check refuses any text drawn for under 0.83 s, and 19 findings failed the strict encode. Gating
  by opacity did not change the finding, and hiding text from the check would defeat it.
- **Reusing a Toon cast rig.** The brief asks for a wholly new host, and the Toon heads are not drawn to fill a frame.
- **A pitch-shifted voice.** It would make the voice less human, but the result has to be judged by listening, and
  the transcription check and the lip track are made from the untreated take.
- **A framing pivot on the face.** A punch-in about the eyes pushed his crown under the label in the tight framing.
