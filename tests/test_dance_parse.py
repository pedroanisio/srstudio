"""The dance schemas: the shipped presets parse, and every malformed, incomplete or hostile document is refused."""

import copy
import json

import pytest

from srstudio import dance
from srstudio.dance import (
    DanceDataError,
    DanceSchemaError,
    MoveError,
    RoutineError,
    load_moves,
    load_routine,
    moves,
    parse_moves,
    parse_routine,
)
from srstudio.music import Groove


def pattern(**changes):
    return {
        "target": "chest.front_back",
        "waveform": "sine",
        "cycles": 1,
        "per": "beat",
        "phase": 0,
        "amplitude": 0.2,
        "snap": 0.5,
    } | changes


def document(**changes):
    return {
        "schema": dance.MOVES_SCHEMA,
        "moves": [{"name": "probe", "support": "either", "patterns": [pattern()]}],
    } | changes


def score(**changes):
    return {
        "schema": dance.ROUTINE_SCHEMA,
        "track_bars": 16,
        "entries": [{"bars": [0, 8], "move": "seat-groove"}],
    } | changes


def text(data):
    return json.dumps(data)


def test_the_presets_parse_and_cover_the_brief():
    assert set(moves()) == {
        "seat-groove",
        "bob",
        "sway",
        "bounce",
        "shoulder-shimmy",
        "head-nod",
        "arm-pump",
        "arm-wave-overhead",
        "step-touch",
        "clap",
        "point-up",
        "raise-the-roof",
        "hand-wave-side",
        "shoulder-roll",
        "hip-sway",
        "hands-up",
    }
    assert moves() is moves()
    assert moves()["step-touch"].support == "feet"
    assert {c.foot for c in moves()["step-touch"].contacts} == {"left_foot", "right_foot"}


def test_every_preset_mirrors_back_to_itself():
    for move in moves().values():
        assert move.mirror().mirror() == move


def test_every_standing_preset_keeps_a_foot_planted_on_every_picture():
    groove = Groove(129)
    for move in moves().values():
        for frame in dance.frames(move, groove, 0.0, 4 * move.loop_beats * groove.beat, 25):
            assert frame.planted or move.support == "seat", (move.name, frame.time)


def test_the_moves_are_read_from_bytes_text_and_a_file(tmp_path):
    assert list(parse_moves(text(document()))) == ["probe"]
    assert list(parse_moves(text(document()).encode())) == ["probe"]
    path = tmp_path / "moves.json"
    path.write_text(text(document(generated_by={"tool": "Claude Code", "model": "m"})))
    assert list(load_moves(path)) == ["probe"]
    with pytest.raises(DanceDataError):
        load_moves(tmp_path / "missing.json")


def test_a_full_pattern_and_move_read_every_field():
    data = document(
        moves=[
            {
                "name": "probe",
                "description": "all fields",
                "support": "feet",
                "loop_beats": 2,
                "lags": {"head": 0.1},
                "contacts": [{"foot": "left_foot", "from": 0, "to": 2}],
                "patterns": [pattern(swing=0.6, intensity=0.5, bias=0.1, cycles=0.5)],
            }
        ]
    )
    move = parse_moves(text(data))["probe"]
    assert move.lag("head") == 0.1 and move.description == "all fields"
    assert move.patterns[0].swing == 0.6 and move.patterns[0].bias == 0.1
    assert move.contacts[0].end == 2


@pytest.mark.parametrize(
    "broken",
    [
        "not json",
        "[]",
        "null",
        '{"schema": "srstudio.dance-moves/1.0.0", "schema": "srstudio.dance-moves/1.0.0", "moves": []}',
        '{"schema": "srstudio.dance-moves/1.0.0", "moves": [{"name": NaN}]}',
        '{"schema": "srstudio.dance-moves/1.0.0", "moves": [{"name": Infinity}]}',
        b"\xff\xfe",
        "[" * 200_000,
        " " * (1_000_001),
        7,
    ],
)
def test_text_that_is_not_one_strict_document_is_refused(broken):
    with pytest.raises(DanceDataError):
        parse_moves(broken)


@pytest.mark.parametrize(
    "data",
    [
        document(schema="srstudio.dance-moves/2.0.0"),
        document(schema="srstudio.dance-routine/1.0.0"),
        document(schema="srstudio.dance-moves"),
        document(schema=1),
        {"moves": []},
    ],
)
def test_another_schema_is_refused(data):
    with pytest.raises(DanceDataError):
        parse_moves(text(data))


def test_a_later_minor_of_the_same_major_is_read():
    assert list(parse_moves(text(document(schema="srstudio.dance-moves/1.4.0")))) == ["probe"]
    with pytest.raises(DanceSchemaError):
        parse_moves(text(document(schema="srstudio.dance-moves/3.0.0")))


def mutated(edit):
    data = copy.deepcopy(document())
    edit(data, data["moves"][0], data["moves"][0]["patterns"][0])
    return data


@pytest.mark.parametrize(
    "edit",
    [
        lambda d, m, p: d.update(extra=1),
        lambda d, m, p: d.update(track_bars=1),
        lambda d, m, p: d.update(generated_by={"tool": "x"}),
        lambda d, m, p: d.update(generated_by={"tool": "x", "model": 1}),
        lambda d, m, p: d.update(moves="seat-groove"),
        lambda d, m, p: d.update(moves=[]),
        lambda d, m, p: d.update(moves=[m] * 257),
        lambda d, m, p: d.update(moves=[m, m]),
        lambda d, m, p: m.update(extra=1),
        lambda d, m, p: m.pop("support"),
        lambda d, m, p: m.update(name=7),
        lambda d, m, p: m.update(description=7),
        lambda d, m, p: m.update(description="x" * 513),
        lambda d, m, p: m.update(patterns="x"),
        lambda d, m, p: m.update(patterns=[p] * 129),
        lambda d, m, p: m.update(lags=[]),
        lambda d, m, p: m.update(lags={str(k): 0 for k in range(17)}),
        lambda d, m, p: m.update(loop_beats="2"),
        lambda d, m, p: m.update(contacts={}),
        lambda d, m, p: m.update(contacts=[{"foot": "left_foot", "from": 0}]),
        lambda d, m, p: p.update(extra=1),
        lambda d, m, p: p.pop("snap"),
        lambda d, m, p: p.update(amplitude="0.2"),
        lambda d, m, p: p.update(amplitude=True),
        lambda d, m, p: p.update(amplitude=None),
        lambda d, m, p: p.update(cycles=False),
        lambda d, m, p: p.update(target=1),
        lambda d, m, p: p.update(per=1),
    ],
)
def test_a_malformed_document_is_refused(edit):
    with pytest.raises(DanceDataError):
        parse_moves(text(mutated(edit)))


def test_a_number_json_rounds_to_infinity_is_refused():
    with pytest.raises(DanceDataError):
        parse_moves(text(document()).replace('"amplitude": 0.2', '"amplitude": 1e999'))


@pytest.mark.parametrize(
    "edit",
    [
        lambda d, m, p: m.update(name="Bad Name"),
        lambda d, m, p: m.update(support="wall"),
        lambda d, m, p: m.update(patterns=[]),
        lambda d, m, p: m.update(lags={"tail": 0.1}),
        lambda d, m, p: p.update(target="tail.wag"),
        lambda d, m, p: p.update(amplitude=9),
        lambda d, m, p: p.update(snap=0.99),
        lambda d, m, p: p.update(per="phrase"),
        lambda d, m, p: m.update(contacts=[{"foot": "left_foot", "from": 0, "to": 1}]),
        lambda d, m, p: m.update(contacts=[{"foot": "left_hand", "from": 0, "to": 1}]),
    ],
)
def test_a_well_formed_document_that_breaks_the_model_is_refused_at_its_path(edit):
    with pytest.raises(MoveError) as caught:
        parse_moves(text(mutated(edit)))
    assert "$.moves[0]" in str(caught.value)
    assert caught.value.to_dict()["path"].startswith("$.moves[0]")


# --- routines ---------------------------------------------------------------------------------------------------------


def test_a_routine_is_read_with_every_field(tmp_path):
    data = score(
        beats_per_bar=4,
        generated_by={"tool": "Claude Code", "model": "m"},
        entries=[
            {"bars": [0, 8], "move": "seat-groove", "expression": "grin"},
            {
                "bars": [8, 16],
                "move": "head-nod",
                "intensity": 0.5,
                "mirror": True,
                "transition_beats": 2,
                "expression": "eyes-closed",
                "hold": {"head.turn_left_right": 0.3},
            },
        ],
    )
    r = parse_routine(text(data), moves())
    assert r.track_bars == 16 and r.entries[1].mirror and r.entries[1].hold == (("head.turn_left_right", 0.3),)
    path = tmp_path / "routine.json"
    path.write_text(text(data))
    assert load_routine(path, moves()) == r


@pytest.mark.parametrize(
    "data",
    [
        score(extra=1),
        score(moves=[]),
        score(track_bars=16.0),
        score(track_bars="16"),
        score(beats_per_bar=True),
        score(entries="x"),
        score(entries=[{"bars": [0, 8], "move": "seat-groove"}] * 513),
        score(entries=[{"bars": [0, 8]}]),
        score(entries=[{"bars": [0, 8], "move": "seat-groove", "extra": 1}]),
        score(entries=[{"bars": [0], "move": "seat-groove"}]),
        score(entries=[{"bars": [0, 8, 9], "move": "seat-groove"}]),
        score(entries=[{"bars": [0, 8.0], "move": "seat-groove"}]),
        score(entries=[{"bars": [0, 8], "move": "moonwalk"}]),
        score(entries=[{"bars": [0, 8], "move": 7}]),
        score(entries=[{"bars": [0, 8], "move": "seat-groove", "mirror": 1}]),
        score(entries=[{"bars": [0, 8], "move": "seat-groove", "intensity": "1"}]),
        score(entries=[{"bars": [0, 8], "move": "seat-groove", "expression": 1}]),
        score(entries=[{"bars": [0, 8], "move": "seat-groove", "hold": []}]),
        score(entries=[{"bars": [0, 8], "move": "seat-groove", "hold": {"head.turn_left_right": "x"}}]),
        document(),
    ],
)
def test_a_malformed_routine_is_refused(data):
    with pytest.raises(DanceDataError):
        parse_routine(text(data), moves())


@pytest.mark.parametrize(
    "data",
    [
        score(entries=[]),
        score(track_bars=4),
        score(entries=[{"bars": [8, 0], "move": "seat-groove"}]),
        score(entries=[{"bars": [0, 8], "move": "seat-groove"}, {"bars": [4, 12], "move": "seat-groove"}]),
        score(entries=[{"bars": [0, 1], "move": "seat-groove", "transition_beats": 5}]),
        score(entries=[{"bars": [0, 8], "move": "seat-groove", "expression": "Big Grin"}]),
        score(entries=[{"bars": [0, 8], "move": "seat-groove", "hold": {"tail.wag": 0.1}}]),
        score(entries=[{"bars": [0, 8], "move": "seat-groove"}, {"bars": [8, 16], "move": "step-touch"}]),
    ],
)
def test_a_routine_that_does_not_fit_is_refused(data):
    with pytest.raises(RoutineError):
        parse_routine(text(data), moves())
