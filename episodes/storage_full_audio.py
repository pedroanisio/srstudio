#!/usr/bin/env python3
"""Storage Full — Comedy Cut 23: generated dialogue and effects, resolved by the engine, and the timeline.

    srstudio record storage-full PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview` (resolve, the speech check, trimming, levelling, the room tone and
``dialogue.json``); this file is the episode: its script, its effects, where the backflip, the chimes and the
flutter sit between the lines (:func:`schedule`) and its camera cuts (:func:`extra`). A pigeon walks up the park
path and does a backflip in front of Milo's bench. "No way. Do that again!" The phone: "Storage full." It offers
the sunsets, then the wedding video; the pigeon waits; Milo says yes; "Recording." The pigeon leaves. Then a message
from his wife. The opening moves from the first frame (the ``sp-hook_motion`` test's arm B): the pigeon is already
walking and the camera already pushing in. The voices: Liam (Milo, as in the café episodes) and Alice (the phone).
"""

from __future__ import annotations

from srstudio.interview import Interview, Schedule, Sound, Spoken, Timing, main
from srstudio.song import Singer

SEED = 23041
VOICES = {
    "milo": Singer("TX3LPaxmHKxFdv7VOQHJ", "Liam", dict(stability=0.45, similarity_boost=0.75, style=0.25)),
    "phone": Singer("Xb7hH8MSUJpSbSDYk0k2", "Alice", dict(stability=0.80, similarity_boost=0.75, style=0.05)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("milo", "No way.", "No way.", 1.00),
    Spoken("milo", "Do that again!", "Do that again!", 1.05),
    Spoken("phone", "Storage full.", "Storage full.", 0.95),
    Spoken("milo", "Delete something!", "Delete something!", 1.05),
    Spoken("phone", "Delete fourteen photos of the same sunset?", "Delete fourteen photos\nof the same sunset?", 1.00),
    Spoken("milo", "Yes!", "Yes!", 1.05),
    Spoken("phone", "Still full.", "Still full.", 0.95),
    Spoken("phone", "Delete your wedding video?", "Delete your\nwedding video?", 0.95),
    Spoken("milo", "Yes.", "…Yes.", 0.90),
    Spoken("phone", "Recording.", "Recording.", 0.95),
    Spoken(
        "phone",
        "Message from Wife. Can you send me our wedding video?",
        "Message from Wife:\n“Can you send me our wedding video?”",
        0.95,
    ),
]
CHIME = "A short soft smartphone notification chime, two gentle bright notes, close, no voices, no music"
EFFECTS = [
    Sound(
        "whoosh",
        "A quick cartoon whoosh of a small bird doing a backflip in the air, then a tiny soft landing tap, no voices, "
        "no music",
        1.0,
        0.7,
        0.34,
        seed=SEED + 1,
    ),
    Sound("chime-1", CHIME, 0.8, 0.5, 0.28, seed=SEED + 2),
    Sound("chime-2", CHIME, 0.8, 0.5, 0.28, seed=SEED + 3),
    Sound("chime-3", CHIME, 0.8, 0.5, 0.28, seed=SEED + 4),
    Sound(
        "flutter",
        "A single pigeon taking off from a park path, a short burst of wing flaps fading away, outdoors, no voices, "
        "no music",
        1.5,
        1.2,
        0.30,
        seed=SEED + 5,
    ),
]
INTERVIEW = Interview(
    slug="storage-full",
    title="Storage Full — Comedy Cut 23",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=EFFECTS,
    voice_note="ElevenLabs premade voices Liam and Alice; no reference-voice cloning.",
    room_tone_seed=SEED + 10,
    reaction_after=0.45,  # the message read out, then Milo's look into the lens
    reaction_hold=1.50,
    end_card=0.0,  # no card: his look is the last frame
)
FLIP = 1.20  # the backflip starts: the pigeon has walked up the path and stopped
FLIP_LENGTH = 0.50
STANDOFF = 1.60  # after "Delete your wedding video?": Milo and the pigeon look at each other
GONE = 0.70  # after the flutter: the empty path, before the message


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts and effect starts from the clip lengths: the gags sit in the gaps between lines."""
    starts: list[float] = []
    fx: dict[str, float] = {"whoosh": FLIP - 0.05}

    def say(i: int, at: float) -> float:
        starts.append(at)
        return at + speech[i]

    end = say(0, FLIP + FLIP_LENGTH + 0.35)
    end = say(1, end + 0.25)
    fx["chime-1"] = end + 0.70  # the pigeon nods: ready; the phone is not
    end = say(2, fx["chime-1"] + 0.15)
    end = say(3, end + 0.25)
    end = say(4, end + 0.20)
    end = say(5, end + 0.15)
    end = say(6, end + 0.30)
    fx["chime-2"] = end + 0.55  # the pigeon looks away, bored
    end = say(7, fx["chime-2"] + 0.15)
    end = say(8, end + STANDOFF)
    end = say(9, end + 0.30)
    fx["flutter"] = end + 0.15
    fx["chime-3"] = fx["flutter"] + effect["flutter"] + GONE
    say(10, fx["chime-3"] + 0.20)
    return Schedule(starts, fx)


def extra(t: Timing) -> dict:
    """The beats the picture keys on, and the cuts between the park, Milo and the pigeon."""
    p, fx = t.phrases, t.effects

    def before(i: int) -> float:
        return p[i]["start"] - 0.10

    stare = p[7]["end"] + 0.10
    return {
        "flip_start": FLIP,
        "flip_end": FLIP + FLIP_LENGTH,
        "chimes": [fx["chime-1"], fx["chime-2"], fx["chime-3"]],
        "flutter_start": fx["flutter"],
        "stare_start": stare,
        "reaction_start": t.reaction,
        "end_card_start": t.ending,
        "camera_cuts": [
            {"time": 0, "angle": "wide"},  # the walk-up and the backflip, the camera pushing in
            {"time": before(0), "angle": "milo"},
            {"time": p[1]["end"] + 0.10, "angle": "pigeon"},  # it nods: ready
            {"time": fx["chime-1"] - 0.05, "angle": "milo"},
            {"time": before(3), "angle": "wide"},  # "Delete something!": the pigeon waits on the path
            {"time": before(4), "angle": "milo"},
            {"time": p[5]["end"] + 0.05, "angle": "pigeon"},  # "Still full.": bored, it looks away
            {"time": fx["chime-2"] - 0.05, "angle": "milo"},
            {"time": stare, "angle": "pigeon"},  # the standoff: the pigeon stares back
            {"time": stare + 0.75, "angle": "milo"},
            {"time": before(9), "angle": "wide"},  # "Recording." and the pigeon leaves
            {"time": fx["chime-3"] - 0.05, "angle": "milo"},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))
