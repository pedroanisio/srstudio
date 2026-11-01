"""news-money-app: an unbranded money app on Gus's phone, whose button stops working on cue."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, news_inked, news_kit, parts


def measure(text: str, size: float) -> float:
    return len(text) * size * 0.5


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=12.0, background=news_kit.PLUM_DEEP)
    return Canvas(scene, news_kit.NEWS.palette())


def xml(cv: Canvas) -> str:
    return cv.scene.to_bytes(layout="pretty").decode()


def nodes(cv: Canvas) -> dict:
    return {node.get("id"): node for node in ET.fromstring(xml(cv)).iter() if node.get("id")}


def app(cv: Canvas, **over) -> None:
    kwargs = dict(
        title="MY MONEY",
        amount="$11.00",
        action="WITHDRAW",
        refused="SUSPENDED",
        start=2.0,
        end=8.0,
        measure=measure,
        taps=(3.0, 3.6),
        refused_at=4.0,
    )
    news_inked.money_app(cv, cv.comp, **{**kwargs, **over})


def test_the_app_shows_its_balance_for_its_window():
    cv = canvas()
    app(cv)
    drawn = nodes(cv)
    assert (drawn["news-money-app"].get("start"), drawn["news-money-app"].get("end")) == ("2", "8")
    text = xml(cv)
    assert all(word in text for word in ("MY MONEY", "$11.00", "WITHDRAW", "SUSPENDED", "BALANCE"))


def test_the_button_stops_working_at_the_instant_it_is_told_and_stays_stopped():
    cv = canvas()
    app(cv)
    drawn = nodes(cv)
    live, dead = drawn["news-money-app-live"], drawn["news-money-app-refused"]
    assert (live.get("start"), live.get("end")) == ("2", "4")
    assert (dead.get("start"), dead.get("end")) == ("4", "8")


def test_a_button_already_refused_has_no_live_state():
    cv = canvas()
    app(cv, refused_at=2.0, taps=())
    drawn = nodes(cv)
    assert "news-money-app-live" not in drawn and "news-money-app-refused" in drawn


def test_each_tap_is_a_short_ring_on_the_button():
    cv = canvas()
    app(cv)
    drawn = nodes(cv)
    assert [drawn[f"news-money-app-tap-{i}"].get("start") for i in range(2)] == ["3", "3.6"]


def test_a_tap_lands_beside_the_word_and_never_on_it(monkeypatch):
    centre = news_inked.PHONE_X + news_inked.PHONE_W / 2
    half_word = measure("WITHDRAW", news_inked.APP_WORD_SIZE) / 2
    ovals = []
    monkeypatch.setattr(news_inked, "_inked_oval", lambda cv, parent, x, y, rx, ry, fill: ovals.append((x, rx)))
    app(canvas())
    assert len(ovals) == 2
    assert all(abs(x - centre) - rx > half_word for x, rx in ovals)


def test_a_word_too_wide_to_leave_room_for_the_tap_is_refused():
    with pytest.raises(news_kit.NewsKitError):
        app(canvas(), action="WITHDRAW FUNDS N")
    app(canvas(), action="WITHDRAW FUNDS N", taps=())


def test_a_note_arrives_on_its_second_and_stays():
    cv = canvas()
    app(cv, notes=((5.0, "PHASE ONE: BITCOIN"), (6.0, "YOUR PHASE: NO DATE")))
    drawn = nodes(cv)
    assert (drawn["news-money-app-note-1"].get("start"), drawn["news-money-app-note-1"].get("end")) == ("6", "8")


def test_the_part_is_a_registered_graphic_that_needs_no_face():
    record = parts.get("news-money-app").versions[-1]
    assert record.number == 1 and parts.get("news-money-app").kind == "graphic"


@pytest.mark.parametrize(
    "over",
    [
        {"start": 8.0},
        {"refused_at": 1.0},
        {"refused_at": 8.0},
        {"taps": (9.0,)},
        {"notes": ((9.0, "LATE"),)},
        {"notes": ((3.0, "ONE"), (3.5, "TWO"), (4.0, "THREE"), (4.5, "FOUR"))},
        {"notes": ((3.0, "NOTE " * 12),)},
        {"amount": ""},
        {"amount": "$1,234,567,890.00"},
    ],
)
def test_an_app_that_cannot_be_read_or_runs_off_its_window_is_refused(over):
    with pytest.raises(news_kit.NewsKitError):
        app(canvas(), **over)


def test_engagement_bait_stays_off_the_app():
    with pytest.raises(news_kit.NewsKitError):
        app(canvas(), notes=((3.0, "FOLLOW FOR MORE"),))
