"""The rig rule: a recurring Stick figure keeps the base rig it was published with (ADR 0069, arc4d3)."""

import dataclasses
import json
import textwrap

import pytest

from srstudio import bible, bible_rig, stick
from srstudio.bible_check import Finding
from srstudio.bible_rig import BaseRig, Drawn
from srstudio.releases import Release, Tags
from srstudio.social import DeliveryError, InstagramPost

DEV = BaseRig("cowlick", False, False)
NOOR = BaseRig("bun", True, False)
GARY = BaseRig("spiky", False, False)
BALD = BaseRig("bald", True, False)
SPOKEN = [{"c": "h", "start": 0.0, "end": 0.1}, {"c": "i", "start": 0.1, "end": 0.2}]
TIMELINE = {
    "duration": 2.0,
    "items": [
        {"actor": "dev", "phones": SPOKEN, "speech_duration": 0.2},
        {"actor": "gary", "phones": [], "speech_duration": 1.25},
    ],
}


PREAMBLE = """
from sr_core.scene import Scene
from srstudio import DAYLIGHT, Canvas, flat_counter, stick, stick_door, stick_flat
scene = Scene(version="auto")
scene.add_project(width=1080, height=1920, fps="24", duration=6.0, background="#d9d2c4")
cv = Canvas(scene, DAYLIGHT, font_asset="inter", namer=flat_counter("n"))
root = cv.comp
"""


def release(slug="the-reel", *, style="Stick", recurring=(), parts=None):
    return Release(
        slug,
        InstagramPost(title="t", description="d", hashtags=("#a",)),
        tags=Tags("money-services", "other-person", "recognition", recurring=recurring),
        style=style,
        parts=parts,
    )


def builder(scripts, slug, body):
    """A reel's builder: it draws through the real ``stick.rig``, or checks a look as an extra's drawing does."""
    scripts.mkdir(exist_ok=True)
    (scripts / bible_rig.script_of(slug)).write_text(PREAMBLE + textwrap.dedent(body))


def project(episodes, slug, timeline=TIMELINE):
    (episodes / slug).mkdir(parents=True)
    (episodes / slug / "marker.txt").write_text("kept")
    if timeline is not None:
        (episodes / slug / "timeline.json").write_text(json.dumps(timeline))


def test_the_base_rig_and_the_clothes_and_props_partition_every_field_of_a_look():
    fields = {f.name for f in dataclasses.fields(stick.Look)}
    assert set(bible_rig.BASE_RIG) | set(bible_rig.CLOTHES_AND_PROPS) == fields
    assert not set(bible_rig.BASE_RIG) & set(bible_rig.CLOTHES_AND_PROPS)
    assert bible_rig.BASE_RIG == tuple(f.name for f in dataclasses.fields(BaseRig))


def test_the_published_base_rigs_are_written_as_data():
    assert bible_rig.PUBLISHED == {"dev": DEV, "gary": GARY, "noor": NOOR}


def test_every_recurring_stick_figure_of_the_bible_has_a_published_base_rig():
    """A figure drawn by the shared rig on two reels has to be placed here, or the rule says nothing about them."""
    library = bible.load(bible_rig.REPO / "bible")
    recurring = {c.name.lower() for c in library.characters if {d.part for d in c.look.drawing} & bible_rig.rig_parts()}
    assert recurring == set(bible_rig.PUBLISHED)


def test_the_rule_quotes_arc4d3_and_cites_the_message():
    assert bible_rig.RULING == (
        "a recurring figure's base rig stays as published, and only clothes and props change per reel."
    )
    assert "1793513568.110249" in bible_rig.RULE


def test_a_recurring_figure_drawn_speaking_with_new_hair_is_flagged():
    found = bible_rig.check("r", {"dev"}, [Drawn("dev", DEV), Drawn("dev", BaseRig("bald", False, False))])
    assert [f.kind for f in found] == ["rig"]
    assert "'dev' was published with hair cowlick, glasses False, neck False" in found[0].message
    assert "the reel draws them with hair bald, glasses False, neck False" in found[0].message
    assert "1793513568.110249" in found[0].message
    assert all(isinstance(f, Finding) and f.where == "r" for f in found)


@pytest.mark.parametrize(
    ("name", "drawn"),
    [
        ("dev", BaseRig("cowlick", True, False)),
        ("dev", BaseRig("cowlick", False, True)),
        ("noor", BaseRig("bun", False, False)),
        ("noor", BaseRig("bun", True, True)),
        ("gary", BaseRig("side-part", False, False)),
    ],
)
def test_every_field_of_the_base_rig_counts_on_a_figure_who_speaks(name, drawn):
    assert [f.kind for f in bible_rig.check("r", {name}, [Drawn(name, bible_rig.PUBLISHED[name]), Drawn(name, drawn)])]


def test_a_look_no_one_speaks_from_counts_only_for_a_neck_on_a_recurring_figures_hair():
    """A nameless extra may recombine hair and glasses; the neck is the base rig arc4d3 ruled off for the figures."""
    found = bible_rig.check(
        "r", {"dev", "noor"}, [Drawn("", DEV), Drawn("", NOOR), Drawn("", BaseRig("bun", True, True))]
    )
    assert ["'noor'" in f.message for f in found] == [True]
    assert bible_rig.check("r", {"dev"}, [Drawn("", DEV), Drawn("", BaseRig("cowlick", True, False))]) == []
    assert bible_rig.check("r", {"dev"}, [Drawn("", DEV), Drawn("", BaseRig("spiky", False, True))]) == []


def test_a_figure_the_reel_names_and_no_one_is_drawn_as_is_flagged():
    found = bible_rig.check("r", {"noor"}, [Drawn("", DEV), Drawn("", BaseRig("bun", False, False))])
    assert "'noor' is named in the reel and no figure is drawn with the base rig" in found[0].message


def test_one_broken_figure_is_one_finding_and_says_the_ruling():
    found = bible_rig.check("r", {"dev"}, [Drawn("dev", BaseRig("cowlick", False, True))])
    assert len(found) == 1
    assert bible_rig.RULING in found[0].message
    assert "Clothes and props are tie, apron, cap, sunhat, brows." in found[0].message


def test_clothes_and_props_change_per_reel_without_a_finding(tmp_path):
    episodes, scripts = tmp_path / "episodes", tmp_path / "scripts"
    project(episodes, "the-reel")
    builder(
        scripts,
        "the-reel",
        """
        stick.check_look(stick.Look(tie="#aa0000", apron="#aa0000", cap="#aa0000", sunhat="#aa0000"))
        stick.check_look(stick.Look(hair="bun", glasses=True, apron="#aa0000", cap="#aa0000", brows=False))
        """,
    )
    assert bible_rig.check_release(release(recurring=("dev", "noor")), episodes, scripts) == []


def test_only_the_recurring_figures_the_reel_names_are_held_to_their_base_rig():
    assert bible_rig.check("r", {"noor"}, [Drawn("", NOOR), Drawn("", BaseRig("cowlick", False, True))]) == []
    assert bible_rig.check("r", {"rex", "fern"}, [Drawn("rex", BALD)]) == []


def test_a_figure_drawn_both_ways_is_flagged_once_for_the_way_that_breaks_the_rule():
    assert len(bible_rig.check("r", {"dev"}, [Drawn("dev", DEV), Drawn("dev", BALD), Drawn("dev", BALD)])) == 1


def test_a_speaking_figure_is_named_by_the_take_whose_phones_its_mouth_is_given(tmp_path):
    episodes, scripts = tmp_path / "episodes", tmp_path / "scripts"
    project(episodes, "the-reel")
    builder(
        scripts,
        "the-reel",
        """
        import json, sys
        from pathlib import Path
        phones = tuple(json.loads(Path(sys.argv[1], "timeline.json").read_text())["items"][0]["phones"])
        keys = [stick.RigKey(0.0, next(iter(stick.SEATED)))]
        stick.rig(cv, root, keys, 1.0, look=stick.Look(hair="bald"), phones=phones)
        stick.rig(cv, root, keys, 1.0, look=stick.Look(hair="bun"))
        """,
    )
    drawn = bible_rig.drawn_looks("the-reel", scripts, episodes)
    assert drawn == [Drawn("dev", BaseRig("bald", False, False)), Drawn("", BaseRig("bun", False, False))]


def test_a_sleeper_who_talks_is_named_by_the_take_as_long_as_the_talk(tmp_path):
    episodes, scripts = tmp_path / "episodes", tmp_path / "scripts"
    project(episodes, "the-reel")
    builder(
        scripts,
        "the-reel",
        """
        stick_flat.murphy_bed(cv, root, 2.0, drop_at=0.0, sleeper=stick.Look(hair="bald"), talk=((0.0, 1.25),))
        stick_flat.murphy_bed(cv, root, 2.0, drop_at=0.0, sleeper=stick.Look(hair="bun"))
        """,
    )
    drawn = bible_rig.drawn_looks("the-reel", scripts, episodes)
    assert drawn == [Drawn("gary", BaseRig("bald", False, False)), Drawn("", BaseRig("bun", False, False))]


def test_a_bed_imported_by_name_is_observed_too(tmp_path):
    episodes, scripts = tmp_path / "episodes", tmp_path / "scripts"
    project(episodes, "the-reel")
    builder(
        scripts,
        "the-reel",
        """
        from srstudio.stick_flat import murphy_bed
        murphy_bed(cv, root, 2.0, drop_at=0.0, sleeper=stick.Look(hair="bald"), talk=((0.0, 1.25),))
        """,
    )
    assert bible_rig.drawn_looks("the-reel", scripts, episodes) == [Drawn("gary", BaseRig("bald", False, False))]


def test_a_tile_is_named_by_the_name_it_carries(tmp_path):
    episodes, scripts = tmp_path / "episodes", tmp_path / "scripts"
    project(episodes, "the-reel")
    builder(scripts, "the-reel", 'stick.Tile("Noor", stick.Look(hair="bald"))\n')
    assert bible_rig.drawn_looks("the-reel", scripts, episodes) == [Drawn("noor", BaseRig("bald", False, False))]


def test_phones_two_speakers_share_name_neither_of_them(tmp_path):
    episodes, scripts = tmp_path / "episodes", tmp_path / "scripts"
    both = {"duration": 2.0, "items": [{"actor": "dev", "phones": SPOKEN}, {"actor": "noor", "phones": SPOKEN}]}
    project(episodes, "the-reel", both)
    builder(
        scripts,
        "the-reel",
        f"""
        stick.rig(cv, root, [stick.RigKey(0.0, next(iter(stick.SEATED)))], 1.0, phones=tuple({SPOKEN!r}))
        """,
    )
    assert bible_rig.drawn_looks("the-reel", scripts, episodes) == [Drawn("", DEV)]


def test_a_rig_imported_by_name_is_observed_too(tmp_path):
    """stick_door takes ``rig`` by name: a figure drawn through it speaks like any other."""
    episodes, scripts = tmp_path / "episodes", tmp_path / "scripts"
    project(episodes, "the-reel")
    builder(
        scripts,
        "the-reel",
        f"""
        stick_door.jogger(cv, root, 1.0, look=stick.Look(hair="bald"), face=stick.Face(), phones=tuple({SPOKEN!r}))
        """,
    )
    assert {d for d in bible_rig.drawn_looks("the-reel", scripts, episodes)} == {
        Drawn("dev", BaseRig("bald", False, False))
    }


def test_drawn_looks_are_read_from_the_builder_in_a_copy_that_is_removed(tmp_path):
    episodes, scripts = tmp_path / "episodes", tmp_path / "scripts"
    project(episodes, "the-reel")
    builder(
        scripts,
        "the-reel",
        """
        import sys
        from pathlib import Path
        Path(sys.argv[1], "written.txt").write_text("scene")
        print(Path(sys.argv[1]))
        stick.check_look(stick.Look(hair="cowlick", neck=True, glasses=True))
        stick.check_look(stick.Look(hair="bun"))
        """,
    )
    assert bible_rig.drawn_looks("the-reel", scripts, episodes) == [
        Drawn("", BaseRig("cowlick", True, True)),
        Drawn("", BaseRig("bun", False, False)),
    ]
    assert not (episodes / "the-reel" / "written.txt").exists(), "the builder writes in the copy, never the project"
    assert sorted(p.name for p in (episodes / "the-reel").iterdir()) == ["marker.txt", "timeline.json"]


def test_a_reel_whose_builder_or_project_is_missing_cannot_be_read(tmp_path):
    episodes, scripts = tmp_path / "episodes", tmp_path / "scripts"
    with pytest.raises(bible_rig.RigError, match="no builder at"):
        bible_rig.drawn_looks("the-reel", scripts, episodes)
    builder(scripts, "the-reel", "stick.check_look(stick.Look())\n")
    with pytest.raises(bible_rig.RigError, match="no project at"):
        bible_rig.drawn_looks("the-reel", scripts, episodes)


def test_a_builder_that_fails_cannot_be_read_and_is_a_delivery_error(tmp_path):
    episodes, scripts = tmp_path / "episodes", tmp_path / "scripts"
    project(episodes, "the-reel")
    builder(scripts, "the-reel", "raise SystemExit('no cache')\n")
    with pytest.raises(bible_rig.RigError, match="its builder failed") as raised:
        bible_rig.drawn_looks("the-reel", scripts, episodes)
    assert isinstance(raised.value, DeliveryError)


def test_a_builder_that_draws_no_figure_is_refused_because_a_rule_that_read_nothing_cannot_fail(tmp_path):
    episodes, scripts = tmp_path / "episodes", tmp_path / "scripts"
    project(episodes, "the-reel")
    builder(scripts, "the-reel", "pass\n")
    with pytest.raises(bible_rig.RigError, match="drew no figure"):
        bible_rig.drawn_looks("the-reel", scripts, episodes)


def test_a_builder_that_runs_past_the_bound_is_stopped_and_refused(monkeypatch, tmp_path):
    episodes, scripts = tmp_path / "episodes", tmp_path / "scripts"
    project(episodes, "the-reel")
    builder(scripts, "the-reel", "import time\ntime.sleep(60)\n")
    monkeypatch.setattr(bible_rig, "TIMEOUT", 1)
    with pytest.raises(bible_rig.RigError, match="ran past 1 s"):
        bible_rig.drawn_looks("the-reel", scripts, episodes)


FIELDS = {
    "who": "",
    "hair": "bun",
    "glasses": False,
    "neck": False,
    "tie": None,
    "apron": None,
    "cap": None,
    "sunhat": None,
    "brows": True,
}


@pytest.mark.parametrize(
    ("printed", "message"),
    [
        ("", "printed 0 look lists"),
        ('print("LOOKS []")\nprint("LOOKS []")', "printed 2 look lists"),
        ('print("LOOKS not-json")', "not JSON"),
        ('print("LOOKS [{\\"hair\\": \\"bun\\"}]")', "not made of the fields"),
        ('print("LOOKS {\\"hair\\": \\"bun\\"}")', "not made of the fields"),
        (f"print('LOOKS ' + {json.dumps(json.dumps([{**FIELDS, 'wig': 1}]))})", "not made of the fields"),
        (f"print('LOOKS ' + {json.dumps(json.dumps([{**FIELDS, 'neck': 'yes'}]))})", "neck"),
        (f"print('LOOKS ' + {json.dumps(json.dumps([{**FIELDS, 'hair': 3}]))})", "hair"),
        (f"print('LOOKS ' + {json.dumps(json.dumps([{**FIELDS, 'who': None}]))})", "who"),
    ],
)
def test_a_look_list_that_is_malformed_or_incomplete_is_refused(monkeypatch, tmp_path, printed, message):
    episodes, scripts = tmp_path / "episodes", tmp_path / "scripts"
    project(episodes, "the-reel")
    builder(scripts, "the-reel", "pass\n")
    monkeypatch.setattr(bible_rig, "HARNESS", printed)
    with pytest.raises(bible_rig.RigError, match=message):
        bible_rig.drawn_looks("the-reel", scripts, episodes)


@pytest.mark.parametrize("timeline", ["{", "[]", '{"items": 3}', '{"items": [3]}'])
def test_a_timeline_that_cannot_be_read_refuses_the_reel(tmp_path, timeline):
    """No names means every figure would be an extra, so the rule would pass on what it never read."""
    episodes, scripts = tmp_path / "episodes", tmp_path / "scripts"
    project(episodes, "the-reel", None)
    (episodes / "the-reel" / "timeline.json").write_text(timeline)
    builder(scripts, "the-reel", "stick.check_look(stick.Look())\n")
    with pytest.raises(bible_rig.RigError, match="its builder failed"):
        bible_rig.drawn_looks("the-reel", scripts, episodes)


def test_a_release_that_does_not_draw_stick_figures_runs_no_builder(tmp_path):
    other = release(style="Cutout", recurring=("dev",))  # no builder exists: running one would raise
    assert bible_rig.check_release(other, tmp_path / "episodes", tmp_path / "scripts") == []


def test_a_stick_release_naming_no_recurring_figure_runs_no_builder(tmp_path):
    assert bible_rig.check_release(release(recurring=("rex",)), tmp_path / "episodes", tmp_path / "scripts") == []


def test_a_release_that_pins_a_rig_part_draws_stick_figures_whatever_its_style_says():
    rig = next(iter(bible_rig.rig_parts()))
    assert bible_rig.draws_stick_figures(release(style="", parts={rig: 1}))
    assert bible_rig.draws_stick_figures(release(style="Stick"))
    assert not bible_rig.draws_stick_figures(release(style="Cutout", parts={}))


def test_a_stick_release_is_held_to_the_looks_its_builder_draws(tmp_path):
    episodes, scripts = tmp_path / "episodes", tmp_path / "scripts"
    project(episodes, "the-reel")
    builder(
        scripts,
        "the-reel",
        """
        stick.check_look(stick.Look(hair="cowlick", tie="#aa0000"))
        stick.check_look(stick.Look(hair="bun", glasses=True))
        stick.check_look(stick.Look(hair="bun", neck=True))
        """,
    )
    found = bible_rig.check_release(release(recurring=("dev", "noor")), episodes, scripts)
    assert [(f.kind, "'noor'" in f.message) for f in found] == [("rig", True)]


def test_a_stick_release_that_keeps_every_base_rig_has_no_finding(tmp_path):
    episodes, scripts = tmp_path / "episodes", tmp_path / "scripts"
    project(episodes, "the-reel")
    builder(
        scripts,
        "the-reel",
        """
        stick.check_look(stick.Look(hair="cowlick", tie="#aa0000"))
        stick.check_look(stick.Look(hair="bun", glasses=True, apron="#aa0000", cap="#aa0000", brows=False))
        stick.check_look(stick.Look(hair="spiky", neck=True))
        """,
    )
    assert bible_rig.check_release(release(recurring=("dev", "noor")), episodes, scripts) == []
