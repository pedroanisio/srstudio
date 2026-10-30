"""The Stick car (location, driving poses, passenger seat, laptop, phone) and the word-by-word captions."""

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, registry, stick, stick_car
from support.stick_car import canvas


def xml(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def keys_of(root: ET.Element, prop: str) -> list[list[tuple[float, float]]]:
    return [
        [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        for a in root.iter("animate")
        if a.get("property") == prop
    ]


def test_the_car_masks_the_scenery_to_its_windows_and_scrolls_it_left():
    cv = canvas()
    stick_car.car(cv, cv.comp, 2.0, scroll=stick_car.Scroll(speed=500))
    root = xml(cv)
    masks = list(root.iter("mask"))
    assert len(masks) == 1 and masks[0].get("type") == "path"
    assert stick_car.SIDE_WINDOW in masks[0].get("path") and stick_car.WINDSHIELD in masks[0].get("path")
    moves = keys_of(root, "x")
    assert [(0.0, 0.0), (2.0, -1000.0)] in moves  # the roadside at the full speed
    assert [(0.0, 0.0), (2.0, -180.0)] in moves  # the hills at their share of it
    still = canvas()
    stick_car.car(still, still.comp, 2.0, scroll=stick_car.Scroll(speed=0))
    assert keys_of(xml(still), "x") == []  # a parked car's scenery does not move


def test_far_layers_are_out_of_focus_and_near_ones_motion_blurred_drawn_far_to_near():
    cv = canvas()
    stick_car.car(cv, cv.comp, 2.0)
    root = xml(cv)
    blurs = {e.get("id"): float(e.get("radius")) for e in root.iter("effect") if e.get("type") == "blur"}
    moving = [g for g in root.iter("group") if g.find("animate[@property='x']") is not None]
    order = [g.get("effects") or g.get("motionBlur") for g in moving]
    assert order[:3] == ["car-far-4", "car-far-3", "car-far-2"]  # clouds, mountains, hills: sharper as they near
    assert [blurs[o] for o in order[:3]] == [4, 3, 2]
    assert order[3:] == ["on", "on", "on"]  # the middle row, the roadside and the rail blur with their motion
    lifted = [g for g in root.iter("group") if g.get("effects") == "car-lift"]
    assert len(lifted) == 3  # the armrest, the driver's seat and the dashboard cast shadows


def test_an_oncoming_car_crosses_the_window_once_at_its_time():
    cv = canvas()
    stick_car.car(cv, cv.comp, 3.0, passing=(1.5,))
    root = xml(cv)
    (car,) = [g for g in root.iter("group") if g.get("shutterAngle") == "300"]
    (x,) = keys_of(car, "x")
    assert x[0][1] == cv.width and x[-1][1] == -520  # from off the right edge to off the left
    left = x[0][1] + (x[-1][1] - x[0][1]) * (1.5 - x[0][0]) / (x[-1][0] - x[0][0])
    assert left + 260 == pytest.approx(cv.width / 2)  # its middle passes the window's middle at its time
    with pytest.raises(stick.StickDataError, match="passing car"):
        stick_car.car(canvas(), None, 1.0, passing=(1.5,))


def test_a_close_up_can_defocus_the_whole_country_behind_the_glass():
    cv = canvas()
    stick_car.car(cv, cv.comp, 2.0, defocus=9)
    root = xml(cv)
    effects = {e.get("id"): e for e in root.iter("effect")}
    glass = next(g for g in root.iter("group") if g.find("mask") is not None)
    riding = [g for g in glass if g.tag == "group"][0]
    (name,) = riding.get("effects").split()
    assert effects[name].get("type") == "blur" and float(effects[name].get("radius")) == 9
    sharp = canvas()
    stick_car.car(sharp, sharp.comp, 2.0)
    glass = next(g for g in xml(sharp).iter("group") if g.find("mask") is not None)
    assert [g for g in glass if g.tag == "group"][0].get("effects") is None
    for bad in (-1, math.nan, math.inf):
        with pytest.raises(stick.StickDataError, match="defocus"):
            stick_car.car(canvas(), None, 2.0, defocus=bad)


def test_the_trees_cover_the_window_for_the_whole_shot():
    cv = canvas()
    end, speed = 3.0, 600
    stick_car.car(cv, cv.comp, end, scroll=stick_car.Scroll(speed=speed, offset=90))
    root = xml(cv)
    trunks = [float(s.get("x")) for s in root.iter("shape") if s.get("fill") == stick_car.TRUNK]
    assert min(trunks) < 0 and max(trunks) > cv.width + speed * end - stick_car.TREE_GAP


@pytest.mark.parametrize(
    "end, scroll, match",
    [
        (0, stick_car.Scroll(), "positive shot length"),
        (math.inf, stick_car.Scroll(), "positive shot length"),
        (1.0, stick_car.Scroll(speed=-1), "scroll"),
        (1.0, stick_car.Scroll(offset=math.nan), "scroll"),
    ],
)
def test_a_car_shot_it_cannot_draw_is_refused(end, scroll, match):
    with pytest.raises(stick.StickDataError, match=match):
        stick_car.car(canvas(), None, end, scroll=scroll)


KEYS = [stick.RigKey(0, "drive"), stick.RigKey(0.5, "grip"), stick.RigKey(1.0, "one-hand"), stick.RigKey(1.5, "turn")]


def test_dev_drives_with_his_hands_on_the_rim():
    cv = canvas()
    keys = KEYS
    stick.rig(cv, cv.comp, keys, 2.0, poses=stick_car.DRIVING)
    on_rim = [(name, i) for name in ("drive", "grip") for i in (0, 1)] + [("one-hand", 1), ("turn", 0)]
    for name, i in on_rim:
        near = stick_car.DRIVING[name].hands[i]
        # the rim is an ellipse of half-axes 40 x 170 about (690, 1060), turned -22 degrees: the hand lies on it
        a = math.radians(22)
        dx, dy = near[0] - 690, near[1] - 1060
        u, v = dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)
        assert (u / 40) ** 2 + (v / 170) ** 2 == pytest.approx(1, abs=0.05), name
    with pytest.raises(stick.StickDataError, match="unknown pose"):
        stick.rig(canvas(), None, [stick.RigKey(0, "type-a")], 1.0, poses=stick_car.DRIVING)


def test_the_cockpit_belts_each_pose_and_shades_the_cabin_but_not_the_glass():
    cv = canvas()
    stick_car.cockpit(cv, cv.comp, KEYS, 2.0, scroll=stick_car.Scroll(speed=400))
    root = xml(cv)
    gates = [g for g in root.iter("group") if g.get("effects") == "car-lift" and g.find("animate") is not None]
    assert len(gates) == 4  # one belt per key, each shown for its key's span
    (shade,) = [g for g in root.iter("group") if g.get("blend") == "multiply" and g.find("mask") is not None]
    mask = shade.find("mask")
    assert mask.get("invert") == "true" and stick_car.SIDE_WINDOW in mask.get("path")
    assert keys_of(shade, "x") == [[(0.0, 0.0), (2.0, -800.0)]]  # the shadows pass at the roadside speed
    with pytest.raises(stick.StickDataError, match="unknown pose"):
        stick_car.cockpit(canvas(), None, [stick.RigKey(0, "type-a")], 1.0)
    with pytest.raises(stick.StickDataError, match="scroll"):
        stick_car.cockpit(canvas(), None, KEYS, 2.0, scroll=stick_car.Scroll(speed=-1))


def test_the_ride_bobs_within_its_amplitude_the_same_every_time():
    def bob(**kw):
        cv = canvas()
        g = cv.group(cv.comp, "body", y=40)
        stick_car.ride(cv, g, 2.0, **kw)
        return keys_of(xml(cv), "y")

    (once,) = bob(amplitude=3)
    assert bob(amplitude=3) == [once] and bob(amplitude=3, phase=1.0) != [once]
    assert once[0][0] == 0 and once[-1][0] >= 2.0 and len(once) == 25  # 12 steps a second
    assert all(37 <= v <= 43 for _, v in once) and len({v for _, v in once}) > 10
    assert bob(amplitude=0) == []
    for kw in (dict(amplitude=-1), dict(step=0), dict(phase=math.nan)):
        with pytest.raises(stick.StickDataError, match="ride"):
            bob(**kw)


def test_the_seat_leaves_the_drivers_head_clear():
    cv = canvas()
    stick_car.seat(cv, cv.comp)
    head = stick_car.DRIVING["drive"].head
    assert head[0] - stick.HEAD_R > 248  # the seat back's right edge
    assert stick_car.CUSHION < stick.WORD_Y  # props on the cushion stand above the word captions


def test_the_laptop_shows_sent_mail_and_its_count():
    cv = canvas()
    g = stick_car.laptop(cv, cv.comp, 450, 1290, title="Sent", rows=("Re: a", "Re: b"), badge="40", scale=1.35)
    root = xml(cv)
    texts = [t.get("text") for t in root.iter("text")]
    assert texts == ["Sent", "40", "Re: a", "Re: b"]
    node = root.find(f".//*[@id='{g.id}']")
    assert (node.get("x"), node.get("y"), node.get("scaleX")) == ("450", "1290", "1.35")


@pytest.mark.parametrize(
    "kw, match",
    [
        (dict(title=" "), "title"),
        (dict(rows=()), "1 to 4"),
        (dict(rows=("a",) * 5), "1 to 4"),
        (dict(rows=("a", " ")), "non-empty"),
        (dict(scale=0), "scale"),
    ],
)
def test_a_laptop_screen_it_cannot_show_is_refused(kw, match):
    base = dict(title="Sent", rows=("Re: a",))
    with pytest.raises(stick.StickDataError, match=match):
        stick_car.laptop(canvas(), None, 0, 0, **{**base, **kw})


def test_the_phone_buzzes_at_each_time_with_marks_and_holds_still_otherwise():
    cv = canvas()
    stick_car.phone(cv, cv.comp, sender="Boss", text="One more thing...", buzz=(0.0, 0.4))
    root = xml(cv)
    assert {"Boss", "One more thing...", "now"} <= {t.get("text") for t in root.iter("text")}
    (shake,) = keys_of(root, "x")
    x0 = stick_car.MOUNT[0]
    assert shake[0] == (0.0, x0) and shake[-1] == (0.65, x0) and min(v for _, v in shake) == x0 - 7
    gates = [a for a in root.iter("animate") if a.get("property") == "opacity"]
    assert len(gates) == 2  # one set of buzz marks per buzz
    quiet = canvas()
    stick_car.phone(quiet, quiet.comp, sender="Boss", text="Hi")
    assert keys_of(xml(quiet), "x") == []


@pytest.mark.parametrize(
    "kw, match",
    [
        (dict(sender=""), "sender"),
        (dict(text=" "), "text"),
        (dict(buzz=(0.5, 0.2)), "in order"),
        (dict(buzz=(-1,)), "non-negative"),
    ],  # fmt: skip
)
def test_a_phone_it_cannot_show_is_refused(kw, match):
    with pytest.raises(stick.StickDataError, match=match):
        stick_car.phone(canvas(), None, **{**dict(sender="Boss", text="Hi"), **kw})


def luminance(color: str) -> float:
    c = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def ratio(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)))
    return (lb + 0.05) / (la + 0.05)


def test_the_screens_small_text_contrasts_with_its_ground_with_room_for_antialiasing():
    # at 15 to 22 px the antialiased glyphs measure well under their nominal contrast: ask 7:1 of the colours
    cv = canvas()
    stick_car.laptop(cv, cv.comp, 400, 1300, title="Sent", rows=("a",), badge="40")
    stick_car.phone(cv, cv.comp, sender="Boss", text="hi")
    texts = {t.get("text"): t.get("color") for t in xml(cv).iter("text")}
    assert ratio(texts["40"], stick_car.BADGE) >= 7
    assert ratio(texts["now"], "#ffffff") >= 7


def test_text_props_need_the_caption_font():
    for draw in (
        lambda cv: stick_car.laptop(cv, cv.comp, 0, 0, title="Sent", rows=("a",)),
        lambda cv: stick_car.phone(cv, cv.comp, sender="Boss", text="Hi"),
        lambda cv: stick.words(cv, cv.comp, [stick.Line(0, 1, "hi", 100)]),
    ):
        with pytest.raises(ValueError, match="font"):
            draw(canvas(font=None))


# -- word captions --------------------------------------------------------------------------------------------
@dataclass
class Take:
    start: float
    end: float
    words: list = field(default_factory=list)


def test_word_cues_run_each_word_to_the_next_and_let_the_last_linger_inside_its_take():
    takes = [
        Take(
            1.0,
            2.6,
            [
                {"text": "Repeat", "start": 0.0, "end": 0.3},
                {"text": "after", "start": 0.35, "end": 0.6},
                {"text": "me.", "start": 0.62, "end": 0.9},
            ],
        ),  # fmt: skip
        Take(2.6, 3.0, []),  # an effect: no words
        Take(3.0, 3.5, [{"text": "Now!", "start": 0.1, "end": 0.4}, {"text": "…", "start": 0.4, "end": 0.45}]),
    ]
    cues = stick.word_cues(takes)
    assert [(c.start, c.end, c.text) for c in cues] == [
        (1.0, 1.35, "Repeat"),
        (1.35, 1.62, "after"),
        (1.62, 2.2, "me"),
        (3.1, 3.5, "Now"),  # the linger stops at the take's end; the bare ellipsis is no word
    ]
    assert all(c.size == stick.WORD_SIZE for c in cues)
    assert [c.end for c in stick.word_cues(takes[:1], linger=0)] == [1.35, 1.62, 1.9]
    with pytest.raises(stick.StickDataError, match="linger"):
        stick.word_cues(takes, linger=-0.1)
    with pytest.raises(stick.StickDataError, match="ends before it starts"):
        words = [{"text": "a", "start": 0.5, "end": 0.6}, {"text": "b", "start": 0.4, "end": 0.7}]
        stick.word_cues([Take(0, 1, words)])


def test_a_word_too_quick_to_read_joins_the_next_words_of_its_take_while_they_fit():
    words = [
        {"text": "work", "start": 0.0, "end": 0.15},
        {"text": "stays", "start": 0.16, "end": 0.3},
        {"text": "at", "start": 0.32, "end": 0.4},
        {"text": "work.", "start": 0.42, "end": 0.7},
        {"text": "Absolutely", "start": 0.8, "end": 1.0},
        {"text": "unbelievably", "start": 0.9, "end": 1.2},
    ]
    takes = [Take(5.0, 6.5, words), Take(6.5, 7.0, [{"text": "Go", "start": 0.0, "end": 0.1}])]
    width = len  # one unit a character: "work stays" is 10 wide
    cues = stick.word_cues(takes, min_seconds=0.3, width=width, max_width=10)
    assert [(c.start, c.end, c.text) for c in cues] == [
        (5.0, 5.32, "work stays"),  # 0.16 s alone: joined by the next word, then shown 0.32 s
        (5.32, 5.8, "at work"),
        (5.8, 5.9, "Absolutely"),  # the next word does not fit beside it: shown alone, however briefly
        (5.9, 6.5, "unbelievably"),  # the last word lingers, never past its take (min_seconds never crosses one)
        (6.5, 6.9, "Go"),
    ]
    assert stick.word_cues(takes) == stick.word_cues(takes, min_seconds=0)  # no minimum: one word a cue
    with pytest.raises(stick.StickDataError, match="width"):
        stick.word_cues(takes, min_seconds=0.3)
    with pytest.raises(stick.StickDataError, match="min_seconds"):
        stick.word_cues(takes, min_seconds=-1, width=width)


def test_words_draw_each_word_as_one_outlined_text_over_a_scrim_that_fades_with_each_run_of_words():
    cv = canvas()
    cues = [stick.Line(0.5, 0.9, "drive", 118), stick.Line(0.9, 1.4, "home", 118), stick.Line(3.0, 3.3, "now", 118)]
    stick.words(cv, cv.comp, cues)
    root = xml(cv)
    texts = [t for t in root.iter("text") if t.get("text") in ("drive", "home", "now")]
    # one layer per word: the contrast check judges every text layer on its own, and an ink outline layer of its
    # own is ink measured against the scene
    assert len(texts) == 3
    assert all(t.get("color") == cv.white and t.get("strokeColor") == cv.ink for t in texts)
    scrims = [r for r in root.iter("shape") if r.get("fill") == "url(#stick-word-scrim)"]
    assert len(scrims) == 1
    scrim = next(g for g in root.iter("group") if scrims[0] in list(g))
    first_word = next(g for g in root.iter("group") if any(x.tag == "layer" for x in g))
    assert list(root.find("composition")).index(scrim) < list(root.find("composition")).index(first_word)
    fade = stick.SCRIM_FADE
    assert keys_of(scrim, "opacity") == [[(0, 0), (0.5 - fade, 0), (0.5, 1), (1.4, 1), (1.4 + fade, 0),
                                          (3.0 - fade, 0), (3.0, 1), (3.3, 1), (3.3 + fade, 0)]]  # fmt: skip
    pops = keys_of(root, "scaleX")
    assert [k[1][0] for k in pops] == [0.5, 0.9, 3.0]  # each pop starts with its word


def test_a_scrim_for_words_from_the_first_frame_is_up_from_the_first_frame():
    cv = canvas()
    stick.words(cv, cv.comp, [stick.Line(0, 0.4, "go", 118)])
    scrim = next(g for g in xml(cv).iter("group") if any(r.get("fill") == "url(#stick-word-scrim)" for r in g))
    assert keys_of(scrim, "opacity") == [[(0, 1), (0.4, 1), (0.4 + stick.SCRIM_FADE, 0)]]


def test_scrims_that_draw_different_bands_get_different_gradients_and_named_peaks_keep_their_names():
    cv = canvas()
    for peak in (0.5, 0.504, 0.502, 0.9, stick.SCRIM_PEAK):
        stick.words(cv, cv.comp, [stick.Line(0, 1, "hi", 118)], scrim=peak)
    fills = [r.get("fill") for r in xml(cv).iter("shape") if (r.get("fill") or "").startswith("url(#stick-word-scrim")]
    assert fills == [
        "url(#stick-word-scrim-50)",
        "url(#stick-word-scrim-50-81)",  # 0.504 is alpha 0x81, not the 0x80 of 0.50
        "url(#stick-word-scrim-50)",  # 0.502 draws 0.50's band, so it shares its gradient
        "url(#stick-word-scrim-90)",
        "url(#stick-word-scrim)",
    ]
    bands = {g.get("id"): g.findall("stop")[1].get("color") for g in xml(cv).iter("linearGradient")}
    assert bands["stick-word-scrim-50"] == f"{cv.ink}80" and bands["stick-word-scrim-50-81"] == f"{cv.ink}81"


def test_every_gradient_filled_rect_holds_its_gradient_in_its_own_coordinates():
    # a rect's paint is in the rect's own space (its top-left is 0, 0); a gradient given in frame coordinates
    # paints a rect that is not at the origin with its first or last stop only
    cv = canvas()
    stick_car.car(cv, cv.comp, 2.0)
    stick_car.seat(cv, cv.comp)
    stick.words(cv, cv.comp, [stick.Line(0, 1, "hi", 118)])
    root = xml(cv)
    gradients = {g.get("id"): g for g in root.iter("linearGradient")}
    filled = [r for r in root.iter("shape") if r.get("shape") == "rect" and (r.get("fill") or "").startswith("url(")]
    assert len(filled) >= 4
    for r in filled:
        g = gradients[r.get("fill")[5:-1]]
        for a, b, size in (("x1", "x2", "width"), ("y1", "y2", "height")):
            lo, hi = sorted((float(g.get(a)), float(g.get(b))))
            assert -1 <= lo and hi <= float(r.get(size)) + 1, (g.get("id"), a, b)


@pytest.mark.parametrize("cue, match", [(stick.Line(0, 1, "two\nlines", 100), "one line"),
                                        (stick.Line(0, 1, " ", 100), "one line"),
                                        (stick.Line(1, 1, "hi", 100), "not after")])  # fmt: skip
def test_a_word_cue_it_cannot_show_is_refused(cue, match):
    with pytest.raises(stick.StickDataError, match=match):
        stick.words(canvas(), None, [cue])


def test_the_car_parts_are_registered_under_stick():
    names = {e.name: e for e in registry.entries()}
    for name, kind in (("stick-car", "location"), ("stick-car-seat", "prop"), ("stick-laptop", "prop"),
                       ("stick-phone", "prop"), ("stick-words", "graphic"), ("stick-cockpit", "prop"),
                       ("stick-ride", "prop")):  # fmt: skip
        assert names[name].kind == kind and names[name].style == "stick", name


def test_every_stick_location_signs_itself():
    from srstudio.canvas import Signature

    plate = stick.Plate("#5a854a", "M 0 0 L 10 0 L 10 10 Z")
    for draw in (
        lambda cv: stick.room(cv, cv.comp),
        lambda cv: stick.yard(cv, cv.comp, [plate], 1),
        lambda cv: stick_car.car(cv, cv.comp, 1.0),
    ):
        signed = Canvas(Scene(version="auto"), DAYLIGHT, font_asset="inter", signature=Signature())
        draw(signed)
        ids = [g.get("id") for g in xml(signed).iter("group")]
        assert any(i.startswith("sig-cactus") for i in ids) and any(i.startswith("sig-code") for i in ids)
        unsigned = canvas()
        draw(unsigned)
        assert not any((g.get("id") or "").startswith("sig-") for g in xml(unsigned).iter("group"))


def test_smaller_word_cues_let_more_quick_words_join_and_carry_their_size():
    words = [{"text": w, "start": i * 0.2, "end": i * 0.2 + 0.15} for i, w in enumerate(("so", "the", "view", "never"))]
    takes = [Take(0.0, 1.0, words)]
    width = len
    big = stick.word_cues(takes, min_seconds=0.85, width=width, max_width=7)
    small = stick.word_cues(takes, min_seconds=0.85, width=width, max_width=20, size=80)
    assert [c.text for c in big] == ["so the", "view", "never"]
    assert [c.text for c in small] == ["so the view never"] and all(c.size == 80 for c in small)
    assert all(c.size == stick.WORD_SIZE for c in big)  # the default is unchanged
    with pytest.raises(stick.StickDataError, match="size"):
        stick.word_cues(takes, size=0)


def test_a_darker_scrim_is_its_own_paint_and_the_default_keeps_its_own():
    cv = canvas()
    stick.words(cv, cv.comp, [stick.Line(0, 1, "hi", 118)], scrim=0.9)
    stick.words(cv, cv.comp, [stick.Line(1, 2, "there", 118)])
    root = xml(cv)
    stops = {g.get("id"): [s.get("color") for s in g.iter("stop")] for g in root.iter("linearGradient")}
    assert stops["stick-word-scrim-90"][1] == f"{cv.ink}{round(0.9 * 255):02x}"
    assert stops["stick-word-scrim"][1] == f"{cv.ink}{round(stick.SCRIM_PEAK * 255):02x}"
    with pytest.raises(stick.StickDataError, match="scrim"):
        stick.words(canvas(), None, [stick.Line(0, 1, "hi", 118)], scrim=1.5)


def test_a_short_cue_can_borrow_time_from_the_next_cue_of_its_take():
    words = [
        {"text": "Absolutely", "start": 0.0, "end": 0.3},
        {"text": "unbelievably", "start": 0.4, "end": 0.9},
        {"text": "cheap", "start": 1.6, "end": 1.9},
    ]
    takes = [Take(0.0, 3.0, words), Take(3.0, 3.4, [{"text": "No", "start": 0.0, "end": 0.2}])]
    plain = stick.word_cues(takes, min_seconds=0.8, width=len, max_width=12)
    assert [(c.start, c.end) for c in plain] == [(0.0, 0.4), (0.4, 1.6), (1.6, 2.2), (3.0, 3.4)]
    lent = stick.word_cues(takes, min_seconds=0.8, width=len, max_width=12, borrow=True)
    # the first cue takes 0.4 s from the second, which keeps its 0.8 s; the takes' last cues lend nothing
    assert [(c.start, c.end, c.text) for c in lent] == [
        (0.0, 0.8, "Absolutely"),
        (0.8, 1.6, "unbelievably"),
        (1.6, 2.2, "cheap"),
        (3.0, 3.4, "No"),
    ]
    with pytest.raises(stick.StickDataError, match="borrow"):
        stick.word_cues(takes, borrow=True)


def test_a_short_last_cue_can_join_the_cue_before_it():
    words = [
        {"text": "With", "start": 0.0, "end": 0.1},
        {"text": "a", "start": 0.15, "end": 0.2},
        {"text": "note", "start": 0.3, "end": 0.5},
        {"text": "trainer.", "start": 0.9, "end": 1.2},
    ]
    takes = [Take(0.0, 1.5, words), Take(2.0, 2.3, [{"text": "No", "start": 0.0, "end": 0.2}])]
    plain = stick.word_cues(takes, min_seconds=0.85, width=len, max_width=20)
    assert [(c.start, c.end, c.text) for c in plain] == [(0.0, 0.9, "With a note"), (0.9, 1.5, "trainer"),
                                                          (2.0, 2.3, "No")]  # fmt: skip
    joined = stick.word_cues(takes, min_seconds=0.85, width=len, max_width=20, tail=True)
    # the take's last cue, 0.6 s, joins the one before; a take of one cue has nothing to join
    assert [(c.start, c.end, c.text) for c in joined] == [(0.0, 1.5, "With a note trainer"), (2.0, 2.3, "No")]
    narrow = stick.word_cues(takes, min_seconds=0.85, width=len, max_width=12, tail=True)
    assert [c.text for c in narrow][:2] == ["With a", "note trainer"]  # too wide together: it takes "note"
    with pytest.raises(stick.StickDataError, match="tail"):
        stick.word_cues(takes, tail=True)


def test_a_short_last_cue_too_wide_to_join_takes_the_last_words_of_the_cue_before():
    words = [
        {"text": "With", "start": 0.0, "end": 0.1},
        {"text": "a", "start": 0.15, "end": 0.2},
        {"text": "note", "start": 0.3, "end": 0.45},
        {"text": "from", "start": 0.5, "end": 0.6},
        {"text": "your", "start": 0.65, "end": 0.8},
        {"text": "trainer.", "start": 0.9, "end": 1.2},
    ]
    takes = [Take(0.0, 1.5, words)]
    plain = stick.word_cues(takes, min_seconds=0.85, width=len, max_width=21)
    assert [c.text for c in plain] == ["With a note from your", "trainer"]
    moved = stick.word_cues(takes, min_seconds=0.85, width=len, max_width=21, tail=True)
    # "your trainer" starts at 0.65 s and runs to the take's end: long enough, and it fits
    assert [(c.start, c.end, c.text) for c in moved] == [(0.0, 0.65, "With a note from"), (0.65, 1.5, "your trainer")]
