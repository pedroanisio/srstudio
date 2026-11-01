"""What a build noted of a character's body, the closed list of what is excused, and the refusal (ADR 0105)."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import anatomy_ledger, collage_everyday, news_inked, parts, toon_bento, toon_head, usage
from srstudio._transaction import scene_transaction
from srstudio.anatomy import AnatomyError
from srstudio.anatomy_ledger import HAND_NO_SIDE, HAND_UNPAIRED, AnatomyRefusedError, Exemption, ExemptionError, Note
from srstudio.canvas import Canvas
from srstudio.episode import Episode, EpisodeSpec
from srstudio.head_motion import HeadPlan
from srstudio.news_kit import Pose as NewsPose

EPISODES = Path(__file__).resolve().parent.parent / "episodes"
ROW = {"reel": "a-b", "rule": HAND_NO_SIDE, "part": "collage-arm", "why": "published with it"}
FAULT = Note(HAND_NO_SIDE, "collage-arm", "brent's hand does not say which arm it is on")


def document(*rows: object, **top: object) -> str:
    return json.dumps({"schema": anatomy_ledger.SCHEMA, "exemptions": list(rows), **top})


@pytest.fixture
def cv():
    return Canvas(Scene(version="auto"), font_asset=None)


def test_an_exemption_list_reads_into_rows():
    assert anatomy_ledger.parse_exemptions(document(ROW)) == (
        Exemption("a-b", HAND_NO_SIDE, "collage-arm", ROW["why"]),
    )


@pytest.mark.parametrize(
    ("text", "said"),
    [
        ("not json", "not JSON"),
        ("[]", "exactly schema"),
        (document(extra=1), "exactly schema"),
        (json.dumps({"schema": "9.0.0", "exemptions": []}), "schema"),
        (json.dumps({"schema": anatomy_ledger.SCHEMA, "exemptions": {}}), "list of rows"),
        (document({**ROW, "by": "me"}), "exactly"),
        (document({"reel": "a-b"}), "exactly"),
        (document("a-b"), "exactly"),
        (document({**ROW, "why": " "}), "words"),
        (document({**ROW, "why": 3}), "words"),
        (document({**ROW, "rule": "ignore-all"}), "one of"),
        (document(ROW, ROW), "twice"),
    ],
)
def test_a_list_that_is_not_one_is_refused(text, said):
    with pytest.raises(ExemptionError, match=said):
        anatomy_ledger.parse_exemptions(text)


def test_the_shipped_list_reads_and_every_row_is_a_slug():
    rows = anatomy_ledger.exemptions()
    assert all(row.reel == row.reel.lower() and " " not in row.reel for row in rows)


def test_a_note_with_no_row_is_refused_by_name():
    with pytest.raises(AnatomyRefusedError, match=r"a-b: .*hand-no-side on collage-arm"):
        anatomy_ledger.refuse("a-b", [FAULT])


def test_a_refusal_is_an_anatomy_error():
    assert issubclass(AnatomyRefusedError, AnatomyError)


def test_a_row_excuses_only_its_own_reel_rule_and_part():
    row = Exemption("a-b", HAND_NO_SIDE, "collage-arm", "why")
    assert anatomy_ledger.unexcused("a-b", [FAULT], [row]) == []
    assert anatomy_ledger.unexcused("c-d", [FAULT], [row]) == [FAULT]
    other_rule = Note(HAND_UNPAIRED, "collage-arm", "")
    other_part = Note(HAND_NO_SIDE, "news-gus", "")
    assert anatomy_ledger.unexcused("a-b", [other_rule, other_part], [row]) == [other_rule, other_part]


def test_nothing_noted_is_nothing_refused():
    anatomy_ledger.refuse("a-b", [])


def test_a_note_comes_back_in_a_fixed_order(cv):
    cv.note_anatomy(HAND_UNPAIRED, "news-vera", "v")
    cv.note_anatomy(HAND_NO_SIDE, "collage-arm", "a")
    assert [n.rule for n in anatomy_ledger.notes(cv)] == [HAND_NO_SIDE, HAND_UNPAIRED]


def test_a_failed_authoring_call_takes_its_notes_with_it(cv):
    with pytest.raises(RuntimeError), scene_transaction(cv.scene, cv):
        cv.note_anatomy(HAND_NO_SIDE, "collage-arm", "a")
        raise RuntimeError
    assert anatomy_ledger.notes(cv) == []


def test_a_side_less_collage_hand_is_noted_and_drawn_as_it_was(cv):
    collage_everyday.arm(cv, cv.comp, "brent", (0.0, 0.0), (100.0, 100.0))
    assert anatomy_ledger.notes(cv) == [FAULT]


@pytest.mark.parametrize("side", [-1, 1])
def test_a_collage_hand_that_says_its_side_is_not_noted(cv, side):
    collage_everyday.arm(cv, cv.comp, "brent", (0.0, 0.0), (100.0, 100.0), side=side)
    assert anatomy_ledger.notes(cv) == []


def test_an_upper_arm_has_no_hand_to_place(cv):
    collage_everyday.arm(cv, cv.comp, "brent", (0.0, 0.0), (100.0, 100.0), hand=False)
    assert anatomy_ledger.notes(cv) == []


def test_a_side_less_reach_is_noted(cv):
    collage_everyday.reach(cv, cv.comp, "deb", (0.0, 0.0), lambda t: (100.0, 100.0 + t), [0.0, 1.0])
    assert [n.part for n in anatomy_ledger.notes(cv)] == ["collage-arm"]


@pytest.mark.parametrize("hand", [True, False])
def test_a_bad_side_is_refused_on_any_arm(cv, hand):
    with pytest.raises(collage_everyday.EverydayError, match="side"):
        collage_everyday.arm(cv, cv.comp, "brent", (0.0, 0.0), (1.0, 1.0), side=2, hand=hand)


def test_an_old_bento_is_noted_and_the_pair_is_not(cv):
    pose = [toon_bento.pose_of(0.0, "neutral")]
    toon_bento.bento_2(cv, cv.comp, pose, 1.0)
    assert anatomy_ledger.notes(cv) == []
    toon_bento.bento(cv, cv.comp, pose, 1.0)
    assert [(n.rule, n.part) for n in anatomy_ledger.notes(cv)] == [(HAND_UNPAIRED, "toon-bento")]


def test_an_old_bento_on_its_rig_is_noted_as_well(cv):
    toon_head.figure(cv, cv.comp, toon_bento.BENTO_RIG, [toon_bento.pose_of(0.0, "neutral")], 1.0, HeadPlan.still())
    assert [n.part for n in anatomy_ledger.notes(cv)] == ["toon-bento"]


@pytest.mark.parametrize("number", [2, 3, 4, 5])
def test_an_unpaired_anchor_is_noted(cv, number):
    news_inked.perform(cv, cv.comp, "gus", 500.0, [(0.0, NewsPose())], 0.0, 1.0, number=number)
    assert [(n.rule, n.part) for n in anatomy_ledger.notes(cv)] == [(HAND_UNPAIRED, "news-gus")]


def test_a_paired_anchor_is_not_noted(cv):
    news_inked.perform(cv, cv.comp, "vera", 500.0, [(0.0, NewsPose())], 0.0, 1.0, number=6)
    assert anatomy_ledger.notes(cv) == []


@pytest.fixture
def episode(project):
    def make(slug: str = "new-reel") -> Episode:
        return Episode(
            EpisodeSpec(
                slug=slug, title="t", description="t", root=project, seed=1, background="#D5DFDF", signature=False
            )
        )

    return make


def _sideless_arm(ep: Episode) -> None:
    collage_everyday.arm(ep.cv, ep.comp, "brent", (0.0, 0.0), (100.0, 100.0))


def test_a_build_with_a_fault_writes_no_scene(episode, tmp_path):
    ep = episode()
    _sideless_arm(ep)
    out = tmp_path / "new-reel.scene.xml"
    with pytest.raises(AnatomyRefusedError, match="new-reel"):
        ep.finish(out=out)
    assert not out.exists()


def test_a_published_reel_on_the_list_still_rebuilds(episode, tmp_path, monkeypatch):
    row = Exemption("old-reel", HAND_NO_SIDE, "collage-arm", "published with it")
    monkeypatch.setattr(anatomy_ledger, "exemptions", lambda: (row,))
    ep = episode("old-reel")
    _sideless_arm(ep)
    assert ep.finish(out=tmp_path / "old-reel.scene.xml").is_file()


def test_a_recorded_build_leaves_what_it_noted(episode, tmp_path, monkeypatch):
    row = Exemption("old-reel", HAND_NO_SIDE, "collage-arm", "published with it")
    monkeypatch.setattr(anatomy_ledger, "exemptions", lambda: (row,))
    with usage.recorded(tmp_path):
        ep = episode("old-reel")
        _sideless_arm(ep)
        ep.finish(out=tmp_path / "old-reel.scene.xml")
    assert anatomy_ledger.read(tmp_path) == [FAULT]


def test_a_clean_recorded_build_leaves_an_empty_record(episode, tmp_path):
    with usage.recorded(tmp_path):
        episode().finish(out=tmp_path / "new-reel.scene.xml")
    assert anatomy_ledger.read(tmp_path) == []


def test_a_refused_build_leaves_no_record(episode, tmp_path):
    anatomy_ledger.write(tmp_path, [])
    with pytest.raises(AnatomyRefusedError), usage.recorded(tmp_path):
        ep = episode()
        _sideless_arm(ep)
        ep.finish(out=tmp_path / "new-reel.scene.xml")
    assert anatomy_ledger.read(tmp_path) is None


def test_a_project_built_before_the_rule_has_no_record(tmp_path):
    assert anatomy_ledger.read(tmp_path) is None


@pytest.mark.parametrize(
    "text",
    ["not json", "{}", json.dumps({"schema": "9.9.9", "notes": []}), json.dumps({"schema": "1.0.0", "notes": [{}]})],
)
def test_a_record_that_is_not_one_is_refused(tmp_path, text):
    (tmp_path / anatomy_ledger.RECORD).write_text(text, encoding="utf-8")
    with pytest.raises(ExemptionError):
        anatomy_ledger.read(tmp_path)


def _sideless(tree: ast.AST) -> list[int]:
    """The lines where a Collage hand-bearing arm is called with no ``side``."""
    lines = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if not (isinstance(node.func.value, ast.Name) and node.func.value.id == "collage_everyday"):
            continue
        said = {k.arg: k.value for k in node.keywords}
        upper = isinstance(said.get("hand"), ast.Constant) and said["hand"].value is False  # type: ignore[union-attr]
        if node.func.attr in ("arm", "reach") and "side" not in said and not upper:
            lines.append(node.lineno)
    return lines


def test_every_side_less_arm_in_an_episode_is_a_listed_published_reel():
    """The list is closed the other way as well: no reel on it can be fixed and stay listed, and no new reel can draw
    a hand with no side and rebuild."""
    found = {
        path.name.removesuffix("_data.py").replace("_", "-")
        for path in EPISODES.glob("*.py")
        if _sideless(ast.parse(path.read_text(encoding="utf-8")))
    }
    listed = {row.reel for row in anatomy_ledger.exemptions() if row.rule == HAND_NO_SIDE}
    assert found == listed


def test_a_version_on_the_list_of_an_unpaired_part_is_still_drawable():
    assert parts.drawing("news-gus", 3).name == "news-gus@3"
