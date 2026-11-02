"""Dance phrases (ADR 0194): counted eights, key poses on counts, travel and turns on the floor, a strict reader, and
the phrase carried by sampling, routines, the choreographer and ``dance_pose``."""

import json
import math

import pytest

from srstudio import choreograph as ch
from srstudio import dance
from srstudio import skeleton as sk
from srstudio.dance import (
    EASES,
    PHRASES_SCHEMA,
    DanceDataError,
    DanceError,
    DanceSchemaError,
    Entry,
    Floor,
    Key,
    Moment,
    Phrase,
    PhraseError,
    Routine,
    RoutineError,
    SongMap,
    SongPart,
    beat_of,
    count_of,
    ease,
    moment,
    parse_phrases,
)
from srstudio.dance_pose import dance_pose, on_floor
from srstudio.errors import SrstudioError
from srstudio.music import Groove

BOTH = frozenset({"left_foot", "right_foot"})
LEFT = frozenset({"left_foot"})
RIGHT = frozenset({"right_foot"})
GROOVE = Groove(120.0)  # half a second a beat
CLASS = Groove(122.65)


def step(**changes):
    """A two-key phrase: stand on 1, step right onto both feet by 3, a hit."""
    keys = (
        Key(0.0, BOTH),
        Key(1.0, LEFT, (("right_upper_leg.front_back", -0.4),), floor=Floor(right=0.05)),
        Key(2.0, BOTH, (("chest.front_back", -0.2),), "hit", Floor(right=0.1, up=-0.05), expression="grin"),
    )
    return Phrase(**{"name": "step", "eights": 1, "keys": keys, **changes})


# --- counts and eases -----------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "count, beat", [("1:1", 0.0), ("1:1e", 0.25), ("1:1&", 0.5), ("1:4a", 3.75), ("2:5&", 12.5), ("16:8a", 127.75)]
)
def test_a_count_names_its_beat_and_back(count, beat):
    assert beat_of(count) == beat
    assert count_of(beat) == count


@pytest.mark.parametrize("count", ["1:9", "0:1", "1:0", "1:1x", "1:1&&", "1", "", "100:1", 3, None])
def test_a_count_off_the_eights_is_refused(count):
    with pytest.raises(PhraseError, match="EIGHT:COUNT") as caught:
        beat_of(count)
    assert caught.value.to_dict()["code"] == "dance.count"


@pytest.mark.parametrize("beat", [0.1, -1.0, 128.0, math.nan, "1"])
def test_a_beat_off_the_sixteenth_grid_has_no_count(beat):
    with pytest.raises(PhraseError, match="sixteenth"):
        count_of(beat)


def test_each_ease_runs_from_the_last_key_to_this_one():
    for kind in EASES:
        assert ease(kind, 0.0) == 0.0 and ease(kind, 1.0) == 1.0
        assert ease(kind, -3.0) == 0.0 and ease(kind, 4.0) == 1.0  # clamped to the span
    assert ease("linear", 0.3) == pytest.approx(0.3)
    assert ease("smooth", 0.5) == pytest.approx(0.5)
    assert ease("smooth", 0.1) < 0.1  # eases out of the last key
    assert ease("hit", 0.6) == 0.0  # holds, then strikes late
    assert 0.0 < ease("hit", 0.9) < 1.0


def test_an_unknown_ease_is_refused():
    with pytest.raises(PhraseError, match="ease") as caught:
        ease("bounce", 0.5)
    assert caught.value.to_dict()["code"] == "dance.ease"


# --- the floor ------------------------------------------------------------------------------------------------------


def test_a_floor_read_after_a_turn_travels_the_turned_way():
    quarter = Floor(right=1.0, turn=math.pi / 2)
    then = quarter.then(Floor(forward=1.0, up=-0.1, turn=0.5))
    assert (then.right, then.forward) == pytest.approx((2.0, 0.0))  # forward after a quarter right is to the right
    assert then.up == -0.1 and then.turn == pytest.approx(math.pi / 2 + 0.5)
    assert Floor(right=0.2, forward=0.3, turn=0.4).mirror() == Floor(right=-0.2, forward=0.3, turn=-0.4)


@pytest.mark.parametrize(
    "kw, field",
    [
        ({"right": 300.0}, "floor.right"),
        ({"up": 0.6}, "floor.up"),
        ({"turn": 300.0}, "floor.turn"),
        ({"forward": math.inf}, "floor.forward"),
        ({"right": True}, "floor.right"),
    ],
)
def test_a_floor_out_of_bounds_is_refused(kw, field):
    with pytest.raises(PhraseError, match=field) as caught:
        Floor(**kw)
    assert caught.value.to_dict()["code"] == "dance.range"


# --- keys and phrases -----------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kw, match",
    [
        ({"beat": 0.1}, "sixteenth"),
        ({"beat": -1.0}, "beat"),
        ({"contacts": {"left_foot"}}, "frozenset"),
        ({"contacts": frozenset({"left_hand"})}, "frozenset"),
        ({"pose": (("root.up", 0.1),)}, "floor, not root"),
        ({"pose": (("chest.front_back", 4.0),)}, "pose chest.front_back"),
        ({"pose": (("chest.front_back", 0.1), ("chest.front_back", 0.2))}, "one"),
        ({"pose": (("tail.wag", 0.1),)}, "canonical"),
        ({"pose": {"chest.front_back": 0.1}}, "tuple"),
        ({"ease": "snap"}, "ease"),
        ({"floor": {"right": 1}}, "Floor"),
        ({"floor": Floor(right=9.0)}, "floor.right"),
        ({"floor": Floor(turn=13.0)}, "floor.turn"),
        ({"airborne": 1}, "airborne"),
        ({"airborne": True}, "airborne, and none"),
        ({"contacts": frozenset()}, "unless it is airborne"),
        ({"expression": "Big Grin!"}, "expression"),
    ],
)
def test_a_key_outside_its_contract_is_refused(kw, match):
    with pytest.raises(PhraseError, match=match):
        Key(**{"beat": 0.0, "contacts": BOTH, **kw})


def test_a_jump_is_a_key_in_the_air():
    assert Key(1.5, frozenset(), airborne=True).airborne


@pytest.mark.parametrize(
    "keys, match",
    [
        ((Key(1.0, BOTH),), "first key is on 1:1"),
        ((Key(0.0, BOTH, floor=Floor(right=0.1)),), "first key is on 1:1"),
        ((Key(0.0, BOTH), Key(2.0, frozenset(), airborne=True)), "starts and ends on the floor"),
        ((Key(0.0, BOTH), Key(8.0, BOTH)), "past 1 eights"),
        ((Key(0.0, BOTH), Key(2.0, BOTH), Key(2.0, BOTH)), "not after"),
        ((Key(0.0, BOTH), Key(1.0, LEFT), Key(2.0, RIGHT)), "no foot carries the body from 1:2 to 1:3"),
        ((), "1..256 keys"),
        ([Key(0.0, BOTH)], "1..256 keys"),
        ((Key(0.0, BOTH), "1:2"), "every key"),
    ],
)
def test_a_phrase_outside_its_contract_is_refused(keys, match):
    with pytest.raises(PhraseError, match=match):
        Phrase("broken", 1, keys)


@pytest.mark.parametrize(
    "kw, match",
    [
        ({"eights": 0}, "eights"),
        ({"eights": 17}, "eights"),
        ({"eights": 1.0}, "eights"),
        ({"description": "x" * 513}, "description"),
        ({"name": "Not A Name"}, "name"),
    ],
)
def test_a_phrase_with_bad_settings_is_refused(kw, match):
    with pytest.raises(PhraseError, match=match):
        step(**kw)


def test_a_phrase_error_is_a_typed_srstudio_error():
    assert issubclass(PhraseError, DanceError) and issubclass(PhraseError, SrstudioError)


def test_a_jump_carries_no_foot_across_it():
    jump = Phrase(
        "jump", 1, (Key(0.0, BOTH), Key(1.0, frozenset(), airborne=True, floor=Floor(up=0.1)), Key(2.0, BOTH))
    )
    assert moment(jump, 0.5).airborne and moment(jump, 0.5).planted == frozenset()
    assert jump.planted(1.0) == frozenset() and jump.planted(2.5) == BOTH


# --- reading a phrase -----------------------------------------------------------------------------------------------


def test_a_moment_on_a_key_is_that_key():
    found = moment(step(), 1.0)
    assert isinstance(found, Moment)
    assert dict(found.values) == {"right_upper_leg.front_back": -0.4}
    assert found.floor == Floor(right=0.05) and found.planted == LEFT and not found.airborne


def test_between_keys_every_channel_moves_on_the_next_keys_ease():
    phrase = step()
    smooth = moment(phrase, 0.5)  # 1:1 to 1:2 is smooth
    assert smooth.values["right_upper_leg.front_back"] == pytest.approx(-0.2)
    assert smooth.floor.right == pytest.approx(0.025)
    held = moment(phrase, 1.5)  # 1:2 to 1:3 is a hit: still on the last key half way
    assert held.values["right_upper_leg.front_back"] == pytest.approx(-0.4)
    assert held.values["chest.front_back"] == pytest.approx(0.0)
    struck = moment(phrase, 1.95)
    assert struck.values["chest.front_back"] < -0.1 and struck.floor.up < -0.03


def test_a_foot_carries_the_body_between_keys_only_when_both_name_it():
    phrase = step()
    assert moment(phrase, 0.5).planted == LEFT  # the right lifts as soon as 1:1 is passed
    assert moment(phrase, 1.5).planted == LEFT  # and lands on 1:3
    assert moment(phrase, 2.0).planted == BOTH


def test_the_face_is_the_last_one_a_key_set():
    phrase = step()
    assert moment(phrase, 1.0).expression is None
    assert moment(phrase, 2.0).expression == "grin" and moment(phrase, 7.9).expression == "grin"


def test_before_the_first_key_and_after_the_last_the_phrase_holds():
    phrase = step()
    assert moment(phrase, -2.0).floor == Floor() and moment(phrase, 99.0).floor == phrase.end
    assert moment(phrase, 99.0).values == moment(phrase, 2.0).values


@pytest.mark.parametrize("args, match", [(("step", 1.0), "Phrase"), ((None, math.nan), "beat")])
def test_a_moment_needs_a_phrase_and_a_beat(args, match):
    phrase, beat = args
    with pytest.raises(PhraseError, match=match):
        moment(step() if phrase is None else phrase, beat)


def test_a_mirrored_phrase_swaps_sides_and_travels_the_other_way():
    phrase = Phrase(
        "turn", 1, (Key(0.0, BOTH), Key(2.0, LEFT, (("right_upper_leg.in_out", 0.2),), floor=Floor(-0.1, 0.0, 0, 0.5)))
    )
    mirrored = phrase.mirror()
    last = mirrored.keys[-1]
    assert last.contacts == RIGHT and dict(last.pose) == {"left_upper_leg.in_out": 0.2}
    assert last.floor == Floor(0.1, 0.0, 0.0, -0.5)
    assert mirrored.mirror() == phrase


# --- sampled like any dance -----------------------------------------------------------------------------------------


def test_a_phrase_samples_into_an_ordinary_dance_frame():
    frame = dance.sample(step(), GROOVE, 1.0)  # beat 2: the hit on 1:3
    assert isinstance(frame, dance.DanceFrame)
    assert frame.move == "step" and frame.support == "feet" and frame.planted == BOTH and not frame.airborne
    assert frame.floor == Floor(right=0.1, up=-0.05) and frame.expression == "grin"
    assert frame.value("chest.front_back") == pytest.approx(-0.2) and frame.root == (0.0, 0.0, 0.0)
    assert len(list(dance.frames(step(), GROOVE, 0.0, 4.0, 10))) == 40


def _routine(*entries, bars=8):
    return Routine(bars, tuple(entries))


def test_a_routine_dances_a_phrase_again_from_where_it_left_the_body():
    routine = _routine(Entry(0, 4, step()))  # two times through the one-eight phrase
    first = dance.sample(routine, GROOVE, 1.0)
    again = dance.sample(routine, GROOVE, 1.0 + 8 * GROOVE.beat)
    assert first.floor.right == pytest.approx(0.1)
    assert again.floor.right == pytest.approx(0.2) and again.floor.up == pytest.approx(-0.05)
    after = dance.sample(routine, GROOVE, 6 * 4 * GROOVE.beat)  # rest after the entry: the body stays put
    assert (after.floor.right, after.floor.up, after.move) == (pytest.approx(0.2), 0.0, None)


def test_a_routine_turns_the_next_time_through_by_the_last_turn():
    quarter = Phrase("quarter", 1, (Key(0.0, BOTH), Key(4.0, BOTH, floor=Floor(forward=0.1, turn=math.pi / 2))))
    again = dance.sample(_routine(Entry(0, 4, quarter)), GROOVE, 12 * GROOVE.beat)
    assert again.floor.turn == pytest.approx(math.pi)
    assert (again.floor.right, again.floor.forward) == pytest.approx((0.1, 0.1))


def test_a_routine_crossfades_a_move_into_a_phrase_and_mirrors_it():
    bob = dance.moves()["bob"]
    routine = _routine(Entry(0, 2, bob), Entry(2, 4, step(), mirror=True, transition_beats=2.0, expression="smirk"))
    early = dance.sample(routine, GROOVE, 8 * GROOVE.beat + 0.2)
    late = dance.sample(routine, GROOVE, 8 * GROOVE.beat + 1.0 + 2 * GROOVE.beat)
    assert early.planted == BOTH  # still mostly the bob
    assert late.move == "step" and late.expression == "smirk" and late.floor.right == pytest.approx(-0.1)


def test_a_routine_holds_a_phrase_only_a_whole_number_of_times():
    with pytest.raises(RoutineError, match="whole number of step"):
        _routine(Entry(0, 3, step()))


def test_a_routine_crossfades_out_of_a_phrase_into_a_move():
    routine = _routine(Entry(0, 2, step()), Entry(2, 4, dance.moves()["bob"], transition_beats=2.0))
    mid = dance.sample(routine, GROOVE, 8 * GROOVE.beat + 0.5)
    assert mid.floor.right == pytest.approx(0.1)  # the body stays where the phrase left it
    assert -0.05 < mid.floor.up < 0.0  # the hips rise back as the phrase fades


def test_sampling_refuses_what_is_not_a_dance():
    with pytest.raises(DanceError, match="Move, a Phrase or a Routine"):
        dance.sample("step", GROOVE, 0.0)


# --- dance_pose carries the floor ---------------------------------------------------------------------------------


@pytest.mark.parametrize("preset", sk.PRESETS)
def test_dance_pose_moves_the_body_in_hip_heights_and_turns_it(preset):
    profile = sk.preset(preset)
    rest = sk.rest_pose(profile)
    frame = dance.sample(Phrase("go", 1, (Key(0.0, BOTH), Key(1.0, BOTH, floor=Floor(1.0, 0.5, -0.1, 0.0)))), GROOVE, 1)
    moved = dance_pose(profile, frame).pose.root.origin - rest.root.origin
    height = profile.pelvis_height
    assert (moved.x, moved.y, moved.z) == pytest.approx((height, 0.1 * height, 0.5 * height))
    turned = on_floor(profile, rest, Floor(turn=math.pi / 2)).root.rotation.rotate(sk.Vec3(0.0, 0.0, 1.0))
    assert (turned.x, turned.z) == pytest.approx((1.0, 0.0), abs=1e-9)  # a positive turn faces the right
    assert on_floor(profile, rest, Floor()) is rest


def test_on_floor_refuses_what_is_not_a_floor():
    profile = sk.preset("stick")
    with pytest.raises(sk.SkeletonSchemaError, match="dance.Floor"):
        on_floor(profile, sk.rest_pose(profile), (0, 0, 0, 0))


# --- the strict reader ----------------------------------------------------------------------------------------------


def document(*phrases, **top):
    return json.dumps({"schema": PHRASES_SCHEMA, "phrases": list(phrases), **top})


def written(**changes):
    phrase = {
        "name": "walk",
        "eights": 1,
        "keys": [
            {"count": "1:1", "contacts": ["left_foot", "right_foot"]},
            {"count": "1:2", "contacts": ["left_foot"], "floor": {"right": 0.1, "up": -0.05}, "ease": "hit"},
            {
                "count": "1:2&",
                "contacts": ["left_foot", "right_foot"],
                "floor": {"turn": 0.5},
                "pose": {"chest.front_back": -0.1},
                "expression": "smirk",
            },
        ],
    }
    phrase.update(changes)
    return phrase


def test_a_phrase_document_reads_into_phrases():
    found = parse_phrases(document(written(), generated_by={"tool": "t", "model": "m"}))
    walk = found["walk"]
    assert walk.keys[1].beat == 1.0 and walk.keys[1].ease == "hit" and walk.keys[2].expression == "smirk"
    assert walk.keys[2].floor == Floor(0.1, 0.0, -0.05, 0.5)  # a channel left out holds the key before's


def _bad(mutate):
    data = {"schema": PHRASES_SCHEMA, "phrases": [written()]}
    mutate(data)
    return json.dumps(data)


@pytest.mark.parametrize(
    "mutate, error, match",
    [
        (lambda d: d.update(schema="srstudio.dance-moves/1.0.0"), DanceSchemaError, "schema"),
        (lambda d: d.update(extra=1), DanceDataError, "extra"),
        (lambda d: d.update(phrases=[]), DanceDataError, "at least one"),
        (lambda d: d.update(phrases=[written()] * 2), DanceDataError, "named twice"),
        (lambda d: d.update(phrases=[written()] * 65), DanceDataError, "phrases"),
        (lambda d: d["phrases"][0].update(tempo=120), DanceDataError, "tempo"),
        (lambda d: d["phrases"][0].update(eights=True), DanceDataError, "eights"),
        (lambda d: d["phrases"][0].update(eights=1.5), DanceDataError, "eights"),
        (lambda d: d["phrases"][0].update(keys={}), DanceDataError, "keys"),
        (
            lambda d: d["phrases"][0].update(keys=[{"count": "1:1", "contacts": ["left_foot"]}] * 257),
            DanceDataError,
            "keys",
        ),
        (lambda d: d["phrases"][0]["keys"][0].update(count="1:9"), PhraseError, "EIGHT:COUNT"),
        (lambda d: d["phrases"][0]["keys"][0].update(count=1), DanceDataError, "count"),
        (lambda d: d["phrases"][0]["keys"][0].pop("contacts"), DanceDataError, "contacts"),
        (lambda d: d["phrases"][0]["keys"][0].update(contacts=["left_foot", "left_foot"]), DanceDataError, "once"),
        (lambda d: d["phrases"][0]["keys"][0].update(contacts=["left_hand"]), PhraseError, "frozenset"),
        (lambda d: d["phrases"][0]["keys"][0].update(contacts="left_foot"), DanceDataError, "contacts"),
        (lambda d: d["phrases"][0]["keys"][1].update(floor={"right": "far"}), DanceDataError, "right"),
        (lambda d: d["phrases"][0]["keys"][1].update(floor={"right": True}), DanceDataError, "right"),
        (lambda d: d["phrases"][0]["keys"][1].update(floor={"left": 0.1}), DanceDataError, "left"),
        (lambda d: d["phrases"][0]["keys"][1].update(floor={"right": 1e300}), PhraseError, "floor.right"),
        (lambda d: d["phrases"][0]["keys"][1].update(pose={"root.up": 0.1}), PhraseError, "root"),
        (lambda d: d["phrases"][0]["keys"][1].update(pose={"chest.front_back": [0.1]}), DanceDataError, "chest"),
        (lambda d: d["phrases"][0]["keys"][1].update(airborne="yes"), DanceDataError, "airborne"),
        (lambda d: d["phrases"][0]["keys"][1].update(ease=3), DanceDataError, "ease"),
        (lambda d: d["phrases"][0]["keys"][1].update(expression=None), DanceDataError, "expression"),
        (lambda d: d["phrases"][0]["keys"][1].update(contacts=[]), PhraseError, "airborne"),
        (lambda d: d["phrases"][0]["keys"].reverse(), PhraseError, "first key"),
    ],
)
def test_a_malformed_or_hostile_phrase_document_is_refused(mutate, error, match):
    with pytest.raises(error, match=match):
        parse_phrases(_bad(mutate))


@pytest.mark.parametrize(
    "text, match",
    [
        ('{"schema": "srstudio.dance-phrases/1.0.0", "phrases": [], "phrases": []}', "repeats"),
        ('{"schema": "srstudio.dance-phrases/1.0.0", "phrases": NaN}', "NaN|JSON"),
        ("[1, 2]", "object"),
        ("{" * 5000, "JSON"),
        (b"\xff\xfe", "JSON|UTF|utf"),
    ],
)
def test_text_that_is_not_one_clean_json_object_is_refused(text, match):
    with pytest.raises(DanceDataError, match=match):
        parse_phrases(text)


def test_a_phrase_file_loads_from_disk(tmp_path):
    path = tmp_path / "phrases.json"
    path.write_text(document(written()))
    assert list(dance.load_phrases(path)) == ["walk"]


# --- the shipped class phrases --------------------------------------------------------------------------------------


SHIPPED = ("groove-step", "kick-ball-change", "plie-roll", "turn-travel")


def _peak(phrase, target, pick=min):
    return pick(dict(k.pose).get(target, 0.0) for k in phrase.keys)


def test_the_class_phrases_ship_as_original_eights():
    found = dance.phrases()
    assert tuple(found) == SHIPPED
    assert all(p.eights == 1 and p.description for p in found.values())
    assert sum(p.eights for p in found.values()) in range(2, 5)  # two to four eight-counts in all


def test_the_class_phrases_dance_what_they_say():
    found = dance.phrases()
    kick = found["kick-ball-change"]
    assert min(_peak(kick, f"{s}_upper_leg.front_back") for s in ("left", "right")) <= -1.0  # a real kick
    plie = found["plie-roll"]
    assert min(k.floor.up for k in plie.keys) <= -0.15  # a deep plie
    assert _peak(plie, "left_upper_arm.down_up", max) >= 2.5 and _peak(plie, "right_upper_arm.down_up", max) >= 2.5
    rolls = [dict(k.pose).get("spine.front_back", 0.0) for k in plie.keys]
    assert min(rolls) < -0.2 and max(rolls) > 0.1  # the spine waves through forward and back
    turn = found["turn-travel"]
    assert min(k.floor.turn for k in turn.keys) == pytest.approx(-math.pi / 2)  # a quarter turn to the left
    assert max(abs(k.floor.right) + abs(k.floor.forward) for k in turn.keys) >= 0.2  # with travel
    groove = found["groove-step"]
    assert max(k.floor.right for k in groove.keys) >= 0.25 and len({k.contacts for k in groove.keys}) == 3


def test_each_class_phrase_returns_to_the_front():
    for phrase in dance.phrases().values():
        assert phrase.end.turn == 0.0 and abs(phrase.end.right) <= 0.15 and abs(phrase.end.forward) <= 0.15


# --- the choreographer draws phrases --------------------------------------------------------------------------------


def _song(bars, phrase_bars):
    parts = (SongPart(0, bars, 0.0, "high"),)
    phrases = math.ceil(bars / phrase_bars)
    return SongMap(CLASS, phrase_bars, (0.0,) * (bars * 4), (0.0,) * phrases, parts)


def test_the_choreographer_draws_a_phrase_only_where_it_fits_whole():
    library = {**dance.moves(), **dance.phrases()}
    palette = ch.Palette(high=("groove-step", "kick-ball-change", "arm-pump"))
    routine = ch.choreograph(_song(10, 4), support="feet", seed=3, palette=palette, library=library)
    names = [e.move.name for e in routine.entries]
    assert names[-1] == "arm-pump"  # the last phrase of the song is two bars: only the move fits it
    assert any(isinstance(e.move, Phrase) for e in routine.entries)
    frame = dance.sample(routine, CLASS, 2.0)
    assert isinstance(frame, dance.DanceFrame)


def test_the_choreographer_refuses_a_pool_with_nothing_that_fits():
    library = {**dance.moves(), **dance.phrases()}
    with pytest.raises(ch.ChoreographyError, match="fills 4 beats"):
        ch.choreograph(_song(1, 1), support="feet", seed=0, palette=ch.Palette(high=("groove-step",)), library=library)


def test_the_choreographer_refuses_a_library_of_something_else():
    with pytest.raises(ch.ChoreographyError, match="Move or dance.Phrase"):
        ch.choreograph(_song(4, 4), support="feet", seed=0, library={"bob": "bob"})


def test_the_class_phrases_hold_only_faces_a_style_knows():
    faces = {k.expression for p in dance.phrases().values() for k in p.keys if k.expression is not None}
    assert faces and faces <= set(ch.EXPRESSIONS)


def test_the_guides_phrase_parses_and_dances():
    from pathlib import Path

    guide = (Path(__file__).resolve().parents[1] / "docs" / "authoring-dance.md").read_text()
    blocks = guide.split("```json\n")[1:]
    documents = [block.split("```")[0] for block in blocks if PHRASES_SCHEMA in block.split("```")[0]]
    assert len(documents) == 1
    found = parse_phrases(documents[0])["side-step"]
    assert found.keys[-1].floor == Floor(right=0.12, up=-0.06) and found.planted(0.6) == LEFT
