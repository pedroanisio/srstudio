---
name: funny-reels
description: Compose a new funny, adult-audience Instagram reel with srstudio, from premise to a delivered, published-gate-clean video, reusing the catalog first and growing the library (new characters, locations, props) with tests when it lacks something. Use when asked for a new episode, sketch, reel or video script; to make a video funnier; to add characters or diversity to the cast; or to extend the catalog for a video.
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
schema_version: 1.3.0
---

# Funny reels with srstudio

The library is `srstudio/` (git repo, `../.venv`). Its [README](../../../README.md) is the reference for every
part, style and pipeline named here; the decisions behind them are in `docs/decisions/`. CLAUDE.md binds every step.

## The bar

A reel ships when the operator, watching the render, finds it funny. Nothing else certifies it: not your own
score, not a model's (ADR 0015 rejected an LLM "funny gate"). Your job is to get the mechanical half right so the
operator's judgement is spent on the joke.

Score every script yourself against the comedy rubric before building, 0–2 each, aim for 14/20 or better, and
report the score as *your* estimate:

| # | Criterion | 2 points means |
|---|---|---|
| 1 | Hook | the premise reads in the first 1–2 s, as on-screen text and the first spoken line, ideally as a question |
| 2 | Premise | one situation an adult recognises from their own life |
| 3 | Structure | setup, turn, punchline, in that order, nothing after the button |
| 4 | Surprise | the turn is not the first thing the viewer guessed |
| 5 | Escalation | each beat raises the stakes of the previous one (rule of three, then break it) |
| 6 | Shown | the gag is on screen (a note on the laptop, a toast with the evidence), not explained in a caption |
| 7 | Timing | a hold of at least 1.2 s before the punchline, a sting or a voice right after; a camera move or pause on the beat (see below) |
| 8 | Clarity | the viewer always knows who is talking (distinct voice, caption tint, speaker on screen) |
| 9 | Sound | foley and music carry beats; music ducks under speech |
| 10 | Ending | a button after the punchline (a "3 hours later…" card, a callback, a loop back to the start) |

Measured failures to learn from: the silent Toon character sheet scored 5/20 and was retired as a comedy piece;
*Focus Mode* sat at 13 until it got its punchline and callback.

What worked: one escalating premise with a hard reversal at the end. In *Upside Down* the board is flipped, then
the scorecard reads "reception: taking notes". In *Five Years* the candidate wants the chair, not the job.
What fell flat: captions that explain the joke, and music fighting the lines. *Camera Off*'s lines sat 6–7 dB
under its score until `Episode.audio(duck=)` was added (ADR 0016). *Off and On*'s first cut was flat, and it only
landed after a funnier rewrite and a composed jingle.

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

Rules of thumb: one camera move per beat, never during a spoken line's key word; let a pause run a beat longer
than feels comfortable, then cut; a zoom without a payoff on screen is noise. Measure, don't assume: `srstudio craft`
<project> --renders <dir> lists every move (punch-in, crash, push; camera or gag) and every pause between lines, with
the rendered level in it, so a pause meant to be awkward is shown to be quiet and not filled by music. A push onto a drawn instance (a
reused symbol) softens it when magnified, so draw the target inline or keep the zoom small, and look at the frame.

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
| Which parts do episodes really use, and which are unused? | `srstudio usage --out ../generated/catalog/usage.json` (ADR 0017) |
| What does each part look like? | the catalog page, `catalogo-scene-render.html` at the workspace root |
| What is already planned? | `docs/backlog/` |

Pick the style whose description fits the joke, not the one used last.

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
2. **Script as data.** Write the beats as a table: time, picture, line, speaker, sound. Keep it 11–35 s; loops of
   12–15 s for a "repeat after me" format. Score it with the rubric. Avoid the premises and settings the usage report
   and the backlog show the catalog already leans on. Never copy a reference's lines, drawings or brand: an
   original script in the same format, an invented brand.
3. **Reuse first.** Build from registered parts and the shared pipelines: `srstudio.sketch` (Toon two-handers:
   speakers, lines, beats, `check`), `srstudio.takes` (voiced takes checked by speech-to-text, optional music `Bed`),
   `srstudio.song` (sung episodes on a beat grid with composed music), `srstudio.interview`, `srstudio.camera`,
   `subtitles.chunk_words`, `Episode.audio(duck=)`, `Episode.check_overlays`, `blob.cue`, `blob.settle`, and the
   polished rooms (ADR 0008, ADR 0011). Each style's own helpers are in its README section. For lip sync (ADR 0019),
   use `lipsync.SPEECH_MOUTH` with timestamped takes, or `soundtrack.OFFICE_MOUTH` with `letters=True` for mouths
   driven by amplitude. `srstudio.interview` gives exact line ends: put the reaction just
   after the last line, hold, then cut to the end card.
4. **Grow the library when it lacks something** (TDD, CLAUDE.md): a failing test first, then the part in
   `src/srstudio/`, registered with `register` so the catalog and usage report see it, then an ADR in
   `docs/decisions/` when it is a decision (new style, rig change, new pipeline). Never put a reusable helper only in
   an episode script (ADR 0016). Gates: `ruff format --check`, `ruff check`, `mypy src`, pytest with branch coverage
   ≥ 80 %, run with `SRSTUDIO_PACKAGES=../generated/packages SRSTUDIO_ENGINE=../generated/bin/scene-render`.
5. **Audio.** ElevenLabs premade voices only (no cloning), a distinct voice per speaker, one request per line,
   every take checked by speech-to-text, never a retry driven by model output; a misheard line stops the run and
   the operator decides. Takes cost money: reuse the cache rather than regenerating them. Music: ask for 120 BPM with "steady kick on every beat" (slow tempo prompts come back
   off-tempo and are refused). The API key comes from the environment; never print, copy or write it.
6. **Build and look.** Build with `srstudio build`, render to `generated/renders/<slug>.mp4`, then *look*: a
   contact sheet of frames, the hook frame, the punchline hold, the safe area, captions that fit. Run `srstudio craft`
   on the project with `--renders` and check that the planned camera moves and pauses are there. A number from a
   scratch file is not evidence; quote real command output. Then update the catalog: re-run the usage report
   from *Live inventory*, then `srstudio page --usage ../generated/catalog/usage.json` with the other arguments
   that `tools/systemd/srstudio-catalog.service` passes. The page build fails until every part the new episode calls has a
   gallery item in `docs/catalog/notes.json`; cut the still, look at it, then add the item.
7. **Instagram delivery.** Add an `InstagramPost` (title, description, credit, `Thumbnail`) to `POSTS` and the
   slug to `VIDEOS` in `episodes/instagram_posts.py`, then from the workspace root:

   ```
   SRSTUDIO_ENGINE=generated/bin/scene-render .venv/bin/python srstudio/episodes/instagram_posts.py \
       deliver generated/renders/ig generated/renders --fonts generated/fonts --only <slug>
   ```

   and the same command with `check` (exit 1 on drift). Open `cover.jpg` and look: a zoom that crops a card, or a
   frame caught mid-caption-fade, leaves a ghost. Credit voices as ElevenLabs premade voices and music as
   "composed with ElevenLabs Music"; credit a reference creator when the format is adapted.
8. **Publish.** A clean delivery is picked up by the `srstudio-drive` systemd unit and copied to
   `gdrive:srstudio/ready-to-publish` (video, `ig.txt`, `cover.jpg`, package). Run
   `python3 episodes/publish_drive.py --dry-run` to see it without waiting.
9. **Report.** The rubric estimate, the cast (and who is new), parts reused versus added, gates run with their
   output, anything skipped and why.

## Never

- Present your rubric score, a render you did not watch, or expected output as observed.
- Write scratch outside `srstudio/_tmp/`, or touch `protected/` or `authorial/`.
- Edit a file another session owns without asking it (`ListAgents`, `SendMessage`); commit only your own paths.
- Commit unless the operator asked; never lower a gate or skip a test to pass.
- Make a character's identity the punchline, or depict a real person or brand.
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
