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

from srstudio import collage_everyday
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
