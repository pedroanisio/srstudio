"""The gate of the show's look refuses what the look forbids, on measured frames (ADR 0074)."""

import dataclasses

import numpy as np
import pytest

from srstudio import show, show_numbers, thumbnail
from srstudio.figure_record import Figure
from srstudio.frame_gates import FrameGateError
from srstudio.framegraph import Drawing, Frame, Node
from srstudio.releases import Release
from srstudio.sample import SYSTEM_FONTS
from srstudio.show_gate import corner_defect, cover_faces, frame_defects, number_defects, scene_defects, show_defects
from srstudio.show_numbers import Claim, Ledger
from srstudio.social import InstagramPost
from srstudio.thumbnail import BAND_TOP, ShowCover, Thumbnail

FONT = next(f for f in SYSTEM_FONTS if f.exists())
PLACE = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
BUG = "show-bug-212"
LEDGER = Ledger(base=200, series={"Saga": 18}, reels={"good-reel": Claim(212), "saga-reel": Claim(213, "Saga", 19)})


def rect(left, top, right, bottom):
    return ((left, top), (right, top), (right, bottom), (left, bottom))


def frame(*shapes, time=1.0, world=PLACE, parent=None, opacity=1.0, draw=True):
    """A frame of the bug and ``shapes``: (id, outline, kind)."""
    extra = [Node("camera", None, "group", PLACE, 1.0, True)] if parent is not None else []
    nodes = [*extra, Node(BUG, parent, "group", world, opacity, draw)]
    nodes.append(Node("chip", len(extra), "shape", PLACE, 1.0, True))
    drawn = {"chip": Drawing((rect(*show.BUG_BOX),), True)}
    for name, outline, kind in shapes:
        nodes.append(Node(name, None, kind, PLACE, 1.0, True))
        if kind == "group":
            nodes.append(Node(f"{name}-shape", len(nodes) - 1, "shape", PLACE, 1.0, True))
            drawn[f"{name}-shape"] = Drawing((outline,), True)
        else:
            drawn[name] = Drawing((outline,), True)
    return Frame(time, 1080.0, 1920.0, tuple(nodes)), drawn


def defects(shown, drawn, figures=(), texts=None):
    return frame_defects([shown], drawn, 212, figures, texts or {})


def post(title="Who said this was fine?", cover=None):
    return InstagramPost(title, "Words.", thumbnail=cover or ShowCover("GOOD", 1.0, number=212))


def release(slug="good-reel", title="Who said this was fine?", cover=None, flag=True):
    return Release(slug, post(title, cover), cover=flag)


SAGA = ShowCover("GOOD", 1.0, number=213, series="Saga", series_number=19)


def document(*children, cover_rule=True):
    override = f'<override target="{BUG}" property="visible" value="false"/>'
    rule = f'<parameters><variant id="cover">{override}</variant></parameters>'
    body = "".join(f'<group id="{c}"/>' for c in children)
    return f'<scene>{rule if cover_rule else ""}<composition>{body}</composition></scene>'.encode()


# -- the number ------------------------------------------------------------------------------------------------------
def test_a_claimed_number_passes():
    reel = release()
    assert number_defects(reel, LEDGER, {reel.slug: reel}) == []


def test_a_number_nobody_claimed_is_refused():
    reel = release(slug="another-reel")
    assert any("not in the ledger" in why for why in number_defects(reel, LEDGER, {reel.slug: reel}))


def test_a_wrong_number_is_refused():
    reel = release(cover=ShowCover("GOOD", 1.0, number=214))
    assert any("the ledger gives it #212" in why for why in number_defects(reel, LEDGER, {reel.slug: reel}))


def test_a_missing_number_is_refused():
    reel = release(cover=ShowCover("GOOD", 1.0))
    assert any("number" in why for why in number_defects(reel, LEDGER, {reel.slug: reel}))


def test_a_number_two_releases_hold_is_refused():
    reel, other = release(), release(slug="other-reel")
    assert any("another release holds #212" in why for why in number_defects(reel, LEDGER, {"a": reel, "b": other}))


def test_a_series_place_two_releases_hold_is_refused():
    title = "Who said this was fine? Saga #19"
    reel = release(slug="saga-reel", title=title, cover=SAGA)
    other = release(slug="other-reel", title=title, cover=dataclasses.replace(SAGA, number=300))
    assert any("another release is Saga #19" in why for why in number_defects(reel, LEDGER, {"a": reel, "b": other}))


def test_a_series_says_its_place_after_the_question():
    good = release(slug="saga-reel", title="Who said this was fine? Saga #19", cover=SAGA)
    assert number_defects(good, LEDGER, {"a": good}) == []
    for title in ("Who said this was fine?", "Saga #19 Who said this was fine?", "This was fine. Saga #19"):
        reel = dataclasses.replace(good, post=post(title, SAGA))
        assert any("first line" in why for why in number_defects(reel, LEDGER, {"a": reel}))


SHOW_LEDGER = Ledger(base=200, series={"juno-and-pip": 0}, reels={"jp-two": Claim(216, "juno-and-pip", 2, "series-v1")})
JP = ShowCover("READY IN FIVE MINUTES", 1.0, number=216, series="Juno & Pip", series_number=2)


def jp(description="Juno & Pip, episode 2.\nA Soft sketch.", cover=JP):
    return Release("jp-two", InstagramPost("I'll be ready in five minutes.", description, thumbnail=cover), cover=True)


def test_a_show_named_in_more_words_matches_its_ledger_slug_and_opens_the_description_with_its_episode():
    reel = jp()
    assert number_defects(reel, SHOW_LEDGER, {"a": reel}) == []


@pytest.mark.parametrize("description", ["A Soft sketch.", "Juno & Pip, episode 3.", "Juno and Pip, episode 2."])
def test_a_show_episode_without_its_episode_line_is_refused(description):
    reel = jp(description)
    assert any("episode line" in why for why in number_defects(reel, SHOW_LEDGER, {"a": reel}))


def test_a_show_episode_the_ledger_places_elsewhere_is_refused():
    reel = jp(description="Juno & Pip, episode 3.", cover=dataclasses.replace(JP, series_number=3))
    assert any(
        "the ledger gives it #216, juno-and-pip #2" in why for why in number_defects(reel, SHOW_LEDGER, {"a": reel})
    )
    unplaced = Ledger(base=200, series={"juno-and-pip": 0}, reels={"jp-two": Claim(216)})
    assert any("the ledger gives it #216," in why for why in number_defects(jp(), unplaced, {"a": jp()}))


def test_a_show_whose_name_is_no_name_is_refused_not_matched():
    reel = jp(cover=dataclasses.replace(JP, series="juno-and-pip"))
    found = number_defects(reel, SHOW_LEDGER, {"a": reel})
    assert any("capitalised words" in why for why in found)


def test_the_show_s_cover_needs_its_cover_variant():
    reel = release(flag=False)
    assert any("cover=True" in why for why in number_defects(reel, LEDGER, {"a": reel}))


def test_a_plain_cover_is_not_this_gate_s_business():
    reel = Release("plain-reel", InstagramPost("Words?", "Words.", thumbnail=Thumbnail("GOOD", 1.0)))
    assert number_defects(reel, Ledger(), {"a": reel}) == []


# -- the scene -------------------------------------------------------------------------------------------------------
def test_a_scene_with_the_bug_last_and_hidden_on_the_cover_passes():
    assert scene_defects(document("camera", BUG), 212) == []


def test_a_scene_without_the_bug_is_refused():
    assert "no bug" in scene_defects(document("camera"), 212)[0]


def test_a_scene_built_for_another_number_is_refused():
    assert "show-bug-211" in scene_defects(document("show-bug-211"), 212)[0]


def test_a_bug_under_something_else_is_refused():
    assert "last" in scene_defects(document(BUG, "camera"), 212)[0]


def test_a_bug_left_on_the_cover_is_refused():
    assert "hidden on the cover" in scene_defects(document(BUG, cover_rule=False), 212)[0]


# -- the frames ------------------------------------------------------------------------------------------------------
def test_a_clean_frame_passes():
    assert defects(*frame()) == []


def test_a_frame_without_the_bug_is_refused_with_the_time_it_goes():
    gone = Frame(3.5, 1080.0, 1920.0, ())
    assert frame_defects([frame()[0], gone], {}, 212, (), {}) == ["the bug is missing in 1 of 2 frames, from 3.50 s"]


def test_a_bug_that_fades_is_refused():
    assert "faded" in defects(*frame(opacity=0.5))[0]
    assert "faded" in defects(*frame(draw=False))[0]


def test_a_bug_that_moves_with_the_camera_is_refused():
    shown, drawn = frame(world=(1.2, 0.0, 0.0, 1.2, -40.0, -60.0))
    assert "moved" in defects(shown, drawn)[0]


def test_a_bug_under_the_camera_at_rest_is_refused_though_it_has_not_moved_yet():
    assert "under the camera" in defects(*frame(parent=0))[0]


@pytest.mark.parametrize("name", ["sig-code", "sig-code-2", "sig-cactus"])
def test_a_signature_mark_under_the_bug_is_refused(name):
    assert "signature" in defects(*frame((name, rect(1000, 280, 1060, 360), "group")))[0]


def test_a_mark_beside_the_bug_passes():
    assert defects(*frame(("sig-code", rect(800, 300, 900, 360), "group"))) == []


def test_text_under_the_bug_is_refused():
    shown, drawn = frame(("words", rect(600, 240, 1040, 300), "layer"))
    assert "text" in defects(shown, drawn, texts={"words": (400.0, "start")})[0]


def test_a_text_box_wider_than_its_letters_is_not_text_under_the_bug():
    shown, drawn = frame(("words", rect(0, 240, 1080, 300), "layer"))
    assert defects(shown, drawn, texts={"words": (745.0, "center")}) == []


def test_a_face_under_the_bug_is_refused_and_a_body_is_not():
    shown, drawn = frame(("body", rect(800, 200, 1080, 1000), "shape"))
    assert "face" in defects(shown, drawn, (Figure("toon-cat", ("body",)),))[0]
    lower, drawn = frame(("body", rect(800, 100, 1080, 700), "shape"))
    assert "face" in defects(lower, drawn, (Figure("toon-cat", ("body",)),))[0]
    below, drawn = frame(("body", rect(800, 340, 1080, 1000), "shape"))
    assert defects(below, drawn, (Figure("toon-cat", ("body",)),)) == []
    arm, drawn = frame(("body", rect(800, -900, 1080, 400), "shape"))
    assert defects(arm, drawn, (Figure("toon-cat", ("body",)),)) == []


def test_a_figure_mostly_off_the_frame_is_not_a_face_under_the_bug_it_never_reaches():
    """Its box covers the corner; what it draws does not: the blob at the edge of a Soft close-up."""
    outline = ((1070, -400), (1400, -400), (1400, 1800), (1070, 1800))
    shown, drawn = frame(("body", outline, "shape"))
    assert defects(shown, drawn, (Figure("soft-blob", ("body",)),)) == []


def test_each_defect_is_said_once_with_its_count():
    bad = frame(world=(1.1, 0.0, 0.0, 1.1, 0.0, 0.0))
    said = frame_defects([bad[0], bad[0], frame()[0]], bad[1], 212, (), {})
    assert said == ["the bug is moved by what it sits under in 2 of 3 frames, from 1.00 s"]


# -- the band --------------------------------------------------------------------------------------------------------
def test_a_face_under_the_band_is_refused():
    cover = ShowCover("GOOD", 1.0, number=212)
    shown, drawn = frame(("body", rect(300, BAND_TOP - 100, 700, 1900), "shape"))
    figures = (Figure("toon-cat", ("body",)),)
    assert cover_faces(cover, shown, drawn, figures, FONT.read_bytes()) == ["toon-cat"]


def test_a_face_above_the_band_passes():
    cover = ShowCover("GOOD", 1.0, number=212)
    shown, drawn = frame(("body", rect(300, 400, 700, 1900), "shape"))
    figures = (Figure("toon-cat", ("body",)),)
    assert cover_faces(cover, shown, drawn, figures, FONT.read_bytes()) == []


# -- the video -------------------------------------------------------------------------------------------------------
def test_a_corner_the_encoder_only_softened_passes():
    scene = np.full(300, 200.0)
    assert corner_defect(scene + 8.0, scene) == ""


def test_a_stale_render_is_refused():
    scene = np.zeros(300)
    assert "render it again" in corner_defect(scene + 120.0, scene)


def test_one_wrong_digit_is_refused_though_the_rest_of_the_corner_matches():
    """The closest two last digits, 5 and 6, part by 50 pixels of the chip's 7,316: too few to move a mean."""
    scene = np.full((66, 118, 3), 12.0)
    video = scene.copy()
    video[40:45, 60:70] = 255.0
    assert "render it again" in corner_defect(video.reshape(-1), scene.reshape(-1))


def test_a_few_stray_pixels_are_the_encoder_and_pass():
    scene = np.full((66, 118, 3), 12.0)
    video = scene.copy()
    video[40, 60:68] = 255.0
    assert corner_defect(video.reshape(-1), scene.reshape(-1)) == ""


def test_a_corner_of_another_size_is_refused():
    assert "size" in corner_defect(np.zeros(3), np.zeros(6))


# -- the whole gate --------------------------------------------------------------------------------------------------
def test_a_plain_reel_never_reads_the_ledger(tmp_path):
    reel = Release("plain-reel", InstagramPost("Words?", "Words.", thumbnail=Thumbnail("GOOD", 1.0)))
    bad = tmp_path / "numbers.json"
    bad.write_text("not json")
    assert show_defects({"plain-reel": reel}, tmp_path, tmp_path, {"plain-reel": "plain"}, "none", bad, FONT) == []


def test_an_unreadable_ledger_stops_a_numbered_reel(tmp_path):
    bad = tmp_path / "numbers.json"
    bad.write_text("not json")
    with pytest.raises(show_numbers.NumberError):
        show_defects({"good-reel": release()}, tmp_path, tmp_path, {"good-reel": "good"}, "none", bad, FONT)


def test_a_numbered_reel_with_no_scene_is_refused_not_skipped(tmp_path):
    said = show_defects(
        {"good-reel": release()}, tmp_path, tmp_path, {"good-reel": "good"}, "none", tmp_path / "n", FONT
    )
    assert any("not in the ledger" in str(d) for d in said)
    assert any("missing" in str(d) for d in said)


def test_a_numbered_reel_built_without_its_record_is_refused(tmp_path):
    (tmp_path / "good-reel").mkdir()
    (tmp_path / "good-reel" / "good-reel.scene.xml").write_bytes(document(BUG))
    show_numbers.set_base(tmp_path / "n", 211)
    show_numbers.claim(tmp_path / "n", "good-reel")
    said = show_defects(
        {"good-reel": release()}, tmp_path, tmp_path, {"good-reel": "good"}, "none", tmp_path / "n", FONT
    )
    assert [d.reason for d in said] == ["figures.json is missing: build it with srstudio build"]


def test_a_gate_that_cannot_run_the_engine_stops_the_delivery(tmp_path):
    project = tmp_path / "good-reel"
    project.mkdir()
    scene = '<scene><project fps="24" duration="1"/><composition><group id="show-bug-212"/></composition>'
    rule = f'<parameters><variant id="cover"><override target="{BUG}"/></variant></parameters></scene>'
    (project / "good-reel.scene.xml").write_text(scene + rule)
    (project / "figures.json").write_text('{"schema": "1.0.0", "figures": []}')
    show_numbers.set_base(tmp_path / "n", 211)
    show_numbers.claim(tmp_path / "n", "good-reel")
    with pytest.raises(FrameGateError):
        show_defects(
            {"good-reel": release()},
            tmp_path,
            tmp_path,
            {"good-reel": "good"},
            tmp_path / "no-engine",
            tmp_path / "n",
            FONT,
        )


def test_episode_four_claimed_before_its_show_is_placed_as_ep_4_and_keeps_its_number(tmp_path):
    """ADR 0233, the Juno & Pip case: #215-#218 were claimed with no series, the show's base came later, and each
    episode's place comes from the release, never from the ledger's order."""

    path = tmp_path / "numbers.json"
    show_numbers.set_base(path, 214)
    for n in range(1, 5):
        show_numbers.claim(path, f"jp-ep{n}", brief="series-v1")
    show_numbers.set_base(path, 0, series="Juno & Pip")
    placed = show_numbers.place(path, "jp-ep4", "Juno & Pip", 4, delivered=())
    assert placed == Claim(218, "juno-and-pip", 4, "series-v1")
    assert show_numbers.episode_document(placed) == {
        "number": 218,
        "series": "juno-and-pip",
        "series_number": 4,
        "brief": "series-v1",
    }
    cover = ShowCover("A NEW NUMBER", 1.0, number=218, series="Juno & Pip", series_number=4)
    reel = Release(
        "jp-ep4", InstagramPost("Hi Mum, this is my new number.", "Juno & Pip, episode 4.", thumbnail=cover), cover=True
    )
    assert number_defects(reel, show_numbers.read(path), {"jp-ep4": reel}) == []
    font = next(f for f in SYSTEM_FONTS if f.exists())
    document = thumbnail.compose(
        cover, backdrop="b.png", font="f.ttf", font_bytes=font.read_bytes(), width=1080, height=1920
    ).to_bytes()
    assert "#218" in document.decode() and "JUNO &amp; PIP · EP 4" in document.decode()
    assert [show_numbers.read(path).reels[f"jp-ep{n}"].number for n in range(1, 5)] == [215, 216, 217, 218]
    for n in range(1, 4):
        assert show_numbers.place(path, f"jp-ep{n}", "Juno & Pip", n, delivered=()).number == 214 + n
    assert show_numbers.claim(path, "jp-ep5", series="Juno & Pip") == Claim(219, "juno-and-pip", 5)
