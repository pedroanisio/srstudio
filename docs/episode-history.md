---
updated-by: OpenAI Codex (GPT-6)
---

# Episode history

[Library README](../README.md) · [Authoring task index](authoring-reference.md)

Historical episode and package implementations, grouped by style. For reusable SDK tasks, use the [authoring task index](authoring-reference.md). Existing releases retain their approved drawings and pins; these records do not replace current contract discovery.

Run commands from the srstudio repository root.

## New episodes with generated audio: *Five Years* (06)

[episodes/five_years.py](../episodes/five_years.py) is the first episode made on the library rather than ported to it.

```bash
python3 episodes/five_years_audio.py PROJECT --key-stdin < key   # resolve, speech check, trims, dialogue.json
SRSTUDIO_ENGINE=scene-render srstudio build episodes/five_years.py PROJECT   # scene + overlay check
scene-render encode PROJECT/five-years.scene.xml --strict         # renders/five-years.mp4
```

**Generated audio, resolved by the engine.** Every line and effect is a `<generated>` asset
(`srstudio.generated.Generated`) for the `srstudio-elevenlabs` provider ([src/srstudio/provider.py](../src/srstudio/provider.py),
console script `scene-render-provider-srstudio-elevenlabs`, or `SR_PROVIDER_SRSTUDIO_ELEVENLABS="python -m srstudio.provider"`).
`scene-render resolve` runs the provider for each stale item and pins the file's SHA-256 in the document; the
episode plays each pinned clip on its own `<audioTrack>` (`Episode.generated_audio()`, placements from the
`clips` of `dialogue.json`) and refuses a clip whose file no longer matches its pin. The provider parses the
resolve request strictly, needs `SRSTUDIO_ALLOW_CLOUD=1`, and writes nothing until ElevenLabs speech-to-text hears
the scripted line; a mismatch fails the item and asks for another `@seed`.

The interview episodes (06 and 09) share one audio pipeline, `srstudio.interview`
([src/srstudio/interview.py](../src/srstudio/interview.py)). An `Interview` lists its voices (`srstudio.song.Singer`),
its `Spoken` lines and its `Sound` effects, and is checked when made. The episode supplies a `schedule` (the start of
every line and effect from the trimmed clip lengths), refused when two lines overlap, an effect is missing or
unknown, or anything plays past the end card, and an `extra` that adds its beats and camera cuts from the `Timing`.

`srstudio.voice` treats the provider's output as untrusted. It parses dialogue, sound effects and speech-to-text
into typed values that reject unknown fields. It checks that the aligned characters spell the requested line,
that timings are finite and ordered, and that each clip is audible and as long as its alignment or its requested
length. Any violation raises `VoiceOutputError` and nothing is cached. Every uncached call is one request, never
retried; cached clips and transcripts are re-verified when read. `tests/test_voice.py`, `tests/test_provider.py`
and `tests/test_generated.py` feed malformed, truncated and adversarial responses and requests through each path.

**Safe area.** `EpisodeSpec(safe_area=srstudio.VERTICAL)` declares a `<safeArea>` with `enforce="error"` and makes it
the project's: the engine then fails validation and rendering when text or a caption leaves x 80–920, y 220–1420
(the engine's documented production box for 1080 × 1920; its platform presets are approximations). The engine does
not measure vector graphics, so `srstudio.layout.check_overlays(scene, ["squeak-loud", ...], engine=...)`
evaluates every frame, maps each drawn shape under the named groups through its world transform (exact bounds for
lines, quadratic and cubic curves and arcs, plus the stroke's reach) and reports every crossing; episode 06 runs it
with `strict=True` after `finish()`, as `ep.check_overlays(out, roots)` does with the engine that
`layout.find_engine()` finds (`--engine`, then `$SRSTUDIO_ENGINE`, then the `PATH`). Episodes 01–05 declare no safe
area and are unchanged. `ep.audio(extra=[music], duck=-8)` ducks every music track under the spoken lines.

**Symbols.** `Canvas.symbol(id, draw)` defines a symbol once and `Canvas.instance(parent, id, symbol)` places it
(ids inside are scoped `instance/inner`); `office_wide`/`office_desk(instanced=True)` share the room and the desk
that way. The engine draws an instance into an offscreen at its frame size and scales that texture, so an instance
under a camera push-in renders soft; episode 06 pushes in on its wide angle and therefore keeps the inline drawing.

Parts added for it: the `office-desk` location (the wide office without the foreground candidate; `chair=False`
leaves the chair to the slot), the `chair-back` prop, the `squeak-mark` graphic, and `camera.spin` with
`camera.show_facing` (a turn about the vertical axis, one `|cos|` key per frame, the far side swapped in at each
edge-on moment).

## Cutout episode with generated audio: *Tip Screen* (12)

[episodes/tip_screen.py](../episodes/tip_screen.py) brings Ava and Milo from episode 05 back to the café. Milo asks for
a black coffee, Ava swivels the tip tablet, and Milo sets down a tablet of his own: "how would you like to tip me for
ordering?" They tap "thirty" at each other until closing, and the scorecard nets it out at nothing.

```bash
python3 episodes/tip_screen_audio.py PROJECT --key-stdin < key   # srstudio.interview: resolve, speech check, timing
srstudio build episodes/tip_screen.py PROJECT                     # PROJECT/tip-screen.scene.xml
```

The dialogue (Liam and Jessica, ElevenLabs premade voices), the swivel, the second tablet and five taps are an
`Interview`; `schedule` lands each tap 0.05 s after the number it answers, and `TAPS` names whose tablet it lights
and which option. Parts added for it: the `tip-tablet` prop (`props.tip_tablet(cv, parent, x, y, heading=,
options=, picks=((time, index), ...), scale=)`: a stand, a heading, one button per option, the tiny "no tip", and
a lit overlay per pick that holds until the next one), and `Barista(..., name=None)`, which leaves the name tag
blank so a close-up carries no lettering out of frame (the default stays "AVA").

The episode declares no engine safe area: its close-ups reframe the menu board and the tablets out of frame on
purpose, which the SA01 text check refuses. Captions and cards are placed inside `layout.VERTICAL` by hand, the
contact sheet is checked by eye, and the cover variant hides the burned captions (`ep.hide_on_cover`).

## Cutout crossover in the park: *Culture Fit* (14)

[episodes/culture_fit.py](../episodes/culture_fit.py) seats Milo (episodes 05 and 09) next to the boss from the
interview series on a park bench. Milo has sent two hundred applications; the boss interviews a pigeon on his lunch
break, hires it, and explains why: "He works for crumbs." Milo makes a counter-offer.

```bash
python3 episodes/culture_fit_audio.py PROJECT --key-stdin < key   # srstudio.interview: resolve, speech check, timing
srstudio build episodes/culture_fit.py PROJECT                     # PROJECT/culture-fit.scene.xml
```

The dialogue (Liam and Eric, ElevenLabs premade voices) and six effects (a flutter, three coos, two notification
pings) are an `Interview`; `schedule` holds 1.3 s before the punchline and 1.2 s before Milo's answer. Parts added
for it: the `legs="seated"` performance extra on the office actors (trousers and shoes below the torso, drawn behind
it; without it nothing changes), `locations.PARK_SEAT_Y` with `locations.park_seat_y(bottom, scale)`, which seats
any actor on the bench, and the `crumbs` prop (`props.crumbs(cv, parent, x, y, ground, toss=, count=, seed=)`: a
handful that leaves the hand at `toss` and lands scattered on `ground`). The push notifications are the
`notification` graphic at 2.25×. Like *Tip Screen*, the episode declares no engine safe area (the park sign's
lettering sits right of x 920); captions and cards are placed inside `layout.VERTICAL` by hand.

## Cutout episode in the conference room: *Market Rate* (16)

[episodes/market_rate.py](../episodes/market_rate.py) brings back the candidate from the interview series, a year into
the job. Alone in the conference room, he asks the boss on the speakerphone for a raise and gets a title instead
("Does Senior pay more?" "It's longer."). Then his own job turns up online, paying more, for external talent only.

```bash
python3 episodes/market_rate_audio.py PROJECT --key-stdin < key   # srstudio.interview: resolve, speech check, timing
srstudio build episodes/market_rate.py PROJECT                     # PROJECT/market-rate.scene.xml
```

The dialogue (Will and Eric, ElevenLabs premade voices, as in the series) and four effects (a call chime, two pings
and hold music) are an `Interview`; `schedule` holds 1.25 s before "It's longer." and puts the hold music before the
last line. It is the first episode in `locations.conference_room`. The speakerphone's ring lights while the boss
talks and while his hold music plays (`conference_room(speaker_talk=)`, new and off by default). The job posting is
the `password-card` graphic, the endorsement the `notification` graphic at 2.25×. The episode declares
`layout.VERTICAL`, so the engine holds every caption and card inside the safe area.

## Cutout episode in the elevator: *Elevator Pitch* (18)

[episodes/elevator_pitch.py](../episodes/elevator_pitch.py) puts the employee from *Market Rate* in the elevator with the
boss: "Working from home? Elevator pitch. You've got till my floor." At floor 4 the doors open on Kevin, the pigeon
from *Culture Fit*, who is fully remote ("He negotiated. You took a title."). At floor 9: "Kevin, your call." Coo.

```bash
python3 episodes/elevator_pitch_audio.py PROJECT --key-stdin < key   # srstudio.interview: resolve, speech check, timing
srstudio build episodes/elevator_pitch.py PROJECT                     # PROJECT/elevator-pitch.scene.xml
```

The dialogue (Will and Eric, as in the series) and four effects (two arrival dings, two coos) are an `Interview`;
`schedule` opens the doors between the pitch and "Morning, Kevin." and holds 1.3 s before the coo that decides.
Parts added for it:

- `locations.elevator` (`elevator`): the cab seen from inside with the doors on the back wall. `riders` stand in front
  of them facing the camera and `on_floor` draws in front of the riders. `floors=((second, floor), ...)` drives a
  seven-segment display (`SEGMENTS`, no font needed), `doors=((open, shut), ...)` slides each door `DOOR_W` behind
  the wall over `DOOR_SLIDE` seconds onto a hallway, and `lit=` lights a button. Out-of-order floors or overlapping
  door spans raise `ValueError`.
- `legs="standing"` on the office actors (`OfficeActor.STANDING_LEGS`): trousers and shoes straight down, drawn
  behind the torso; `locations.elevator_stand_y(bottom, scale)` stands them on the cab floor. Without the extra
  nothing changes.

The pigeon is `cast.pigeon` in a walking group that comes forward through the doorway. The episode declares
`layout.VERTICAL`.

## Cutout crossover finale: *Going Down* (20)

[episodes/going_down.py](../episodes/going_down.py) closes the office series. Floor 9, going down. "Am I being fired?"
"No. Your role is being sunset." "So I'm fired." "You're going fully remote. From your couch. Forever." At floor 4
Kevin, the pigeon from *Culture Fit*, walks in with a pink slip in his beak: "He flew in for this. He's Head of People
now." The slip lands at the boss's feet, lettered ERIC. "Kevin... is my role being sunset?" A 1.3 s hold, then a
coo. The lobby, then the bench from *Culture Fit*: the two of them tossing crumbs to the pigeons. "What are we
doing?" "Networking."

```bash
python3 episodes/going_down_audio.py PROJECT --key-stdin < key   # srstudio.interview: resolve, speech check, timing
srstudio build episodes/going_down.py PROJECT                     # PROJECT/going-down.scene.xml, 29.8 s
```

The dialogue (Will and Eric, as in the series) and seven effects (two dings, three coos, the slip's slap, a flutter)
are an `Interview`; `extra` returns `park_start`, where the elevator's shots end and the park's begin, and each room
is reframed with only its own camera angles. Parts added or extended for it:

- `props.pink_slip` (`pink-slip`): a sealed pink envelope lettered `name=` (up to `SLIP_CHARS`; `None` shows its
  blank back), shown only in `show=(start, end)` (held in a hand or a beak) or falling `fall=(at, height)` onto its
  mark in `SLIP_FALL` seconds, tipping as it lands.
- `locations.elevator(going="down")` points the display's arrow down; the default stays `"up"`, byte for byte.

The episode declares no engine safe area, as *Culture Fit* does, because the park sign's lettering sits right of
x 920; captions and cards are placed inside x 80–920 by hand.

## Cutout episode at the café counter: *Cup Fee* (22)

[episodes/cup_fee.py](../episodes/cup_fee.py) brings Ava and Milo back to the café. "One black coffee. Three bucks."
Then a fee for the cup, the lid fee, a service fee ("for serving you") and, when Milo offers cash, a cash fee, each
a beep and a higher total on the card reader. "How much is the actual coffee?" "Oh, the coffee's free." "Then what
are the three bucks for?" "The coffee fee." The tip tablet from *Tip Screen* swivels round to him.

```bash
srstudio record cup-fee PROJECT   # srstudio.interview: resolve, speech check, timing
srstudio build cup-fee PROJECT    # PROJECT/cup-fee.scene.xml
```

The dialogue (Jessica and Liam, as in *Tip Screen*), four beeps and the swivel are an `Interview`; `schedule` lands
each beep 0.05 s after the line naming its fee and holds 1.3 s before "Oh, the coffee's free." Its first second is
still (arm A of the `sp-hook_motion` test): the two-shot keeps the espresso machine's steam out of frame and nothing
moves before the first line. Parts added or extended for it:

- `props.card_reader` (`card-reader`): a counter-top card terminal whose screen shows `readings=((time, amount,
  label), ...)`, a big amount (up to `READER_AMOUNT` characters) over a small label (up to `READER_LABEL`), each held
  until the next. The first reading is at 0 and still; each later one pops in about the screen's middle.
- `locations.cafe(menu=(coffee, pastry, footer))` letters the menu board's three lines under its title (up to
  `MENU_CHARS` each); without it the board is the shipped one, byte for byte.
- `locations.finish(cv, parent)`: an opt-in Cutout grade (`locations.FINISH`: a warm vignette and a soft bloom, no
  grain and no blur) on a group the episode draws its sets into, so camera moves stay inside it. A set drawn without
  it is unchanged.

Like *Tip Screen*, the episode declares no engine safe area (its close-ups reframe the menu board out of frame);
captions are placed inside x 80–920 by hand.

## Cutout episode on the park bench: *Storage Full* (23)

[episodes/storage_full.py](../episodes/storage_full.py) puts Milo on the park bench from *Culture Fit*. A pigeon walks
up the path and does a backflip. "No way. Do that again!" The phone: "Storage full." It offers fourteen photos of the
same sunset ("Still full."), then the wedding video. Milo and the pigeon look at each other. "...Yes." "Recording."
The pigeon flies off, and a message from his wife asks for the wedding video.

```bash
srstudio record storage-full PROJECT
srstudio build storage-full PROJECT    # PROJECT/storage-full.scene.xml
```

Its first frame already moves (arm B of the `sp-hook_motion` test): the pigeon is walking in and the camera pushes in
from the first key. It reuses `cast.pigeon` (nested in walk, flip and turn groups, the flip turning about the
mirrored rig's body centre), `graphics.notification` holders at 2.25 times for the phone, and `locations.finish` over
the park.



## Cutout episode across the interview desk: *Name a Number* (24)

[episodes/name_a_number.py](../episodes/name_a_number.py) brings the interviewer and the applicant from *Five Years*
back for the salary talk, where whoever names a number first loses. "So. What number did you have in mind?" "What's
the range?" "What would make you happy?" "What would make you happy?" "I asked first." "The ad said competitive."
"Extremely competitive." "Competitive with what?" "Other ads." They both write it down: the offer says LESS THAN
YOURS, the ask says MORE THAN YOURS. "Great. We're aligned." "Are we?" "Competitively."

```bash
srstudio record name-a-number PROJECT
srstudio build name-a-number PROJECT    # PROJECT/name-a-number.scene.xml
```

Its first second is still (arm A of the `sp-hook_motion` test): the job ad lies on the desk and the interviewer's
question is heard over it, its caption from 1.15 s. The desk inserts take one light from the top left, each sheet's
shadow falling down and to the right, and every angle is drawn into `locations.finish`. Extended for it:

- `locations.office_wide(depth=)` and `locations.office_reverse(depth=)` blur the room behind the desk (wall, art,
  plant) or the wall behind the chair by that many px in a group of its own; the desk, the cast and the signature
  marks stay sharp. `locations.elevator(depth=)` does the same for the hallway through the doorway, its cactus kept
  sharp. Without `depth` each set is the shipped one, byte for byte; an instanced office refuses it.

## Interview episodes with a Google caption face

An `Interview` takes an opt-in `font=GoogleFont(...)` (for example `interview.NOTO_SANS_BOLD`, Noto Sans 700, close
to DejaVu Sans Bold's width). The record step then installs that face with `srstudio.fonts.install` into
`PROJECT/assets/fonts` (pinned in `fonts.lock.json`, its licence beside it) before any clip is requested, and copies
no DejaVu file; a face that will not install stops the record with an `InterviewError` instead of falling back to
DejaVu. The picture script gives its `EpisodeSpec` the matching fields with `**interview.spec_font(face, root)`,
which reads the pin and never downloads. Without `font=`, the caption face is DejaVu Sans Bold as before, and every
published interview project rebuilds byte for byte.

## Cutout episode in the elevator: *Neighbor Names* (25)

[episodes/neighbor_names.py](../episodes/neighbor_names.py) puts the applicant from *Five Years* in the elevator with
Rosa, his neighbor of seven years, whose name he never learned. "Morning!" "Morning... you!" "Seven years in this
building, huh?" "Seven years!" "Can I ask you something I should know by now?" "Anything, dear." "Where did you get
that cardigan?" "I made it." Her name is stitched on it; his parcel's label says DEV 7C. The doors open on a third
neighbor: "Morning, Linda! Morning, Steve!" The doors shut. "Steve." "Linda."

```bash
srstudio record neighbor-names PROJECT
srstudio build neighbor-names PROJECT    # PROJECT/neighbor-names.scene.xml
```

Its first frame already moves (arm B of the `sp-hook_motion` test): the greeting is under way, his hand up and her
lean toward him, with no camera move. The voices are Lily (Rosa), Will and Eric; the captions are Noto Sans 700 (`interview.NOTO_SANS_BOLD`). Parts added or extended for it:

- `cast.Rosa` (`rosa`): an office-family actor with a grey bob, round glasses and a terracotta cardigan whose pocket
  has her name stitched over it (`stitch=`, 1 to `Rosa.STITCH` characters, default ROSA; `None` draws no text).
- `props.parcel` (`parcel`): a taped cardboard box with an address label, lettered by `label=` (1 to `PARCEL_LABEL`
  characters) or left blank.
- `locations.elevator(hallway=)`: a slot drawn in the hallway behind the doors and in focus, for someone waiting
  there while they are open; `depth=` blurs the hallway itself. Without either, the elevator is the shipped one.

The episode declares no engine safe area, as *Cup Fee* does: each close-up reframes the other rider's lettering out of
frame, which the SA01 text check refuses; captions are placed inside x 80–920 by hand.

## Cutout episode at the home printer: *Out of Cyan* (26)

[episodes/out_of_cyan.py](../episodes/out_of_cyan.py) sits Rosa at her desk with one black page to print and a printer
that reads LOW ON CYAN. "It's black and white." It answers in pages: a ransom note in cut-out letters, WE HAVE YOUR
DOCUMENT, then BRING CYAN. COME ALONE. She pays $64 at a shop till, and it wants OFFICIAL CYAN. She pays $89, and it
wants the magenta too, with an instant photo of her page tied to a chair. "Don't hurt it." She pays $98. The display
says THANK YOU, and her black page comes out blue.

```bash
srstudio record out-of-cyan PROJECT
srstudio build out-of-cyan PROJECT    # PROJECT/out-of-cyan.scene.xml
```

Its first second is a held frame (arm A of the `sp-hook_motion` test). The voice is Lily (Rosa); the printer never
speaks, and the long gaps between her lines are its whirs and pages, not silence. The captions are Noto Sans 700.

Rosa's card, for this and every later appearance:

- **wants**: to be treated with basic courtesy, by neighbours and by machines;
- **flaw**: she is too polite to refuse anything that asks nicely or threatens nicely;
- **habit**: she answers a demand with "dear" and then meets it.

Parts added for it, in `srstudio.cutout_home`:

- `desk_printer` (`desk-printer`): a home printer from the front; `lcd=` is timed readings of 1 to `LCD_CHARS`
  characters, `whirs=` are spans it rattles, `sheets=` slide out into its tray.
- `ransom_note` (`ransom-note`): a sheet whose `lines=` (1 to `NOTE_LINE` characters) are cut from magazines, each
  letter on a seeded scrap.
- `hostage_photo` (`hostage-photo`): an instant photo of a sheet of paper tied to a chair under one bulb.
- `paper_bag` (`paper-bag`): a very small carrier bag.
- `home_study` (`home-study`): a sage study with a window and an out-of-focus bookshelf; `behind_desk=` draws whoever
  sits there and `on_desk=` what stands in front of them. `desk_top` is the same desk from above, for inserts.
- `shop_till` (`shop-till`): out-of-focus shelves over a pale counter; `on_counter=` draws on it.

These six parts are recorded `proposed`: nothing draws them by default and no release can pin them until the operator
has approved them. `srstudio parts` shows such a part with `-` as its default.

## Cutout episode in the break room: *I'm Quitting* (27)

[episodes/im_quitting.py](../episodes/im_quitting.py) stands the applicant at the coffee machine, already mid-rant. "That's
it. I'm quitting. Today." His friend, eyes on his own mug: "Mm." The same shot, a new mug, a bigger plant, and the wall
board reads 2,190 days since "today". "This time I mean it." "Mm." Twelve years in, a planner lands on the counter. "You
said Friday." "Which Friday?" Every Friday in it is circled. "Twelve years of them." A banner, a gold watch. "Forty
years. Thank you." He taps the mic. "That's it. I'm quitting." The same mug: "Mm."

```bash
srstudio record im-quitting PROJECT
srstudio build im-quitting PROJECT    # PROJECT/im-quitting.scene.xml
```

Its first frame already moves (arm B of the `sp-hook_motion` test). Time passes on the props and not on the people: the
mug, the plant and the board. The voices are Will and Eric; the captions are Noto Sans 700. Parts added for it, in
`srstudio.cutout_office`, all recorded `proposed` until the operator has approved them:

- `drip_machine` (`drip-machine`): an office coffee machine; `pours=` are spans its stream runs.
- `office_mug` (`office-mug`): a mug in any colour, lettered by `label=` (1 to `MUG_LABEL` characters) or plain.
- `days_board` (`days-board`): a workplace-safety style wall board; `heading=` and timed `counts=` (1 to `BOARD_CHARS`
  characters).
- `wall_planner` (`wall-planner`): a planner page with every Friday circled around `note=`; `months=` flips its pages.
- `gold_watch` (`gold-watch`), `stage_mic` (`stage-mic`): a presentation watch with a `gleam=` time, a mic on a stand.
- `party_crowd` (`party-crowd`): the backs of an audience's heads out of focus; hands clap in `claps=`.
- `break_room` (`break-room`): a mustard wall, cupboards and a fridge out of focus, and a counter; `on_wall=`,
  `behind_counter=` and `on_counter=` draw at those depths.
- `office_party` (`office-party`): a dark teal function room with streamers; `banner=` hangs in focus, `stage=` draws
  under it and `front=` nearest the lens.

## Cutout episode in the hiring office: *Entry Level* (28)

[episodes/entry_level.py](../episodes/entry_level.py) opens on an interviewer and the ad on his desk: ENTRY LEVEL, 10 YEARS'
EXPERIENCE. "It's entry level, so just ten years." "I'm 22." "Have you tried starting earlier?" The desk bell brings a
crayon CV with small shoes swinging under it: "Been in the role since nursery." "Promising." Milo: "This software came
out in 2024." "We need twenty years in it." A crib, a CV over its rail: "I've been networking since the womb."
"Overqualified. We'd lose you." "Who actually got it?" The blind snaps up on Rosa at a desk in a paper hat that says
TRAINEE. "She's still on probation."

```bash
srstudio record entry-level PROJECT
srstudio build entry-level PROJECT    # PROJECT/entry-level.scene.xml
```

Its first second is a held frame (arm A of the `sp-hook_motion` test). The toddler and the baby are heard, in grown men's
voices (Brian and George), and never drawn. The other voices are Eric, Will and Liam; the captions are Noto Sans 700.
Parts added for it, in `srstudio.cutout_hiring`, all recorded `proposed` until the operator has approved them:

- `job_ad` (`job-ad`): a printed advert standing on a desk; `heading=` and two `lines=` of 1 to `AD_LINE` characters.
- `crayon_cv` (`crayon-cv`): a CV in crayon with a clip-on tie, two small hands on it and shoes under it; `swings=`.
- `crib` (`crib`): a slatted crib and mobile with a CV over the rail; `rattles=` shakes the rattle.
- `paper_hat` (`paper-hat`): a folded paper hat lettered by `label=` (1 to `HAT_LABEL` characters).
- `roller_blind` (`roller-blind`): a blind that snaps up at `snap=`, its cord dipping first.
- `hiring_office` (`hiring-office`): a slate wall and a poster out of focus, a glass wall onto `next_room=` behind the
  blind, a desk; `behind_desk=` and `on_desk=` draw at those depths.

## Cutout episode at the barber's: *Just a Trim* (29)

[episodes/just_a_trim.py](../episodes/just_a_trim.py) opens on Rosa in a barber's mirror, a lawnmower parked behind her and
a hedge trimmer on the shelf. "Just a trim, please." "Sure." A cape covers the mirror; a hedge trimmer is heard, then a
lawnmower. The barber steps in front of the glass: "Bit off the sides?" Hair falls past the lens in sheets. "...Sure."
The engine stops, the cloth drops, and the head in the mirror is not hers. Two seconds of nothing. "How's that?" The
face wobbles. "Love it." The card reader shows the cut, $22, then the tip, $30, and it stops there.

```bash
srstudio record just-a-trim PROJECT
srstudio build just-a-trim PROJECT    # PROJECT/just-a-trim.scene.xml
```

Its first second is a held frame (arm A of the `sp-hook_motion` test). Nobody's hair is redrawn: the cut is another
approved character in the mirror, with Rosa's voice and mouth. New parts live in
[src/srstudio/cutout_shop.py](../src/srstudio/cutout_shop.py): `barbershop` draws the people inside the glass with
`in_mirror=` and the shelf with `on_counter=`, and `barber_cape(spread=True)` is the cloth over the mirror.

## Cutout episode at the store: *Just One Thing* (30)

[episodes/just_one_thing.py](../episodes/just_one_thing.py) is already walking when it starts, with a very small basket: "I
only need light bulbs." The basket is a cart: a lamp, three candles, a plant. "We do need a plant." A bigger cart: a
ladder, a kayak. "It was on sale." Bigger again: a paddle, a life ring. "That's just safety." At the till the screen
says $412, then rolls on while the receipt runs down the frame, and Milo is proud of it. At home, in the dark, sitting
in the kayak, a dead switch goes click, click, click, nothing for longer than is comfortable, click, and it stops on
his eyes.

```bash
srstudio record just-one-thing PROJECT
srstudio build just-one-thing PROJECT    # PROJECT/just-one-thing.scene.xml
```

It moves from the first frame (arm B of the `sp-hook_motion` test). New parts live in
[src/srstudio/cutout_store.py](../src/srstudio/cutout_store.py): `store_aisle` slides its shelves with `drift=`,
`shopping_cart(contents=)` holds the goods behind its front wire, and `kayak(rider=)` seats someone in the cockpit.

## Ink episode: *The Router* (Ink 02)

[episodes/the_router.py](../episodes/the_router.py) is the first original Ink episode: the internet is down and the router
would rather be rebooted by hand. Twenty takes as a shot sequence (desk, human close, router on its shelf, wide).

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/the_router_audio.py PROJECT --font DIR   # voices, effects, timeline.json
python3 episodes/the_router.py PROJECT                                            # scene, SRT, ig.txt
scene-render encode PROJECT/the-router.scene.xml --out-dir OUT                    # OUT/renders/the-router.mp4
```

[episodes/the_router_audio.py](../episodes/the_router_audio.py) makes one request per take through `srstudio.voice`
(typed parse, alignment spells the line, audible, right length), confirms each voice id is the premade voice it names,
and requires ElevenLabs speech-to-text to hear every line as scripted; three interjections were respelled until it did.
Each verified clip is trimmed, levelled and conformed to one 48 kHz mono WAV per take under `audio/`, checked to the
sample, and `timeline.json` lists the takes with words and character timings relative to the take. The key is read
from `ELEVENLABS_API_KEY` and never written. Parts added: `talking-router`, `ink-hand`, `ink-router-shot`,
`ink-router-wide`.

## Ink episode: *Not a Robot* (Ink 03)

[episodes/not_a_robot.py](../episodes/not_a_robot.py): one form before lunch, and the captcha escalates from traffic
lights to sad traffic lights to "every moment you felt truly alive", fails the human for hesitating like one, and the
router welcomes him home. Fourteen takes through `srstudio.takes` (human, captcha and router voices), with the
screens as data in `SCREENS` ([episodes/not_a_robot_audio.py](../episodes/not_a_robot_audio.py)).

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/not_a_robot_audio.py PROJECT   # takes, checked by speech-to-text
python3 episodes/not_a_robot.py PROJECT                                # scene, SRT, ig.txt
```

`takes.Script(font=)` names the caption font (file, licence) a script ships with; it defaults to the takes font.
Parts added (`srstudio.ink_captcha`): `ink-captcha`, a verification card with a prompt band, a grid of drawn tiles
(`TILES`: lights, happy and sad lights, car, tree, laptop), timed picks with a tick and a verdict banner, and
`ink-checkbox`, the "I'm not a robot" box whose tick lands at `tick_at`. Bad tiles, picks or timings raise
`CaptchaError`. Burned captions are hidden on the cover (`hide_on_cover`).

## Ink episode: *Message Failed* (Ink 04)

[episodes/message_failed.py](../episodes/message_failed.py): a text about the boss goes to the boss. The router from
*The Router* drops the Wi-Fi so it fails, then retries it because it hates failing; the boss types, agrees, and the
router offers a reply. Fourteen takes through `srstudio.takes` (human and router voices, two effects), with the chats
as data in `SCREENS` and the router's power beats in `ROUTER_BEATS`
([episodes/message_failed_audio.py](../episodes/message_failed_audio.py)).

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/message_failed_audio.py PROJECT   # takes, checked by speech-to-text
python3 episodes/message_failed.py PROJECT                                # scene, SRT, ig.txt
```

Parts added (`srstudio.ink_phone`): `ink-phone`, a held phone with the contact in its header, `Bubble`s (mine in
ink on the right, theirs outlined on the left) that arrive at their second, a delivery status (`STATUS_TEXT`:
sending, not delivered, delivered, read) under the last of mine that changes on the shot's clock, and typing dots
that pulse in the slot their reply lands in; and `ink-phone-shot`, the phone over the desk line with the signature
cactus. A contact, bubble, status or typing span the screen cannot show, or a chat that does not fit, raises
`PhoneError`.

## Ink episode: *U Up?* (Ink 05)

[episodes/u_up.py](../episodes/u_up.py): two in the morning, the human from *The Router* has texted his ex. The router
will not unsend it: it does not fail any more, it has grown (a callback to *Message Failed*). She asks who this is,
then remembers the forty dollars, and the router has already paid them from his account, with a memo. Twelve takes
through `srstudio.takes` (human and router voices, two effects), the chats as data in `SCREENS`, under the contact
"Do Not Text" ([episodes/u_up_audio.py](../episodes/u_up_audio.py)). It reuses `ink-phone`, `ink-closeup` and the
router shots; no new parts.

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/u_up_audio.py PROJECT --font DIR   # takes, checked by speech-to-text
python3 episodes/u_up.py PROJECT                                           # scene, SRT, ig.txt
```

## Ink episode: *Premium Suction* (Ink 06)

[episodes/premium_suction.py](../episodes/premium_suction.py): the robot vacuum has stopped in the middle of the floor,
because its free trial ended. Suction is monthly, the kitchen premium, the corners platinum; what is free is the map
of the home, which it sells. The landlord texts: he saw the map, and rent goes up in May. He liked the second
bedroom, which is the closet. Deleting it is premium. Fourteen takes go through `srstudio.takes`: the human (Chris,
as in the earlier Ink episodes), the vacuum (Lily) and one effect
([episodes/premium_suction_audio.py](../episodes/premium_suction_audio.py)). The vacuum's moves and displays are data
in `VACUUM`, the map's in `MAPS`, the chat in `SCREENS`.

The new parts are in [src/srstudio/ink_vacuum.py](../src/srstudio/ink_vacuum.py):

- `vacuum` (`talking-vacuum`): a disc seen from above at three quarters. Its ring of lights chases and voice marks
  flicker while it speaks. `state` is `still`, `roll` (it rolls off through the take) or `stop` (it rolls in and
  brakes), and `display` puts a word of up to five characters on top. The side band carries the signature code.
- `vacuum_shot` (`ink-vacuum-shot`): the floor, the baseboard, the outlet and the dock, with the vacuum normal or
  close.
- `floor_map` (`ink-floor-map`): the app's map, with `Room`s outlined and named (`PLAN` by default). `trace=(start,
  end)` draws the route dot by dot, and `relabel=(room, label, at)` renames and shades one room at its moment.

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/premium_suction_audio.py PROJECT --font DIR   # takes, checked by speech-to-text
python3 episodes/premium_suction.py PROJECT                                           # scene, SRT, ig.txt
```

## Ink episode: *Home Sick* (Ink 07)

[episodes/home_sick.py](../episodes/home_sick.py): it is Monday, 2:14 PM, and the human is home early with sunglasses on
his forehead. His video doorbell will not let him in, because the resident is home sick today. He got better? Then
he is late for work. The doorbell asks the street's group chat who he is, from his own account: never seen him,
nope, and, after a hold, his boss: that's my employee. Face recognized, welcome home; the boss texts him, feeling
better? Nice tan. Thirteen takes go through `srstudio.takes`: the human (Chris), the doorbell (George) and three
message dings ([episodes/home_sick_audio.py](../episodes/home_sick_audio.py)). The face box's tags are data in `LENS`,
the doorbell's verdicts in `DOORBELL`, the chats in `SCREENS`.

The new parts are in [src/srstudio/ink_doorbell.py](../src/srstudio/ink_doorbell.py):

- `doorbell` (`talking-doorbell`): a tall rounded box with the lens, the speaker and the button. Its ring of lights
  chases and voice marks flicker while it speaks, and `mark=(verdict, at)` shows a cross (`deny`) or a tick
  (`allow`) on the button from `at`. It carries the signature code.
- `doorstep` (`ink-doorstep`): the siding, the front door with its panels, knob and deadbolt, the house number
  (`number=`, up to four characters), the mat and the signature cactus, with the doorbell beside the door, normal or
  close.
- `doorbell_view` (`ink-doorbell-view`): the doorbell's camera. The human is seen through a round lens with REC
  blinking, a FRONT DOOR strip with `clock=`, and a face box whose tag changes at each `(at, text)` of `tags=`.

`ink.human(shades=True)` pushes a pair of sunglasses up on the doodle's forehead; the default draws him as before.

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/home_sick_audio.py PROJECT --font DIR   # takes, checked by speech-to-text
python3 episodes/home_sick.py PROJECT                                           # scene, SRT, ig.txt
```

## Ink episode: *Pay to Park* (Ink 08)

[episodes/pay_to_park.py](../episodes/pay_to_park.py): the human holds a coin up to a parking meter whose slot is taped
over. Coins? How retro. The meter sends him through its app: download it, create an account (full name, email, shoe
size), choose a password with a capital, a symbol and a childhood memory. Biscuit. That memory is already in use.
Enable location; he is right in front of it. Minimum session two hours, rate your parking experience, and "Session
started!" as the tow truck lifts his car. The hold music stops dead as it drives off, and he says thank you. Fourteen
takes go through `srstudio.takes`: the human (Chris), the meter (Laura), two effects and a hold-music bed
([episodes/pay_to_park_audio.py](../episodes/pay_to_park_audio.py)). The app's screens are data in `SCREENS` and the
meter's readings in `DISPLAYS`; a cue there is a word of the take's line, resolved on the recorded words, or seconds
into the take. Take 06's `heard=("Biskit",)` is an operator-approved speech-to-text spelling (2026-10-29).

The new parts are in [src/srstudio/ink_meter.py](../src/srstudio/ink_meter.py):

- `meter` (`talking-meter`): a box on a post with a display whose reading changes at each `(at, text)` of
  `display=`, lights that chase and voice marks while it speaks, a QR code, and a coin slot taped over with
  `TAPE_TEXT`. Lettering that would draw under `LEGIBLE_PX` at the scale it is seen is a pen scrawl instead. It carries
  the signature code.
- `kerb` (`ink-kerb`): the pavement and the road from the side, with the doodle, the meter, the signature cactus and
  his parked car, or the meter alone (`close=True`). `tow=` brings a tow truck, already hooked on, that lifts the
  car's front by `LIFT_DEGREES` and drives off with it; a negative `tow` began before the take, so a cut carries the
  tow on. `view=` frames it: `KERB_VIEW`, `TOW_WIDE` (the default with a tow) or `TOW_TIGHT` on the car and the truck.
- `app_screen` (`ink-app-screen`): the held phone of `ink_phone` with a form on it. A title bar, `AppRow`s that
  arrive, tick or are refused (`taken=`: the row flips to ink with a cross and `TAKEN_TEXT`), a progress bar and five
  stars that light one after another.

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/pay_to_park_audio.py PROJECT --font DIR   # takes, bed, checked by speech-to-text
python3 episodes/pay_to_park.py PROJECT                                           # scene, SRT, ig.txt
```

## Soft style episode: *Focus Mode* (07)

[episodes/focus_mode_audio.py](../episodes/focus_mode_audio.py) declares seven sung lines and a record scratch as
`<generated>` ElevenLabs items. The engine resolves and pins them, speech-to-text must hear each line as written,
and each line is placed on its beat of `Groove(bpm=120)`. A line that would run into the next stops the build. The
script then synthesises the groove on the same grid: bars 0–5 play, bars 6–7 rest for the deadline, and the groove
creeps back in bars 8–9. [episodes/focus_mode.py](../episodes/focus_mode.py) places Pip's cues on that grid (typing on
eighths, sway, wiggle, hands-behind-head groove, freeze, a planted-foot side-step out of frame) with eased
in-betweens (four drawings before a beat, two before an eighth; the scratch cuts without any), arcs on sitting and
standing, overshoot on dance landings and a contact shadow, and burns the lyrics at the top in Poppins inside
the `VERTICAL` safe area. The audio script also pins the caption face with `fonts.install`.

```bash
grep '^ELEVENLABS_API_KEY=' .env | cut -d= -f2- | SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/focus_mode_audio.py PROJECT --key-stdin
python3 episodes/focus_mode.py PROJECT && scene-render encode PROJECT/focus-mode.scene.xml --output main -o "$PWD/focus-mode.mp4"
```

## Soft style episode: *Camera Off* (08)

Both sung Soft episodes share one audio pipeline, `srstudio.song` ([src/srstudio/song.py](../src/srstudio/song.py)). A `Song` lists its voices
by role, its `Line`s on (bar, beat), its `Effect`s, the groove `Section`s and where the last line must end. `main`
resolves and pins the items, checks each line with speech-to-text, places the lines and effects on the grid, renders
the groove, pins the caption font and writes `dialogue.json`. The refactor leaves episode 07's `dialogue.json`
byte-identical.

[episodes/camera_off_audio.py](../episodes/camera_off_audio.py) is the second song. It has ten lines in two voices:
Pip (Will) sings, and the boss (Eric) talks from the call. It also has a mouse click, a call chime and a groove. Polite
hat and keys play in bars 0–2, the whole groove in bars 4–7, and the meeting music returns in bars 10–11. The music
rests while the camera goes off and while the boss asks.

In [episodes/camera_off.py](../episodes/camera_off.py), Pip nods along on the beat (`nod`), clicks the camera off,
grooves, cheers (`cheer-a/b`) and waves at nobody (`wave-a/b`). He freezes on the chime, then scrambles back to type
on the eighths. A call badge over the laptop shows what the meeting sees: CAM ON, CAM OFF, SHARE?, SHARING. Boss lines
are captioned in blue. The video is 24.4 s.

```bash
grep '^ELEVENLABS_API_KEY=' .env | cut -d= -f2- | SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/camera_off_audio.py PROJECT --key-stdin
python3 episodes/camera_off.py PROJECT && scene-render encode PROJECT/camera-off.scene.xml --output main -o "$PWD/camera-off.mp4"
```

## Soft style episode: *Day Off* (11)

[episodes/day_off_audio.py](../episodes/day_off_audio.py) is an instrumental `Song`: six 4-second chunks composed at
120 bpm with no vocals, and Pip's six lines spoken by Will on the bar grid. Two effects sit on the grid with them: a
calendar ping and a meeting-ended chime. An earlier sung version failed its speech-to-text checks repeatedly.
Spoken lines over a composed bed passed on the first composition seed.

In [episodes/day_off.py](../episodes/day_off.py), Pip spends Saturday in `blob.home`. His hands keep typing on nothing
(seeded keyboard foley on the eighths), he nods along to the lamp, and he books a meeting with the sofa. The meeting
runs over and he extends it. The calendar is a `soft_props.status_badge`
([src/srstudio/soft_props.py](../src/srstudio/soft_props.py), graphic `soft-status-badge`): pill states that pop in
by span, one of them struck through (SOFA SYNC, ACCEPTED, ENDED, EXTEND?, EXTENDED). Two crash zooms
(`camera.push_in`, 0.2 s) land on Pip's face, on the invite and on the snap back to work. Each one cuts back to the
wide shot on a beat, and the frame drops 150 px while zoomed so the sprout clears the badge. The video is 24.4 s.

```bash
grep '^ELEVENLABS_API_KEY=' .env | cut -d= -f2- | SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/day_off_audio.py PROJECT --key-stdin --engine scene-render
python3 episodes/day_off.py PROJECT && scene-render encode PROJECT/day-off.scene.xml -o "$PWD/day-off.mp4"
```

## Soft style episode: *Unlimited PTO* (13)

[episodes/unlimited_pto_audio.py](../episodes/unlimited_pto_audio.py) is an instrumental `Song` with two speakers on
the bar grid: Bo (Eric, the boss of episode 08) and Pip (Will). It has three decline blips and an approval chime,
and a composed bed of six 4-second chunks: office-pop while Bo sells unlimited vacation, one held pad for the hold
before the punchline, and a steel-drum groove for the button.

In [episodes/unlimited_pto.py](../episodes/unlimited_pto.py), Bo is on screen for the first time, in the polished
`blob.meeting_room`. Every one of his cues is mirrored (`Cue(flip=True)`), so he faces Pip across the room. Pip
stands up from the swivel chair to ask (Friday, Friday afternoon, lunch) and drops back at each decline. The
request badge (`soft_props.status_badge`) shows each ask in amber, then DECLINED struck through in red, and finally
Bo's own "BO: BALI 3 WK" in green. Bo waves and walks out, and Pip types on. Bo's lines are captioned in blue. The
video is 24.4 s.

```bash
grep '^ELEVENLABS_API_KEY=' .env | cut -d= -f2- | SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/unlimited_pto_audio.py PROJECT --key-stdin --engine scene-render
SRSTUDIO_ENGINE=scene-render python3 episodes/unlimited_pto.py PROJECT && scene-render encode PROJECT/unlimited-pto.scene.xml -o "$PWD/unlimited-pto.mp4"
```

## Soft style episode: *Return to Office* (15)

[episodes/return_to_office_audio.py](../episodes/return_to_office_audio.py) is an instrumental `Song`: Pip (Will) and
Bo (Eric) on the bar grid, six effects (a call chime, a seagull, the call ending and three motion-sensor light
switches) and a composed bed in six chunks: office-pop for the welcome, steel drums for Bali, a held pad before the
punchline, almost nothing for the lights.

In [episodes/return_to_office.py](../episodes/return_to_office.py), Pip stands alone in `blob.meeting_room` on day one
back, and Bo calls in from a beach on the wall screen. The room takes the call through an opt-in slot,
`blob.meeting_room(on_screen=)`: `blob.meeting_screen()` gives the screen picture as a flat frame (its top-left, size
and the `skewY` that lays it along the back wall), and the slot draws into it, masked to the picture; without it the
slide is drawn as before. The call is the new `soft_props.beach_call` graphic (`soft-beach-call`: sky, sun, sea,
sand, a swaying palm, a `guest` slot and a name tag placed by `tag=`), with Bo's rig grooving inside it. Two crash
zooms land on the screen; the status badge tells the story (RTO: DAY 1, ON CALL, 312 WATCHING, CALL ENDED, NO
MOTION), and a dark overlay plays the motion-sensor lights that switch off on Pip, back on for a wave, and off
again. The video is 28.4 s.

```bash
grep '^ELEVENLABS_API_KEY=' .env | cut -d= -f2- | SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/return_to_office_audio.py PROJECT --key-stdin --engine scene-render
SRSTUDIO_ENGINE=scene-render python3 episodes/return_to_office.py PROJECT && scene-render encode PROJECT/return-to-office.scene.xml -o "$PWD/return-to-office.mp4"
```

## Soft style episode: *Smart Lamp* (17)

[episodes/smart_lamp_audio.py](../episodes/smart_lamp_audio.py) is an instrumental `Song` with three voices: Juno
(Laura), Pip (Will) and the smart lamp (Matilda), four effects (a wake-up blip, two order chimes and an error bloop)
and a composed bed in five chunks: a domestic sitcom groove for the argument, a shopping-channel bounce for the
orders, a held pad before the proposal and a short outro.

In [episodes/smart_lamp.py](../episodes/smart_lamp.py), Pip sits on the sofa in `blob.home` and Juno stands at the left.
The floor lamp is the third character through an opt-in slot, `blob.home(lamp_talk=)`: a list of `(start, end)`
spans, in order and apart (a `BlobError` otherwise), during which a halo, a lit shade and an orange rim glow; without
it the room is drawn as before. `blob.LAMP_SHADE` is the shade's point in the room, so the camera anchors on it and
pushes in at "She said yes." and at the last line. The status badge tells the story (LISTENING, + FLOWERS, + RING,
ENGAGED, PARDON?). The video is 30.4 s.

```bash
grep '^ELEVENLABS_API_KEY=' .env | cut -d= -f2- | SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/smart_lamp_audio.py PROJECT --key-stdin --engine scene-render
SRSTUDIO_ENGINE=scene-render python3 episodes/smart_lamp.py PROJECT && scene-render encode PROJECT/smart-lamp.scene.xml -o "$PWD/smart-lamp.mp4"
```

## Soft style episode: *The Cake* (19)

[episodes/the_cake_audio.py](../episodes/the_cake_audio.py) is an instrumental `Song` with three voices: Juno (Laura),
Pip (Will) and Bo (Eric), three effects (a party blower, a plate turned on the counter and a sad trombone) and a
composed bed in five chunks: an office sitcom groove for the collection, an office-party groove for Bo's entrance, a
held pad for the pause before the cake turns, the party groove deflated, and an outro.

In [episodes/the_cake.py](../episodes/the_cake.py), Juno and Pip are in the polished break room (`blob.break_room`) and
Bo glides in from the left carrying the cake. The cake is a new prop, `soft_props.cake`: a frosted round cake on a
plate with one candle and iced lettering (up to two lines of twelve characters) on the front. With `back=` and
`turn_at=` it turns half round on its plate (`CAKE_TURN`) and shows the back lettering. `lettering=` limits the
lettering to spans: the lettering is text, which the engine holds inside the safe area, so it shows only while the
cake is in frame. The camera cuts to the cake as Pip reads WE'LL MISS YOU, holds through the turn (BYE PIP) and the
trombone, cuts to Pip for his line and goes back wide. The video is 32.5 s.

```bash
grep '^ELEVENLABS_API_KEY=' .env | cut -d= -f2- | SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/the_cake_audio.py PROJECT --key-stdin --engine scene-render
SRSTUDIO_ENGINE=scene-render python3 episodes/the_cake.py PROJECT && scene-render encode PROJECT/the-cake.scene.xml -o "$PWD/the-cake.mp4"
```

## Soft style episode: *Hang Out*

The first Soft reel with no music: [episodes/hang_out_audio.py](../episodes/hang_out_audio.py) records through
`srstudio.interview` (Juno is Laura, Pip is Will, the old lines the same voices taken slower), and the build writes its
foley with `srstudio.foley`. [episodes/hang_out.py](../episodes/hang_out.py) is staged for a close shot in `soft_sets`,
frontal sets for a cast at about twice `blob.SCALE`: `soft_sets.park` takes `growth=`, so the tree between them goes from
a staked sapling to a crown wider than the frame while the town rises and the two-shot never changes. Its props are
`soft_props.phone` (held with `blob.held`, which rides a group between the hands), `soft_props.bench`, `soft_props.cane`
and `soft_props.time_card`, whose year flips on each cut. The video is 20.7 s.

```bash
srstudio record hang-out PROJECT   # the key from ELEVENLABS_API_KEY
srstudio build hang-out PROJECT && scene-render encode PROJECT/hang-out.scene.xml --out-dir generated --strict
```

## Soft style episode: *Early Night*

A narrator goes on announcing an early night while the hour card runs away from him. [episodes/early_night.py](../episodes/early_night.py)
is a bed seen from its foot, `soft_sets.bedroom`: rows of `Light` take the room from one flickering pool around a phone to
black and then to day, and rows of `Shot` cut in on everything but the nightstand, which keeps the signature marks in the
last frame, a single open eye. What is on her phone is drawn at full frame with `soft_props.shovel` and `soft_props.hive`.
The video is 17.1 s.

```bash
srstudio record early-night PROJECT   # the key from ELEVENLABS_API_KEY
srstudio build early-night PROJECT && scene-render encode PROJECT/early-night.scene.xml --out-dir generated --strict
```

## Soft style episode: *Why*

Five whys to the edge of what anyone knows, in [episodes/why.py](../episodes/why.py). `soft_sets.playroom` is a room straight
on, with a window of sky and a door; its `Shot` rows cut between one fixed close-up of Pip and a close-up of Bo that comes
in a little more each time, and `Dim` takes the light out of the room when he sits down. The first and last shots are the
same room with the sizes swapped, with `soft_props.necktie` and
`soft_props.briefcase`. The video is 20.0 s.

```bash
srstudio record why PROJECT   # the key from ELEVENLABS_API_KEY
srstudio build why PROJECT && scene-render encode PROJECT/why.scene.xml --out-dir generated --strict
```

## Cel style package: *Work Training Be Like*

The fourth style comes from the silent package `mushroom-training-2.0.0` (a recreation of an Under Studio
workplace-training cartoon: a mushroom at a desk, teal caption boxes with hand lettering, a slow camera push).
[episodes/mushroom_training.py](../episodes/mushroom_training.py) rebuilds its `scene.xml` element for element and its
SRT byte for byte from the package's own data: `script.json` (timed captions with their lettering boxes and glyph
paths), `assets/camera.json` and `assets/room-camera.json` (measured camera samples every 0.25 s), `assets/poses.json`
(which drawing is held when) and `assets/pose-NN.json` (the traced contours of each drawing). Nothing in the library
is specific to the mushroom: `cel.traced` holds any sheet of drawings, `cel.room` draws the set in any palette, and
`cel.lettering` draws any boxed glyph paths. The package's character art, dialogue and lettering are adapted from the
reference and remain their author's; the style, the loaders and the conventions are what the library keeps.

```bash
python3 episodes/mushroom_training.py /path/to/mushroom-training-2.0.0/project   # scene.xml, SRT, ig.txt, qa/
scene-render encode scene.xml -o /abs/path/mushroom-training.mp4                 # 1053 frames, 43.875 s, silent
```

### Narrated master

The silent build is the fidelity reference; a narrated master is the same scene with an ElevenLabs voice-over
(premade voice *Alice*) and keyboard foley on the mix. [episodes/mushroom_training_audio.py](../episodes/mushroom_training_audio.py)
reads the caption script and speaks each caption through `srstudio.voice` (typed parse, alignment check,
speech-to-text that must hear the scripted words, voice id confirmed by name) at the narrator's own pace: nothing
is asked again faster and nothing is time-stretched. `srstudio.narration.plan_relaxed` places the clips: a line
that outlasts its caption spills into the next, which waits for it (a 40 ms guard, at most 0.9 s after its own
caption, then the spilling line is cut instead); a montage fragment ("He...", "Lunch...") starts on its caption
and is cut where the caption ends, which is the joke; and the project is extended past the last caption so the
last line is heard whole. Three one-word fragments and the spelt-out score are spoken in a form the recogniser
can confirm (`SPOKEN`). Under the voice, `srstudio.foley` synthesises two to four keystrokes wherever the
package's tracked hand (`assets/poses.json`, sampled every 0.25 s) moves more than 8 px while on the keyboard
(poses flagged `raised` are skipped), seeded so the bed is reproducible; the keystroke onsets are written to the
manifest (`effects[].taps`) and the drawn keyboard sinks 4 px on the same beats.
The clips are conformed to 48 kHz mono under `audio/` and listed in `narration.json` with their placement, the
typing bed (`effects`), the extended `duration` and SHA-256s; `mushroom_training.py --voice` checks the manifest
and the hashes, holds the last drawing and caption to the extended end, and presses the keyboard: a traced
drawing's ink is one compound path whose holes are the coloured areas, so no limb can move on its own, but
`cel.Pressed` splits every fill's subpaths inside the keyboard box into what sinks (filled regions with the
holes they carry) and what stays (the ink frame), so the keyboard face and its key rows dip inside the frame on
each keystroke. It adds one dialogue track per clip and one effects track at −8 dB, and encodes with AAC
mastered by the Cel style's mix. The cloud step needs `SRSTUDIO_ALLOW_CLOUD=1` and `ELEVENLABS_API_KEY`; cached takes cost nothing.

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/mushroom_training_audio.py PROJECT   # audio/vo-NN.wav, narration.json
python3 episodes/mushroom_training.py PROJECT --voice                       # scene.xml with the 41 tracks
scene-render encode PROJECT/scene.xml -o /abs/path/mushroom-training.mp4    # h264 + aac, 43.875 s
```

## Stick style package: *Check With My Team*

The fifth style comes from the silent package `check-with-my-team-1.0.0` (a recreation of a `@theaifilmmaker`
cartoon: a stick figure at a laptop says they will check with their team, and the team turns out to be a person and
three AI assistants, stick figures with logo badges for heads, dancing in a garden).
[episodes/check_with_my_team.py](../episodes/check_with_my_team.py) rebuilds its `scene.xml` element for element and its
SRT byte for byte from the package's own data: `script.json` (timed captions with their sizes), `assets/poses.json`
(141 traced poses at 12 fps: the seated figure's legs, head and ink plates, or the dancers' measured head centres,
head angle, body and head plates), `assets/icons.json` (the badge drawings around their traced centres),
`assets/lettering.json` (the hook and headline as glyph plates) and `assets/foliage.json`. `stick.room` and
`stick.yard` draw the two sets, `stick.figures` holds one group per pose and puts a `stick.Badge` (a coloured face
with an icon drawing turned by the measured head angle) on every dancer but the leader, and `stick.hook`,
`stick.headline` and `stick.captions` letter it. The badge faces, their colours and the logos are the episode's data,
not the library's; the character art, dialogue and lettering are adapted from the reference and remain their
author's.

`--voice` builds the same picture as `scene.silent.xml` and dubs into `scene.xml` what
[episodes/check_with_my_team_audio.py](../episodes/check_with_my_team_audio.py) wrote: one ElevenLabs take cut at its
word boundaries and placed phrase by phrase on the captions (`srstudio.phrasing`), and an ElevenLabs Music song at
the dance's measured 152 bpm whose drop lands on the cut to the garden (`dub.beat_offset`, `dub.music_bed`). The
voiced scene ends at frame 230, where the package's recording starts over, so it loops without a repeat.

```bash
python3 episodes/check_with_my_team.py PROJECT --package /path/to/check-with-my-team-1.0.0   # verify and copy inputs
python3 episodes/check_with_my_team.py PROJECT                     # silent scene.xml + SRT, the fidelity reference
grep '^ELEVENLABS_API_KEY=' .env | cut -d= -f2- | SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/check_with_my_team_audio.py PROJECT --key-stdin
python3 episodes/check_with_my_team.py PROJECT --voice             # scene.xml with the voice and the music, 9.583 s
```

### An original Stick episode: *Screen Share* (R2)

[episodes/screen_share.py](../episodes/screen_share.py) is the first Stick episode drawn rather than traced
([ADR 0009](../docs/decisions/0009-stick-rig.md), [ADR 0012](../docs/decisions/0012-stick-looks-and-call.md)). Dev, a
`stick-rig` figure, sits in the `stick-room` through a video call that shares too much, a disconnect that comes just
in time, and a "got a sec?" on a Friday. `stick.rig` poses a figure from `RigKey`s, seated (`SEATED`) or standing
(`STANDING`), dressed by a `stick.Look` (hair, glasses, tie), placed, scaled or mirrored anywhere, and lip-syncs the
mouth to the take's phones: Dev keeps the default look, the boss stands in the room on Friday, bald, in glasses and a
tie. `stick.call` is the call: the boss's shared inbox above the captions, one row marked, and the participants'
tiles below. `stick.camera` cuts to a close shot or pushes in; `stick-card` letters each beat's hook in Inter; the
captions page the words (`subtitles.chunk_words`) with a width check, their outline drawn as a layer of its own
(`captions(outline="layer")`, or `"none"` over the call's dark screen) so the contrast check measures the white
against the ink: the encode reports no contrast warning. [episodes/screen_share_audio.py](../episodes/screen_share_audio.py) voices the nine lines with ElevenLabs and
keeps a take only when its transcript matches the script.

```bash
SRSTUDIO_ALLOW_CLOUD=1 ELEVENLABS_API_KEY=... python3 episodes/screen_share_audio.py PROJECT --font FONT_DIR   # takes + timeline.json
python3 episodes/screen_share.py PROJECT        # screen-share.scene.xml + SRT, 17.542 s
```

### An original Stick episode in a car: *Repeat After Me* (R3)

[episodes/repeat_after_me.py](../episodes/repeat_after_me.py) puts Dev behind the wheel on the drive home. He makes
the viewer repeat his vows to stop working after hours, until the passenger seat gives him away
([ADR 0018](../docs/decisions/0018-stick-car-and-voiced-takes.md)).

The car is `srstudio.stick_car`:

- `stick-car` is the cabin seen from the passenger door. The country passes the window in six parallax layers: the
  far ones out of focus under a haze, the near trees, poles, wires and guardrail motion-blurred by the engine. An
  oncoming car can pass on a cue (`passing=`).
- `DRIVING` poses put the hands on the wheel's rim.
- `stick-cockpit` draws over the figure: the knee panel, the wheel, a seatbelt per pose, the trees' soft shadows
  sweeping across the cabin, the sun and a vignette.
- `stick-ride` bobs the driver and the scenery on the suspension.
- `stick-car-seat`, `stick-laptop` and `stick-phone` stage the reveal.

Depth comes from the engine's effects, through `Canvas.effect`: blur, drop and inner shadows, screen and multiply
blending, and per-node motion blur.

The words come one at a time, as spoken (`stick.word_cues` + `stick-words`). The mouth uses
`lipsync.SPEECH_MOUTH` through `stick.rig(mouth=)`.

[episodes/repeat_after_me_audio.py](../episodes/repeat_after_me_audio.py) is a `srstudio.takes.Script`: seven lines in
the premade voice Will, a phone-buzz effect and an instrumental bed from the ElevenLabs Music API. Each take must be
heard as scripted, and the bed must hold no words and cover the episode. `screen_share_audio.py` uses the same
pipeline.

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/repeat_after_me_audio.py PROJECT --font FONT_DIR   # takes, bed, timeline.json
python3 episodes/repeat_after_me.py PROJECT     # repeat-after-me.scene.xml + SRT, 14.708 s
```

### An original Stick episode at the store: *Unexpected Item* (R4)

[episodes/unexpected_item.py](../episodes/unexpected_item.py): Dev buys one avocado at the self-checkout. The kiosk
wants it in the bagging area, calls it unexpected, wants it out, wants it back, and calls for help; the supervisor
reads his month off the screen and makes him employee of the month. He asks whether he gets paid, which is an
unexpected item too. On Saturday he wears the apron and says the kiosk's line to the next shopper.

The store is `srstudio.stick_shop`:

- `stick-checkout`: stocked shelves under strip lights, the hanging sign, a tiled floor and the bagging shelf
  (`BAG_SPOT`).
- `stick-kiosk`: the pedestal, the scanner bed and the screen. `Screen(start, text, tone, face=)` holds each message
  until the next, in a tone from `TONES` (idle, error, help, award; white lettering passes the 4.5:1 contrast
  check on every header), and an award shows a `Look`'s face. The lamp flashes red at each `alarm`. A schedule the
  screen cannot show raises `StickDataError`.
- `stick-avocado` and `stick-name-badge`. `hand(pose, at=, flip=)` finds where a placed figure's near hand carries
  an item; `SHOPPER_AT` and `CLERK_AT` (mirrored) stand `STANDING` poses either side of the counter.

`stick.Look(apron=)` dresses the torso in a shop apron under the tie; it is off by default, so earlier episodes
rebuild byte for byte. [episodes/unexpected_item_audio.py](../episodes/unexpected_item_audio.py) is a `takes.Script`
in three premade voices (Laura for the kiosk, Will, Alice), a scanner beep and a supermarket music bed, with the
screens per take in `SCREENS`.

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/unexpected_item_audio.py PROJECT --font FONT_DIR   # takes, bed, timeline.json
python3 episodes/unexpected_item.py PROJECT     # unexpected-item.scene.xml + SRT, 34.333 s
```

### An original Stick episode in a flat for rent: *The Viewing* (R5)

[episodes/the_viewing.py](../episodes/the_viewing.py): flat hunting, day 41. The kitchen has a toilet in it, the window
is painted on, and the bed folds down out of the wall with Gary asleep in it: he comes with the lease. Two grand a
month, each. Dev takes it and is applicant forty-seven; Gary, asleep, is forty-six.

The flat is `srstudio.stick_flat`:

- `stick-studio-flat`: the wall and floorboards, the counter with its stove, pot and tap, a toilet beside the stove,
  a window whose sunny view is painted on (the blue runs over the frame and drips), and the bed's cabinet. The set
  is `SET_W` wide, so a camera turns from the kitchen (`WINDOW_FOCUS`) to the bed (`BED_FOCUS`). Figures stand at
  `VIEWER_AT` and, mirrored, `AGENT_AT`.
- `stick-murphy-bed`: closed in the wall, folding down at `drop_at` through one mid frame (`FOLD`), and open on the
  floor with a `sleeper` under the blanket who snores and opens his mouth in each `talk` span. A timing the bed
  cannot show raises `StickDataError`.

The word captions take three options, off by default so earlier episodes rebuild byte for byte:
`stick.word_cues(size=)` letters the cues smaller so more quick words join a readable cue, `borrow=True` lets a cue
shorter than `min_seconds` take time from the next cue of its take, and `stick.words(scrim=)` darkens the band behind
the words over a bright set. With them the encode reports no legibility or contrast warning.
[episodes/the_viewing_audio.py](../episodes/the_viewing_audio.py) is a `takes.Script` in three premade voices (Will,
Lily for the agent, Callum for Gary), a bed-drop effect and a lounge-house bed.

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/the_viewing_audio.py PROJECT --font FONT_DIR   # takes, bed, timeline.json
python3 episodes/the_viewing.py PROJECT     # the-viewing.scene.xml + SRT, 25.125 s
```

### An original Stick episode at the gym: *Cancel Anytime* (R6)

[episodes/cancel_anytime.py](../episodes/cancel_anytime.py): Theo wants to cancel his gym membership. The sign says
anytime, with an asterisk: in person (he is here), on a Tuesday (it is Tuesday), before sunrise (it is still dark),
with a note from his trainer, whom he has never met. Any other way? A death certificate. Whose? They are flexible.
Then the sun comes up in the window, and Brooke at the desk sees him next week.

The gym is `srstudio.stick_gym`:

- `stick-gym`: the wall with the brand (`BRAND`), a poster, a dumbbell rack, a treadmill and mats, and a window on a
  night city. `gym(..., sunrise=)` keys the dawn layer and the sun over `DAWN` seconds from that moment in the shot;
  `sunrise=0` draws the day already up, and a time outside the shot raises `StickDataError`.
- `stick-gym-counter`: the front desk with a card reader, a cactus and a tent sign: the headline in `LETTER` red
  (contrast-checked) and a fine-print line that only reads in a close-up. A sign longer than `SIGN_CHARS` or fine
  print longer than `FINE_CHARS` raises `StickDataError`. Figures stand at `MEMBER_AT` and, mirrored, `STAFF_AT`.

`stick.word_cues(tail=True)` (off by default, so earlier episodes rebuild byte for byte) mends a take's last cue
when it is shorter than `min_seconds`: it joins the cue before it when the joined words fit the width, and otherwise
takes that cue's last words. It needs `min_seconds`. With it the encode reports no legibility or contrast warning.
[episodes/cancel_anytime_audio.py](../episodes/cancel_anytime_audio.py) is a `takes.Script` in two premade voices
(Callum for Theo, Jessica for Brooke) and a 120 BPM gym-pop bed.

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/cancel_anytime_audio.py PROJECT --font FONT_DIR   # takes, bed, timeline.json
python3 episodes/cancel_anytime.py PROJECT     # cancel-anytime.scene.xml + SRT, 27.208 s
```

### An original Stick episode at school: *What My Dad Does* (R7)

[episodes/what_my_dad_does.py](../episodes/what_my_dad_does.py): parent-teacher night. Dev perches on a child's chair,
knees above his hip, while the teacher reads his son's essay: Dad works from home, a tie on top and no pants; his job
is saying "I think you're on mute"; at three he has Focus Time, and Focus Time snores. Dev has an answer for each.
Last line: Dad says he works from home. Mom says he's just home. What did he get? An A. His mom helped.

The classroom is `srstudio.stick_school`:

- `stick-classroom`: the wall with an alphabet strip, a chalkboard lettered `board=` (up to `BOARD_CHARS`), the
  class's drawings pinned up, a clock and the linoleum floor.
- `stick-tiny-chair` and the `PERCHED` poses (`perch`, `perch-lean`, `perch-shrug`, `perch-point`, `perch-face`):
  a grown-up on a child's chair, the hip on the seat at `SEAT_Y` and the knees above it.
- `stick-teacher-desk`: the front layer at `DESK_X`, with marked papers, an apple and the cactus. The teacher
  stands mirrored at `TEACHER_AT` in `TEACHER_POSES` (`STANDING` plus `READING`: `read`, `lower`), and
  `held(pose)` is where the page in her hands goes.
- `stick-essay`: the child's page, its title and author, the first `shown` lines (up to `ESSAY_LINES`, each up to
  `LINE_CHARS`), a highlighter sweeping line `mark` over `SWEEP` seconds from `mark_at`, a circled `grade`, a margin
  `note` that appears at `note_at`, and the crayon drawing of Dad. A page that would run ahead of the reading, or
  letter more than it can hold, raises `StickDataError`.

[episodes/what_my_dad_does_audio.py](../episodes/what_my_dad_does_audio.py) is a `takes.Script` in two premade voices
(Will for Dev, Sarah for the teacher), one chalk effect and a 120 BPM pizzicato bed; `PAGES` says, per essay take,
how many lines are up, which is marked and the spoken word the highlighter starts on.

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/what_my_dad_does_audio.py PROJECT --font FONT_DIR   # takes, bed, timeline.json
python3 episodes/what_my_dad_does.py PROJECT     # what-my-dad-does.scene.xml + SRT, 32.417 s
```

### An original Stick episode at the airport: *Group 9* (R8)

[episodes/group_nine.py](../episodes/group_nine.py): gate B9. Sam asks if Group 9 is boarding. After the luggage; his
bag is Group 4, and it's doing great. An upgrade? Same seat, you just pay. The plane can't leave without him?
Everyone says that. He puts on the cap: he's the pilot, and pilots are Group 9. Button: row 38, between two
neighbours who own both armrests, this is your captain speaking from the middle seat.

The airport is `srstudio.stick_airport`:

- `stick-gate`: the window with the parked plane, a `NOW BOARDING` sign calling `now=` (up to `NOW_CHARS`) under
  the gate number `gate=` (up to `GATE_CHARS`), the waiting-room seats and the carpet.
- `stick-gate-podium`: the agent's podium at `PODIUM_X`, drawn in front of the agent standing mirrored at
  `AGENT_AT`; `plate=False` leaves its gate plate unlettered for a close-up whose caption band would cross it.
- `stick-carry-on`: a wheeled bag whose tag (`TAG_SPAN` from its middle) is lettered `tag=` (up to `TAG_CHARS`;
  `None` leaves it blank). Place it so the tag ends left of `PODIUM_X`, or the podium hides it.
- `stick-cabin` and `stick-armrests`: a row seen from the aisle, the row number `row=` and seat letters `seats=` on
  the overhead bins, seat backs at `SEATS` (`SEAT_STEP` apart); the armrests at `ARMRESTS` are drawn after the
  passengers so an elbow rests on them. `SQUEEZED` holds the seated poses: `tucked` and `tucked-up` keep both
  elbows between the armrests, `spread` takes the neighbouring one.

`stick.Look(cap=)` (a `#rrggbb` colour; `None`, the default, draws no cap) puts a peaked cap with a badge on the
head. `stick.word_cues(balance=True)` (off by default) splits each take where its shortest cue lasts longest within
the width limit, the fewest cues on a tie, instead of filling cues greedily from the left; it needs `width` and
refuses `tail`. [episodes/group_nine_audio.py](../episodes/group_nine_audio.py) is a `takes.Script` in two premade
voices (Liam for Sam, Matilda for the agent) and a 120 BPM airport-lounge bed; `NOW` says which group the sign calls
on each gate take, and `CAPPED` the take from which Sam wears the cap.

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/group_nine_audio.py PROJECT --font FONT_DIR   # takes, bed, timeline.json
python3 episodes/group_nine.py PROJECT     # group-nine.scene.xml + SRT, 25.625 s
```

### An original Stick episode in the car: *The Exit* (R9)

[episodes/the_exit.py](../episodes/the_exit.py): Dev has missed the exit, and he and Noor run their oldest argument in
shorthand. "Your sister's wedding." "Your mum's birthday." "The tent." "The tent." Dead air. "Sorry." "Sorry." Then
it dawns on them: they are not going to her sister's. Her sister texts; Noor puts the phone face down.

The car from the front is `srstudio.stick_windshield`:

- `stick-windshield`: the back layer seen from the hood, with the sky, the headliner, the rear window with the road
  receding behind the car (`speed=` dashes a second), the rear seat and the two front seats at `SEATS`.
- `FRONT` holds the seated poses, centred on x 540: `sit`, `drive`, `cite`, `crossed`, `reach` and `slump`. Place
  them with `stick.rig(at=PASSENGER_AT)` or `at=DRIVER_AT`.
- `stick-windshield-dash`: what lies between the camera and the couple. That is the wheel, the dashboard (its top at
  `DASH_TOP`) with the cactus, the phone in its mount buzzing at `buzz=`, put face down at `down=`, the glare, the
  wipers, the pillars and the hood with the code. The phone cannot buzz in its mount once it is down.
- `COUPLE` holds the couple's looks under their short names (`dev`, and `noor`: a bun and glasses).

[episodes/the_exit_audio.py](../episodes/the_exit_audio.py) is a `takes.Script` in two premade voices: Will for Dev,
as in R3, and Jessica for Noor. It has two effects and a 120 BPM car-radio bed, hushed (`gloss_reel.hush`) through
the dead air. It also holds the staging: `PARTS`, both figures' poses per take; `SETTLE`, the beat after a line
lands; and `CAMERAS`, framed as follows:
- the two-shot at 1.25× on the windshield;
- the singles at 1.7×;
- the face-down punch-in at 1.5×, with the phone down at `DOWN` and the cut back to the two-shot at `CUT`.

The word captions sit at `WORDS_Y`, over the hood.

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/the_exit_audio.py PROJECT --font FONT_DIR   # takes, bed, timeline.json
python3 episodes/the_exit.py PROJECT     # the-exit.scene.xml + SRT, 17.792 s
```

### An original Stick episode at a door: *Hold the Door* (R10)

[episodes/hold_the_door.py](../episodes/hold_the_door.py): Dev holds the door for a stranger far too far away, so the
stranger has to jog for it. Others overtake him, day turns to night, snow settles, a marathon passes. Years later the
stranger is three steps away when Dev's arm gives out.

The set is `srstudio.stick_door`:

- `stick-entrance`: the lobby and the street through its doorway, with a wall clock that runs and a street that
  darkens over the shot; `stick-street-lens` is the same street on a long lens, for close work on a runner.
- `stick-glass-door`: the pane on its hinge, held, swinging shut, or `closed`.
- `stick-snow-cap` and `stick-marathon`: snow in three sizes, and the silhouettes past the end of the street.
- `HOLD` and `JOG`: the poses of the arm that tires and of a run, with `shaking()` and `jogger()`; `on_path()`,
  `approach()` and `through()` put a figure on the path and behind the doorway.

`srstudio.stick_reel` holds what a recorded Stick reel repeats: `spec()`, the spoken `words()` and `close()`.

### An original Stick episode in a kitchen: *Take My Phone* (R11)

[episodes/take_my_phone.py](../episodes/take_my_phone.py): she hands her friend her phone and tells her not to let her
text him. Twenty seconds later she wants it back. The friend runs, sits on it, freezes it, locks it up and swallows
the key. She has already lifted the friend's own phone.

The set is `srstudio.stick_home`: `stick-kitchen` with its fridge and wall safe, `stick-table` drawn apart so figures
pass behind and in front of it, `stick-fridge-open` and `stick-safe-open` over the shut ones, `stick-handset` and
`stick-key` for the hands, `stick-reply-screen` for a message that takes the whole frame, and `POSES` for the argument.
The chase is `stick-kitchen-plan` and `stick-from-above`, straight down: two full figures crossing the frame again and
again fail the flash check, because each head's outline sweeps the same pixels more than three times a second.

### An original Stick episode at the coffee machine: *Good, You* (R12)

[episodes/good_you.py](../episodes/good_you.py): "How was your weekend?" "Good, you?" "Good." Every Monday, through a
cast, a neck brace, a parrot, a small fire and a headstone, and through the Friday a meteor lands outside the window.
Repeated lines are one recording, so the deadpan cannot drift.

The set is `srstudio.stick_office`: `stick-coffee-corner` with its window on the city, `stick-coffee-counter` in front
of the figures, and what the weeks leave: `stick-arm-cast`, `stick-neck-brace`, `stick-parrot`, `stick-flames` and
`stick-tombstone`, placed by `on_figure()`, with `stick-mug` and `stick-meteor` in the window's `view()`.

### An original Stick episode on the road: *The Stove* (R13)

[episodes/the_stove.py](../episodes/the_stove.py): Dev and Noor leave for the airport and turn back for the stove, for
the door, and for an iron they do not own. The sign says Airport 2. The neighbour ages, the tree grows, the children
grow up in the window, and in the last car she asks about the stove.

The car is `stick_windshield`, moving from the first frame. The rest is `srstudio.stick_street`: `stick-home-street`
with a tree that grows and a window (`in_window()`, `window_frame()`), `stick-side-car`, `stick-road-plan` and
`stick-top-car` for a U-turn from above with a skid mark for each one before it, `stick-stove-knob` and
`stick-door-lock` for what they came back to check, `stick-road-ahead` and `stick-road-sign`, and `stick-suitcases`.

## Toon style package: *Anonymous Employee Survey*

The sixth style recreates a the.nope.cat reel from a screen recording: a blue cartoon cat at a laptop answers an
"anonymous" employee survey out loud while each phrase appears in a white pill at the top of the frame.
[episodes/employee_survey_data.py](../episodes/employee_survey_data.py) is the reel as data: `SENTENCES` (what the
narrator records, one request each), `SEGMENTS` (every change of caption or expression at its reference time, each
spoken one naming the sentence and the word it starts on), `cues()` and `poses()` (which derive `script.json` and
`assets/poses.json` from the segments) and `place_segments()` (which moves the segments onto a narration).
[episodes/employee_survey.py](../episodes/employee_survey.py) draws it with the Toon parts: `toon.room` (a gradient
wall, the window, the chair back), `toon.cat` (one group per pose run holding a body traced from the recording for
the pose's arms, the eyes in one of nine kinds and the mouth in one of nine), `toon.desk` (the laptop lid and the
desk) and `toon.captions` (each cue in the style's font inside a pill measured with `fonts.text_width`). The cat's
drawings are packaged data (`assets/toon/cat.json`, schema `toon-cat/1.0.0`): a body per arm pose (`desk`, two
typing frames, `crossed`, `sigh`, `lean`, `face`, `face2`), eyes and mouths as closed cubic paths in the
reference's screen pixels, parsed by `toon.parse_art` (exact tables, finite coordinates, every expression present)
and mapped to the frame by `toon.fx`/`toon.fy`. While keys are heard the two typing bodies alternate
(`toon.typing_frames`, every `TYPE_SWAP` within a burst, back to the first frame between bursts), with opacity keys
on the composition clock (`toon.swap_frames`). The character, dialogue and captions are adapted from the reference
and remain their author's; the style, the loaders, the drawing conventions and the vocabulary (`EYES`, `MOUTHS`,
`ARMS`) are what the library keeps.

```bash
python3 episodes/employee_survey.py PROJECT --init    # script.json, assets/poses.json, Comic Neue Bold Italic pinned
python3 episodes/employee_survey.py PROJECT           # the silent master on the reference timing, 63.125 s
```

### Narrated master

[episodes/employee_survey_audio.py](../episodes/employee_survey_audio.py) records the 21 sentences through
`srstudio.voice` (premade voice *Brian*, typed parse, alignment check, speech-to-text that must hear the scripted
words, voice id confirmed by name) at the narrator's own pace, nothing quickened. Two sentences are interrupted by
the survey in the reference ("Do you have any feed—", "mark an X where you s—"): the whole sentence is recorded
and confirmed, then cut after the letter the reference cuts at, read from the character alignment. The lines are
placed by `srstudio.narration.plan_relaxed` on the reference's sentence starts, then the picture is moved to the
voice: a spoken segment starts where its word is heard, a silent beat (the sigh, the stare, the camera) a moment
after the line before it ends and no later than the next spoken segment, and a change that would cut a caption
short of 0.85 s waits for it, at most 0.45 s after its own word. `srstudio.foley` types only in the quiet windows of
the typing segments (`typing_bursts(speech=…)`, seeded bursts every 0.3 s, `SPEECH_MARGIN` clear of every placed
line, so no clack lands under a word) and the laptop's camera clicks on the flash; the keystroke onsets go into the
manifest and `toon.cat` swaps its typing frames on the same beats. The clips are
conformed to 48 kHz mono under `audio/`; `narration.json` lists them with their placement, the two effect beds, the
extended `duration` and SHA-256s; `voiced/script.json` and `voiced/poses.json` are the moved picture, and
`employee_survey.py --voice` builds from them after checking the hashes, with one dialogue track per clip, the
typing at −2 dB (peak-normalised to 0.70 before the gain) and the click at −3 dB, mastered by the style's mix. The cloud step needs `SRSTUDIO_ALLOW_CLOUD=1`
and `ELEVENLABS_API_KEY`; cached takes cost nothing.

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/employee_survey_audio.py PROJECT   # audio/, narration.json, voiced/
python3 episodes/employee_survey.py PROJECT --voice                        # the narrated master
scene-render encode PROJECT/employee-survey.scene.xml -o /abs/path/employee-survey.mp4   # h264 + aac, 63.6 s
```

### Toon sketches: *The Report* (T3), *Logo Bigger* (T4) and *Quick Question* (T5)

The coworkers' episodes are short comedies written as data and cut between the two characters
([docs/decisions/0015-toon-sketches.md](../docs/decisions/0015-toon-sketches.md)).
[src/srstudio/sketch.py](../src/srstudio/sketch.py) defines a `Sketch`: its `Speaker`s (an ElevenLabs premade voice
each and the Toon character one plays, or none for a voice heard on a speaker), its `Line`s (one request each) and
its `Beat`s (every change of caption, on-screen character, expression or prop event at its scripted time, a spoken
beat naming the line and the word it starts on). `check` refuses an inconsistent sketch; `cues` (the caption script,
each cue carrying its line's speaker so `toon.captions(tints=)` colours the pill by who speaks), `appearances` (one
stretch of one character on screen, its poses counted from its entrance) and `events` (`"toast:0"`,
`"clock:09:05"`, `"logo:2.3"`, `"pop"`, `"hangup"`) are what the build draws. `record` says every line in its
speaker's voice through `srstudio.voice`, confirms each voice by name, hears each take back with speech-to-text
(the run stops on any misheard line), places the lines at the speakers' own pace and moves the beats onto the heard
words (`place`); the placed beats are written to `voiced/beats.json` and read back typed by `load_beats`. The
same run turns each take's character timestamps into its character's viseme track (`visemes`, sampled at
`VISEME_RATE` over the part of the take that was kept, joined in order by `extend_track`) and writes
`voiced/mouths.json`, read back typed by `load_mouths` (known characters, known visemes, rising seconds within the
project).

[src/srstudio/toon_props.py](../src/srstudio/toon_props.py) holds the sets and props the sketches play with, all in
the style's reference pixels: `toon-meeting` (a mint room with a whiteboard where the window was), `toon-mug`
(steam in the spans asked), `toon-clock` (hour and minute hands that jump to each `(second, "HH:MM")`),
`toon-notes` (up to four sticky notes lettered on the laptop lid), `toon-toast` (a phone notification that slides
in and shakes with the buzz; `gated=True` letters the card only once it has landed, so a camera push never leaves
its lettering wholly off frame, where the strict encode's contrast check fails it), `toon-board-text`, `toon-logo` (a sun that scales about its centre to each asked
size over 0.3 s, `scale_keys`, with a drop shadow through a span) and `toon-badge` (the call status under the
pill). `toon_cast.sticky_note` and the `stickers=` parameter of `dog`/`frog` stick a note on a character's forehead
that follows its sigh and lean. `foley.buzz` and `foley.tones` (`STING`, `CHIME`) are the phone and the sting, as
deterministic as the keyboard.

[srstudio.toon_sketch](../src/srstudio/toon_sketch.py) is the build the Toon sketches share: `build` draws one gated
group per appearance (set and props behind the character, the character on its poses, the desk, the props in
front), tints the pills, refuses a caption too wide for one pill (`fit_captions`), checks that `voiced/beats.json`
and `narration.json` agree, draws the mouths from `voiced/mouths.json` (refusing one whose end differs from the
beats'), and adds the voices and effects; `record_episode` is the ElevenLabs run plus the
keyboard between the lines, a buzz under every toast and the sting on the hangup. Each sketch is a data module
with its `SKETCH`, a `validate` for what its events ask of the props, and a `dress` for its shots:
[episodes/the_report_data.py](../episodes/the_report_data.py) (Fern asks where the report is; Rex has never heard of
it; his own reminders buzz in; the notes and the one on his forehead have been there from the first frame;
"...What report?") and [episodes/logo_bigger_data.py](../episodes/logo_bigger_data.py) (a client on speaker wants the
logo bigger until it is the size of the building, then popping, then smaller; the original pops; "Invoice sent.")
and [episodes/quick_question_data.py](../episodes/quick_question_data.py) (T5 *Quick Question*: Pip the rabbit has a
quick question for Bruno the bear; first some context, March, then Dave; his clock jumps from 9:02 to 9:48 and his
coffee goes cold; the question is when the stand-up is, and it is on the board behind her; "Oh. Quick
follow-up."). *Quick Question* records with `record_episode(mouth=)` set to the Toon reading plus the English
spelling, closed bilabials, lead and bridged joins of `srstudio.lipsync`.

```bash
python3 episodes/the_report.py PROJECT --init                                # script.json, assets/poses.json, Comic Neue pinned
python3 episodes/the_report.py PROJECT                                       # the silent master on the scripted timing
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/the_report_audio.py PROJECT          # the recording: audio/, voiced/, narration.json
python3 episodes/the_report.py PROJECT --voice                               # the narrated master
scene-render encode PROJECT/the-report.scene.xml -o /abs/path/the-report.mp4
```

`logo_bigger.py`, `logo_bigger_audio.py`, `quick_question.py`, `quick_question_audio.py`, `whose_milk.py`,
`whose_milk_audio.py`, `out_of_office.py`, `out_of_office_audio.py`, `date_night.py`, `date_night_audio.py`,
`in_network.py`, `in_network_audio.py`, `split_it.py` and `split_it_audio.py` take the same arguments.

*Whose Milk?* (T6, [episodes/whose_milk_data.py](../episodes/whose_milk_data.py)) is the first sketch in the office
kitchen. Fern (Matilda) and Rex (Charlie) argue over the milk in the fridge, labelled Rex, 2019. The note on the
fridge escalates through `note:` events (WHOSE MILK?, IT MOVED., WHOSE YOGURT?). Each new note is cut in full frame
with `toon_sets.note_insert` for its beat, and the last one holds to the end as the button. Rex's coffee brews
behind him in every one of his shots.

*Out of Office* (T7, [episodes/out_of_office_data.py](../episodes/out_of_office_data.py)) brings Pip (Alice) and Bruno
(Bill) back, and it is the first sketch in the home office at night. Bruno is on vacation, out-of-office on. He has
answered every email to say so, personally. The tear-off calendar behind him loses its pages on `page:` events, only
in his shots. His boss's reply and, as the button, his own auto-reply arrive as `toast:` events, drawn larger with
`toon_props.toasts(size=)`. The desk lamp lights his laptop, and the plant stands in front of its glow, right of his
paws.

*Date Night* (T8, [episodes/date_night_data.py](../episodes/date_night_data.py)) takes the Toon home: Mae (a
rabbit, Sarah) is in the kitchen and Otto (a bear, Daniel) in the home office next door, on a video call. He has
sent her a calendar invite for dinner. Its agenda, her status as optional and, as the button, a shared spreadsheet
of apartments arrive on her phone as `toast:` events, and the fridge carries the date. The tear-off calendar
behind him jumps from OCT 29 to JUN 30 on the `page:` event of the punchline, the month their lease ends.

*In Network* (T9, [episodes/in_network_data.py](../episodes/in_network_data.py)) is a phone call to an insurer. Gil (a
frog, Chris) is in the home office at night; Dana (a dog, Jessica) is in claims, in the new call-centre cubicle
(`toon_sets.call_centre`), and wears the new headset sticker (`toon_cast.headset`). Is a broken arm covered? Which
arm? They cover the right. The claims arrive on his phone as `toast:` events. Her CALLS WAITING board climbs on
`tick:` events, only in her shots, and jumps to 999 in the hold before her punchline: try again in January, fresh
deductible. After the sting, his calendar jumps to JAN 1 and the button is the callback toast, a new claim.

*Split It* (T10, [episodes/split_it_data.py](../episodes/split_it_data.py)) is the end of a dinner. Brock (a bear,
Roger) wants to split the bill evenly; Mia (a rabbit, River) had a side salad and water, he had three lobsters and
the wine. It is the first sketch in the new restaurant (`toon_dinner.restaurant`), and its staging swaps the office
desk for the dinner table with the new `Staging(desk=toon_dinner.table)` option (the default stays `toon.desk`).
Each side of the table is laid with `toon_dinner.dishes`, and the card reader (`toon_dinner.card_reader`) changes
screen on `reader:` events: DECLINED for him, APPROVED for her. Her payment, his transfer of $6.50 and, as the
punchline, what it is for (half her salad) arrive on her phone as `toast:` events; the button is his last toast,
"Same place Friday?".

Two more staging options serve the opening A/B test (a still first second against a moving one). A sketch may open
on a silent, uncaptioned beat and caption its first line later: the build checks the caption script against the
sketch's first cue, not against second 0, so a still opening holds the frame unchanged until the first word. And
`Staging(camera=)` moves each shot: it is called with the dressed `Shot` (its beats are the ones drawn, scripted or
voiced) and the shot's group (set, character, desk and props; the captions stay still), and the group is named
`shot-NNN` so `srstudio craft` counts its moves as camera. Without it, shots keep their anonymous ids and every earlier sketch
rebuilds byte-identical.

### Toon dinner: the restaurant, the table, the dishes and the card reader

`srstudio.toon_dinner` draws the restaurant set in the Toon line. `restaurant(cv, parent, special=(dish, price))`
is the wall with a seascape, a lit sconce, wainscot, a leather banquette and a chalk SPECIALS board.
`table(cv, parent)` is a tablecloth that takes the desk's place in a sketch and carries the signature marks.
`dishes(cv, parent, items, id=)` lays `(kind, x[, at])` items (salad, water, lobster, shells, wine, glass, empty,
check), each appearing at `at` when given. `card_reader(cv, parent, states, at=, id=)` shows one screen per
`(start, text, tone)` state, with tones `idle`, `bad` and `good`. Bad data raises `ToonDataError`.

### Toon sets: the office kitchen and the home office at night

[src/srstudio/toon_sets.py](../src/srstudio/toon_sets.py) adds two backdrops and four props, drawn more finely than
the first sets ([ADR 0022](../docs/decisions/0022-toon-kitchen-and-home-sets.md)). Objects are inked with the brush,
so their outlines swell and taper like the characters'. Surfaces carry light: a highlight on glass, steel and
glaze, a soft shadow under each object, and glows drawn as radial gradients. Everything is placed in reference
pixels and keyed on the composition clock. Looping motion runs from 0 to `end` (`cycle_keys`) and is left out when
`end` is 0, so a still frame is the same either way.

| Part | What it is | Motion |
|---|---|---|
| `toon-kitchen` | butter wall, mint cabinets, subway tiles with a glint each, a counter at `COUNTER_Y`, a tall fridge with magnets | a `note=` (1 to `NOTE_MAX` = 14 characters) on the fridge door |
| `toon-home` | dusk-violet wall, a night window with a cratered moon, the city skyline, a gathered curtain, string lights, a bookshelf | stars twinkle, bulbs pulse, lit windows go out and come back, until `end` |
| `toon-coffee-machine` | a drip machine on the counter: carafe, coffee, steel glint | in each `brewing` span: the light blinks, drops fall, steam sways |
| `toon-desk-lamp` | an angled teal lamp at the desk's right, its head over the laptop | its cone and pool of light show in the `lit` spans (`None`: always on) |
| `toon-plant` | a terracotta pot with five glossy leaves; `at` and `scale` | the leaves sway until `end` |
| `toon-calendar` | a tear-off wall calendar in the clock's place | at each `(second, "OCT 28")` in `pages` the page above tears, tips and falls |
| `toon-note-insert` | a full-frame close-up of the fridge note, lettered at 128 px so it reads on a phone | shown from `start` to `end` under a slow push |
| `toon-call-centre` | a cubicle: a pale office wall, a flecked fabric partition, a YOUR CALL MATTERS poster, a CALLS WAITING LED board in the window's place | one count at a time from `waiting` (`(second, count)`, from 0, up to `WAITING_MAX`); the board's lamp blinks until `end`; `legible=True` letters the label lighter (`LED_LABEL`) so it passes a strict encode's contrast check |

The signature marks stay on `toon.desk`, which is in front of every Toon shot. The new sets draw neither mark, and
the defaults of the lamp and the plant stand clear of the desk's cactus. *Whose Milk?* uses the kitchen, the coffee
machine and the note insert.

`toon_cast.headset(look, mic=True)` (`toon-headset`) fits a headset to any brush-drawn look from its silhouette: a
band just over the crown, ear cups at eye height and a boom to a mic beside the mouth. It is a list of layers, like
`toon_cast.sticky_note`, passed to the figure with `stickers=` so it leans and sighs with the character.

### Toon rooms: a living room at night and a service counter, lit over time

[src/srstudio/toon_rooms.py](../src/srstudio/toon_rooms.py) adds two backdrops whose light a sketch drives
([ADR 0043](../docs/decisions/0043-lit-toon-rooms.md)). Each room has a main light and a screen. A light runs through
cues `(second, state)` from 0. The states are:

- `on` and `off`;
- `flicker`, a stutter that repeats until the next cue;
- `dim`, a fade to `DIM` over `FADE` seconds.

A screen's cue may also name a colour from `SCREEN_COLOURS` (blue, white, red, green, amber, purple). The colour holds
until a cue changes it. Cues are plain data:

```python
toon_rooms.dress(shot, "lounge", {"lamp": [[0, "on"], [4.5, "flicker"]], "tv": [[0, "on", "blue"], [3, "on", "red"]]})
```

The light shows on the sources themselves, in the set behind the character. It also reaches the character: a sketch
built with `Staging(lit=True)` gets a light layer in every shot, between the character and the desk. In that layer, a
shade multiplies the frame darker as the main light goes down, and glows add each light's colour over the
character's side of the frame. The desk, with the signature on it, is drawn after the light layer, so no light state
changes it. Tests render each state and compare the signature's pixels.

| Part | What it is | Lights and motion |
|---|---|---|
| `toon-lounge` | deep teal striped wall, a shelf above the pill with a router and the library's smart speaker (`toon-speaker` at scale 0.5), a floor lamp at the left, a wall TV over a media console, a plum sofa behind the character | `lamp` (main) and `tv` (screen, default blue); the router's lights blink until `end`; the speaker's ring follows `speaker=` (`(second, state)`, default off) |
| `toon-counter` | mint wall and wainscot, ceiling tiles with two fluorescent fixtures, a TAKE A NUMBER sign with its dispenser, a NOW SERVING board, an orange plastic chair | `tubes` (main) and `board` (screen, default red); the board shows one ticket at a time from `serving=` (`(second, "A17")`, from 0) |

`toon_rooms.ROOMS` names each room's lights, its defaults and the boxes its objects keep clear of the figure, the pill
and the desk. `toon_rooms.stage(cv, back, light, name, lights, end)` draws a room outside a sketch.

### Toon everyday props: the phone, the speaker, the receipt, the queue and the form

[src/srstudio/toon_everyday.py](../src/srstudio/toon_everyday.py) adds five props for everyday tech, money and
services, job search and dating ([ADR 0042](../docs/decisions/0042-toon-everyday-props.md)). Each stands at `at`
(reference pixels) and `scale` (0.9 to 2.0; the speaker, which carries no lettering, from 0.5), takes states keyed from 0 in rising seconds, and returns its
footprint. A footprint that leaves the frame, enters the caption band or touches `SIGNATURE_BOX`, the desk's
signature marks, raises `ToonDataError`, as does text that does not fit its box in the style's font (`measure=`,
the sketch's `Shot.measure`).

| Part | What it is | Motion |
|---|---|---|
| `toon-phone` | a phone, held (`hand=`) or set down, with typed `Screen`s: `notify`, `code`, `profile`, `declined`, `loading`, `off` | one screen at a time; a notification buzzes the phone; the loading bar fills to `fill` |
| `toon-speaker` | a smart speaker with a light ring and a halo | `off`, `listen`, `think` (a light chasing round), `speak` (pulsing), `error` (red), until `end` |
| `toon-receipt` | a receipt strip under a printer slot: a header, `(name, price)` rows, a total | unrolls from `start` at `pace` seconds a row; each row shows as the paper passes it |
| `toon-take-a-number` | a ticket dispenser on a pole under a NOW SERVING display, the customer's `ticket` in it | the display changes at each `(second, number)` |
| `toon-clipboard` | a form on a clipboard: a title and up to five `Field(label, value, at)` rows | each value is written in at its second; a `(second, text, tone)` stamp lands with a pop |

No episode draws them yet, so the catalog's notes need no gallery item for them.

### Lyra and Retro Orbit: flat print parts

[src/srstudio/toon_plate.py](../src/srstudio/toon_plate.py) draws a mid-century poster as brush shapes: `shape` turns an
absolute path into a closed `Shape`, `Frame` places a plate inside a part, and `clip` and `inside` stand in for a clip
path. A plate keeps its literal colours on any canvas palette.

[src/srstudio/toon_orbit.py](../src/srstudio/toon_orbit.py) adds two 9:16 locations, `planetarium_salon` and
`starlight_terrace`, and five props: `telescope`, `moon_globe`, `saturn_model`, `field_notebook`, `signal_clicker`.
Signs are live text in the two fonts of `Lettering`, Bebas Neue and DM Sans, installed with `fonts.install`; with no
`Lettering` they stand blank. `print_finish` is the one grain, and it fits `Staging.finish`. Neither set signs a shot,
so a reel there gives its shots a `Staging.desk` that does.

[src/srstudio/toon_lyra.py](../src/srstudio/toon_lyra.py) is `lyra`, an owl who presents astronomy. `MOODS` and
`EYE_POSES` are typed data; `pose(start, name)` writes a pose in either, and `mood()` and `eye_pose()` refuse an unknown
name. She is lip synced through her beak, and `LYRA_RIG` is her head rig, with `mood_plan` turning her head from mood
to mood. Her moods go through the rig, not through `toon_cast.figure`, which holds to the shared names.

Lyra and her rig are approved. The two locations and five props are proposed, so a reel cannot use them until they are
decided. The reasons and where the port differs from the pack are in [docs/decisions/0063-lyra-retro-orbit.md](decisions/0063-lyra-retro-orbit.md).

## Saga style: a space-opera parody in seven episodes (S1–S7)

The galaxy's grandeur is the setup; the turn is that it runs on the systems the viewer suffers at work, and a
deadpan field guide, the *Handbook*, gets the last word ([docs/decisions/0025-saga-style.md](../docs/decisions/0025-saga-style.md)).
Everything is original: no franchise names, characters, crawl or theme.

- **Cast**, [src/srstudio/saga.py](../src/srstudio/saga.py): Lord Gloom (a visor whose red glow is the mouth),
  Enforcer Seven and Gary (helmets with a mic light), Juno, Rook and Elder Mabel (visemes and blinks; Mabel has
  glasses and a cane), and a bar droid whose smile bar glows. Each figure is lit from the upper left: an inner
  shadow and a soft drop shadow (`saga.FORM`, `saga.LIFT`), drawn shadow sides, a gold rim and a contact shadow.
- **Sets and props**, [src/srstudio/saga_sets.py](../src/srstudio/saga_sets.py): space, bridge, cantina (with its bar
  as a front layer), desert, cockpit (with its console) and trash compactor; the hologram `holo`, the battle cube,
  a freighter, a fighter, a pebble; the hook card and the Handbook `entry`. Each location blurs its far plane by
  `DEPTH_BLUR` and keeps the floor, the cast and both signature marks sharp; `finish` grades a shot with `GRADE`.
- **Staging as data**, [src/srstudio/saga_reel.py](../src/srstudio/saga_reel.py): one `Stage` per recorded take
  (set, `Place`s, panels, props, a `Move`, blackouts, shakes, or an `Entry`). `check` refuses a staging that does
  not fit the recording before anything is drawn; `build` draws it, hooks the first take, crossfades into the
  entry, captions and mixes.

An episode is two files: `episodes/saga_<name>_audio.py` (its takes and stages; run it to record through
`srstudio.takes`, every line heard back by speech-to-text, no retries) and a three-line `episodes/saga_<name>.py`
that builds it. `tests/test_saga_episodes.py` holds all seven to the format: the narrator's hook question first, a
hold of at least 1.2 s before the button, the Handbook entry last, and a staging that fits at other speaking rates.

| # | Episode | The turn |
|---|---|---|
| S1 | *Known Issue* | the battle cube's fatal hole sat in the backlog for nine years |
| S2 | *Annual Review* | an enforcer who never hit anything is enforcer of the year |
| S3 | *Group Chat* | the big reveal was already in the family group chat |
| S4 | *Card Reader* | a smuggler meets the tip screen |
| S5 | *Update* | mid-chase, the jump drive installs an update |
| S6 | *Free Tier* | the energy that binds the galaxy, on the free plan |
| S7 | *Open Plan* | the compactor walls closing in are a workspace upgrade |

S13 *The Code* (the weapon's two-factor code went to the phone on the target planet) and S14 *Take-Home* (an
unpaid interview task is launched as the station that rejected her) use the opt-in switches of the ADR's
2026-10-30 amendment: a `still` opening shot that holds every frame of the first second, and `fade` panels and
entries whose text passes the strict encode. S15 *Call Juno* (the smart speaker calls the dark lord instead of
the granddaughter, and he gets mothered), S16 *Travel Notice* (the most feared man in the galaxy has his card frozen
over a coffee and washes dishes), S17 *Typing* (from the next seat, "we need to talk", then a typing indicator; it
is about snacks) and S18 *Friday Deploy* (one tiny fix at five on a Friday, and the only one who can roll it back
is on leave) use them too; S15's desert darkens under the captions with the second amendment's `shade` switch.

## Gloss style: a cheerful forever-plaza in nine episodes (G1–G9)

The relentless cheer is the setup; the turn is that it is a system you cannot leave, only rate, score and wait in,
narrated by a calm orb host in the deadpan of a facility announcement while a Joy Points board scores every small act
([docs/decisions/0030-gloss-style.md](../docs/decisions/0030-gloss-style.md)). Everything is original: the Plaza,
Sunny, the guests and the Joy Points are the library's own.

- **Cast**, [src/srstudio/gloss.py](../src/srstudio/gloss.py): glossy vinyl peg dolls Nadia (a NEW sticker that
  peels), Gus (a wind-up key that unwinds) and Tamsin (a spring base that bounces), and Sunny, a floating orb with
  a screen face that scans and wears a tie as the manager. Faces and poses are tracks on the shot's clock; the vinyl
  is rounded from each silhouette (`gloss.FORM`, `gloss.RIM`) with gradient highlights (`gloss.haze`) and seated by
  contact shadows. `gloss.LIFT`, a soft drop shadow, is applied only by `gloss.finish(..., lift=True)`, which no
  shipped part calls.
- **Sets and props**, [src/srstudio/gloss_sets.py](../src/srstudio/gloss_sets.py): the Plaza, the Activity Room and
  the Waiting Room (far planes softened by `DEPTH_BLUR`, lettering in strokes, a caption shade at the foot of the
  frame); the Joy Points `board` of `Card`s, the painted-on `door`, the queue `ticket`; the `hook` card and the
  Plaza `notice` that buttons each reel. `finish` grades a shot's world with `GRADE`; the board and the notice card
  stay ungraded and crisp. A `Card(carried=True)` stays on across a cut without popping again.
- **Staging as data**, [src/srstudio/gloss_reel.py](../src/srstudio/gloss_reel.py): one `Stage` per recorded take
  (set, `Place`s, cards, props, one camera `Move`, shake, blackout, or a `Notice`), checked against the takes before
  anything is drawn. The music ducks `DUCK` dB under every line and a further `HUSH` dB through every pause between
  lines (`hush`), so the hold before a punchline is quiet; the camera is the `gloss-<take>-angle` group, which
  `srstudio craft` reports.

An episode is two files: `episodes/gloss_<name>_audio.py` (its takes and stages; run it to record through
`srstudio.takes` via `episodes/_gloss.py`, every line heard back by speech-to-text, no retries) and a short
`episodes/gloss_<name>.py` that builds it. `tests/test_gloss_episodes.py` holds every reel to the format: Sunny's
hook question first, a hold of at least 1.2 s before the button, the Plaza notice last.

**A still opening.** A reel may open on a still first second (arm A of the `sp-hook_motion` test) with
`Reel(still=1.0)`. The recording (`takes.Script.still`) puts that much silence at the head of the first take, so the
first word comes after it and the timeline still runs contiguous from zero. The build then holds the first shot and
the hook on their first frame until then: it draws a copy of each inside `Canvas.frozen()`, where every key keeps
only its value at 0 s, and shows the running shot from the first word on. `gloss_reel.still_opening` refuses a
staging that would change the shot inside the still second (a card, move, blackout, shake, walk, face or pose
before the first word) and a notice as the first shot; a frozen drawing refuses expressions and text animators, which
it cannot hold still. Without `still`, recordings and builds are as before. Two other designs were rejected. A
timeline that starts its first take late breaks the contiguous-from-zero rule every take timeline keeps. An output
segment that freezes the first frame would make the encoded file a second longer than the scene whose clock the
captions, markers and craft checks read.

**Captions from G8 on.** G8 and later caption in `gloss_reel.LOOK_INK`: the lines wrap and hold as in
`gloss_reel.LOOK`, in solid dark letters (the sung word too) outlined thinly in their own color. The engine's contrast
check compares the pixels a caption changes most with the set behind them. A white letter in a dark outline lightens
some of those pixels and darkens the others, and on the light Gloss sets that averages to 1.00:1, so the strict encode
refused the house look (the published *Terms* fails it the same way under the current engine). A centered outline
passed but filled the white letters in, and a plum sung word measured under 3:1 on the notice's darker floor. G1–G7
keep the looks they shipped with. A reel that runs long can ask for its own encoder quality, `Reel(crf="20")`, over
the series output, to keep its master under the size cap; *Fewer Meetings* does.

| # | Episode | The turn |
|---|---|---|
| G1 | *Orientation* | the exit is painted on, and it arrives "in a future update" |
| G2 | *Joy Points* | points can be redeemed for more points, and the balance does not roll over |
| G3 | *Trust Exercise* | nobody catches anyone; catching was not in the budget |
| G4 | *Feedback* | the guests' complaint about the plaza is answered with more plaza |
| G5 | *Exit* | behind the exit door is a waiting room, and waiting is the attraction |
| G6 | *Wellness* | the manager is the same orb in a tie; wellbeing is the top priority, ranked fourth |
| G7 | *Terms* | declining the terms is added to the terms; real is also premium |
| G8 | *Fewer Meetings* | the meeting about fewer meetings schedules more; meetings are reduced to one, this one, and it does not end (opens still) |
| G9 | *Notifications* | saying no to notifications is a notification; turning them off is coming soon, and you will be notified |

## Collage style: grown-ups losing to brainrot

Paper cut-out people on painted sets give up their dignity to *BOWLHEADS*, an invented kids' show starring Flush,
a singing porcelain toilet. The style is decided in
[docs/decisions/0026-collage-style.md](../docs/decisions/0026-collage-style.md). The series bible (the world, the family at its centre and a card per character) is
[docs/decisions/0036-collage-series-bible.md](../docs/decisions/0036-collage-series-bible.md).

- **Cast and sets**, [src/srstudio/collage.py](../src/srstudio/collage.py) and
  [src/srstudio/collage_sets.py](../src/srstudio/collage_sets.py): ten characters as data (`collage.LOOKS`, drawn by
  `collage.DRAWERS`), twelve painted rooms (`collage_sets.SETS`), and the paper sign, chart and TV props.
- **The build**, [src/srstudio/collage_sketch.py](../src/srstudio/collage_sketch.py): a `Staging` per episode turns a
  sketch's beats into one shot per appearance, with crash zooms, the sting, Kai's beep, lip sync and tinted
  caption pills. `Staging.cast` decides who is drawn in a shot. `Staging.still` holds the first shot still for
  that many seconds (the `sp-hook_motion` test's still arm): no grain, and `Staging.opening` draws its cast keying
  nothing (`collage.figure(still=True)`). `Staging.bitrate` sets the master's average video bitrate, encoded in
  two passes (the rate factor alone, as published, by default).
- **Camera-safe zooms and call buttons**: `collage_sets.zoom_pivot` moves a zoom's pivot off a face only as far as
  keeps the set's whole signature in frame; `collage_sets.call_buttons` turns a shot into the far side of a video
  call.
- **Group shots**, [src/srstudio/collage_group.py](../src/srstudio/collage_group.py): `Lineup` puts several of the
  cast on one set, each in a fixed `Place`, the listeners holding their reactions while the speaker plays its
  beats; outside its spans it draws the speaker alone.
- **The family photo's props**, [src/srstudio/collage_photo.py](../src/srstudio/collage_photo.py): the self-timer
  on a stack of books, the viewfinder's countdown, the sofa front, the flash and the printed photo.
- **Everyday props**, [src/srstudio/collage_everyday.py](../src/srstudio/collage_everyday.py): food, a phone with a
  screen the scene writes on, message bubbles, a bedside clock, a cereal box, a duvet and a tablecloth, a salt
  shaker, chip bags and chips, a certificate, a snapshot, a gust of air, walking bills, confetti that can turn and
  fall back up, an arm on its own, a thumbs-up, and `chew`, which keeps a mouth working while a character eats.
- **A change of room and the extra sounds**: `Staging.setting` picks a shot's set from the beats (a reel that moves
  from the sofa to the bed), and rows can start on a later word of a line, `(line, word, caption)`. Beats also take
  `swat`, `ding`, `crunch` and `hiss:<seconds>`, written by `sound_effects` from `srstudio.foley`.

An episode is `episodes/<name>_data.py` (the lines, the timed beats and the `Staging`), `episodes/<name>.py`
(the build) and `episodes/<name>_audio.py` (the ElevenLabs recording, every line heard back by speech-to-text, no
retries). Its release is `episodes/posts/<name>.py`.
