"""news-forecast-map: an invented county in the sun, one pin, and a cloud that finds it."""

from __future__ import annotations

import math
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


def nodes(cv: Canvas) -> dict:
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty").decode())
    return {node.get("id"): node for node in root.iter() if node.get("id")}


def forecast(cv: Canvas, **over) -> None:
    kwargs = dict(
        title="FORECAST",
        pin="HIM",
        counter="DRY DAYS",
        counts=((2.0, "63"), (9.0, "64")),
        start=2.0,
        end=10.0,
        measure=measure,
        rain=(4.0, 8.0),
    )
    news_inked.forecast_map(cv, cv.comp, **{**kwargs, **over})


def test_the_map_is_up_for_its_window():
    cv = canvas()
    forecast(cv)
    group = nodes(cv)["news-forecast-map"]
    assert (group.get("start"), group.get("end")) == ("2", "10")


def test_the_cloud_comes_and_goes_when_it_is_told():
    cv = canvas()
    forecast(cv)
    cloud = nodes(cv)["news-forecast-map-cloud"]
    assert (cloud.get("start"), cloud.get("end")) == ("4", "8")


def test_the_cloud_ends_over_the_pin():
    cv = canvas()
    forecast(cv)
    xml = ET.tostring(nodes(cv)["news-forecast-map-cloud"], encoding="unicode")
    landing = news_inked.PHONE_X + news_inked.FORECAST_PIN[0]
    assert f"{landing:g}" in xml


def test_it_rains_only_once_the_cloud_has_arrived():
    cv = canvas()
    forecast(cv)
    rain = nodes(cv)["news-forecast-map-rain"]
    assert float(rain.get("start")) == pytest.approx(4.0 + news_inked.FORECAST_DRIFT)
    assert float(rain.get("end")) == pytest.approx(8.0)


def test_each_count_holds_until_the_next():
    cv = canvas()
    forecast(cv)
    first, second = nodes(cv)["news-forecast-map-count-0"], nodes(cv)["news-forecast-map-count-1"]
    assert (first.get("start"), first.get("end")) == ("2", "9")
    assert (second.get("start"), second.get("end")) == ("9", "10")


def test_a_dry_county_has_no_cloud():
    cv = canvas()
    forecast(cv, rain=None)
    assert "news-forecast-map-cloud" not in nodes(cv)


def test_it_draws_at_least_a_map_of_suns():
    cv = canvas()
    forecast(cv)
    assert len(news_inked.FORECAST_SUNS) >= 5


@pytest.mark.parametrize(
    "over",
    [
        {"rain": (1.0, 8.0)},
        {"rain": (4.0, 11.0)},
        {"rain": (8.0, 4.0)},
        {"rain": (4.0, 4.5)},
        {"counts": ()},
        {"counts": ((3.0, "63"),)},
        {"counts": ((2.0, "63"), (2.0, "64"))},
        {"counts": ((2.0, "63"), (10.5, "64"))},
        {"title": "W" * 80},
        {"pin": ""},
        {"pin": "W" * 60},
        {"counter": "W" * 80},
        {"counts": ((2.0, "W" * 40),)},
    ],
)
def test_a_map_that_cannot_be_read_stops_the_build(over):
    with pytest.raises(news_kit.NewsKitError):
        forecast(canvas(), **over)


def test_the_show_refuses_its_banned_copy_on_the_map():
    with pytest.raises(news_kit.NewsKitError):
        forecast(canvas(), pin="LINK IN BIO")


def test_a_span_that_is_not_one_stops_the_build():
    with pytest.raises(news_kit.NewsKitError):
        forecast(canvas(), start=5.0, end=5.0)


def test_the_part_is_registered_and_approved():
    versions = parts.get("news-forecast-map").versions
    assert [(v.number, v.status) for v in versions] == [(1, "approved")]


def test_every_sun_stays_on_land():
    corners = news_inked.FORECAST_COAST
    for sx, sy in news_inked.FORECAST_SUNS:
        for (ax, ay), (bx, by) in zip(corners, (*corners[1:], corners[0]), strict=True):
            along = max(
                0.0, min(1.0, ((sx - ax) * (bx - ax) + (sy - ay) * (by - ay)) / ((bx - ax) ** 2 + (by - ay) ** 2))
            )
            away = math.hypot(sx - (ax + along * (bx - ax)), sy - (ay + along * (by - ay)))
            assert away > news_inked.FORECAST_REACH, ((sx, sy), (ax, ay))


def test_no_sun_touches_the_pin_or_its_name():
    px, py = news_inked.FORECAST_PIN
    for sx, sy in news_inked.FORECAST_SUNS:
        reach = news_inked.FORECAST_REACH
        apart = sx + reach < px - 70.0 or sx - reach > px + 70.0 or sy + reach < py - 100.0 or sy - reach > py + 70.0
        assert apart, (sx, sy)


def test_the_map_covers_the_banners_word():
    cv = canvas()
    forecast(cv)
    rest = nodes(cv)["news-forecast-map-rest"]
    assert (rest.get("start"), rest.get("end")) == ("2", "10")
