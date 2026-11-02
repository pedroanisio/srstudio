"""Your Half as data: a Saga reel with no music and no closing entry, ending on the send line, its staging fitted to
a synthetic recording before any request is made."""

import sys
from pathlib import Path

import pytest

from srstudio import saga_reel
from support.saga import recorded

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def reel():
    sys.path.insert(0, str(EPISODES))
    try:
        import your_half_audio

        return your_half_audio.REEL
    finally:
        sys.path.pop(0)


def test_it_goes_without_the_series_bed_at_the_batch_loudness(reel):
    assert reel.bed is False and reel.loudness == "-14"
    assert reel.script().bed is None and "composed" not in reel.script().voice_note


def test_it_ends_on_the_send_line_with_no_handbook_entry(reel):
    stages = reel.stages(recorded(reel))
    assert reel.takes[-1].text == "You rounded down."
    assert all(s.entry is None for s in stages.values())


def test_the_staging_fits_a_recording(reel):
    takes = recorded(reel)
    saga_reel.check(takes, reel.stages(takes))


def test_a_close_never_zooms_the_console_marks_out_of_frame(reel):
    stages = reel.stages(recorded(reel))
    assert all(s.move is None for s in stages.values())
    closes = [s for s in stages.values() if len(s.cast) == 1]
    assert len(closes) >= 5 and all(s.cast[0].scale > 1 for s in closes)


def test_every_panel_holds_long_enough_to_read(reel):
    takes = recorded(reel)
    stages = reel.stages(takes)
    for take in takes:
        panels = stages[take.id].panels
        edges = [*(p.start for p in panels), take.duration]
        assert all(b - a >= 0.84 for a, b in zip(edges, edges[1:], strict=False))


def by_id(reel):
    takes = recorded(reel)
    return {t.id: t for t in takes}, reel.stages(takes)


def test_the_hit_lands_on_her_side_on_the_first_frame_of_the_sound(reel):
    _, stages = by_id(reel)
    hit = stages["05"]
    assert hit.options == {"hit": 0.0}  # the effect is loudest in its first 0.25 s (measured on fx-05.wav)
    assert "jump" not in hit.options
    assert hit.front["hit"] == 0.0
    assert hit.thrown is not None and hit.thrown.roll[0][0] == 0.0


def test_both_pilots_react_to_the_hit_and_she_goes_harder_than_he_does(reel):
    _, stages = by_id(reel)
    rook, juno = sorted(stages["05"].cast, key=lambda p: p.who != "rook")
    assert rook.lurch and juno.lurch and rook.mouth and juno.mouth
    assert max(abs(k[2]) for k in juno.lurch) > max(abs(k[2]) for k in rook.lurch)


def test_her_hand_is_on_the_stick_and_the_jab_comes_before_paid(reel):
    takes, stages = by_id(reel)
    jab = stages["09"].front["jab"]
    paid = next(p for p in stages["09"].panels if p.title.startswith("PAID"))
    assert 0.0 < jab.at and jab.at + 0.3 < paid.start
    assert [p.who for p in stages["09"].cast] == ["juno"]
    assert takes["09"].duration - paid.start >= 0.84


def test_every_shot_gives_the_cactus_something_to_stand_on(reel):
    _, stages = by_id(reel)
    assert all(s.front.get("ledge") is True for s in stages.values())
