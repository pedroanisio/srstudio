"""The Unwritten Rules, the group chat: a pilot of the talking-head show, main trigger recognition: the sketch as data.

Lint, a clothes moth, tells the lens the group chat's unwritten rules with total conviction, in a cardigan he is eating.
Every rule tops the last, and each time the phone on his shelf buzzes the lit screen drags him down to it mid-sentence.
Rule three is the one nobody admits: everyone muted it, and it is only you in there. The third buzz is you, asking if
anyone has seen your cardigan. He looks down at it, puts the phone out, and leaves you on read, rule one, then signs off
as if you were the one in the wrong. The last frame is framed and lit as the first, so the reel cuts back to its start.

``SKETCH`` is checked by :func:`srstudio.sketch.check`; :func:`validate` checks the events and every word the reel shows
against :func:`srstudio.host_kit.check_copy`. ``ACTS`` runs parallel to the beats.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import foley as synth
from srstudio import host_kit, scripting, sketch
from srstudio.host_kit import BONE, Bubble, Pose
from srstudio.sketch import Line, Sketch
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

SEED = 3112
SLUG = "unwritten-rules-group-chat"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "The group chat has rules — The Unwritten Rules"
DESCRIPTION = (
    "A pilot of a talking-head show: Lint, a moth who lives in your wardrobe, explains the unwritten rules of the "
    "group chat straight to camera, and breaks the first one."
)
ACCESSIBILITY = (
    "An animated moth in a bitten mustard cardigan talks to camera inside a wardrobe, a huge phone lying on the shelf "
    "in front of him. He counts three rules of the group chat on his fingers. Each time the phone buzzes its light "
    "pulls him down to it and his wings flutter. Rule three: everyone has it on mute and it is just you in there. The "
    "phone shows a message, has anyone seen my cardigan, marked read. He looks down at the cardigan he is wearing and "
    "chewing, presses the side button and the screen goes dark. He looks at the lens and says you know what you did."
)
NARRATION = "Voiced with the ElevenLabs premade voice Harry; synthesised buzz and button click; no music."
NOTE = "ElevenLabs premade voice Harry at its natural pace; no reference-voice cloning."
TINTS = {"lint": BONE}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12, fine=True)
VERSIONS: dict[str, int] = {}
END = 29.6
SIGN_OFF = "You know what you did."
CHAT_NAME = "The Group Chat"
LABELS = (  # the beat it arrives on, the beat it leaves on, its words
    ("hook", "where", "THE GROUP CHAT HAS RULES"),
    ("one", "buzz-1", "RULE 1"),
    ("two", "they-know", "RULE 2"),
    ("three", "mute", "RULE 3"),
)

LINES = (
    Line("lint", "Nobody tells you the group chat has rules."),
    Line("lint", "I live in your wardrobe. You added me by accident."),
    Line("lint", "Rule one. You never leave someone on read."),
    Line("lint", "Never."),
    Line("lint", "Rule two. Haha means you didn't laugh."),
    Line("lint", "Ha. With a period. Means they know."),
    Line("lint", "Ignore that."),
    Line("lint", "Rule three. The one nobody admits."),
    Line("lint", "Everyone has it on mute. Everyone."),
    Line("lint", "It's just you in there, alone, typing haha."),
    Line("lint", SIGN_OFF),
)
PLACEHOLDER = ("side", "flat", "desk")  # a Toon pose for the sketch's check: this cast is drawn from ACTS
script = scripting.Script(LINES)
say, hold, first, part = script.say, script.hold, script.first, script.part
LOOK = Pose()
DRAWN = Pose("down", "talk", pull=0.72)
HOOKED = Pose("down", "flat", pull=1.0)
ROWS: tuple[tuple[str, sketch.Beat, Pose], ...] = (
    ("hook", say(0.0, "lint", 0, *PLACEHOLDER), Pose(head=-2.0)),
    ("where", first(2.35, "close", 1, "I live in your wardrobe.", *PLACEHOLDER), Pose(head=3.0)),
    ("added", part(3.7, "lint", 1, 5, "You added me by accident.", *PLACEHOLDER), Pose("squint", head=-3.0)),
    ("one", first(5.4, "close", 2, "Rule one.", *PLACEHOLDER), Pose("wide", arm="one", head=-2.0)),
    ("never", part(6.3, "tight", 2, 2, "You never leave someone on read.", *PLACEHOLDER), Pose("squint")),
    ("buzz-1", hold(7.85, "lint", "", *PLACEHOLDER, "buzz"), Pose("down", "flat", pull=0.72)),
    ("pulled", say(8.35, "lint", 3, *PLACEHOLDER), DRAWN),
    ("two", first(9.2, "close", 4, "Rule two.", *PLACEHOLDER, "dark"), Pose("wide", arm="two", head=2.0)),
    ("haha", part(10.2, host_kit.CHAT, 4, 2, "Haha means you didn't", *PLACEHOLDER), LOOK),
    ("laugh", part(11.35, "tight", 4, 6, "laugh.", *PLACEHOLDER), LOOK),
    ("they-know", say(12.22, "tight", 5, *PLACEHOLDER), Pose("squint", head=-4.0)),
    ("buzz-2", hold(14.75, "lint", "", *PLACEHOLDER, "buzz"), HOOKED),
    ("ignore", say(15.25, "lint", 6, *PLACEHOLDER), Pose("down", "talk", pull=1.0)),
    ("three", first(16.25, "close", 7, "Rule three.", *PLACEHOLDER, "dark"), Pose("wide", arm="three")),
    ("admits", part(17.25, "tight", 7, 2, "The one nobody admits.", *PLACEHOLDER), Pose("squint")),
    ("mute", first(18.65, "close", 8, "Everyone has it on mute.", *PLACEHOLDER), Pose(head=2.0)),
    ("everyone", part(20.55, "tight", 8, 5, "Everyone.", *PLACEHOLDER), Pose("squint")),
    ("alone", say(21.65, "close", 9, *PLACEHOLDER), Pose(head=-2.0)),
    ("buzz-3", hold(24.6, "lint", "", *PLACEHOLDER, "buzz"), HOOKED),
    ("insert", hold(25.0, host_kit.CHAT, "", *PLACEHOLDER), LOOK),
    ("chewing", hold(26.35, "close", "", *PLACEHOLDER), Pose("down", "chew", head=4.0, pull=0.4)),
    ("press", hold(27.0, "lint", "", *PLACEHOLDER, "press"), Pose("level", "chew", "press")),
    ("sign", say(28.2, "lint", 10, *PLACEHOLDER), Pose("squint")),
)
NAMES = tuple(row[0] for row in ROWS)
BEATS = tuple(row[1] for row in ROWS)
ACTS = tuple(row[2] for row in ROWS)
SKETCH = Sketch(SLUG, TITLE, (host_kit.LINT,), LINES, BEATS, END, cast=host_kit.HOST_CAST)
EVENTS = ("buzz", "dark", "press")
PUSH = (0.8, 1.08)  # seconds and scale of the push that moves the first second
HAHA = (Bubble("haha"), Bubble("haha", at=0.15), Bubble("haha", at=0.3))
ASKED = (Bubble("Has anyone seen my cardigan?", sender="You", status="Read by Lint", status_at=0.45),)
POST = InstagramPost(
    title="Which group chat rule do you break?",
    description="Lint lives in your wardrobe. He has rules.",
    credit="An animated character; synthetic voice.\nVoice: ElevenLabs premade Harry.",
    hashtags=("#groupchat", "#unwrittenrules", "#animation", "#lint"),
    thumbnail=Thumbnail(
        "Group chat\nhas rules", 3.2, "The Unwritten Rules", focus=(540.0, 650.0), zoom=1.0, place="bottom"
    ),
)


def beat(name: str, beats=BEATS):
    """The beat called ``name``, from the sketch's or a recording's ``beats``."""
    return beats[NAMES.index(name)]


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, the phone goes out once, the first picture speaks, the acts match the beats, and no
    word the reel shows is one the show keeps off it."""
    sketch.check(sk)
    if len(ACTS) != len(sk.beats) or len(NAMES) != len(sk.beats) or len(set(NAMES)) != len(NAMES):
        raise sketch.SketchError(f"{len(ACTS)} acts and {len(NAMES)} names for {len(sk.beats)} beats")
    scripting.exactly_once(sk.beats, "press", "he puts the phone out once")
    scripting.only_events(sk.beats, set(EVENTS))
    if sk.beats[0].line is None:
        raise sketch.SketchError("the reel opens on Lint's line")
    if sk.lines[-1].text != SIGN_OFF:
        raise sketch.SketchError("every episode closes on the sign-off")
    for text in (*(q.text for q in sk.lines), *(row[2] for row in LABELS), *(b.text for b in ASKED), POST.title):
        host_kit.check_copy(text)


def overlay(cv, parent, beats, end, measure) -> None:
    """Over the picture: the four labels, the two inserts, the sign-off, the signature marks."""
    host_kit.sign(cv, parent)
    for a, b, text in LABELS:
        host_kit.label(cv, parent, text, beat(a, beats).start, beat(b, beats).start, measure)
    host_kit.screen(
        cv, parent, CHAT_NAME, _late(HAHA, beat("haha", beats).start), *_span("haha", "laugh", beats), measure
    )
    host_kit.screen(
        cv, parent, CHAT_NAME, _late(ASKED, beat("insert", beats).start), *_span("insert", "chewing", beats), measure
    )
    host_kit.sign_off(cv, parent, SIGN_OFF, beat("sign", beats).start, end, measure)


def _span(a: str, b: str, beats) -> tuple[float, float]:
    return beat(a, beats).start, beat(b, beats).start


def _late(bubbles, start: float) -> tuple[Bubble, ...]:
    return tuple(replace(b, at=start + b.at, status_at=start + b.status_at) for b in bubbles)


def foley(beats, end: float, speech, root, seed: int) -> list[dict]:
    """A buzz on each ``buzz`` beat and the click of the side button; no sting and no bed."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    buzzes = [at for at, _ in sketch.events(beats, "buzz")]
    press = sketch.events(beats, "press")[0][0]
    return [
        sketch.effect("buzz", 0.0, -3.0, root, synth.write_buzz(audio / "buzz.wav", buzzes, end, seed=seed)),
        sketch.effect("click", 0.0, -4.0, root, host_kit.write_click(audio / "click.wav", [press], end)),
    ]
