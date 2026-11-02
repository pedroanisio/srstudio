"""The paintover proof (examples/paintover_proof): the opening of it-autoplayed on 3D plates, rigs live and unchanged.

The study builds in a project holding the script's timing, a caption font and blank plates. Its plates draw far, back,
rigs, front in every shot, only the far one blurred, and every shape it draws and key it moves is one the approved set's
build draws too, so no rig changed. A plate record that does not describe the plates is refused, the plate script
refuses any srlocations but the pinned commit, and the check that the near edge hides the busts' base fails on a base in
view. The plates themselves need srlocations' interpreter, so `lounge_plates.py` runs outside this suite.
"""

import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree

import numpy as np
import pytest
from PIL import Image

from srstudio import TOON, sketch, toon_rooms, toon_world

ROOT = Path(__file__).resolve().parent.parent
FOLDER = ROOT / "examples" / "paintover_proof"
SCRIPT = FOLDER / "paintover_proof_study.py"
EPISODES = ROOT / "episodes"
FONT = Path(
    "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf"
)  # stands in for Comic Neue: the captions must fit
SPOTS = {"cactus": [900.0, 1270.0], "code": [1030.0, 1410.0]}


@pytest.fixture(scope="module")
def modules():
    sys.path[:0] = [str(FOLDER), str(EPISODES)]
    try:
        import _base_check
        import _lounge_set
        import _span

        import it_autoplayed_data
    finally:
        del sys.path[:2]
    return _lounge_set, _base_check, _span, it_autoplayed_data


@pytest.fixture
def lounge(modules):
    return modules[0]


@pytest.fixture
def base(modules):
    return modules[1]


def record(lounge) -> dict:
    return {
        "seconds": dict.fromkeys(lounge.LAYERS, 1.0),
        "engine": "scene-render",
        "srlocations_commit": lounge.SRLOCATIONS_COMMIT,
        "spots": SPOTS,
        "size": [lounge.WIDTH, lounge.HEIGHT],
    }


def run(root: Path, *flags: str) -> None:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    done = subprocess.run([sys.executable, str(SCRIPT), str(root), *flags], env=env, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr


@pytest.fixture(scope="module")
def project(modules, tmp_path_factory) -> Path:
    assert FONT.exists(), f"the test needs {FONT}"
    lounge, _, _, reel = modules
    root = tmp_path_factory.mktemp("paintover-proof")
    sk = reel.SKETCH
    (root / "assets").mkdir()
    (root / "script.json").write_text(json.dumps(sketch.cues(sk.beats, sk.end, sk.lines)))
    (root / "assets" / "poses.json").write_text(json.dumps(sketch._appearance_data(sk.beats, sk.end)))
    font = root / TOON.font.src
    font.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(FONT, font)
    (root / "plates").mkdir()
    for name in {*lounge.LAYERS, "front"}:
        Image.new("RGBA", (lounge.WIDTH, lounge.HEIGHT)).save(root / "plates" / f"{name}.png")
    (root / "plates" / "registration.json").write_text(json.dumps(record(lounge)))
    run(root, "--silent")
    run(root, "--silent", "--control")
    return root


def scene(project: Path, name: str) -> list[ElementTree.Element]:
    return list(ElementTree.parse(project / f"{name}.scene.xml").iter())


def tag(element: ElementTree.Element) -> str:
    return element.tag.rpartition("}")[2]


def test_the_palette_is_the_toon_set_s(lounge):
    assert (lounge.WALL_TOP, lounge.WALL_MID, lounge.WALL_LOW) == tuple(c for _, c in toon_rooms.LOUNGE_WALL)
    for name in ("STRIPE", "SHELF", "ROUTER", "ROUTER_LED", "LAMP_POLE", "LAMP_SHADE", "CONSOLE"):
        assert getattr(lounge, name) == getattr(toon_rooms, name)
    for name in ("SOFA", "SOFA_LIGHT", "SOFA_SEAM", "PILLOW"):
        assert getattr(lounge, name) == getattr(toon_rooms, name)
    for name in (
        "SOFA_DARK",
        "SOFA_DEEP",
        "TABLE",
        "TABLE_DARK",
        "TABLE_LEG",
        "FLOOR",
        "FLOOR_LINE",
        "RUG",
        "RUG_BAND",
    ):
        assert getattr(lounge, name) == getattr(toon_world, name)


def test_the_paired_frames_lie_in_order_inside_the_span(modules):
    _, _, span, _ = modules
    assert span.PAIRS == tuple(sorted(set(span.PAIRS)))
    assert 0 <= span.PAIRS[0] and span.PAIRS[-1] < span.FRAMES
    assert 6 <= span.FRAMES / span.FPS <= 8


def test_the_study_carries_the_three_plates_and_nothing_else_as_a_picture(project):
    images = {e.attrib["id"]: e.attrib["src"] for e in scene(project, "paintover-proof") if tag(e) == "image"}
    assert images == {"plate-far": "plates/far.png", "plate-back": "plates/back.png", "plate-front": "plates/front.png"}


def test_every_shot_draws_far_back_rigs_front(project):
    order = [
        e.attrib["asset"] if tag(e) == "layer" else "shape"
        for e in scene(project, "paintover-proof")
        if tag(e) == "shape" or (tag(e) == "layer" and e.attrib.get("asset", "").startswith("plate-"))
    ]
    starts = [i for i, name in enumerate(order) if name == "plate-far"]
    assert len(starts) > 1
    for start, stop in zip(starts, [*starts[1:], len(order)], strict=True):
        shot = order[start:stop]
        assert shot[:2] == ["plate-far", "plate-back"]
        front = shot.index("plate-front")
        assert "shape" in shot[2:front], "a rig draws between the back plate and the front plate"


def test_only_the_far_plate_is_blurred(project):
    elements = scene(project, "paintover-proof")
    blurred = [e for e in elements if e.attrib.get("effects") == "paintover-far"]
    assert blurred
    assert {c.attrib["asset"] for e in blurred for c in e if tag(c) == "layer"} == {"plate-far"}
    parents = {child: parent for parent in elements for child in parent}
    for layer in elements:
        if layer.attrib.get("asset") in ("plate-back", "plate-front"):
            assert "effects" not in parents[layer].attrib


def drawn(project: Path, name: str) -> Counter:
    """Every shape as drawn and every animation as keyed, without the ids a build numbers in order."""
    elements = scene(project, name)
    shapes = (frozenset((k, v) for k, v in e.attrib.items() if k != "id") for e in elements if tag(e) == "shape")
    moves = (tuple(tuple(sorted(k.attrib.items())) for k in e) for e in elements if tag(e) == "animate")
    return Counter(shapes) + Counter(moves)


def test_the_rigs_are_the_approved_rigs(project):
    plates, control = drawn(project, "paintover-proof"), drawn(project, "control")
    assert plates and not plates - control


def test_the_engine_validation_of_the_study_has_no_finding(project):
    assert json.loads((project / "qa" / "paintover-proof-validation.json").read_text()) == []


def registration_after(project: Path, tmp_path: Path, change) -> Path:
    data = json.loads((project / "plates" / "registration.json").read_text())
    change(data)
    path = tmp_path / "registration.json"
    path.write_text(json.dumps(data))
    return path


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda d: d.update(guess=True), "expected the fields"),
        (lambda d: d.pop("spots"), "expected the fields"),
        (lambda d: d.update(srlocations_commit="0" * 40), "drawn by srlocations"),
        (lambda d: d.update(size=[1080, 1080]), "the plates are"),
        (lambda d: d["seconds"].pop("near"), "the layers are"),
        (lambda d: d["spots"].pop("code"), "the spots are"),
    ],
)
def test_a_plate_record_that_does_not_describe_the_plates_is_refused(project, tmp_path, change, message):
    path = registration_after(project, tmp_path, change)
    code = (
        "import sys; from pathlib import Path\n"
        f"sys.argv = ['x']; sys.path.insert(0, {str(FOLDER)!r})\n"
        "import paintover_proof_study as study\n"
        "try:\n"
        f"    study.Registration.load(Path({str(path)!r}))\n"
        "except study.PlateError as error:\n"
        "    print(error)\n"
        "else:\n"
        "    raise SystemExit('accepted')\n"
    )
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    done = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr + done.stdout
    assert message in done.stdout


def git(folder: Path, *words: str) -> str:
    who = ("-c", "user.name=t", "-c", "user.email=t@example.com")
    return subprocess.run(["git", "-C", str(folder), *who, *words], capture_output=True, text=True, check=True).stdout


@pytest.fixture
def package(tmp_path) -> Path:
    outside = tmp_path / "studio"
    inside = outside / "srlocations"
    inside.mkdir(parents=True)
    git(outside, "init", "-q")
    (inside / "paint.py").write_text("x = 1\n")
    (outside / "README.md").write_text("one\n")
    git(outside, "add", ".")
    git(outside, "commit", "-qm", "one")
    return inside


def test_the_plate_script_refuses_another_commit(lounge, package):
    with pytest.raises(lounge.PinError, match="pinned to"):
        lounge.pinned(package)


def test_the_plate_script_refuses_an_edited_package_at_the_pin(lounge, package, monkeypatch):
    monkeypatch.setattr(lounge, "SRLOCATIONS_COMMIT", git(package, "rev-parse", "HEAD").strip())
    (package / "paint.py").write_text("x = 2\n")
    with pytest.raises(lounge.PinError, match="uncommitted edits"):
        lounge.pinned(package)


def test_the_plate_script_takes_the_pinned_commit_and_ignores_edits_outside_the_package(lounge, package, monkeypatch):
    commit = git(package, "rev-parse", "HEAD").strip()
    monkeypatch.setattr(lounge, "SRLOCATIONS_COMMIT", commit)
    (package.parent / "README.md").write_text("two\n")
    assert lounge.pinned(package) == commit


def masks(figure_bottom: int = 80, near_top: int = 60, width: int = 100) -> tuple[np.ndarray, np.ndarray]:
    figure, near = np.zeros((100, width), np.uint8), np.zeros((100, width), np.uint8)
    figure[20:figure_bottom, 30:70] = 255
    near[near_top:, :] = 255
    return figure, near


def test_a_base_under_the_near_edge_is_covered(base):
    figure, near = masks()
    assert base.exposed_columns(figure, near) == 0
    assert base.clearance(figure, near) == 19


def test_a_base_above_the_near_edge_is_in_view(base):
    figure, near = masks(near_top=90)
    assert base.exposed_columns(figure, near) == 40
    assert base.clearance(figure, near) < 0


def test_a_near_edge_with_a_gap_shows_the_columns_of_the_gap(base):
    figure, near = masks()
    near[:, 40:45] = 0
    assert base.exposed_columns(figure, near) == 5


def test_a_raised_arm_is_not_a_base(base):
    figure, near = masks()
    near[:, 75:90] = 0
    figure[20:30, 75:90] = 255
    assert base.exposed_columns(figure, near) == 0


def test_no_figure_has_no_base(base):
    _, near = masks()
    empty = np.zeros_like(near)
    assert base.exposed_columns(empty, near) == 0
    assert base.clearance(empty, near) == 100
