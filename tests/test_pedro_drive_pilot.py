"""Pedro drives, then flies: the cut of the 30 s piece is whole, its captions fit the safe area, the world's travel is
continuous, and a missing plate, font or encoder is refused with a typed error."""

from __future__ import annotations

import stat
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PILOTS = ROOT / "episodes" / "pilots"
if str(PILOTS) not in sys.path:
    sys.path.insert(0, str(PILOTS))

import pedro_drive as pilot  # noqa: E402

SHOTS = (pilot.CAR_WIDE, pilot.CAR_CLOSE, pilot.JET_WIDE, pilot.COCKPIT, pilot.JET_AWAY)


def test_the_shots_follow_one_another_and_the_only_gap_is_the_streak_flash_that_cuts_car_to_jet():
    assert SHOTS[0][0] == 0.0 and SHOTS[-1][1] == pilot.DURATION
    gaps = [(a[1], b[0]) for a, b in zip(SHOTS, SHOTS[1:], strict=False) if a[1] != b[0]]
    assert gaps == [(pilot.CAR_CLOSE[1], pilot.JET_WIDE[0])]
    assert pilot.FLASH[0] < gaps[0][0] and gaps[0][1] == pilot.FLASH[1]  # the flash covers the whole gap


@pytest.mark.parametrize(("faces", "shot"), [(pilot.CAR_FACES, pilot.CAR_CLOSE), (pilot.JET_FACES, pilot.COCKPIT)])
def test_each_close_up_is_cast_with_a_plate_at_every_moment_and_only_known_plates(faces, shot):
    assert faces[0][1] == shot[0] and faces[-1][2] == shot[1]
    assert all(a[2] == b[1] for a, b in zip(faces, faces[1:], strict=False))
    assert {name for name, _, _ in faces} <= set(pilot.PLATES)


def test_every_plate_is_used_and_the_car_wears_a_blazer_and_the_pilot_a_puffer_with_glasses():
    used = {name for name, _, _ in (*pilot.CAR_FACES, *pilot.JET_FACES)}
    assert used == set(pilot.PLATES)
    assert all(pilot.PLATES[n][2:] == ("blazer", False) for n in used if n.startswith("car"))
    assert all(pilot.PLATES[n][2:] == ("puffer", True) for n in used if n.startswith("jet"))


def test_the_captions_sit_in_the_vertical_safe_area_and_do_not_overlap_in_time():
    # safe area: top 11.46 %, right 14.81 %, bottom 26.04 %, left 7.41 % (one pixel of rounding in the piece's margins)
    assert pilot.SAFE_X >= 0.0741 * pilot.W - 1 and pilot.SAFE_X + pilot.SAFE_W <= (1 - 0.1481) * pilot.W + 1
    for text, start, end, y in pilot.CAPTIONS:
        assert text and 0.0 <= start < end <= pilot.DURATION
        assert 0.1146 * pilot.H < y - 90 and y + 90 < (1 - 0.2604) * pilot.H  # the 180 px caption box is clear
    assert all(a[2] <= b[1] for a, b in zip(pilot.CAPTIONS, pilot.CAPTIONS[1:], strict=False))


def test_the_world_cruises_queues_to_a_halt_and_goes_again_with_one_jump_hidden_by_the_flash():
    assert pilot.speed(0.0) == 1.0 and pilot.speed(7.0) == 0.0 and pilot.speed(15.0) == 2.2
    assert pilot.speed(29.99) > 2.2
    samples = [(i / 600, pilot.speed(i / 600)) for i in range(600 * 30)]
    assert min(v for _, v in samples) == 0.0
    jumps = [t for (t, a), (_, b) in zip(samples, samples[1:], strict=False) if abs(a - b) >= 0.01]
    assert jumps and all(pilot.FLASH[0] <= t < pilot.FLASH[1] for t in jumps)  # only the cut to the jet jumps


def test_the_distance_grows_with_every_frame_and_stands_still_while_the_car_queues():
    travel = pilot.distance(pilot.FPS * 30)
    assert len(travel) == 900 and travel[0] == pytest.approx(pilot.speed(0.0) / pilot.FPS)
    steps = travel[1:] - travel[:-1]
    assert (steps >= 0).all()
    halted = round(7.0 * pilot.FPS)
    assert travel[halted + 5] == pytest.approx(travel[halted])


def test_smooth_is_a_clamped_ease_and_inside_is_half_open():
    assert (pilot.smooth(-1), pilot.smooth(0.5), pilot.smooth(2)) == (0.0, 0.5, 1.0)
    assert pilot.inside((1.0, 2.0), 1.0) and not pilot.inside((1.0, 2.0), 2.0)


def test_a_missing_caption_font_is_refused_and_named(tmp_path, monkeypatch):
    monkeypatch.setenv("SRSTUDIO_FONTS", str(tmp_path / "none"))
    with pytest.raises(pilot.DriveError, match="caption font .* is missing"):
        pilot.Piece(tmp_path / "out")


def test_a_piece_without_a_fonts_directory_is_refused_and_says_what_to_set(tmp_path, monkeypatch):
    monkeypatch.delenv("SRSTUDIO_FONTS", raising=False)
    with pytest.raises(pilot.DriveError, match="SRSTUDIO_FONTS must name"):
        pilot.Piece(tmp_path / "out")
    monkeypatch.setenv("SRSTUDIO_FONTS", "")
    with pytest.raises(pilot.DriveError, match="SRSTUDIO_FONTS must name"):
        pilot.Piece(tmp_path / "out")


def test_a_plate_to_render_needs_the_engine_and_a_plates_directory_and_says_which(tmp_path, monkeypatch):
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    (fonts / f"{pilot.FONT}.ttf").write_bytes(b"not a font, only read for its hash")
    monkeypatch.setenv("SRSTUDIO_FONTS", str(fonts))
    monkeypatch.delenv("SRSTUDIO_ENGINE", raising=False)
    with pytest.raises(pilot.DriveError, match="SRSTUDIO_ENGINE must name"):
        pilot.Piece(tmp_path / "out").plate("car-calm")
    monkeypatch.setenv("SRSTUDIO_ENGINE", "engine")
    monkeypatch.delenv("SRSTUDIO_PLATES", raising=False)
    monkeypatch.delenv("SRSTUDIO_RENDERS", raising=False)
    with pytest.raises(pilot.DriveError, match="SRSTUDIO_RENDERS must name"):
        pilot.Piece(tmp_path / "out").plate("car-calm")


def test_a_plate_nobody_drew_is_refused_with_the_choices_named(tmp_path, monkeypatch):
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    (fonts / f"{pilot.FONT}.ttf").write_bytes(b"not a font, only read for its hash")
    monkeypatch.setenv("SRSTUDIO_FONTS", str(fonts))
    with pytest.raises(pilot.DriveError, match="no plate called 'car-asleep'.*car-calm"):
        pilot.Piece(tmp_path / "out").plate("car-asleep")


def fake_engine(tmp_path: Path, code: int) -> Path:
    engine = tmp_path / "engine"
    engine.write_text(f"#!/bin/sh\necho out >&1\necho err >&2\nexit {code}\n")
    engine.chmod(engine.stat().st_mode | stat.S_IXUSR)
    return engine


def test_the_encode_calls_the_software_encoder_and_a_failing_one_raises_a_typed_error(tmp_path):
    scene = tmp_path / "x.scene.xml"
    scene.write_text("<scene/>")
    assert pilot.encode(scene, fake_engine(tmp_path, 0)) == tmp_path / "x.scene.mp4"
    with pytest.raises(pilot.DriveError, match=r"encode failed \(3\)[\s\S]*err"):
        pilot.encode(scene, fake_engine(tmp_path, 3))


def test_main_needs_a_folder_and_encodes_only_when_asked(tmp_path, monkeypatch, capsys):
    with pytest.raises(SystemExit):
        pilot.main(["pedro_drive"])
    built = []

    class Stub:
        def __init__(self, root):
            self.root = root

        def build(self):
            built.append(self.root)
            return self.root / "s.scene.xml"

    monkeypatch.setattr(pilot, "Piece", Stub)
    monkeypatch.setenv("SRSTUDIO_ENGINE", "engine")
    ran = []
    assert pilot.main(["pedro_drive", str(tmp_path / "o")], run=lambda s, e: ran.append(e) or s) == 0
    assert built and not ran
    assert pilot.main(["pedro_drive", str(tmp_path / "o"), "--encode"], run=lambda s, e: ran.append(e) or s) == 0
    assert ran == [Path("engine")]
    assert "s.scene.xml" in capsys.readouterr().out
