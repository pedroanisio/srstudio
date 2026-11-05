"""Small Print's explainer shots (ADR 0240): the bar holds as checks that fail before any plate renders, the subject
fills the frame, nothing stands still, words never touch printed faces, and a shot draws as plates in his world."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image
from sr_core.scene import Scene

from srstudio import Canvas
from srstudio import smallprint_lab as lab
from srstudio import smallprint_scene as sc
from srstudio.plates import Camera
from srstudio.plates import digest as plates_digest
from srstudio.smallprint_kit import ScriptError, Stamp, stamp

LENS = Camera((0.0, -300.0, -362.0), (0.0, -290.0, -205.0), 33.0, 4.0)
FOUND = Stamp("FED AT ONE HOUR", "Gee et al., 1994")


def measure(text: str, size: float) -> float:
    return 0.52 * size * len(text)


def _big(m) -> None:
    m.box("feeder", (0.0, -290.0, -205.0), (70.0, 120.0, 10.0))


def _small(m) -> None:
    m.box("feeder", (0.0, -290.0, -205.0), (20.0, 20.0, 10.0))


def _swimming(t: float) -> float:
    return round(math.sin(t * 3.0) * 12.0, 1)


def _parked(t: float) -> float:
    return 0.0


def _pellet(m, pose: float) -> None:
    m.ell("pellet", (pose, -290.0, -215.0), (3.0, 3.0, 3.0))


def shot(still=_big, pose=_swimming, **changes) -> sc.Shot:
    return replace(sc.Shot("test-tank", LENS, "A TEST", still, pose, _pellet, lab.materials, lab.finished), **changes)


def _face_at(y: float):
    def still(m) -> None:
        _big(m)
        m.faceplate("dialface", (-22.0, y, -212.0), 12.0, 12.0)

    return still


# -- the camera and the shot's own rules ------------------------------------------------------------------------------
@pytest.mark.parametrize(("key", "match"), [({"zoom": 1.3}, "zooms 1 to"), ({"zoom": 0.9}, "zooms 1 to"),
                                            ({"dx": math.nan}, "numbers"), ({"at": math.inf}, "numbers")])  # fmt: skip
def test_a_camera_key_out_of_bounds_is_refused(key, match):
    with pytest.raises(ScriptError, match=match):
        sc.Move(**{"at": 0.0, **key})


@pytest.mark.parametrize(
    ("changes", "match"),
    [
        ({"headline": "a test"}, "26 capitals"),
        ({"headline": "A HEADLINE FAR TOO LONG TO READ"}, "26 capitals"),
        ({"headline": "  "}, "has a headline"),
        ({"moves": (sc.Move(2.0), sc.Move(1.0))}, "forward in time"),
        ({"moves": ()}, "forward in time"),
        ({"stamp_top": 100.0}, "a stamp lands from row"),
        ({"stamp_top": 1300.0}, "a stamp lands from row"),
        ({"room": "the-moon"}, "his rooms are"),
    ],
)
def test_a_shot_that_breaks_its_own_rules_is_refused(changes, match):
    with pytest.raises(ScriptError, match=match):
        shot(**changes)


def test_the_camera_eases_between_its_keys_and_holds_outside_them():
    s = shot(moves=(sc.Move(1.0, 1.0, 0.0, 0.0), sc.Move(3.0, 1.2, -40.0, 20.0)))
    assert sc.camera_at(s, 0.0) == (1.0, 0.0, 0.0) and sc.camera_at(s, 9.0) == (1.2, -40.0, 20.0)
    zoom, dx, dy = sc.camera_at(s, 2.0)
    assert (zoom, dx, dy) == pytest.approx((1.1, -20.0, 10.0))
    assert sc.camera_at(s, 1.5)[0] < 1.05  # eased: slow out of the key


def test_the_moving_parts_change_plate_every_step_frames():
    rows = sc.frames(shot(), 1.0, 2.0)
    assert len(rows) == sc.FPS
    poses = [pose for _, pose in rows]
    assert all(poses[k] == poses[k - k % sc.STEP] for k in range(len(poses)))


# -- the bar ----------------------------------------------------------------------------------------------------------
def test_the_share_counts_what_the_shot_explains_and_grows_as_the_camera_pushes_in():
    big, small = shot(), shot(still=_small)
    assert sc.share(big, 0.0) >= sc.SHARE > sc.share(small, 0.0)
    pushed = shot(still=_small, moves=(sc.Move(0.0, 1.0), sc.Move(1.0, 1.25)))
    assert sc.share(pushed, 1.0) > sc.share(pushed, 0.0) * 1.4


def test_a_bare_band_is_rows_nothing_covers_and_words_on_screen_cover_their_rows():
    small = shot(still=_small)
    bare = sc.empty_band(small, 0.0)
    assert bare > sc.BAND
    across = (0.0, 0.0, sc.W, sc.H * 0.45)
    assert sc.empty_band(small, 0.0, words=[across]) < bare
    narrow = (0.0, 0.0, sc.W * 0.05, sc.H * 0.45)  # under BAND_FILL of a row: still bare
    assert sc.empty_band(small, 0.0, words=[narrow]) == pytest.approx(bare)


def test_a_shot_that_stands_still_is_measured_and_one_that_swims_is_not():
    assert sc.longest_still(shot(pose=_parked), 0.0, 3.0) >= 2.9
    assert sc.longest_still(shot(), 0.0, 3.0) < sc.STILL_FOR
    camera = shot(pose=_parked, moves=(sc.Move(0.0, 1.0), sc.Move(3.0, 1.2)))
    assert sc.longest_still(camera, 0.0, 3.0) < sc.STILL_FOR  # the camera's push is motion too


def test_a_printed_face_under_the_headline_clashes_and_one_clear_of_it_does_not():
    head = sc.headline_box(shot(), measure)
    near = shot(still=_face_at(-336.0), printed=frozenset({"dialface"}))
    clear = shot(still=_face_at(-300.0), printed=frozenset({"dialface"}))
    ((_, box),) = sc.printed_boxes(near, 0.0)
    assert box[1] < head[3] + sc.CLEAR_PX and box[0] < head[2]  # the face is where the headline is
    assert sc.clashes(near, None, 0.0, measure, [0.0]) == ["test-tank: at 0.00 s the dialface touches the headline"]
    assert sc.clashes(clear, None, 0.0, measure, [0.0]) == []


def test_after_the_stamp_lands_the_headline_is_gone_and_the_stamp_and_its_chip_count():
    on = sc.words(shot(), FOUND, 2.0, measure)
    assert [name for name, *_ in on] == ["headline", "stamp", "source"]
    (_, head, _, until), (_, stamped, since, _), (_, chip, chip_since, _) = on
    assert until == since == chip_since == 2.0
    assert stamped[1] == pytest.approx(sc.STAMP_TOP, abs=30.0) and chip[1] > stamped[1]
    near = shot(still=_face_at(-336.0), printed=frozenset({"dialface"}))
    found = sc.clashes(near, FOUND, 1.0, measure, [0.0, 1.5])
    assert "test-tank: at 0.00 s the dialface touches the headline" in found
    assert any(f.startswith("test-tank: at 1.50 s the dialface touches the s") for f in found)


def test_the_stamp_lands_on_its_word_or_a_little_after_its_line_never_before_the_shot():
    assert sc.stamp_time(shot(stamp_at=3.2), 2.0, 1.0) == 3.2
    assert sc.stamp_time(shot(stamp_at=0.5), 2.0, 1.0) == 1.0
    assert sc.stamp_time(shot(), 2.0, 1.0) == pytest.approx(2.0 + sc.STAMP_LEAD)
    assert sc.stamp_time(shot(), None, 1.0) == pytest.approx(1.0 + sc.STAMP_LEAD)


@pytest.mark.parametrize(
    ("changes", "first", "last", "stamped", "match"),
    [
        ({"still": _small}, 0.0, 2.0, None, "the subject covers"),
        ({"still": _small}, 0.0, 2.0, None, "bare band"),
        ({"pose": _parked}, 0.0, 2.0, None, "nothing moves for"),
        ({"still": _face_at(-336.0), "printed": frozenset({"dialface"})}, 0.0, 1.0, None, "touches the headline"),
        ({"stamp_at": 1.6}, 0.0, 2.0, FOUND, "the stamp is up 0.40 s"),
    ],
)
def test_a_shot_that_misses_the_bar_is_refused_naming_the_miss(changes, first, last, stamped, match):
    with pytest.raises(ScriptError, match=match):
        sc.check(shot(**changes), first, last, stamped, measure)


def test_a_shot_that_keeps_the_bar_passes():
    sc.check(shot(stamp_at=0.5), 0.0, 2.0, FOUND, measure)


# -- the drawing ------------------------------------------------------------------------------------------------------
class _Renders:
    """Stands in for the engine: one small picture file per plate asked for."""

    def __init__(self, folder: Path) -> None:
        self.folder, self.asked = folder, []

    def plate(self, plate) -> Path:
        self.asked.append(plate)
        path = self.folder / f"plate-{len(self.asked)}.png"
        Image.new("RGBA", (8, 8)).save(path)
        return path


def _drawn(s: sc.Shot, tmp_path: Path, stamped: Stamp | None = FOUND) -> tuple[ET.Element, _Renders]:
    renders = _Renders(tmp_path)
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=3.0)
    cv = Canvas(scene, font_asset="fraunces")
    sc.draw(cv, cv.comp, s, 0.0, 2.0, renders, tmp_path / "project", measure, stamped)
    return ET.fromstring(scene.to_bytes(layout="pretty")), renders


def test_a_shot_draws_his_room_his_worktop_and_a_plate_for_each_pose_with_its_words(tmp_path):
    s = shot(stamp_at=0.5, moves=(sc.Move(0.0, 1.0), sc.Move(2.0, 1.1)))
    root, renders = _drawn(s, tmp_path)
    ids = {e.get("id") for e in root.iter()}
    assert {"test-tank-room-angle", "test-tank-bench-angle"} <= ids
    poses = {pose for _, pose in sc.frames(s, 0.0, 2.0)}
    assert len(renders.asked) == 2 + len(poses)  # room, worktop, one plate per pose
    words = {e.get("text") for e in root.iter() if e.tag.endswith("text")}
    assert {"A TEST", FOUND.text, FOUND.source} <= words
    assert len(list((tmp_path / "project" / "assets" / "rafa").iterdir())) == len(renders.asked)


def test_a_shot_that_misses_the_bar_renders_no_plate(tmp_path):
    with pytest.raises(ScriptError, match="nothing moves"):
        _drawn(shot(pose=_parked), tmp_path, None)
    assert not list(tmp_path.glob("plate-*.png"))


def test_the_room_moves_less_than_the_worktop_as_the_camera_pushes_in(tmp_path):
    root, _ = _drawn(shot(stamp_at=0.5, moves=(sc.Move(0.0, 1.0), sc.Move(2.0, 1.2))), tmp_path)

    def top_zoom(name: str) -> float:
        group = next(e for e in root.iter() if e.get("id") == name)
        return max(float(k.get("value")) for a in group if a.get("property") == "scaleX" for k in a)

    room, bench = top_zoom("test-tank-room-angle"), top_zoom("test-tank-bench-angle")
    assert bench == pytest.approx(1.2) and room == pytest.approx(1.0 + 0.2 * sc.PARALLAX)


def test_two_shots_through_one_lens_share_their_room_plate_as_one_asset(tmp_path):
    renders = _Renders(tmp_path)
    renders.plate = lambda plate, _cache={}: _cache.setdefault(  # one file a plate, as the engine's cache gives
        plates_digest(plate), _Renders.plate(renders, plate)
    )
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=5.0)
    cv = Canvas(scene, font_asset="fraunces")
    first, second = shot(stamp_at=0.5), replace(shot(stamp_at=2.5), panel="test-tank-2")
    sc.draw(cv, cv.comp, first, 0.0, 2.0, renders, tmp_path / "project", measure, FOUND)
    sc.draw(cv, cv.comp, second, 2.0, 4.0, renders, tmp_path / "project", measure, FOUND)
    root = ET.fromstring(scene.to_bytes(layout="pretty"))
    ids = [e.get("id") for e in root.iter() if e.tag.endswith("image")]
    assert ids and len(ids) == len(set(ids))


@pytest.mark.parametrize("finding", [FOUND, Stamp("WEEKS, EVEN MONTHS", "Culum Brown, Live Science, 2021")])
def test_a_stamp_landing_in_the_headline_s_place_never_leaves_the_safe_area_as_it_comes_down(tmp_path, finding):
    """The engine checks a text layer's box as the stamp scales down onto its place, without its turn."""
    root, _ = _drawn(shot(stamp_at=0.5), tmp_path, finding)
    group = next(e for e in root.iter() if (e.get("id") or "").startswith("smallprint-stamp"))
    biggest = max(float(k.get("value")) for a in group if a.get("property") == "scaleY" for k in a)
    text = next(e for e in root.iter() if e.tag.endswith("text") and e.get("text") == finding.text)
    turn = math.radians(abs(float(group.get("rotation"))))
    w, h = float(text.get("width")), float(text.get("height"))
    reach = (w * math.sin(turn) + h * math.cos(turn)) / 2  # the turned text box, as the engine measures it
    assert float(group.get("y")) - biggest * reach >= sc.SAFE_TOP - 1e-6
    assert biggest >= sc.LANDS - 1e-6  # it still comes down onto its place


def test_a_stamp_placed_over_its_own_ceiling_is_refused():
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=3.0)
    cv = Canvas(scene, font_asset="fraunces")
    with pytest.raises(ScriptError, match="over its ceiling"):
        stamp(cv, cv.comp, FOUND, 0.5, 2.0, measure, top=sc.STAMP_TOP, ceiling=sc.SAFE_TOP)


# -- a cut inside a shot, to the one part it is about -----------------------------------------------------------------
CLOSE = Camera((0.0, -290.0, -224.0), (0.0, -290.0, -215.0), 33.0, 4.0)  # a hand's width from the pellet
PELLET = frozenset({"pellet"})


def _nudging(t: float) -> float:
    return round(math.sin(t * 3.0) * 0.6, 2)


def _cut(at: float = 1.0, lens: Camera = CLOSE, **changes) -> sc.Cut:
    return replace(sc.Cut(at, lens, hero=PELLET), **changes)


def test_a_shot_cut_in_two_sees_the_rest_through_the_close_lens():
    s = shot(pose=_nudging, cuts=(_cut(1.0),))
    (a, a0, a1), (b, b0, b1) = sc.pieces(s, 0.0, 2.0)
    assert (a.lens, a0, a1, a.cuts, a.hero) == (LENS, 0.0, 1.0, (), frozenset())
    assert (b.lens, b0, b1, b.cuts, b.hero, b.panel) == (CLOSE, 1.0, 2.0, (), PELLET, "test-tank-1")
    assert b.moves == (sc.Move(1.0),)
    assert sc.pieces(shot(), 0.0, 2.0) == [(shot(), 0.0, 2.0)]


def test_the_part_a_close_shot_is_about_is_measured_alone():
    s = shot(pose=_nudging, cuts=(_cut(1.0),))
    wide, close = (piece for piece, _, _ in sc.pieces(s, 0.0, 2.0))
    assert sc.hero_share(close, 1.5) >= sc.SHARE
    assert sc.hero_share(replace(wide, hero=PELLET), 0.5) < 0.05
    assert sc.hero_share(wide, 0.5) == sc.share(wide, 0.5)  # no hero: the whole subject


@pytest.mark.parametrize(
    ("changes", "stamp_at", "match"),
    [
        ({"cuts": (_cut(1.0, LENS),)}, None, "the pellet covers"),
        ({"cuts": (_cut(2.5),)}, None, "outside the shot"),
        ({"cuts": (_cut(1.0),)}, 0.5, "lands before the last cut"),
    ],
)
def test_a_cut_that_misses_the_bar_is_refused(changes, stamp_at, match):
    with pytest.raises(ScriptError, match=match):
        sc.check(shot(pose=_nudging, stamp_at=stamp_at, **changes), 0.0, 2.0, FOUND if stamp_at else None, measure)


def test_cuts_go_forward_in_time():
    with pytest.raises(ScriptError, match="cuts go forward"):
        shot(cuts=(_cut(1.5), _cut(1.0)))


def test_a_shot_with_a_cut_passes_and_draws_both_sides_with_one_headline(tmp_path):
    s = shot(pose=_nudging, stamp_at=1.0, cuts=(_cut(1.0),))
    sc.check(s, 0.0, 2.0, FOUND, measure)
    root, renders = _drawn(s, tmp_path)
    ids = {e.get("id") for e in root.iter()}
    assert {"test-tank-room-angle", "test-tank-1-room-angle"} <= ids
    assert {p.camera for p in renders.asked} == {LENS, CLOSE}
    texts = [e.get("text") for e in root.iter() if e.tag.endswith("text")]
    assert texts.count("A TEST") == 1 and FOUND.text in texts


# -- a lens among the parts: what is behind it is not in the frame ---------------------------------------------------
INSIDE = Camera((0.0, -290.0, -214.0), (0.0, -290.0, -150.0), 33.0, 4.0)  # past the face at z -212, looking away


def test_a_printed_face_behind_the_lens_touches_no_word_and_covers_nothing():
    behind = shot(still=_face_at(-290.0), printed=frozenset({"dialface"}), lens=INSIDE)
    assert all(name != "dialface" for name, _ in sc.printed_boxes(behind, 0.0))
    assert sc.clashes(behind, FOUND, 0.0, measure, [0.0, 1.0]) == []


def test_a_part_the_lens_stands_inside_counts_only_what_is_in_front_of_it(tmp_path):
    def wall(m) -> None:  # a slab from 4 behind the lens to 20 in front of it, wide enough to fill the view
        m.box("feeder", (0.0, -290.0, -206.0), (400.0, 400.0, 24.0))

    inside = shot(still=wall, pose=_parked, lens=INSIDE)
    assert sc.share(inside, 0.0) > 0.95  # its front, 20 ahead, fills the frame


def test_a_part_wholly_behind_the_lens_covers_none_of_the_frame():
    def behind(m) -> None:
        m.box("feeder", (0.0, -290.0, -240.0), (40.0, 40.0, 10.0))

    def far_pellet(m, pose) -> None:
        m.ell("pellet", (0.0, -290.0, -260.0), (3.0, 3.0, 3.0))

    gone = shot(still=behind, pose=_parked, draw=far_pellet, lens=INSIDE)
    assert sc.share(gone, 0.0) == 0.0
    assert sc.hero_share(replace(gone, hero=frozenset({"pellet"})), 0.0) == 0.0
