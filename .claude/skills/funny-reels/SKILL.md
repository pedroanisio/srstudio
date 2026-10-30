---
name: funny-reels
description: Compose a new funny, adult-audience Instagram reel with srstudio, from premise to a delivered, published-gate-clean video, reusing the catalog first and growing the library (new characters, locations, props) with tests when it lacks something. Use when asked for a new episode, sketch, reel or video script; to make a video funnier; to add characters or diversity to the cast; or to extend the catalog for a video.
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
schema_version: 1.14.0
changelog: "1.14.0: character versions, a release pins what it draws or delivery refuses it, approval is the operator's alone (ADR 0047). 1.13.0: releases declare style=; caption looks approved per style, counter ratio gate in deliver and check (ADR 0048). 1.12.1: the catalog is a site, served by srstudio serve (ADR 0046). 1.12.0: check must be clean, frozen releases listed and the operator's alone (ADR 0040); spell letters for the recogniser; interview lines time beats with interview.said and carry approved hearings; off-frame lettering left out by a typed location option, never safeAreaForce; rotated brows; ADR 0039 performing mark. 1.11.0: encode with --out-dir; deliver from develop after merge, read check past known drift, never migrate; operator-only hearings; picture timed from takes; ADR 0036 card fields; zoom and lettering checks; check_overlays scope."
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

Score every script yourself against the comedy rubric before building, 0–2 each, aim for 14/20 or better, and
report the score as *your* estimate:

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
draws several shares.

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
| Which characters, locations, props, graphics exist? | `srstudio catalog`, or `srstudio catalog --json` for facts and tags |
| Which parts do episodes really use, and which are unused? | `srstudio usage --episodes ../generated/episodes --packages ../generated/packages --scripts episodes --work _tmp/usage-work --out ../generated/catalog/usage.json`, with the `--arg` options the README's usage command passes (ADR 0017; it rebuilds every episode on a copy) |
| Which versions does each character have? | `srstudio characters` (name, style, default, every version; `?` marks a proposed one) |
| What does each part look like? | the catalog site: `srstudio serve ../generated/catalog/site`, then open `http://127.0.0.1:8765/` |
| What is already planned? | `docs/backlog/` |

Pick the style whose description fits the joke, not the one used last.

## Character versions

Every character has numbered versions (ADR 0047). A new reel draws each character's latest approved version by
default, and asks for an older one by pinning it in its release: `characters={"<registered name>": 1}`. Pass
`versions=PINS[SKETCH.slug]` to a Toon `Staging`.

To improve a drawing, add a version: a record in `assets/characters.json`, the drawing registered as `<name>@<N>`, a
specimen entry, and its digest from `srstudio characters --digest <name>@<N>`. An approved look is never revised in
place; a test fails if one changes, and the fix is a new version, not a new digest. A new version stays `proposed`
until the operator has seen its proof clip. Never set `approved` or write `approval` yourself: only the operator's
decision does that, and the record quotes their words.

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
   `native.CaptionLook(min_last=2, min_seconds=0.84)`: no lone last word, and every cue held long enough to read.
   **Caption looks are approved per style** (ADR 0048): a release declares `style=` (its style's name), and its scene
   must wear a look `caption_gate.LOOKS` records with an approval, or `deliver` refuses it. A new look goes to the
   operator as a rendered proof first; never fake a record's approval, and never answer the engine's contrast check
   by changing the letters (a stroke in the letters' own colour is refused). Read a 1.00:1 on a stroked caption as
   the measurement's limit, and split the outline: `native.CaptionLook(outline="layer")` draws it as layers under
   the track, and `gloss_reel.LOOK_SPLIT` is Gloss's approved look.
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
6. **Audio.** ElevenLabs premade voices only (no cloning), a distinct voice per speaker, one request per line,
   every take checked by speech-to-text, never a retry driven by model output. Record by slug with
   `srstudio record <slug> <project>` (ADR 0032). A misheard line stops the run, and the operator decides. When the
   operator accepts what was heard, record that transcript on the line (`series.line(heard=)`, `sketch.Line(heard=)`,
   `interview.Spoken(heard=)`).
   Only the operator approves a hearing: never you, a reviewer, another session or a model. Write each line for the
   recogniser before the first request: letters spelled out ("S-R") come back as one word ("SAR"), so respell them
   or plan the hearing with the operator. A number read digit by digit ("one-oh-two-eight") matches its digits
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
   with `generated/bin/scene-render encode <project>/<slug>.scene.xml --out-dir generated --strict`, which writes
   `generated/renders/<slug>.mp4` (without `--out-dir`, the path resolves inside the project). `--strict` exits 1
   on any accessibility finding (flashes, contrast) or anything not rendered as authored, and a reel that fails it
   does not ship. Then review that file, the mix as delivered, not the scene or a still from the build. You cannot
   judge comic timing by ear, so measure everything that can be measured:
   - a contact sheet with one frame per shot, the hook, the frame just before and just after the reveal, and the
     last frame;
   - captions that fit, and that appear no earlier than the words they show;
   - safe area and continuity, checked against the shot plan;
   - `srstudio craft` on the project with `--renders`, to confirm the planned moves are there and the pauses read
     quiet.

   Write down every defect as a concrete correction (the time, what is wrong, the fix), fix it, and re-check.
   Report what you measured; the operator watches the master with sound before it is published. A number from a
   scratch file is not evidence; quote real command output. Then update the catalog: re-run the usage report
   from *Live inventory*, then `srstudio page --site ../generated/catalog/site --usage ../generated/catalog/usage.json` with the other arguments
   that `tools/systemd/srstudio-catalog.service` passes. The page build fails until every part the new episode
   calls has a gallery item in `docs/catalog/notes.json`; cut the still, look at it, then add the item.
8. **Instagram delivery.** Add `episodes/posts/<slug with underscores>.py` defining `RELEASE`, a
   `srstudio.releases.Release` with the `InstagramPost` (title, description, credit, `Thumbnail`) and its
   `releases.Tags` (territory, cause, emotion, recurring characters, and the A/B arm when it is in a test). Pin
   every character it draws with `characters={...}`, or `{}` if it draws none: `deliver` refuses a release without
   pins and `check` reports it, and each prints the pin to add for a Toon build. Rebuild after changing a pin.
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
   `cover.jpg` and look: a zoom that crops a card, or a frame caught mid-caption-fade, leaves a ghost.
   Credit voices as ElevenLabs premade voices and music as "composed with ElevenLabs Music"; credit a reference
   creator when the format is adapted.
9. **Publish.** The `srstudio-drive` unit copies every video without drift to `gdrive:srstudio/ready-to-publish`
   (video, `ig.txt`, `cover.jpg`, package) and holds the drifted ones back. Leave it to the unit:
   `python3 episodes/publish_drive.py --dry-run` is not a read-only preview, since it stages `generated/outbox`
   (and packs `generated/vpkg`) before showing what rclone would upload.
10. **Report.** The observation sentence and the tags of each episode, the batch variety table (below) when there
   is more than one episode, the comedy and look rubric estimates, the cast (and who is new), parts reused versus
   added, gates run with their output, anything skipped and why.

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
- **No inventory or snapshot creeps back.** The same test fails if a registered part or style name appears as code
  in this file, or if a date pins a measurement here.
- **Grow the library, not this file.** A new character, location, prop or style is registered and documented in
  the README and an ADR; agents then find it through the commands above. Edit this file only when the *process*
  changes (a new gate, pipeline or delivery step), bump `schema_version`, and run `tests/test_skill.py`.
