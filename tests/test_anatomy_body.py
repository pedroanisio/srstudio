"""Rule 2: a hand is on an arm, a character has one pair of arms, and a bust does not stand in the open (ADR 0148)."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import (
    anatomy,
    anatomy_gate,
    anatomy_ledger,
    anatomy_parts,
    cli,
    collage_everyday,
    figure_record,
    registry,
    toon_everyday,
)
from srstudio.anatomy import AnatomyError, Body, Framing, Side
from srstudio.anatomy_ledger import ARM_THIRD, BUST_OPEN, HAND_NO_ARM, Limb, Note
from srstudio.anatomy_parts import BODIES, CHARACTERS, LOOSE_HANDS
from srstudio.canvas import Canvas
from srstudio.figure_record import Figure
from srstudio.framegraph import Drawing, Frame, Node
from srstudio.layout import LayoutError
from srstudio.releases import Release
from srstudio.social import InstagramPost

EPISODES = Path(__file__).resolve().parent.parent / "episodes"
PLACE = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
POST = InstagramPost(title="t", description="d")


def WIDTH(text: str, size: float) -> float:
    return len(text) * size * 0.5


def box(left: float, top: float, right: float, bottom: float) -> tuple[tuple[float, float], ...]:
    return ((left, top), (right, top), (right, bottom), (left, bottom))


def frame(*shapes: tuple[str, tuple]) -> tuple[Frame, dict[str, Drawing]]:
    nodes = tuple(Node(name, None, "shape", PLACE, 1.0, True) for name, _ in shapes)
    return Frame(1.0, 1080.0, 1920.0, nodes), {name: Drawing((outline,), True) for name, outline in shapes}


@pytest.fixture
def cv():
    return Canvas(Scene(version="auto"), font_asset=None)


# -- the contract ---------------------------------------------------------------------------------------------------
def test_a_body_has_a_pair_of_arms_or_none():
    assert Body(Framing.BUST).arms == 2
    assert Body(Framing.WHOLE, arms=0, why="a toilet").arms == 0
    for arms in (1, 3, 4):
        with pytest.raises(AnatomyError, match="pair"):
            Body(Framing.FULL, arms=arms)


def test_a_body_with_no_arms_says_why():
    with pytest.raises(AnatomyError, match="why"):
        Body(Framing.WHOLE, arms=0)


def test_only_a_bust_needs_covering():
    assert Body(Framing.BUST).needs_cover
    assert not Body(Framing.FULL).needs_cover
    assert not Body(Framing.WHOLE, why="a printer").needs_cover


def test_every_registered_character_declares_its_body():
    names = {e.name.partition("@")[0] for e in registry.entries("character")}
    assert names == set(BODIES)


def test_a_body_with_hands_has_arms_for_them():
    for name, hands in CHARACTERS.items():
        if hands.kind is not anatomy_parts.Kind.NONE:
            assert BODIES[name].arms == 2, name


def test_a_loose_hand_is_a_declared_hand():
    assert set(LOOSE_HANDS) <= set(anatomy_parts.HAND_PROPS)


# -- a hand is on an arm --------------------------------------------------------------------------------------------
def test_a_loose_hand_is_noted(cv):
    toon_everyday.phone(cv, cv.comp, (toon_everyday.Screen(0.0, "off"),), measure=WIDTH, hand="#aa8866")
    assert [(n.rule, n.part) for n in anatomy_ledger.notes(cv)] == [(HAND_NO_ARM, "toon-phone")]


def test_a_prop_with_no_hand_is_not_noted(cv):
    toon_everyday.phone(cv, cv.comp, (toon_everyday.Screen(0.0, "off"),), measure=WIDTH)
    assert anatomy_ledger.notes(cv) == []


def test_a_hand_on_a_named_arm_is_not_noted_and_draws_the_same(cv):
    other = Canvas(Scene(version="auto"), font_asset=None)
    toon_everyday.phone(cv, cv.comp, (toon_everyday.Screen(0.0, "off"),), measure=WIDTH, hand="#aa8866")
    with anatomy_ledger.on_arm("bear", Side.RIGHT):
        toon_everyday.phone(other, other.comp, (toon_everyday.Screen(0.0, "off"),), measure=WIDTH, hand="#aa8866")
    assert anatomy_ledger.notes(other) == []
    assert cv.scene.to_bytes() == other.scene.to_bytes()


def test_the_named_arm_ends_with_its_block(cv):
    with anatomy_ledger.on_arm("bear", Side.RIGHT):
        pass
    toon_everyday.phone(cv, cv.comp, (toon_everyday.Screen(0.0, "off"),), measure=WIDTH, hand="#aa8866")
    assert len(anatomy_ledger.notes(cv)) == 1


def test_an_arm_needs_a_character_and_a_side():
    with pytest.raises(AnatomyError, match="whose"), anatomy_ledger.on_arm(" ", Side.LEFT):
        pass
    with pytest.raises(anatomy.HandError), anatomy_ledger.on_arm("bear", 0):  # type: ignore[arg-type]
        pass


@pytest.mark.parametrize("part", sorted(LOOSE_HANDS))
def test_every_loose_hand_draws_through_the_rule(part):
    import inspect

    assert f'loose_hand(cv, "{part}")' in inspect.getsource(registry.get("prop", part).builder)


def _keyword(call: ast.Call, name: str) -> ast.expr | None:
    return next((k.value for k in call.keywords if k.arg == name), None)


def _loose_in(path: Path) -> set[str]:
    """The loose hands a file's calls draw, read from its tree. ``hand`` can arrive through a splat, so a splatted call
    counts when the file names ``hand`` at all: this reads more than is drawn, never less."""
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    guarded: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.With) and any("on_arm" in ast.dump(item.context_expr) for item in node.items):
            guarded |= {id(inner) for inner in ast.walk(node)}
    found: set[str] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)) or id(node) in guarded:
            continue
        module = node.func.value.id if isinstance(node.func.value, ast.Name) else ""
        part = anatomy_parts.LOOSE_CALLS.get((module, node.func.attr))
        if part is None:
            continue
        said = _keyword(node, "hand")
        splatted = any(k.arg is None for k in node.keywords) and ("hand=" in text or '"hand"' in text)
        absent = said is None or (isinstance(said, ast.Constant) and said.value is None)
        if anatomy_parts.LOOSE_HANDS[part] and absent and not splatted:
            continue
        found.add(part)
    return found


def test_every_loose_hand_in_an_episode_is_a_listed_published_reel():
    found = {
        (path.name.removesuffix(".py").removesuffix("_data").replace("_", "-"), part)
        for path in EPISODES.glob("*.py")
        for part in _loose_in(path)
    }
    listed = {(row.reel, row.part) for row in anatomy_ledger.exemptions() if row.rule == HAND_NO_ARM}
    assert found == listed


# -- one pair of arms -----------------------------------------------------------------------------------------------
def test_a_collage_arm_records_whose_it_is(cv):
    g = collage_everyday.arm(cv, cv.comp, "brent", (0.0, 0.0), (9.0, 9.0), side=1)
    assert list(cv.limbs.values()) == [Limb("brent", Side.RIGHT, g.id)]


def test_an_upper_arm_is_not_a_second_limb(cv):
    collage_everyday.arm(cv, cv.comp, "brent", (0.0, 0.0), (9.0, 9.0), hand=False, side=1)
    assert list(cv.limbs.values()) == []


def test_a_reach_records_its_hand(cv):
    held = collage_everyday.reach(cv, cv.comp, "deb", (0.0, 0.0), lambda t: (9.0, 9.0 + t), [0.0, 1.0], side=-1)
    assert list(cv.limbs.values()) == [Limb("deb", Side.LEFT, held.id)]


def _limbs(*ids: str) -> list[Limb]:
    return [Limb("gary", Side.LEFT, i) for i in ids]


def test_two_hands_on_one_arm_on_a_frame_are_refused():
    shown, drawn = frame(("a", box(0, 0, 10, 10)), ("b", box(20, 0, 30, 10)))
    assert anatomy_gate.third_arms(shown, drawn, _limbs("a", "b")) == [("gary", Side.LEFT, 2)]


def test_one_hand_at_a_time_on_one_arm_is_fine():
    shown, drawn = frame(("a", box(0, 0, 10, 10)))
    assert anatomy_gate.third_arms(shown, drawn, _limbs("a", "b")) == []


def test_a_hand_on_each_arm_is_fine():
    shown, drawn = frame(("a", box(0, 0, 10, 10)), ("b", box(20, 0, 30, 10)))
    limbs = [Limb("gary", Side.LEFT, "a"), Limb("gary", Side.RIGHT, "b")]
    assert anatomy_gate.third_arms(shown, drawn, limbs) == []


def test_a_faded_hand_is_not_on_the_frame():
    nodes = (Node("a", None, "shape", PLACE, 1.0, True), Node("b", None, "shape", PLACE, 0.0, True))
    drawn = {"a": Drawing((box(0, 0, 10, 10),), True), "b": Drawing((box(20, 0, 30, 10),), True)}
    assert anatomy_gate.third_arms(Frame(1.0, 1080.0, 1920.0, nodes), drawn, _limbs("a", "b")) == []


def test_a_hand_wholly_behind_a_solid_shape_is_not_on_the_frame():
    shown, drawn = frame(("a", box(0, 0, 10, 10)), ("b", box(20, 0, 30, 10)), ("wall", box(15, -5, 40, 20)))
    assert anatomy_gate.third_arms(shown, drawn, _limbs("a", "b")) == []


def test_a_hand_partly_behind_a_solid_shape_is_still_on_the_frame():
    shown, drawn = frame(("a", box(0, 0, 10, 10)), ("b", box(20, 0, 30, 10)), ("wall", box(15, -5, 28, 20)))
    assert anatomy_gate.third_arms(shown, drawn, _limbs("a", "b")) == [("gary", Side.LEFT, 2)]


def test_a_hand_behind_a_see_through_shape_is_still_on_the_frame():
    shown, drawn = frame(("a", box(0, 0, 10, 10)), ("b", box(20, 0, 30, 10)), ("glass", box(15, -5, 40, 20)))
    drawn["glass"] = Drawing(drawn["glass"].outlines, False)
    assert anatomy_gate.third_arms(shown, drawn, _limbs("a", "b")) == [("gary", Side.LEFT, 2)]


def test_a_hand_in_front_of_a_solid_shape_is_still_on_the_frame():
    shown, drawn = frame(("wall", box(15, -5, 40, 20)), ("a", box(0, 0, 10, 10)), ("b", box(20, 0, 30, 10)))
    assert anatomy_gate.third_arms(shown, drawn, _limbs("a", "b")) == [("gary", Side.LEFT, 2)]


def test_a_hand_beyond_the_edge_of_the_frame_is_not_on_it():
    shown, drawn = frame(("a", box(0, 0, 10, 10)), ("b", box(1100, 0, 1130, 10)))
    assert anatomy_gate.third_arms(shown, drawn, _limbs("a", "b")) == []


def test_a_hand_cut_by_the_edge_of_the_frame_is_still_on_it():
    shown, drawn = frame(("a", box(0, 0, 10, 10)), ("b", box(1070, 0, 1100, 10)))
    assert anatomy_gate.third_arms(shown, drawn, _limbs("a", "b")) == [("gary", Side.LEFT, 2)]


def test_two_characters_each_have_their_own_arms():
    shown, drawn = frame(("a", box(0, 0, 10, 10)), ("b", box(20, 0, 30, 10)))
    limbs = [Limb("gary", Side.LEFT, "a"), Limb("omar", Side.LEFT, "b")]
    assert anatomy_gate.third_arms(shown, drawn, limbs) == []


# -- a bust is covered ----------------------------------------------------------------------------------------------
BUST = box(300, 841, 789, 1406)


def test_a_bust_ending_in_the_open_is_open():
    shown, drawn = frame(("body", BUST), ("counter", box(0, 1500, 1080, 1920)))
    assert anatomy_gate.open_bust(shown, [0], drawn)


def test_a_bust_behind_a_deep_counter_is_not_open():
    shown, drawn = frame(("body", BUST), ("counter", box(0, 1380, 1080, 1920)))
    assert not anatomy_gate.open_bust(shown, [0], drawn)


def test_a_bust_cropped_by_the_frame_is_not_open():
    shown, drawn = frame(("body", box(300, 841, 789, 1919)))
    assert not anatomy_gate.open_bust(shown, [0], drawn)


def test_a_figure_with_its_legs_drawn_is_not_a_bust():
    shown, drawn = frame(("manager-legs", box(300, 1000, 500, 1600)), ("body", BUST))
    assert not anatomy_gate.open_bust(shown, [0, 1], drawn)


@pytest.fixture
def built(tmp_path):
    release = Release("a-b", POST, video="The_Video")
    project = tmp_path / "ep" / "a-b"
    project.mkdir(parents=True)
    (project / release.scene_file).write_bytes(b"<scene/>")
    return {"a-b": release}, tmp_path / "ep", project


def test_a_bust_with_no_cover_is_a_defect_of_its_reel(built, monkeypatch):
    releases, episodes, project = built
    figure_record.write(project, [Figure("toon-cat", ("body",))])
    anatomy_ledger.write(project, [])
    shown, drawn = frame(("body", BUST))
    monkeypatch.setattr(anatomy_gate.framegraph, "evaluate", lambda *_: [shown])
    monkeypatch.setattr(anatomy_gate.framegraph, "drawings", lambda *_: drawn)
    monkeypatch.setattr(anatomy_gate, "_duration", lambda *_: 1.0)
    [drift] = anatomy_gate.body_defects(releases, episodes, {"a-b": "The_Video"}, "engine")
    assert BUST_OPEN in drift.reason and "toon-cat" in drift.reason


def test_a_full_figure_is_not_judged_as_a_bust(built, monkeypatch):
    releases, episodes, project = built
    figure_record.write(project, [Figure("stick-rig", ("body",))])
    anatomy_ledger.write(project, [])
    shown, drawn = frame(("body", BUST))
    monkeypatch.setattr(anatomy_gate.framegraph, "evaluate", lambda *_: [shown])
    monkeypatch.setattr(anatomy_gate.framegraph, "drawings", lambda *_: drawn)
    monkeypatch.setattr(anatomy_gate, "_duration", lambda *_: 1.0)
    assert anatomy_gate.body_defects(releases, episodes, {"a-b": "The_Video"}, "engine") == []


def test_two_hands_on_an_arm_in_the_record_are_a_defect_of_the_reel(built, monkeypatch):
    releases, episodes, project = built
    figure_record.write(project, [])
    anatomy_ledger.write(project, [], _limbs("a", "b"))
    shown, drawn = frame(("a", box(0, 0, 10, 10)), ("b", box(20, 0, 30, 10)))
    monkeypatch.setattr(anatomy_gate.framegraph, "evaluate", lambda *_: [shown])
    monkeypatch.setattr(anatomy_gate.framegraph, "drawings", lambda *_: drawn)
    monkeypatch.setattr(anatomy_gate, "_duration", lambda *_: 1.0)
    [drift] = anatomy_gate.body_defects(releases, episodes, {"a-b": "The_Video"}, "engine")
    assert ARM_THIRD in drift.reason and "gary" in drift.reason


def test_a_scene_with_no_figures_record_cannot_be_read(built):
    releases, episodes, _ = built
    [drift] = anatomy_gate.body_defects(releases, episodes, {"a-b": "The_Video"}, "engine")
    assert "figures.json" in drift.reason


def test_a_loose_hand_in_a_record_stands_at_first_delivery(built):
    releases, episodes, project = built
    note = Note(HAND_NO_ARM, "toon-phone", "a hand with no arm")
    anatomy_ledger.write(project, [note])
    assert "hand-no-arm" in anatomy_gate.hand_defects(releases, episodes, {"a-b": "The_Video"})[0].reason


def test_a_record_keeps_its_limbs(tmp_path):
    limbs = [Limb("gary", Side.RIGHT, "g-0001")]
    anatomy_ledger.write(tmp_path, [], limbs)
    assert anatomy_ledger.read_limbs(tmp_path) == limbs


def test_a_record_with_an_unknown_side_is_refused(tmp_path):
    (tmp_path / anatomy_ledger.RECORD).write_text(
        json.dumps({"schema": anatomy_ledger.SCHEMA, "notes": [], "limbs": [{"owner": "g", "side": 7, "id": "a"}]}),
        encoding="utf-8",
    )
    with pytest.raises(anatomy_ledger.ExemptionError):
        anatomy_ledger.read_limbs(tmp_path)


# -- at the build ---------------------------------------------------------------------------------------------------
def test_a_new_reel_with_a_loose_hand_does_not_build():
    with pytest.raises(anatomy_ledger.AnatomyRefusedError, match="hand-no-arm"):
        anatomy_ledger.refuse("a-new-reel", [Note(HAND_NO_ARM, "toon-phone", "no arm")])


def test_a_published_reel_with_its_loose_hand_listed_still_builds():
    anatomy_ledger.refuse("text-me", [Note(HAND_NO_ARM, "toon-phone", "no arm")])


def test_a_listed_part_excuses_no_other_part():
    with pytest.raises(anatomy_ledger.AnatomyRefusedError, match="toon-lasagna"):
        anatomy_ledger.refuse("text-me", [Note(HAND_NO_ARM, "toon-lasagna", "no arm")])


def _open_scene(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    figure_record.write(project, [Figure("toon-cat", ("body",))])
    anatomy_ledger.write(project, [])
    shown, drawn = frame(("body", BUST))
    monkeypatch.setattr(anatomy_gate.framegraph, "evaluate", lambda *_: [shown])
    monkeypatch.setattr(anatomy_gate.framegraph, "drawings", lambda *_: drawn)
    monkeypatch.setattr(anatomy_gate, "_duration", lambda *_: 1.0)


def test_the_build_command_fails_on_an_open_bust(built, monkeypatch, capsys):
    _, _, project = built
    _open_scene(project, monkeypatch)
    monkeypatch.setattr(cli, "find_engine", lambda: Path("engine"))
    assert cli._anatomy_frames(project) == 1
    assert BUST_OPEN in capsys.readouterr().err


def test_the_build_command_says_when_it_could_not_measure(built, monkeypatch, capsys):
    _, _, project = built

    def nothing() -> Path:
        raise LayoutError("no scene-render")

    monkeypatch.setattr(cli, "find_engine", nothing)
    assert cli._anatomy_frames(project) == 0
    assert "not measured" in capsys.readouterr().err


def test_the_build_command_passes_a_covered_figure(built, monkeypatch):
    _, _, project = built
    figure_record.write(project, [Figure("toon-cat", ("body",))])
    anatomy_ledger.write(project, [])
    shown, drawn = frame(("body", BUST), ("counter", box(0, 1380, 1080, 1920)))
    monkeypatch.setattr(anatomy_gate.framegraph, "evaluate", lambda *_: [shown])
    monkeypatch.setattr(anatomy_gate.framegraph, "drawings", lambda *_: drawn)
    monkeypatch.setattr(anatomy_gate, "_duration", lambda *_: 1.0)
    monkeypatch.setattr(cli, "find_engine", lambda: Path("engine"))
    assert cli._anatomy_frames(project) == 0


def test_a_project_with_no_scene_has_nothing_to_measure(tmp_path):
    assert cli._anatomy_frames(tmp_path) == 0


def test_an_undeclared_character_is_refused_not_passed():
    with pytest.raises(AnatomyError, match="declares no body"):
        anatomy_parts.body("toon-nobody")
    assert anatomy_parts.body("toon-fox@2") is BODIES["toon-fox"]


def test_the_delivery_gate_runs_the_frame_rule():
    source = (EPISODES / "instagram_posts.py").read_text(encoding="utf-8")
    assert "anatomy_gate.body_defects(chosen, _beside(renders), first, engine)" in source
