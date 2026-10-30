"""End-to-end: synthetic projects through the office and café kits, checked by the SDK."""

import json
import shutil
import xml.etree.ElementTree as ET

import pytest

from srstudio import CAFE, CAFE_MOUTH, Episode, EpisodeSpec, camera, cast, graphics, locations
from srstudio.episode import EpisodeError, SceneCheckError
from srstudio.errors import SrstudioError
from support.build import office_episode


def test_office_episode_builds_and_validates(project, tmp_path):
    ep, path = office_episode(project, tmp_path)
    assert ep.check() == []
    root = ET.parse(path).getroot()
    ids = {el.get("id") for el in root.iter() if el.get("id")}
    assert {
        "wide-office-angle",
        "candidate-reverse-angle",
        "manager-character",
        "candidate-character",
        "manager-facepalm",
        "candidate-pointing-hand",
        "silent-work-phone",
        "dialogue-1",
    } <= ids
    assert (tmp_path / "sdk-validation.json").read_text().strip() == "[]"
    # Five mouth shapes per head, each switched by hold keys.
    head = next(el for el in root.iter("group") if el.get("id") == "manager-head")
    mouths = [c for c in head if c.tag == "shape" and any(a.get("property") == "opacity" for a in c.findall("animate"))]
    assert len(mouths) == 5


def test_cafe_episode_builds_and_validates(project, tmp_path):
    ep = Episode(
        EpisodeSpec(
            slug="t-cafe",
            title="t",
            description="t",
            root=project,
            seed=2,
            background="#F0DDC0",
            palette=CAFE,
            mouth_style=CAFE_MOUTH,
            font_id="font",
        )
    )
    t, P = ep.t, ep.P
    mouth = ep.mouth("candidate", smile=[(0, P(0).start)])
    cafe = ep.setup(
        locations.cafe,
        [(0, t.reaction)],
        behind_counter=lambda g: ep.perform(cast.Barista(ep.cv), g, 750, 800, 1.35, nods=[(0, 0), (1, -3)]),
        at_counter=lambda g: ep.perform(
            cast.Customer(ep.cv), g, 270, 1035, 1.53, mouth=mouth, held_cup=[(P(1).end, t.reaction)]
        ),
    )
    camera.reframe(ep.cv, cafe, [(0, 1, 0, 0), (P(1).start, 1.4, 540 - 270 * 1.4, 775 - 1035 * 1.4)])
    ep.setup(
        locations.park,
        [(t.reaction, t.duration)],
        on_bench=lambda g: ep.perform(cast.Customer(ep.cv, seated=True), g, 510, 770, 1.62, mouth=mouth),
        beside_bench=lambda g: cast.pigeon(ep.cv, g, nods=[(0, 0), (t.ending, -7)]),
    )
    graphics.password_card(ep.cv, ep.comp, "WI-FI", "secret", "NO SPACES", show=(P(1).start, t.reaction))
    graphics.location_slate(ep.cv, ep.comp, "LATER", show=(t.reaction, t.reaction + 1))
    ep.captions(x=40, y=1488, width=1000, weight=None, line_height="1.12", stroke=ep.cv.ink)
    ep.audio_mix(track_id="voice")
    ep.markers(name="{name}-marker", extra=[("park-marker", t.reaction, "park")])
    path = ep.finish(tmp_path / "t-cafe.scene.xml")
    assert ep.check() == []
    ids = {el.get("id") for el in ET.parse(path).getroot().iter() if el.get("id")}
    assert {"location-cafe", "location-park", "pigeon", "ava-name", "park-marker"} <= ids


def test_finish_refuses_a_document_with_findings(project, tmp_path):
    ep = Episode(EpisodeSpec(slug="t-bad", title="t", description="t", root=project, seed=3, background="#D5DFDF"))
    ep.comp.add_group(id="dup")
    ep.comp.add_group(id="dup")
    with pytest.raises(SceneCheckError, match="id 'dup' is already used") as refused:
        ep.finish(tmp_path / "t-bad.scene.xml")
    assert isinstance(refused.value, SrstudioError) and isinstance(refused.value, ValueError)
    assert [f.code for f in refused.value.findings] == ["xsd:id-unique"]
    assert not (tmp_path / "t-bad.scene.xml").exists()


def test_default_captions_work_without_reaction_beats_and_clamp_the_first_lead(project, tmp_path):
    project = shutil.copytree(project, tmp_path / "project")
    data = json.loads((project / "dialogue.json").read_text())
    data.pop("reaction_start")
    data["phrases"][0]["start"] = 0
    (project / "dialogue.json").write_text(json.dumps(data))
    ep = Episode(EpisodeSpec(slug="captions", title="t", description="t", root=project, seed=1, signature=False))
    specs = ep.default_captions()
    assert specs[0][0] == 0
    assert specs[-1][1] == ep.t.duration
    ep.captions()
    assert ep.check() == []


def test_caption_boundaries_follow_time_instead_of_cut_indices(project, tmp_path):
    project = shutil.copytree(project, tmp_path / "project")
    data = json.loads((project / "dialogue.json").read_text())
    phrases = data["phrases"]
    # More than one shot within a line must not truncate that line's caption.
    extra = {"time": (phrases[0]["start"] + phrases[0]["end"]) / 2, "angle": "insert"}
    data["camera_cuts"].insert(1, extra)
    (project / "dialogue.json").write_text(json.dumps(data))
    ep = Episode(EpisodeSpec(slug="captions", title="t", description="t", root=project, seed=1))
    specs = ep.default_captions()
    assert specs[0][1] == data["camera_cuts"][2]["time"]
    assert all(end >= p.end for (_, end, _, _), p in zip(specs, ep.phrases, strict=True))


def test_caption_scripts_keep_their_own_windows(project, tmp_path):
    project = shutil.copytree(project, tmp_path / "project")
    items = [{"start": 0, "end": 1, "text": "First"}, {"start": 2, "end": 3, "text": "Second"}]
    (project / "script.json").write_text(json.dumps(items))
    ep = Episode(EpisodeSpec(slug="captions", title="t", description="t", root=project, seed=1, dialogue="script.json"))
    assert [(a, b) for a, b, _, _ in ep.default_captions(lead=0)] == [(0, 1), (2, 3)]


def test_spoken_captions_end_before_the_next_one_starts(project):
    ep = Episode(EpisodeSpec(slug="s", title="t", description="d", root=project, seed=1))
    specs = ep.spoken_captions(tail=100.0, lead=0.05)
    assert all(a[1] <= b[0] for a, b in zip(specs, specs[1:], strict=False))
    assert specs[-1][1] == ep.phrases[-1].end + 100.0
    assert [s[3] for s in specs[:2]] == ["dialogue-1", "dialogue-2"]


def test_spoken_captions_refuse_a_negative_tail(project):
    ep = Episode(EpisodeSpec(slug="s", title="t", description="d", root=project, seed=1))
    with pytest.raises(EpisodeError, match="lead and tail"):
        ep.spoken_captions(tail=-1.0)
