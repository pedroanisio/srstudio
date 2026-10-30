#!/usr/bin/env python3
"""Just One Thing: generated dialogue and effects, resolved by the engine, and the timeline.

    srstudio record just-one-thing PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, its effects, and its cuts
(:func:`extra`). Milo goes in for light bulbs, walks out with a kayak, and sits in it in the dark. He is walking from
frame one (arm B of the ``sp-hook_motion`` test). Milo is Liam.
"""

from __future__ import annotations

from srstudio.interview import NOTO_SANS_BOLD, Interview, Schedule, Sound, Spoken, Timing, main
from srstudio.song import Singer

SEED = 26201
CLICK = "A loud sharp plastic light switch click, very close to the microphone, one hard snap, no voices, no music"
VOICES = {"milo": Singer("TX3LPaxmHKxFdv7VOQHJ", "Liam", dict(stability=0.45, similarity_boost=0.75, style=0.30))}
SCRIPT = [  # role, text, caption, speed
    Spoken("milo", "I only need light bulbs.", "I only need light bulbs.", 1.05),
    Spoken("milo", "We do need a plant.", "We do need a plant.", 1.05),
    Spoken("milo", "It was on sale.", "It was on sale.", 1.00),
    Spoken("milo", "That's just safety.", "That's just safety.", 1.00),
]
EFFECTS = [
    Sound(
        "cart",
        "A rattling metal shopping cart rolling fast down a store aisle, squeaky wheel, no voices, no music",
        5.6,
        5.4,
        0.20,
        seed=SEED + 1,
    ),
    Sound(
        "cart-on",
        "A rattling metal shopping cart rolling fast down a store aisle, squeaky wheel, no voices, no music",
        5.6,
        1.5,
        0.20,
        seed=SEED + 1,
    ),
    Sound(
        "beeps",
        "Fast supermarket checkout scanner beeps, one after another without stopping, no voices, no music",
        2.6,
        2.4,
        0.26,
        seed=SEED + 2,
    ),
    Sound("click-1", CLICK, 0.8, 0.5, 0.42, seed=SEED + 4),
    Sound("click-2", CLICK, 0.8, 0.5, 0.42, seed=SEED + 4),
    Sound("click-3", CLICK, 0.8, 0.5, 0.42, seed=SEED + 4),
    Sound("click-4", CLICK, 0.8, 0.5, 0.42, seed=SEED + 4),
]
ROLL = 2.5  # the screen rolling on, with his pride
DARK = 5.5  # the dark to the end, with a fourth click after longer than is comfortable
INTERVIEW = Interview(
    slug="just-one-thing",
    title="Just One Thing",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=EFFECTS,
    voice_note="ElevenLabs premade voice Liam; no reference-voice cloning.",
    room_tone_seed=SEED + 10,
    reaction_after=0.30,
    reaction_hold=ROLL + DARK,
    end_card=0.0,
    font=NOTO_SANS_BOLD,
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts and effect starts from the clip lengths: each line lands on its own cart."""
    starts: list[float] = []
    fx: dict[str, float] = {"cart": 0.0}
    end = 0.2
    for i, gap in enumerate((0.0, 0.6, 0.55, 0.55)):
        starts.append(end + gap)
        end = starts[-1] + speech[i]
    till = end + 0.30
    fx["cart-on"] = starts[3] - 0.30
    fx["beeps"] = till + 0.05
    dark = till + ROLL
    fx["click-1"] = dark + 0.70
    fx["click-2"] = dark + 1.45
    fx["click-3"] = dark + 2.05
    fx["click-4"] = dark + 4.05
    return Schedule(starts, fx)


def extra(t: Timing) -> dict:
    """The beats the picture keys on and the cuts: basket, cart, bigger cart, biggest, till, the dark."""
    p, fx = t.phrases, t.effects
    till = p[3]["end"] + 0.30
    return {
        "till": till,
        "clicks": [fx["click-1"], fx["click-2"], fx["click-3"], fx["click-4"]],
        "reaction_start": t.reaction,
        "end_card_start": t.ending,
        "camera_cuts": [
            {"time": 0, "angle": "basket"},
            {"time": p[1]["start"] - 0.3, "angle": "cart"},
            {"time": p[2]["start"] - 0.3, "angle": "bigger"},
            {"time": p[3]["start"] - 0.3, "angle": "biggest"},
            {"time": till, "angle": "till"},
            {"time": till + ROLL, "angle": "dark"},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))
