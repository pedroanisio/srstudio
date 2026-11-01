"""The rig rule: a recurring Stick figure keeps the base rig it was published with (ADR 0069, arc4d3)."""

import dataclasses
import textwrap

import pytest

from srstudio import bible_rig, stick
from srstudio.bible_check import Finding
from srstudio.releases import Release, Tags
from srstudio.social import DeliveryError, InstagramPost

DEV = {"hair": "cowlick", "neck": False}
NOOR = {"hair": "bun", "neck": False}
RED = "#aa0000"
UNDRESSED = {"glasses": False, "tie": None, "apron": None, "cap": None, "sunhat": None}


def look(hair, neck, **clothes):
    return {"hair": hair, "neck": neck, **UNDRESSED, **clothes}


def release(slug="the-reel", *, style="Stick", recurring=(), parts=None):
    return Release(
        slug,
        InstagramPost(title="t", description="d", hashtags=("#a",)),
        tags=Tags("money-services", "other-person", "recognition", recurring=recurring),
        style=style,
        parts=parts,
    )


def builder(scripts, slug, body):
    """A reel's builder: it draws through ``stick.check_look`` as the real ones do through ``stick.rig``."""
    scripts.mkdir(exist_ok=True)
    (scripts / bible_rig.script_of(slug)).write_text("from srstudio import stick\n" + textwrap.dedent(body))


def project(episodes, slug):
    (episodes / slug).mkdir(parents=True)
    (episodes / slug / "marker.txt").write_text("kept")


def test_the_base_rig_and_the_clothes_and_props_partition_every_field_of_a_look():
    fields = {f.name for f in dataclasses.fields(stick.Look)}
    assert set(bible_rig.BASE_RIG) | set(bible_rig.CLOTHES_AND_PROPS) == fields
    assert not set(bible_rig.BASE_RIG) & set(bible_rig.CLOTHES_AND_PROPS)


def test_the_published_base_rigs_are_written_as_data():
    assert bible_rig.PUBLISHED == {"dev": bible_rig.BaseRig("cowlick", False), "noor": bible_rig.BaseRig("bun", False)}


def test_a_look_with_a_recurring_figures_hair_and_a_neck_the_figure_was_not_published_with_is_flagged():
    found = bible_rig.check("r", {"dev", "noor"}, [look("cowlick", True), look("bun", True)])
    assert [f.kind for f in found] == ["rig", "rig"]
    assert (
        "'dev' was published with hair cowlick and neck False; the reel draws cowlick with neck True"
        in found[0].message
    )
    assert "'noor' was published with hair bun and neck False" in found[1].message
    assert "1793513568.110249" in found[0].message
    assert all(isinstance(f, Finding) and f.where == "r" for f in found)


def test_clothes_and_props_change_per_reel_without_a_finding():
    clothed = [look("cowlick", False, glasses=True, tie=RED), look("bun", False, apron=RED, cap=RED, sunhat=RED)]
    assert bible_rig.check("r", {"dev", "noor"}, clothed) == []


def test_a_look_with_other_hair_is_another_person_and_is_left_alone():
    assert bible_rig.check("r", {"dev", "noor"}, [look("spiky", True), look("bald", True)]) == []


def test_only_the_recurring_figures_the_reel_names_are_held_to_their_base_rig():
    assert bible_rig.check("r", {"noor"}, [look("cowlick", True)]) == []
    assert bible_rig.check("r", {"rex", "fern"}, [look("cowlick", True), look("bun", True)]) == []


def test_a_figure_drawn_both_ways_is_flagged_once_for_the_way_that_breaks_the_rule():
    found = bible_rig.check("r", {"dev"}, [look("cowlick", False), look("cowlick", True), look("cowlick", True)])
    assert len(found) == 1


def test_drawn_looks_are_read_from_the_builder_in_a_copy_that_is_removed(tmp_path):
    episodes, scripts, scratch = tmp_path / "episodes", tmp_path / "scripts", tmp_path / "scratch"
    project(episodes, "the-reel")
    builder(
        scripts,
        "the-reel",
        """
        import sys
        from pathlib import Path
        Path(sys.argv[1], "written.txt").write_text("scene")
        stick.check_look(stick.Look(hair="cowlick", neck=True, glasses=True))
        stick.check_look(stick.Look(hair="bun"))
        """,
    )
    looks = bible_rig.drawn_looks("the-reel", scripts, episodes, scratch)
    assert [(x["hair"], x["neck"], x["glasses"]) for x in looks] == [("cowlick", True, True), ("bun", False, False)]
    assert not (episodes / "the-reel" / "written.txt").exists(), "the builder writes in the copy, never the project"
    assert not (scratch / "rig-the-reel").exists()


def test_a_reel_whose_builder_or_project_is_missing_cannot_be_read(tmp_path):
    episodes, scripts, scratch = tmp_path / "episodes", tmp_path / "scripts", tmp_path / "scratch"
    with pytest.raises(bible_rig.RigError, match="no builder at"):
        bible_rig.drawn_looks("the-reel", scripts, episodes, scratch)
    builder(scripts, "the-reel", "stick.check_look(stick.Look())\n")
    with pytest.raises(bible_rig.RigError, match="no project at"):
        bible_rig.drawn_looks("the-reel", scripts, episodes, scratch)


def test_a_builder_that_fails_cannot_be_read_and_is_a_delivery_error(tmp_path):
    episodes, scripts, scratch = tmp_path / "episodes", tmp_path / "scripts", tmp_path / "scratch"
    project(episodes, "the-reel")
    builder(scripts, "the-reel", "raise SystemExit('no cache')\n")
    with pytest.raises(bible_rig.RigError, match="its builder failed") as raised:
        bible_rig.drawn_looks("the-reel", scripts, episodes, scratch)
    assert isinstance(raised.value, DeliveryError)
    assert not (scratch / "rig-the-reel").exists()


def test_a_builder_that_draws_no_figure_is_refused_because_a_rule_that_read_nothing_cannot_fail(tmp_path):
    episodes, scripts, scratch = tmp_path / "episodes", tmp_path / "scripts", tmp_path / "scratch"
    project(episodes, "the-reel")
    builder(scripts, "the-reel", "pass\n")
    with pytest.raises(bible_rig.RigError, match="drew no figure"):
        bible_rig.drawn_looks("the-reel", scripts, episodes, scratch)


def test_a_builder_that_runs_past_the_bound_is_stopped_and_refused(monkeypatch, tmp_path):
    episodes, scripts, scratch = tmp_path / "episodes", tmp_path / "scripts", tmp_path / "scratch"
    project(episodes, "the-reel")
    builder(scripts, "the-reel", "import time\ntime.sleep(60)\n")
    monkeypatch.setattr(bible_rig, "TIMEOUT", 1)
    with pytest.raises(bible_rig.RigError, match="ran past 1 s"):
        bible_rig.drawn_looks("the-reel", scripts, episodes, scratch)


@pytest.mark.parametrize(
    ("printed", "message"),
    [
        ("", "printed 0 look lists"),
        ('print("LOOKS []")\nprint("LOOKS []")', "printed 2 look lists"),
        ('print("LOOKS not-json")', "not JSON"),
        ('print("LOOKS [{\\"hair\\": \\"bun\\"}]")', "not made of the fields"),
        ('print("LOOKS {\\"hair\\": \\"bun\\"}")', "not made of the fields"),
    ],
)
def test_a_look_list_that_is_malformed_or_incomplete_is_refused(monkeypatch, tmp_path, printed, message):
    episodes, scripts, scratch = tmp_path / "episodes", tmp_path / "scripts", tmp_path / "scratch"
    project(episodes, "the-reel")
    builder(scripts, "the-reel", "pass\n")
    monkeypatch.setattr(bible_rig, "HARNESS", printed)
    with pytest.raises(bible_rig.RigError, match=message):
        bible_rig.drawn_looks("the-reel", scripts, episodes, scratch)


def test_a_release_that_does_not_draw_stick_figures_runs_no_builder(tmp_path):
    other = release(style="Cutout", recurring=("dev",))  # no builder exists: running one would raise
    assert bible_rig.check_release(other, tmp_path / "episodes", tmp_path / "scripts", tmp_path / "scratch") == []


def test_a_stick_release_naming_no_recurring_figure_runs_no_builder(tmp_path):
    named = release(recurring=("rex",))
    assert bible_rig.check_release(named, tmp_path / "episodes", tmp_path / "scripts", tmp_path / "scratch") == []


def test_a_release_that_pins_a_rig_part_draws_stick_figures_whatever_its_style_says():
    rig = next(iter(bible_rig.rig_parts()))
    assert bible_rig.draws_stick_figures(release(style="", parts={rig: 1}))
    assert bible_rig.draws_stick_figures(release(style="Stick"))
    assert not bible_rig.draws_stick_figures(release(style="Cutout", parts={}))


def test_a_stick_release_is_held_to_the_looks_its_builder_draws(tmp_path):
    episodes, scripts, scratch = tmp_path / "episodes", tmp_path / "scripts", tmp_path / "scratch"
    project(episodes, "the-reel")
    builder(
        scripts,
        "the-reel",
        """
        stick.check_look(stick.Look(hair="cowlick", glasses=True))
        stick.check_look(stick.Look(hair="bun", neck=True))
        """,
    )
    found = bible_rig.check_release(release(recurring=("dev", "noor")), episodes, scripts, scratch)
    assert [(f.kind, "'noor'" in f.message) for f in found] == [("rig", True)]


def test_a_stick_release_that_keeps_every_base_rig_has_no_finding(tmp_path):
    episodes, scripts, scratch = tmp_path / "episodes", tmp_path / "scripts", tmp_path / "scratch"
    project(episodes, "the-reel")
    builder(
        scripts,
        "the-reel",
        """
        stick.check_look(stick.Look(hair="cowlick", tie="#aa0000"))
        stick.check_look(stick.Look(hair="bun", apron="#aa0000", cap="#aa0000"))
        stick.check_look(stick.Look(hair="spiky", neck=True))
        """,
    )
    assert bible_rig.check_release(release(recurring=("dev", "noor")), episodes, scripts, scratch) == []
