"""What a reel's frames must not get wrong, on the reels where a frame got it wrong: a body has two arms, a thing in a
shot stands somewhere it can stand, a holder's hand is the holder's, and two clocks in a room agree."""

import ast
import importlib
import sys
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from types import ModuleType, SimpleNamespace

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
from srstudio.collage_group import Place
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


def test_free_right_leaves_the_screen_right_arm_to_the_scene() -> None:
    look = collage.LOOKS["brent"]
    under, over = collage._arms(look, "free-right")
    both, _ = collage._arms(look, "down")
    assert len(under) * 2 == len(both) and not over
    assert under == both[: len(under)]


def test_a_shoulder_is_on_the_side_asked_for() -> None:
    left, right = collage_everyday.shoulder("brent"), collage_everyday.shoulder("brent", 1)
    assert left[1] == right[1]
    assert left[0] + right[0] == 2 * collage.CX
    assert left[0] < right[0]


def test_eased_follows_keys_and_holds_outside_them() -> None:
    keys = [(1.0, 0.0), (2.0, 10.0)]
    assert collage_everyday.eased(keys, 0.0, "sine-in-out") == 0.0
    assert collage_everyday.eased(keys, 3.0, "sine-in-out") == 10.0
    assert collage_everyday.eased(keys, 1.5, "sine-in-out") == pytest.approx(5.0)
    assert collage_everyday.eased(keys, 1.5, "cubic-in") == pytest.approx(1.25)
    with pytest.raises(collage_everyday.EverydayError):
        collage_everyday.eased(keys, 1.5, "bounce")
    with pytest.raises(collage_everyday.EverydayError):
        collage_everyday.eased([], 1.0, "cubic-in")


def test_frames_runs_each_span_with_both_ends_and_no_repeats() -> None:
    assert collage_everyday.frames((0.0, 0.1), (0.1, 0.2), step=0.05) == [0.0, 0.05, 0.1, 0.15, 0.2]
    with pytest.raises(collage_everyday.EverydayError):
        collage_everyday.frames((1.0, 1.0))


class _Keyed:
    """A canvas of plain groups that keeps what is keyed on them, for an arm's angle and length."""

    def __init__(self) -> None:
        self.keyed: dict[tuple[int, str], list[tuple[float, float]]] = {}
        self.ink = "#000000"

    def uid(self, prefix: str) -> str:
        return prefix

    def group(self, parent: object, id: str, **kw: object) -> SimpleNamespace:
        return SimpleNamespace(**kw)

    def keys(self, node: object, prop: str, values: list[tuple[float, float]], *a: object, **kw: object) -> None:
        self.keyed[(id(node), prop)] = values


def test_reach_keeps_the_arm_on_the_shoulder_and_the_hand_on_its_path(monkeypatch: pytest.MonkeyPatch) -> None:
    drawn: list[object] = []
    monkeypatch.setattr(collage_everyday, "arm", lambda *a, **kw: drawn.append(a[2:]) or SimpleNamespace())
    monkeypatch.setattr(collage_everyday, "draw_shapes", lambda *a: None)
    cv = _Keyed()
    frm = (100.0, 100.0)
    spots = {0.0: (100.0, 400.0), 1.0: (400.0, 100.0), 2.0: (-200.0, 100.0)}
    hand = collage_everyday.reach(cv, object(), "brent", frm, spots.__getitem__, sorted(spots))
    assert drawn
    by_prop = {prop: values for (_, prop), values in cv.keyed.items()}
    assert [v for _, v in by_prop["rotation"]] == pytest.approx([0.0, -90.0, 90.0])
    assert [v for _, v in by_prop["x"]] == [100.0, 400.0, -200.0]
    assert [v for _, v in by_prop["y"]] == [400.0, 100.0, 100.0]
    lengths = {t: collage_everyday.REACH_DRAWN * v for t, v in by_prop["scaleY"]}
    short = 300.0 - collage_everyday.REACH_CUFF
    assert lengths == pytest.approx({0.0: short, 1.0: short, 2.0: short})
    assert hand is not None


def test_reach_refuses_a_hand_on_the_shoulder_and_no_times() -> None:
    with pytest.raises(collage_everyday.EverydayError):
        collage_everyday.reach(_Keyed(), object(), "brent", (0.0, 0.0), lambda t: (0.0, 0.0), [0.0])
    with pytest.raises(collage_everyday.EverydayError):
        collage_everyday.reach(_Keyed(), object(), "brent", (0.0, 0.0), lambda t: (1.0, 1.0), [])


def _shoulder_on_screen(place: Place, who: str, side: int) -> tuple[float, float]:
    (ox, oy), scale = (place.x - 540.0 * place.scale, place.base - 1920.0 * place.scale), place.scale
    x, y = collage_everyday.shoulder(who, side)
    return (ox + x * scale, oy + y * scale)


def _reaches(monkeypatch: pytest.MonkeyPatch, mod: ModuleType) -> dict[str, tuple[float, float]]:
    """Whose arm the reel's scene draws, and from where."""
    drawn: dict[str, tuple[float, float]] = {}

    def reach(cv: object, parent: object, who: str, frm: tuple[float, float], *a: object, **kw: object) -> object:
        drawn[who] = frm
        return SimpleNamespace()

    monkeypatch.setattr(collage_everyday, "reach", reach)
    monkeypatch.setattr(mod, "collage_things", SimpleNamespace(**dict.fromkeys(_THINGS, lambda *a, **kw: None)))
    monkeypatch.setattr(mod.collage_everyday, "tablecloth", lambda *a, **kw: None)
    return drawn


_THINGS = ("fork", "tiny_cup", "receipt", "desk_phone")


@pytest.mark.usefixtures("reels")
def test_the_forks_at_any_news_come_down_on_their_owners_arms(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _data("any_news")
    drawn = _reaches(monkeypatch, mod)
    shot = SimpleNamespace(cv=_Keyed(), app=SimpleNamespace(start=20.0, end=26.8), front=object())
    mod._forks(shot)
    assert drawn == {
        "brent": _shoulder_on_screen(mod.TWO["brent"], "brent", 1),
        "gary": _shoulder_on_screen(mod.TWO["gary"], "gary", -1),
    }


@pytest.mark.usefixtures("reels")
def test_the_two_brothers_at_the_bill_tug_with_their_own_arms(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _data("ill_get_this")
    drawn = _reaches(monkeypatch, mod)
    beat = SimpleNamespace(start=9.0, who="gary", line=None, events=("crunch",), reveal="", name="")
    monkeypatch.setattr(mod, "events", lambda beats, name: [(9.0, beat)])
    shot = SimpleNamespace(cv=_Keyed(), app=SimpleNamespace(start=0.0, end=2.0), beats=[beat], front=object())
    mod._table(shot)
    assert drawn == {
        "gary": _shoulder_on_screen(mod.TABLE["gary"], "gary", 1),
        "omar": _shoulder_on_screen(mod.TABLE["omar"], "omar", -1),
    }


@pytest.mark.usefixtures("reels")
@pytest.mark.parametrize(("reel", "places", "who", "arms"), [
    ("any_news", "TWO", "brent", "free-right"),
    ("any_news", "TWO", "gary", "free"),
    ("ill_get_this", "TABLE", "gary", "free-right"),
    ("ill_get_this", "TABLE", "omar", "free"),
])  # fmt: skip
def test_who_reaches_gives_up_the_posed_arm(reel: str, places: str, who: str, arms: str) -> None:
    mod = _data(reel)
    assert mod.REACHING[who] == arms and who in getattr(mod, places)


@pytest.mark.usefixtures("reels")
def test_brent_slides_the_phone_with_his_own_arm(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _data("fluent")
    drawn = _reaches(monkeypatch, mod)
    cv = _Keyed()
    cv.gate = lambda *a: None
    cv.rect = lambda *a, **kw: None
    mod._slide_arm(cv, object(), 10.0)
    assert drawn == {"brent": _shoulder_on_screen(mod.PLACES["brent"], "brent", 1)}
    assert mod.SLIDING == "free-right"


@pytest.mark.usefixtures("reels")
@pytest.mark.parametrize("reel", ["any_news", "ill_get_this"])
def test_a_speaker_in_the_shot_frees_the_arm_too(reel: str) -> None:
    mod = _data(reel)
    who, arms = next(iter(mod.REACHING.items()))
    app = Appearance(who, 1.0, 3.0, [{"start": 0.0, "eyes": "open", "mouth": "flat", "arms": "hold"}])
    assert [p["arms"] for p in mod._reaching(app).poses] == [arms]


@pytest.mark.usefixtures("reels")
def test_brent_speaking_over_the_slide_frees_the_arm_until_it_lets_go() -> None:
    mod = _data("fluent")
    row = {"eyes": "open", "mouth": "flat"}
    poses = [{"start": 0.0, **row, "arms": "down"}, {"start": 5.0, **row, "arms": "hold"}]
    app = Appearance("brent", 10.0, 17.0, poses)
    freed = mod._sliding(app, 10.0)
    lets_go = mod._speed(10.0)[1] + 0.25 - 10.0
    assert [(p["start"], p["arms"]) for p in freed.poses] == [(0.0, "free-right"), (lets_go, "down"), (5.0, "hold")]
    assert mod._sliding(Appearance("deb", 10.0, 17.0, poses), 10.0).poses == poses
    assert mod._sliding(Appearance("brent", 2.0, 4.0, poses), 10.0).poses == poses


def _calls(tree: ast.Module, function: str, name: str) -> list[ast.Call]:
    body = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function)
    found = (n for n in ast.walk(body) if isinstance(n, ast.Call))
    return [n for n in found if ast.unparse(n.func).split(".")[-1] == name]


def test_the_references_right_arm_stays_behind_the_desk_until_the_hand_is_over_it() -> None:
    tree = ast.parse((EPISODES / "the_reference.py").read_text())
    for function, parent, span in (("cards", "up", "(0.0, ON_DESK)"), ("on_desk", "over", "(ON_DESK, DURATION)")):
        right = [c for c in _calls(tree, function, "reach") if ast.unparse(c.args[3]) == "SHOULDERS[1]"]
        assert [ast.unparse(c.args[1]) for c in right] == [parent]
        gates = _calls(tree, function, "gate")
        assert (parent, f"[{span}]") in [(ast.unparse(c.args[0]), ast.unparse(c.args[1])) for c in gates]
