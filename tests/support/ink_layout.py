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
