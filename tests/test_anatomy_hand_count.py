"""Rule 2, counted per figure: the hands a figure's own layers draw at once, whatever a set covers (ADR 0174).

arc4d3 ruled Bruno's Wow in it-autoplayed a fault: he raises both arms while his body drawing keeps its two paws on his
belly. The sofa's back covered the belly in the master, so two hands showed; a higher seat shows all four.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import (
    DAYLIGHT,
    anatomy_gate,
    anatomy_ledger,
    cli,
    collage,
    figure_record,
    framegraph,
    toon_bed,
    toon_cast,
    usage,
)
from srstudio.anatomy import Side
from srstudio.anatomy_ledger import ARM_THIRD, HAND_COUNT, HAND_NO_ARM, Limb
from srstudio.canvas import Canvas
from srstudio.figure_record import Figure
from srstudio.framegraph import Drawing, Frame, Node
from srstudio.toon import Pose

EPISODES = Path(__file__).resolve().parent.parent / "episodes"
PLACE = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def box(left: float, top: float, right: float, bottom: float) -> tuple[tuple[float, float], ...]:
    return ((left, top), (right, top), (right, bottom), (left, bottom))


def frame(*shapes: tuple[str, tuple], faded: tuple[str, ...] = ()) -> tuple[Frame, dict[str, Drawing]]:
    """A frame of shapes drawn in order, the last in front; a ``faded`` one is at opacity 0."""
    nodes = tuple(Node(name, None, "shape", PLACE, 0.0 if name in faded else 1.0, True) for name, _ in shapes)
    return Frame(1.0, 1080.0, 1920.0, nodes), {name: Drawing((outline,), True) for name, outline in shapes}


def paws(owner: str, node: str) -> list[Limb]:
    """A body drawing's two hands, as a figure records them on the drawing that holds them."""
    return [Limb(owner, Side.LEFT, node), Limb(owner, Side.RIGHT, node)]


def _body(*ids: str) -> Figure:
    return Figure("toon-bear", ids)


BEAR = box(380, 700, 700, 1300)  # the bear's body drawing, head to belly, its paws on the belly
RAISED_L, RAISED_R = box(330, 450, 380, 520), box(700, 450, 750, 520)
SOFA_BACK = box(0, 1000, 1080, 1920)  # up over his belly, so the resting paws are behind it


@pytest.fixture
def cv():
    return Canvas(Scene(version="auto"), font_asset=None)


# -- the count on a frame -------------------------------------------------------------------------------------------
def test_raised_arms_over_resting_paws_are_four_hands_though_the_sofa_covers_two():
    shown, drawn = frame(("bear", BEAR), ("up-l", RAISED_L), ("up-r", RAISED_R), ("sofa", SOFA_BACK))
    limbs = [*paws("bear", "bear"), Limb("bear", Side.LEFT, "up-l"), Limb("bear", Side.RIGHT, "up-r")]
    assert anatomy_gate.extra_hands(shown, drawn, limbs, [_body("bear")]) == [("bear", 4)]


def test_a_body_drawing_with_its_two_paws_is_fine():
    shown, drawn = frame(("bear", BEAR), ("sofa", SOFA_BACK))
    assert anatomy_gate.extra_hands(shown, drawn, paws("bear", "bear"), [_body("bear")]) == []


def test_a_pose_not_shown_draws_no_hands():
    shown, drawn = frame(("desk", BEAR), ("up", BEAR), ("up-l", RAISED_L), faded=("desk",))
    limbs = [*paws("bear", "desk"), Limb("bear", Side.LEFT, "up"), Limb("bear", Side.LEFT, "up-l")]
    assert anatomy_gate.extra_hands(shown, drawn, limbs, [_body("desk", "up")]) == []


def test_a_hand_beyond_the_frame_s_edge_is_still_one_the_figure_draws():
    shown, drawn = frame(("bear", BEAR), ("parked", box(1100, 450, 1150, 520)))
    limbs = [*paws("bear", "bear"), Limb("bear", Side.RIGHT, "parked")]
    assert anatomy_gate.extra_hands(shown, drawn, limbs, [_body("bear")]) == [("bear", 3)]


def test_two_figures_each_have_their_own_pair():
    shown, drawn = frame(("bear", BEAR), ("rabbit", box(0, 700, 300, 1300)))
    limbs = [*paws("bear", "bear"), *paws("rabbit", "rabbit")]
    assert anatomy_gate.extra_hands(shown, drawn, limbs, [_body("bear"), _body("rabbit")]) == []


def tree(*nodes: tuple[str, str | None, tuple | None]) -> tuple[Frame, dict[str, Drawing]]:
    """A frame of ``(id, parent id, outline)`` nodes in drawing order; a node with no outline is a group."""
    at = {name: i for i, (name, _, _) in enumerate(nodes)}
    shown = tuple(
        Node(name, None if up is None else at[up], "shape" if outline else "group", PLACE, 1.0, True)
        for name, up, outline in nodes
    )
    return Frame(1.0, 1080.0, 1920.0, shown), {name: Drawing((o,), True) for name, _, o in nodes if o}


def test_two_of_one_character_in_a_crowd_each_have_their_own_pair():
    """someone-else at 30 s: a call centre of rows of the same five characters, each one a figure of its own."""
    shown, drawn = frame(*((f"raccoon-{n}", box(300 * n, 300, 300 * n + 250, 600)) for n in range(3)))
    limbs = [hand for n in range(3) for hand in paws("raccoon", f"raccoon-{n}")]
    figures = [Figure("toon-raccoon", (f"raccoon-{n}",)) for n in range(3)]
    assert anatomy_gate.extra_hands(shown, drawn, limbs, figures) == []


def test_a_swung_arm_counts_with_the_figure_drawn_nearest_it():
    """Two bears in two shots of one frame (a split screen); the raised arms are drawn in the left one's shot."""
    shown, drawn = tree(
        ("left", None, None),
        ("bear-l", "left", box(40, 700, 500, 1300)),
        ("up-l", "left", RAISED_L),
        ("up-r", "left", box(450, 450, 500, 520)),
        ("right", None, None),
        ("bear-r", "right", box(580, 700, 1040, 1300)),
    )
    limbs = [*paws("bear", "bear-l"), *paws("bear", "bear-r")]
    limbs += [Limb("bear", Side.LEFT, "up-l"), Limb("bear", Side.RIGHT, "up-r")]
    figures = [Figure("toon-bear", ("bear-l",)), Figure("toon-bear", ("bear-r",))]
    assert anatomy_gate.extra_hands(shown, drawn, limbs, figures) == [("bear", 4)]


GARY = box(390, 980, 880, 1700)  # in bed, his pose's one hand and the scene's arm with the phone
HELD = box(510, 1520, 580, 1700)
INSERT = box(190, 830, 890, 1780)  # the phone up to his eye: it covers the bed shot's gary whole
POV = box(800, 1440, 960, 1920)


def test_a_figure_wholly_behind_an_insert_counts_only_the_hands_seen():
    """thought-of-you at 3.5 s: the bed shot's gary, his pose's hand and the hand on the phone, is wholly behind the
    insert that shows that same hand from his eyes. One hand of his is on the frame, and no body to hold more."""
    shown, drawn = frame(("bed", GARY), ("held", HELD), ("insert", INSERT), ("pov", POV))
    limbs = [Limb("gary", Side.RIGHT, "bed"), Limb("gary", Side.LEFT, "held"), Limb("gary", Side.LEFT, "pov")]
    assert anatomy_gate.extra_hands(shown, drawn, limbs, [_body("bed")]) == []


def test_a_figure_is_seen_by_its_own_pixels_not_its_box():
    """thought-of-you at 3.5 s again: the insert covers all of gary's drawing, not the empty corner of his box."""
    leaning = ((380.0, 700.0), (700.0, 700.0), (380.0, 1300.0))
    cover = ((370.0, 690.0), (720.0, 690.0), (370.0, 1320.0))
    shown, drawn = frame(("bed", leaning), ("held", box(400, 720, 460, 800)), ("insert", cover), ("pov", POV))
    hidden = shown.box(0, drawn)
    assert hidden is not None and hidden.right == 700.0 and hidden.bottom == 1300.0  # its box's corner is uncovered
    limbs = [Limb("gary", Side.RIGHT, "bed"), Limb("gary", Side.LEFT, "held"), Limb("gary", Side.LEFT, "pov")]
    assert anatomy_gate.extra_hands(shown, drawn, limbs, [_body("bed")]) == []


def test_a_figure_seen_counts_its_hands_behind_the_set():
    shown, drawn = frame(("bed", GARY), ("held", HELD), ("duvet", box(0, 1450, 1080, 1920)), ("pov", POV))
    limbs = [Limb("gary", Side.RIGHT, "bed"), Limb("gary", Side.LEFT, "held"), Limb("gary", Side.LEFT, "pov")]
    assert anatomy_gate.extra_hands(shown, drawn, limbs, [_body("bed")]) == [("gary", 3)]


# -- at the build ---------------------------------------------------------------------------------------------------
@pytest.fixture
def project(tmp_path):
    project = tmp_path / "a-b"
    project.mkdir()
    (project / "a-b.scene.xml").write_bytes(b"<scene/>")
    return project


def _wow(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    figure_record.write(project, [Figure("toon-bear", ("bear",))])
    limbs = [*paws("bear", "bear"), Limb("bear", Side.LEFT, "up-l"), Limb("bear", Side.RIGHT, "up-r")]
    anatomy_ledger.write(project, [], limbs)
    shown, drawn = frame(("bear", BEAR), ("up-l", RAISED_L), ("up-r", RAISED_R), ("sofa", SOFA_BACK))
    monkeypatch.setattr(anatomy_gate.framegraph, "evaluate", lambda *_: [shown])
    monkeypatch.setattr(anatomy_gate.framegraph, "drawings", lambda *_: drawn)
    monkeypatch.setattr(anatomy_gate, "_duration", lambda *_: 1.0)
    monkeypatch.setattr(cli, "find_engine", lambda: Path("engine"))


def test_the_build_fails_on_four_hands_with_the_belly_covered(project, monkeypatch, capsys):
    _wow(project, monkeypatch)
    assert cli._anatomy_frames(project) == 1
    said = capsys.readouterr().err
    assert f"{HAND_COUNT} on bear: 4 hands at 1 s" in said
    assert ARM_THIRD not in said  # one fault, said once: the arms over the pair are the count's


def test_a_pose_s_one_hand_and_the_scene_s_arm_are_a_pair_whatever_side_the_arm_defaults_to(project, monkeypatch):
    """cold-front at 6 s: Deb's pose draws one hand and leaves the other arm to the scene, which does not say its side,
    so it defaults to the pose hand's. Two hands are her pair: arm-third reads the scene's hands, the count all."""
    figure_record.write(project, [Figure("collage-deb", ("deb",))])
    anatomy_ledger.write(project, [], [Limb("deb", Side.LEFT, "deb"), Limb("deb", Side.LEFT, "arm")])
    shown, drawn = frame(("deb", box(30, 850, 720, 1950)), ("arm", box(850, 1560, 1080, 1950)))  # past the foot
    monkeypatch.setattr(anatomy_gate.framegraph, "evaluate", lambda *_: [shown])
    monkeypatch.setattr(anatomy_gate.framegraph, "drawings", lambda *_: drawn)
    monkeypatch.setattr(anatomy_gate, "_duration", lambda *_: 1.0)
    monkeypatch.setattr(cli, "find_engine", lambda: Path("engine"))
    assert cli._anatomy_frames(project) == 0


# -- what a figure records ------------------------------------------------------------------------------------------
def test_a_toon_pose_records_a_hand_per_arm_it_draws(cv):
    poses = [Pose(0.0, "wide", "flat", "desk"), Pose(1.0, "wide", "flat", "face")]
    groups = toon_cast.figure(cv, cv.comp, toon_cast.BEAR, poses, 2.0)
    assert set(cv.limbs.values()) == {limb for g in groups for limb in paws("bear", g.id)}


def test_a_collage_pose_records_the_hands_it_draws(cv):
    look = collage.LOOKS["gary"]
    [down, free] = collage.figure(
        cv, cv.comp, look, [Pose(0.0, "half", "flat", "down"), Pose(1.0, "half", "flat", "free")], 2.0
    )
    assert set(cv.limbs.values()) == {*paws("gary", down.id), Limb("gary", Side.RIGHT, free.id)}


def test_a_swung_arm_on_a_named_arm_records_its_hand_and_draws_the_same(cv):
    other = Canvas(Scene(version="auto"), font_asset=None)
    toon_bed.swung_arm(cv, cv.comp, (300.0, 700.0), "#a8764f", [(0.0, -60.0)], 0.0, 1.0)
    with anatomy_ledger.on_arm("bear", Side.LEFT):
        g = toon_bed.swung_arm(other, other.comp, (300.0, 700.0), "#a8764f", [(0.0, -60.0)], 0.0, 1.0)
    assert list(other.limbs.values()) == [Limb("bear", Side.LEFT, g.id)]
    assert anatomy_ledger.notes(other) == []
    assert cv.scene.to_bytes() == other.scene.to_bytes()


def test_a_swung_arm_no_character_owns_is_noted(cv):
    toon_bed.swung_arm(cv, cv.comp, (300.0, 700.0), "#a8764f", [(0.0, -60.0)], 0.0, 1.0)
    assert [(n.rule, n.part) for n in anatomy_ledger.notes(cv)] == [(HAND_NO_ARM, "toon-swung-arm")]
    assert cv.limbs == {}


# -- it-autoplayed, as built ----------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def reel():
    sys.path.insert(0, str(EPISODES))
    try:
        import instagram_posts
        import it_autoplayed_data

        return it_autoplayed_data, instagram_posts.PINS[it_autoplayed_data.SLUG]
    finally:
        sys.path.pop(0)


def _two_shot(reel, cv: Canvas):
    from srstudio import sketch
    from srstudio.scripting import at
    from srstudio.toon_sketch import Shot

    data, pins = reel
    sting = at(data.BEATS, "sting")
    app = sketch.Appearance("bruno", sting, sting + 1.4, [])
    back, front = cv.group(cv.comp, "back"), cv.group(cv.comp, "front")
    shot = Shot(
        cv, app, back, front, data.BEATS, data.END, lambda text, size=1.0: len(text) * size * 0.5, versions=pins
    )
    data._two(shot)
    return sting


def test_bruno_s_wow_records_his_raised_arms_beside_his_resting_paws(reel):
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=reel[0].END, background="#101420")
    cv = Canvas(scene, DAYLIGHT, font_asset=None)
    sting = _two_shot(reel, cv)
    bear = [limb for limb in cv.limbs.values() if limb.owner == "bear"]
    assert len(bear) >= 4  # a pair per body drawing, and the two raised arms
    assert {limb.side for limb in bear} == {Side.LEFT, Side.RIGHT}
    assert anatomy_ledger.notes(cv) == []  # every arm in the shot says whose it is
    assert sting > 0


def _engine() -> Path:
    found = os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")
    if not found or not Path(found).exists():
        pytest.skip("set SRSTUDIO_ENGINE to a scene-render binary")
    return Path(found)


def test_bruno_s_wow_is_four_hands_on_the_engine_s_frame(reel, tmp_path):
    engine = _engine()
    data, _ = reel
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=data.END, background="#101420")
    cv = Canvas(scene, DAYLIGHT, font_asset=None)
    figures: list[Figure] = []
    with usage.trace(figures):
        sting = _two_shot(reel, cv)
    path = tmp_path / "wow.scene.xml"
    path.write_bytes(cv.scene.to_bytes())
    up = sting + (data.WOW_LATE + data.WOW_DOWN) / 2
    [shown] = framegraph.evaluate(engine, path, [up])
    drawn = framegraph.drawings(path.read_bytes())
    found = dict(anatomy_gate.extra_hands(shown, drawn, list(cv.limbs.values()), figures))
    assert found.get("bear") == 4
