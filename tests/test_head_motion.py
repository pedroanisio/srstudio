"""Organic head motion as data: hashed noise, springs, the speech schedule, the idle layers, the glances (ADR 0050)."""

from __future__ import annotations

import importlib.util
import math
import wave
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import head_motion as hm
from srstudio.head_motion import Channel, HeadMotionError, HeadStyle, Spring, Word
from srstudio.voice import Alignment
from support.spring_curve import peak, sample

STYLE = HeadStyle(
    seed=7,
    signature="^",
    nod_px=6.0,
    nod_roll=1.0,
    head=Spring(1.4, 0.75, 0.1),
    settle=Spring(0.8, 0.9),
    body=Spring(1.0, 1.0),
)


def alignment(text: str, step: float = 0.08, gaps: dict[int, float] | None = None) -> Alignment:
    """Evenly timed characters; ``gaps`` adds silence before the character at an index."""
    gaps = gaps or {}
    chars, starts, ends = [], [], []
    t = 0.0
    for i, c in enumerate(text):
        t += gaps.get(i, 0.0)
        chars.append(c)
        starts.append(round(t, 4))
        t += step
        ends.append(round(t, 4))
    return Alignment(tuple(chars), tuple(starts), tuple(ends))


def speech(text: str, at: float = 1.0, level=lambda t: -20.0, **kw) -> hm.Speech:
    words = hm.words_of(alignment(text, **kw), at)
    end = max(w.end for w in words) - at + 0.5
    levels = tuple(level(k / hm.LOUD_RATE) for k in range(int(end * hm.LOUD_RATE)))
    return hm.Speech(at, words, levels)


def loud_on(*spans):
    return lambda t: -10.0 if any(a <= t < b for a, b in spans) else -24.0


# -- noise -------------------------------------------------------------------------------------------------------------
def test_a_hash_is_the_same_on_every_run_and_differs_by_channel_and_index():
    assert hm.hash_unit(1, "a", 0) == pytest.approx(hm.hash_unit(1, "a", 0))
    assert 0.0 <= hm.hash_unit(1, "a", 0) < 1.0
    assert (
        len({hm.hash_unit(1, "a", 0), hm.hash_unit(1, "b", 0), hm.hash_unit(1, "a", 1), hm.hash_unit(2, "a", 0)}) == 4
    )
    assert round(hm.hash_unit(1, "a", 0), 9) == 0.351548713  # no platform or Python version may move it


def test_noise_is_smooth_bounded_and_zero_on_its_lattice():
    values = [hm.fbm(k * 0.02, 0.5, 3, "x") for k in range(2000)]
    assert max(abs(v) for v in values) <= 1.0 and max(values) > 0.2 and min(values) < -0.2
    assert max(abs(b - a) for a, b in zip(values, values[1:], strict=False)) < 0.06  # a slow wander, no jumps
    assert hm.noise(3.0, 1, "y") == 0.0
    with pytest.raises(HeadMotionError):
        hm.fbm(float("nan"), 0.5, 1, "x")


# -- springs -----------------------------------------------------------------------------------------------------------
def test_a_spring_is_named_by_frequency_and_damping_and_written_as_the_engine_reads_it():
    s = Spring(1.0, 0.5)
    attrs = s.attributes()
    assert float(attrs["stiffness"]) == pytest.approx((2 * math.pi) ** 2, abs=1e-3)
    assert float(attrs["damping"]) == pytest.approx(2 * 0.5 * 2 * math.pi, abs=1e-3)
    assert attrs["mass"] == "1"


@pytest.mark.parametrize(
    "bad", [(0.0, 0.5, 0.0), (-1.0, 0.5, 0.0), (1.0, 0.0, 0.0), (1.0, 2.5, 0.0), (1.0, 0.5, 0.6), (float("inf"), 1, 0)]
)
def test_a_spring_that_cannot_settle_is_refused(bad):
    with pytest.raises(HeadMotionError):
        Spring(*bad)


# -- words and stress --------------------------------------------------------------------------------------------------
def test_words_come_from_the_character_timestamps_with_the_punctuation_on_the_side():
    words = hm.words_of(alignment("And everyone, knows."), 2.0)
    assert [w.text for w in words] == ["And", "everyone", "knows"]
    assert words[0].start == 2.0
    assert [w.stop for w in words] == [False, True, True]
    assert len(words[1].chars) == len("everyone")


def test_words_of_an_empty_alignment_are_none_and_bad_timing_is_refused():
    assert hm.words_of(Alignment((), (), ()), 0.0) == ()
    with pytest.raises(HeadMotionError):
        hm.words_of(alignment("hi"), -1.0)
    with pytest.raises(HeadMotionError):
        hm.words_of(Alignment(("a", "b"), (0.5, 0.1), (0.6, 0.2)), 0.0)


@pytest.mark.parametrize(
    "word,expected",
    [
        ("everyone", (0, 3)),
        ("rested", (0, 2)),
        ("knows", (0, 1)),
        ("absolutely", (2, 4)),
        ("Banana", (1, 3)),
        ("didn't", (0, 2)),
    ],
)
def test_stress_comes_from_the_dictionary(word, expected):
    assert hm.stress(word) == expected


def test_a_word_outside_the_dictionary_is_stressed_on_its_first_vowel_group():
    assert hm.stress("zzblorptang") == (0, 2)
    assert hm.stress("brrr") == (0, 1)


def test_the_stressed_syllable_is_found_in_the_word_and_runs_about_three_phones():
    words = hm.words_of(alignment("banana"), 0.0)
    at, span = hm.stressed_at(words[0])
    assert at == pytest.approx(words[0].chars[3][0])  # the "a" of ba-NA-na
    assert span == pytest.approx(0.24)
    short = hm.words_of(alignment("go"), 0.0)[0]
    assert hm.stressed_at(short)[1] == pytest.approx(0.08)  # never past the word's end
    odd = hm.words_of(alignment("everyone"), 0.0)[0]  # three syllables in four vowel groups: proportional
    assert hm.stressed_at(odd)[0] == pytest.approx(odd.chars[0][0])


# -- the schedule ------------------------------------------------------------------------------------------------------
def test_accents_are_stressed_loud_content_words():
    s = speech("And everyone knows I rested", level=loud_on((0.32, 0.5), (1.68, 1.9)))
    accents = hm.accents(s, STYLE)
    assert [a.word.text for a in accents] == ["everyone", "rested"]
    assert all(a.over > 0 for a in accents)


def test_every_phrase_has_its_loudest_and_its_last_content_word_as_accents_even_in_a_flat_read():
    s = speech("Nobody ever reads anything")
    assert [a.word.text for a in hm.accents(s, STYLE)] == ["Nobody", "anything"]


def test_a_phrase_ends_on_its_nuclear_accent_however_quietly_it_is_said():
    s = speech("And everyone knows I rested", level=loud_on((0.32, 0.5)))
    assert hm.accents(s, STYLE)[-1].word.text == "rested"


def test_a_nuclear_accent_is_never_dropped_for_the_nod_before_it():
    s = speech("Everyone rested", step=0.05)
    style = replace(STYLE, min_gap=5.0)
    assert [n.word for n in hm.nods(s, style)] == ["rested"]


def test_a_nuclear_accent_always_carries_a_nod():
    style = replace(STYLE, nod_share=0.01, min_gap=0.0)
    assert [n.word for n in hm.nods(speech("Everyone rested"), style)] == ["rested"]


def test_a_character_that_never_nods_does_not_nod_on_a_nuclear_accent_either():
    assert hm.nods(speech("Everyone rested"), replace(STYLE, nod_share=0.0)) == []


def test_a_phrase_of_only_function_words_has_no_accent():
    assert hm.accents(speech("and then it was"), STYLE) == []


def test_about_four_in_five_accents_carry_a_nod():
    words = " ".join(f"word{k}" for k in range(4))
    text = ", ".join(words for _ in range(120))
    s = speech(text, step=0.05)
    style = replace(STYLE, min_gap=0.0)
    every = hm.accents(s, style)
    kept = hm.nods(s, style)
    assert 0.72 <= len(kept) / len(every) <= 0.88


def test_a_nod_lasts_two_to_four_phones_leads_its_syllable_and_keeps_the_gap():
    s = speech("Monday Tuesday Wednesday Thursday, Friday Saturday Sunday", step=0.07, level=loud_on((0.0, 9.0)))
    style = replace(STYLE, nod_share=1.0)
    nods = hm.nods(s, style)
    assert len(nods) >= 2
    assert all(0.12 <= n.span <= 0.34 for n in nods)
    assert all(b.at - a.at >= style.min_gap for a, b in zip(nods, nods[1:], strict=False))
    first = hm.accents(s, style)[0]
    assert nods[0].at == pytest.approx(first.at - style.lead)


def test_one_character_repeats_one_movement_type():
    s = speech("Monday, Tuesday, Wednesday, Thursday", step=0.1)
    assert {n.kind for n in hm.nods(s, replace(STYLE, signature="~", nod_share=1.0))} == {"~"}
    assert {n.kind for n in hm.nods(s, replace(STYLE, signature="/", nod_share=1.0))} == {"/"}


def test_an_intensifier_earns_a_bigger_nod_inside_the_bound():
    plain = hm.nods(speech("It was good"), replace(STYLE, nod_share=1.0))
    strong = hm.nods(speech("It was really good"), replace(STYLE, nod_share=1.0))
    assert strong[0].word == "really"
    assert plain[0].amplitude < strong[0].amplitude <= STYLE.nod_px * hm.INTENSIFIER_GAIN


def test_a_phrase_after_a_pause_opens_with_a_dip():
    text = "First part here. Second part there"
    s = speech(text, gaps={17: 0.6})
    dips = hm.dips(s)
    assert dips == [s.words[0].start, s.words[3].start]
    assert hm.dips(speech("First part, second part")) == [1.0]  # a comma with no pause is no new breath


# -- the plan ----------------------------------------------------------------------------------------------------------
def line() -> hm.Speech:
    return speech("And everyone knows I rested.", level=loud_on((0.3, 0.6), (1.7, 2.0)))


def test_the_same_inputs_give_the_same_plan_and_the_seed_moves_it():
    a = hm.plan(STYLE, [line()], 6.0)
    assert a == hm.plan(STYLE, [line()], 6.0)
    assert a != hm.plan(replace(STYLE, seed=8), [line()], 6.0)


def test_changing_the_speech_leaves_the_idle_noise_at_its_lattice():
    quiet, spoken = hm.plan(STYLE, [], 6.0), hm.plan(STYLE, [line()], 6.0)
    assert quiet.idle_roll.keys[0] == spoken.idle_roll.keys[0]  # the same hash lattice, only the duck differs


@pytest.mark.parametrize("name", hm.CHANNELS)
@pytest.mark.parametrize("seed", range(6))
def test_every_channel_stays_inside_its_bound_through_the_springs(name, seed):
    style = replace(STYLE, seed=seed)
    s = speech("I really absolutely never ever said that, not once, not ever", level=loud_on((0.0, 3.0)))
    channel = getattr(hm.plan(style, [s], 14.0), name)
    assert channel.keys
    assert peak(channel) <= hm.limit(style, name)


SWAY = replace(STYLE, signature="~", nod_px=4.5, head=Spring(1.9, 0.72, 0.1), nod_share=1.0)  # Rafa's head


def short_loud_so() -> hm.Speech:
    """A line opening on a short, loud intensifier: the shortest nod at the full gain."""
    return speech("So that's what I sound like.", step=0.06, level=loud_on((0.0, 0.12)))


def test_a_short_loud_intensifier_on_a_swaying_head_stays_inside_the_bound():
    """The sway crested and troughed inside the shortest nod, 0.06 s apart, faster than the head's spring follows: the
    spring overshot the style's own envelope and the plan raised (a Small Print take, 2026-11-03)."""
    first = hm.nods(short_loud_so(), SWAY)[0]
    assert (first.word, first.kind, first.span) == ("So", "~", hm.NOD_SPAN[0])
    assert first.amplitude == SWAY.nod_px * hm.INTENSIFIER_GAIN
    plan = hm.plan(SWAY, [short_loud_so()], 6.0)
    for name in ("nod", "roll"):
        assert peak(getattr(plan, name)) <= hm.limit(SWAY, name)


def library_styles() -> list[tuple[str, HeadStyle]]:
    """Every head style the library ships, by module and name."""
    found = {}
    for module in ("host_kit", "news_head", "pedro_host", "rafa_host", "toon_bento", "toon_critters", "toon_inked",
                   "toon_lyra", "toon_redrawn"):  # fmt: skip
        for name, value in vars(importlib.import_module(f"srstudio.{module}")).items():
            if isinstance(value, HeadStyle):
                found[f"{module}.{name}"] = value
    return sorted(found.items())


@pytest.mark.parametrize("step", [0.04, 0.06, 0.08])
@pytest.mark.parametrize(("name", "style"), library_styles(), ids=[name for name, _ in library_styles()])
def test_every_library_head_follows_a_short_loud_intensifier_inside_its_envelope(name, style, step):
    """Rafa's head overshot the nod envelope, and the host, fox and dog heads the roll envelope, on this line."""
    s = speech("So that's what I sound like.", step=step, level=loud_on((0.0, 2 * step)))
    plan = hm.plan(style, [s], 6.0)
    for channel in ("nod", "roll"):
        assert peak(getattr(plan, channel)) <= hm.limit(style, channel)


def test_a_nod_the_spring_cannot_follow_swings_longer_and_one_it_can_keeps_its_span():
    s = short_loud_so()
    lead = hm.ANTICIPATE
    for style, stretched in ((SWAY, True), (replace(SWAY, head=Spring(4.0, 0.72, 0.1)), False)):
        nod = hm.nods(s, style)[0]
        crests = [t for t, v in hm.plan(style, [s], 6.0).nod.keys if v == round(nod.amplitude, 4)]
        assert len(crests) == 1
        assert (crests[0] > round(nod.at + lead + nod.span * 0.5, 6)) is stretched
        assert crests[0] <= round(nod.at + lead + hm.NOD_SPAN[1] * 0.5, 6)


@pytest.mark.parametrize("name", ("nod", "roll", "turn", "lean", "face_x"))
def test_a_spring_channel_comes_back_to_rest_after_the_last_word(name):
    plan = hm.plan(STYLE, [line()], 8.0)
    channel = getattr(plan, name)
    assert channel.keys[-1][1] == 0.0 and channel.keys[-1][0] <= 8.0
    assert abs(sample(channel, 8.0)) < 0.01


def test_key_times_rise_and_stay_inside_the_duration():
    plan = hm.plan(STYLE, [line()], 6.0)
    for name in hm.CHANNELS:
        times = [t for t, _ in getattr(plan, name).keys]
        assert times == sorted(set(times)), name
        assert times[0] >= 0.0 and times[-1] <= 6.0, name
    gaze = [t for t, _ in plan.gaze]
    assert gaze == sorted(set(gaze))


def test_a_signature_slow_shift_returns_slower_than_a_plain_nod():
    s = speech("Everyone knows", at=1.0)
    plain = hm.plan(replace(STYLE, nod_share=1.0, signature="^"), [s], 6.0).nod
    shift = hm.plan(replace(STYLE, nod_share=1.0, signature="/"), [s], 6.0).nod
    assert shift.keys[-1][0] > plain.keys[-1][0]


def test_an_overshooting_nod_swings_past_rest_on_the_way_back():
    s = speech("Everyone knows", at=1.0)
    nod = hm.plan(replace(STYLE, nod_share=1.0, signature="~"), [s], 6.0).nod
    assert min(v for _, v in nod.keys) < -0.3


def test_anticipation_moves_the_head_the_other_way_first():
    s = speech("Everyone knows", at=1.0)
    keys = hm.plan(replace(STYLE, nod_share=1.0, signature="^"), [s], 6.0).nod.keys
    first_up = next(i for i, (_, v) in enumerate(keys) if v > 1.0)
    assert any(v < 0 for _, v in keys[:first_up])


def test_a_nod_cut_short_by_the_next_runs_straight_into_it():
    s = speech("Everyone knows it", step=0.05)
    style = replace(STYLE, nod_share=1.0, signature="/", min_gap=0.0)
    keys = hm.plan(style, [s], 6.0).nod.keys
    assert [t for t, _ in keys] == sorted(t for t, _ in keys)


def test_idle_ducks_while_the_character_speaks():
    plan = hm.plan(STYLE, [speech("Monday Tuesday Wednesday Thursday Friday Saturday", at=2.0, step=0.1)], 12.0)
    spoken = [abs(v) for t, v in plan.idle_roll.keys if 2.2 < t < 5.0]
    bound = STYLE.idle_roll * hm.DUCK
    assert spoken and max(spoken) <= bound + 1e-9
    assert plan.idle_roll.curve == "catmull-rom"


def test_breath_is_an_uneven_cycle_when_quiet():
    keys = hm.plan(STYLE, [], 20.0).breath.keys
    rises = [b[0] - a[0] for a, b in zip(keys, keys[1:], strict=False) if b[1] > a[1]]
    falls = [b[0] - a[0] for a, b in zip(keys, keys[1:], strict=False) if b[1] < a[1]]
    assert len(rises) >= 3
    assert sum(rises) < sum(falls)  # in quickly, out slowly
    assert len({round(r, 3) for r in rises}) > 1  # no metronome


@pytest.mark.parametrize("duration", (3.0, 6.0, 8.0, 9.5, 11.0))
def test_a_shot_ends_part_way_through_a_breath_instead_of_holding_still_for_a_cycle_that_would_not_fit(duration):
    keys = hm.plan(STYLE, [], duration).breath.keys
    assert keys[-1][0] == duration
    assert all(b[0] - a[0] <= STYLE.breath_period * 1.15 for a, b in zip(keys, keys[1:], strict=False))
    assert 0.0 <= keys[-1][1] <= 1.0
    assert keys[-1][1] != keys[-2][1]


def test_a_breath_carries_on_after_the_last_word():
    keys = hm.plan(STYLE, [speech("Nobody ever reads anything")], 5.0).breath.keys
    assert keys[-1][0] == 5.0
    assert max(v for t, v in keys if t > 3.5) > 0.3


def test_breath_is_taken_in_the_pause_and_let_out_across_the_phrase():
    s = speech("First part here. Second part there", gaps={17: 0.6})
    keys = dict(hm.plan(STYLE, [s], 8.0).breath.keys)
    second = s.words[3].start
    assert keys[round(second, 6)] == 1.0
    end = s.words[-1].end
    assert keys[round(end, 6)] == 0.0


def test_glances_hold_the_eyes_and_the_head_follows_late_and_comes_back():
    plan = hm.plan(STYLE, [], 20.0)
    assert plan.gaze and plan.gaze[0][1] in hm.GAZES and plan.gaze[-1][1] == "ahead"
    away = plan.gaze[0][0]
    assert away > 0.0
    first_move = next(t for t, v in plan.face_x.keys if v != 0.0) if plan.gaze[0][1] != "up" else away + 1.0
    assert first_move > away  # eyes first, then the head
    assert {g for _, g in plan.gaze} - {"ahead"}


def test_a_line_can_open_with_a_look_away_and_the_eyes_are_back_for_the_first_word():
    for seed in range(12):
        s = speech("Everyone knows", at=3.0)
        gaze = hm.plan(replace(STYLE, seed=seed, glance_every=100.0, avert=1.0), [s], 6.0).gaze
        assert gaze[0][0] < 3.0 and gaze[1] == (round(3.0 - hm.AVERT_BACK, 6), "ahead")


def test_the_eyes_keep_to_the_camera_while_a_line_plays():
    s = speech("Monday Tuesday Wednesday Thursday Friday Saturday", at=1.0, step=0.1)
    plan = hm.plan(replace(STYLE, avert=0.0, glance_every=2.0), [s], 9.0)
    assert plan.gaze
    for t, gaze in plan.gaze:
        assert not (1.0 <= t <= s.words[-1].end) or gaze == "ahead"


def test_a_short_quiet_plan_has_room_for_nothing_but_still_breathes_and_drifts():
    plan = hm.plan(STYLE, [], 0.5)
    assert plan.gaze == ()
    assert plan.idle_roll.keys and plan.breath.keys


def test_the_lean_opens_on_the_phrase_and_the_head_trails_it():
    plan = hm.plan(STYLE, [line()], 6.0)
    start = line().words[0].start
    assert any(v != 0.0 for t, v in plan.lean.keys if start < t < start + 1.0)
    trailing = [t for t, v in plan.turn.keys if v != 0.0]
    assert trailing and min(trailing) > start  # the head goes after the body


def test_a_still_plan_has_no_keys_at_all():
    still = hm.HeadPlan.still()
    assert all(not getattr(still, name).keys for name in hm.CHANNELS) and still.gaze == ()


# -- failure paths -----------------------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "change",
    [
        {"signature": "x"},
        {"nod_px": 0.0},
        {"nod_px": float("nan")},
        {"nod_roll": -1.0},
        {"nod_share": 1.5},
        {"min_gap": -0.1},
        {"lead": -0.1},
        {"idle_roll": -1.0},
        {"idle_hz": 0.0},
        {"breath_period": 0.0},
        {"breath_px": -1.0},
        {"breath_scale": 1.0},
        {"glance_every": 0.0},
        {"glance_hold": 0.0},
        {"avert": 2.0},
        {"lean": -1.0},
        {"follow": 2.0},
    ],
)
def test_a_style_out_of_range_is_refused_by_name(change):
    key = next(iter(change))
    with pytest.raises(HeadMotionError, match=key):
        replace(STYLE, **change)


def test_a_plan_refuses_a_bad_duration_and_unsorted_or_overrunning_speech():
    with pytest.raises(HeadMotionError):
        hm.plan(STYLE, [], 0.0)
    with pytest.raises(HeadMotionError):
        hm.plan(STYLE, [], float("nan"))
    with pytest.raises(HeadMotionError):
        hm.plan(STYLE, [speech("Hello", at=3.0), speech("Hello", at=1.0)], 6.0)
    with pytest.raises(HeadMotionError):
        hm.plan(STYLE, [speech("Hello there my friend", at=5.5)], 6.0)


def test_speech_refuses_nan_loudness_and_words_out_of_order():
    words = hm.words_of(alignment("Hello there"), 0.0)
    with pytest.raises(HeadMotionError):
        hm.Speech(0.0, words, (float("nan"),))
    with pytest.raises(HeadMotionError):
        hm.Speech(0.0, words[::-1], (-20.0,))
    with pytest.raises(HeadMotionError):
        hm.Speech(float("inf"), words, (-20.0,))


def test_a_word_refuses_bad_times():
    with pytest.raises(HeadMotionError):
        Word("x", 1.0, 0.5, ((1.0, 0.5),), False)
    with pytest.raises(HeadMotionError):
        Word("", 0.0, 0.5, (), False)


def test_a_channel_refuses_keys_out_of_order():
    with pytest.raises(HeadMotionError):
        Channel(((1.0, 0.0), (0.5, 0.0)))
    with pytest.raises(HeadMotionError):
        Channel(((0.0, float("nan")),))


# -- reading a take ----------------------------------------------------------------------------------------------------
def test_a_take_s_loudness_is_read_per_hundredth_in_decibels(tmp_path):
    path = tmp_path / "tone.wav"
    rate = 48000
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = bytearray()
        for k in range(rate // 2):  # half a second of tone, half of silence
            frames += int(8000 * math.sin(k * 0.05)).to_bytes(2, "little", signed=True)
        frames += bytes(rate)
        w.writeframes(bytes(frames))
    s = hm.speech_of(alignment("Hello"), 1.0, path)
    assert s.at == 1.0 and [w.text for w in s.words] == ["Hello"]
    assert len(s.levels) == pytest.approx(100, abs=1)
    assert s.levels[10] > s.levels[80] + 40  # the tone over the silence
    assert s.level(1.1) == s.levels[10] and s.level(-5.0) == s.levels[0] and s.level(99.0) == s.levels[-1]


# -- the stress table --------------------------------------------------------------------------------------------------
def test_the_stress_table_builds_from_the_dictionary_text_byte_for_byte(tmp_path):
    root = Path(__file__).parent.parent
    spec = importlib.util.spec_from_file_location("build_stress", root / "tools" / "build_stress.py")
    assert spec and spec.loader
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    text = "absolutely AE2 B S AH0 L UW1 T L IY0\nabsolutely(2) AE1 B S AH0 L UW2 T L IY0\nbrr B R\ngo G OW1 # note\n"
    assert tool.table(text) == "absolutely\t2010\nbrr\t\ngo\t1\n"
    source = tmp_path / "d.dict"
    source.write_text(text, encoding="utf-8")
    a, b = tmp_path / "a.gz", tmp_path / "b.gz"
    for out in (a, b):
        tool.sys.argv = ["build_stress.py", str(source), str(out)]
        tool.main()
    assert a.read_bytes() == b.read_bytes()


# -- listening ---------------------------------------------------------------------------------------------------------
def other() -> hm.Speech:
    return speech("The quarterly report is finished, and everybody really loved it.", at=2.0)


def test_nobody_else_speaking_plans_exactly_what_it_planned_before():
    assert hm.plan(STYLE, [line()], 8.0, heard=()) == hm.plan(STYLE, [line()], 8.0)


def test_a_listener_nods_small_at_the_end_of_the_other_s_phrases():
    plan = hm.plan(STYLE, [], 10.0, heard=[other()])
    alone = hm.plan(STYLE, [], 10.0)
    assert alone.nod.keys == ((0.0, 0.0),)
    biggest = max(abs(v) for _, v in plan.nod.keys)
    assert 0.0 < biggest <= round(STYLE.nod_px * hm.LISTEN_SHARE, 4)
    nuclear = [a.at + a.span for a in hm.accents(other(), STYLE) if a.nuclear]
    assert all(min(abs(t - at) for at in nuclear) < 1.0 for t, v in plan.nod.keys if v)


def test_a_listener_nods_on_its_own_signature_and_never_rolls_or_leans():
    plan = hm.plan(replace(STYLE, signature="/"), [], 10.0, heard=[other()])
    assert plan.roll.keys == ((0.0, 0.0),)
    assert plan.lean.keys == ((0.0, 0.0),)
    assert len(plan.nod.keys) > 1


def test_a_listener_keeps_its_eyes_on_the_speaker_and_quiets_its_idle():
    spoken = other()
    start, end = spoken.words[0].start, spoken.words[-1].end
    style = replace(STYLE, glance_every=1.0, glance_hold=0.3)
    alone = hm.plan(style, [], 12.0)
    plan = hm.plan(style, [], 12.0, heard=[spoken])
    assert any(start <= t <= end for t, name in alone.gaze)
    assert not any(start - 0.3 <= t <= end + 0.3 for t, name in plan.gaze)
    quiet = [
        (a, b) for (a, b), (_, c) in zip(alone.idle_roll.keys, plan.idle_roll.keys, strict=True) if abs(c) != abs(b)
    ]
    assert quiet and all(start - 0.3 <= t <= end + 0.3 for t, _ in quiet)


def test_listening_leaves_the_breath_to_the_character_s_own_speech():
    assert hm.plan(STYLE, [], 10.0, heard=[other()]).breath == hm.plan(STYLE, [], 10.0).breath


def test_a_character_that_speaks_while_another_does_keeps_its_own_nods_and_adds_none():
    own = speech("Absolutely not, and that is final, and I will say it again and again.", at=2.0)
    assert hm.plan(STYLE, [own], 10.0, heard=[other()]).nod == hm.plan(STYLE, [own], 10.0).nod


def test_a_character_that_never_nods_does_not_nod_while_listening_either():
    assert hm.plan(replace(STYLE, nod_share=0.0), [], 10.0, heard=[other()]).nod.keys == ((0.0, 0.0),)


def test_what_is_heard_is_checked_like_what_is_said():
    with pytest.raises(HeadMotionError, match="past the shot"):
        hm.plan(STYLE, [], 3.0, heard=[other()])


# -- a shot's keys -----------------------------------------------------------------------------------------------------
def test_a_channel_during_a_shot_keeps_its_keys_and_one_either_side():
    channel = Channel(((0.0, 0.0), (1.0, 1.0), (2.0, 2.0), (3.0, 3.0), (4.0, 4.0)), STYLE.head)
    assert channel.during(1.5, 2.5).keys == ((0.0, 0.0), (1.0, 1.0), (2.0, 2.0), (3.0, 3.0))
    assert channel.during(2.0, 3.0).keys == ((0.0, 0.0), (1.0, 1.0), (2.0, 2.0), (3.0, 3.0))
    assert channel.during(1.5, 2.5).spring is STYLE.head


def test_spring_during_keeps_the_same_position_and_velocity_at_a_shot_cut():
    channel = Channel(((0.0, 0.0), (1.0, 10.0), (2.0, 0.0), (3.0, 10.0)), hm.Spring(0.5, 0.2))
    first, second = channel.during(0.0, 1.5), channel.during(1.5, 3.0)
    for t in (1.49, 1.5, 1.51):
        assert sample(first, t) == pytest.approx(sample(second, t), abs=1e-8)


def test_catmull_rom_during_keeps_neighboring_keys_for_matching_tangents():
    channel = Channel(tuple((float(i), float(i % 2)) for i in range(8)), curve='catmull-rom')
    assert channel.during(3.5, 4.5).keys == channel.keys[2:7]


def test_long_carried_spring_rejects_work_above_its_sampling_budget():
    channel = Channel(tuple((float(i * 100), float(i)) for i in range(10)), Spring(0.5, 0.7))
    with pytest.raises(HeadMotionError, match='sampling budget'):
        channel.during(0, 1)


def test_long_spring_rejects_unrepresentable_frequency_with_typed_error():
    channel = Channel(tuple((float(i), float(i)) for i in range(10)), Spring(1e308, 0.7))
    with pytest.raises(HeadMotionError, match='sampling budget'):
        channel.during(0, 1)


def test_a_shot_past_the_last_key_keeps_the_last_key():
    assert Channel(((0.0, 0.0), (1.0, 1.0))).during(5.0, 6.0).keys == ((1.0, 1.0),)


def test_a_plan_during_a_shot_moves_the_same_and_keeps_every_gaze_state():
    plan = hm.plan(STYLE, [line()], 12.0)
    shot = plan.during(3.0, 5.0)
    assert shot.gaze == plan.gaze
    for name in ("lean", "turn", "nod", "roll", "face_x", "idle_roll", "idle_y", "breath"):
        kept, whole = getattr(shot, name), getattr(plan, name)
        if whole.spring and len(whole.keys) > hm.SPRING_RUN:
            assert kept.spring is None and kept.curve == "linear"
            assert kept.keys[0][0] <= max(3, whole.keys[0][0])
            assert kept.keys[-1][0] >= min(5, whole.keys[-1][0])
        else:
            assert set(kept.keys) <= set(whole.keys)
            assert len(kept.keys) <= len(whole.keys)
