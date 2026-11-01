"""The Unwritten Rules #2 to #4: each keeps the show's rules, in Will's voice, timed from its takes, with its number."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from srstudio import comedy_floor, host_kit, native, rafa_show, toon

ROOT = Path(__file__).resolve().parents[1]
PILOTS = ROOT / "episodes" / "pilots"
if str(PILOTS) not in sys.path:
    sys.path.insert(0, str(PILOTS))

import unwritten_rules_door_data as door  # noqa: E402
import unwritten_rules_make_yourself_at_home_data as home  # noqa: E402
import unwritten_rules_present_data as present  # noqa: E402

EPISODES = (present, door, home)
SHOWS = [module.SHOW for module in EPISODES]
each = pytest.mark.parametrize("show", SHOWS, ids=[show.slug for show in SHOWS])


@each
def test_each_script_keeps_the_format_and_its_sketch_is_timed_from_the_takes(show):
    show.validate()
    show.validate_sketch()
    assert 20.0 <= show.sketch.end <= 30.0
    assert len(show.kept) == len(show.beats)


def test_the_numbers_run_on_from_the_first_episode():
    assert [show.number for show in SHOWS] == [2, 3, 4]
    for show in SHOWS:
        kicker = f"The Unwritten Rules #{show.number}"
        assert show.title.endswith(kicker) and show.post.thumbnail.kicker == kicker
        assert show.post.description.startswith(kicker)


@each
def test_rafa_speaks_in_the_voice_the_operator_chose(show):
    assert rafa_show.HOST == "rafa"
    assert rafa_show.SPEAKER.voice.id == "bIHbv24MWmeRgasZH58o"
    assert {speaker.name for speaker in show.sketch.speakers} == {rafa_show.HOST}


@each
def test_the_first_statement_is_over_by_three_seconds_and_a_caption_opens_on_frame_one(show):
    assert show.kept[0] <= 3.0
    assert show.starts()[0] == 0.0


@each
def test_every_cue_fits_its_band_and_the_hook_stays_one_cue(show):
    lines = [toon.Line(str(i), beat.line, 0.0, 2.0) for i, beat in enumerate(show.beats)]
    cues = host_kit.caption_cues(lines, skip=(rafa_show.SIGN_OFF,))
    look = host_kit.CAPTION_LOOK
    assert all(len(native.wrap(c.text, look.max_chars, look.max_words)) <= look.max_lines for c in cues)
    assert cues[0].text == show.beats[0].line


def test_one_opening_in_the_stock_is_still():
    assert sorted(show.push[1] for show in SHOWS) == [1.0, 1.05, 1.05]


@each
def test_each_foley_lands_and_no_clip_is_missing(show, tmp_path):
    module = EPISODES[SHOWS.index(show)]
    beats, end = show.sketch.beats, show.sketch.end
    speech = [(b.start, b.start + kept) for b, kept in zip(beats, show.kept, strict=True)]
    rows = module.foley(beats, end, speech, tmp_path, rafa_show.SEED)
    assert {"room", "mug", "buzz", "folder"} <= {row["id"] for row in rows}
    assert all((tmp_path / row["audio"]).is_file() for row in rows)


def test_the_steps_come_nearer_from_faint_to_the_last_frame(tmp_path):
    show = door.SHOW
    beats, end = show.sketch.beats, show.sketch.end
    speech = [(b.start, b.start + kept) for b, kept in zip(beats, show.kept, strict=True)]
    rows = [row for row in door.foley(beats, end, speech, tmp_path, rafa_show.SEED) if row["id"].startswith("step")]
    gains = [row["gain_db"] for row in rows]
    assert gains == sorted(gains) and gains[0] == door.STEP_FROM and gains[-1] == door.STEP_TO
    assert len(door.steps(beats, end)[0]) >= 1


@each
def test_the_notes_clear_the_floor_with_the_comedy_scores(show):
    notes = ROOT / "pilots" / "host" / show.slug / "notes.md"
    assert comedy_floor.notes_shortfall(notes.read_bytes()) == ""


@each
def test_the_caption_on_file_is_the_post(show):
    folder = ROOT / "pilots" / "host" / show.slug
    assert (folder / "ig.txt").read_text(encoding="utf-8") == show.post.text()
    assert (folder / "cover.jpg").is_file()
    assert show.post.title.endswith("?")


@each
def test_the_blurred_room_reaches_the_frame_edge(show):
    assert show.bleed is True


def test_the_show_hands_its_bleed_to_the_staging(monkeypatch, tmp_path):
    seen = []
    monkeypatch.setattr(rafa_show, "build", lambda root, staging, flags: seen.append(staging))
    env = {"SRSTUDIO_ENGINE": "e", "SRSTUDIO_RENDERS": str(tmp_path), "SRSTUDIO_FONTS": str(tmp_path)}
    rafa_show.run(SHOWS[0], ["show", str(tmp_path), "--init"], env)
    assert seen[0].bleed is True
