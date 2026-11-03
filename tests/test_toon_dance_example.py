"""The Toon dance proof (ADR 0190): a valid scene with its track, numbers that meet the measured car dance, a review
page that opens as a local file, and, with the engine, the groove read back out of rendered pictures."""

import importlib.util
import json
import os
import sys
import xml.etree.ElementTree as ET
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


def test_the_proof_pins_the_approved_drop_and_can_draw_the_shipped_one():
    module = example()
    shipped = dn.moves()["seat-groove"]

    def drop(move):
        return [p.amplitude for p in move.patterns if p.target == "root.up"]

    assert drop(module.seat_groove()) == [module.APPROVED_BOB] == [-0.19]
    assert drop(module.seat_groove(None)) == drop(shipped) and module.seat_groove(None) == shipped
    assert {e.move for e in module.routine().entries[:2]} == {module.seat_groove()}
    assert {e.move for e in module.routine(None).entries[:2]} == {shipped}


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


def test_the_page_is_local_in_portuguese_and_says_what_was_not_rendered(built):
    module, out = built
    text = (out / "index.html").read_text()
    assert '<html lang="pt-BR">' in text and 'src="dance-toon.mp4"' in text
    assert "O que mudou" in text and "O que julgar" in text and "nenhum motor foi dado" in text
    assert "views.mp4" not in text and "arms.png" not in text  # shown only when they are there
    assert "../v1/index.html" not in text  # the previous version is linked only when it is there
    assert "https://" not in text and "http://" not in text  # nothing to fetch: it opens as a local file
    (out / "views.mp4").write_bytes(b"")
    (out / "arms.png").write_bytes(b"")
    (out.parent / "v1").mkdir(exist_ok=True)
    (out.parent / "v1" / "index.html").write_text("")
    numbers = json.loads((out / "measurements.json").read_text())
    numbers["rendered"] = {**numbers["numbers"], "pictures": 3, "radius_px": 58.4}
    numbers["rendered"]["sway"] = {**numbers["rendered"]["sway"], "misses": ["peak to peak 0.3, not 0.17..0.23"]}
    numbers["stills"] = {"arm_pixels": 1000, "arm_pixels_differ": 12, "raised_frame": 279}
    text = module.page(out, numbers).read_text()
    assert 'src="views.mp4"' in text and "topo (x, z, a frente para baixo na tela)" in text
    assert "peak to peak 0.3, not 0.17..0.23" in text and "Medido nas imagens renderizadas" in text
    assert 'src="arms.png"' in text and "12 diferem (1.20%)" in text and "imagem 279" in text
    assert 'href="../v1/index.html"' in text


def test_the_still_scenes_draw_the_dance_at_rest_and_the_approved_drawing(tmp_path):
    rest, approved = example().still_scenes(tmp_path)
    rest_ids = {e.get("id") or "" for e in ET.parse(rest).iter()}
    approved_ids = {e.get("id") or "" for e in ET.parse(approved).iter()}
    assert any(i.startswith("arm-left-") for i in rest_ids)  # the dance's own arms
    assert not any(i.startswith("arm-") for i in approved_ids)  # the rig's own desk arms


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
