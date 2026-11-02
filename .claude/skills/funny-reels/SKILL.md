---
name: funny-reels
description: Compose a new funny, adult-audience Instagram reel with srstudio, from premise to a delivered, published-gate-clean video, reusing the catalog first and growing the library (new characters, locations, props) with tests when it lacks something. Use when asked for a new episode, sketch, reel or video script; to make a video funnier; to add characters or diversity to the cast; or to extend the catalog for a video.
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
schema_version: 1.48.0
changelog: "1.48.0: a 3D location from srlocations reaches a reel only as a record written by tools/location_export.py on the pinned srlocations commit and read by srstudio.location_bridge, which checks it against srlocations' projection; drawn in our cel/ink or clay look, with no brand or trade dress, from Pedro's photographs only (ADR 0179). 1.47.0: a character draws one pair of hands on a frame, counted across its pose layers, limb tracks and swung arms whatever the set covers, at the build and at first delivery, the rule hand-count; a swung Toon arm runs in anatomy_ledger.on_arm (ADR 0174). 1.46.0: a text is timed on the frames, across layers and cuts, against the reading minimum, at the build and at first delivery, the check text-timing (ADR 0150). 1.45.0: a burned window that drops a sentence stop, or keeps it and breaks off inside the next sentence, is a build error and a delivery gate, the check caption-grammar (ADR 0149). 1.44.0: a hand has to say which arm it is on, an unpaired hand version is a build error, and the anatomy gate reads what a build noted (ADR 0147); a hand exists only on an arm, one character has one pair of arms and a bust does not end in the open, as build errors, and a prop that draws a hand runs in anatomy_ledger.on_arm (ADR 0148). 1.43.0: a new reel keeps phrases whole across caption breaks: CaptionLook(keep_together=True) and keep_together=True on look.wrap, saga_sets.wrap and gloss_sets.wrap; no break after a weak word, inside a number or inside a name while another fits; delivered reels keep their cuts (ADR 0173). 1.42.0: read the master's levels with srstudio scopes, which names illegal codes, out-of-gamut and oversaturated samples and reports clipping; it does not refuse delivery yet, because every master so far has illegal samples (ADR 0172). 1.41.0: every render and encode srstudio starts waits its turn on one GPU lock and stops with GpuBusyError naming the holder; a hand-run engine command takes it with flock (ADR 0171). 1.40.0: encode with srstudio master, which installs the master write-once and never replaces one (ADR 0170); voice takes, songs and package versions are write-once too. 1.36.0: a timely reel may name the first day it can post (not_before). 1.35.0: hands, thumbs and their direction in motion join the full-size frame review, each raised-hands moment zoomed, on a reel's pinned version. 1.34.0: the hybrid drawing method is the default for new work (ADR 0091): rigid objects through proxy, wheels through vehicle, motion through on_beat, a track's groove from srstudio beat. 1.33.0: a timely reel names its due day with srstudio number claim --post-by, and autopost posts it that day ahead of the number order. 1.32.0: what the drawing crossref found: the shows are Style values that srstudio styles does not list; models, drawn shades and unproven effects, with DRAWING.md named as a proposal; publish_pilots.py runs no frame gate, so a pilot is not covered by them. 1.31.0: Tags carry a second test in also=, so one reel can sit in two A/B tests. 1.30.0: the cast bible checks a first delivery, and the skill names srstudio bible check, rig and gaps. 1.29.0: the commands and refusals the skill had not caught up with: srstudio proof, frames, overlap, arms, lip-proof, lipsync, inspect, cards and fonts in the step that uses each; a cover frame with a caption, a bare word speech-to-text cannot confirm and a Collage strobe are refused early; a test now fails when a command goes unnamed here. 1.28.0: the target is sends and follows: the send test, its sendability table and the lowest-third cut in Select before you produce, Tags send_to and send_line, srstudio number claim --brief send-v1, and first delivery refuses bait on a reel on the test (ADR 0080). 1.27.0: first delivery reads the render report: a --strict finding refuses the reel unless a record in episodes/strict proves it false on the master's own frames (LEG-SHORT, LEG-CONTRAST, or a TXT-FIT cut only while the text comes in), signed off by a reviewer who is not the author; srstudio strict lists the reels shipped that way; a style that declares no report encodes with --report (ADR 0078). 1.26.0: a Collage reel with a bitrate encodes with --hw software, and craft names a two-pass master made in hardware (ADR 0076). 1.25.0: every new reel sets bleed=True, so a blurred far plane reaches the frame's edge; a reel already built keeps its rim, frozen. 1.24.0: the Okayville show signature: one cover band, a fixed corner bug, numbers claimed with srstudio number before the final build, a first-delivery gate on reels in that look (ADR 0074). 1.23.0: the full-size frame review is a required two-step gate on every Okayville reel, first delivery refuses run-together captions, hidden signature marks, cut figures, a detached Stick head and a set that runs out, and batches deliver independently (ADR 0073). 1.21.0: a caption carries at most 5 hashtags, deliver and publish_pilots refuse a new video over that, published posts keep theirs (ADR 0065). 1.20.0: the account is Okayville, @okayville.tv, and the brand is everyday life, animated, not office cartoons. 1.19.0: 14/20 is a floor, not an aim: a reviewer in a different session scores independently, the lower counts, deliver and publish_pilots refuse a new @tuxmeme reel or News pilot under it, Mind and Maps owe none (ADR 0064). 1.17.0: auto-enhance, on by default: every video lands one real enhancement on develop before its first delivery, deliver and publish_pilots refuse without it, srstudio enhance shows the mode, ledger and kinds (ADR 0056). 1.16.0: every part of every kind has numbered versions, a release pins them all with parts=, srstudio build records what it drew and deliver needs that record, a head rig is a record on its version. 1.15.0: heads in Staging move a rigged Toon character's head; what a new rig supplies (ADR 0050). 1.14.0: character versions, a release pins what it draws or delivery refuses it, approval is the operator's alone (ADR 0047). 1.13.0: releases declare style=; caption looks approved per style, counter ratio gate in deliver and check (ADR 0048). 1.12.1: the catalog is a site, served by srstudio serve (ADR 0046). 1.12.0: check must be clean, frozen releases listed and the operator's alone (ADR 0040); spell letters for the recogniser; interview lines time beats with interview.said and carry approved hearings; off-frame lettering left out by a typed location option, never safeAreaForce; rotated brows; ADR 0039 performing mark. 1.11.0: encode with --out-dir; deliver from develop after merge, read check past known drift, never migrate; operator-only hearings; picture timed from takes; ADR 0036 card fields; zoom and lettering checks; check_overlays scope."
---

# Funny reels with srstudio

The library is `srstudio/` (git repo, `../.venv`). Its [README](../../../README.md) is the reference for every
part, style and pipeline named here; the decisions behind them are in `docs/decisions/`. CLAUDE.md binds every step.

**In a git worktree, point Python at it.** The shared venv installs srstudio editable from the main checkout, so
in a worktree `import srstudio` silently loads the main tree's code, and your tests and rebuilds prove nothing
about your branch. Export `PYTHONPATH=<worktree>/src` and check it once with
`python -c 'import srstudio; print(srstudio.__file__)'`, which must print a path inside the worktree. The relative
`../generated` and `../.venv` paths below assume the main checkout; from a worktree, spell them out absolutely.

## The bar

A reel ships when the operator, watching the render, finds it funny. Nothing else certifies it: not your own
score, not a model's (ADR 0015 rejected an LLM "funny gate"). Your job is to get the mechanical half right so the
operator's judgement is spent on the joke.

Score every script yourself against the comedy rubric before building, 0–2 each, and report the score as *your*
estimate. **14/20 is a floor, not an aim** (ADR 0064): a reviewer in a different session scores the reel independently,
without seeing your number, and the lower score counts. Under the floor, rewrite the joke; never raise a score to
clear it. See *Comedy floor* for where the scores go.

| # | Criterion | 2 points means |
|---|---|---|
| 1 | Hook | the premise reads in the first 1–2 s, through an opening chosen for it (see *Pick the mechanism*), not a question by default |
| 2 | Premise | one situation most adults recognise from their own life, in plain words: no workplace jargon, no niche or franchise reference |
| 3 | Structure | the mechanism's setup, turn and payoff, nothing after the strongest laugh |
| 4 | Surprise | the turn is not the first thing the viewer guessed |
| 5 | Escalation | each beat raises the stakes of the previous one (rule of three, then break it), and the payoff is still owed at the halfway mark |
| 6 | Shown | the gag is on screen, and a prop or the location does work in it (plants, escalates or pays off), not explained in a caption |
| 7 | Timing | a hold of at least 1.2 s before the punchline, a sting or a voice right after; a camera move or pause on the beat (see below) |
| 8 | Clarity | the viewer always knows who is talking (distinct voice, caption tint, speaker on screen) |
| 9 | Sound | foley and music carry beats; music ducks under speech |
| 10 | Ending | the last frame is the strongest consequence or reaction; a button (a callback, a card, a loop) only when it tops the punchline |

Measured failures to learn from: the silent Toon character sheet scored 5/20 and was retired as a comedy piece;
*Focus Mode* sat at 13 until it got its punchline and callback.

What worked: one escalating premise with a hard reversal at the end. In *Upside Down* the board is flipped, then
the scorecard reads "reception: taking notes". In *Five Years* the candidate wants the chair, not the job.
What fell flat: captions that explain the joke, and music fighting the lines. *Camera Off*'s lines sat 6–7 dB
under its score until `Episode.audio(duck=)` was added (ADR 0016). *Off and On*'s first cut was flat, and it only
landed after a funnier rewrite and a composed jingle. A batch of fifteen, spread over three styles, opened every
episode on a question and ended every two-hander on the same hold, sting and button: one structure under three
looks. A strong single episode does not excuse a repetitive batch (see *Review the batch for variety*).

The account's own analytics add a harder lesson: the joke can be right and the premise still lose. Premises most
adults live through were promoted far more often than ones mainly office workers recognise, and office was both the
weakest setting and the most produced. Job interviews and everyday tech did best. A world built on a niche reference
stalled on every episode. A reel was more likely to be promoted than not once viewers watched about half of it.
And reach did not turn into follows, which is the case for recurring characters people want to see again.

The account is Okayville, handle @okayville.tv, and the brand is everyday life, animated, not office cartoons. Where a
handle appears in a frame, a cover, an end card or a caption, it is @okayville.tv.

## Select before you produce

Every post slot is scarce (the platform caps posts per day), so a weak reel displaces a stronger one. Make choosing
the premise harder than making the reel.

1. **Write the observation first.** One sentence about people, true off screen, before choosing a style, a cast or
   a reference: "Parents ask for a natural family photo and then direct every smile." If it reduces to "work is
   annoying" or "technology is stupid", it is not specific enough yet.
2. **Most adults must recognise it.** On this account, that alone separated the reels that were promoted from those
   that were not. Prefer the territories the analytics favour: everyday tech, money and services, job hunting. Keep
   office premises to at most one reel in five, so they stay measured but in the minority. Until relationships,
   family and "our own worst enemy" have been measured, give them deliberate tries in every batch (the operator
   sets the split; the last one was seven reels from the favoured territories and three untested).
3. **Epic and absurd worlds, ordinary problems.** An invented world is welcome when the problem in it is an
   everyday one ("a galactic villain who cannot coordinate childcare"). Build the world from scratch; never echo a
   franchise (it invites takedown claims) or lean on a niche reference a newcomer would not get.
4. **Ask the selection questions.** Answer each one in writing; a "no" sends the premise back:
   - Is there a specific observation behind it (step 1)?
   - Would most adults recognise the situation?
   - Does a character's choice cause something?
   - Can part of the joke happen through action, expression or a prop?
   - Will a viewer still be watching at the halfway mark (about 12 s of a 24 s reel)? Something new must happen on
     screen at least every few seconds, and the payoff must still be owed at that point.
   - Does the ending change what we understood, or deliver a satisfying consequence?
   - Does it add something distinct to the recent episodes (*Review the batch for variety*)?
5. **Tag it.** Decide the territory, who causes the problem (an institution, another person, or the protagonist)
   and the emotion it leaves (recognition, embarrassment, tension, relief, affection, triumph). They go in the
   release as `releases.Tags` (ADR 0033), and the batch alternates emotions as well as styles.

Make reels only; no carousels unless the operator reopens them. When the operator runs an A/B test (an opening, a
release rhythm, plain words against jargon), keep the paired reels matched in series, length and territory, and
set the `test` and `arm` in the release's tags. Tests are decided by promotion, not by shares, until a typical reel
draws several shares. While a test runs, `srstudio arms <test>` counts each arm and exits 1 on what
keeps the split from being fair. `--share` gives a split that is not even, and `--order`, a file of slugs in delivery
order, also names a slug outside the test, one left out and two running on one arm.

### The send test

The target is sends and follows, not reach. A reel earns them when a viewer thinks of one person and sends it, so every
reel answers these four, from batch E on:

1. **Who gets it.** The script names the one person a viewer sends it to: mum, partner, the group chat, a manager, a
   roommate. The premise is about that relationship, and sending it says "this is you" or "this is us".
2. **The send line.** The last line is the reason to send: a line people quote.
3. **Punch-up.** A second writer, not the author, rewrites for the send line only.
4. **No bait.** Never "tag a friend" or "send this to", on screen or in the caption. `srstudio.send_gate` refuses those
   words at first delivery and in the publish check, in a character's mouth too, so write around them.

Score sendability 0 to 2 on each row, out of 10. The author, the punch-up writer and the orchestrator each score, and the
lowest counts:

| # | Criterion | 2 points means |
|---|---|---|
| 1 | Recipient | one specific person most viewers have in their life, named in the script's header and evident on screen |
| 2 | Relationship | the joke is a pattern of that relationship, not a general observation with a mum added |
| 3 | Accusation | sending it says something to that person: a viewer can picture their reaction |
| 4 | Send line | the last line works as a quote on its own, spoken in about eight words or fewer |
| 5 | Stands alone | the recipient gets it cold, with no account, series or earlier reel |

**The lowest third by sendability is not made.** Write half as many again as a round needs, and the orchestrator cuts;
ties break on the comedy score. The comedy floor stays, so a reel needs both.

One reel in five is a holdout, the measure: drawn before writing, seeded, never redrawn, written to the old brief with
the same mix and floor, and with no recipient, no punch-up and no cut.

The release carries the test as `send_to=` and `send_line=` in `releases.Tags`, and a holdout carries neither. Every reel
of the batch, holdouts included, claims its number with `srstudio number claim <slug> --brief send-v1` (ADR 0080), which
puts the brief in `episode.json` for the posting job. A timely reel also takes `--post-by YYYY-MM-DD`, on the claim or later, and the posting job sends it that day ahead of the number order. A reel that must not post early also takes `--not-before YYYY-MM-DD`, and it waits in the outbox until then. A reel in two A/B tests names the first in `test` and `arm` and the second in
`also=(("sp-speakers", "a"),)`; `ab.json` then carries both, and a holdout's only test sits at the top level.

## Pick the mechanism, then stage it

Choose how the joke works before writing lines, and let that choice set the opening, the shots and the ending.

| Mechanism | The setup must plant | The camera and the cast | It ends on |
|---|---|---|---|
| Visual reveal | the object or space the viewer has not seen yet, kept out of frame or covered | a frame that hides it, then a cut or a move that shows it; no caption names it first | the reveal itself, or the first face that sees it |
| Misunderstanding | two readings of one word or object, both fair | both characters sure of themselves; the reaction shot shows which reading was wrong | the moment one of them catches up |
| Status reversal | who holds power, made visible (who sits, who stands, whose screen, whose room) | the framing changes as power changes hands (low angle to high angle, wide to small) | the new order, held |
| Physical comedy | the space, the object and the body that will meet | a wide that shows the whole body and the room; no cut during the gag | the recovery, or the failed attempt at it |
| Escalating consequences | one small choice | each beat a bigger result of that choice, each shown, not reported | the largest consequence, or the smallest possible reaction to it |
| Callback | a line, a prop or a gesture that means one thing early on | the same framing as its first appearance | the callback with its meaning changed |

Openings vary with the premise:
- action already under way;
- an awkward exchange in mid-sentence;
- a surprising image held before anyone speaks;
- narration, when the narrator has a point of view the picture contradicts;
- a question.

Whichever you choose, the premise still reads in 1–2 s.

## Camera and pauses are part of the joke

Where the camera is and when nobody speaks are comic tools, not decoration. Plan them in the beat table (a
`camera` column next to picture, line and sound), and check them on the render.

| Technique | What it does to the joke | How to build it |
|---|---|---|
| Wide for the physical gag | the viewer sees the whole body and the room, so a fall or a slow reaction reads as comic, not painful | hold the location's wide angle; cut in only after the gag has landed |
| Crash zoom (snap zoom) | a sudden push onto a face or object underlines a realisation; pair it with a whoosh or a sting | `camera.crash_zoom` (snaps in at most `camera.SNAP` seconds, optional snap back, returns the cue), the pivot set by `camera.anchor`; `foley.write_whoosh` on the returned cue |
| Punch-in on the cut | a hold-key change of framing between shots for emphasis without a visible move | `camera.zoom_holds`, or `camera.reframe` for cut-to-cut scale and position |
| Slow push | builds dread or importance under a line that is about to go wrong | `camera.push_in` eased over 1–3 s |
| Reaction shot / look to camera | the listener's face, or a glance into the lens, tells the viewer what to feel about what was just said | cut to the listener (`Timeline.shots` for the cut spans) and hold on a face that does not move |
| Awkward pause | silence after a line that should get an answer; the discomfort is the laugh | leave 1.5–3 s of dead air between lines, with no new caption and the music ducked or stopped, then a small reaction or the button |
| The spin, the double take | a turn or a look away and back marks the moment the character understands | `camera.spin` with `camera.show_facing`; a pose change held, released, then repeated faster |
| Insert | a full-frame detail (the card's front, the screen, the receipt) that the joke turns on, held long enough to read | a cut to the object alone, gated to its beat (`toon_sets.note_insert` in Toon, `Canvas.gate` elsewhere); cut back to a face |

Rules of thumb: one camera move per beat, never during a spoken line's key word; let a pause run a beat longer
than feels comfortable, then cut; a zoom without a payoff on screen is noise. Measure, don't assume:
`srstudio craft <project> --renders <dir>` lists every move (punch-in, crash, push; camera or gag) and every pause
between lines, with the rendered level in it, so a pause meant to be awkward is shown to be quiet and not filled by
music. A push onto a drawn instance (a reused symbol) softens it when magnified, so draw the target inline or keep
the zoom small, and look at the frame.

Two things `craft` needs from a style, or it reports nothing useful:

- **Name the camera.** A move counts as camera only when its group id matches `craft.CAMERA` (a location, an angle,
  a shot or a setup); an id from `Canvas.uid` reads as a gag that grows. Moves inside a `<sequence>` are reported on
  the episode's clock, so a crash zoom's time can be checked against the line it underlines.
- **Lower the music through the pauses, not only under the lines.** `Episode.audio(duck=)` ducks the bed while
  someone speaks; in the silence it comes back up and `craft` reports the pause as filled. Animate the music
  track's `gain` (audio automation, in dB) down through every gap `craft.pauses` finds, ramping inside the gap, as
  a style's reel helper (`gloss_reel.hush` is one); then re-run `craft` and see the holds read quiet. A sound
  effect inside a gap may fill it on purpose; say so in the report.

A staged series gets both from `srstudio.staging` (ADR 0031): `staging.rig` builds the camera group, and its
`name=` gives it an id `craft` counts.

## The picture has to look finished

A funny script in a flat, unlit picture still reads as a draft: the operator scored a style 4/10 on looks alone.
Score the look yourself, 0–2 each, aim for 8/10 or better, and report it as *your* estimate:

| # | Criterion | 2 points means |
|---|---|---|
| 1 | Depth | at least three planes: a far plane out of focus, the cast sharp, a contact shadow under every figure |
| 2 | Light | one light direction per set; figures shaded on their dark side and lifted off the set; lamps and screens bloom |
| 3 | Composition | the cast stands on a floor line that leaves the caption band clean; panels and cards sized to their words, never half empty |
| 4 | Finish | one grade over every shot (vignette, bloom, fine grain), owned by the style's module, not by an episode |
| 5 | Consistency | one line weight, palette and light logic across sets, props and cards; the signature marks stay sharp |

How to get there:

- **Look before you record.** Takes cost money and rebuilds are free, so render one still per set with the cast,
  a text panel and the caption band (`scene-render render` on a document, `-t` a second, `-o` a PNG), tile them
  into one sheet, look at it, and fix what fails the table before any audio request. Repeat after every change.
- **Use the engine, not more shapes.** Gradients come from `Canvas.grad` and `Canvas.rgrad`. A name is one
  gradient: redeclaring it with other stops, coordinates or units raises `NativeError`, so give each colour its
  own name. Effects are declared with `Canvas.effect` and put on a group with `Canvas.apply`. A style's finish is
  drawn with `srstudio.look` (ADR 0031), called with the style's own numbers and id prefix. The engine has blur,
  drop and inner shadows, bloom, glow, vignette, film grain, colour grading and many more (the full list is the
  effect type in the scene-render schema). Depth of field and a grade lifted a style further than any redraw did.
- **Models and new effects need proof.** `srstudio.clay` bakes a model and `srstudio.plates` path-traces it into cached
  stills; a changed camera or pose can need a new plate, so a moving camera is not one render. For a drawn shade, reuse
  `brush.crescent` before writing a new shape. An effect no video has used is unproven: try it on
  `generated/bin/scene-render`, because the `scene-render/` checkout can be ahead of the engine we render with.
- **The hybrid method is the default for new work (ADR 0091).** Anything rigid seen from more than one angle starts as
  a `clay.Model` drawn by `proxy.layers`: cel plates cut into back, front and under, with the people drawn between
  back and front. `vehicle.tyre` and `vehicle.turning_rim` give it wheels, and `on_beat.ride`, `on_beat.sway` and
  `on_beat.alternate` move a drawing on a `music.Groove`. `srstudio beat <audio>` measures that groove from a track
  and warns under eight bars, where the bar line can land a beat off; a tempo outside about 90 to 160 can read double or half, with no warning, so check it by ear and pass `--near` to settle it.
  `examples/car_vibe` is the worked example, and it never ships. `DRAWING.md` says which layers each
  style takes, and a flat style stays flat. Its `forms` and `paint` modules are not built, so no reel waits on them, and
  a new look needs an approved animated clip and a new part version (ADR 0047).
- **Test the look like any other contract.** A finish, a depth blur or a lit figure is a library default with a
  test (every shot carries the grade, every location blurs its far plane, no signature mark sits under a blur), so
  each episode in the style gets it.
- **Known traps.** A blur on a group that holds the signature marks softens them; draw the far plane in its own
  group. Bloom with a low threshold makes white costumes glow. An inner glow goes all round a figure and reads as
  a sticker outline, not a rim light. A pool of light under the caption band lowers caption contrast.

## Compose in depth, keep it continuous

A set is a stage with planes, not a backdrop with people pasted on it. Plan the depth of every location before
drawing it, add a `layers` column to the beat table next to `camera`, and check it on the lookbook sheet.

**Three planes, each with a job.**

| Plane | Holds | Treatment |
|---|---|---|
| Background | the room or the street: walls, windows, far furniture, sky | lower contrast and saturation, blurred, lit by the set's key light only; never carries a word the joke needs |
| Midground | the cast, the props they touch, the gag's evidence (the note, the screen, the chart) | sharp, full contrast, a contact shadow under every figure and prop that stands on something |
| Foreground | a partial object at the frame edge (a mug, a plant, a chair back, a door frame) that the camera looks past | darker, larger, cropped by the frame, optionally blurred; never over a face, the gag's evidence, the caption band or the signature |

Overlap sells depth more cheaply than any effect: a figure in front of a desk edge, a desk in front of a window
frame. Draw each plane as its own group, far to near, so blur, light and parallax can be given per plane.

**Props are placed, not scattered.**

- Every prop on screen either sets the place in one glance or pays off a gag; remove the rest.
- A gag prop has a job in the joke's structure. It is planted in the setup, changed or used in the escalation, and
  pays off at the end (the board that changes text behind the speaker, a phone that keeps bringing worse news).
  Let the location do the same: an obstacle the character has to work around, or a detail behind them that
  contradicts what they are saying.
- The gag's prop sits in the midground, on a third of the frame, at a size that reads on a phone, and never inside
  the caption band or behind a speaker's head.
- A prop that rests on something gets a contact shadow and the set's light direction; a floating prop reads as a
  mistake.
- Props stay clear of the signature marks, and a test proves it: the Collage episodes record every placed card,
  chart and screen and assert each one clears `collage_sets.signature_box`. Give a new style the same test. A zoom
  keeps both marks in frame too: choose its pivot so it does, and look at the frame.
- Lettering reads at the scale the shot shows it, or it is not lettering. Text below the engine's legibility floor
  (`ink_meter.LEGIBLE_PX` on a 1080 frame) or cut by the frame edge reads as a rendering slip; draw it as a scrawl.
- Lettering framed out is still measured. The engine's safe-area check (SA01) measures a text layer even off frame,
  so a framing that crops a sign fails the build until the text is not drawn at all. Leave it out with a typed
  option on the location (`locations.park(sign_lettering=False)` is the model), added with a test when the
  location lacks one. Never key or hide a set's inner node from the episode, and never set `safeAreaForce` on set
  dressing.

**Frame for a phone held upright.**

- 9:16: faces in the upper half, the caption band clean in the lower third, the cast on a floor line the style
  fixes. `Episode.check_overlays` proves the overlay groups you name (cards, panels, toasts) stay inside the safe
  area on every frame of the finished scene; faces against captions you check on the contact sheet.
- One idea per frame. A wide shows the room and the physical gag; a medium shows who talks to whom; a close-up is
  for the realisation. Cut in on a beat, never at random (see *Camera and pauses*).
- Leave look room on the side a character faces, and headroom that does not change between cuts of the same shot
  size.

**Move the camera through the planes, not over a flat card.**

- 2D move. `camera.push_in`, `camera.crash_zoom` and `camera.reframe` scale one group, so every plane grows at the
  same rate. They are fine for comic snaps, but they look flat on a slow move.
- Hand-drawn parallax. Each plane gets its own speed, as the scrolling scenery does in `stick_car.LAYERS` (far
  layers slower, near layers faster, ADR 0018). This always works, and every speed is a number you set.
- Native 2.5D parallax. Mark each plane group `threeD="true"` and give it a `zDepth`. Then add a perspective
  `<camera>` to the composition and animate the camera, not the planes. The engine works out the parallax from
  depth. Probed on scene-render 0.8.0:
  - With the camera at the 1:1 distance below, a sideways dolly moved a near plane about 3.6 times as far as a
    plane 1200 px behind it.
  - A plane group that carries a blur effect still sits at its depth.
  - To draw `zDepth` 0 at 1:1, place the camera at z = −(frame width / 2) / tan(fov / 2).
  - A deeper plane draws smaller, so scale it up by (zDepth + that distance) / that distance to fill the frame.
  - The camera's own `depthOfField` did not blur 2.5D planes. Keep depth blur as a blur effect on the far plane.
  - srstudio wraps none of this yet. Grow it as a library helper with a test and an ADR before an episode uses it.
- Size the move to the beat. A slow lateral drift (a few percent of the frame width over a line) gives life to a
  dialogue; a push through the foreground into a close-up is a reveal. Do not run a parallax drift under a crash
  zoom: one move per beat still holds.

**Light the scene once, shade everything from it.**

- One key light direction per set and per style, written down in the style sheet. Every figure, prop and contact
  shadow follows it, and the shadows fall on the opposite side from the window or lamp the set shows.
- Paint lit fills with gradients from `Canvas.grad` or `Canvas.rgrad`. Put form and rim effects in their own
  group, and draw the ink outline on top of that group, outside it, so no effect softens the line.
- Small soft highlights, blush and contact shadows are radial gradients that fade to a transparent colour, not
  blur effects. Every node that carries effects renders in its own isolated buffer, so effects cost GPU memory node
  by node. Count the `effects=` attributes on the busiest frame before a full render: frames with 81–105 effect
  groups ran out of memory on an 8 GB GPU while 34 rendered, so keep a frame near 40.

**3D and ray tracing, when the style earns it.**

- The engine also renders lit 3D: `object3D` primitives (sphere, box, capsule, extruded text, meshes) with PBR
  materials, lights (directional, spot, area, dome) and shadows. A probe composited a path-traced sphere, with a
  soft contact shadow, over a flat 2D wall at about 0.4 s per 540×960 frame at 64 samples.
- With `renderer="pathtrace"`, a shadow catcher is not drawn, and the engine says so; give the object a real floor
  instead.
- Use it for one hero object a joke turns on: a trophy, a glossy product, a toilet the gag is about. Never use it
  for the cast or a whole set in a vector-ink style: lit 3D shading next to flat ink reads as two shows. ADR 0018
  rejected `object3D` for Stick because its renderer and lighting were of no use to that style's vector ink.
- Before any episode uses it, add it to the library with a test and an ADR, then look at a frame next to the
  style's figures.
- **3D locations come from srlocations (ADR 0179).** srstudio never imports srlocations. Run
  `tools/location_export.py` with srlocations' interpreter for the shots a script needs at the reel's 1080x1920, and read
  the record with `location_bridge.load`: `location_bridge.LocationRecord.placement` gives a mark's feet and pixels per
  metre, `location_bridge.LocationRecord.in_frame` whether it is in frame, and `location_bridge.Camera.project` any point
  of the set. Draw the location in the style's cel/ink or clay look, never path-traced realism; no brand, badge, livery
  or trade dress; its photographs are Pedro's only and never enter the repository.

**Continuity across shots.**

- A set is one function that draws every plane. Every shot of that set reframes the same drawing (`camera.reframe`
  or a camera move), so walls, windows and props never jump between cuts.
- Keep screen direction: a character who faces right in the wide still faces right in their close-up, and two
  speakers keep their sides of the frame (the 180° line). Eyelines meet across the cut.
- Light, time of day, costume and props hold across a scene unless the gag changes them. If a mug is spilt in shot
  2, it is still spilt in shot 4.
- On the lookbook sheet, tile one frame from each shot of a scene and check plane by plane that nothing jumped.

## Acting: each character performs, including when silent

A rig that holds one pose while someone else talks reads as a cut-out. Before the beats, write a short acting
note per character:
- a resting posture;
- two signature gestures;
- how they listen (still, fidgeting, eyes on their screen);
- their tempo (answers fast, or lets a silence sit);
- how their personality handles this situation.

Then act the beats with it:

- **Listening.** Give the listener their own beat when a line lands on them: a look away, a narrowing, a pose that
  changes. A face held still is a choice (deadpan, the awkward pause), written down as one, never the default.
- **Heads.** In a Toon sketch, `heads=("sloth", "goat")` in `Staging` moves those characters' heads through the whole
  reel: nods on their own words, smaller nods on the other's, glances and breath. It is off unless you name them,
  and a character with no rig is refused by name (`toon_rigs.RIGS` lists who has one). Each rig has its own signature
  in its `HeadStyle`, so choose the cast with it in mind. It needs the recording run's `voiced/speech.json`: a project
  recorded before this records again, which costs nothing with cached takes. Heads do not replace acting, so still
  give the listener a beat when a line lands. Reels already published stay as they are.
- **A new rig.** A character joins by supplying a skull, a face, a trunk, its head contour, neck pivot and tilt, what
  covers the seam and a `HeadStyle`, then an entry in `toon_rigs.RIGS`; a `toon_torso` character gets most of it from
  `toon_critters.Split`. The seam and bounds tests then run on it. Look at a rendered clip beside the flat drawing:
  the rig is a second drawing, and it can drift (the fox's first rig had a collar).
- **Hesitation and anticipation.** Before a big pose or a hard line, add a small opposite move or a held breath:
  eyes away, the arms still, then the line. Soft's rig has this as `blob.cue` (anticipation) and `blob.settle`
  (overshoot and rest); other rigs get it from a short beat with its own pose.
- **Recovery.** After the punchline, show how the character carries on: they pretend nothing happened, try to
  save face, or give up. The recovery is often the button.
- **Eyelines.** Characters look where the thing is: at the other speaker across the cut, down at the prop, into
  the lens only for a look to camera.
- **Measure the face before you push it.** Brows keyed by rotation (the `brows=` extra of `Episode.perform`) turn
  about the head's origin, not their own centre, so a big "raised" angle tilts them inward. In *The Cactus* the
  shock read with brows at 12° and the eyes scaled to 1.10; past those, it read as anger, and the eye whites hid the
  brows. Look at the frame for any expression pushed to the rig's limit.
- **Personality sets the reaction.** The same news gets a different reaction from each character: a controller
  takes notes, an avoider changes the subject. Two characters reacting the same way is a missed joke.

## Characters people come back for

A viewer follows for someone they expect to see again. Before a character appears in a second episode, write their
card in the style's series bible (its ADR or README section; ADR 0036 is the model):

- **wants**: what they want in every episode ("Gary wants respect");
- **flaw**: what in them works against it ("he cannot stop defending his most embarrassing obsession");
- **habit**: the predictable way they fail, with consequences the viewer cannot predict.

Then:

- Write the joke from the card. The flaw or the habit causes the turn; what they want sets what is at stake. A
  script that contradicts a card changes the card in the same commit.
- Every episode pays off for a first-time viewer. A relationship may grow across episodes, but a callback to an
  earlier one is a bonus for regulars, never the joke.
- Prefer a recurring pair over a new cast. One pair in three standalone situations, each showing a different side
  of their relationship, tests the strategy faster than three unrelated casts.
- Story cards are a different thing: `srstudio cards <folder> --fonts ../generated/fonts`, with `--only <name>`, draws
  the show's cast from each character's latest approved version.
- Name them in the release tags (`recurring`) by the short name the bible records, so the analytics can compare
  their episodes with the rest.

## Protect the reveal

The laugh comes when the viewer gets the information, so control the moment each piece of information appears:

- **Captions.** The punchline's words appear when they are spoken, never earlier. Split a long line so that the
  reveal word starts its own cue. Never caption a reveal the picture shows.
- **Props.** The reveal object is out of frame, covered or gated (`Canvas.gate`) until its beat. Toasts, boards
  and cards that give the answer away arrive on the beat, not in the setup.
- **Sound.** The sting goes after the reveal, never before it.
- **Hook and cover.** The opening card and the cover pose the premise and never show the payoff. Use
  `Episode.hide_on_cover` for burned-in text, and set a `Thumbnail` time before the reveal.
- **The end.** Stop on the strongest consequence or reaction. Add a button only when it gets a laugh of its own;
  otherwise cut a beat after the reaction.

## Made for adults

Adult means adult *life*, not explicit content: work, money, landlords, dating apps, group chats, parenting,
ageing, bureaucracy, burnout, tech that patronises you. Instagram's community guidelines still apply: no nudity,
sexual content, slurs, or real people. Irony, deadpan and dark understatement are welcome; the joke is never a
character's identity (age, body, skin, gender, disability, accent, species-as-stand-in). Punch at situations,
systems and the main character's own choices.

## Live inventory: ask the library, never this file

Characters, locations, props, graphics and styles grow with every episode, so this skill lists none of them. Read
them fresh each time:

| Question | Command (from `srstudio/`, with `SRSTUDIO_PACKAGES=../generated/packages`) |
|---|---|
| Which styles exist, and what is each good at? | `srstudio styles` (frame, clock, palettes, parts, description) |
| Which shows exist? | the *Styles* section of the README: `srstudio styles` and `srstudio.styles.STYLES` hold no show, and each show's `Style` value is in its kit |
| Which characters, locations, props, graphics exist? | `srstudio catalog`, or `srstudio catalog --json` for facts and tags |
| Which parts do episodes really use, and which are unused? | `srstudio usage --episodes ../generated/episodes --packages ../generated/packages --scripts episodes --work _tmp/usage-work --out ../generated/catalog/usage.json`, with the `--arg` options the README's usage command passes (ADR 0017; it rebuilds every episode on a copy) |
| Which versions does each part have? | `srstudio parts` (name, kind, style, default, every version; `?` marks a proposed one); `--refused` lists the parts with no drawing of their own |
| How is a part called? | `srstudio inspect <kind> <name>`, kind being character, location, prop or graphic (signature, callback slots, documentation, usage) |
| What does each part look like? | the catalog site: `srstudio serve ../generated/catalog/site`, then open `http://127.0.0.1:8765/` |
| What is already planned? | `docs/backlog/` |

Pick the style whose description fits the joke, not the one used last.

## Part versions

Every registered part has numbered versions (ADR 0047), of every kind. A new reel draws each part's latest approved
version by default, and asks for an older one by pinning it in its release: `parts={"<registered name>": 1}`. Pass
`versions=PINS[SKETCH.slug]` to a Toon `Staging`. `srstudio build <slug> <project>` records every part it drew in the
project's `parts.json`, and `deliver` compares that with the pins, so build with it, not by running the script. Toon's characters take a second version, and so does a show's kit named in `parts.KIT_VERSIONS`, whose new
version is a module the reel calls by name (`news_inked`, not `news_kit`, for a new News Compiler reel); any other part is
refused by name until its kind and style are in `parts.ROUTED`.

To improve a drawing, add a version: a record in `assets/parts.json`, the drawing registered as `<name>@<N>`, a
specimen entry or recipe, and its digest from `srstudio parts --digest <name>@<N>`. An approved look is never revised in
place; a test fails if one changes, and the fix is a new version, not a new digest. A new version stays `proposed`
until the operator has seen its proof clip. Never set `approved` or write `approval` yourself: only the operator's
decision does that, and the record quotes their words.

A head rig is a record on its version, by the same rules: `srstudio parts --json` shows it, and a reel cannot move a
head whose rig the operator has not approved. Changing an approved rig means adding a version of the character.

## Character diversity

Rotate the cast and widen it. Before casting, run the usage report and prefer characters and settings that recent
episodes did not use. Then audit the live catalog along these dimensions, and treat any that it does not cover as a
gap to fill:

- setting: office, home, street, transport, shop, outdoors;
- age: young adult, middle-aged, older;
- body: more than one default silhouette;
- skin tone: as a named look, not an ad-hoc colour override;
- gender expression and hair;
- disability and mobility aids (a wheelchair, a cane) the rig can pose with;
- voice: a distinct premade voice and accent per speaker.

Give each new character a trait that *does* something in a gag (a headset that keeps beeping, glasses that slide on
a double take), never one that *is* the gag. A new character is a registered part (step 4), so the next agent finds
it in `srstudio catalog` without this file changing.

## Workflow

1. **Inventory.** Run the live inventory above, then read the README section for the chosen style.
2. **Script as data.** Start from the observation sentence and the answers of *Select before you produce*, and the
   recurring characters' cards. Write the beats as a table: time, picture, line, speaker, sound, camera, layers.
   Keep it 11–35 s; loops of 12–15 s for a "repeat after me" format. Score it with the rubric. Avoid the premises
   and settings the usage report and the backlog show the catalog already leans on. Never copy a reference's lines,
   drawings or brand: an original script in the same format, an invented brand.
   Name the mechanism and the opening (*Pick the mechanism*). Then write a **shot plan**: one row per shot, a shot
   being a run of beats in one framing. Each row has:

   | Field | What it says |
   |---|---|
   | purpose | setup, turn, reveal, reaction or ending |
   | focus | the one thing the eye must land on |
   | acting | what the speaker and the listener do |
   | props | the props and their state |
   | camera | framing, and a move or "hold" |
   | continuity | what must match the shots before and after |

   A simple entry is allowed ("hold, same as shot 2"); an empty cell is not.
   For a **new style**, and above all a parody of a show or genre, first write a short series bible in the style's
   ADR: the world, the cast with one working trait each, the recurring devices (a host, a board, an end card), and
   the comic engine in one sentence (what the setup always is, what the turn always is). Parody the genre's tropes
   in your own words and drawings; no franchise names, characters, designs, logos, catchphrases or music. Every
   episode script is then checked against the bible before it is scored.
3. **Reuse first.** Build from registered parts and the shared pipelines: `srstudio.sketch` (Toon two-handers:
   speakers, lines, beats, `check`; the Toon and Collage builders are `srstudio.toon_sketch` and
   `srstudio.collage_sketch`, the beat helpers `srstudio.scripting`), `srstudio.takes` (voiced takes checked by
   speech-to-text, optional music `Bed`), `srstudio.song` (sung episodes on a beat grid with composed music),
   `srstudio.interview`, `srstudio.camera`, `subtitles.chunk_words`, `Episode.audio(duck=)`,
   `Episode.check_overlays`, `blob.cue`, `blob.settle`, and the polished rooms (ADR 0008, ADR 0011). Each style's own
   helpers are in its README section. For lip sync (ADR 0019), use `lipsync.SPEECH_MOUTH` with timestamped takes, or
   `soundtrack.OFFICE_MOUTH` with `letters=True` for mouths driven by amplitude. `srstudio.interview` gives exact
   line ends: put the reaction just after the last line, hold, then cut to the end card. Time a beat inside a line
   from the word that triggers it with `interview.said`, never from a fraction of the line. A repeated graphic needs
   its own `id=` per instance; an explicit `prefix=` or `text_id=` keeps the part names you give it.
   **A staged series** (a recorded take timeline staged shot by shot) declares its voices, settings, music bed,
   font, encoder output, reel builder and caption look once as a `series.Series`, subclasses `series.Reel`, finishes
   its picture with `srstudio.look` and stages with `srstudio.staging` (ADR 0031). Never copy another style's
   `*_sets`, `*_reel` or `episodes/_<style>.py`. A new series opts into readable captions,
   `native.CaptionLook(min_last=2, min_seconds=0.84, keep_together=True)`: no lone last word, every cue held long
   enough to read, and no cue cut after a weak word (`the`, `to`, `and`), inside a number or inside a name while
   another cut fits (ADR 0173). Lines a kit wraps itself pass `keep_together=True` to `look.wrap`,
   `saga_sets.wrap` or `gloss_sets.wrap`. A delivered reel keeps its cuts, because its rebuild is frozen.
   `caption_breaks.audit` lists the forbidden breaks in a built scene.
   **Every new reel sets `bleed=True`**, on `collage_sketch.Staging`, `series.Reel`, `stick_reel.spec` or
   `EpisodeSpec`. Without it the engine's blur fades a far plane out at the frame's edge and the page shows through
   as a pale rim about 6 px wide. A far plane painted exactly to the frame also needs `look.depth(..., overscan=True)`,
   and a hand-made blurred group takes `**look.sheet(cv)`. Never set it on a reel that is delivered or already built:
   it changes the drawing, which is frozen.
   **Caption looks are approved per style** (ADR 0048): a release declares `style=` (its style's name), and its scene
   must wear a look `caption_gate.LOOKS` records with an approval, or `deliver` refuses it. A new look goes to the
   operator as a rendered proof first; never fake a record's approval, and never answer the engine's contrast check
   by changing the letters (a stroke in the letters' own colour is refused). Read a 1.00:1 on a stroked caption as
   the measurement's limit, and split the outline: `native.CaptionLook(outline="layer")` draws it as layers under
   the track, and `gloss_reel.LOOK_SPLIT` is Gloss's approved look.
   A new caption face comes from `srstudio fonts add`, which fetches a Google Fonts face, verifies it and pins it.
   **Shared helpers** (ADR 0035): set text with `look.text`, and get the caption font with `Canvas.require_font`,
   which refuses a silent canvas with your error. A talking character takes its mouth states from `lipsync.talk`
   and checks a mouth or pose track with `lipsync.check_track`; a rigged character is placed with
   `rig.check_place` and blinks with `rig.blinks`. Never copy a style's private text, mouth or blink helper.
4. **Grow the library when it lacks something** (TDD, CLAUDE.md): a failing test first, then the part in
   `src/srstudio/`, registered with `register` so the catalog and usage report see it, then an ADR in
   `docs/decisions/` when it is a decision (new style, rig change, new pipeline). Never put a reusable helper only in
   an episode script (ADR 0016). A new module's error class subclasses `errors.SrstudioError`, and a builder reads
   its command-line flags with `errors.flags`, which refuses a typo instead of silently building another cut
   (ADR 0034). Check its inputs with `srstudio.checks` (`checks.positive`, `checks.non_negative`, `checks.second`,
   `checks.spans`, `checks.rising`), passing your own error class and message, never with a hand-written range
   test (ADR 0035). Gates: `ruff format --check`, `ruff check`, `mypy src`, pytest with branch coverage ≥ 80 %,
   run with `SRSTUDIO_PACKAGES=../generated/packages SRSTUDIO_ENGINE=../generated/bin/scene-render`.
5. **Look.** Run the lookbook from *The picture has to look finished* and score the look table. Fix the style in the
   library (step 4) until it reaches 8/10, before any audio request. Add one frame from each shot of every scene,
   then check the planes, the props, the light direction and the continuity rules from *Compose in depth, keep it
   continuous*.
6. **Audio.** Before the first take, `srstudio overlap <project> --episodes ../generated/episodes` lists each run of
   words another episode already said. It only reports: a callback inside a series is often meant, and a repeat
   anywhere else reads as a rerun, so rewrite it. An episode with no script of its own is not compared.
   ElevenLabs premade voices only (no cloning), a distinct voice per speaker, one request per line,
   every take checked by speech-to-text, never a retry driven by model output. Record by slug with
   `srstudio record <slug> <project>` (ADR 0032). A misheard line stops the run, and the operator decides. When the
   operator accepts what was heard, record that transcript on the line (`series.line(heard=)`, `sketch.Line(heard=)`,
   `interview.Spoken(heard=)`).
   Only the operator approves a hearing: never you, a reviewer, another session or a model. Write each line for the
   recogniser before the first request: letters spelled out ("S-R") come back as one word ("SAR"), so respell them
   or plan the hearing with the operator. `sketch.record` refuses a one-word line with a twin (`hearing.TWINS`: a bare
   "Son." comes back "Sun.") before anything is synthesized, so put the word in a sentence or ask the operator to accept
   the hearing. A number read digit by digit ("one-oh-two-eight") matches its digits
   (`voice.check_transcript`). Where a caption must differ from the words spoken, the line keeps the two apart
   (`interview.Spoken` has `text` and `caption`). Structure the takes
   before the first request: a pause is part of a take's duration, never a gap between takes, and shot-sequence
   takes start at 0 and run back to back, with every word inside its take. `Timeline.load` refuses any other
   timeline with `TimelineError`, after the recording money is spent. The recording re-times every beat, so time
   the picture (a reaction, a prop's change, a group shot) from the takes' words and events, never from fixed
   seconds. Takes cost money: reuse the cache rather than regenerating them. Music: ask for 120 BPM
   with "steady kick on every beat" (slow tempo prompts come back off-tempo and are refused). The API key comes from
   the environment; never print, copy or write it.
7. **Build, encode and review the master.** Build with `srstudio build <slug> <project>` (ADR 0032); it validates
   the scene against the schema, and anything but "0 findings" is a defect to fix. Encode from the workspace root
   with `srstudio master <project>/<slug>.scene.xml --out-dir generated -- --strict`, which runs the engine's encode
   and installs `generated/renders/<slug>.mp4` write-once (ADR 0170): a master already there is never replaced, and
   the command stops before it renders. To try again, `--next` writes `<slug>-v2.mp4` beside it, and you promote the
   one you keep by hand. Engine options go after `--`. The encode waits for any other render on the GPU, because
   one job at a time owns the card (ADR 0171). If it stops with `GpuBusyError`, that error names the job holding the
   GPU: wait for it, and never start a second render beside it. If you run the engine by hand, wrap the command in
   `flock -w 900 /run/lock/srstudio-gpu.lock`. `--strict` exits 1
   on any accessibility finding (flashes, contrast) or anything not rendered as authored, and a reel that fails it
   does not ship unless every finding is proven false (see *Strict findings*). Only Toon, Collage and Stick write
   their report by themselves: any other style adds `--report <project>/qa/render-report.json`, or the first delivery
   refuses it. A Collage staging meets the flash rule sooner: `collage_sketch.check_flashes` refuses two `flash`
   beats nearer than `collage_sketch.FLASH_GAP`, on the scripted clock and again on a recording's. A reel whose `Staging.bitrate` is set adds `--hw software`: only libx264 takes the two passes
   its scene asks for, and the hardware encoder the engine otherwise picks leaves a caption's colour on the wall after
   the caption has gone (ADR 0076). Read the master's levels with `srstudio scopes generated/renders/<slug>.mp4`: it names illegal codes, out-of-gamut and oversaturated samples, and reports clipping without judging it. It does not refuse a delivery yet, because every master measured so far carries illegal samples (ADR 0172), so put its line in the review and never call a master clean on it. Then review that file, the mix as delivered, not the scene or a still from the build. You cannot
   judge comic timing by ear, so measure everything that can be measured:
   - a contact sheet with one frame per shot, the hook, the frame just before and just after the reveal, and the
     last frame;
   - `srstudio proof <master>` for the numbers a report quotes, read from the master itself (ffprobe, ebur128).
     Each `--at <seconds>` adds a moment, and `--sheet <image>` writes the first frame, 2 s, the last frame and those moments
     in a row. On a reel in the sp-hook_motion test, `--arm a` or `--arm b` fails unless the master looks like the arm
     its release claims, and also gives the loop seam, what the last frame is from the first;
   - captions that fit, and that appear no earlier than the words they show;
   - safe area and continuity, checked against the shot plan;
   - `srstudio craft` on the project with `--renders`, to confirm the planned moves are there, the pauses read
     quiet, and no line says two passes went to a hardware encoder;
   - on a lip-synced reel, `srstudio lip-proof <project> --master <mp4> --out <folder>`, which pulls full-size frames
     from the middle of words with the pose each should hold, and names a vowel on a shut mouth. A person compares
     them. `srstudio lipsync <timeline.json>` scores the shipped and the speech mouth over the takes.

   On an Okayville reel, look at full-size frames on this first render, before you start the next reel (see
   *Full-size frame review*). Write down every defect as a concrete correction (the time, what is wrong, the fix), fix it, and re-check.
   Report what you measured; the operator watches the master with sound before it is published. A number from a
   scratch file is not evidence; quote real command output. Then update the catalog: re-run the usage report
   from *Live inventory*, then `srstudio page --site ../generated/catalog/site --usage ../generated/catalog/usage.json` with the other arguments
   that `tools/systemd/srstudio-catalog.service` passes. The page build fails until every part the new episode
   calls has a gallery item in `docs/catalog/notes.json`; cut the still, look at it, then add the item.
8. **Instagram delivery.** Add `episodes/posts/<slug with underscores>.py` defining `RELEASE`, a
   `srstudio.releases.Release` with the `InstagramPost` (title, description, credit, `Thumbnail`) and its
   `releases.Tags` (territory, cause, emotion, recurring characters, and the A/B arm when it is in a test). Pin
   every part it draws with `parts={...}`, or `{}` if it draws none: `deliver` refuses a release without
   pins and `check` reports it, and each prints the pin to add for a Toon build. Rebuild after changing a pin.
   While auto-enhance is on, the first delivery of a video also needs its enhancement (see *Auto-enhance*), and a new
   reel always needs its two scores at the floor (see *Comedy floor*). An Okayville reel also needs its independent
   full-size review with no blocker open, and `deliver` runs every new reel through the frame gates (see *Full-size frame review*).
   Deliver only once your branch is merged into develop, from the workspace root with the main checkout's code,
   never from a branch or worktree: any write to `generated/renders/ig` fires the `srstudio-drive` unit, which
   checks and uploads with the main checkout's code and releases:

   ```
   SRSTUDIO_ENGINE=generated/bin/scene-render .venv/bin/python srstudio/episodes/instagram_posts.py \
       deliver generated/renders/ig generated/renders --fonts generated/fonts --only <slug>
   ```

   Then run the same command with `check` instead of `deliver` (and no `--only`). This publish gate compares each
   delivery with its render, post, cover drawing and font. Read the result from `check`'s output, never from the
   fields or version of the `delivery.json` manifest. It must end "delivery current" and exit 0. Every run also
   lists the releases frozen at a cover the operator accepted (ADR 0040); a frozen video stays current only while
   its post draws exactly that cover. Any drift is a defect to report, not background: fix your own video and
   deliver it again with `--only`; for another video, stop and tell the operator. Never re-deliver another video
   to clear it, never freeze a release yourself (`releases.Release(frozen=)` is the operator's decision), and
   never run `migrate` or extend `social.LEGACY_LAYOUTS` (a one-time conversion and a closed set, ADR 0037). Always deliver with `--only`, repeated for each of your videos: a bare
   `deliver` re-delivers every drifted video, published ones included, which breaks the frozen rule. The caption
   gate runs in both commands on every reel not in the closed `posts/_grandfathered.py`: it reports a counter ratio
   under `caption_gate.MIN_COUNTERS` (letters closing up), and a new reel never joins that list. Open
   `cover.jpg` and look: a zoom that crops a card, or a frame caught mid-caption-fade, leaves a ghost. `deliver` refuses
   a cover whose frame carries a spoken caption (`releases.caption_on_cover`): move `Thumbnail(at=)` to a moment with no
   caption, or draw the cover from the scene's cover variant (`Release(cover=True)`). It refuses captions printed over
   each other too (`releases.doubled_captions`).
   Credit voices as ElevenLabs premade voices and music as "composed with ElevenLabs Music"; credit a reference
   creator when the format is adapted.
9. **Publish.** The `srstudio-drive` unit copies every video without drift to `gdrive:srstudio/ready-to-publish`
   (video, `ig.txt`, `cover.jpg`, package) and holds the drifted ones back. Leave it to the unit:
   `python3 episodes/publish_drive.py --dry-run` is not a read-only preview, since it stages `generated/outbox`
   (and packs `generated/vpkg`) before showing what rclone would upload.
10. **Report.** The enhancement each video landed, the observation sentence and the tags of each episode, the batch variety table (below) when there
   is more than one episode, both comedy scores and the look rubric estimate, the cast (and who is new), parts reused versus
   added, gates run with their output, the full-size review with who did it and each blocker's outcome, anything skipped
   and why.

## Five hashtags

A caption carries at most 5 hashtags (`social.HASHTAG_LIMIT`), Instagram's cap since 18 December 2025. The whole
caption counts, and a tag in the description is one of the five. `deliver` and `episodes/publish_pilots.py` refuse a
first delivery over it by slug before anything is written (ADR 0065). The fix is the caption alone, with no re-render.
Published posts keep the 6 to 8 they went out with, so never copy a tag list from a published release. The `SERIES`
tags in `episodes/posts/_interview.py` already number six, so a new Interview reel picks its own five.

## The show's signature

A new Okayville reel in this look (ADR 0074) carries the show's cover and its corner bug. The look's part is approved,
and a new reel opts in like this:

1. **Claim the number before the final build.** `srstudio number claim <slug>`, with `--series Saga` for a series reel,
   prints what it gets. The number is burned in, so it cannot wait for delivery. `srstudio number list` shows the
   ledger. Claims are refused until the count is set once with `srstudio number base`; the counts are in ADR 0074, so
   never guess one. Only reels count, and a pulled reel leaves a gap.
2. **Declare it on the cover.** The release's thumbnail is a `srstudio.thumbnail.ShowCover`: the premise in at most 5
   words and two lines, `number=`, and for a series `series=` and `series_number=`, with `cover=True`. The art stays
   the reel's own, so pick a `at` where no face falls under the band (y 1270 down).
3. **Build by slug.** `srstudio build` reads the number from the release and draws the bug above the camera. Nothing
   else draws it, and it adds no seconds, so the reel's length stands.
4. **A series reel says so.** The caption's first line is the question and then the tag: `Who approved this? Saga #19`.
   The episode still stands alone.

`srstudio.show_gate.show_defects` runs at first delivery and refuses by slug: a number out of the ledger or held by
another release, a missing series tag, a bug that is gone, moved, faded or on another number, a bug over a face, a
signature mark or text, a band over a face, or a video whose corner is not its scene's. The bug stays where it is: move
the pose, the mark or the cover's frame. Published reels never meet this gate, and a reel on any other cover is not
touched. A clean gate proves the corner and the numbers. The look of the frame stays with the full-size review.

## Comedy floor

`comedy_floor.FLOOR` is the number, and the first delivery enforces it with no mode to turn off (ADR 0064):

- A new Okayville reel declares `comedy=Scores(author=15, reviewer=14)` in its release (`srstudio.comedy_floor.Scores`).
- A new News pilot writes `comedy-author` and `comedy-reviewer` in the frontmatter of its `notes.md`.
- Each score is a whole number from 0 to 20, and the lower must reach the floor. Missing, malformed, off the scale or
  under it, `deliver` and `episodes/publish_pilots.py` refuse by slug before anything is written.
- Mind and Maps pilots are not comedy and owe no score. A video already delivered owes none.

The reviewer is a different session, and it scores before it sees the author's number. The gate cannot check that: it
reads two numbers and cannot see who wrote them, so keeping the reviewer independent is on you. A pass proves two
scores were recorded, never that the reel is funny, and the operator keeps the last word.

## Full-size frame review

A required gate on every Okayville reel, from the first render to delivery, in two steps (ADR 0073). The rule, as
arc4d3 set it: "Make the full-size frame review a standing gate for every Okayville batch from now on" and "Full-size
frame review on each reel's first render, not after the batch. Look at a few full-size frames per reel as soon as it
first renders: captions, faces, marks inside heads, props. A defect then costs one re-render instead of holding a whole
batch."

Why it exists: reduced-size passes by the authors missed every defect the first review found, floating figures, missing
limbs, a detached head, run-together captions and missing marks. Contact sheets show that a shot exists, not that a body
ends. And four frames are a sample, so neither step certifies the frames it did not view.

1. **At first render, the building agent.** As soon as a reel first renders, before going on to the next reel, view a
   few full-size frames of it at 1080x1920, one image at a time: captions, faces, marks inside heads, props. Fix what
   you find here, where it costs one re-render. On a voiced project, `srstudio frames <project>` lists the frames to look
   at from its beats (first, 2 s, the payoff, the last and one in every caption), and `--out <folder>` renders each at
   full size with `SRSTUDIO_ENGINE` set, so no caption goes unseen.
2. **On the finished batch, someone who is not the author.** A reviewer who did not build the reel views four frames
   at 1080x1920, one image at a time, never a sheet or a reduced copy: the first frame, 2 s, 75 % of the running time
   and the last frame. The reviewer gets the defect list below and the frames, not the author's opinion of them, and
   reports each defect as a blocker with the time and what is wrong. The orchestrator opens each reported frame and
   checks each blocker before acting on it, since a report is input, not evidence. A confirmed blocker holds that reel
   until a re-render clears it, and the fixed frames are viewed again.

The defect list: a figure ending in a straight cut or floating above what it should stand on; missing legs, arms or
hands, an arm with no hand, a hand with no arm; a head off its neck; a set or a wall that runs out in the frame, scenery
hanging in the air; captions that run two sentences together or cover a face; a mark inside a head or missing from the
shot. Hands, thumbs and their direction in motion: the right hand is the mirror of the left, and a hand's thumb
follows its side, so with palms to camera both thumbs point inward and with backs to camera both point outward.

Hands are not read from a contact sheet: two same hands looked correct on one, twice. Look at each raised-hands moment
at twice full size, in motion as well as at rest. Before a re-render counts as a fix, read the version the episode
module pins, not only its data file, since a reel pinned to an older version rebuilds without the fix.

"deliver batch by batch, a batch never waits for another": a blocker holds its reel, never the other reels of its batch
and never another batch. Each `delivered:` post carries the count, as `delivered: the-refund, split-shift (2 of 24)`
in `docs/slack-channel.md`.

The first delivery runs what code can hold, on any new reel, with no mode to turn off. A delivered reel owes none of it:
`deliver` measures only videos not yet in the manifest, and `check` does not run them. `episodes/publish_pilots.py` runs
none of them, so on a pilot these defects are caught only by someone looking at its frames.

- `frame_gates.captions_run_together`: a burned caption window that runs across a sentence end with no mark. Split the
  window, or mark the end.
- `frame_gates.signature_hidden`: both signature marks seen for at least `MIN_SHOWN` of the running time, measured on the
  engine's frames, so a mark the camera crops or a body covers does not count. Place them where the framing sees them.
- `strict_gate.strict_defects`: a `--strict` finding not proven false, or no render report to read (see *Strict
  findings*).
- `figure_gates.figure_defects`: a character ending in a straight cut that nothing hides or holds, a Stick head off its
  neck, a set that runs out at one edge. It reads the `figures.json` that `srstudio build` writes, so a project built any
  other way is refused until built by the command. Fix the drawing. Never add a thing to quiet the check: a cover drawn
  only to pass still leaves the bust in the picture.
- `anatomy_gate.hand_defects`, the check named `anatomy`: what the build noted against `srstudio.anatomy`, read from the
  `anatomy.json` that `srstudio build` writes, so a scene built before the rule is refused until rebuilt. The build
  itself refuses first (`AnatomyRefusedError`): a hand from a version with one drawing on both arms, or a Collage
  `arm` or `reach` that does not pass `side`. Give the arm its side and use the current version. An arm the camera
  looks down, the viewer's own hand in an insert, adds `view=anatomy.View.POV`, which inverts its thumb. `srstudio anatomy`
  prints the closed list of published reels that keep such a hand. A reel never joins that list to get out, and on a
  first delivery the list excuses nothing.
- `text_rules.caption_defects`, the check named `caption-grammar`, after `frame_gates.captions_run_together`: a burned
  window runs across no sentence end. `Episode.finish` refuses it at the build as `caption-run` (`Take it Whatever`, or
  `Meetings have been reduced to one. It is`); a window of whole sentences with their stops passes (ADR 0149). Cut the
  window at the sentence end. `srstudio anatomy` prints the published windows too, and a reel never joins that list to
  get out.
- `text_rules.timing_defects`, the check named `text-timing`: a text is on screen for 0.8333 s, measured on the frames
  the engine evaluates, from the first frame its words are legible to the last, whichever layers draw them, and each
  burned caption page as the engine pages it. A card carried across a cut is one text, so the engine's false LEG-SHORT
  on it does not count here; a word that flashes does. `srstudio build` runs it after the build with an engine and
  exits 1 as `text-short`; with no engine it says it did not measure, and first delivery measures either way. It does
  not clear the strict gate's records (ADR 0150). Hold the text longer, or carry it into the next shot.
- `anatomy_gate.body_defects`, the same check on the frames: a bust that ends in the open, more than one pair of hands
  on one character on a frame (`hand-count`), and two hands on one arm of one character on a frame. `hand-count` counts
  every hand the character draws on the frame, across its pose groups, limb tracks and swung arms, whatever a sofa, a
  bed or the frame's edge covers: raised arms drawn over a pose whose own paws still rest are four hands though the set
  hides two. Only a character none of whose body is seen (wholly behind an insert) counts just the hands seen. Hide the
  pose's own arms (`omit_arms`) when you swing new ones. `srstudio build` runs it after the build when it has an engine, and exits 1 on a fault; with
  no engine it says the frames were not measured, and first delivery measures them either way. A prop that draws a hand
  and no arm (`phone` or `clipboard` with `hand=`, `lasagna`, `watering_can`, `highlighter`, `folded_sheet`,
  `crayon_cv`), and `toon_bed.swung_arm` or `toon_pair.reach`, is refused at the build unless it runs in `with anatomy_ledger.on_arm("bear", Side.RIGHT):`, which
  changes no drawing and names the arm. `anatomy_parts.BODIES` says what each character has of a body; a new character
  declares its body or a test fails.

A clean gate proves none of the review. The gates do not see an arm with no hand, scenery on a wall or a face under a
caption, and they do not read effects: those are the review's.

## Strict findings

`deliver` reads each new reel's `qa/render-report.json` (ADR 0078). A finding at warning or error refuses the reel, and
so does a report that is missing, of another scene, or of part of the reel. The publishing side's rule: "A reel whose
findings are all proven false ships", "measured on the rendered frames, not argued", and "Real findings still get
fixed." Fix a finding first. Only a finding the frames show is false goes further.

Three kinds can be proven false. Any other code is a real finding.

- `LEG-SHORT`: the text's real time on screen, its first to its last legible frame, against the report's minimum.
- `LEG-CONTRAST`: the ratio on the composited frame, at the text's worst frame, against the report's minimum.
- `TXT-FIT`: a text cut only while it comes in. At rest its glyphs are inside the box that holds them and inside the
  frame, and the report's cut is over by the first frame it rests. A text cut at rest, or as it leaves, is cut.

Measure on the master that will ship, last, because any re-encode voids the record even from the same scene. Save
whole frames of that master, untouched and uncropped, under `<project>/qa/strict/`, and write
`episodes/strict/<slug>.json` in the shape ADR 0078 gives. Cite a `LEG-SHORT` run's first and last frames and a
`LEG-CONTRAST` run's worst, and a `TXT-FIT` run's first, rest and last. Someone who is not the author reads the frames and signs as `reviewer`. The gate checks the
numbers against the files, and it cannot see that the text is readable in those frames or stayed up between them: that
is what the reviewer signs.

The `delivered:` post carries each reel's lines from `srstudio strict` and its frames, because arc4d3 spot-checks them.

## The cast bible

A first delivery is checked against the cast bible (ADR 0069), so run `srstudio bible check` on the release and the
brief before recording: it flags a name, a relation or a drawing the bible does not hold. `srstudio bible rig` holds a
recurring Stick figure to the base rig it was published with; clothes and props change per reel, the rig does not.
`srstudio bible gaps` lists what published reels have that the bible lacks. A persona edited without a new version is
drift, and nothing is delivered on it.

## Auto-enhance

Every video leaves the process better for the next one. The mode is on by default; `srstudio enhance` shows it and the
ledger of what every video added. When the mode is on, the agent that builds a video owns one enhancement, done when
the video is finished and merged into develop before the video's first delivery. `deliver` and
`episodes/publish_pilots.py` refuse a new video without it (ADR 0056). When it is off, deliver the video and do nothing
else. Only the operator changes the mode, with `srstudio enhance off` or `on`; never turn it off to get past the gate.

Start from what this video made hard, what looked weakest, or what you wished the library had, and write the change for
the next video, not this one. The commit's `Enhancement-Kind` is one of these, listed by `srstudio enhance kinds`:

| Kind | What it can be |
|---|---|
| `comedy` | a joke mechanism, a beat-timing helper, a hook or payoff rule in this file |
| `story` | a stronger shape: a format, escalation, an ending, a replay loop, how premises are chosen |
| `picture` | grade, light, depth, palette, composition, finish |
| `motion` | gestures, walks, reactions, secondary motion, timing curves |
| `effects` | transitions, engine effects, particles, text animators |
| `camera` | moves, framing, cuts, parallax |
| `music` | scores, stings, ducking, the mix |
| `sound` | foley, ambience, impacts, room tone |
| `voice` | casting, delivery settings, pacing, lip sync |
| `character` | written descriptions, expressions, poses, wardrobe, rigs of the approved cast |
| `props` | a new or better prop the next reel can use |
| `sets` | a new or better location or room |
| `readability` | captions and on-screen text: size, timing, placement, emphasis |
| `covers` | headline, crop, contrast, the first frame |
| `checks` | a new automatic check that catches a defect before delivery |
| `speed` | a cheaper or faster build, render, take or reuse |
| `insight` | a lesson from the account's numbers, turned into a rule or a default |

What the gate reads, from the history of develop:

- One commit, one video. It ends with these two trailers in its last paragraph, beside `Co-Authored-By`:

  ```
  Enhances: <slug>
  Enhancement-Kind: <kind>
  ```

- It changes `src/srstudio/` or `tools/` and adds a test, or it changes this file and bumps `schema_version`.
- It touches none of the video's own files: not its scripts, its release or its pilot folder. A batch of ten owes ten.
- A video that has been delivered once owes nothing again.

The gate proves a change landed. It cannot prove the change is an improvement, so the bar is yours: a real change the
next video can use, never a comment, a rename or a test that cannot fail. The usual limits still bind. Published
reels stay byte-identical, so a library change defaults to no change. A new part follows the approval rules, and new
character looks, hearings, frozen reels and the caption looks stay the operator's. Never loosen a check as your
enhancement.

## Lanes

Each batch or pilot set is one govern lane (ADR 0058), so its state and its token cost live outside any one chat. The
tool is `/home/pals/src/super-tools/bin/govern`, and it finds the workspace from any worktree.

- Start: `govern new <slug> --process reel` or `--process pilot`, then write `lane.json` in the lane's folder
  (`generated/govern/projects/<slug>/`) with `branch` and, for a pilot, `series`. Name the worktree with
  `govern file <slug> worktree '{repo}/_tmp/wt/<name>/'`, so sessions working there count on the lane.
- Work: `govern brief <slug>` starts a session from the lane's state. Record a decision with `govern note` when you
  make it.
- Move: `govern advance <slug> --note "<evidence>"`. Merge and deliver leave only on their checks; a note cannot pass
  them, and a failed check is a defect to fix.
- Cost: `govern usage <slug>` reports model tokens. ElevenLabs takes are not in it.

A lane records the work and never replaces a gate. Approvals stay where they are, the operator's own words on the
record, and a pilot's `watch` note quotes them and approves nothing.

## Review the batch for variety

When you write several episodes, check them as a set before any audio request, and again against the last
episodes already published (the releases in `episodes/posts/`). Make one table with a row per episode and these
columns:
- territory (the `Tags` territory) and who causes the problem;
- emotion it leaves;
- recurring characters;
- opening;
- mechanism;
- staging (which shots and in what order);
- pairing of characters;
- ending.

Rules of thumb:
- no two episodes in a row share both opening and mechanism;
- no opening, mechanism or ending appears in more than a third of the batch;
- a pairing repeats only when the relationship is what the joke is about;
- office premises make at most one in five, counting the recent releases;
- no two episodes in a row leave the same emotion.

The same structure redrawn in another style is still a repeat. Keep what makes a style or a cast recognisable (the
look, the signature marks, a character's traits), and vary the joke underneath it.

## Never

- Re-render, rebuild or re-deliver a published video unless the operator asks: published content is frozen, and
  improvements apply to new episodes only.
- Present your rubric score, a render you did not watch, or expected output as observed.
- Write scratch outside `srstudio/_tmp/`, or touch `protected/` or `authorial/`.
- Edit a file another session owns without asking it (`ListAgents`, `SendMessage`); commit only your own paths.
- Commit unless the operator asked; never lower a gate or skip a test to pass.
- Make a character's identity the punchline, or depict a real person or brand.
- Echo a franchise (its names, characters, designs, logos, catchphrases or music) or build a joke on a reference a
  newcomer would not get.
- Let a signature mark carry a plot beat except through `signature.cactus(act=)` or a location's `cactus=` slot,
  with exactly one `sig-cactus` in every shot (ADR 0039).
- Change a shipped default (a mouth style, a style's frame or palette) for a new episode: it breaks the fidelity
  tests and the rebuilds of videos already delivered. Add an option and leave the default alone; prove a refactor
  with a byte-identical rebuild.

## Keeping this skill true

The library will outgrow any list, so this skill is built not to hold one:

- **Inventory is read live.** Parts, styles, usage and gaps come from the commands in *Live inventory*. The skill
  names dimensions to audit, never which parts exist or are missing.
- **Every citation is tested.** `tests/test_skill.py` resolves each module, function and constant this file cites,
  runs each `srstudio` command it names with `--help`, and checks each ADR and repository path. A rename or removal
  in the library fails the suite until this file follows it.
- **Every command is named.** The same test fails when `srstudio` has a command this file does not name, so a new one
  lands here with the step that uses it. Nothing tests that a new refusal reaches this file: that stays the author's.
- **No inventory or snapshot creeps back.** The same test fails if a registered part or style name appears as code
  in this file, or if a date pins a measurement here.
- **Grow the library, not this file.** A new character, location, prop or style is registered and documented in
  the README and an ADR; agents then find it through the commands above. Edit this file only when the *process*
  changes (a new gate, pipeline or delivery step), bump `schema_version`, and run `tests/test_skill.py`.
