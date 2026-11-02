"""The Toon dance proof (ADR 0190): a valid scene with its track, numbers that meet the measured car dance, a review
page that opens as a local file, and, with the engine, the groove read back out of rendered pictures."""

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

from srstudio import dance as dn

SCRIPT = Path(__file__).resolve().parents[1] / "examples" / "toon_dance.py"


def example():
    spec = importlib.util.spec_from_file_location("toon_dance_example", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("toon-dance")
    module = example()
    assert module.main([str(out), "--no-engine"]) == 0
    return module, out


def test_the_routine_is_seated_and_raises_the_arm_for_the_last_four_seat_bars():
    routine = example().routine()
    assert routine.support == "seat" and routine.track_bars == 14
    seat = [e for e in routine.entries if e.move.name == "seat-groove"]
    assert [(e.start_bar, e.end_bar, bool(e.hold)) for e in seat] == [(0, 4, False), (4, 8, True)]
    assert [e.move.name for e in routine.entries[2:]] == ["head-nod", "shoulder-shimmy", "arm-pump"]


def test_the_proof_scene_holds_the_dance_and_its_track(built):
    module, out = built
    scene = (out / "dance-toon.scene.xml").read_text()
    assert 'src="track.wav"' in scene and "audioMix" in scene and 'path="dance-toon.mp4"' in scene
    assert (out / "track.wav").stat().st_size > 1000
    assert oct((out / "dance-toon.scene.xml").stat().st_mode & 0o777) == "0o600"


def test_the_numbers_meet_the_seat_groove(built):
    _, out = built
    numbers = json.loads((out / "measurements.json").read_text())
    assert numbers["numbers"]["bob"]["misses"] == [] and numbers["numbers"]["sway"]["misses"] == []
    assert numbers["numbers"]["clamped"] == 0 and "rendered" not in numbers


def test_the_page_is_local_and_says_what_was_not_rendered(built):
    module, out = built
    text = (out / "index.html").read_text()
    assert 'src="dance-toon.mp4"' in text and "What to judge" in text and "no engine was given" in text
    assert "views.mp4" not in text  # the three-view video is shown only when it is there
    assert "https://" not in text and "http://" not in text  # nothing to fetch: it opens as a local file
    (out / "views.mp4").write_bytes(b"")
    numbers = json.loads((out / "measurements.json").read_text())
    numbers["rendered"] = {**numbers["numbers"], "pictures": 3, "radius_px": 58.4}
    numbers["rendered"]["sway"] = {**numbers["rendered"]["sway"], "misses": ["peak to peak 0.3, not 0.17..0.23"]}
    text = module.page(out, numbers).read_text()
    assert 'src="views.mp4"' in text and "top (x, z, front down the screen)" in text
    assert "peak to peak 0.3, not 0.17..0.23" in text and "Measured on rendered pictures" in text


def test_the_example_needs_an_engine_or_says_it_has_none(tmp_path, monkeypatch):
    monkeypatch.delenv("SRSTUDIO_ENGINE", raising=False)
    with pytest.raises(SystemExit):
        example().main([str(tmp_path)])


def test_the_rendered_pictures_hold_the_groove(tmp_path):
    engine = os.environ.get("SRSTUDIO_ENGINE")
    if not engine:
        pytest.skip("set SRSTUDIO_ENGINE to read the groove out of rendered pictures")
    pytest.importorskip("PIL")
    reading = example().rendered(tmp_path, engine)
    for axis, target in (("bob", dn.SEAT_GROOVE_BOB), ("sway", dn.SEAT_GROOVE_SWAY)):
        assert reading[axis]["cycles_per_beat"] == pytest.approx(1, abs=0.02)
        assert abs(reading[axis]["hit_offset_s"]) <= 0.02  # the drop lands on the beat
        assert reading[axis]["misses"] == [], (axis, target)
