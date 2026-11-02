#!/usr/bin/env python3
"""Trial Shift: generated dialogue, resolved by the engine, and the timeline.

    srstudio record trial-shift PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, where each line sits (:func:`schedule`)
and its beats (:func:`extra`). Milo is Liam, Ava is Jessica and the Candidate is Will. There is no music, and the foley
is synthesized in the build.
"""

from __future__ import annotations

from srstudio.interview import NOTO_SANS_BOLD, Interview, Schedule, Spoken, Timing, main
from srstudio.song import Singer

SEED = 3607
VOICES = {
    "ava": Singer("cgSgspJ2msm6clMCkdW9", "Jessica", dict(stability=0.45, similarity_boost=0.75, style=0.25)),
    "milo": Singer("TX3LPaxmHKxFdv7VOQHJ", "Liam", dict(stability=0.45, similarity_boost=0.75, style=0.25)),
    "candidate": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.42, similarity_boost=0.75, style=0.25)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("milo", "How long have you worked here?", "How long have you\nworked here?", 1.00),
    Spoken("ava", "I don't. It's just a quick trial shift.", "I don't. It's just\na quick trial shift.", 1.00),
    Spoken("milo", "When did it start?", "When did it start?", 1.00),
    Spoken("ava", "April.", "April.", 1.00),
    Spoken("milo", "That's not so bad.", "That's not so bad.", 1.00),
    Spoken("ava", "2019.", "2019.", 0.95),
    Spoken("candidate", "They'll let us know Friday.", "They'll let us\nknow Friday.", 1.00),
    Spoken("milo", "Which Friday?", "Which Friday?", 1.00),
    Spoken("milo", "Has anyone ever been hired?", "Has anyone ever\nbeen hired?", 1.00),
    Spoken("ava", "Of course!", "Of course!", 1.00),
    Spoken("milo", "Who?", "Who?", 1.00),
    Spoken("milo", "It's just a quick trial shift.", "It's just a quick\ntrial shift.", 0.98),
]  # fmt: skip
CUE = 0.86  # the least a line starts after the one before, so that one's caption cue holds
START = 0.30  # the first word: the apron is already being tied
BEHIND_HIM = 0.95  # after "2019.": Milo's smile, and the Candidate crossing behind him with a tray
THE_TAG = 0.85  # then Ava's tag, seen for the first time
TURNS = 0.60  # after "Which Friday?": the Candidate walks on, Milo turns to Ava
ON_AVA = 0.60  # after "Who?": the smile holds, the chime
LOOK = 0.90  # the wide: the hand at the door, and all three look
LOOKS_DOWN = 0.25  # Milo, at his apron
CROSSES = 0.60  # to the door
TAKES = 0.30  # the spare, off its hook, then the line
ENDING = 0.08  # out on the last word
CAPTION_LEAD = 0.05  # a caption comes on this long before its line
CAPTION_TAIL = 0.20  # and stays this long past it
CAPTION_MIN = 0.84  # a short word's cue is up at least this long
# The picture's numbers the tests read, here because importing the episode runs its build.
MILO_Y, MILO_SIZE, AT_DOOR = 1035.0, 1.4, 270.0
SHOULDER, ARM, REST = (-72.0, 143.0), 96.0, (-96.0, 326.0)  # his left arm, in rig units
HOOK = (226.0, 1440.0)  # hip height on the counter's end, on the wood: his hand drops to it, with the elbow open
HELD_OUT = (90.0, 1400.0)  # low, and clear of his face
TWO = (1.2, -232.0, -320.0)  # scale, x, y of the two-shot: the board clear of the hook line
PASTRY_RIGHT = 365.0  # where the board's "$3" ends in the room
KEY_LEFT = 220.0  # where the hook line's bar starts in the frame
MILO_X, MILO_JAW = 630.0, 125.0  # where he stands, and half his head at the height of the tray
MILO_RIGHT_SHOULDER, MILO_RIGHT_HAND = (73.0, 144.0), (84.0, 332.0)  # once he turns to Ava, in rig units
AVA_SIZE, AVA_APART, AVA_REACH = 1.3, 905.0, 153.0  # from the turn she stands off him: her far hand's reach in the room
AVA_SHOULDER, AVA_HAND = (-66.0, 140.0), (-80.0, 328.0)  # her near arm, close at her side from the turn on
TRAY_SIZE, TRAY_HAND, HAND_RADIUS = 1.35, 122.0, 18.0  # the Candidate's hands, in rig units, on the ends of the tray
TURNS_FRAME = (1.2, -220.0, -320.0)  # the two-shot, slid so the Candidate has the side of the frame
WALKS_ON = (262.0, 245.0)  # through the turn he is past Milo, his arm and his body clear of the head
CODE_LEFT, HEAD_AT_CODE = 381.0, 112.0  # where the board's code starts in the room, and half his head at its height
DOOR_RIGHT, OUT_OF_SIGHT = 198.0, 0.0  # the frame of the door, and where the whole of him is behind it
LEAVES, GONE = 0.15, 0.10  # before Milo looks down, and after he crosses: the Candidate goes, and Milo has the door
INTERVIEW = Interview(
    slug="trial-shift",
    title="Trial Shift",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Liam, Jessica and Will; no voice cloning. Foley synthesized; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=0.05,
    reaction_hold=ENDING,
    end_card=0.0,
    font=NOTO_SANS_BOLD,
)


def cue_off(line: dict) -> float:
    """When a line's caption comes down, unless the next line's takes it first."""
    return max(line["end"] + CAPTION_TAIL, line["start"] - CAPTION_LEAD + CAPTION_MIN)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: a quick back and forth, and the real holds."""
    starts: list[float] = []

    def say(i: int, gap: float) -> float:
        """Line ``i``, ``gap`` after the last one ends, and never before the last one's cue has held."""
        at = max(end + gap, starts[-1] + CUE) if starts else gap
        starts.append(at)
        return at + speech[i]

    end = 0.0
    end = say(0, START)
    end = say(1, 0.15)
    end = say(2, 0.15)
    end = say(3, 0.15)
    end = say(4, 0.15)
    end = say(5, 0.20)
    end = say(6, CAPTION_TAIL + BEHIND_HIM + THE_TAG + CAPTION_LEAD)
    end = say(7, 0.15)
    end = say(8, TURNS)
    end = say(9, 0.15)
    end = say(10, 0.15)
    say(11, ON_AVA + LOOK + LOOKS_DOWN + CROSSES + TAKES)
    return Schedule(starts, {})


def extra(t: Timing) -> dict:
    """The beats the picture keys on, and the cuts: medium, closes, the tag, the two-shots, the wide, the door."""
    p = t.phrases
    behind = cue_off(p[5])
    tag = behind + BEHIND_HIM
    chime = p[10]["end"] + ON_AVA - 0.10
    wide = p[10]["end"] + ON_AVA
    down = wide + LOOK
    crosses = down + LOOKS_DOWN
    arrives = crosses + CROSSES
    return {
        "behind": behind,
        "tag": tag,
        "chime": chime,
        "wide": wide,
        "down": down,
        "crosses": crosses,
        "arrives": arrives,
        "camera_cuts": [
            {"time": 0, "angle": "open"},
            {"time": p[1]["start"] - 0.05, "angle": "ava"},
            {"time": p[2]["start"] - 0.05, "angle": "milo"},
            {"time": p[3]["start"] - 0.05, "angle": "ava"},
            {"time": p[4]["start"] - 0.05, "angle": "milo"},
            {"time": p[5]["start"] - 0.05, "angle": "ava"},
            {"time": behind, "angle": "behind"},
            {"time": tag, "angle": "tag"},
            {"time": p[6]["start"] - 0.05, "angle": "friday"},
            {"time": p[7]["start"] - 0.05, "angle": "milo"},
            {"time": cue_off(p[7]), "angle": "turns"},
            {"time": p[9]["start"] - 0.05, "angle": "ava"},
            {"time": wide, "angle": "wide"},
            {"time": arrives, "angle": "door"},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))
