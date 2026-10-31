"""What a reel's frames must not get wrong, on the reels where a frame got it wrong: a body has two arms, a thing in a
shot stands somewhere it can stand, a holder's hand is the holder's, and two clocks in a room agree."""

import ast
import importlib
import sys
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from types import ModuleType

import pytest

from srstudio import (
    collage,
    collage_everyday,
    signature,
    stick,
    stick_reel,
    stick_windshield,
    toon_extras,
    toon_house,
    toon_sketch,
)
from srstudio.sketch import Appearance

EPISODES = Path(__file__).resolve().parent.parent / "episodes"
WIDTH, HEIGHT = 1080.0, 1920.0


@pytest.fixture
def reels() -> Iterator[None]:
    sys.path.insert(0, str(EPISODES))
    yield
    sys.path.remove(str(EPISODES))


def _data(name: str) -> ModuleType:
    return importlib.import_module(f"{name}_data")


def _appearance(mod: ModuleType, start: float) -> Appearance:
    return Appearance("gary", start, mod.END, [])


@pytest.mark.usefixtures("reels")
def test_gary_holds_his_wallet_with_the_two_arms_he_has(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _data("ill_get_this")
    reached: list[tuple[float, float]] = []
    monkeypatch.setattr(collage_everyday, "arm", lambda cv, parent, who, frm, to: reached.append(frm))
    monkeypatch.setattr(mod.collage_things, "wallet", lambda *a, **k: None)

    class Shot:
        cv = front = None

    mod._wallet(Shot)
    assert len(reached) == 2
    assert all(0 <= x <= WIDTH and 0 <= y <= HEIGHT for x, y in reached)  # from his elbows, not from under the frame
    assert mod.BEATS[-1].arms == "hold"  # his forearms go behind the wallet: no second pair of hands under it


@pytest.mark.usefixtures("reels")
def test_the_wallet_shot_poses_his_arms_behind_it_whatever_the_recording_says(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _data("ill_get_this")
    drawn: list[str] = []
    monkeypatch.setattr(mod, "solo", lambda cv, parent, app, mouths: drawn.extend(p["arms"] for p in app.poses))
    beats = mod.BEATS
    insert = next(t for t, what in mod.events(beats, "reveal") if what == "insert")
    app = replace(
        _appearance(mod, insert + 1.0), poses=[{"start": 0.0, "eyes": "wide", "mouth": "frown", "arms": "down"}]
    )
    mod.casting(beats, mod.END)(None, None, app, {})
    assert drawn == ["hold"]


@pytest.mark.usefixtures("reels")
def test_the_horses_suitcase_stands_on_the_floor_clear_of_his_muzzle() -> None:
    mod = _data("sorry_what")
    x, y, w, h = mod.CASE
    muzzle_bottom, ledge = 1160.0, 1336.0
    assert y - mod.CASE_HANDLE >= muzzle_bottom
    assert y < ledge <= y + h  # it stands behind the ledge line, not in the air
    assert 0 <= x and x + w <= WIDTH


@pytest.mark.usefixtures("reels")
def test_the_goats_thumb_on_the_phone_is_a_dark_hoof() -> None:
    hand = _data("get_your_mother").HELD["hand"]
    red, green, blue = (int(hand[i : i + 2], 16) for i in (1, 3, 5))
    assert max(red, green, blue) < 128


def test_the_wall_clock_agrees_with_the_chip_when_the_chip_is_up() -> None:
    tree = ast.parse((EPISODES / "one_more_page.py").read_text())
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
    clocks = {
        kw.value.value
        for call in calls
        if call.func.attr == "wall_clock"
        for kw in call.keywords
        if kw.arg == "time" and isinstance(kw.value, ast.Constant)
    }
    chips = {
        n.args[0].value
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "TimeState"
    }
    assert chips <= clocks


def _sleeves(monkeypatch: pytest.MonkeyPatch, mod: ModuleType) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Every arm a shot draws, as (from, to), with the things it holds left out."""
    drawn: list[tuple[tuple[float, float], tuple[float, float]]] = []

    def arm(cv: object, parent: object, who: str, frm: tuple[float, float], to: tuple[float, float], **_: object):
        drawn.append((frm, to))

    monkeypatch.setattr(collage_everyday, "arm", arm)
    return drawn


def test_the_free_pose_leaves_the_screen_left_arm_to_the_scene() -> None:
    look = collage.LOOKS["rosa"]
    assert "free" in collage.ARMS
    under, over = collage._arms(look, "free")
    both, _ = collage._arms(look, "down")
    assert len(under) * 2 == len(both) and not over
    assert under == both[len(under) :]  # the arm that stays is the screen-right one of "down", to the shape


def test_an_upper_arm_has_no_hand_on_it(monkeypatch: pytest.MonkeyPatch) -> None:
    class Canvas:
        uid = staticmethod(lambda _: "g")
        group = staticmethod(lambda parent, name: None)

    counts: list[int] = []
    monkeypatch.setattr(collage_everyday, "draw_shapes", lambda cv, parent, shapes: counts.append(len(shapes)))
    points = (336.0, 1390.0), (262.0, 1590.0)
    collage_everyday.arm(Canvas, None, "rosa", *points)  # type: ignore[arg-type]
    collage_everyday.arm(Canvas, None, "rosa", *points, hand=False)  # type: ignore[arg-type]
    assert 0 < counts[1] < counts[0]


@pytest.mark.parametrize(("who", "thing"), [("rosa", "glass"), ("deb", "fork")])
@pytest.mark.usefixtures("reels")
def test_what_they_hold_at_any_news_is_held_from_the_shoulder(
    monkeypatch: pytest.MonkeyPatch, who: str, thing: str
) -> None:
    mod = _data("any_news")
    drawn = _sleeves(monkeypatch, mod)
    monkeypatch.setattr(mod.collage_things, "fork", lambda *a, **k: None)
    monkeypatch.setattr(mod.collage_things, "wine_glass", lambda *a, **k: None)
    monkeypatch.setattr(collage_everyday, "tablecloth", lambda *a, **k: None)

    class Shot:
        cv = front = None

    mod._holding(Shot, who, thing)
    assert drawn[0][0] == collage_everyday.shoulder(who)
    assert drawn[0][1] == drawn[1][0]  # the elbow joins them
    assert drawn[0][1][1] <= collage_everyday.TABLE_TOP  # above the cloth: no sleeve across the table


@pytest.mark.usefixtures("reels")
def test_any_news_singles_with_something_in_hand_free_the_arm_that_holds_it(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _data("any_news")
    drawn: list[list[str]] = []
    monkeypatch.setattr(mod, "solo", lambda cv, parent, app, mouths: drawn.append([p["arms"] for p in app.poses]))
    draw = mod.casting(mod.BEATS, mod.END)
    pose = {"start": 0.0, "eyes": "open", "mouth": "flat", "arms": "hold"}
    draw(None, None, Appearance("deb", 5.45, 6.5, [pose]), {})
    assert drawn == [["free"]]


@pytest.mark.usefixtures("reels")
def test_rosa_lifts_the_tiny_cup_with_her_own_arm(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _data("ill_get_this")
    drawn = _sleeves(monkeypatch, mod)
    monkeypatch.setattr(mod.collage_things, "tiny_cup", lambda *a, **k: None)
    monkeypatch.setattr(collage_everyday, "tablecloth", lambda *a, **k: None)
    cup = next(t for t, what in mod.events(mod.BEATS, "reveal") if what == "cup")

    class Canvas:
        uid = staticmethod(lambda _: "g")
        group = staticmethod(lambda parent, name: None)
        keys = staticmethod(lambda *a, **k: None)

    class Shot:
        cv, front, beats = Canvas, None, mod.BEATS
        app = Appearance("rosa", cup + 0.5, cup + 0.6, [])

    mod._cup(Shot)
    assert drawn[0][0] == collage_everyday.shoulder("rosa")
    assert drawn[0][1] == drawn[1][0]


@pytest.mark.usefixtures("reels")
def test_rosa_frees_the_arm_with_the_cup_and_keeps_the_flick(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _data("ill_get_this")
    drawn: list[list[str]] = []
    monkeypatch.setattr(mod, "solo", lambda cv, parent, app, mouths: drawn.append([p["arms"] for p in app.poses]))
    cup = next(t for t, what in mod.events(mod.BEATS, "reveal") if what == "cup")
    poses = [{"arms": "down"}, {"arms": "point"}]
    mod.casting(mod.BEATS, mod.END)(None, None, Appearance("rosa", cup + 0.5, cup + 0.6, poses), {})
    assert drawn == [["free", "point"]]


@pytest.mark.usefixtures("reels")
def test_deb_answers_the_phone_with_an_arm_she_stops_hanging(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _data("fluent")
    drawn: list[list[str]] = []
    monkeypatch.setattr(mod, "solo", lambda cv, parent, app, mouths: drawn.append([p["arms"] for p in app.poses]))
    ear = next(t for t, what in mod.events(mod.BEATS, "reveal") if what == "ear")
    mod.casting(mod.BEATS, mod.END)(None, None, Appearance("deb", ear, ear + 1.0, [{"arms": "down"}]), {})
    assert drawn == [["free"]]
    lift = next(t for t, what in mod.events(mod.BEATS, "reveal") if what == "lift")
    lineup = mod._lineup(mod.BEATS, mod.END)
    assert lineup.reactions["deb"][-1]["arms"] == "free"
    assert lineup.reactions["deb"][-1]["start"] > lift  # she keeps the arm until the one with the handset comes in
    assert collage_everyday.shoulder("deb") == mod.SHOULDER_CLOSE


def _seen(framing: tuple, x: float, y: float) -> bool:
    """Whether a stick set's point lands inside the frame under ``((fx, fy), zoom, (tx, ty))``."""
    (fx, fy), zoom, (tx, ty) = framing
    return 0 <= tx + zoom * (x - fx) <= WIDTH and 0 <= ty + zoom * (y - fy) <= HEIGHT


def test_third_snore_shows_its_marks_in_every_framing() -> None:
    sys.path.insert(0, str(EPISODES))
    try:
        audio = importlib.import_module("third_snore_audio")
    finally:
        sys.path.remove(str(EPISODES))
    x, y = audio.MARKS_AT
    for framing in (audio.CLOSE_FROM, audio.CLOSE_TO, audio.WIDE):
        assert _seen(framing, x, y)
        assert _seen(framing, x, y - 152.0 * audio.MARKS_SCALE)
        assert _seen(framing, *audio.CODE_AT)
        assert _seen(framing, audio.CODE_AT[0] + signature.text_width("SR-1028", audio.CODE_H), audio.CODE_AT[1])
        assert not _seen(framing, 330.0, 1150.0), "the studio's own cactus is out of every shot of the bed"


@pytest.mark.usefixtures("reels")
def test_moms_plate_stands_clear_of_the_cactus_and_she_sits_on_the_ledge() -> None:
    mod = _data("call_your_mother")
    scale, _ = mod.FIGURES["cat"]
    assert scale == 1.0, "the trace ends at the desk's edge and roughens when enlarged: a larger cat floats over it"
    plate_right = mod.PLATE_AT[0] + 104.0
    pot_left = 548.0 - 36.0 * 0.7
    assert plate_right + 8.0 <= pot_left


@pytest.mark.usefixtures("reels")
def test_book_a_tables_two_stand_on_legs_and_the_towel_stays_on_her_shoulder() -> None:
    mod = _data("book_a_table")
    hem = mod.PLACES["deb"].base
    for hip, ankle in mod.DEB_LEGS:
        assert hip[1] <= hem < ankle[1] <= HEIGHT, "her legs run from under the hem to the floor"
    for hip, ankle in mod.PRIYA_LEGS:
        assert hip[1] < mod.STOOL[1] + 0.2 * mod.STOOL[2] and ankle[1] >= HEIGHT, "behind the seat, out of the frame"
    towel, place = mod.TOWEL_CLOSE, mod.PLACES["deb"]
    x0, y0 = place.transform()
    assert towel["x"] * place.scale + x0 == pytest.approx(mod.TOWEL["x"], abs=0.1)
    assert towel["y"] * place.scale + y0 == pytest.approx(mod.TOWEL["y"], abs=0.1)
    assert towel["w"] * place.scale == pytest.approx(mod.TOWEL["w"], abs=0.1)
    assert towel["h"] * place.scale == pytest.approx(mod.TOWEL["h"], abs=0.1)


@pytest.mark.usefixtures("reels")
def test_the_baby_monitor_stands_on_the_counter_and_the_mitts_have_arms() -> None:
    mod = _data("baby_monitor")
    door_frame_left = mod.DOOR["at"][0] - 14.0
    assert mod.MONITOR["at"][0] + 36.0 * mod.MONITOR["scale"] <= door_frame_left
    mitts = {side: mod.DISH["at"][0] + side * 196.0 * mod.DISH["scale"] for side in (-1, 1)}
    for shoulder, hand, side in mod.ARMS:
        assert 0 < shoulder[0] < WIDTH and shoulder[1] < hand[1], "from her body, down to the dish"
        assert hand[0] * 592.0 / 1080.0 == pytest.approx(mitts[side], abs=40.0)


def test_more_tireds_marks_clear_the_card_in_every_framing() -> None:
    sys.path.insert(0, str(EPISODES))
    try:
        audio = importlib.import_module("more_tired_audio")
    finally:
        sys.path.remove(str(EPISODES))
    (fx, fy), zoom, (tx, ty) = audio.CAMERA
    pushed = ((fx, fy), audio.OPENING_ZOOM, (tx, ty))
    for framing in (audio.CAMERA, pushed):
        x, y = audio.MARKS_AT
        assert _seen(framing, x, y)
        top = y - 152.0 * audio.MARKS_SCALE
        assert _seen(framing, x, top) and ty + framing[1] * (top - fy) > stick.CARD[1] + stick.CARD[3]
        assert _seen(framing, *audio.CODE_AT)
        assert _seen(framing, audio.CODE_AT[0] + signature.text_width("SR-1028", audio.CODE_H), audio.CODE_AT[1])


def _luminance(colour: str) -> float:
    r, g, b = (int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def test_turn_this_cars_code_reads_on_the_hood_above_the_captions_scrim() -> None:
    sys.path.insert(0, str(EPISODES))
    try:
        audio = importlib.import_module("turn_this_car_audio")
    finally:
        sys.path.remove(str(EPISODES))
    x, y, height, colour = audio.CODE
    assert 1462 < y < stick_reel.WORDS_Y - 60 and height >= 14
    assert abs(_luminance(colour) - _luminance(stick_windshield.BODY_LIGHT)) > 0.35


def test_any_questions_code_is_seen_under_the_push_and_clear_of_the_folder() -> None:
    sys.path.insert(0, str(EPISODES))
    try:
        audio = importlib.import_module("any_questions_audio")
    finally:
        sys.path.remove(str(EPISODES))
    right, y, height = audio.CODE
    left = right - signature.text_width("SR-1028", height)
    for scale, offset in ((1.0, 0.0), (1.324, -15.0)):
        assert 0.0 <= offset + scale * left and offset + scale * right <= 1080.0
    assert y + height <= audio.FOLDER[1] - 150.0  # the folder's top edge, open


@pytest.mark.usefixtures("reels")
def test_the_steamed_frog_stands_behind_the_ledge_and_hides_the_shelf() -> None:
    mod = _data("shower_argument")
    base = mod.GHOST_AT[1] + mod.GHOST_SCALE * (toon_sketch.SEAT[1] - toon_extras.SEAT[1])
    assert base >= toon_house.LEDGE_TOP
    assert mod.GHOST_OPACITY >= 0.7
