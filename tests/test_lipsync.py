"""Lip sync: English spelling read as mouth poses, bilabials that always close, a lead on the sound, short pauses
bridged, and amplitude mouths guided by the line's letters. The old defaults stay sample-for-sample."""

from __future__ import annotations

import math
import random
import re
from dataclasses import replace
from types import SimpleNamespace

import pytest

from srstudio import INK_MOUTH, OFFICE_MOUTH, Soundtrack, Timeline, lipsync, mouth_states, phoneme_states
from srstudio.lipsync import SPEECH_MOUTH, letter_poses
from srstudio.sketch import MOUTH_STYLE as SKETCH_MOUTH
from srstudio.soundtrack import PhonemeStyle


def phones(text, step=0.08, at=0.0):
    return [{"c": c, "start": at + i * step, "end": at + (i + 1) * step} for i, c in enumerate(text)]


def legacy_states(phones, duration, mood="", style=INK_MOUTH):
    """The sampler as it shipped, kept verbatim as the reference the default styles must still match."""
    out = []
    for j in range(math.ceil(duration * style.rate) + 1):
        t = min(duration, j / style.rate)
        ch = next((z["c"].lower() for z in phones if z["start"] <= t < z["end"]), " ")
        pose = "closed"
        if ch.isalpha():
            if mood in style.scream_moods:
                pose = "shout"
            elif ch in style.round_letters:
                pose = "round"
            elif ch in style.open_letters:
                pose = "open" if mood not in style.angry_moods else "shout"
            elif ch in style.closed_letters:
                pose = "closed"
            else:
                pose = "teeth"
        out.append((t, pose))
    return out


def random_take(rng: random.Random):
    """Seeded speech-like timestamps: words of letters, spaces and punctuation, uneven lengths, a gap now and then."""
    out, t = [], rng.uniform(0, 0.2)
    for _ in range(rng.randint(1, 30)):
        c = rng.choice("abcdefghijklmnopqrstuvwxyz      .,!?'ABMOW")
        length = rng.uniform(0.01, 0.2)
        out.append({"c": c, "start": round(t, 4), "end": round(t + length, 4)})
        t += length + (rng.uniform(0, 0.3) if rng.random() < 0.1 else 0)
    return out, t + rng.uniform(0, 0.4)


# -- the shipped defaults ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("style", [INK_MOUTH, SKETCH_MOUTH], ids=["ink", "sketch"])
def test_the_default_styles_still_sample_exactly_as_they_shipped(style):
    rng = random.Random(1028)
    for _ in range(300):
        take, duration = random_take(rng)
        mood = rng.choice(["", "scream", "angry", "calm"])
        assert phoneme_states(take, duration, mood, style) == legacy_states(take, duration, mood, style)


# -- spelling ---------------------------------------------------------------------------------------------------------
def test_spelling_reads_english_letters_as_the_mouth_makes_them():
    poses = dict(zip(["phone", "wow", "come", "the", "light", "queen"], [
        letter_poses(w, SPEECH_MOUTH) for w in ["phone", "wow", "come", "the", "light", "queen"]
    ], strict=True))  # fmt: skip
    assert poses["phone"] == ["teeth", "teeth", "round", "teeth", "teeth"]  # ph is an f; the final e is silent
    assert poses["wow"] == ["round", "round", "round"]
    assert poses["come"] == ["teeth", "round", "closed", "closed"]  # the silent e holds the m
    assert poses["the"] == ["teeth", "teeth", "open"]  # too short for a silent e
    assert poses["light"] == ["teeth", "open", "open", "open", "teeth"]  # gh is silent
    assert poses["queen"][:2] == ["round", "round"]
    assert letter_poses("Hi, you!", SPEECH_MOUTH) == ["open", "open", None, None, "open", "round", "round", None]


def test_without_spelling_letters_keep_their_plain_poses():
    assert letter_poses("phone", INK_MOUTH) == ["closed", "open", "round", "teeth", "open"]
    assert letter_poses("wow", INK_MOUTH) == ["teeth", "round", "teeth"]


# -- timing -----------------------------------------------------------------------------------------------------------
def test_a_bilabial_between_two_samples_still_closes_the_mouth():
    take = [
        {"c": "a", "start": 0.0, "end": 0.1},
        {"c": "m", "start": 0.1, "end": 0.13},  # between the samples at 1/12 and 2/12 s
        {"c": "a", "start": 0.13, "end": 0.4},
    ]
    old = [p for t, p in phoneme_states(take, 0.4, "", INK_MOUTH) if 0 < t < 0.4]
    assert "closed" not in old
    new = [p for t, p in phoneme_states(take, 0.4, "", replace(SPEECH_MOUTH, lead=0.0)) if t < 0.4]
    assert new == ["open", "closed", "open", "open", "open"]  # the closure lands on the sample nearest the m


def test_a_scream_never_closes_on_a_bilabial():
    take = phones("ama", 0.1)
    assert "closed" not in [p for t, p in phoneme_states(take, 0.3, "scream", SPEECH_MOUTH) if t < 0.3]
    assert "closed" in [p for t, p in phoneme_states(take, 0.3, "", SPEECH_MOUTH) if t < 0.3]


def test_the_mouth_leads_the_sound():
    take = [{"c": "a", "start": 0.0, "end": 0.5}, {"c": "o", "start": 0.5, "end": 1.0}]
    plain = dict(phoneme_states(take, 1.0, "", replace(SPEECH_MOUTH, lead=0.0)))
    led = dict(phoneme_states(take, 1.0, "", replace(SPEECH_MOUTH, lead=0.1)))
    assert plain[5 / 12] == "open" and led[5 / 12] == "round"  # 0.417 s looks at 0.517 s
    assert led[1.0] == "closed"


def test_a_short_pause_between_words_keeps_the_mouth_open_and_a_long_one_closes_it():
    short = phones("a", 0.2) + [{"c": " ", "start": 0.2, "end": 0.29}] + phones("a", 0.2, at=0.29)
    long = phones("a", 0.2) + [{"c": " ", "start": 0.2, "end": 0.5}] + phones("a", 0.2, at=0.5)
    style = replace(SPEECH_MOUTH, lead=0.0)
    assert [p for t, p in phoneme_states(short, 0.49, "", style) if t < 0.49] == ["open"] * 6
    assert "closed" in [p for t, p in phoneme_states(long, 0.7, "", style) if t < 0.7]
    gap = phones("a", 0.2) + phones("a", 0.2, at=0.27)  # no phone at all between the words
    assert [p for t, p in phoneme_states(gap, 0.47, "", style) if t < 0.47] == ["open"] * 6


def test_the_take_still_opens_and_ends_closed():
    states = phoneme_states(phones("  ma  ", 0.1), 0.6, "", SPEECH_MOUTH)
    assert states[0] == (0.0, "closed") and states[-1] == (0.6, "closed")


@pytest.mark.parametrize(
    "changes, match",
    [
        (dict(rate=0), "rate"),
        (dict(lead=-0.01), "lead"),
        (dict(lead=float("nan")), "lead"),
        (dict(min_rest=-1.0), "min_rest"),
        (dict(min_rest=float("inf")), "min_rest"),
    ],
)
def test_a_style_that_cannot_sample_is_refused(changes, match):
    with pytest.raises(ValueError, match=match):
        PhonemeStyle(**changes)


# -- amplitude mouths guided by the text -------------------------------------------------------------------------------
def talking(states, t, role):
    spans = t.spans(role)
    return [s for tm, s in states if any(a + 0.05 <= tm < b - 0.05 for a, b in spans)]


def test_letters_choose_round_only_where_the_line_has_round_sounds(project):
    t = Timeline.load(project / "dialogue.json")
    s = Soundtrack(project / "assets" / "dialogue.wav")
    guided = replace(OFFICE_MOUTH, letters=True)

    def with_text(text):
        return replace(t, phrases=[replace(p, text=text) if p.role == "candidate" else p for p in t.phrases])

    flat = talking(mouth_states(s, with_text("Yes, I said that, Steve."), "candidate", style=guided), t, "candidate")
    assert flat and "round" not in flat and {"open", "small"} & set(flat)
    plain = talking(mouth_states(s, with_text("Yes, I said that, Steve."), "candidate"), t, "candidate")
    assert "round" in plain  # the clock-driven rounding rounds a line with no round sound
    rounded = talking(mouth_states(s, with_text("Who? You? Oooh, woo."), "candidate", style=guided), t, "candidate")
    assert rounded.count("round") > len(rounded) / 2
    hum = talking(mouth_states(s, with_text("Mmm, mmm, mmm."), "candidate", style=guided), t, "candidate")
    assert set(hum) == {"rest"}


def test_letters_need_the_phrases_text_not_bare_spans(project):
    t = Timeline.load(project / "dialogue.json")
    s = Soundtrack(project / "assets" / "dialogue.wav")
    with pytest.raises(ValueError, match="letters"):
        mouth_states(s, t, "candidate", style=replace(OFFICE_MOUTH, letters=True), speaking=[(0.0, 1.0)])


def test_the_module_is_exported():
    assert lipsync.SPEECH_MOUTH is SPEECH_MOUTH and SPEECH_MOUTH.spelling and SPEECH_MOUTH.close_bilabials


# -- scoring a lip sync against the takes -----------------------------------------------------------------------------
def test_score_counts_closed_bilabials_snapped_joins_and_changes():
    quick_m = [
        {"c": "a", "start": 0.0, "end": 0.1},
        {"c": "m", "start": 0.1, "end": 0.13},
        {"c": "a", "start": 0.13, "end": 0.4},
    ]
    join = phones("a", 0.2) + [{"c": " ", "start": 0.2, "end": 0.29}] + phones("a", 0.2, at=0.29)
    takes = [(quick_m, 0.4, ""), (join, 0.49, ""), (phones("ama", 0.1), 0.3, "scream")]
    old, new = lipsync.score(takes, INK_MOUTH), lipsync.score(takes, SPEECH_MOUTH)
    assert (old.bilabials, old.closed_bilabials, old.joins, old.snapped_joins) == (1, 0, 1, 1)  # a scream's m: none
    assert (new.closed_bilabials, new.snapped_joins) == (1, 0)
    assert old.seconds == pytest.approx(1.19) and old.changes_per_second > 0
    assert "1/1 bilabials closed" in new.summary() and "0/1 word joins snapped shut" in new.summary()
    with pytest.raises(ValueError, match="takes"):
        lipsync.score([], SPEECH_MOUTH)


def test_the_command_scores_the_takes_of_timelines_with_both_mouths(tmp_path, capsys):
    import json

    from srstudio import cli
    from support.ink_layout import takes_data

    path = tmp_path / "timeline.json"
    path.write_text(json.dumps(takes_data()))
    assert cli.main(["lipsync", str(path)]) == 0
    printed = capsys.readouterr().out
    assert "INK_MOUTH" in printed and "SPEECH_MOUTH" in printed and "bilabials closed" in printed
    assert cli.main(["lipsync", str(tmp_path / "missing.json")]) == 2


def test_a_toon_sketch_can_record_its_visemes_with_the_speech_mouth():
    from srstudio import sketch
    from srstudio.voice import Alignment

    quick_m = Alignment(("a", "m", "a"), (0.0, 0.1, 0.13), (0.1, 0.13, 0.4))
    shipped = [v for _, v in sketch.visemes(quick_m, 1.0, 0.0, 0.4)]
    assert shipped == ["open", "closed"]  # the m falls between samples: one open run, then the end
    speech = [v for _, v in sketch.visemes(quick_m, 1.0, 0.0, 0.4, style=SPEECH_MOUTH)]
    assert speech == ["open", "closed", "open", "closed"]


# -- talk and state tracks (shared by Saga and Gloss) -----------------------------------------------------------------
class StyleError(ValueError):
    pass


def spoken(text: str = "open your mouth", duration: float = 1.5):
    phones = tuple(
        {"c": c, "start": round(0.1 + i * 0.07, 3), "end": round(0.17 + i * 0.07, 3)} for i, c in enumerate(text)
    )
    return SimpleNamespace(phones=phones, duration=duration, mood="", is_effect=False)


def test_talk_is_one_state_per_change_of_viseme_ending_closed_within_the_take():
    states = lipsync.talk(spoken(), SPEECH_MOUTH)
    assert states[0][0] == 0 and states[-1][1] == "closed" and states[-1][0] <= 1.5
    assert all(b[0] > a[0] and b[1] != a[1] for a, b in zip(states, states[1:], strict=False))
    assert {p for _, p in states} <= set(lipsync.VISEMES) and {"open", "round"} <= {p for _, p in states}


def test_an_effect_or_a_take_without_timestamps_says_nothing():
    assert lipsync.talk(SimpleNamespace(phones=spoken().phones, is_effect=True), SPEECH_MOUTH) == []
    assert lipsync.talk(SimpleNamespace(phones=(), duration=1.0, mood=""), SPEECH_MOUTH) == []


def check(track, end: float = math.inf, names=lipsync.VISEMES) -> None:
    lipsync.check_track(
        track,
        names,
        StyleError,
        rising=lambda i, t, last: f"state {i}: {t!r} after {last}",
        unknown=lambda i, state: f"state {i}: {state!r} unknown",
        end=end,
        outside=lambda i, t: f"state {i}: {t} outside",
    )


def test_a_track_rises_strictly_from_zero_in_known_states():
    check([(0, "closed"), (0.25, "open"), (1, "closed")])


@pytest.mark.parametrize(
    ("track", "message"),
    [
        ([(0.5, "open"), (0.2, "closed")], "state 1: 0.2 after 0.5"),
        ([(0.5, "open"), (0.5, "closed")], "state 1: 0.5 after 0.5"),
        ([(-1, "open")], "state 0: -1 after -1.0"),
        ([(True, "open")], "state 0: True after -1.0"),
        ([(math.nan, "open")], "state 0: nan after -1.0"),
        ([(math.inf, "open")], "state 0: inf after -1.0"),
        ([("0", "open")], "state 0: '0' after -1.0"),
        ([(0, "grin")], "state 0: 'grin' unknown"),
    ],
)
def test_a_track_out_of_order_non_numeric_or_unknown_is_refused_in_the_callers_words(track, message):
    with pytest.raises(StyleError, match=f"^{re.escape(message)}$"):
        check(track)


def test_a_track_with_an_end_keeps_its_states_before_it():
    check([(0, "open")], end=1.0)
    with pytest.raises(StyleError, match="^state 1: 1.0 outside$"):
        check([(0, "open"), (1.0, "closed")], end=1.0)


def test_a_track_with_an_end_and_no_outside_message_says_where_it_ends():
    with pytest.raises(StyleError, match="^state 0: second 2 must fall before 1.0$"):
        lipsync.check_track(
            [(2, "open")], lipsync.VISEMES, StyleError, rising=lambda *_: "", unknown=lambda *_: "", end=1.0
        )


def test_a_take_cut_mid_word_closes_the_mouth_at_its_end():
    states = lipsync.talk(spoken("aaaaaaaaaaaaaaaaaaaa", duration=1.0), SPEECH_MOUTH)
    assert states[-1] == (1.0, "closed") and states[-2][1] != "closed"
