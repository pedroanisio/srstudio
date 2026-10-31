"""Keyboard foley: keystroke bursts where the tracked hand moves, synthesised deterministically."""

import dataclasses
import wave

import pytest

from srstudio import cel, foley

SAMPLES = [cel.Feature(i * 0.25, x, 200.0) for i, x in enumerate([100, 100, 100, 80, 100, 100, 70, 100])]


def test_bursts_fall_where_the_hand_moves_more_than_the_threshold_while_on_the_keyboard():
    assert foley.typing_bursts(SAMPLES, threshold=8.0) == [0.75, 1.0, 1.5, 1.75]
    assert foley.typing_bursts(SAMPLES, threshold=50.0) == []
    assert foley.typing_bursts(SAMPLES, threshold=8.0, spans=[(0.0, 1.0), (1.75, 2.0)]) == [0.75, 1.75]
    with pytest.raises(ValueError, match="threshold"):
        foley.typing_bursts(SAMPLES, threshold=0)


def test_taps_are_a_few_keystrokes_shortly_after_each_burst_and_repeat_for_a_seed():
    a = foley.taps([0.75, 2.0], seed=5)
    assert a == foley.taps([2.0, 0.75], seed=5) and a != foley.taps([0.75, 2.0], seed=6)
    first = [t for t in a if t < 2.0]
    assert 2 <= len(first) <= 4 and 0.77 <= first[0] and first[-1] <= 0.75 + 4 * 0.08
    assert a == sorted(a) and all(t > 2.0 for t in a if t not in first)
    assert foley.taps([]) == []


def test_taps_until_a_bound_are_the_same_taps_cut_there_so_a_bed_of_that_length_takes_them():
    bursts = [0.4, 1.0, 2.69]  # the last one held to a 3 s end: its taps can run past the bed's tail
    end = 3.0
    for seed in range(40):
        free = foley.taps(bursts, seed=seed)
        bound = foley.taps(bursts, seed=seed, until=end - foley.KEY_TAIL)
        assert bound == [t for t in free if t <= end - foley.KEY_TAIL]
        foley.keystrokes(bound, end, rate=8000, seed=seed)
    assert any(max(foley.taps(bursts, seed=s)) > end - foley.KEY_TAIL for s in range(40))


def test_keystrokes_are_deterministic_bounded_and_levelled(tmp_path):
    a = foley.keystrokes([0.75, 1.0], duration=1.5, rate=8000, seed=7, peak=0.5)
    b = foley.keystrokes([0.75, 1.0], duration=1.5, rate=8000, seed=7, peak=0.5)
    assert a == b and len(a) == 12000
    assert 0.49 <= max(abs(v) for v in a) <= 0.5
    assert all(v == 0 for v in a[: int(0.70 * 8000)])  # silence before the first burst
    assert any(v != 0 for v in a[int(0.75 * 8000) : int(1.0 * 8000)])  # strokes after it
    assert foley.keystrokes([], duration=0.5, rate=8000) == [0.0] * 4000
    with pytest.raises(ValueError, match="duration"):
        foley.keystrokes([0.1], duration=0.05, rate=8000)
    with pytest.raises(ValueError, match="peak"):
        foley.keystrokes([], duration=0.1, rate=8000, peak=1.5)
    path = foley.write_typing(tmp_path / "typing.wav", [0.8, 0.85], duration=2.0, rate=8000, seed=3, peak=0.5)
    with wave.open(str(path), "rb") as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()) == (1, 2, 8000, 16000)
    with pytest.raises(ValueError, match="rate"):
        foley.write_typing(tmp_path / "x.wav", [0.8], duration=2.0, rate=100, seed=3, peak=0.5)


def test_a_phone_buzz_is_two_pulses_deterministic_bounded_and_quiet_elsewhere(tmp_path):
    bed = foley.buzz([0.5, 1.5], 2.0, rate=8000, seed=3, peak=0.6)
    assert len(bed) == 16000 and bed == foley.buzz([0.5, 1.5], 2.0, rate=8000, seed=3, peak=0.6)
    assert max(abs(v) for v in bed) == pytest.approx(0.6)
    assert all(v == 0 for v in bed[:4000]) and all(v == 0 for v in bed[int(0.86 * 8000) : 12000])
    first, second = (
        bed[4000 : 4000 + int(foley.BUZZ * 8000 / 2)],
        bed[4000 + int(foley.BUZZ * 8000 / 2) : 4000 + int(foley.BUZZ * 8000)],
    )
    assert max(map(abs, first)) > 0.3 and max(map(abs, second)) > 0.3
    gap = bed[4000 + int(foley.BUZZ / 2 * 0.9 * 8000) : 4000 + int(foley.BUZZ / 2 * 8000)]
    assert all(v == 0 for v in gap)  # the gap between the pulses
    out = foley.write_buzz(tmp_path / "buzz.wav", [0.5], 2.0, rate=8000, seed=3, peak=0.6)
    with wave.open(str(out), "rb") as w:
        assert (w.getnchannels(), w.getframerate(), w.getnframes()) == (1, 8000, 16000)
    with pytest.raises(ValueError, match="must leave"):
        foley.buzz([1.9], 2.0, rate=8000)
    with pytest.raises(ValueError, match="length"):
        foley.buzz([0.5], 2.0, rate=8000, length=3.0)


def test_a_sting_plays_its_notes_in_turn_and_a_chime_is_a_different_tune(tmp_path):
    bed = foley.tones([0.5], 2.0, rate=8000, peak=0.7)
    assert len(bed) == 16000 and max(abs(v) for v in bed) == pytest.approx(0.7)
    assert all(v == 0 for v in bed[:4000])
    first, second = bed[4000 : 4000 + int(0.32 * 8000)], bed[4000 + int(0.32 * 8000) : 4000 + int(0.74 * 8000)]
    assert max(map(abs, first)) > 0.3 and max(map(abs, second)) > 0.3 and all(v == 0 for v in bed[4000 + 6000 :])
    chime = foley.tones([0.5], 2.0, foley.CHIME, rate=8000, peak=0.7)
    assert chime != bed and sum(1 for v in chime if v != 0) < sum(1 for v in bed if v != 0)  # shorter notes
    out = foley.write_tones(tmp_path / "sting.wav", [0.5, 1.0], 2.0, rate=8000)
    with wave.open(str(out), "rb") as w:
        assert (w.getnchannels(), w.getframerate(), w.getnframes()) == (1, 8000, 16000)
    with pytest.raises(ValueError, match="must leave"):
        foley.tones([1.5], 2.0, rate=8000)
    with pytest.raises(ValueError, match="notes are"):
        foley.tones([0.5], 2.0, [(10.0, 10.0, 0.1)], rate=8000)


def test_a_burst_is_seeded_levelled_and_lands_on_its_cues():
    sound = foley.Burst(0.05, 2000.0, tone_hz=400.0, tone_end_hz=300.0, tone=0.5)
    a = foley.bursts([0.1, 0.4], 0.6, sound, rate=8000, seed=3)
    assert a == foley.bursts([0.4, 0.1], 0.6, sound, rate=8000, seed=3) and a != foley.bursts(
        [0.1, 0.4], 0.6, sound, rate=8000, seed=4
    )
    assert len(a) == 4800 and max(abs(v) for v in a) == pytest.approx(foley.PEAK)
    assert not any(a[:800]) and any(a[800:840]) and not any(a[1200:3200]) and any(a[3200:3240])


def _brightness(samples):
    """How much of the sound is sample-to-sample change: the higher, the brighter."""
    change = sum(abs(b - a) for a, b in zip(samples, samples[1:], strict=False))
    return change / max(sum(abs(v) for v in samples), 1e-9)


def test_table_sounds_differ_where_the_ear_tells_them_apart():
    bite, chew = (foley.bursts([0.0], 0.5, s, rate=16000) for s in (foley.BITE, foley.CHEW))
    assert _brightness(bite) > 1.5 * _brightness(chew)
    paper = foley.bursts([0.0], 0.5, foley.PAPER_CRUNCH, rate=16000)
    assert _brightness(paper) > _brightness(bite)


def test_a_coin_rings_on_and_a_bite_is_over_at_once():
    assert foley.COIN.tone > 0.5 and foley.COIN.tone_hz > 3000
    assert foley.BITE.seconds <= 0.12
    assert foley.GAS_LIFT.tone == 0.0  # a hiss holds no pitch


def test_a_longer_gas_lift_is_the_same_hiss_held():
    held = dataclasses.replace(foley.GAS_LIFT, seconds=2.4)
    long, short = (foley.bursts([0.0], 3.0, s, rate=8000) for s in (held, foley.GAS_LIFT))
    assert sum(abs(v) for v in long[12000:16000]) > sum(abs(v) for v in short[12000:16000]) == 0.0


def test_a_burst_cut_by_the_end_of_the_bed_stops_there():
    assert len(foley.bursts([0.55], 0.6, foley.SNORE, rate=8000)) == 4800


@pytest.mark.parametrize(
    "sound",
    [
        foley.REMOTE_CLICK,
        foley.SCRAPE,
        foley.SNORE,
        foley.ROAD,
        foley.CHOPPER,
        foley.GULL,
        foley.BITE,
        foley.CHEW,
        foley.PAPER_CRUNCH,
        foley.COIN,
        foley.GAS_LIFT,
        foley.CART_WHEELS,
        foley.PEN,
    ],
)
def test_the_named_sounds_are_sound(sound):
    assert any(foley.bursts([0.0], 0.5, sound, rate=8000))


@pytest.mark.parametrize(
    "kw, match",
    [
        ({"seconds": 0.0, "low_hz": 100.0}, "lasts"),
        ({"seconds": 1.0, "low_hz": 1.0}, "low-pass"),
        ({"seconds": 1.0, "low_hz": 100.0, "attack": 2.0}, "attack"),
        ({"seconds": 1.0, "low_hz": 100.0, "decay": 0.0}, "decay"),
        ({"seconds": 1.0, "low_hz": 100.0, "tone": 2.0}, "tone level"),
        ({"seconds": 1.0, "low_hz": 100.0, "flutter_hz": -1.0}, "flutter"),
    ],
)
def test_a_burst_refuses_numbers_it_cannot_sound(kw, match):
    with pytest.raises(foley.FoleyError, match=match):
        foley.Burst(**kw)


@pytest.mark.parametrize(
    "args, match", [(([2.0], 1.0, foley.KNOCK), "every cue"), (([0.0], 0.0, foley.KNOCK), "every cue")]
)
def test_bursts_refuse_a_cue_the_bed_does_not_hold(args, match):
    with pytest.raises(foley.FoleyError, match=match):
        foley.bursts(*args)


def test_bursts_refuse_a_rate_or_a_peak_out_of_range():
    with pytest.raises(foley.FoleyError, match="rate"):
        foley.bursts([0.0], 1.0, foley.KNOCK, rate=10)
    with pytest.raises(foley.FoleyError, match="peak"):
        foley.bursts([0.0], 1.0, foley.KNOCK, peak=2.0)


def test_write_bursts_writes_a_wav(tmp_path):
    path = foley.write_bursts(tmp_path / "k.wav", [0.0], 0.2, foley.KNOCK, rate=8000)
    with wave.open(str(path)) as w:
        assert w.getframerate() == 8000 and w.getnframes() == 1600


def test_a_name_means_one_sound_a_phones_ding_stays_two_tones_and_the_bell_is_a_burst():
    assert all(len(note) == 3 for note in foley.DING)
    assert isinstance(foley.BELL, foley.Burst)


def test_no_sound_is_exported_twice():
    assert len(foley.__all__) == len(set(foley.__all__))


def test_water_runs_in_its_spans_and_is_silent_outside_them():
    rate = 8000
    bed = foley.water([(0.5, 1.0), (1.5, 2.0)], 2.5, rate=rate, seed=3)
    assert len(bed) == round(2.5 * rate)
    assert max(abs(v) for v in bed[: int(0.5 * rate)]) == 0.0
    assert max(abs(v) for v in bed[int(1.0 * rate) + 1 : int(1.5 * rate)]) == 0.0
    assert max(abs(v) for v in bed[int(0.6 * rate) : int(0.9 * rate)]) > 0.1
    assert bed == foley.water([(0.5, 1.0), (1.5, 2.0)], 2.5, rate=rate, seed=3)


def test_water_stops_dead_when_the_tap_is_turned_off():
    rate = 8000
    bed = foley.water([(0.0, 1.0)], 2.0, rate=rate)
    fade = int(foley.WATER_EDGE * rate)
    assert max(abs(v) for v in bed[int(1.0 * rate) - fade // 2 : int(1.0 * rate)]) < max(
        abs(v) for v in bed[: rate // 2]
    )
    assert all(v == 0.0 for v in bed[int(1.0 * rate) :])


@pytest.mark.parametrize(
    ("spans", "duration", "match"),
    [([], 2.0, "span"), ([(1.0, 0.5)], 2.0, "span"), ([(0.0, 3.0)], 2.0, "span"), ([(0.0, 1.0)], 0, "duration")],
)
def test_water_refuses_spans_it_cannot_lay(spans, duration, match):
    with pytest.raises(foley.FoleyError, match=match):
        foley.water(spans, duration, rate=8000)


def test_write_water_writes_a_wave(tmp_path):
    path = foley.write_water(tmp_path / "water.wav", [(0.0, 0.2)], 0.3, rate=8000)
    with wave.open(str(path)) as w:
        assert w.getframerate() == 8000 and w.getnframes() == 2400
