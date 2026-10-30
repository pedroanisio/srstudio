"""What test_ink_layout.py shares with other test modules."""

from sr_core.scene import Scene

from srstudio import MONO, Canvas, Timeline, shared_counter


def phones(text, step=0.08):
    return [{"c": c, "start": i * step, "end": (i + 1) * step} for i, c in enumerate(text)]


# -- the talking router (Ink 02) -------------------------------------------------------------------------
def router_take(actor="router", shot="router", text="Hi. Everything okay over there?", **kw):
    data = dict(
        id="02",
        actor=actor,
        shot=shot,
        text=text,
        mood="calm",
        start=0.0,
        duration=2.2,
        speech_duration=2.0,
        audio="audio/take-02.wav",
        words=({"text": "Hi.", "start": 0.05, "end": 0.4}, {"text": "Everything", "start": 0.6, "end": 1.1}),
        phones=phones("hi. everything okay over there?", 0.06),
    )
    data.update(kw)
    return Timeline.from_dict({"duration": 2.2, "items": [data]}).takes[0]


def square_canvas(signed=True):
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1080, fps="24", duration=3)
    from srstudio import Signature

    cv = Canvas(
        scene,
        MONO,
        width=1080,
        height=1080,
        namer=shared_counter(),
        local_time=True,
        signature=Signature("SR-1028") if signed else None,
    )
    return scene, cv


WORDS = [
    {"text": "Okay.", "start": 0.02, "end": 0.54},
    {"text": "Come", "start": 0.72, "end": 0.79},
    {"text": "on.", "start": 0.86, "end": 1.35},
    {"text": "Come", "start": 1.49, "end": 1.56},
    {"text": "on!", "start": 1.62, "end": 2.03},
]


def takes_data():
    return {
        "duration": 6.0,
        "tempo_adjustment": 1.0,
        "items": [
            {
                "id": "01",
                "actor": "human",
                "shot": "desk",
                "text": "Okay. Come on. Come on!",
                "mood": "impatient",
                "start": 0,
                "duration": 2.1,
                "speech_duration": 2.03,
                "audio": "audio/conform-01.wav",
                "words": WORDS,
                "phones": phones("okay come on come on"),
            },
            {
                "id": "02",
                "actor": "sfx",
                "shot": "printer",
                "text": "[PRINTER WHIRRS]",
                "seconds": 1.35,
                "start": 2.1,
                "duration": 1.35,
                "speech_duration": 0,
                "audio": "audio/printer-02.wav",
            },
            {
                "id": "03",
                "actor": "printer",
                "shot": "printer-close",
                "text": "Magenta!",
                "mood": "smug",
                "start": 3.45,
                "duration": 1.2,
                "speech_duration": 1.1,
                "audio": "audio/conform-03.wav",
                "words": [{"text": "Magenta!", "start": 0.05, "end": 1.0}],
                "phones": phones("magenta!"),
            },
            {
                "id": "04",
                "actor": "human",
                "shot": "human",
                "text": "Aaargh!",
                "mood": "scream",
                "start": 4.65,
                "duration": 1.35,
                "speech_duration": 0.9,
                "audio": "audio/conform-04.wav",
                "words": [{"text": "Aaargh!", "start": 0.05, "end": 0.9}],
                "phones": phones("aaargh!"),
            },
        ],
    }
