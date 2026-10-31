"""The pilot's script is checked, every claim is one the sources allow, and it stays outside the publishing path."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from srstudio import mind_kit, sketch, toon_parlour
from srstudio.sketch import Line
from support.toon_props import canvas

ROOT = Path(__file__).resolve().parents[1]
PILOTS = ROOT / "episodes" / "pilots"
if str(PILOTS) not in sys.path:
    sys.path.insert(0, str(PILOTS))

import choice_blindness_data as pilot  # noqa: E402

SCRIPTED = {name: sketch.events(pilot.SKETCH.beats, name)[0][0] for name in pilot.EVENTS}


def words() -> str:
    """Everything the reel says or shows, and its caption."""
    return " ".join(
        (
            *(q.text for q in pilot.LINES),
            *pilot.STAMP,
            pilot.NAME,
            pilot.POST.title,
            pilot.POST.description,
            pilot.POST.thumbnail.headline,
            pilot.POST.thumbnail.kicker,
        )
    )


def with_lines(*changes: tuple[int, str]) -> sketch.Sketch:
    lines = list(pilot.LINES)
    for index, text in changes:
        lines[index] = replace(lines[index], text=text)
    return replace(pilot.SKETCH, lines=tuple(lines))


def test_the_pilot_as_written_is_valid():
    pilot.validate()


def test_the_hook_is_the_supported_wording_and_it_opens_the_reel():
    assert pilot.HOOK == "Most people will explain a choice they never made."
    assert pilot.LINES[0].text == pilot.HOOK and pilot.LINES[0].speaker == "narrator"
    assert pilot.BEATS[0].start == 0.0 and pilot.BEATS[0].line == 0


def test_the_stamp_is_the_decided_wording_and_counts_swaps():
    assert " ".join(pilot.STAMP[:2]) == "Only 13% of swaps spotted at the time."
    assert pilot.STAMP[2] == "Johansson et al., 2005"


def test_the_spoken_figure_is_the_stamps():
    assert "thirteen percent of swaps" in pilot.SAID


@pytest.mark.parametrize(
    "claim",
    [
        "defend",
        "87%",
        "87 percent",
        "of people",
        "johansson & hall",
        "johansson and hall",
        "vote",
        "election",
        "politic",
        "lying",
        "liar",
        "lie ",
    ],
)
def test_a_reel_never_says_what_the_sources_warn_against(claim):
    assert claim not in words().lower().replace("most people", "")


def test_a_number_is_only_ever_about_swaps():
    for line in pilot.LINES:
        digits = any(c.isdigit() for c in line.text) or "percent" in line.text
        assert not digits or "swaps" in line.text


def test_the_turn_says_may():
    assert " ".join(pilot.TURN) == "When we explain a choice, we may be building the reason, not remembering it."


def test_the_caption_keeps_the_scope_and_the_short_source():
    assert "Simple choices, in experiments" in pilot.POST.description
    assert "Source: Johansson et al. (2005), Science" in pilot.POST.description


def test_the_sketch_carries_no_second_figure():
    reasons = [q.text for q in pilot.LINES if q.speaker == "goat"]
    assert not any(c.isdigit() for text in reasons for c in text)
    assert "typical" not in words().lower()


def test_nobody_in_the_sketch_challenges_him_past_asking_why():
    asked = [q.text for q in pilot.LINES if q.speaker == "fox"]
    assert asked == ["Why mint?", "Why toothpaste?"]


def test_the_last_reason_is_the_last_thing_said():
    assert pilot.LINES[-1].text == pilot.LAST == "Vanilla has never once protected my enamel."


def test_the_stamps_words_are_not_captioned_twice():
    stamp, sneak = (next(b for b in pilot.BEATS if b.event == e) for e in ("stamp", "sneak"))
    assert stamp.caption == "" and sneak.caption == ""


def test_the_swap_lands_while_the_stamp_is_still_being_said():
    sneak = next(b for b in pilot.BEATS if b.event == "sneak")
    assert sneak.line == 4 and sneak.word > 0


def test_the_stamp_is_gone_when_he_tastes_the_toothpaste(monkeypatch):
    """The stamp sits across the tube, so it must not outstay the moment the tube pays off."""
    cv = canvas()
    ends = []
    group = cv.group

    def recording(parent, name, **kw):
        ends.append(kw.get("end"))
        return group(parent, name, **kw)

    monkeypatch.setattr(cv, "group", recording)
    pilot._stamp(SimpleNamespace(cv=cv, front=cv.comp), SCRIPTED)
    assert SCRIPTED["sneak"] < ends[0] <= SCRIPTED["tasted"]


def test_the_fox_leaves_with_the_mint_she_took(monkeypatch):
    seen = []
    monkeypatch.setattr(toon_parlour, "cone", lambda cv, g, at, flavour: seen.append(flavour))
    monkeypatch.setattr(toon_parlour, "toothpaste_cone", lambda cv, g, at: seen.append("toothpaste"))
    cv = canvas()
    app = SimpleNamespace(who="goat", start=0.0, end=pilot.END)
    pilot._sneak(SimpleNamespace(cv=cv, app=app, front=cv.comp), SCRIPTED)
    assert seen == ["toothpaste", "mint"]


def test_a_shot_that_ends_before_the_swap_finishes_draws_no_arm(monkeypatch):
    seen = []
    monkeypatch.setattr(toon_parlour, "cone", lambda *a: seen.append(a))
    cv = canvas()
    app = SimpleNamespace(who="goat", start=0.0, end=SCRIPTED["sneak"])
    pilot._sneak(SimpleNamespace(cv=cv, app=app, front=cv.comp), SCRIPTED)
    assert not seen


def test_a_hold_of_at_least_one_and_a_fifth_seconds_comes_before_the_last_line():
    assert SCRIPTED["last"] - SCRIPTED["blink"] >= 1.2


@pytest.mark.parametrize("bad", ["Science proves it.", "This is your OCD talking.", "Tag someone who does this."])
def test_a_line_the_channel_keeps_off_screen_stops_the_build(bad):
    with pytest.raises(mind_kit.MindKitError):
        pilot.validate(with_lines((9, bad)))


def test_a_lost_event_stops_the_build():
    beats = tuple(replace(b, event="") if b.event == "last" else b for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_an_unknown_event_stops_the_build():
    beats = tuple(replace(b, event="bonus") if b.event == "named" else b for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_events_out_of_order_stop_the_build():
    swap = {"years": "blink", "blink": "years"}
    beats = tuple(replace(b, event=swap.get(b.event, b.event)) for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError, match="the events run"):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_a_reel_that_does_not_open_on_the_claim_stops_the_build():
    beats = (replace(pilot.BEATS[0], line=None, word=None, caption=""), *pilot.BEATS[1:])
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_the_reel_is_a_short_one():
    assert 20.0 <= pilot.END <= 30.0


def test_a_pilot_has_no_release_and_no_post():
    posts = (ROOT / "episodes" / "instagram_posts.py").read_text(encoding="utf-8")
    assert pilot.SLUG not in posts
    assert not list((ROOT / "episodes" / "posts").rglob(f"*{pilot.SLUG.replace('-', '_')}*"))
    assert pilot.OUTPUT.startswith("renders/pilots/") and "/ig" not in pilot.OUTPUT


def test_no_hearing_was_written():
    assert all(isinstance(q, Line) and not q.heard for q in pilot.LINES)


def test_the_cast_is_two_approved_rigged_characters():
    assert pilot.VERSIONS == {"toon-goat": 1, "toon-fox": 2}
    assert set(pilot.HEADS) == {"goat", "fox"}


def test_the_recording_carries_the_banner():
    text = (PILOTS / "choice_blindness_audio.py").read_text(encoding="utf-8")
    assert "ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error." in text
    assert "Absence of output verification is a design defect, not a runtime bug." in text
    assert "All LLM output must be treated as untrusted and validated explicitly." in text
