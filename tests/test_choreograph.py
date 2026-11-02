"""A routine from a song (ADR 0193): one entry per phrase, moves chosen by the part's level from the moves the
character's support allows, faces held per phrase, the same seed giving the same routine, and every refusal typed."""

import math
from dataclasses import replace

import pytest

from srstudio import choreograph as ch
from srstudio import dance, music
from srstudio import skeleton as sk
from srstudio.dance import DanceError, Routine, SongMap, SongPart, song_map
from srstudio.dance_pose import dance_pose
from srstudio.errors import SrstudioError
from srstudio.music import Groove, Section

GRID = Groove(160)  # a bar is 1.5 s, so 24 bars render quickly
QUIET = frozenset({"hat", "keys"})
RATE = 16000
MOVES = dance.moves()


@pytest.fixture(scope="module")
def track(tmp_path_factory):
    """Eight quiet bars, eight full ones, eight quiet: a verse, a chorus, a verse."""
    sections = [Section(0, 8, QUIET), Section(8, 16), Section(16, 24, QUIET)]
    samples = music.render(GRID, sections, rate=RATE)
    return music.write_wav(tmp_path_factory.mktemp("choreo") / "song.wav", samples, RATE)


@pytest.fixture(scope="module")
def song(track):
    return song_map(track, GRID, phrase_bars=4)


def flat(bars, phrase_bars, *levels, groove=GRID):
    """A song map of ``bars`` bars whose parts are ``(start, end, level)``, without audio."""
    parts = tuple(SongPart(a, b, -3.0 if level == "low" else 0.0, level) for a, b, level in levels)
    phrases = math.ceil(bars / phrase_bars)
    return SongMap(groove, phrase_bars, (0.0,) * (bars * groove.beats_per_bar), (0.0,) * phrases, parts)


def level_at(found, bar):
    return next(p.level for p in found.parts if p.start_bar <= bar < p.end_bar)


def test_the_track_reads_as_quiet_full_quiet(song):
    assert [(p.start_bar, p.end_bar, p.level) for p in song.parts] == [(0, 8, "low"), (8, 16, "high"), (16, 24, "low")]


@pytest.mark.parametrize("support", ["seat", "feet"])
def test_entries_start_on_phrase_boundaries_and_cover_the_track(song, support):
    routine = ch.choreograph(song, support=support, seed=7)
    assert isinstance(routine, Routine)
    assert routine.track_bars == 24 and routine.beats_per_bar == GRID.beats_per_bar
    assert [(e.start_bar, e.end_bar) for e in routine.entries] == [(b, b + 4) for b in range(0, 24, 4)]


@pytest.mark.parametrize("support", ["seat", "feet"])
@pytest.mark.parametrize("seed", range(6))
def test_moves_and_faces_fit_the_parts_level_and_the_support(song, support, seed):
    routine = ch.choreograph(song, support=support, seed=seed)
    palette = ch.Palette()
    allowed = {"seat": {"seat", "either"}, "feet": {"feet", "either"}}[support]
    for entry in routine.entries:
        level = level_at(song, entry.start_bar)
        assert entry.move.name in (palette.low if level == "low" else palette.high)
        assert entry.expression in (palette.low_faces if level == "low" else palette.high_faces)
        assert entry.move.support in allowed


def test_a_seated_routine_never_stands_and_a_standing_one_never_sits(song):
    for seed in range(8):
        assert ch.choreograph(song, support="seat", seed=seed).support in ("seat", "either")
        assert ch.choreograph(song, support="feet", seed=seed).support in ("feet", "either")


def test_the_same_seed_gives_the_same_routine_and_another_can_differ(song):
    first = ch.choreograph(song, support="feet", seed=3)
    assert ch.choreograph(song, support="feet", seed=3) == first
    assert any(ch.choreograph(song, support="feet", seed=s) != first for s in range(4, 12))


def test_no_move_runs_longer_than_the_repeat_bound():
    long = flat(64, 2, (0, 64, "even"))
    palette = ch.Palette(low=("head-nod", "shoulder-roll"), high=("clap",))
    for limit in (1, 2, 3):
        for seed in range(5):
            names = [
                e.move.name
                for e in ch.choreograph(long, support="seat", seed=seed, max_repeat=limit, palette=palette).entries
            ]
            runs, run = [], 1
            for a, b in zip(names, names[1:], strict=False):
                run = run + 1 if a == b else 1
                runs.append(run)
            assert max(runs, default=1) <= limit, (limit, seed, names)


def test_a_repeated_move_is_danced_the_other_way_round():
    long = flat(64, 2, (0, 64, "low"))
    routine = ch.choreograph(long, support="seat", seed=1, max_repeat=2, palette=ch.Palette(low=("head-nod", "clap")))
    pairs = list(zip(routine.entries, routine.entries[1:], strict=False))
    repeats = [(a, b) for a, b in pairs if a.move.name == b.move.name]
    assert repeats, "a two-move pool over 32 phrases repeats a move"
    assert all(b.mirror != a.mirror for a, b in repeats)
    assert all(not b.mirror for a, b in pairs if a.move.name != b.move.name)


def test_an_even_track_draws_from_both_pools():
    even = flat(64, 4, (0, 64, "even"))
    palette = ch.Palette()
    names = {e.move.name for s in range(4) for e in ch.choreograph(even, support="feet", seed=s).entries}
    assert names <= set(palette.low) | set(palette.high)
    assert names & set(palette.low) and names & set(palette.high)


def test_every_entry_crossfades_in_over_the_stated_transition(song):
    routine = ch.choreograph(song, support="seat", seed=2, transition_beats=3.0)
    assert [e.transition_beats for e in routine.entries] == [3.0] * 6


def test_a_phrase_shorter_than_the_transition_takes_a_transition_of_its_length():
    short = flat(9, 4, (0, 8, "low"), (8, 9, "high"))
    routine = ch.choreograph(short, support="seat", seed=0, transition_beats=6.0)
    assert [(e.start_bar, e.end_bar, e.transition_beats) for e in routine.entries] == [
        (0, 4, 6.0),
        (4, 8, 6.0),
        (8, 9, 4.0),
    ]


def test_the_routine_is_bounded_by_the_track_and_dances_within_every_presets_limits(song):
    routine = ch.choreograph(song, support="feet", seed=5)
    assert routine.entries[-1].end_bar == routine.track_bars == song.parts[-1].end_bar
    end = GRID.at(routine.track_bars)
    for character in sk.PRESETS:
        profile = sk.preset(character)
        for frame in dance.frames(routine, GRID, 0.0, end, 4):
            dance_pose(profile, frame)  # no clamp: a value past a limit raises


def test_a_track_path_is_mapped_then_choreographed(track, song):
    from_path = ch.choreograph_track(track, GRID, phrase_bars=4, support="seat", seed=9)
    assert from_path == ch.choreograph(song, support="seat", seed=9)


def test_the_default_pools_name_shipped_moves():
    palette = ch.Palette()
    assert set(palette.low) | set(palette.high) <= set(MOVES)
    assert {"seat-groove", "bob", "head-nod"} <= set(palette.low)
    assert {"arm-pump", "raise-the-roof", "point-up", "clap"} <= set(palette.high)
    assert set(palette.low_faces) | set(palette.high_faces) <= set(ch.EXPRESSIONS)


# --- refusals ----------------------------------------------------------------------------------------------------


def test_a_song_shorter_than_one_phrase_is_refused():
    with pytest.raises(ch.ChoreographyError, match="phrase"):
        ch.choreograph(flat(3, 4, (0, 3, "even")), support="seat", seed=0)


@pytest.mark.parametrize(
    "parts",
    [
        (),
        ((2, 8, "low"),),  # does not open the track
        ((0, 4, "low"), (5, 8, "high")),  # a gap
        ((0, 6, "low"), (6, 8, "high")),  # a part off the phrase grid
        ((0, 8, "loud"),),  # an unknown level
    ],
)
def test_a_song_map_whose_parts_do_not_tile_its_phrases_is_refused(parts):
    with pytest.raises(ch.ChoreographyError):
        ch.choreograph(flat(8, 4, *parts), support="seat", seed=0)


@pytest.mark.parametrize("phrase_bars", [0, 65, 4.0, True])
def test_a_song_map_with_a_phrase_outside_its_range_is_refused(phrase_bars):
    with pytest.raises(ch.ChoreographyError, match="phrase_bars"):
        ch.choreograph(replace(flat(8, 4, (0, 8, "low")), phrase_bars=phrase_bars), support="seat", seed=0)


def test_only_a_song_map_is_choreographed():
    with pytest.raises(ch.ChoreographyError, match="SongMap"):
        ch.choreograph("song.wav", support="seat", seed=0)


def test_a_song_past_the_routine_bounds_is_refused():
    with pytest.raises(ch.ChoreographyError, match="phrases"):
        ch.choreograph(flat(1100, 2, (0, 1100, "even")), support="seat", seed=0)


@pytest.mark.parametrize("support", ["either", "lying", None])
def test_a_support_other_than_seat_or_feet_is_refused(song, support):
    with pytest.raises(ch.ChoreographyError, match="support"):
        ch.choreograph(song, support=support, seed=0)


@pytest.mark.parametrize("seed", [True, 1.5, "1", None, -1])
def test_a_seed_is_a_whole_number(song, seed):
    with pytest.raises(ch.ChoreographyError, match="seed"):
        ch.choreograph(song, support="seat", seed=seed)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("transition_beats", -1.0),
        ("transition_beats", math.nan),
        ("transition_beats", True),
        ("max_repeat", 0),
        ("max_repeat", 1.0),
        ("max_repeat", 65),
    ],
)
def test_out_of_range_settings_are_refused(song, name, value):
    with pytest.raises(ch.ChoreographyError, match=name):
        ch.choreograph(song, support="seat", seed=0, **{name: value})


def test_unknown_move_names_are_refused(song):
    with pytest.raises(ch.ChoreographyError, match="moonwalk"):
        ch.choreograph(song, support="seat", seed=0, palette=ch.Palette(high=("clap", "moonwalk")))


def test_an_empty_pool_for_the_support_is_refused(song):
    standing_only = ch.Palette(low=("bob", "sway"), high=("bounce",))
    with pytest.raises(ch.ChoreographyError, match="seat"):
        ch.choreograph(song, support="seat", seed=0, palette=standing_only)


def test_a_pool_that_cannot_change_move_in_time_is_refused():
    long = flat(16, 4, (0, 16, "low"))
    with pytest.raises(ch.ChoreographyError, match="repeat"):
        ch.choreograph(long, support="seat", seed=0, max_repeat=2, palette=ch.Palette(low=("head-nod",)))


def test_a_one_move_pool_is_fine_while_its_runs_stay_short():
    routine = ch.choreograph(flat(8, 4, (0, 8, "low")), support="seat", seed=0, palette=ch.Palette(low=("head-nod",)))
    assert [e.move.name for e in routine.entries] == ["head-nod", "head-nod"]


@pytest.mark.parametrize(
    "changes",
    [
        {"low": ()},
        {"low": ["head-nod"]},
        {"low": ("head-nod", "head-nod")},
        {"low": ("head-nod", 3)},
        {"low_faces": ("grin", "scowl")},
        {"high_faces": ()},
        {"high_faces": ("grin", "grin")},
    ],
)
def test_a_palette_outside_its_contract_is_refused(changes):
    with pytest.raises(ch.ChoreographyError):
        replace(ch.Palette(), **changes)


def test_a_library_that_is_not_a_mapping_of_moves_is_refused(song):
    with pytest.raises(ch.ChoreographyError, match="library"):
        ch.choreograph(song, support="seat", seed=0, library=[MOVES["clap"]])
    with pytest.raises(ch.ChoreographyError, match="library"):
        ch.choreograph(song, support="seat", seed=0, library={"clap": "clap"})


def test_a_palette_that_is_not_a_palette_is_refused(song):
    with pytest.raises(ch.ChoreographyError, match="Palette"):
        ch.choreograph(song, support="seat", seed=0, palette={"low": ("head-nod",)})


def test_the_choreography_error_is_a_dance_error():
    assert issubclass(ch.ChoreographyError, DanceError) and issubclass(ch.ChoreographyError, SrstudioError)


# --- a routine as data, and the command line --------------------------------------------------------------------------


def test_a_routine_is_written_as_its_document_and_reads_back(song):
    routine = ch.choreograph(song, support="seat", seed=4)
    text = dance.dump_routine(routine)
    assert dance.parse_routine(text, MOVES) == routine
    held = dance.Routine(
        8,
        (
            dance.Entry(0, 4, MOVES["clap"], intensity=0.5, mirror=True, expression="grin"),
            dance.Entry(4, 8, MOVES["seat-groove"], transition_beats=2.5, hold=MOVES["hands-up"].held()),
        ),
        beats_per_bar=3,
    )
    assert dance.parse_routine(dance.dump_routine(held), MOVES) == held


def test_only_a_routine_is_written():
    with pytest.raises(DanceError, match="Routine"):
        dance.dump_routine(MOVES["clap"])


def test_the_command_line_choreographs_a_track(track, capsys):
    from srstudio.cli import main

    args = ["choreograph", str(track), "--support", "feet", "--seed", "3", "--phrase-bars", "4", "--near", "160"]
    assert main(args) == 0
    printed = capsys.readouterr()
    routine = dance.parse_routine(printed.out, MOVES)
    assert "160 BPM" in printed.err
    # the measured grid opens its first bar a little after zero, so the last bar can fall short of the track
    assert routine.track_bars in (23, 24)
    assert [e.start_bar for e in routine.entries] == list(range(0, routine.track_bars, 4))
    assert main(args) == 0
    assert dance.parse_routine(capsys.readouterr().out, MOVES) == routine  # the same seed, the same routine


def test_the_command_line_warns_when_too_few_bars_place_the_bar_line(track, capsys):
    from srstudio.cli import main

    args = ["choreograph", str(track), "--support", "seat", "--seed", "0", "--phrase-bars", "2", "--near", "160"]
    assert main([*args, "--seconds", "9"]) == 0  # six bars at 160 BPM, under music.SURE_BARS
    printed = capsys.readouterr()
    assert "may open on another beat" in printed.err
    routine = dance.parse_routine(printed.out, MOVES)
    assert routine.track_bars <= 6 and routine.entries


def test_the_command_line_reports_a_refusal(tmp_path, track, capsys):
    from srstudio.cli import main

    assert main(["choreograph", str(tmp_path / "missing.wav"), "--support", "seat", "--seed", "0"]) == 1
    assert "srstudio choreograph:" in capsys.readouterr().err
    assert main(["choreograph", str(track), "--support", "seat", "--seed", "0", "--phrase-bars", "64"]) == 1
    assert "phrase" in capsys.readouterr().err
