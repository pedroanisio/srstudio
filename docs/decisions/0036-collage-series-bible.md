---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0036: The Collage series bible, its group shot, and the cast cards of the reels batch

- Status: accepted; implemented 2026-10-29 (`srstudio.collage_group`, `srstudio.collage_photo`,
  `srstudio.stick_windshield.COUPLE`; `tests/test_collage_group.py`, `tests/test_collage_photo.py`,
  `tests/test_stick_windshield.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md); uses the tags of [ADR 0033](0033-episode-tags-for-analytics.md)

## Context

Twelve Collage sketches are published. The cast and the world they share live only in the episodes'
data files and in `srstudio.collage.LOOKS`. A look's one-line summary says what a character looks like, but not
what the character wants or how it fails. A writer starting a new sketch has to reread old ones to keep a
character consistent. The funny-reels skill (1.9.0) asks for a card per recurring character: a want, a flaw and a
habit.

The Collage build also drew one character per shot. A family photo, three people on one sofa in one framing, could
not be staged.

The same batch brings back the Ink doodle and introduces a Stick couple. Release tags ([ADR 0033](0033-episode-tags-for-analytics.md))
name recurring characters by short name. Neither style recorded those characters anywhere a tag could point to.

## Decision

### The world

- **Grown-ups losing to brainrot.** Every Collage sketch is about adults who give up their dignity to the kids'
  show *BOWLHEADS*. Its star is Flush, a singing porcelain toilet with a paper head. The show and Flush are the
  library's own invention.
- **Mixed media.** Paper cut-out people with hand-cut edges and drop shadows stand on painted, slightly blurred
  sets. Every line appears in a tinted pill, and each character has its own ElevenLabs premade voice
  (`collage_sketch.SPEAKERS`), the same in every episode.
- **One family at the centre.** Rosa is Gary's mother. Kai is Gary's son and Rosa's grandson (*The Will*: "To my
  son Gary", "Grandma?").

### The cards

| Character | Wants | Flaw | Habit |
|---|---|---|---|
| **Gary** | Kai's respect | Earns it through Kai's toilet show, which he now likes more than Kai does | When ignored, performs a bit nobody asked for, usually Flush's voice |
| **Rosa** | The family to turn out properly | Demands dignity while enjoying everyone's humiliation | Can't resist a cutting line even when she's already winning |
| **Kai** | To be left alone, and to look grown up | A kids'-show beep rules him | The headset beeps and takes him away at the worst moment |
| **Flush** | To be loved by everyone | Has no idea he's a toilet | Sings through any serious moment |
| **Brent** | To own the next big thing | Rebrands what he doesn't understand | Turns every problem into a slide |
| **Jun** | To be taken seriously as an artist | Makes the toilet show | Explains his work to anyone, unprompted |
| **Omar** | To keep the news serious | Slides from panic to engagement on air | Reads the next line whatever it says |
| **Priya** | Her students to read real books | Grades everything, even at home | The red pen comes out mid-sentence |
| **Deb** | A grown-up evening | Dates people with Kai's show in their lives | Keeps smiling while she plans her exit |
| **Dr. Feld** | To have heard everything | Has not, until now | Writes it down before reacting |

Only the Gary, Rosa and Kai cards are tested against a script in this batch (*The Family Photo*). The other cards
come from the looks' summaries and the published sketches' premises. A sketch that contradicts a card changes the
card in the same commit.

### The group shot

- **`collage_group.Lineup`** is what a `collage_sketch.Staging.cast` returns. That casting is called with the beats
  the build draws, scripted or voiced. A recording re-times every beat, so an episode makes its lineup's spans and
  reactions from the beats' events, not from fixed times. Inside its `spans` the lineup draws every placed
  character, each scaled into its `Place` (centre line, the bust's cut-off bottom, and a scale), at the same place
  in every shot. The cut from one speaker to the next therefore keeps the room and the family where they were.
- The speaker plays its own beats. The others hold `reactions`, which are poses on the project clock, so a
  listener reacts while someone else talks. A crash zoom anchors on the speaker's face in its place.
- Outside the spans the lineup draws the speaker alone, exactly as the default `solo` does. A staging can
  therefore mix group shots and singles. The default path rebuilds every published Collage release byte for byte.

### The family photo's props

- **`collage_photo`** holds:
  - the phone propped on books, counting its self-timer down;
  - the same countdown in the phone's viewfinder over the group shot;
  - the sofa front the seated busts sink into;
  - the flash;
  - the printed photo, a still of the lineup in its room. Each character holds one pose (no breath or blink),
    named subjects are blurred, and the image is cropped to the camera's framing inside a paper border.

### The other recurring characters of the batch

| Character | Style, where recorded | Wants | Flaw | Habit |
|---|---|---|---|---|
| **The doodle** (`doodle`) | Ink, `ink.human` | To get one small thing done today | Is polite to machines that are not polite to him | Does whatever a device asks |
| **Dev** (`dev`) | Stick, `stick_windshield.COUPLE["dev"]` (`stick.PLAIN`, the R3 driver) | To be the reasonable one | Argues by citing history | Can't let a point go |
| **Noor** (`noor`) | Stick, `stick_windshield.COUPLE["noor"]` (a bun and glasses) | An easy life | Picks fights to get out of things | Always says the quiet part |

A release's `Tags.recurring` uses these short names: `gary`, `rosa` and `kai` are `collage.LOOKS` keys, `dev` and
`noor` are `COUPLE` keys, and `doodle` names the Ink human.

### The still opening, the camera-safe zoom and the call buttons (2026-10-30)

- **A still first second.** The reel batch of 2026-10-30 tests a still first second against a moving one
  (`releases.Tags(test="sp-hook_motion", arm="a")`). A Collage shot is never still: the figure breathes and blinks,
  and the paper grain (`film-grain`) is drawn afresh every frame. `Staging.still` makes the first shot a still: it
  draws no grain, and `Staging.opening` (by default `collage_sketch.stilled`) draws its cast with
  `collage.figure(still=True)`, which keys no breath, blink or lip sync. `collage_sketch.check_still` refuses a
  still opening that is not one silent shot, without caption or event, ending on a cut no earlier than `still`.
  The build checks it on the scripted and on the voiced beats. Grain-free for one second is the price; keying the
  grain's amount was rejected because the grain is one shared effect definition.
- **A zoom keeps the signature.** `collage_sets.zoom_pivot(set, face, scale)` returns the face when a zoom on it
  keeps the whole signature box in frame, otherwise the nearest pivot that does. A set whose shelf is on the right
  needs the figure moved right in its shots for the zoom to land on the face.
  `Staging.keep_signature` applies it to every zoom of a reel, with the shelf above the caption pill; published
  reels leave it off and stay as they landed.
- **A smaller master.** The paper grain changes every frame, so a Collage master at the published rate factor (17)
  runs to 40–58 MB, and still to 29–35 MB at a rate factor of 25. `Staging.bitrate` sets the video's average
  bitrate, encoded in two passes, so a master's size follows its length; the batch of 2026-10-30 sets 5.8 Mbit/s
  (17.6 MB for 23.5 s) to stay under the posting job's 20 MB. Rejected: a higher rate factor alone, which did not
  bound the size; and a one-pass cap (`maxBitrate`, 5 Mbit/s), which starved the first keyframe, so a still opening
  sharpened frame by frame and drifted 0.55–0.75 from its first frame, failing the still arm's limit of 0.5, where
  two passes hold it at 0.09–0.46. The default is the rate factor alone, so every published reel rebuilds byte for
  byte.
- **Video calls.** `collage_sets.call_buttons` draws a call's mute, hang-up and camera buttons, without lettering,
  so a shot reads as the far side of a video call.

## Rejected alternatives

- **A group-shot build loop of its own.** It would duplicate `collage_sketch.build` (the shots, zooms and
  captions) and drift from it. A cast hook keeps one build, and its default is proven identical on the published
  episodes.
- **Scaling the existing single shot to fake a group**, i.e. three solo appearances in split screens. A split
  screen breaks the photo's single framing. That framing is the joke: the print shows the same frame the
  viewfinder showed.
- **The print as a rendered still of the scene.** The engine renders a whole frame, not an asset the scene can
  place. Drawing the lineup again as data (`collage.figure_shapes`) keeps it vector and deterministic, and lets
  one subject be blurred.
- **Cards in the skill or in memory only.** The skill is shared across styles and memory is not in the
  repository. An ADR is versioned with the cast it describes.

## Consequences

- A new Collage sketch can put several of the cast on one set: `Staging(cast=casting)`, where
  `casting(beats, end)` returns a `Lineup`.
- The `timer` and `flash` events mark the self-timer's start and the shutter. The build makes the shutter's sound
  on `flash`, and an episode times its countdown and flash from the two events.
- Cards are binding for new sketches. A deliberate change to a character changes its card here, with a reason.
- The Stick couple and the Ink doodle have short names that analytics can count across styles.
