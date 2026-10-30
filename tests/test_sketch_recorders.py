"""The Toon and Collage sketch helpers hand their recording scripts a ready ``main``: the shared command line of
:mod:`srstudio.recording` around the helper's ``record_episode``, with the same arguments the scripts passed."""

from pathlib import Path

import pytest

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture
def helpers(monkeypatch):
    monkeypatch.syspath_prepend(str(EPISODES))
    from srstudio import collage_sketch, toon_sketch

    return toon_sketch, collage_sketch


def test_the_toon_recorder_passes_the_sketch_seed_note_and_mouth(helpers, monkeypatch, tmp_path):
    toon, _ = helpers
    got = []
    monkeypatch.setattr(toon, "record_episode", lambda *a, **k: got.append((a, k)))
    main = toon.recorder("SKETCH", 7, "note", "Doc\n\nmore", mouth="MOUTH")
    assert main([str(tmp_path), "--ffmpeg", "ff"], {"K": "v"}) == 0
    assert got == [
        (
            ("SKETCH", tmp_path.resolve(), {"K": "v"}, "ff", 7, "note"),
            {"mouth": "MOUTH", "foley_of": toon.sound_effects, "sounds": None},
        )
    ]


def test_the_toon_recorder_passes_a_reels_own_foley(helpers, monkeypatch, tmp_path):
    toon, _ = helpers
    got = []
    foley = lambda *a: []  # noqa: E731
    monkeypatch.setattr(toon, "record_episode", lambda *a, **k: got.append(k))
    assert toon.recorder("SKETCH", 7, "note", "Doc", foley_of=foley)([str(tmp_path)], {}) == 0
    assert got[0]["foley_of"] is foley


def test_the_toon_recorder_keeps_the_default_mouth_when_none_is_named(helpers, monkeypatch, tmp_path):
    toon, _ = helpers
    got = []
    monkeypatch.setattr(toon, "record_episode", lambda *a, **k: got.append(k))
    toon.recorder("SKETCH", 7, "note", "Doc")([str(tmp_path)], {})
    assert got == [{"mouth": toon.sketch.MOUTH_STYLE, "foley_of": toon.sound_effects, "sounds": None}]


def test_the_toon_recorder_validates_the_sketch_after_parsing_and_before_recording(helpers, monkeypatch, tmp_path):
    toon, _ = helpers
    order = []
    monkeypatch.setattr(toon, "record_episode", lambda *a, **k: order.append("record"))
    main = toon.recorder("SKETCH", 7, "note", "Doc", validate=lambda sk: order.append(f"validate {sk}"))
    with pytest.raises(SystemExit):
        main([], {})
    assert order == []
    main([str(tmp_path)], {})
    assert order == ["validate SKETCH", "record"]


def test_a_failed_validation_records_nothing(helpers, monkeypatch, tmp_path):
    toon, _ = helpers
    order = []
    monkeypatch.setattr(toon, "record_episode", lambda *a, **k: order.append("record"))

    def refuse(sk):
        raise toon.sketch.SketchError("bad events")

    with pytest.raises(toon.sketch.SketchError, match="bad events"):
        toon.recorder("SKETCH", 7, "note", "Doc", validate=refuse)([str(tmp_path)], {})
    assert order == []


def test_the_collage_recorder_passes_the_staging_note_and_mouth(helpers, monkeypatch, tmp_path):
    _, collage = helpers
    got = []
    monkeypatch.setattr(collage, "record_episode", lambda *a, **k: got.append((a, k)))
    main = collage.recorder("STAGING", "note", "Doc", mouth="MOUTH")
    assert main([str(tmp_path)], {}) == 0
    (staging, project, env, _ffmpeg, note), kw = got[0]
    assert (staging, project, env, note, kw) == ("STAGING", tmp_path.resolve(), {}, "note", {"mouth": "MOUTH"})


def test_a_recorder_refuses_a_missing_project(helpers):
    toon, _ = helpers
    with pytest.raises(SystemExit):
        toon.recorder("SKETCH", 7, "note", "Doc")([], {})


@pytest.mark.parametrize(
    ("script", "flags", "options"),
    [
        ("employee_survey_audio", [], {}),
        ("mushroom_training_audio", [], {}),
        ("check_with_my_team_audio", ["--key-stdin"], {"key_stdin": True}),
        ("the_router_audio", ["--font", "fonts"], {"font": Path("fonts")}),
    ],
)
def test_the_bespoke_recorders_share_the_recording_command_line(monkeypatch, tmp_path, script, flags, options):
    monkeypatch.syspath_prepend(str(EPISODES))
    module = __import__(script)
    got = []
    monkeypatch.setattr(module, "record", lambda *a, **k: got.append((a, k)))
    assert module.main([str(tmp_path), "--ffmpeg", "ff", *flags], {"K": "v"}) == 0
    assert got == [((tmp_path.resolve(), {"K": "v"}, "ff"), options)]
