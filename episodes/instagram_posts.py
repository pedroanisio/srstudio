#!/usr/bin/env python3
"""The Instagram post of every episode, as data, and the publish gate of the rendered videos.

Each episode script calls ``ep.instagram(POSTS[slug])`` so a build leaves ``ig.txt`` next to its scene. Each post
also designs its cover: a :class:`~srstudio.thumbnail.Thumbnail` drawn over a frame of the video. ``deliver``
writes one ``<out>/<video name>/`` folder per rendered video, holding ``ig.txt`` and ``cover.jpg``, for every video
that drifted, and records ``<out>/delivery.json``; ``check`` exits 1 and lists every drift (a video re-rendered after
its cover, a changed post, an edited or missing file, a post without a render) and writes nothing:

    python3 instagram_posts.py deliver OUT RENDERS --fonts DIR [--engine BIN] [--only NAME ...]
    python3 instagram_posts.py check OUT RENDERS --fonts DIR

``--only`` delivers the named videos alone (one ready to publish while another post waits for its render); the
rest of the delivery is left as it was, and ``check`` still reports what drifted there.

The headline font (:data:`THUMBNAIL_FONT`) is installed into ``--fonts`` and pinned there; once it is in place
nothing is downloaded. ``--engine`` defaults to ``$SRSTUDIO_ENGINE``, then ``scene-render`` on the ``PATH``.
"""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

from srstudio import fonts
from srstudio.social import DeliveryError, Drift, InstagramPost, Item, check_delivery, publish
from srstudio.thumbnail import Thumbnail

THUMBNAIL_FONT = fonts.GoogleFont("Anton", 400)  # a condensed display face: two big lines fit a portrait cover

VOICES = "Voices: ElevenLabs premade voices Eric and Will."
SERIES = ("#TheInterview", "#officehumor", "#jobinterview", "#workcomedy", "#animatedshorts", "#vectoranimation")

POSTS: dict[str, InstagramPost] = {
    "honesty-interview": InstagramPost(
        title="Greatest weakness? Honesty.",
        description=(
            "Episode 01 of The Interview. The candidate is asked for a weakness and gives the one answer the manager "
            "cannot argue with, twice.\n"
            "Contains one strong word."
        ),
        credit=VOICES,
        hashtags=SERIES + ("#honesty", "#interviewfail"),
        thumbnail=Thumbnail("Greatest weakness?\nHonesty.", 2.4, "The Interview · 01", (540, 690), 1.4),
    ),
    "pressure-interview": InstagramPost(
        title="How do you handle pressure?",
        description=(
            "Episode 02 of The Interview. A perfectly honest answer about pressure, and a manager who realises too "
            "late that they were talking about the same thing."
        ),
        credit=VOICES,
        hashtags=SERIES + ("#notifications", "#worklifebalance"),
        thumbnail=Thumbnail("How do you handle\npressure?", 6.0, "The Interview · 02", (540, 700), 1.4),
    ),
    "fast-at-math": InstagramPost(
        title="17 × 19? Forty-two. But it was fast.",
        description=(
            "Episode 03 of The Interview. Greatest strength: speed. Accuracy was not on the list. Hand gestures, a "
            "facepalm and a scorecard that keeps the receipts."
        ),
        credit=VOICES + " Original sound effects.",
        hashtags=SERIES + ("#mathjokes", "#fastnotright"),
        thumbnail=Thumbnail("17 × 19?\nForty-two.", 5.4, "The Interview · 03", (600, 520), 1.15),
    ),
    "multitasking": InstagramPost(
        title="Are you good at multitasking? Absolutely.",
        description=(
            "Episode 04 of The Interview. Asked for an example, the candidate names the one task they can run in "
            "parallel without dropping anything. Status pings included."
        ),
        credit=VOICES,
        hashtags=SERIES + ("#multitasking", "#disappointment"),
        thumbnail=Thumbnail("Good at\nmultitasking?", 5.0, "The Interview · 04", (540, 520), 1.1),
    ),
    "wifi-password": InstagramPost(
        title="The Wi-Fi password is a sales tactic.",
        description=(
            "Comedy Cut 05, new cast: Ava the barista, Milo the customer and one park pigeon. The password is exactly "
            "what she said. No spaces. Five bucks well spent on a spelling lesson."
        ),
        credit="Voices: ElevenLabs premade voices Jessica and Liam. Procedural café and park sound effects.",
        hashtags=(
            "#TheInterview",
            "#cafehumor",
            "#wifipassword",
            "#baristalife",
            "#workcomedy",
            "#animatedshorts",
            "#vectoranimation",
            "#pigeon",
        ),
        thumbnail=Thumbnail("What's the\nWi-Fi password?", 9.0, "Comedy Cut 05", (540, 560), 1.2),
    ),
    "scene": InstagramPost(  # printer-recreation: the project slug of the square cartoon
        title="The printer was fine this morning.",
        description=(
            "A printer that makes startup noises instead of printing, and knows exactly when you are in a hurry.\n"
            "This is a procedural, hand-built vector recreation of Mark Kacy's printer cartoon, with newly "
            "synthesized performances. Original idea, writing and design: Mark Kacy."
        ),
        credit="Recreation of a cartoon by Mark Kacy. Voices: ElevenLabs premade voices Chris and Callum.",
        hashtags=(
            "#printerproblems",
            "#officehumor",
            "#cartoon",
            "#handdrawn",
            "#animatedshorts",
            "#recreation",
            "#markkacy",
            "#workcomedy",
        ),
        thumbnail=Thumbnail("Use the\nblack ink!", 37.0, "Printer", place="top"),
    ),
    "five-years": InstagramPost(
        title="Where do you see yourself in five years?",
        description=(
            "Episode 06 of The Interview. The candidate has a plan. It does not involve the job. It does involve the "
            "chair, which squeaks, and which gets taken for a spin before the credits."
        ),
        credit=VOICES + " Sound effects generated with ElevenLabs.",
        hashtags=SERIES + ("#fiveyearplan", "#executivechair"),
        thumbnail=Thumbnail("Where do you see\nyourself in 5 years?", 10.4, "The Interview · 06", (540, 560), 1.2),
    ),
    "upside-down": InstagramPost(
        title="When the Q3 numbers are bad, check the board.",
        description=(
            "Episode 07 of The Interview. The candidate got a job after all: reception. Upstairs the boss presents "
            "a chart going down, until the speakerphone points out the board is upside down. Record quarter! "
            "Bonuses for everyone! Including reception? Flip.\n"
            "Episode 09, in the new polished reception and conference room."
        ),
        credit="Voices: ElevenLabs premade voices Eric, Will and Liam. Sound effects generated with ElevenLabs.",
        hashtags=SERIES + ("#quarterlyreview", "#bonus"),
        thumbnail=Thumbnail("Check\nthe board.", 19.2, "The Interview · 09", (700, 760), 1.25),
    ),
    "the-router": InstagramPost(
        title="Have you tried turning me off and on again?",
        description=(
            "The internet is down and the router knows exactly how to fix it. It just would rather you did it.\n"
            "Ink 02: the second square cartoon, an original talking appliance this time."
        ),
        credit="Voices: ElevenLabs premade voices Chris and Daniel. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#routerproblems",
            "#officehumor",
            "#itsupport",
            "#turnitoffandonagain",
            "#handdrawn",
            "#animatedshorts",
            "#workcomedy",
        ),
        thumbnail=Thumbnail("Off and\non again?", 11.0, "Ink 02", place="top"),
    ),
    "mushroom-training": InstagramPost(
        title="Work training be like.",
        description=(
            "This module will take 45 minutes to complete, and there will be a test at the end. A mushroom sits "
            "through all of it.\n"
            "Recreation of the Under Studio training cartoon in the Cel style: traced drawings, a measured camera "
            "push, hand-lettered captions and a new synthesized narration. Character art, dialogue and lettering "
            "are adapted from the reference; the original creator retains rights."
        ),
        credit="Narration: ElevenLabs premade voice Alice. Reference: understudiohub / Under Studio.",
        hashtags=(
            "#worktraining",
            "#officehumor",
            "#onboarding",
            "#compliancetraining",
            "#workcomedy",
            "#animatedshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Work training\nbe like", 36.0, "Workplace module", (540, 700), 1.3),
    ),
    "focus-mode": InstagramPost(
        title="Focus. The deadline is... oh.",
        description=(
            "Pip sits down to work, types for one bar, and the groove wins. A record scratch: the deadline. Focus. "
            "Then he checks the date.\n"
            "Episode 07, the first in the Soft style: every pose lands on the beat."
        ),
        credit="Voice: ElevenLabs premade voice Will. Music composed with ElevenLabs Music.",
        hashtags=(
            "#focusmode",
            "#deadline",
            "#procrastination",
            "#officehumor",
            "#workcomedy",
            "#animatedshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Shake it\nto the beat!", 10.0, "Episode 07", (620, 1000), 1.3),
    ),
    "camera-off": InstagramPost(
        title="Camera off. Pajamas on the beat.",
        description=(
            "Pip is very professional on the call. Then the boss announces forty slides, the camera goes off and "
            "the dancing starts, until someone asks him to share his screen.\n"
            "Episode 08, the second in the Soft style: every pose lands on the beat."
        ),
        credit=(
            "Song composed and sung with the ElevenLabs Music API. Boss: ElevenLabs premade voice Eric. "
            "Sound effects generated with ElevenLabs."
        ),
        hashtags=(
            "#cameraoff",
            "#zoommeeting",
            "#workfromhome",
            "#remotework",
            "#officehumor",
            "#workcomedy",
            "#animatedshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Camera off.\nPajamas on.", 10.0, "Episode 08", (560, 1000), 1.25),
    ),
    "off-and-on": InstagramPost(
        title="IT support has one fix. It's a jingle.",
        description=(
            "The coffee machine is broken: turn it off and on again. Pip is broken: lights off, lights on, and now "
            "he loves Mondays. Then Remy's own screen dies, and the IT hotline knows exactly what to say.\n"
            "Episode 10, the third in the Soft style, with Juno and Remy in the new meeting room and break room."
        ),
        credit=(
            "Music and Remy's vocal composed with the ElevenLabs Music API. Voices: ElevenLabs premade voices Laura "
            "(Juno), Will (Pip) and Charlie (IT hotline). Sound effects generated with ElevenLabs."
        ),
        hashtags=(
            "#itsupport",
            "#turnitoffandonagain",
            "#mondays",
            "#officehumor",
            "#workcomedy",
            "#animatedshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Somebody\nreboot me.", 29.5, "Episode 10", (600, 1000), 1.2),
    ),
    "employee-survey": InstagramPost(
        title="Anonymous employee survey.",
        description=(
            "Would you recommend working for this company? Not a chance in hell. Then the survey asks for a "
            "department, a job title, a start date and a seat on the office map.\n"
            "Recreation of the.nope.cat's survey reel in the Toon style: a flat cartoon cat whose expression swaps "
            "per line, each phrase in a white pill, and a new synthesised narration. Character, dialogue and "
            "captions are adapted from the reference; the original creator retains rights."
        ),
        credit="Narration: ElevenLabs premade voice Brian. Reference: the.nope.cat.",
        hashtags=(
            "#employeesurvey",
            "#anonymous",
            "#officehumor",
            "#workcomedy",
            "#catsofinstagram",
            "#animatedshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Anonymous\nsurvey?", 37.0, "Employee survey", (480, 1050), 1.3),
    ),
    "check-with-my-team": InstagramPost(
        title="POV: you gotta check with your team first.",
        description=(
            "Let me just check with my team real quick and get back to you. The team turns out to be one person and "
            "three AI assistants, dancing in a garden. Three hours later, the verdict is in.\n"
            "Recreation of @theaifilmmaker's cartoon in the Stick style: traced stick figures on painted sets, "
            "outlined captions, a new synthesised voice-over and music at the dance's tempo. Character art, dialogue "
            "and lettering are adapted from the reference, and the original creator retains rights; the card and the "
            "closing line are new."
        ),
        credit="Voice-over: ElevenLabs premade voice Chris. Music composed with ElevenLabs Music. "
        "Reference: @theaifilmmaker.",
        hashtags=(
            "#checkwithmyteam",
            "#officehumor",
            "#aitools",
            "#workcomedy",
            "#stickfigure",
            "#animatedshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Let me check\nwith my team", 0.8, "POV", (430, 900), 1.3),
    ),
    "screen-share": InstagramPost(
        title="Can everyone see my screen?",
        description=(
            "Yes. And the inbox. All of it. Three beats of a remote workday: a shared screen that shows too much, a "
            "meeting that runs over meets a very bad connection, and a Friday 4:59 PM \"got a sec?\".\n"
            "Stick 02, the first original episode in the Stick style: drawn stick figures, a call screen and a boss "
            "who walks in."
        ),
        credit="Voices: ElevenLabs premade voices Eric and Will. Sound effect generated with ElevenLabs.",
        hashtags=(
            "#screenshare",
            "#remotework",
            "#zoommeeting",
            "#officehumor",
            "#workcomedy",
            "#stickfigure",
            "#animatedshorts",
        ),
        thumbnail=Thumbnail("Can everyone\nsee my screen?", 2.2, "Stick 02", (380, 900), 2.2),
    ),
    "repeat-after-me": InstagramPost(
        title="Repeat after me.",
        description=(
            "I will not check my email on the drive home. I will leave work at work. Say it twice, say it firmer, "
            "and whatever you do, don't look at the passenger seat.\n"
            "Stick 03: Dev's vows on the commute, a car drawn in code with the road passing in the window, and the "
            "captions one word at a time."
        ),
        credit="Voice: ElevenLabs premade voice Will. Sound effect and instrumental music composed with ElevenLabs.",
        hashtags=(
            "#workfromcar",
            "#worklifebalance",
            "#afterhours",
            "#officehumor",
            "#workcomedy",
            "#stickfigure",
            "#animatedshorts",
        ),
        thumbnail=Thumbnail("Repeat\nafter me.", 10.8, "Stick 03", (540, 1200), 1.3),
    ),
    "the-report": InstagramPost(
        title="Rex. It's on your forehead.",
        description=(
            "Fern wants the report. Rex has never heard of any report. The eleven reminders, the sticky notes and "
            "the one on his forehead say otherwise.\n"
            "A Toon two-hander voiced with ElevenLabs premade voices Charlie (Rex) and Matilda (Fern); original "
            "characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Charlie and Matilda. Original characters, drawn in code.",
        hashtags=(
            "#officehumor",
            "#workcomedy",
            "#thereport",
            "#animatedshorts",
            "#vectoranimation",
            "#cartoondog",
            "#cartoonfrog",
        ),
        thumbnail=Thumbnail("It's on your\nforehead.", 27.5, "Toon 03", (330, 1000), 1.4),
    ),
    "logo-bigger": InstagramPost(
        title="Can you make the logo bigger?",
        description=(
            "The client wants the logo bigger. Then bigger. Then the size of the building. Then it should pop. "
            "Then smaller. Rex sends the invoice.\n"
            "A Toon sketch voiced with ElevenLabs premade voices George (the client), Matilda (Fern) and Charlie "
            "(Rex); original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices George, Matilda and Charlie. Original characters, drawn in code.",
        hashtags=(
            "#makeitbigger",
            "#designerproblems",
            "#clientfeedback",
            "#officehumor",
            "#workcomedy",
            "#animatedshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Can you make\nit bigger?", 16.5, "Toon 04", (700, 950), 1.2),
    ),
    "quick-question": InstagramPost(
        title="Quick question. Got a sec?",
        description=(
            "Pip has a quick question. First, some context. It started in March. Then Dave left. Forty-six "
            "minutes later: when's the stand-up? Three minutes ago. It's on the board behind her.\n"
            "A Toon sketch voiced with ElevenLabs premade voices Alice (Pip) and Bill (Bruno), lip-synced to their "
            "words; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Alice and Bill. Original characters, drawn in code.",
        hashtags=(
            "#quickquestion",
            "#officehumor",
            "#workcomedy",
            "#standupmeeting",
            "#animatedshorts",
            "#vectoranimation",
            "#lipsync",
        ),
        thumbnail=Thumbnail("Quick question.\nGot a sec?", 1.0, "Toon 05", (340, 1050), 1.3),
    ),
}

# project slug -> the file name of its rendered video, without extension
VIDEOS = {
    "honesty-interview": "honesty-interview-recreated",
    "pressure-interview": "pressure-interview",
    "fast-at-math": "fast-at-math",
    "multitasking": "multitasking",
    "wifi-password": "wifi-password",
    "scene": "Printer_Recreation",
    "five-years": "five-years",
    "upside-down": "upside-down",
    "the-router": "the-router",
    "mushroom-training": "mushroom-training",
    "focus-mode": "focus-mode",
    "camera-off": "camera-off",
    "off-and-on": "off-and-on",
    "employee-survey": "employee-survey",
    "check-with-my-team": "check-with-my-team",
    "screen-share": "screen-share",
    "repeat-after-me": "repeat-after-me",
    "the-report": "the-report",
    "logo-bigger": "logo-bigger",
    "quick-question": "quick-question",
}


# Episodes whose scene hides its burned-in text (hook card, captions) in a cover variant, with the scene file in
# <episodes>/<slug>/ that the published video is encoded from: the cover's backdrop is drawn from it, so the headline
# does not sit on a cut card or a ghost caption.
COVER_SCENES = {"repeat-after-me": "repeat-after-me.scene.xml", "check-with-my-team": "scene.xml"}


def items(renders: Path, episodes: Path | None = None) -> dict[str, Item]:
    """Every post with its rendered video (and the scene its cover is drawn from, for :data:`COVER_SCENES`), keyed
    by the video's name. ``episodes`` defaults to the ``episodes`` folder beside ``renders``."""
    episodes = Path(episodes) if episodes is not None else Path(renders).resolve().parent / "episodes"
    return {
        VIDEOS[slug]: Item(
            post,
            Path(renders) / f"{VIDEOS[slug]}.mp4",
            episodes / slug / COVER_SCENES[slug] if slug in COVER_SCENES else None,
        )
        for slug, post in POSTS.items()
    }


def font_file(folder: Path) -> Path:
    """The headline font, installed into ``folder`` (and pinned by its lock) the first time."""
    return fonts.install(THUMBNAIL_FONT, folder).path


def write_all(
    out: Path, renders: Path, *, fonts_dir: Path, engine: str | Path, only: list[str] | None = None
) -> list[Path]:
    """Deliver every post whose video drifted (or only the ``only`` ones) and record the delivery; returns the
    folders written."""
    return publish(items(renders), out, font=font_file(fonts_dir), engine=engine, only=only)


def check_all(out: Path, renders: Path, *, fonts_dir: Path) -> list[Drift]:
    """Every drift between ``out`` and delivering every post from ``renders`` now."""
    return check_delivery(items(renders), out, font=font_file(fonts_dir))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("deliver", "check"))
    parser.add_argument("out", type=Path, help="the delivery folder: one folder per video and delivery.json")
    parser.add_argument("renders", type=Path, help="the folder of rendered <video name>.mp4 files")
    parser.add_argument("--fonts", type=Path, required=True, help="where the headline font is installed")
    parser.add_argument("--engine", default=os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render"))
    parser.add_argument("--only", action="append", metavar="NAME", help="deliver this video alone (repeatable)")
    args = parser.parse_args(argv)
    if args.command == "check":
        drift = check_all(args.out, args.renders, fonts_dir=args.fonts)
        for d in drift:
            print(d)
        print(f"{len(POSTS)} videos, {len(drift)} drifted" if drift else f"{len(POSTS)} videos, delivery current")
        return 1 if drift else 0
    if not args.engine:
        parser.error("no engine: pass --engine or set SRSTUDIO_ENGINE")
    try:
        written = write_all(args.out, args.renders, fonts_dir=args.fonts, engine=args.engine, only=args.only)
    except DeliveryError as exc:
        raise SystemExit(f"deliver: {exc}") from None
    for folder in written:
        print(folder / "ig.txt", folder / "cover.jpg")
    if args.only:
        left = [d for d in check_all(args.out, args.renders, fonts_dir=args.fonts) if d.name not in args.only]
        print(f"delivered {', '.join(args.only)}; {len(left)} drift(s) left elsewhere, see check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
