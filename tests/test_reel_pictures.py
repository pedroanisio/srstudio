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

from srstudio import collage, collage_everyday
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


def test_nobody_in_the_headphones_aisle_is_there_twice() -> None:
    """The stopped row is a crowd of strangers: the same face twice, or a lead's, reads as a copy, not as a crowd."""
    tree = ast.parse((EPISODES / "headphones.py").read_text())
    shoppers = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "shoppers")
    row = next(n.value for n in ast.walk(shoppers) if isinstance(n, ast.Assign) and ast.unparse(n.targets[0]) == "row")
    assert isinstance(row, ast.List)
    cast = [ast.unparse(person.elts[0]) for person in row.elts if isinstance(person, ast.Tuple)]
    assert len(cast) == len(row.elts) >= 3
    assert len(set(cast)) == len(cast), cast
    assert not {"cast.Customer", "cast.Rosa"} & set(cast)  # Milo and Rosa stand in the same aisle
