#!/usr/bin/env python3
"""The Instagram caption of every episode, as data, and a writer for the rendered videos.

Each episode script calls ``ep.instagram(POSTS[slug])`` so a build leaves ``ig.txt`` next to its scene.
Run this file directly to write one ``<out>/<video name>/ig.txt`` per rendered video:

    python3 instagram_posts.py /path/to/generated/renders/ig
"""

from __future__ import annotations

import sys
from pathlib import Path

from srstudio.social import InstagramPost

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
    ),
    "pressure-interview": InstagramPost(
        title="How do you handle pressure?",
        description=(
            "Episode 02 of The Interview. A perfectly honest answer about pressure, and a manager who realises too "
            "late that they were talking about the same thing."
        ),
        credit=VOICES,
        hashtags=SERIES + ("#notifications", "#worklifebalance"),
    ),
    "fast-at-math": InstagramPost(
        title="17 × 19? Forty-two. But it was fast.",
        description=(
            "Episode 03 of The Interview. Greatest strength: speed. Accuracy was not on the list. Hand gestures, a "
            "facepalm and a scorecard that keeps the receipts."
        ),
        credit=VOICES + " Original sound effects.",
        hashtags=SERIES + ("#mathjokes", "#fastnotright"),
    ),
    "multitasking": InstagramPost(
        title="Are you good at multitasking? Absolutely.",
        description=(
            "Episode 04 of The Interview. Asked for an example, the candidate names the one task they can run in "
            "parallel without dropping anything. Status pings included."
        ),
        credit=VOICES,
        hashtags=SERIES + ("#multitasking", "#disappointment"),
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
    ),
    "five-years": InstagramPost(
        title="Where do you see yourself in five years?",
        description=(
            "Episode 06 of The Interview. The candidate has a plan. It does not involve the job. It does involve the "
            "chair, which squeaks, and which gets taken for a spin before the credits."
        ),
        credit=VOICES + " Sound effects generated with ElevenLabs.",
        hashtags=SERIES + ("#fiveyearplan", "#executivechair"),
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
    ),
    "focus-mode": InstagramPost(
        title="Focus. The deadline is today.",
        description=(
            "Pip sits down to work, types for one bar, and the groove wins. A record scratch: the deadline. Focus. "
            "The groove creeps back anyway.\n"
            "Episode 07, the first in the Soft style: every pose lands on the beat."
        ),
        credit="Voice: ElevenLabs premade voice Will. Music synthesised in code.",
        hashtags=(
            "#focusmode",
            "#deadline",
            "#procrastination",
            "#officehumor",
            "#workcomedy",
            "#animatedshorts",
            "#vectoranimation",
        ),
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
    "the-router": "the-router",
    "mushroom-training": "mushroom-training",
    "focus-mode": "focus-mode",
    "camera-off": "camera-off",
}


def write_all(out: Path) -> list[Path]:
    """Write ``<out>/<video name>/ig.txt`` for every post; ``out`` is created with mode 700."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    out.chmod(0o700)
    paths = []
    for slug, post in POSTS.items():
        folder = out / VIDEOS[slug]
        paths.append(post.write(folder))
        folder.chmod(0o700)
    return paths


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    for p in write_all(Path(sys.argv[1])):
        print(p)
