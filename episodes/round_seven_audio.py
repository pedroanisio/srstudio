#!/usr/bin/env python3
"""Round Seven: generated dialogue, resolved by the engine, and the timeline.

    srstudio record round-seven PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, where each line sits (:func:`schedule`)
and its cuts (:func:`extra`). The seventh round of interviews at a building that already gave him a parking space. Ava
is Jessica, the Candidate Will and the Boss Eric, as in the interview reels. There is no music, and the foley is
synthesized in the build. He walks in on the first frame, and the first word comes by 0.45 s.
"""

from __future__ import annotations

from srstudio.interview import NOTO_SANS_BOLD, Interview, Schedule, Spoken, Timing, main
from srstudio.song import Singer

SEED = 3311
VOICES = {
    "barista": Singer("cgSgspJ2msm6clMCkdW9", "Jessica", dict(stability=0.45, similarity_boost=0.75, style=0.25)),
    "candidate": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.42, similarity_boost=0.75, style=0.20)),
    "manager": Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.55, similarity_boost=0.75, style=0.15)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("barista", "Morning! Round seven?", "Morning! Round seven?", 1.05),
    Spoken("candidate", "Round seven.", "Round seven.", 0.95),
    Spoken("manager", "So. Tell me about yourself.", "So. Tell me about yourself.", 1.00),
    Spoken("candidate", "We've met. Six times.", "We've met. Six times.", 0.98),
    Spoken("manager", "Great energy. One more round.", "Great energy.\nOne more round.", 1.02),
    Spoken("barista", "Your parking space came through.", "Your parking space came through.", 1.02),
    Spoken("candidate", "I don't work here.", "I don't work here.", 1.00),
    Spoken("barista", "You're a fire warden.", "You're a fire warden.", 1.00),
    Spoken("barista", "Surprise!", "Surprise!", 1.05),
    Spoken("candidate", "Do I have the job?", "Do I have the job?", 0.96),
    Spoken("manager", "It's between you and Dave.", "It's between you and Dave.", 0.98),
    Spoken("barista", "Dave has a pension.", "Dave has a pension.", 0.90, gain=-4.0),
]
START = 0.42  # the first word: he is already walking in
HUSH = 1.30  # after "Surprise!": the held bracket, no speech and no new caption
TURN = 0.55  # "Dave." to the crash zoom: he turns to Ava, she nods at the wall
READ = 1.70  # the plaque, held long enough to read twice
ENDING = 0.80  # the last line, held
INTERVIEW = Interview(
    slug="round-seven",
    title="Round Seven",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Jessica, Will and Eric; no voice cloning. Foley synthesized; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=0.05,
    reaction_hold=ENDING,
    end_card=0.0,
    font=NOTO_SANS_BOLD,
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: quick exchanges, four short scenes, the hush, the plaque and the whisper."""
    starts: list[float] = []

    def say(i: int, at: float) -> float:
        starts.append(at)
        return at + speech[i]

    end = say(0, START)
    end = say(1, end + 0.30)
    end = say(2, max(end + 0.55, 3.10))
    end = say(3, end + 0.30)
    end = say(4, end + 0.30)
    end = say(5, end + 0.70)
    end = say(6, end + 0.30)
    end = say(7, end + 0.30)
    end = say(8, end + 0.70)
    end = say(9, end + HUSH)
    end = say(10, end + 0.30)
    say(11, end + TURN + READ)
    return Schedule(starts, {})


def extra(t: Timing) -> dict:
    """The beats the picture keys on, and the cuts: the lobby, the desk and the chair, and the lobby again."""
    p = t.phrases
    zoom = p[10]["end"] + TURN
    return {
        "lanyard": p[5]["start"] - 0.25,
        "turn": p[10]["end"] + 0.08,
        "zoom": zoom,
        "camera_cuts": [
            {"time": 0, "angle": "arrive"},
            {"time": 3.0, "angle": "desk"},
            {"time": p[3]["start"] - 0.05, "angle": "chair"},
            {"time": p[4]["start"] - 0.05, "angle": "desk"},
            {"time": p[5]["start"] - 0.45, "angle": "lanyard"},
            {"time": p[8]["start"] - 0.25, "angle": "party"},
            {"time": zoom, "angle": "plaque"},
            {"time": p[11]["start"] - 0.20, "angle": "whisper"},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))
