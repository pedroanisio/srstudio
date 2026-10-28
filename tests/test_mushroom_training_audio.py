"""The narration step of Work Training Be Like: slots from captions, bounded speed-ups, placement, the manifest."""

import hashlib
import json
import sys
import wave
from pathlib import Path

import pytest

from srstudio import cel
from srstudio.voice import RATE

EPISODES = Path(__file__).resolve().parent.parent / "episodes"
BOX = {"x": 1, "y": 1, "w": 1, "h": 1, "glyphs": "M 1 1"}


@pytest.fixture(scope="module")
def narration():
    sys.path.insert(0, str(EPISODES))
    try:
        import mushroom_training_audio
    finally:
        sys.path.pop(0)
    return mushroom_training_audio


def captions(*spans, phase="test"):
    return cel.parse_captions(
        [
            {"id": f"{i + 1:02}", "start": s, "end": e, "text": text, "phase": phase, "boxes": [BOX]}
            for i, (s, e, text) in enumerate(spans)
        ]
    )


def test_slots_run_from_a_caption_to_just_before_the_next_and_the_last_to_the_end(narration):
    caps = captions((0.1, 1.0, "One."), (1.1, 2.0, "Two..."), (2.2, 2.5, "Three."))
    got = narration.slots(caps, 3.0)
    assert [(s.id, s.start, round(s.end, 3)) for s in got] == [("01", 0.1, 1.08), ("02", 1.1, 2.18), ("03", 2.2, 3.0)]
    assert [s.text for s in got] == ["One.", "Two...", "Three."] and got[1].montage is False
    assert narration.slots(captions((0.0, 1.0, "x"), phase="montage"), 1.0)[0].montage is True
    with pytest.raises(ValueError, match="ends at 2.5"):
        narration.slots(caps, 2.4)
    with pytest.raises(ValueError, match="no text"):
        narration.slots(captions((0.0, 1.0, "   ")), 1.0)
    with pytest.raises(ValueError, match="no captions"):
        narration.slots([], 1.0)


def test_retry_speed_is_bounded_and_only_asked_for_when_the_line_overflows(narration):
    assert narration.retry_speed(1.0, 1.2, base=1.08) is None  # fits
    assert narration.retry_speed(1.3, 1.0, base=1.0) == 1.2  # would need 1.33: capped
    assert narration.retry_speed(1.1, 1.0, base=1.0) == 1.12  # 1.1 × 1.02 margin
    assert narration.retry_speed(1.3, 1.0, base=1.2) is None  # already at the cap: nothing more to ask


def test_place_fits_leads_quickens_or_cuts_within_bounds(narration):
    long = narration.Slot("01", "x", False, start=10.0, end=12.0)
    p = narration.place(1.5, long, prev_end=9.0)
    assert (p.start, p.kept, p.lead, p.tempo, p.cut) == (10.0, 1.5, 0.0, 1.0, False)
    p = narration.place(2.2, long, prev_end=9.0)  # overflows by 0.2: starts 0.2 early, nothing else
    assert (round(p.start, 3), round(p.kept, 3), round(p.lead, 3), p.tempo, p.cut) == (9.8, 2.2, 0.2, 1.0, False)
    p = narration.place(2.6, long, prev_end=9.0)  # needs 0.6: the lead is capped at 0.5, the rest is tempo
    assert (round(p.start, 3), round(p.kept, 3), round(p.lead, 3), round(p.tempo, 3), p.cut) == (
        9.5,
        2.5,
        0.5,
        1.04,
        False,
    )
    p = narration.place(3.5, long, prev_end=9.0)  # lead and tempo both capped: the tail is cut
    assert (round(p.start, 3), round(p.kept, 3), round(p.tempo, 3), p.cut) == (9.5, 2.5, 1.15, True)
    p = narration.place(2.6, long, prev_end=9.9)  # the previous line ends late: lead limited by it
    assert (round(p.start, 3), round(p.lead, 3), round(p.tempo, 3), round(p.kept, 3), p.cut) == (
        9.94,
        0.06,
        1.15,
        2.06,
        True,
    )
    frag = narration.Slot("02", "He...", True, start=5.0, end=5.3)
    p = narration.place(0.6, frag, prev_end=4.0)  # montage fragments are cut, never led or quickened
    assert (p.start, round(p.kept, 3), p.lead, p.tempo, p.cut) == (5.0, 0.3, 0.0, 1.0, True)
    with pytest.raises(ValueError, match="no room"):
        narration.place(0.6, narration.Slot("03", "x", True, start=5.0, end=5.0), prev_end=4.0)


def test_plan_asks_a_line_to_hurry_when_the_next_one_cannot_fit_otherwise(narration):
    base = narration.SETTINGS.speed
    natural = {0: 1.9, 1: 1.5, 2: 0.4}
    asked = []

    def measure(i, speed):
        asked.append((i, speed))
        return natural[i] * base / speed

    plan = [
        narration.Slot("01", "a", False, start=0.0, end=2.0),
        narration.Slot("02", "b", False, start=2.02, end=3.0),
        narration.Slot("03", "c", True, start=3.02, end=3.5),
    ]
    out = narration.plan_narration(plan, measure)
    first, second, third = out
    assert first.speed == narration.MAX_SPEED and round(first.speech, 3) == 1.71 and not first.at.cut
    assert second.speed == narration.MAX_SPEED and not second.at.cut and round(second.at.lead, 3) == 0.27
    assert round(second.at.start + second.at.kept, 3) <= 3.0 and third.at == narration.place(third.speech, plan[2], 0)
    # base for every line, one retry for the second, one hurry for the first: never more than three a line
    assert asked == [(0, base), (1, base), (1, narration.MAX_SPEED), (0, narration.MAX_SPEED), (2, base)]
    # when the next line fits on its own, the line before is left at its natural pace
    natural[1] = 0.9
    asked.clear()
    out = narration.plan_narration(plan, measure)
    assert out[0].speed == base and asked == [(0, base), (1, base), (2, base)]


def wav(path: Path, seconds=0.5):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"\x10\x00" * int(RATE * seconds))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(root: Path, **changes):
    (root / "audio").mkdir(exist_ok=True)
    digest = wav(root / "audio" / "vo-01.wav")
    item = {
        "id": "01",
        "text": "One.",
        "phase": "test",
        "caption_start": 0.1,
        "start": 0.1,
        "duration": 0.5,
        "speech_duration": 0.5,
        "speed": 1.08,
        "lead": 0.0,
        "tempo": 1.0,
        "cut": False,
        "audio": "audio/vo-01.wav",
        "sha256": digest,
    }
    item.update(changes)
    (root / "narration.json").write_text(json.dumps({"items": [item]}))
    return root / "narration.json"


def test_conform_plays_faster_within_its_bound(narration, tmp_path):
    wav(tmp_path / "in.wav", seconds=1.0)
    got = narration.conform(tmp_path / "in.wav", tmp_path / "out.wav", 0.0, 1.0, 0.8, 0.0, tempo=1.25)
    assert abs(got - 0.8) < 1.5 / RATE
    with pytest.raises(ValueError, match="tempo"):
        narration.conform(tmp_path / "in.wav", tmp_path / "out.wav", 0.0, 1.0, 0.8, 0.0, tempo=1.6)


def test_narration_cues_verify_the_manifest_and_the_files(narration, tmp_path):
    cues = narration.narration_cues(manifest(tmp_path), tmp_path)
    assert [(c.id, c.start, c.duration, c.audio) for c in cues] == [("01", 0.1, 0.5, "audio/vo-01.wav")]
    with pytest.raises(ValueError, match="sha256"):
        narration.narration_cues(manifest(tmp_path, sha256="0" * 64), tmp_path)
    with pytest.raises(ValueError, match="missing"):
        path = manifest(tmp_path)
        data = json.loads(path.read_text())
        del data["items"][0]["start"]
        path.write_text(json.dumps(data))
        narration.narration_cues(path, tmp_path)
    with pytest.raises(ValueError, match="unknown"):
        narration.narration_cues(manifest(tmp_path, extra=1), tmp_path)
    with pytest.raises(ValueError, match="duration"):
        narration.narration_cues(manifest(tmp_path, duration=0), tmp_path)
    with pytest.raises(ValueError, match="audio/vo-01.wav"):
        path = manifest(tmp_path)
        (tmp_path / "audio" / "vo-01.wav").unlink()
        narration.narration_cues(path, tmp_path)
    with pytest.raises(ValueError, match="items"):
        path.write_text(json.dumps({"items": "no"}))
        narration.narration_cues(path, tmp_path)
