"""The Collage sketches as data: each is cast from the Collage cast with the shared voices, staged on known sets,
opens on its hook, holds a silent beat of at least 1.0 s before its button, and lands a zoom and a sting; the shared
build's helpers (timing, prop spans, effects, staging checks) are tested on them (ADR 0026). The Family Photo's group
shot, countdown and flash follow its events, scripted or voiced (ADR 0036)."""

import ast
import importlib
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, collage, collage_sets, flat_counter, releases, sketch
from srstudio.canvas import Signature
from srstudio.collage_group import Lineup
from srstudio.errors import ConsentError

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


def _imports(path: Path, module: str) -> bool:
    return any(isinstance(n, ast.ImportFrom) and n.module == module for n in ast.parse(path.read_text()).body)


# every sketch whose data module stages it with the shared Collage build, found rather than listed
NAMES = tuple(
    sorted(
        p.name.removesuffix("_data.py") for p in EPISODES.glob("*_data.py") if _imports(p, "srstudio.collage_sketch")
    )
)


# the sketches published while the hook was a question; frozen as published, each still opens on one
PUBLISHED = (
    "book_report",
    "brand_refresh",
    "breaking_news",
    "final_broadcast",
    "first_date",
    "goldfish_funeral",
    "gritty_reboot",
    "intervention",
    "the_lore",
    "the_will",
    "therapy_session",
    "thought_leader",
)
HOOK_SECONDS = 2.0  # funny-reels rubric #1, Hook: the premise reads in the first 1-2 s
STILL_ARM = 0.45  # the shortest held first frame of the sp-hook_motion test's arm a
RELEASES = releases.load(EPISODES / "posts")


@pytest.fixture(scope="module")
def mods():
    sys.path.insert(0, str(EPISODES))
    try:
        builder = importlib.import_module("srstudio.collage_sketch")
        return builder, {n: importlib.import_module(f"{n}_data") for n in NAMES}
    finally:
        sys.path.pop(0)


def test_the_collage_sketches_are_found():
    assert len(NAMES) >= 12 and "brand_refresh" in NAMES and "final_broadcast" in NAMES


def test_the_sketches_are_distinct_and_checked(mods):
    builder, data = mods
    slugs = [d.STAGING.sketch.slug for d in data.values()]
    assert len(set(slugs)) == len(NAMES) and all(s == n.replace("_", "-") for s, n in zip(slugs, NAMES, strict=True))
    seeds = [d.STAGING.seed for d in data.values()]
    assert len(set(seeds)) == len(NAMES)
    for d in data.values():
        builder.check_staging(d.STAGING)


@pytest.mark.parametrize("name", NAMES)
def test_each_sketch_has_the_comic_beats(mods, name):
    builder, data = mods
    sk = data[name].STAGING.sketch
    assert 11 <= sk.end <= 35
    assert sketch.events(sk.beats, "zoom") and sketch.events(sk.beats, "sting")
    last_spoken = max(i for i, b in enumerate(sk.beats) if b.line is not None)
    silent = [(b, nxt) for b, nxt in zip(sk.beats, sk.beats[1:], strict=False) if b.line is None and b.caption == ""]
    assert any(nxt.start - b.start >= 1.0 for b, nxt in silent)  # an awkward pause with no caption
    assert sk.beats[last_spoken].line == len(sk.lines) - 1  # the button is the last line


@pytest.mark.parametrize("name", NAMES)
def test_each_sketch_opens_on_its_hook(mods, name):
    _, data = mods
    sk = data[name].STAGING.sketch
    if name in PUBLISHED:
        assert sk.lines[0].text.endswith("?")  # published when the hook was a question by default
        return
    # rubric #1: the hook is an opening chosen for the premise, tagged for analytics, its first beat a spoken line
    # that has landed by HOOK_SECONDS; in the still arm of the sp-hook_motion test, a still shot instead, cut by
    # HOOK_SECONDS to the first line
    tags = RELEASES[sk.slug].tags
    assert tags is not None, f"{sk.slug}: a new release carries its Tags"
    still = tags.test == "sp-hook_motion" and tags.arm == "a"
    assert (data[name].STAGING.still >= STILL_ARM) == still, (
        f"{sk.slug}: a still opening is the still arm's, and only its"
    )
    first, second = sk.beats[0], sk.beats[1]
    assert first.start == 0.0 and first.line == (None if still else 0)
    assert second.start <= HOOK_SECONDS, f"{sk.slug}: the opening beat runs {second.start} s"
    if still:
        assert second.line == 0, f"{sk.slug}: the still shot cuts to the first line"


def test_the_published_sketches_are_still_there():
    assert set(PUBLISHED) <= set(NAMES)


def test_every_character_keeps_one_voice_across_episodes(mods):
    builder, data = mods
    ids = {}
    for d in data.values():
        for s in d.STAGING.sketch.speakers:
            assert s is builder.SPEAKERS[s.name]
            ids.setdefault(s.voice.id, set()).add(s.name)
    assert all(len(names) == 1 for names in ids.values())
    assert set(builder.SPEAKERS) == set(collage.LOOKS) == set(builder.TINTS)


def test_staging_refuses_another_cast_an_unknown_set_or_event(mods):
    builder, data = mods
    st = data["the_lore"].STAGING
    with pytest.raises(builder.StagingError, match="Collage cast"):
        builder.check_staging(replace(st, sketch=replace(st.sketch, cast=sketch.TOON_CAST)))
    with pytest.raises(builder.StagingError, match="no set"):
        builder.check_staging(replace(st, sets={"gary": "living-room"}))
    with pytest.raises(builder.StagingError, match="unknown sets"):
        builder.check_staging(replace(st, sets={"gary": "moon", "kai": "living-room"}))
    beats = list(st.sketch.beats)
    beats[0] = replace(beats[0], event="explode")
    with pytest.raises(builder.StagingError, match="unknown events"):
        builder.check_staging(replace(st, sketch=replace(st.sketch, beats=tuple(beats))))


def test_timed_beats_and_prop_spans(mods):
    builder, _ = mods
    lines = (sketch.Line("gary", "Hi?"), sketch.Line("kai", "No."))
    beats, end = builder.timed(
        lines,
        (
            (1.0, "gary", 0, "open", "flat", "down"),
            (1.5, "kai", "", "half", "flat", "down", "reveal"),
            (1.0, "kai", 1, "half", "flat", "down"),
        ),
        tail=1.0,
    )
    assert [(b.start, b.who, b.line, b.event) for b in beats] == [
        (0.0, "gary", 0, ""),
        (1.0, "kai", None, "reveal"),
        (2.5, "kai", 1, ""),
    ]
    assert end == 3.5
    kai = sketch.appearances(beats, end)[1]
    assert builder.until(beats, "reveal", kai, before=False) == [(1.0, 3.5)]
    assert builder.until(beats, "reveal", kai, before=True) == []
    assert builder.until(beats, "nothing", kai, before=True) == [(1.0, 3.5)]
    assert builder.until(beats, "nothing", kai, before=False) == []
    assert builder.zooms(beats, kai) == []


def test_sound_effects_follow_the_events(mods, tmp_path):
    builder, data = mods
    sk = data["first_date"].STAGING.sketch
    effects = builder.sound_effects(sk.beats, sk.end, tmp_path, 7)
    assert [e["id"] for e in effects] == ["whoosh", "sting", "beep"]
    assert all((tmp_path / e["audio"]).is_file() for e in effects)
    zoom = sketch.events(sk.beats, "zoom")[0][0]
    assert builder.zooms(sk.beats, next(a for a in sketch.appearances(sk.beats, sk.end) if a.start <= zoom < a.end))


def test_recording_needs_consent(mods, tmp_path):
    builder, data = mods
    with pytest.raises(ConsentError, match="SRSTUDIO_ALLOW_CLOUD"):
        builder.record_episode(data["book_report"].STAGING, tmp_path, {}, "ffmpeg", "note")


TILT_MARGIN = 24.0  # a card turned a few degrees reaches this far past its box


@pytest.mark.parametrize("name", NAMES)
def test_no_prop_covers_the_signature_on_its_set(mods, name, monkeypatch):
    builder, data = mods
    st = data[name].STAGING
    placed: list[tuple[str, tuple[float, float, float, float]]] = []

    def record(kind, box):
        placed.append((kind, box))

    monkeypatch.setattr(
        collage_sets, "sign", lambda cv, parent, text, x, y, w, h, **kw: record(text, (x, y, x + w, y + h))
    )
    monkeypatch.setattr(
        collage_sets, "chart", lambda cv, parent, x, y, w, h, values, *a, **kw: record("chart", (x, y, x + w, y + h))
    )
    monkeypatch.setattr(collage_sets, "tv", lambda cv, parent, x, y, w: record("tv", (x, y, x + w, y + w * 0.66)))
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=st.sketch.end, background=collage.PAPER.background)
    cv = Canvas(scene, collage.PAPER, namer=flat_counter("k"), signature=Signature())
    for app in sketch.appearances(st.sketch.beats, st.sketch.end):
        placed.clear()
        g = cv.group(cv.comp, cv.uid("g"))
        st.dress(builder.Shot(cv, app, g, g, st.sketch.beats, st.sketch.end, lambda text, size: 10.0 * len(text)))
        sx0, sy0, sx1, sy1 = collage_sets.signature_box(st.set_of(st.sketch.beats, app))
        for kind, (x0, y0, x1, y1) in placed:
            m = TILT_MARGIN
            clear = x1 + m <= sx0 or x0 - m >= sx1 or y1 + m <= sy0 or y0 - m >= sy1
            assert clear, (name, app.who, kind)


def test_signature_box_names_a_known_set():
    with pytest.raises(collage.CollageError, match="no set"):
        collage_sets.signature_box("moon")


def _retimed(beats, end, k):
    """The beats as a recording might place them: every start and the end stretched by ``k``."""
    return [replace(b, start=round(b.start * k, 6)) for b in beats], round(end * k, 6)


@pytest.mark.parametrize("k", [1.0, 1.15, 1.4])
def test_the_family_photo_stages_its_group_countdown_and_flash_from_its_events(mods, k):
    _, data = mods
    fp = data["the_family_photo"]
    beats, end = _retimed(fp.STAGING.sketch.beats, fp.STAGING.sketch.end, k)
    plan = fp.plan(beats, end)
    timer = sketch.events(beats, "timer")[0][0]
    flash = sketch.events(beats, "flash")[0][0]
    reveal = sketch.events(beats, "reveal")[0][0]
    assert isinstance(plan.lineup, Lineup) and set(plan.lineup.places) == {"gary", "rosa", "kai"}
    for app in sketch.appearances(beats, end):
        group = timer < app.start < reveal and app.who != "kai"
        assert plan.lineup.staged(app) == group, (k, app.who, app.start)  # Kai's close and the ends are singles
    # the countdown starts on the press and ticks evenly to zero on the shutter, from at most ten
    assert plan.start == timer and plan.start + plan.seconds * plan.tick == pytest.approx(flash)
    assert 1 <= plan.seconds <= 10 and 0.5 <= plan.tick <= 2.0
    flushy = next(b.start for b in beats if b.line == 6)
    for name in ("rosa", "kai"):
        laughing = [r for r in plan.lineup.reactions[name] if r["eyes"] == "closed" and r["mouth"] == "grin"]
        assert laughing and laughing[0]["start"] >= flushy  # they crack up at the impression, not before
    assert plan.reveal == reveal


def test_the_family_photo_reveal_shows_the_print_alone(mods):
    _, data = mods
    fp = data["the_family_photo"]
    sk = fp.STAGING.sketch
    cast = fp.STAGING.cast(sk.beats, sk.end)
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=sk.end, background=collage.PAPER.background)
    cv = Canvas(scene, collage.PAPER, namer=flat_counter("k"))
    apps = {a.start: a for a in sketch.appearances(sk.beats, sk.end)}
    cast(cv, cv.comp, apps[fp.plan(sk.beats, sk.end).reveal], {})
    assert scene.to_bytes(layout="pretty").count(b"<shape") == 0  # nobody in front of the print
    cast(cv, cv.comp, apps[0.0], {})
    assert scene.to_bytes(layout="pretty").count(b"<shape") > 0  # the setup shot draws Gary


def test_the_family_photo_zoom_keeps_the_whole_signature_in_frame(mods):
    builder, data = mods
    fp = data["the_family_photo"]
    sk = fp.STAGING.sketch
    cast = fp.STAGING.cast(sk.beats, sk.end)
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=sk.end, background=collage.PAPER.background)
    cv = Canvas(scene, collage.PAPER, namer=flat_counter("k"))
    zoom = sketch.events(sk.beats, "zoom")[0][0]
    app = next(a for a in sketch.appearances(sk.beats, sk.end) if a.start <= zoom < a.end)
    px, py = cast(cv, cv.comp, app, {})
    x0, y0, x1, y1 = collage_sets.signature_box(fp.STAGING.sets[app.who])
    k = builder.ZOOM_SCALE
    # the cactus from its left edge, and the code at the shelf's right end, top to bottom of the box
    corners = [(px + (x - px) * k, py + (y - py) * k) for x in (x0 + fp.CACTUS_LEFT, x1) for y in (y0, y1)]
    assert all(0 <= x <= 1080 and 0 <= y <= 1920 for x, y in corners), corners  # cactus and label both in frame
    fx, _ = collage.face(collage.LOOKS[app.who])
    assert 0 < px + (fx - px) * k <= 720  # the face stays in frame, its headset's far cup clear of the edge


def _small(mods, name="the_lore"):
    return mods[1][name].STAGING


def test_a_staging_can_change_rooms_and_refuses_an_unknown_one(mods):
    builder, _ = mods
    st = _small(mods)
    app = sketch.appearances(st.sketch.beats, st.sketch.end)[0]
    assert st.set_of(st.sketch.beats, app) == st.sets[app.who]
    moved = replace(st, setting=lambda beats, a: "bedroom")
    assert moved.set_of(st.sketch.beats, app) == "bedroom"
    builder.check_staging(moved)
    with pytest.raises(builder.StagingError, match="unknown set"):
        builder.check_staging(replace(st, setting=lambda beats, a: "moon"))


def test_a_hiss_says_for_how_long(mods):
    builder, _ = mods
    st = _small(mods)
    beats = list(st.sketch.beats)
    beats[1] = replace(beats[1], event="hiss:soon")
    with pytest.raises(builder.StagingError, match="hiss"):
        builder.check_staging(replace(st, sketch=replace(st.sketch, beats=tuple(beats))))


def test_the_new_events_write_their_sounds(mods, tmp_path):
    builder, _ = mods
    beats = [
        sketch.Beat(0.0, "gary", "", "open", "flat", "down", event="swat"),
        sketch.Beat(0.5, "gary", "", "open", "flat", "down", event="ding"),
        sketch.Beat(1.0, "gary", "", "open", "flat", "down", event="crunch"),
        sketch.Beat(2.0, "gary", "", "open", "flat", "down", event="hiss:0.5"),
    ]
    effects = builder.sound_effects(beats, 3.0, tmp_path, 7)
    assert [e["id"] for e in effects] == ["swat", "ding", "crunch", "hiss-0"]
    assert all((tmp_path / e["audio"]).is_file() for e in effects)


def test_a_row_can_start_on_a_later_word_of_a_line(mods):
    builder, _ = mods
    lines = (sketch.Line("priya", "Tacos? Sushi?"),)
    beats, _ = builder.timed(
        lines,
        (
            (0.5, "gary", (0, 0, "Tacos?"), "open", "flat", "down"),
            (0.5, "gary", (0, 1, "Sushi?"), "open", "flat", "fist"),
        ),
    )
    assert [(b.word, b.caption) for b in beats] == [(0, "Tacos?"), (1, "Sushi?")]
