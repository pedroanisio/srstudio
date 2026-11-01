"""The episode harness every staged series shares (srstudio.series): a style declares its voices, music bed, font
and reel builder once, and each episode is a Reel of takes and staging (ADR 0031)."""

from __future__ import annotations

import dataclasses
import os
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from srstudio import SAGA, VERTICAL, native, series, takes
from srstudio.series import Reel, Series, SeriesError
from srstudio.voice import Voice, VoiceSettings

CALM = VoiceSettings(stability=0.6, similarity_boost=0.75, style=0.2, speed=1.0)
VOICES = {
    "narrator": Voice(role="narrator", id="JBFqnCBsd6RMkjVDRZzb", name="George"),
    "juno": Voice(role="juno", id="SAz9YHcvj6GT2YYXdXww", name="River"),
    "rook": Voice(role="rook", id="CwhRBWXzGAHq8TQ4Fs17", name="Roger"),
}
OUTPUT = {"codec": "h264", "container": "mp4", "fps": "24"}
CALLS: dict = {}


def stage(ep, stages, *, hook, font, look=native.CAPTION_LOOK):
    CALLS["stage"] = dict(ep=ep, stages=stages, hook=hook, font=font, look=look)
    return {"hook": "hook-node", "captions": "captions-node", "mix": "mix-node"}


SERIES = Series(
    style=SAGA,
    voices=VOICES,
    settings={r: CALM for r in VOICES},
    font=("space-grotesk-700.ttf", "space-grotesk.OFL.txt"),
    output=OUTPUT,
    stage=stage,
)


@dataclass(frozen=True)
class DemoReel(Reel):
    series = SERIES


def reel(**kw) -> DemoReel:
    fields = dict(
        slug="demo-reel",
        number="D1",
        title="Demo",
        description="A demo reel.",
        accessible="Two figures talk.",
        takes=(series.line("01", "narrator", "Hello there?"), series.line("02", "juno", "Hi.", 1.2)),
        hook="Hello there?",
        stages=lambda recorded: {"01": "stage-1", "02": "stage-2"},
    )
    return DemoReel(**(fields | kw))


# -- the series -------------------------------------------------------------------------------------------------------
def test_a_series_needs_settings_for_every_voice_and_voices_filed_under_their_role():
    with pytest.raises(SeriesError, match="settings for every voice.*juno"):
        Series(style=SAGA, voices=VOICES, settings={"narrator": CALM, "rook": CALM}, font=SERIES.font,
               output=OUTPUT, stage=stage)  # fmt: skip
    with pytest.raises(SeriesError, match="'lead' holds the voice of 'juno'"):
        Series(style=SAGA, voices={"lead": VOICES["juno"]}, settings={"lead": CALM}, font=SERIES.font,
               output=OUTPUT, stage=stage)  # fmt: skip


def test_a_series_frames_its_episodes_in_the_vertical_safe_area_by_default():
    assert SERIES.safe_area is VERTICAL
    assert (SERIES.seed, SERIES.language, SERIES.bed) == (1028, "en-US", None)


# -- takes ------------------------------------------------------------------------------------------------------------
def test_a_line_and_an_effect_are_takes_and_an_effect_asks_for_no_voices_or_music():
    said = series.line("03", "rook", "Skip it!", 0.2, mood="angry")
    assert said == takes.Take("03", "rook", "Skip it!", 0.2, mood="angry")
    assert said.heard == ()
    boom = series.effect("04", "[BOOM]", "A distant explosion", 1.6, 0.3, peak=0.4)
    assert boom.actor == "sfx" and boom.text == "[BOOM]"
    assert boom.prompt == "A distant explosion, no voices, no music"
    assert (boom.seconds, boom.longest, boom.peak, boom.hold) == (1.6, 1.6, 0.4, 0.3)


def test_a_line_carries_the_hearings_the_operator_accepted():
    said = series.line("09", "juno", "Real is also premium.", 1.2, heard=("Reel is also premium.",))
    assert said == takes.Take("09", "juno", "Real is also premium.", 1.2, mood="calm", heard=("Reel is also premium.",))


def test_word_at_finds_a_words_start_ignoring_case_and_punctuation():
    words = ({"text": "Tonight!", "start": 0.1}, {"text": "“tonight", "start": 0.71234})
    said = SimpleNamespace(id="05", text="Tonight! Tonight works!", words=words)
    assert series.word_at(said, "TONIGHT") == 0.1
    assert series.word_at(said, "tonight", 1) == 0.712
    with pytest.raises(ValueError, match="no word 2 starting with 'tonight'"):
        series.word_at(said, "tonight", 2)


# -- the script -------------------------------------------------------------------------------------------------------
def test_the_script_casts_only_the_voices_its_lines_use_and_credits_them_by_name():
    script = reel().script()
    assert set(script.voices) == {"narrator", "juno"} == set(script.settings)
    assert script.voice_note.startswith("ElevenLabs premade voices River and George; no reference-voice cloning.")
    assert (script.title, script.seed, script.font, script.bed) == ("Demo", 1028, SERIES.font, None)


def test_three_voices_are_credited_as_a_list():
    takes3 = (series.line("01", "narrator", "A?"), series.line("02", "juno", "B."), series.line("03", "rook", "C."))
    assert "voices River, George and Roger;" in reel(takes=takes3).script().voice_note


def test_a_reel_opens_on_its_still_second_only_when_it_asks_for_one():
    assert reel().script().still == 0.0
    assert reel(still=1.0).script().still == 1.0


def test_a_line_for_a_voice_the_series_lacks_is_refused():
    with pytest.raises(SeriesError, match="no voice for 'gary'"):
        reel(takes=(series.line("01", "gary", "Hi."),)).script()


def test_a_reel_outside_a_series_is_refused():
    plain = Reel("s", "1", "t", "d", "a", (series.line("01", "juno", "Hi."),), "Hi?", lambda r: {})
    with pytest.raises(SeriesError, match="belongs to no series"):
        plain.script()


def test_record_runs_the_takes_recording_on_the_script(monkeypatch):
    seen = {}
    monkeypatch.setattr(series.takes, "main", lambda script: seen.setdefault("script", script) and 0)
    assert series.record(reel()) == 0
    assert seen["script"].title == "Demo"


def test_a_reel_can_go_without_its_series_music_bed_and_says_so_in_its_voice_note():
    bed = takes.Bed(SimpleNamespace(), seed=1, bpm=120, gain_db=-16.0, fade=1.0)
    scored = dataclasses.replace(SERIES, bed=bed)

    @dataclass(frozen=True)
    class Scored(Reel):
        series = scored

    fields = {f.name: getattr(reel(), f.name) for f in dataclasses.fields(Reel)}
    assert Scored(**fields).script().bed is bed
    assert "Instrumental music bed" in Scored(**fields).script().voice_note
    bare = Scored(**(fields | {"bed": False})).script()
    assert bare.bed is None
    assert bare.voice_note == "ElevenLabs premade voices River and George; no reference-voice cloning."


def test_a_reel_asks_for_no_bed_with_a_boolean_or_is_refused():
    with pytest.raises(SeriesError, match="bed must be True or False, got None"):
        reel(bed=None)


# -- the build --------------------------------------------------------------------------------------------------------
class FakeEpisode:
    made: list = []

    def __init__(self, spec):
        self.spec = SimpleNamespace(font="assets/font.ttf", given=spec)
        self.takes = ("take-01", "take-02")
        self.hidden = ()
        self.posted = None
        FakeEpisode.made.append(self)

    def hide_on_cover(self, *nodes):
        self.hidden = nodes

    def instagram(self, post):
        self.posted = post

    def finish(self, scene, report, *, private=False):
        self.finished = (scene, report)
        self.private = private
        return scene


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "font.ttf").write_bytes(b"FONT")
    monkeypatch.setattr(series, "Episode", FakeEpisode)
    old = os.umask(0o022)
    yield tmp_path
    os.umask(old)


def test_build_stages_the_recorded_takes_and_finishes_the_scene_in_the_project(project):
    out = series.build(reel(), "unused.py", argv=["demo.py", str(project)])
    ep = FakeEpisode.made[-1]
    spec = ep.spec.given
    assert (spec.slug, spec.number, spec.style, spec.root, spec.seed) == ("demo-reel", "D1", SAGA, project, 1028)
    assert spec.output_options == OUTPUT and spec.safe_area is VERTICAL
    assert spec.accessibility["description"] == "Two figures talk."
    assert CALLS["stage"]["stages"] == {"01": "stage-1", "02": "stage-2"}
    assert (CALLS["stage"]["hook"], CALLS["stage"]["font"]) == ("Hello there?", b"FONT")
    assert CALLS["stage"]["look"] is native.CAPTION_LOOK
    assert ep.hidden == ("hook-node", "captions-node")
    assert ep.posted is None
    assert out == project / "demo-reel.scene.xml"
    assert ep.finished == (out, project / "qa" / "sdk-validation.json")
    assert ep.private
    assert os.umask(0o022) == 0o022


def test_build_failure_keeps_the_callers_umask(project):
    (project / 'assets' / 'font.ttf').unlink()
    with pytest.raises(FileNotFoundError):
        series.build(reel(), 'unused.py', argv=['demo.py', str(project)])
    assert os.umask(0o022) == 0o022


def test_build_passes_the_reels_caption_look_and_its_post(project):
    look = native.CaptionLook(min_last=2)
    series.build(reel(captions=look), "unused.py", posts={"demo-reel": "the-post"}, argv=["demo.py", str(project)])
    assert CALLS["stage"]["look"] is look
    assert FakeEpisode.made[-1].posted == "the-post"


def test_a_reel_asks_for_bleed_and_is_built_without_it_by_default(project):
    series.build(reel(), "unused.py", argv=["demo.py", str(project)])
    assert FakeEpisode.made[-1].spec.given.bleed is False
    series.build(reel(bleed=True), "unused.py", argv=["demo.py", str(project)])
    assert FakeEpisode.made[-1].spec.given.bleed is True


def test_a_reel_can_encode_at_its_own_crf_over_the_series_output(project):
    series.build(reel(crf="21"), "unused.py", argv=["demo.py", str(project)])
    assert FakeEpisode.made[-1].spec.given.output_options == {**OUTPUT, "crf": "21"}
    assert OUTPUT.get("crf") != "21"  # the series' own output is left as it is
    series.build(reel(), "unused.py", argv=["demo.py", str(project)])
    assert FakeEpisode.made[-1].spec.given.output_options == OUTPUT


@pytest.mark.parametrize("crf", ["", "52", "-1", "18.5", "eighteen", 20, None, True])
def test_a_crf_the_encoder_cannot_take_is_refused(crf):
    if crf is None:
        assert reel(crf=None).crf is None  # None: the series' crf
        return
    with pytest.raises(SeriesError, match="crf"):
        reel(crf=crf)


def test_build_without_a_project_argument_builds_beside_the_episode_file(project):
    out = series.build(reel(), str(project / "demo.py"), argv=["demo.py"])
    assert out == project / "demo-reel.scene.xml"


def test_a_series_in_a_silent_style_has_no_caption_font_to_build_with(project, monkeypatch):
    class SilentEpisode(FakeEpisode):
        def __init__(self, spec):
            super().__init__(spec)
            self.spec.font = None

    monkeypatch.setattr(series, "Episode", SilentEpisode)
    with pytest.raises(SeriesError, match="draws no text"):
        series.build(reel(), "unused.py", argv=["demo.py", str(project)])


def test_a_reel_captions_in_its_series_look_unless_it_names_its_own(project):
    tidy = native.CaptionLook(min_last=2)

    @dataclass(frozen=True)
    class TidyReel(Reel):
        series = Series(style=SAGA, voices=VOICES, settings=SERIES.settings, font=SERIES.font, output=OUTPUT,
                        stage=stage, captions=tidy)  # fmt: skip

    plain = reel()
    tidy_reel = TidyReel(**{f: getattr(plain, f) for f in ("slug", "number", "title", "description", "accessible",
                                                           "takes", "hook", "stages")})  # fmt: skip
    assert SERIES.captions is native.CAPTION_LOOK
    assert tidy_reel.look() is tidy
    series.build(tidy_reel, "unused.py", argv=["demo.py", str(project)])
    assert CALLS["stage"]["look"] is tidy
    own = native.CaptionLook(min_last=3)
    assert dataclasses.replace(tidy_reel, captions=own).look() is own
