---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0060: The news kit is a library module with its own set, anchors, graphics and letters

- Status: accepted (2026-10-31). The show's approvals are delegated to arc4d3, and the kit's approval came with
  arc4d3's publish decision on both pilots: real-roast (Slack 1793463409.801599) and everyday-breaking (Slack
  1793473619.087319). arc4d3 approved the second version, with `news-missing-card` and `news-route`, in Slack
  1793475342.947029
- Deciders: arc4d3, by the operator's delegation; recorded by Claude Opus 5.5 in Claude Code
- Applies [ADR 0047](0047-character-versions.md) to new parts, and does not extend
  [ADR 0053](0053-automatic-flow-new-parts.md)
- Back to the [library README](../../README.md)

## Context

@news.compiler relaunches as News Compiler, the parody desk: two anchors at one desk, reading real headlines roasted
and the breaking news of everyday life. Each episode should be mostly a script, two voices and one graphic, so the set,
anchors and graphics have to be built once. The show is not @tuxmeme and it is not Mind, and it must imitate no real
network. A viewer needs to tell a real story from a parody on every frame, and arc4d3 will measure the two kinds against
each other, so one reel must never mix them.

## Decision

`src/srstudio/news_kit.py` holds the show on the Toon sketch build and recording road, under its own `NEWS` style.

- **Look.** A plum set with a bright wall of nine gradient monitors, tangerine and mint accents, cream type panels.
  Barlow Condensed 700 from Google Fonts. The palette and type are chosen to read as no network.
- **Parts.** `news-set`, `news-desk`, `news-vera`, `news-gus`, and the graphics `news-bug`, `news-parody-tag`,
  `news-source-card`, `news-lower-third`, `news-banner`, `news-ticker`, `news-captions` and `news-phone`, all `proposed`.
  The sting is `write_sting`, a function, because the registry has no kind for a sound. It is four short rising notes
  and no bed.
- **A shot is a framing.** The cast's shots are `desk`, `vera`, `gus` and `phone`, drawn by the kit's own dress from
  `Act`s that run parallel to the sketch's beats, because a beat holds one figure's pose and a two-shot has two.
- **Graphics over the camera.** `Staging.overlay` draws what stays over every shot, under the captions, from the beats
  the build placed. `Shot.mouths` hands a figure the dress draws its visemes.
- **Copy limits in the kit.** `check_copy` refuses engagement bait in every graphic, and `Source` needs an outlet, a
  date and a headline.

### The series bible

| | Vera Stillman | Gus Bellows |
|---|---|---|
| Role | Anchor, deadpan | Co-host, chaotic |
| Voice | Matilda, ElevenLabs premade, steady | Charlie, ElevenLabs premade, loose |
| Wants | To finish one bulletin as written | To be part of the story |
| Flaw | Cannot be surprised, so she never stops a thing in time | Cannot let anything go, and every story turns out to be about him |
| Habit | Lowers her glasses and holds a stare | Orders, texts or scrolls on his phone during the news |

Both anchors keep the same look and voices in every episode. Whatever Gus says about his life is a character's boast.

## Rejected alternatives

- **An existing character as the straight anchor.** The coordinator ruled it out for this show, and a recurring cast is
  the point of the format: it gives people a reason to follow.
- **The map kit's or Mind's styling.** The show has to read as its own channel, in the first second, among those feeds.
- **Each anchor as a Toon cast member with `drawer_extras`.** The Toon rig seats one figure per shot; two-shots at one
  desk with their own poses would fight it. `bare` shots and a kit dress keep the build's recording road unchanged.
- **Graphics drawn in each shot's dress.** A lower-third that crosses a cut would redraw and reset at the cut, and a
  camera would move it.
- **A registered part for the sting.** The registry's kinds are character, location, prop and graphic, and adding a
  kind for one function costs more than it buys.
- **A release for each pilot.** Anything with a release can reach ready-to-publish and post to @tuxmeme.
- **A continuous music bed.** The brief asks for a sting only, and on @tuxmeme reels without a bed lead.

## Consequences

- Published reels are untouched: `Staging.overlay` defaults to nothing, `Shot.mouths` is unread by every other dress,
  and `load_mouths` now reads the sketch's own cast.
- New parts cannot be pinned by a release until they are approved.
- The field-reporter frame in the show's brief is for later episodes and is not built here.
- The delivery tool learns the series `news` from the coordinator after the map pilots merge.

## Amendment: the polish pass (2026-10-31)

The operator approved the voices and asked for the picture to be refined. In their words, on 2026-10-31: "run an refine
/ polish pass on the news caracter, props and location. voice aproved." That approval covers the voices of Vera and Gus,
and nothing else. The look's approval was arc4d3's, by the delegation above, and arc4d3 gave it the same day; every
version is recorded in `parts.json` with its words.

The same day the operator ruled that the two pilots are not re-cut: real-roast publishes on its delivered master, and
both pilots stay as delivered and frozen. So they stay on version 1, and the polish is the default for new reels only.

The two pilots looked flat beside the approved inked Toon cast: a wall of nine plain gradients, a dead band over it, no
shadow where anything met the desk, a desk that was a strip and a tall lettered panel, and two figures with no necks and
hose arms. Every drawing that changed is a new version, and version 1 still draws:

- `news-set@2`, `news-desk@2`, `news-vera@2`, `news-gus@2`: the room in planes behind a far blur, a desk with thickness
  and a floor, a camera out of focus in the foreground, and anchors in the cast's pressed line with shade away from the
  key light, necks, jointed sleeves and hands. Their forearms lie over the desk, on a contact shadow.
- `news-bug@2`, `news-parody-tag@2`, `news-source-card@2`, `news-lower-third@2`, `news-banner@2`, `news-ticker@2`,
  `news-captions@2`, `news-phone@2`: one system, with one corner, one shadow, one chip height on the top row, and a
  bottom stack that is flush. The tangerine rule on the lower-third is gone. The desk's lettering is gone, so the Reels
  safe zone carries nothing a viewer needs.

The desk's top moves up 38 px, to 1082, and the banner moves down 50 px, to 1146, so it sits under the top and the hands
on the desk stay in the picture. The stack is shorter, so the ticker's foot moves down only 14 px, to 1416, and stays
over the safe zone. The close-ups pull back, to 1.22 and 1.14, so a head clears a two-line cue.

These parts live in `srstudio.news_inked`, new reels of the show call it, and the two pilots do not. `finish` stays in `news_kit` with its
numbers unchanged, because the polish needed no change to the grade. `parts.KIT_VERSIONS` lets a kit's parts take a second
version: nothing reads a pin for them, because a reel chooses by calling the module.

### Rejected alternatives

- **Redraw `news_kit` in place.** Version 1 would stop drawing, and the delivered masters could not be rebuilt.
- **Adding `(prop, toon)`, `(location, toon)` and `(graphic, toon)` to `parts.ROUTED`.** Those builds read no pin, so a
  second version of any Toon prop would draw for every reel. The check against that stays in force for all of them.
- **Keeping the desk at 1120 with the banner above it.** The banner covered the desk's whole top and every hand on it.
- **A brighter wall to make the set read.** Screens that bright compete with a face, so the room's level comes down and
  the anchors take the light.
