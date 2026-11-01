"""The fictional reels on the polished look: visibly parody from the first frame to the last, each with its own
ending and something on screen doing the work, and all of them outside the Okayville publishing path."""

from __future__ import annotations

import importlib
import os
import sys
import wave
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path
from types import ModuleType

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, craft, news_head, news_kit, sketch
from srstudio.news_inked import BANNER_Y
from srstudio.news_kit import TEXT_LEFT, NewsKitError
from srstudio.sketch import Line, SketchError
from srstudio.thumbnail import Thumbnail, _backdrop_placement, covered, layout

ROOT = Path(__file__).resolve().parents[1]
PILOTS = ROOT / "episodes" / "pilots"
if str(PILOTS) not in sys.path:
    sys.path.insert(0, str(PILOTS))

# module, the event that pays the reel off, and what its cover must not give away
REELS = {
    "you_too": ("slip", "happy birthday"),
    "one_more_episode": ("three", "are you"),
    "security_question": ("wrong", "waffles"),
    "where_to_eat": ("board", "cereal"),
    "missing_lid": ("plea", "sock"),
    "came_in_for": ("reason", "away"),
}
BANNER = (
    "ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.",
    "Absence of output verification is a design defect, not a runtime bug.",
    "All LLM output must be treated as untrusted and validated explicitly.",
)
LEGIBLE = 0.9  # a window the engine's strict encode can read, with a frame to spare
HAIR_TOP = 565.0  # the highest hair of any shot on the desk, in px of the frame


def load(name: str) -> ModuleType:
    return importlib.import_module(f"{name}_data")


@pytest.fixture(params=list(REELS))
def pilot(request) -> ModuleType:
    return load(request.param)


def cover(reel: ModuleType) -> Thumbnail:
    assert reel.POST.thumbnail is not None
    return reel.POST.thumbnail


def overlay(reel: ModuleType) -> dict[str, ET.Element]:
    """The groups the reel draws over its picture, by id."""
    sk = reel.SKETCH
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=sk.end, background=news_kit.PLUM_DEEP)
    cv = Canvas(scene, news_kit.NEWS.palette(), font_asset="barlow-condensed")
    reel.overlay(cv, cv.comp, sk.beats, sk.end, lambda text, size: 0.42 * size * len(text))
    root = ET.fromstring(scene.to_bytes(layout="pretty"))
    return {node.get("id", ""): node for node in root.iter()}


def frontmatter(reel: ModuleType) -> dict[str, str]:
    head = (ROOT / "pilots" / "news" / reel.SLUG / "notes.md").read_text(encoding="utf-8").split("---")[1]
    return {k.strip(): v.strip() for k, v in (row.split(":", 1) for row in head.strip().splitlines())}


def wave_of(path: Path) -> list[int]:
    """The samples of a mono 16-bit file, thinned to 8 kHz."""
    with wave.open(str(path), "rb") as w:
        rate, frames = w.getframerate(), w.readframes(w.getnframes())
    samples = [int.from_bytes(frames[i : i + 2], "little", signed=True) for i in range(0, len(frames), 2)]
    return samples[:: rate // 8000]


def words(reel: ModuleType) -> int:
    return sum(len(line.text.split()) for line in reel.LINES)


def test_the_pilot_as_written_is_valid(pilot):
    pilot.validate()


def test_the_parody_tag_is_on_every_frame(pilot):
    tag = overlay(pilot)["news-parody-tag"]
    assert float(tag.get("start", "0")) == 0.0 and float(tag.get("end", "0")) == pilot.SKETCH.end


def test_no_source_card_because_the_kinds_never_mix(pilot):
    assert not [name for name in overlay(pilot) if name.startswith("news-source-card")]


def test_the_banner_runs_from_the_first_frame_to_the_last(pilot):
    banner = overlay(pilot)["news-banner"]
    assert float(banner.get("start", "0")) == 0.0 and float(banner.get("end", "0")) == pilot.SKETCH.end


def test_the_script_fits_the_reel(pilot):
    assert 55 <= words(pilot) <= 70


def test_the_first_picture_speaks(pilot):
    assert pilot.BEATS[0].line == 0 and pilot.BEATS[0].start == 0.0


def test_every_lower_third_stays_up_long_enough_to_read(pilot):
    """All but the last, which runs to the recorded end: the strict encode of the master holds that one."""
    starts = [pilot.BEATS[row[0]].start for row in pilot.LOWERS]
    for start, after in zip(starts, starts[1:], strict=False):
        assert after - start >= LEGIBLE - 1e-9, (pilot.SLUG, start)


@pytest.mark.parametrize("window", range(16))
def test_a_lower_third_names_only_who_is_speaking_or_alone_on_screen(pilot, window):
    """A name under the other anchor's face reads as her name."""
    if window >= len(pilot.LOWERS):
        return
    index, kicker = pilot.LOWERS[window][:2]
    name = next((k for k in ("vera", "gus") if kicker.lower().startswith(k)), None)
    if name is None:
        return
    stop = pilot.LOWERS[window + 1][0] if window + 1 < len(pilot.LOWERS) else len(pilot.BEATS)
    for beat in pilot.BEATS[index:stop]:
        speaking = None if beat.line is None else pilot.LINES[beat.line].speaker
        assert speaking == name or beat.who == name, (kicker, beat.start)


@pytest.mark.parametrize("brand", ["netflix", "tupperware", "uber", "doordash", "google", "apple", "instagram"])
def test_no_real_person_or_brand_is_the_subject(pilot, brand):
    text = " ".join(
        (*(q.text for q in pilot.LINES), *pilot.TICKER, *(str(w) for row in pilot.LOWERS for w in row[1:3]))
    )
    assert brand not in text.lower()


def test_the_cover_does_not_show_the_payoff(pilot):
    event, word = next(v for k, v in REELS.items() if load(k) is pilot)
    assert cover(pilot).at < sketch.events(pilot.BEATS, event)[0][0]
    assert word not in cover(pilot).headline.lower()


def test_the_cover_headline_stays_off_the_heads(pilot):
    episodes = os.environ.get("SRSTUDIO_EPISODES")
    font = Path(episodes or "") / "pilots" / "news" / pilot.SLUG / "assets" / "fonts" / "barlow-condensed-700.ttf"
    if not episodes or not font.exists():
        pytest.skip("needs SRSTUDIO_EPISODES and the project's pinned font")
    assert covered(cover(pilot), font.read_bytes(), 1080, 1920, pilot.FACES) == []


def test_the_keep_clear_boxes_start_at_the_hair(pilot):
    assert all(top <= HAIR_TOP for _, top, _, _ in pilot.FACES)


def test_the_cover_cuts_no_word_of_the_banner(pilot):
    episodes = os.environ.get("SRSTUDIO_EPISODES")
    font = Path(episodes or "") / "pilots" / "news" / pilot.SLUG / "assets" / "fonts" / "barlow-condensed-700.ttf"
    if not episodes or not font.exists():
        pytest.skip("needs SRSTUDIO_EPISODES and the project's pinned font")
    thumb = cover(pilot)
    x, y, zoom = _backdrop_placement(thumb, layout(thumb, font.read_bytes(), 1080, 1920), 1080, 1920)
    assert y + zoom * BANNER_Y >= 1920 or x + zoom * TEXT_LEFT >= 0


def test_the_caption_opens_on_a_question_and_says_parody(pilot):
    post = pilot.POST
    assert post.title.endswith("?") and post.description == "Parody."
    assert 3 <= len(post.hashtags) <= 5
    assert "Matilda" in post.credit and "Charlie" in post.credit


@pytest.mark.parametrize("bad", ["Tag a friend.", "Follow us!", "Link in bio."])
def test_bait_in_a_line_stops_the_build(pilot, bad):
    lines = list(pilot.LINES)
    lines[1] = Line("gus", bad)
    with pytest.raises((NewsKitError, SketchError)):
        pilot.validate(replace(pilot.SKETCH, lines=tuple(lines)))


def test_a_lost_event_stops_the_build(pilot):
    event = pilot.EVENTS[-1]
    beats = tuple(replace(b, event="") if b.event == event else b for b in pilot.BEATS)
    with pytest.raises(SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_an_unknown_event_stops_the_build(pilot):
    event = pilot.EVENTS[-1]
    beats = tuple(replace(b, event="explosion") if b.event == event else b for b in pilot.BEATS)
    with pytest.raises(SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_a_pilot_has_no_release_and_no_post(pilot):
    assert pilot.SLUG not in (ROOT / "episodes" / "instagram_posts.py").read_text(encoding="utf-8")
    assert pilot.OUTPUT.startswith("renders/pilots/") and "/ig" not in pilot.OUTPUT


def test_the_notes_say_what_the_brief_asks(pilot):
    notes = frontmatter(pilot)
    assert notes["pilot"] == pilot.SLUG and notes["type"] == "fictional"
    assert notes["generated-by"] == "claude-opus-5-5 in Claude Code" and notes["main-trigger"]
    assert min(int(notes["comedy-author"]), int(notes["comedy-reviewer"])) >= 14


def test_it_says_it_has_no_sources(pilot):
    assert "fictional, no sources" in (ROOT / "pilots" / "news" / pilot.SLUG / "sources.md").read_text(encoding="utf-8")


def test_the_recording_script_carries_the_banner(pilot):
    text = (PILOTS / f"{pilot.SLUG.replace('-', '_')}_audio.py").read_text(encoding="utf-8")
    assert all(line in text for line in BANNER)


def test_the_headline_is_said_by_three_seconds_in_the_recording(pilot):
    episodes = os.environ.get("SRSTUDIO_EPISODES")
    project = Path(episodes or "") / "pilots" / "news" / pilot.SLUG
    if not episodes or not project.exists():
        pytest.skip("needs SRSTUDIO_EPISODES and the recorded project")
    assert craft.statement(project, pilot.FIRST_STATEMENT).end <= craft.STATEMENT_BY


def test_the_reels_end_differently():
    last = {name: load(name).BEATS[-1] for name in REELS}
    assert last["one_more_episode"].who == load("one_more_episode").BEATS[0].who  # the loop, and no other
    assert last["security_question"].line is None and last["security_question"].who == "gus"
    assert last["where_to_eat"].line is not None
    assert last["you_too"].line is None and last["you_too"].who == "vera"
    assert load("missing_lid").LOWERS[-1][1] == "COMING UP"


def test_the_counter_goes_back_to_0_in_the_silence_after_her_slip():
    reel = load("you_too")
    zero = next(i for i, b in enumerate(reel.BEATS) if b.event == "zero")
    assert reel.BEATS[zero].line is None
    row = next(r for r in reel.LOWERS if r[0] == zero)
    assert row[1:3] == ("DAYS SINCE INCIDENT", "0")
    slip = next(b for b in reel.BEATS if b.event == "slip")
    assert reel.LINES[slip.line].text == "You too." and reel.BEATS[zero].start > slip.start
    assert ("DAYS SINCE INCIDENT", "4,383") in [r[1:3] for r in reel.LOWERS]


def test_the_countdown_ends_on_the_picture_it_started_on():
    reel = load("one_more_episode")
    assert reel.ACTS[-1] == reel.ACTS[0] and reel.BEATS[-1].who == reel.BEATS[0].who
    assert reel.BEATS[-1].event == "loop" and reel.LOWERS[-1][1:3] == reel.LOWERS[0][1:3]
    assert reel.SKETCH.tail >= LEGIBLE - 1e-9 and reel.SKETCH.end - reel.BEATS[-1].start >= 0.2
    counts = [sketch.events(reel.BEATS, name)[0][0] for name in ("three", "two", "one", "loop")]
    assert all(b - a >= LEGIBLE - 0.05 for a, b in zip(counts, counts[1:], strict=False))


def test_security_question_holds_on_gus_with_no_cut_back():
    reel = load("security_question")
    expired = next(i for i, line in enumerate(reel.LINES) if line.text == "Your session has expired.")
    at = next(i for i, b in enumerate(reel.BEATS) if b.line == expired)
    assert {b.who for b in reel.BEATS[at:]} == {"gus"}
    assert reel.LOWERS[-1][1:3] == ("LOCAL FARM", "HAS NO RECORD OF WAFFLES")
    assert "loop" not in reel.EVENTS


def test_the_board_holds_before_cereal_and_the_reel_cuts_on_the_word():
    reel = load("where_to_eat")
    board = sketch.events(reel.BEATS, "board")[0][0]
    call = sketch.events(reel.BEATS, "call")[0][0]
    assert call - board >= 1.2
    assert reel.SKETCH.tail == 0.0 and reel.BEATS[-1].event == "call"
    assert reel.LINES[reel.BEATS[-1].line].text == "Cereal. In a landslide."
    assert "CEREAL" not in reel.LOWERS[-2][2] and reel.LOWERS[-1][2].startswith("CEREAL")


def test_the_flyer_is_only_beside_vera_before_the_plea():
    reel = load("missing_lid")
    plea = sketch.events(reel.BEATS, "plea")[0][0]
    cards = [v for k, v in overlay(reel).items() if k.startswith("news-missing-card") and "start" in v.attrib]
    assert cards
    for card in cards:
        beat = next(b for b in reel.BEATS if b.start == float(card.get("start", "-1")))
        assert beat.who == "vera" and beat.start < plea
    assert all(float(card.get("end", "0")) <= plea for card in cards)


def test_the_answer_snaps_in_on_the_line_that_gives_it_after_a_held_turn():
    reel = load("came_in_for")
    turn = sketch.events(reel.BEATS, "turn")[0][0]
    reason = next(b for b in reel.BEATS if b.event == "reason")
    assert reason.start - turn >= 1.2 and reel.LINES[reason.line].text == "To get away from you."
    row = reel.LOWERS[-1]
    assert reel.BEATS[row[0]] is reason and row[1:] == ("CASE CLOSED", "THE REASON: GUS", False)
    assert not any("GUS" in r[2] for r in reel.LOWERS[:-1])


def test_the_reason_is_on_the_desk_where_a_head_can_turn_and_the_last_line_is_to_camera():
    reel = load("came_in_for")
    who = {b.event: b.who for b in reel.BEATS if b.event}
    assert who["turn"] == who["reason"] == "desk"
    assert who["close"] == "vera" and reel.ACTS[-1].vera.eyes == "level"


def test_gus_says_the_same_word_small_and_only_that_line_is_small():
    reel = load("came_in_for")
    small = [line for line in reel.LINES if line.gain < 0]
    assert [line.text for line in small] == ["Ma'am?"] and small[0].speaker == "gus"
    assert small[0].gain <= -6.02  # under half of the full voice


def test_gus_small_line_keeps_the_gain_its_take_was_recorded_at():
    """ffmpeg gets the gain to four decimals: -9.1186 would move this take a step, -9.11864 does not."""
    reel = load("came_in_for")
    assert reel.SMALL == -9.11864
    assert 10 ** (reel.SMALL / 20) == pytest.approx(0.35, abs=1e-6)


def test_the_live_door_is_beside_vera_and_shuts_only_after_gus_says_it_small():
    reel = load("came_in_for")
    nodes = overlay(reel)
    windows = [v for k, v in nodes.items() if k.startswith("news-live-door-") and k[-1].isdigit()]
    assert windows
    for window in windows:
        beat = next(b for b in reel.BEATS if b.start == float(window.get("start", "-1")))
        assert beat.who == "vera"
    slam = sketch.events(reel.BEATS, "slam")[0][0]
    small = sketch.events(reel.BEATS, "small")[0][0]
    shut = nodes["news-live-door-last-shut"]
    assert slam > small and float(shut.get("start", "0")) == pytest.approx(slam + reel.SLAM)
    assert float(shut.get("end", "0")) == reel.SKETCH.end and reel.BEATS[-1].start > slam + reel.SLAM
    assert "news-live-door-last-shut" in nodes and not [k for k in nodes if k.endswith("-shut") and "last" not in k]


def test_the_door_slam_is_in_the_mix_at_the_instant_the_picture_shuts(tmp_path):
    reel = load("came_in_for")
    effects = reel.foley(reel.BEATS, reel.END, None, tmp_path, reel.SEED)
    assert [e["id"] for e in effects] == ["sting", "whoosh", "tick", "door"]
    door = wave_of(tmp_path / "audio" / "door.wav")
    at = sketch.events(reel.BEATS, "slam")[0][0] + reel.SLAM
    assert max(abs(v) for v in door[: int(at * 8000) - 80]) == 0
    assert max(abs(v) for v in door[int(at * 8000) : int((at + 0.1) * 8000)]) > 0


def test_nothing_about_gus_family_goes_past_what_the_show_has_said():
    reel = load("came_in_for")
    assert not {"wife", "mother", "mom", "kids"} & set(" ".join(q.text.lower() for q in reel.LINES).split())


def test_vera_stays_on_gus_from_the_turn_to_the_close():
    pilot = load("came_in_for")
    starts = {beat.event: beat.start for beat in pilot.BEATS if beat.event}
    assert news_head.holds_of(pilot.ACTS, pilot.BEATS) == (
        news_head.Held("vera", "gus", starts["turn"], starts["close"]),
    )
