"""The Meshing Hypothesis — a pilot of "There's a Name for That", main trigger reversal: the sketch as data.

A hedgehog highlights the last row of a page that is already all yellow. "I'm a visual learner." A cat asks what it
says. "It's important." A fourth-grade quiz told her so, and many of us were told the same. There's a name for that,
and its last word is the point. Her preference is real; what it tracked was how learning felt, not what was recalled.
Four researchers looked for fair tests and found no adequate evidence base. Not disproved: a later meta-analysis found
a small benefit its authors would not build on. Then the book shuts, the cat asks again, and she answers from memory.
The one row she writes down gets highlighted, and this time "It's important." is true.

Text on screen carries every key point, for a muted viewer. The narrator is the channel's voice, ElevenLabs premade
Bella; the two characters are ElevenLabs premade Jessica and Laura. ``SKETCH`` is checked by
:func:`srstudio.sketch.check`; :func:`validate` checks the events and every word on screen against
:func:`srstudio.mind_kit.check_copy`; :func:`dress` draws each shot and :func:`foley` its sound.

Every claim traces to ``pilots/mind/learning-styles/sources.md``, whose rows are named beside each one below. Pashler
et al. was read from its abstract only, and the card's words stay inside that abstract: no page goes on screen. The
reel never says disproved as a finding, matching does nothing, or that everyone was told this.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from srstudio import camera, mind_kit, scripting, sketch, toon_sets, toon_study
from srstudio import foley as synth
from srstudio.mind_kit import CARD, STAGE
from srstudio.sketch import Beat, Line, Sketch, Speaker
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail
from srstudio.toon_house import ledge
from srstudio.toon_study import HIGHLIGHT, PINK
from srstudio.voice import Voice, VoiceSettings

SEED = 3105
SLUG = "learning-styles"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "The Meshing Hypothesis — There's a Name for That"
NAME = "The Meshing Hypothesis"  # sources.md claims 1 and 5: the review's own phrase, "the popular meshing hypothesis"
DESCRIPTION = (
    "A pilot about how people think: a hedgehog highlights a whole page because she is a visual learner, and the idea "
    "behind that is named, shown and tied to one review of the evidence."
)
ACCESSIBILITY = (
    "A cartoon hedgehog highlights the last row of an open book whose every row is already yellow, and says she is a "
    "visual learner. A cat asks what it says. She says it's important. An old school quiz reads mostly A's, visual, "
    "with a gold star, then four smaller sheets lie side by side. A card reads There's a name for that, The Meshing "
    "Hypothesis, and the last word is underlined. A lens tagged your style slides over a file marked how it felt, "
    "which lifts, then over a file marked recall, which stays. A paper card sums up one review, and a line below says "
    "not disproved. The hedgehog shuts the book and answers the cat from memory. The book opens on one written row "
    "and she highlights it."
)
NARRATION = "Voiced with ElevenLabs premade voices Bella (narrator), Jessica and Laura; synthesised effects."
NOTE = "ElevenLabs premade voices Bella, Jessica and Laura at their natural pace; no reference-voice cloning."

# Pashler et al. 2008: full text not accessed, abstract only (PMID 26162104); sources.md claims 2, 4 and 6. The one page
# confirmed is p. 105, for claim 4, and only by Rogowsky et al. 2020 quoting it.
REVIEW = mind_kit.Evidence(
    "Pashler, McDaniel, Rohrer & Bjork",
    "2008",
    "Looked for fair tests of teaching to your style. Very few existed.",
    '"No adequate evidence base" for using it in general teaching.',
)
# Clinton-Lisell & Litzinger 2024, abstract and Discussion, full text; sources.md, Replication status. g = 0.31 is the
# abstract's figure and the one the caption prints; its Results section gives 0.32.
CAVEAT = (
    "Not disproved.",
    "A 2024 meta-analysis found",
    "a small benefit, but",
    '"too small and too infrequent"',
    "for widespread adoption.",
)
BELIEF = "89.1% of educators surveyed believed it too."  # Newton & Salvi 2020, abstract and Results; weighted
# educators, not the public; sources.md claim 12
FELT, RECALLED = "How it felt", "Recall"  # Knoll et al. 2017, abstract; sources.md claim 8

NARRATOR = mind_kit.NARRATOR
HOG = Speaker(
    "hog",
    Voice(role="hog", id="cgSgspJ2msm6clMCkdW9", name="Jessica"),
    VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.35),
    "hedgehog",
)
CAT = Speaker(
    "cat",
    Voice(role="cat", id="FGY2WhTYpPnrIDTdsKH5", name="Laura"),
    VoiceSettings(stability=0.60, similarity_boost=0.75, style=0.15),
    "cat",
)
TINTS = {"hog": mind_kit.SPOT, "cat": mind_kit.SPOT, "narrator": mind_kit.INK}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VERSIONS = {"toon-hedgehog": 2, "toon-cat": 1}
FIGURES = {"hedgehog": (1.35, 0.0), "cat": (1.0, 0.0)}

ROWS = toon_study.BOOK_ROWS
LAST_ROW = ROWS - 1
ALL_YELLOW = {row: (PINK if row in (3, 10) else HIGHLIGHT) for row in range(ROWS) if row != LAST_ROW}
PAGE_MARKS = {row: (PINK if row in (2, 6) else HIGHLIGHT) for row in range(toon_study.SHEET_ROWS)}
PAGE_KEY = ((HIGHLIGHT, "important"), (PINK, "very important"))
PAGE_HEADING = "Chapter 4: Plants"
ANSWER = ("Plants make", "food from light.")
QUIZ_TITLE = ("What kind of learner", "are you?")
QUIZ_RULE = "Mostly A's:"
QUIZ_RESULTS = ("VISUAL", "AUDITORY", "HANDS-ON")
LANDED = (  # one sheet becomes four: no sheet covers another's words
    ((300.0, 715.0), -3.0),
    ((745.0, 735.0), 4.0),
    ((305.0, 1235.0), 3.0),
    ((745.0, 1245.0), -4.0),
)
QUIZ_AT = (510.0, 985.0)
LAND_SCALE, LAND_FROM, LAND_STEP = 0.5, 0.5, 1.0  # seconds after the line widens to many of us, and between sheets
BOOK_AT, BOOK_SCALE, SHUT_SCALE = (292.0, 812.0), 1.0, 0.8
DESK = "#3a2a22"
PAW = "#c49a6c"
SHELF_Y = 1180.0
LENS_Y, LENS_R = 1098.0, 92.0  # low on the files, so a label is never under the glass
FILE_X = (315.0, 765.0)
LENS_REST = 150.0
LENS_TAG, TAG_SIZE = "Your style", 38.0
SHELF_LABELS = (FELT, RECALLED)
UNDERLINE = "#a3301a"
PUSH = 1.08
MARKER_CLEAR = 36.0
FIRST_SWEEP = 0.25
SQUEAK: tuple[synth.Glide, ...] = ((2300.0, 2900.0, 0.16), (2900.0, 2500.0, 0.2), (2500.0, 3000.0, 0.16))
THUD: tuple[synth.Glide, ...] = ((120.0, 60.0, 0.14),)

LINES = (
    Line("hog", "I'm a visual learner."),
    Line("narrator", "Fourth time through this page."),
    Line("cat", "What's it say?"),
    Line("hog", "It's important."),
    Line("narrator", "A fourth-grade quiz told her so."),
    Line("narrator", "Many of us were told: teach to your style, you learn more."),
    Line("narrator", "There's a name for that."),
    Line("narrator", "The meshing hypothesis."),
    Line("narrator", "Note the last word."),
    Line("narrator", "Your preference is real."),
    Line("narrator", "In one study, it tracked how learning felt."),
    Line("narrator", "Not what people recalled."),
    Line("narrator", "Four researchers looked for fair tests. Their verdict: no adequate evidence base."),
    Line("narrator", "Not disproved: a 2024 analysis found a small benefit, too small to adopt."),
    Line("narrator", "Test yourself instead of rereading."),
    Line("cat", "What's it say?"),
    Line("hog", "Plants make food from light."),
    Line("hog", "It's important."),
)

script = scripting.Script(LINES)
hold, say = script.hold, script.say


def on_card(beat: Beat) -> Beat:
    """A line whose words the card already shows, so no caption repeats them."""
    return replace(beat, caption="")


def ask(start: float, line: int, event: str) -> tuple[Beat, ...]:
    """The cat's one line. She has no lip sync, so her mouth moves by the word."""
    return (
        say(start, "cat", line, "half", "open", "desk", event),
        replace(say(start + 0.3, "cat", line, "half", "round", "desk"), word=1),
        replace(say(start + 0.5, "cat", line, "half", "open", "desk"), word=2),
    )


BEATS = (
    say(0.0, "hedgehog", 0, "down", "flat", "desk"),  # already at it, the last row going yellow
    say(1.2, CARD, 1, "wide", "flat", "desk", "page"),
    *ask(3.25, 2, "ask"),
    hold(4.15, "hedgehog", "", "down", "flat", "desk", "stare"),  # she looks: there is nothing to read
    say(5.35, "hedgehog", 3, "up", "grin", "desk"),
    hold(6.15, "cat", "", "half", "flat", "desk", "blank"),  # the silence is the laugh
    say(6.85, STAGE, 4, "wide", "flat", "desk", "quiz"),
    say(8.95, STAGE, 5, "wide", "flat", "desk", "told"),
    hold(13.0, STAGE, BELIEF, "wide", "flat", "desk", "believed"),  # read, not said: more sheets are still landing
    on_card(say(14.7, CARD, 6, "wide", "flat", "desk", "name")),
    on_card(say(15.85, CARD, 7, "wide", "flat", "desk", "reveal")),
    on_card(say(17.45, CARD, 8, "wide", "flat", "desk", "word")),
    say(18.85, STAGE, 9, "wide", "flat", "desk", "shelf"),
    say(20.15, STAGE, 10, "wide", "flat", "desk", "felt"),
    say(23.4, STAGE, 11, "wide", "flat", "desk", "recalled"),
    on_card(say(24.85, CARD, 12, "wide", "flat", "desk", "study")),
    on_card(replace(say(27.5, CARD, 12, "wide", "flat", "desk", "verdict"), word=7)),  # the card's result, on "Their"
    on_card(say(30.5, CARD, 13, "wide", "flat", "desk", "caveat")),
    hold(36.6, "hedgehog", "", "side", "flat", "desk", "turn"),
    say(36.8, "hedgehog", 14, "down", "flat", "desk", "shut"),  # the book shuts on "Test"
    *ask(39.15, 15, "again"),
    hold(40.0, "hedgehog", "", "up", "flat", "desk", "think"),
    say(41.05, "hedgehog", 16, "wide", "grin", "desk"),
    hold(42.3, "hedgehog", "", "down", "flat", "desk", "mark"),
    say(42.55, "hedgehog", 17, "down", "grin", "desk"),
    hold(43.3, "hedgehog", "", "down", "grin", "desk"),
)
END = 44.0
SKETCH = Sketch(SLUG, TITLE, (NARRATOR, HOG, CAT), LINES, BEATS, END, cast=mind_kit.MIND_CAST)
EVENTS = (
    "page",
    "ask",
    "stare",
    "blank",
    "quiz",
    "told",
    "believed",
    "name",
    "reveal",
    "word",
    "shelf",
    "felt",
    "recalled",
    "study",
    "verdict",
    "caveat",
    "turn",
    "shut",
    "again",
    "think",
    "mark",
)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, each event happens once and in order, the first picture speaks, and no word on
    screen is one the channel keeps off it."""
    sketch.check(sk)
    for event in EVENTS:
        scripting.exactly_once(sk.beats, event, f"{event} happens once")
    scripting.only_events(sk.beats, set(EVENTS))
    times = [sketch.events(sk.beats, event)[0][0] for event in EVENTS]
    if times != sorted(times):
        raise sketch.SketchError(f"the events run {EVENTS}")
    if sk.beats[0].line is None:
        raise sketch.SketchError("the reel opens on the behaviour, with its line")
    for text in (
        *(q.text for q in sk.lines),
        NAME,
        BELIEF,
        REVIEW.what,
        REVIEW.result,
        *CAVEAT,
        *SHELF_LABELS,
        *PAGE_KEY_WORDS,
        PAGE_HEADING,
        *ANSWER,
        *QUIZ_TITLE,
        QUIZ_RULE,
        *QUIZ_RESULTS,
        POST.title,
        POST.description,
    ):
        mind_kit.check_copy(text)


PAGE_KEY_WORDS = tuple(words for _, words in PAGE_KEY)


def no_desk(cv, parent) -> None:
    """Each shot lays its own surface: see :func:`dress`."""


def _at(shot, event: str) -> float:
    return sketch.events(shot.beats, event)[0][0]


def _home(shot, start: float, end: float) -> None:
    """The room behind a character, out of focus, and its light."""
    cv = shot.cv
    toon_sets.home(cv, mind_kit.far(cv, cv.group(shot.back, cv.uid("g"), start=start, end=end)), end=shot.end)
    mind_kit.key(cv, shot.light)


def _book(shot, start: float, end: float, *, sweep: float | None = None) -> None:
    """The open book with every row marked, and its last row going yellow at ``sweep`` under the marker."""
    cv = shot.cv
    g = cv.group(shot.front, cv.uid("g"), start=start, end=end)
    ledge(cv, g, "oak")
    marks = dict(ALL_YELLOW)
    if sweep is None:
        marks[LAST_ROW] = HIGHLIGHT
    toon_study.open_book(
        cv,
        g,
        marks,
        sweep=None if sweep is None else (LAST_ROW, HIGHLIGHT, sweep),
        at=BOOK_AT,
        scale=BOOK_SCALE,
        id=cv.uid("book"),
    )
    left, right, y = toon_study.row_span(LAST_ROW, BOOK_AT, BOOK_SCALE)
    if sweep is None:
        path = ()
        tip = (right, y + 6)
    else:
        path = ((sweep, left), (sweep + toon_study.SWEEP, right))
        tip = (left, y + 6)
    toon_study.highlighter(cv, g, tip, PAW, path, id=cv.uid("marker"))


def _answer(shot, start: float, end: float, mark: float) -> None:
    """The first frame's framing again: the book open on what she can say, that going yellow under the marker."""
    cv = shot.cv
    g = cv.group(shot.front, cv.uid("g"), start=start, end=end)
    ledge(cv, g, "oak")
    toon_study.open_book(
        cv,
        g,
        note=ANSWER,
        note_sweep=(HIGHLIGHT, mark),
        measure=shot.measure,
        at=BOOK_AT,
        scale=BOOK_SCALE,
        id=cv.uid("book"),
    )
    left, right, y = toon_study.note_span(ANSWER, shot.measure, BOOK_AT, BOOK_SCALE)
    done = mark + toon_study.SWEEP
    path = ((mark, left), (done, right), (done + 0.25, right + MARKER_CLEAR))  # it lifts off the row's last letter
    toon_study.highlighter(cv, g, (left, y + 16), PAW, path, id=cv.uid("marker"))


def _shut(shot, start: float, end: float) -> None:
    cv = shot.cv
    g = cv.group(shot.front, cv.uid("g"), start=start, end=end)
    ledge(cv, g, "oak")
    toon_study.shut_book(cv, g, at=BOOK_AT, scale=SHUT_SCALE, id=cv.uid("book"))


def _desk_ground(shot) -> None:
    shot.cv.rect(shot.back, 0, 0, shot.cv.width, shot.cv.height, DESK)


def _quiz(shot, told: float) -> None:
    """The old quiz; then, as the narrator widens it to many of us, it is one sheet among others."""
    cv, measure = shot.cv, shot.measure
    _desk_ground(shot)
    push = cv.group(shot.front, cv.uid("g"))  # the push is on the sheet alone; the signature marks hold still
    camera.anchor(push, *QUIZ_AT, place=True)
    camera.push_in(cv, push, scale=[(shot.app.start, 1.0), (told, PUSH)])
    toon_study.quiz_sheet(
        cv, push, QUIZ_TITLE, QUIZ_RULE, QUIZ_RESULTS[0], measure=measure, at=QUIZ_AT, end=told, id=cv.uid("quiz")
    )
    for k, (at, tilt) in enumerate(LANDED):
        toon_study.quiz_sheet(
            cv,
            shot.front,
            QUIZ_TITLE,
            QUIZ_RULE,
            QUIZ_RESULTS[k % len(QUIZ_RESULTS)],
            measure=measure,
            at=at,
            scale=LAND_SCALE,
            tilt=tilt,
            start=told + (LAND_FROM + (k - 1) * LAND_STEP if k else 0.0),
            answers_lettered=False,
            id=cv.uid("quiz"),
        )


def _underline(shot, at: float, end: float) -> None:
    """A rule under the name's last word, as the narrator points at it."""
    cv = shot.cv
    lines, size = mind_kit.name_lines(NAME, shot.measure)
    width = shot.measure(lines[-1], size)
    foot = 1000.0 + len(lines) * size * 1.12 / 2
    g = cv.group(
        shot.front, cv.uid("g"), start=at, end=end, x=cv.width / 2 - width / 2, y=foot - 6, anchorX=0, anchorY=0
    )
    cv.rect(g, 0, 0, width, 14.0, UNDERLINE, radius=7.0)
    cv.keys(g, "scaleX", [(at, 0.02), (at + 0.3, 1.0)], local=False)


def _preference(shot, at: Mapping[str, float], end: float) -> None:
    """The mechanism: a lens that is the preference passes over two files. One lifts. The other does not."""
    cv, felt, recalled = shot.cv, at["felt"], at["recalled"]
    path = ((felt, LENS_REST), (felt + 0.8, FILE_X[0]), (recalled, FILE_X[0]), (recalled + 0.8, FILE_X[1]))
    mind_kit.memory_shelf(
        cv, shot.front, SHELF_LABELS, measure=shot.measure, pull=(0, felt + 0.9), y=SHELF_Y, id=cv.uid("shelf")
    )
    mind_kit.lens(cv, shot.front, (LENS_REST, LENS_Y), shot.app.start, end, radius=LENS_R, path=path, id=cv.uid("lens"))
    tag = cv.group(shot.front, cv.uid("g"), x=LENS_REST, y=LENS_Y)
    wide = shot.measure(LENS_TAG, TAG_SIZE) + 36.0
    cv.rect(tag, -wide / 2, -36.0, wide, 72.0, mind_kit.INK, radius=14.0)
    cv.text(
        tag, cv.uid("tag"), LENS_TAG, -wide / 2, -30.0, round(wide), 60, TAG_SIZE, color=mind_kit.PAPER, wrap="none"
    )
    cv.keys(tag, "x", list(path), kind="sine-in-out", local=False)
    mind_kit.floor(cv, shot.front)


def _caveat(shot, at: float, end: float) -> None:
    """The later meta-analysis, in the channel's letters, under the card."""
    cv = shot.cv
    g = cv.group(shot.front, cv.uid("g"), start=at, end=end)
    size = 50.0
    for k, row in enumerate(CAVEAT):
        if shot.measure(row, size) > 900.0:
            raise sketch.SketchError(f"a caveat row is wider than the safe zone: {row!r}")
        cv.text(g, cv.uid("caveat"), row, 90.0, 1090.0 + k * 66.0, 900, 66, size, color=mind_kit.PAPER, wrap="none")


def dress(shot) -> None:
    """Every shot's set and props: the home for the behaviour, sheets for the page and the quiz, the stage for the name,
    the mechanism and the evidence, and the home again for the turn and the last frame."""
    cv, app = shot.cv, shot.app
    at = {name: _at(shot, name) for name in EVENTS}
    if app.who == CARD and app.start == at["page"]:
        _desk_ground(shot)
        toon_study.study_page(
            cv, shot.front, PAGE_HEADING, PAGE_MARKS, PAGE_KEY, measure=shot.measure, id=cv.uid("page")
        )
        mind_kit.sign(cv, shot.front)
    elif app.who == CARD and app.start == at["name"]:
        mind_kit.stage(cv, shot.back)
        mind_kit.name_card(cv, shot.front, NAME, app.start, at["reveal"], app.end, shot.measure, id=cv.uid("name"))
        _underline(shot, at["word"], app.end)
        mind_kit.sign(cv, shot.front)
    elif app.who == CARD:
        mind_kit.stage(cv, shot.back)
        mind_kit.evidence_card(
            cv, shot.front, REVIEW, app.start, app.end, shot.measure, id=cv.uid("review"), reveal=at["verdict"]
        )
        _caveat(shot, at["caveat"], app.end)
        mind_kit.sign(cv, shot.front)
    elif app.who == STAGE and app.start == at["quiz"]:
        _quiz(shot, at["told"])
        mind_kit.sign(cv, shot.front)
    elif app.who == STAGE:
        mind_kit.stage(cv, shot.back)
        _preference(shot, at, app.end)
    elif app.who == "cat":
        _home(shot, app.start, app.end)
        ledge(cv, shot.front, "oak")
    elif app.start == 0.0:
        _home(shot, app.start, app.end)
        _book(shot, app.start, app.end, sweep=FIRST_SWEEP)
    elif app.start < at["turn"]:
        _home(shot, app.start, app.end)
        _book(shot, app.start, app.end)
    elif app.start == at["turn"]:
        _home(shot, app.start, app.end)
        _book(shot, app.start, at["shut"])
        _shut(shot, at["shut"], app.end)
    else:
        _home(shot, app.start, app.end)
        _shut(shot, app.start, at["mark"])
        _answer(shot, at["mark"], app.end, at["mark"] + 0.15)


def foley(beats, end, speech, root, seed) -> list[dict]:
    """The channel's sting on the name, and a marker's squeak on both highlighted rows."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    times = {name: sketch.events(beats, name)[0][0] for name in ("told", "reveal", "shut", "mark")}
    sting = mind_kit.write_sting(audio / "sting.wav", [times["reveal"]], end)
    squeak = synth.write_tones(audio / "squeak.wav", [FIRST_SWEEP, times["mark"] + 0.15], end, SQUEAK)
    thud = synth.write_tones(audio / "thud.wav", [times["shut"]], end, THUD)
    land = [times["told"] + LAND_FROM + k * LAND_STEP for k in range(len(LANDED) - 1)]
    paper = synth.write_whoosh(audio / "paper.wav", land, end)
    return [
        sketch.effect("sting", 0.0, -5.0, root, sting),
        sketch.effect("squeak", 0.0, -14.0, root, squeak),
        sketch.effect("thud", 0.0, -12.0, root, thud),
        sketch.effect("paper", 0.0, -20.0, root, paper),
    ]


POST = InstagramPost(
    title="Fourth time through this page.",
    description=(
        "The meshing hypothesis: the idea that you learn more when teaching matches your style. Pashler et al. found "
        '"no adequate evidence base" for building it into general teaching. Not disproved: a 2024 meta-analysis found '
        'a small benefit (g = 0.31), "too small and too infrequent" for widespread adoption.\n'
        "Source: Pashler et al. (2008); Clinton-Lisell & Litzinger (2024); Knoll et al. (2017); "
        "Dunlosky et al. (2013); 89.1% is among educators surveyed, Newton & Salvi (2020)."
    ),
    credit="Voices: ElevenLabs premade voices Bella, Jessica and Laura. Original characters, drawn in code.",
    hashtags=("#psychology", "#learningstyles", "#howpeoplethink", "#studytips"),
    thumbnail=Thumbnail("It's important.", 36.9, "There's a name for that", place="top"),
)
