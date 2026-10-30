"""Invalid authoring inputs leave scenes and sample projects ready to retry."""

import json
from pathlib import Path

import pytest
from sr_core.scene import Scene, SchemaValueError

from srstudio import Canvas, Episode, EpisodeSpec, Timeline, graphics, sample
from srstudio.sample import SampleError


@pytest.mark.parametrize("explicit_font", [False, True])
def test_sample_returns_exactly_what_it_writes(tmp_path, project, explicit_font):
    root = tmp_path / "sample"
    font = project / "assets" / "DejaVuSans-Bold.ttf" if explicit_font else None
    result = sample.write_sample_project(root, [sample.Line("manager", "Hello")], font=font)
    assert result["font_real"] is True
    assert json.loads((root / "dialogue.json").read_text()) == result
    assert Timeline.load(root / "dialogue.json").meta["font_real"] is True


def test_a_bad_later_caption_can_be_corrected_without_rebuilding(project):
    ep = Episode(EpisodeSpec(slug="t", title="t", description="t", root=project, seed=1, signature=False))
    before = ep.scene.to_bytes()
    with pytest.raises(SchemaValueError):
        ep.captions([(0, 1, "first", "first"), (1, 2, "second", "bad id")])
    assert ep.scene.to_bytes() == before
    assert ep.caption_specs == []
    ep.captions([(0, 1, "first", "first"), (1, 2, "second", "second")])
    ep.markers()
    assert ep.check() == []


def test_failed_captions_remove_a_new_assets_container_and_allow_retry():
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=3)
    cv = Canvas(scene)
    before = scene.to_bytes()
    with pytest.raises(SchemaValueError):
        graphics.captions(cv, [(0, 1, "first", "first"), (1, 2, "second", "bad id")])
    assert scene.to_bytes() == before
    graphics.captions(cv, [(0, 1, "first", "first")])
    assert len(cv.assets.find_all("text")) == 1


def test_failed_captions_preserve_existing_caption_nodes(project):
    ep = Episode(EpisodeSpec(slug="t", title="t", description="t", root=project, seed=1, signature=False))
    ep.captions([(0, 1, "existing", "existing")])
    before = ep.scene.to_bytes()
    with pytest.raises(SchemaValueError):
        ep.captions([(0, 1, "new", "new"), (1, 2, "bad", "bad id")])
    assert ep.scene.to_bytes() == before


@pytest.mark.parametrize(
    "lines,options,field",
    [
        ([], {}, "lines"),
        ([sample.Line("a", "hi"), sample.Line("b", "bye")], {"angles": ["wide"]}, "angles"),
        ([sample.Line("a", "hi")], {"angles": []}, "angles"),
        ([sample.Line("a", "hi", -1)], {}, "seconds"),
        ([sample.Line("a", "hi", 1, gap=-1)], {}, "gap"),
        ([sample.Line("a", "hi")], {"lead": float("nan")}, "lead"),
        ([sample.Line("a", "hi")], {"tail": 0}, "tail"),
    ],
)
def test_bad_sample_inputs_fail_before_creating_or_changing_files(tmp_path, lines, options, field):
    root = tmp_path / "project"
    root.mkdir()
    sentinel = root / "dialogue.json"
    sentinel.write_text("keep")
    with pytest.raises(SampleError, match=field):
        sample.write_sample_project(root, lines, **options)
    assert sentinel.read_text() == "keep"
    assert list(root.iterdir()) == [sentinel]


@pytest.mark.parametrize("font_name", ["DejaVuSans.ttf", "DejaVuSerif-Bold.ttf", "DejaVuSans-BoldOblique.ttf"])
def test_sample_refuses_wrong_font_identity_before_writing(tmp_path, font_name):
    font = Path("/usr/share/fonts/truetype/dejavu") / font_name
    if not font.is_file():
        pytest.skip(f"font fixture {font_name} is unavailable")
    root = tmp_path / "project"
    with pytest.raises(SampleError, match="DejaVu Sans.*700"):
        sample.write_sample_project(root, [sample.Line("a", "hi")], font=font)
    assert not root.exists()
