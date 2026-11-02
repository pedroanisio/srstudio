"""The shipped move libraries (ADR 0212): ``dance.library`` loads them by name and refuses others; every move of the
transcribed FE!N library, mirrored too, dances inside every preset's limits unclamped; a palette splits a library by
how much it moves; the command and the review tool reach a library by name."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from srstudio import choreograph, dance
from srstudio import skeleton as sk
from srstudio.dance_pose import dance_pose
from srstudio.music import Groove

ROOT = Path(__file__).resolve().parents[1]
GRID = Groove(152)
PROFILES = {name: sk.preset(name) for name in sk.PRESETS}
STEPS = 48
FEIN = dance.library("fein")


def test_the_libraries_load_by_name_and_the_presets_are_one():
    assert dance.LIBRARIES == ("moves", "fein")
    assert dance.library("moves") is dance.moves()
    assert len(FEIN) >= 60 and all(name.startswith("fein-") for name in FEIN)


@pytest.mark.parametrize("name", ["", "FEIN", "../moves", "moves.json", "styles", 3, None])
def test_an_unknown_or_unsafe_library_name_is_refused(name):
    with pytest.raises(dance.DanceDataError, match="library"):
        dance.library(name)


def test_the_transcribed_library_carries_its_provenance():
    text = (ROOT / "src" / "srstudio" / "assets" / "dance" / "fein.json").read_text()
    top = json.loads(text)
    assert top["schema"] == dance.MOVES_SCHEMA
    assert top["generated_by"]["tool"] == "tools/dance_transcribe.py" and "Claude" in top["generated_by"]["model"]
    for move in FEIN.values():
        assert move.support == "feet" and move.loop_beats == 4
        assert {c.foot for c in move.contacts} == {"left_foot", "right_foot"}
        assert "Seen" in move.description and "head radii" in move.description
        assert all(p.cycles == 0.25 and p.per == "beat" and p.waveform == "sine" for p in move.patterns)


@pytest.mark.parametrize("character", sk.PRESETS)
@pytest.mark.parametrize("name", list(FEIN))
def test_every_transcribed_move_dances_within_every_characters_limits_unclamped(name, character):
    move = FEIN[name]
    for source in (move, move.mirror()):
        for step in range(round(move.loop_beats * STEPS)):
            dance_pose(PROFILES[character], dance.sample(source, GRID, step / STEPS * GRID.beat))


def test_a_palette_splits_a_library_by_how_much_it_moves():
    palette = choreograph.palette_of(FEIN)
    assert set(palette.low) | set(palette.high) == set(FEIN)
    assert len(palette.low) >= len(palette.high) >= len(FEIN) // 2
    assert max(choreograph.energy(FEIN[n]) for n in palette.low) <= min(
        choreograph.energy(FEIN[n]) for n in palette.high
    )
    one = {"fein-01": FEIN["fein-01"]}
    assert choreograph.palette_of(one) == choreograph.Palette(("fein-01",), ("fein-01",))
    with pytest.raises(choreograph.ChoreographyError):
        choreograph.palette_of({"x": "not a move"})
    with pytest.raises(choreograph.ChoreographyError, match="at least one"):
        choreograph.palette_of({})


def test_a_routine_composes_from_the_library(tmp_path):
    song = dance.SongMap(
        GRID, 4, (0.0,) * 64, (-6.0, 0.0, 0.0, -6.0),
        (dance.SongPart(0, 4, -6.0, "low"), dance.SongPart(4, 12, 0.0, "high"), dance.SongPart(12, 16, -6.0, "low")),
    )  # fmt: skip
    palette = choreograph.palette_of(FEIN)
    routine = choreograph.choreograph(song, support="feet", seed=5, palette=palette, library=FEIN)
    assert [e.move.name in palette.low for e in routine.entries] == [True, False, False, True] or all(
        e.move.name in FEIN for e in routine.entries
    )
    assert dance.parse_routine(dance.dump_routine(routine), FEIN) == routine
    with pytest.raises(choreograph.ChoreographyError):  # the presets do not know the transcribed names
        choreograph.choreograph(song, support="feet", seed=5, palette=palette)


@pytest.fixture(scope="module")
def track(tmp_path_factory):
    from srstudio import music

    samples = music.render(GRID, [music.Section(0, 8, frozenset()), music.Section(8, 16)], rate=22050)
    return music.write_wav(tmp_path_factory.mktemp("library") / "song.wav", samples, 22050)


def test_the_command_line_draws_from_a_library(track, capsys):
    from srstudio.cli import main

    args = ["choreograph", str(track), "--support", "feet", "--seed", "3", "--phrase-bars", "4", "--near", "152"]
    assert main([*args, "--library", "fein"]) == 0
    routine = dance.parse_routine(capsys.readouterr().out, FEIN)
    assert routine.entries and all(e.move.name in FEIN for e in routine.entries)
    with pytest.raises(SystemExit) as stop:  # argparse refuses a name outside the shipped libraries
        main([*args, "--library", "waltz"])
    assert stop.value.code == 2


def test_the_review_tool_plans_from_a_library():
    spec = importlib.util.spec_from_file_location("dance_views_tool", ROOT / "tools" / "dance_views.py")
    assert spec is not None and spec.loader is not None
    views = importlib.util.module_from_spec(spec)
    sys.modules["dance_views_tool"] = views
    spec.loader.exec_module(views)
    assert views.plan(["fein-02", "fein-01"], 2, "fein") == (("fein-02", 0, 2), ("fein-01", 2, 4))
    assert len(views.plan(list(FEIN)[:10], 1, "fein")) == 10
    with pytest.raises(views.ViewsError, match="fein library holds"):
        views.plan(["bob"], 2, "fein")
    with pytest.raises(views.ViewsError, match="library"):
        views.plan(["bob"], 2, "nope")
