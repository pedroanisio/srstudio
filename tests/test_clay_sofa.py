"""The clay look study (examples/clay_sofa): Mae and Bruno as clay figures seated in the sofa room.

The figures keep the drawing: each part's outline is the drawn outline, the face is the rig's own layers. Head and body
are one surface; each figure has one pair of arms, rigged from the shoulders, and every gesture moves those two arms;
the anatomy rule counts their hands as it counts a drawn figure's (ADR 0174). The gasp and the jump lift the whole
figure off the cushion and set it back, rigid. They sit on the room's cushion, as the room's cameras see it (checked
against the room record's own projection), Bruno on his card's column and Mae as near hers as the two-shot lets her sit
whole inside it, without passing through each other; the sofa's arm covers Bruno's right side as it covers his card.
Lifted off the cushion, a figure leaves no shadow darker than the room's own under a card. The performance record of
the reel is read strictly, and the passes are put together as the study says, plain and inked in the room's own line.
The engine runs only as a stand-in script here: the study renders its passes outside this suite.
"""

import json
import math
import os
import stat
import sys
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import pytest
from shapely import contains_xy
from shapely.geometry import MultiPoint, Polygon
from shapely.geometry import Point as ShapelyPoint

from srstudio import sketch as sketch_mod
from srstudio.scripting import at as scripting_at

ROOT = Path(__file__).resolve().parent.parent
FOLDER = ROOT / "examples" / "clay_sofa"

# the room record's own projection of the two seats (lounge_plates.seats, srlocations 8dfe7a19): x, y, pixels per metre
TWO = dict(eye=(-0.29, 0.72, -3.0), look_at=(-0.29, 0.855, 0.0), lens=31.0)
MAE_CAMERA = dict(
    eye=(-0.2092501382060422, 0.74, -1.7880889162679965),
    look_at=(-0.6025370496533634, 0.6808013323798329, 0.3589155529562892),
    lens=31.0,
)
SEEN = {
    "two": {"mae": (148.47, 1333.39, 755.84), "bruno": (463.66, 1333.39, 755.84)},
    "mae": {"mae": (297.0, 1311.0, 1142.37), "bruno": (773.66, 1325.99, 1183.31)},
}


@pytest.fixture(scope="module")
def kit():
    """The study's modules, imported without keeping the umask and the search path a script sets."""
    path, mask = list(sys.path), os.umask(0)
    os.umask(mask)
    sys.path[:0] = [str(FOLDER), str(ROOT / "examples" / "paintover_proof"), str(ROOT / "episodes")]
    try:
        import clay_anatomy
        import clay_figure
        import clay_ink
        import clay_room
        import clay_sofa_study
        import performance
    finally:
        sys.path[:] = path
        os.umask(mask)
    return dict(
        cf=clay_figure, cr=clay_room, study=clay_sofa_study, pf=performance, ca=clay_anatomy, ci=clay_ink,
        reel=clay_sofa_study.reel,
    )  # fmt: skip


@pytest.fixture(scope="module")
def rigs():
    from srstudio import toon_redrawn

    return dict(mae=toon_redrawn.RABBIT_RIG, bruno=toon_redrawn.BEAR_RIG)


# --- the figure keeps the drawing -------------------------------------------------------------------------------------


def test_the_drawing_is_split_into_the_parts_it_draws(kit, rigs):
    cf = kit["cf"]
    for rig in rigs.values():
        parts = cf.parts_of(rig)
        assert len(parts.ears) == 2
        assert parts.coat == rig.look.coat and parts.shade != parts.coat
        assert all(len(s) <= cf.OUTLINE_POINTS for s in parts.head_strokes + parts.body_strokes)
        head = Polygon(parts.head)
        assert all(Polygon(ear).centroid.y < head.centroid.y for ear in parts.ears)  # ears up top


def test_each_part_keeps_its_drawn_outline_and_the_body_stands_flat_on_its_base(kit, rigs):
    cf = kit["cf"]
    for rig in rigs.values():
        fig = cf.figure(rig)
        parts = fig.parts
        for drawn, volume in ((parts.head, fig.head), *zip(parts.ears, fig.ears, strict=True)):
            rim = volume.front[-cf.SPOKES :, :2]
            assert Polygon(rim).area == pytest.approx(Polygon(drawn).area, rel=0.01)
            assert Polygon(rim).symmetric_difference(Polygon(drawn).buffer(0)).area < 0.02 * Polygon(drawn).area
        body = fig.body
        assert body.front[:, 1].max() == pytest.approx(cf.BASE)
        under = body.front[:, 1] >= cf.BASE - 1e-9
        assert under.sum() > cf.SPOKES // 4  # a flat seat, not a point
        assert np.allclose(body.front_normals[under], (0.0, 1.0, 0.0))
        kept = Polygon(parts.body).buffer(0).intersection(Polygon(body.front[-cf.SPOKES :, :2]).buffer(0))
        assert kept.area == pytest.approx(Polygon(parts.body).buffer(0).area, rel=0.01)


def test_every_front_faces_the_lens_with_no_hole_at_its_middle(kit, rigs):
    cf = kit["cf"]
    for rig in rigs.values():
        fig = cf.figure(rig)
        volumes = [fig.body, fig.head, fig.skin, *fig.ears]
        for volume in volumes:
            p, t = volume.front, volume.triangles
            normal = np.cross(p[t[:, 1]] - p[t[:, 0]], p[t[:, 2]] - p[t[:, 0]])
            seat = (p[t][:, :, 1] >= cf.BASE - 1e-9).all(axis=1)  # the flat base, its normal straight down
            solid = (np.linalg.norm(normal, axis=1) > 1e-6) & ~seat
            assert (normal[solid, 2] < 0).mean() > 0.995
            fold = (p[t][:, :, 1] >= cf.BASE - 1e-9).any(axis=1)  # the body's middle sits on its base: the fold there
            assert (normal[solid & ~fold & (t[:, 0] == 0)][:, 2] < 0).all()  # the fan round the deepest point too


def test_a_fan_wound_the_wrong_way_is_turned_round(kit):
    cf = kit["cf"]
    flat = np.array([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.5, 0.5)])
    tris = np.array([(4, 0, 1), (4, 1, 2), (4, 3, 2), (4, 3, 0)])  # the last two the other way round
    fixed = cf._wound(flat, tris)
    a, b, c = (flat[fixed[:, i]] for i in range(3))
    area = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
    assert (np.sign(area) == np.sign(area[0])).all()


def test_texture_coordinates_put_the_drawings_top_row_at_the_top_of_the_picture(kit):
    cf = kit["cf"]
    box = cf.Box(10.0, 100.0, 110.0, 300.0)
    uv = box.uv(np.array([(10.0, 100.0), (110.0, 300.0), (60.0, 200.0)]))
    assert uv.tolist() == [[0.0, 1.0], [1.0, 0.0], [0.5, 0.5]]  # OBJ's v runs up


def test_the_face_is_painted_from_the_rigs_own_layers_for_each_state(kit, rigs):
    cf = kit["cf"]
    rig, fig = rigs["bruno"], cf.figure(rigs["bruno"])
    rest = cf.Face("narrow", "ahead", False, "flat", "flat")
    talking = replace(rest, mouth="teeth")
    blinking = replace(rest, blink=True)
    pictures = [cf.skin_textures(rig, fig, face)[0] for face in (rest, talking, blinking)]
    assert pictures[0].shape == pictures[1].shape == pictures[2].shape
    assert not np.array_equal(pictures[0], pictures[1]) and not np.array_equal(pictures[0], pictures[2])
    assert rest.key() != talking.key() != blinking.key()


def test_the_paws_at_rest_lie_on_the_lap(kit, rigs):
    cf = kit["cf"]
    for rig in rigs.values():
        fig = cf.figure(rig)
        surface = cf.front_of(fig.skin)
        for chain in fig.arms:
            joints = cf.reach(chain, chain.rest)
            paw = joints.paw
            under = float(surface(np.array([paw[0]]), np.array([paw[1]]))[0])
            # it rests on the lap: its middle in front of the belly, its back on the belly or on its own forearm's end
            # (laid on the belly, which the paw covers), within a fifth of the paw's thickness
            deep = cf.paw_depth(chain)
            path, radii = cf.arm_line(chain, joints)
            rest_on = min(under, float(path[-1, 2] - radii[-1]))
            assert paw[2] < under
            assert rest_on - 0.4 * deep <= paw[2] + deep, (paw[2] + deep, rest_on)
            assert Polygon(fig.parts.body).contains(ShapelyPoint(paw[0], paw[1]))  # on the lap, not beside it


def test_only_mae_and_bruno_are_built(kit):
    from srstudio import toon_redrawn

    others = [r for n, r in vars(toon_redrawn).items() if n.endswith("_RIG") and n not in ("BEAR_RIG", "RABBIT_RIG")]
    if not others:
        pytest.skip("no other redrawn rig to refuse")
    with pytest.raises(kit["cf"].FigureError, match="Mae and Bruno"):
        kit["cf"].figure(others[0])


# --- the room's cameras -----------------------------------------------------------------------------------------------


@pytest.mark.parametrize("take, camera", [("two", TWO), ("mae", MAE_CAMERA)])
def test_the_clay_camera_sees_the_seats_where_the_room_record_does(kit, take, camera):
    cr, lounge = kit["cr"], kit["study"].lounge
    lens = cr.camera_of(camera["eye"], camera["look_at"], camera["lens"])
    for name, seat in (("mae", lounge.SEAT_MAE), ("bruno", lounge.SEAT_BRUNO)):
        x, y, ppm = SEEN[take][name]
        px = cr.project([cr.engine(seat)], lens)[0]
        assert px[0] == pytest.approx(x, abs=0.6) and px[1] == pytest.approx(y, abs=0.6)
        assert cr.pixels_per_metre(seat, lens) == pytest.approx(ppm, rel=0.002)


def test_a_seat_keeps_the_card_size_its_column_and_its_back_on_the_sofa(kit, rigs):
    cr = kit["cr"]
    lens = cr.camera_of(TWO["eye"], TWO["look_at"], TWO["lens"])
    fig = kit["cf"].figure(rigs["bruno"])
    back_at, card = 0.5, (-0.391, 0.374, 0.3)
    seat = cr.seat_of(fig, card, lens, 1.2, False, back_at)
    x, _, z = seat.at[0] / 100.0, seat.at[1], seat.at[2] / 100.0
    per = seat.per / 100.0
    assert z + fig.skin.depth[1] * per == pytest.approx(back_at, abs=1e-4)
    assert cr.project([seat.at], lens)[0][0] == pytest.approx(cr.project([cr.engine(card)], lens)[0][0], abs=0.01)
    assert 1.2 / cr.pixels_per_metre((x, cr.CUSHION_TOP, z), lens) == pytest.approx(per, rel=1e-3)
    assert -seat.at[1] / 100.0 == pytest.approx(cr.CUSHION_TOP - cr.SINK)


def box_mesh(clay, x0, x1, z0, z1):
    xs, ys, zs = (x0, x1), (0.0, 10.0), (z0, z1)
    points = np.array([(x, y, z) for x in xs for y in ys for z in zs], float)
    return clay.Mesh("m", points, np.tile((0.0, 0.0, -1.0), (8, 1)), np.array([(0, 1, 2)]))


def test_clearance_measures_the_gap_and_a_pass_through(kit):
    cr = kit["cr"]
    front = [box_mesh(cr.clay, 0.0, 10.0, 0.0, 5.0)]
    assert cr.clearance(front, [box_mesh(cr.clay, 0.0, 10.0, 8.0, 12.0)]) == pytest.approx(0.03)
    assert cr.clearance(front, [box_mesh(cr.clay, 0.0, 10.0, 2.0, 12.0)]) == pytest.approx(-0.03)
    assert cr.clearance(front, [box_mesh(cr.clay, 50.0, 60.0, 0.0, 5.0)]) == float("inf")


def test_the_pair_sits_clear_of_each_other_on_the_cushion(kit, rigs, tmp_path):
    study, cr = kit["study"], kit["cr"]
    performance = resting_performance(kit)
    room = type("R", (), {"takes": {"two": dict(TWO)}})()
    places = study.seats(room, performance)
    posed = {
        who: cr.posed(who, rigs[who], kit["cf"].figure(rigs[who]), performance.at(who, 0), places[who])
        for who in ("mae", "bruno")
    }
    assert cr.clearance(posed["bruno"], posed["mae"]) >= study.GAP - 0.0006
    for who in ("mae", "bruno"):  # each sits on the cushion, pressed in as far as the cards
        low = max(float(m.vertices[:, 1].max()) for m in posed[who]) / -100.0
        assert low == pytest.approx(cr.CUSHION_TOP - cr.SINK, abs=1e-6)


def test_a_mirrored_figure_turns_about_the_seat_line(kit, rigs):
    cr = kit["cr"]
    frame = resting_performance(kit).at("mae", 0)
    body, _ = cr.chains(rigs["mae"], frame, True)
    x = body @ np.array([cr.SEAT_X + 50.0, 700.0, 1.0])
    assert x[0] == pytest.approx(cr.SEAT_X - 50.0, abs=1.0)


# --- the performance record -------------------------------------------------------------------------------------------


def resting_frame(**change) -> dict:
    row = dict(eyes="narrow", gaze="ahead", blink=False, mouth="flat", pose_mouth="flat", pose_arms="desk", lift=0.0,
               tilt=0.0, lean=0.0, breath=0.0, turn=0.0, roll=0.0, nod=0.0, idle_roll=0.0, idle_y=0.0, face_x=0.0,
               arms=[], holds="")  # fmt: skip
    row.update(change)
    return row


def record(**change) -> dict:
    data = dict(
        schema="clay-sofa.performance/1.2.0",
        fps=24,
        frames=2,
        shots=[dict(name="two", start=0.0, end=4.6)],
        cast={"mae": [resting_frame(), resting_frame()], "bruno": [resting_frame(), resting_frame(mouth="teeth")]},
    )
    data.update(change)
    return data


def resting_performance(kit):
    return kit["pf"].Performance.parse(record())


def test_a_written_performance_reads_back_the_same(kit, tmp_path):
    pf = kit["pf"]
    performance = pf.Performance.parse(record())
    performance.dump(tmp_path / "p.json")
    again = pf.Performance.load(tmp_path / "p.json")
    assert asdict(again) == asdict(performance)
    assert again.at("bruno", 1).mouth == "teeth" and again.shot(0) == "two"


@pytest.mark.parametrize(
    "data, match",
    [
        (record(schema="clay-sofa.performance/1.1.0"), "schema"),
        (record(cast={"mae": [resting_frame(holds="cup")] * 2, "bruno": [resting_frame()] * 2}), "holds"),
        (record(fps=30), "fps"),
        (record(extra=1), "fields"),
        ({k: v for k, v in record().items() if k != "shots"}, "fields"),
        (record(shots=[]), "names its shots"),
        (record(shots=[dict(name="kitchen", start=0.0, end=1.0)]), "name"),
        (record(cast={"mae": [resting_frame()] * 2}), "cast"),
        (record(cast={"mae": [resting_frame()], "bruno": [resting_frame()] * 2}), "frames"),
        (record(cast={"mae": [resting_frame(eyes="lasers")] * 2, "bruno": [resting_frame()] * 2}), "eyes"),
        (record(cast={"mae": [resting_frame(pose_arms="juggle")] * 2, "bruno": [resting_frame()] * 2}), "arms"),
        (record(cast={"mae": [resting_frame(lift=1e9)] * 2, "bruno": [resting_frame()] * 2}), "lift"),
        (record(cast={"mae": [resting_frame(nod=float("nan"))] * 2, "bruno": [resting_frame()] * 2}), "nod"),
        (record(cast={"mae": [resting_frame(blink="yes")] * 2, "bruno": [resting_frame()] * 2}), "blink"),
        (record(cast={"mae": [resting_frame(surprise=1)] * 2, "bruno": [resting_frame()] * 2}), "fields"),
        (
            record(
                cast={
                    "mae": [{k: v for k, v in resting_frame().items() if k != "face_x"}] * 2,
                    "bruno": [resting_frame()] * 2,
                }
            ),
            "fields",
        ),  # fmt: skip
        ("not a record", "fields"),
    ],
)
def test_a_performance_that_is_not_the_studys_is_refused(kit, data, match):
    pf = kit["pf"]
    with pytest.raises(pf.PerformanceError, match=match):
        pf.Performance.parse(data)


def test_an_unreadable_performance_file_is_refused(kit, tmp_path):
    pf = kit["pf"]
    (tmp_path / "p.json").write_text('{"schema": ')
    with pytest.raises(pf.PerformanceError, match="not a readable"):
        pf.Performance.load(tmp_path / "p.json")


def test_a_hold_keyed_layer_shows_from_its_key_until_switched_off(kit):
    pf = kit["pf"]
    keys = {"open": [(1.0, 1), (2.0, 0)], "round": [(1.5, 1), (1.8, 0)]}
    assert [pf._state(keys, t, "closed") for t in (0.5, 1.2, 1.6, 1.9, 2.5)] == [
        "closed",
        "open",
        "round",
        "closed",
        "closed",
    ]


# --- the passes put together ------------------------------------------------------------------------------------------


def picture(lum: float, alpha: float = 1.0, size=(20, 30)) -> np.ndarray:
    out = np.zeros((*size, 4))
    out[..., :3] = lum
    out[..., 3] = alpha
    return out


def test_the_shadow_is_what_the_figures_take_from_the_sofa_never_more_and_never_light(kit):
    cr = kit["cr"]
    b, k = picture(0.5), picture(0.0, 0.0)
    p = picture(0.5)
    p[5:15, 5:25, :3] = 0.05  # a deep shadow
    p[0:2, :, :3] = 0.9  # brighter than the sofa: no shadow is light
    dark = cr.shadow(p, b, k)
    assert dark.min() == pytest.approx(cr.SHADOW_FLOOR)
    assert dark.max() == 1.0 and (dark[0, :] == 1.0).all()
    noise = picture(0.5 * (1 - cr.SHADOW_NOISE / 2))
    assert (cr.shadow(noise, b, k) == 1.0).all()  # under the renderer's noise


# lounge_plates' soft shadow under a card at its darkest: its plates/back.png over the clean-plates/back.png drawn
# without it, on the two-shot and both close-ups (0.673 to 0.681)
ROOM_SHADOW = 0.673


def test_a_figure_off_the_cushion_darkens_it_no_more_than_the_room_shadows_a_card(kit):
    """Bruno's gasp lifts him off the cushion: the strip of seat under him, which only the fill reaches, reads as the
    room's own soft shadow under a card, never as a black cut."""
    cr = kit["cr"]
    b, k = picture(0.5), picture(0.0, 0.0)
    p = picture(0.5)
    p[5:15, 5:25, :3] = 0.0  # nothing but the fill
    assert cr.shadow(p, b, k).min() >= ROOM_SHADOW - 0.01


def test_the_composite_lays_the_figures_over_the_shadowed_plate(kit):
    cr = kit["cr"]
    back, b = picture(0.8), picture(0.5)
    p = picture(0.5)
    p[:, :10, :3] = 0.25  # the figures' shadow on the sofa's left
    p[:, 20:, :3] = 0.1  # the figure itself
    k = picture(0.0, 1.0)
    k[:, 20:, :3] = 1.0
    out, dark = cr.composite(back, p, k, b)
    assert np.allclose(out[:, 22:-1, :3], 0.1)  # the figure where K says it is seen
    assert np.allclose(out[:, 12:17, :3], 0.8)  # the plate untouched where nothing falls
    assert (out[:, 1:8, 0] < 0.8 * (1 - cr.SHADOW_NOISE)).all()  # darkened by its shadow
    with pytest.raises(cr.RenderError, match="different sizes"):
        cr.shadow(picture(0.5, size=(10, 10)), b, k)


# --- the engine's run ------------------------------------------------------------------------------------------------


def fake_engine(tmp_path: Path, body: str) -> Path:
    script = tmp_path / "engine.sh"
    script.write_text("#!/bin/sh\n" + body + "\n")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return script


def small_plate(kit):
    cr = kit["cr"]
    lens = cr.camera_of(TWO["eye"], TWO["look_at"], TWO["lens"])
    return cr.Plate(cr.WIDTH, cr.HEIGHT, lens, cr.lights(), (cr.Placed(cr.sofa()),), (cr.STAND_IN,))


def test_a_pass_is_rendered_once_and_served_from_the_cache_after(kit, tmp_path, monkeypatch):
    cr = kit["cr"]
    engine = fake_engine(tmp_path, 'echo run >> "$(dirname "$0")/runs"; printf png > plate.png')
    monkeypatch.setenv("SRSTUDIO_ENGINE", str(engine))
    spent = cr.Spent.new()
    first = cr.render(small_plate(kit), tmp_path / "cache", "B", spent)
    again = cr.render(small_plate(kit), tmp_path / "cache", "B", spent)
    assert first == again and first.read_bytes() == b"png"
    assert (tmp_path / "runs").read_text().count("run") == 1
    assert spent.runs == {"B": 1} and spent.cached == {"B": 1}


@pytest.mark.parametrize(
    "body, match",
    [
        ("echo 'no GPU' >&2; exit 3", "could not render"),
        ("echo 'warning: texture clamped' >&2; printf png > plate.png", "warned"),
    ],
)
def test_a_pass_the_engine_refuses_or_warns_on_fails(kit, tmp_path, monkeypatch, body, match):
    cr = kit["cr"]
    monkeypatch.setenv("SRSTUDIO_ENGINE", str(fake_engine(tmp_path, body)))
    with pytest.raises(cr.RenderError, match=match):
        cr.render(small_plate(kit), tmp_path / "cache", "P", cr.Spent.new())
    assert not list((tmp_path / "cache" / "P").glob("*.png"))  # nothing cached from a failed run


def test_the_k_pass_is_flat_white_figures_on_black(kit):
    cr = kit["cr"]
    from srstudio import plates

    raster = cr._raster(plates.document(small_plate(kit))).decode()
    assert 'renderer="raster"' in raster and 'ambientOcclusion="false"' in raster and 'exposure="0"' in raster
    assert cr.MASK_ON.emissive == "#FFFFFF" and not cr.MASK_OFF.emissive and cr.MASK_OFF.color == "#000000"


def test_a_shot_shows_the_frames_whose_time_falls_in_it(kit):
    study = kit["study"]
    assert study.frames_of(0.0, 4.6, 191) == (0, 110)
    assert study.frames_of(4.6, 6.65, 191) == (111, 159)
    assert study.frames_of(6.65, 7.95, 191) == (160, 190)
    shots = [dict(name="two", start=0.0, end=4.6), dict(name="mae", start=4.6, end=6.65),
             dict(name="bruno", start=6.65, end=7.95)]  # fmt: skip
    performance = kit["pf"].Performance.parse(record(frames=191, shots=shots, cast={
        who: [resting_frame()] * 191 for who in ("mae", "bruno")}))  # fmt: skip
    taken = [performance.shot(n) for n in (0, 110, 111, 159, 160, 190)]
    assert taken == ["two", "two", "mae", "mae", "bruno", "bruno"]


def test_the_compare_counts_only_an_underside_turned_to_the_camera(kit):
    sys.path[:0] = [str(FOLDER), str(ROOT / "examples" / "paintover_proof")]
    try:
        import clay_compare
    finally:
        del sys.path[:2]
    cr = kit["cr"]
    base = cr.clay.Mesh("m", np.array([(0.0, -37.0, 40.0), (10.0, -37.0, 40.0)]), np.array([(0.0, 1.0, 0.0)] * 2),
                        np.array([(0, 1, 1)]))  # fmt: skip
    assert clay_compare.underside_facing([base], np.array((0.0, -72.0, -300.0))) == 0  # seen from above
    assert clay_compare.underside_facing([base], np.array((0.0, 10.0, -300.0))) == 2  # seen from below
    ear = cr.clay.Mesh("e", np.array([(0.0, -90.0, 40.0)] * 2), np.array([(0.0, 1.0, 0.0)] * 2), np.array([(0, 1, 1)]))
    assert clay_compare.underside_facing([base, ear], np.array((0.0, -72.0, -300.0))) == 0  # an outline's foot


def test_the_study_writes_nothing_others_can_read(kit, tmp_path):
    cr = kit["cr"]
    mask = os.umask(0o077)
    try:
        cr.write(tmp_path / "sub" / "f.png", picture(0.5))
    finally:
        os.umask(mask)
    assert stat.S_IMODE((tmp_path / "sub").stat().st_mode) == 0o700
    assert stat.S_IMODE((tmp_path / "sub" / "f.png").stat().st_mode) == 0o600
    assert json.loads(json.dumps(asdict(resting_performance(kit))))["schema"].endswith("1.2.0")


def test_the_heads_pictures_are_refused_without_the_face_they_show(kit, rigs):
    cr = kit["cr"]
    with pytest.raises(cr.RenderError, match="face it shows"):
        cr._textures(rigs["mae"], "head")


# --- round 2: one pair of arms, real body motion, one surface, the room's ink ----------------------------------------


def frame_of(kit, **change):
    """One performance frame, parsed under the record's own rules."""
    return kit["pf"]._frame(resting_frame(**change), "test frame")


def wow_arms(kit) -> list[dict]:
    """Bruno's raised hands at the end of their swing, as the two-shot records them (performance.late_hands)."""
    from srstudio import toon_bed, toon_pair, toon_sketch

    reel, (sx, sy) = kit["reel"], toon_sketch.SEAT
    rows = []
    for root, target in reel.WOW_HANDS:
        degrees, length = toon_pair.aim(root, target)
        at = reel.BRUNO_AT
        local = [(root[0] - at[0]) / reel.PAIR_SCALE + sx, (root[1] - at[1]) / reel.PAIR_SCALE + sy]
        rows.append(dict(root=local, degrees=degrees, length=length / reel.PAIR_SCALE, width=toon_bed.ARM_WIDTH))
    return rows


def gestures(kit) -> dict:
    """Every gesture of the reel the clay performs with its arms: the Wow, the gasp's flinch, the pat."""
    reel = kit["reel"]
    pat = 14.15
    patting = kit["pf"].pat_hand(reel, pat, pat - 0.5, pat + 1.2, pat + 0.04 + reel.PAT_EVERY)  # a paw up
    assert len(patting) == 1
    return {
        "wow": dict(arms=wow_arms(kit)),
        "gasp": dict(tilt=reel.GASP_TILT),
        "pat": dict(arms=[dict(root=list(a.root), degrees=a.degrees, length=a.length, width=a.width) for a in patting]),
    }


def parts_by_id(parts) -> dict:
    return {part.id: part for part in parts}


def points(part) -> np.ndarray:
    return np.concatenate([mesh.vertices for mesh in part.meshes])


@pytest.mark.parametrize("who", ["mae", "bruno"])
def test_a_clay_figure_has_one_pair_of_arms_rooted_at_its_shoulders_and_no_hands_in_its_body(kit, rigs, who):
    cf, cr = kit["cf"], kit["cr"]
    rig = rigs[who]
    fig = cf.figure(rig)
    assert [chain.side for chain in fig.arms] == ["left", "right"]
    body = Polygon(fig.parts.body)
    for chain in fig.arms:
        shoulder = ShapelyPoint(chain.shoulder[0], chain.shoulder[1])
        assert body.contains(shoulder)  # the arm grows from the body
        assert chain.shoulder[1] < rig.neck[1] + 40.0  # up at the shoulder, not at the hip
        assert (chain.shoulder[0] < cr.SEAT_X) == (chain.side == "left")
    parts = cr.local_parts(who, rig, fig, frame_of(kit))
    hands = [part for part in parts if part.hand is not None]
    assert sorted(part.hand.word for part in hands) == ["left", "right"]  # one pair, counted
    assert all(part.chain == part.hand.word for part in hands)  # each on its own chain
    assert {part.chain for part in parts if part.chain} == {"left", "right"}
    # the body carries no arm and no paw: nothing the pose's arms draw is painted or modelled into it
    from srstudio.toon_cast import _arms

    under, _ = _arms(rig.look, "desk", 0)
    drawn = {tuple(shape) for shape, _ in under}
    assert not drawn & {tuple(shape) for shape, _ in fig.parts.body_layers}
    assert not drawn & {tuple(shape) for shape, _ in fig.parts.ear_layers[0] + fig.parts.ear_layers[1]}
    assert [part.id for part in parts if part.chain is None and part.hand is None] == [
        f"{who}-skin",
        f"{who}-ear0",
        f"{who}-ear1",
    ]


@pytest.mark.parametrize("gesture", ["wow", "gasp", "pat"])
def test_every_gesture_moves_the_two_resting_arms_and_nothing_else(kit, rigs, gesture):
    cr, cf = kit["cr"], kit["cf"]
    rig, fig = rigs["bruno"], cf.figure(rigs["bruno"])
    rest = parts_by_id(cr.local_parts("bruno", rig, fig, frame_of(kit)))
    moved = parts_by_id(cr.local_parts("bruno", rig, fig, frame_of(kit, **gestures(kit)[gesture])))
    assert moved.keys() == rest.keys()  # the same parts: no arm appears, none is left behind
    changed = {k for k in rest if not np.allclose(points(rest[k]), points(moved[k]))}
    assert changed and all(rest[k].chain for k in changed)  # only the arms' chains move
    paws = [k for k in changed if rest[k].hand is not None]
    assert paws  # and a hand goes with its arm
    for k in rest:  # the resting chains are the moving ones: a chain is whole at rest and in the gesture
        if rest[k].chain:
            assert moved[k].chain == rest[k].chain and moved[k].hand == rest[k].hand


def test_the_raised_paws_reach_the_flat_cards_hands(kit, rigs):
    cr, cf = kit["cr"], kit["cf"]
    rig, fig = rigs["bruno"], cf.figure(rigs["bruno"])
    frame = frame_of(kit, arms=wow_arms(kit))
    targets = cr.arm_targets(fig, frame)
    for chain in fig.arms:
        joints = cf.reach(chain, targets[chain.side])
        assert joints.paw[1] < rig.neck[1] - 120.0  # up beside the head, not a stub at the shoulder
        bones = (joints.elbow - joints.shoulder, joints.wrist - joints.elbow)
        assert np.linalg.norm(bones[0]) == pytest.approx(chain.upper)  # bones keep their length
        assert np.linalg.norm(bones[1]) == pytest.approx(chain.fore)


def test_the_anatomy_rule_counts_the_clay_hands_and_refuses_a_second_pair(kit, rigs):
    ca, cr, cf = kit["ca"], kit["cr"], kit["cf"]
    from srstudio.anatomy_ledger import HAND_COUNT

    lens = cr.camera_of(TWO["eye"], TWO["look_at"], TWO["lens"])
    performance = resting_performance(kit)
    room = type("R", (), {"takes": {"two": dict(TWO)}})()
    places = kit["study"].seats(room, performance)
    wow = frame_of(kit, arms=wow_arms(kit))
    figures = {
        "rabbit": cr.posed_parts("mae", rigs["mae"], cf.figure(rigs["mae"]), frame_of(kit), places["mae"]),
        "bear": cr.posed_parts("bruno", rigs["bruno"], cf.figure(rigs["bruno"]), wow, places["bruno"]),
    }
    counted = ca.count(figures, lens)
    assert counted.hands == {"rabbit": 2, "bear": 2} and counted.notes == []
    # round 1's rig: the paws at rest left on the body while a second pair goes up
    second = tuple(
        cr.Part(f"{part.id}-again", part.meshes, part.hand, part.chain) for part in figures["bear"] if part.chain
    )
    doubled = {**figures, "bear": (*figures["bear"], *second)}
    refused = ca.count(doubled, lens)
    assert refused.hands["bear"] == 4
    assert [(note.rule, note.part) for note in refused.notes] == [(HAND_COUNT, "bear")]
    # hidden paws still count: a second pair pushed behind the sofa is still drawn
    hidden = tuple(
        cr.Part(p.id, tuple(cr.clay.Mesh(m.material, m.vertices + (0.0, 0.0, 400.0), m.normals, m.triangles)
                            for m in p.meshes), p.hand, p.chain)
        for p in second
    )  # fmt: skip
    assert ca.count({**figures, "bear": (*figures["bear"], *hidden)}, lens).hands["bear"] == 4


@pytest.mark.parametrize("who, motion", [("bruno", dict(lift=-58.0, tilt=-5.0)), ("mae", dict(lift=-28.0))])
def test_the_gasp_and_the_jump_lift_the_whole_figure_off_the_cushion_rigid(kit, rigs, who, motion):
    cr, cf = kit["cr"], kit["cf"]
    rig, fig = rigs[who], cf.figure(rigs[who])
    seat = cr.Seat((0.0, -37.4, 30.0), 0.16, who == "mae")
    rest = cr.posed_parts(who, rig, fig, frame_of(kit), seat)
    up = cr.posed_parts(who, rig, fig, frame_of(kit, **motion), seat)
    lift = cr.figure_motion(frame_of(kit, **motion), who == "mae")
    linear = lift[:2, :2]
    assert np.allclose(linear @ linear.T, np.eye(2))  # a turn and a move: no stretch, no shear
    lowest = [max(float(points(p)[:, 1].max()) for p in parts) for parts in (rest, up)]  # engine y is down
    assert lowest[1] < lowest[0] - 0.5  # the base leaves the cushion (centimetres)
    for a, b in zip(rest, up, strict=True):
        if a.chain:
            continue  # the gasp also flinches the arms: their own test
        d0 = np.linalg.norm(points(a)[::97, None] - points(a)[None, ::97], axis=2)
        d1 = np.linalg.norm(points(b)[::97, None] - points(b)[None, ::97], axis=2)
        assert np.allclose(d0, d1, atol=1e-6)  # every part keeps its shape


def test_the_figure_settles_back_on_the_cushion_and_never_presses_through_it(kit, rigs):
    cr, cf = kit["cr"], kit["cf"]
    rig, fig = rigs["bruno"], cf.figure(rigs["bruno"])
    seat = cr.Seat((0.0, -37.4, 30.0), 0.16, False)
    rest = max(float(points(p)[:, 1].max()) for p in cr.posed_parts("bruno", rig, fig, frame_of(kit), seat))
    for share in np.linspace(0.0, 1.0, 11):  # the gasp's lift and tilt share their keys: one runs as far as the other
        frame = frame_of(kit, lift=-58.0 * share, tilt=-5.0 * share)
        low = max(float(points(p)[:, 1].max()) for p in cr.posed_parts("bruno", rig, fig, frame, seat))
        assert low <= rest + 1e-6  # never deeper into the cushion than at rest
    back = max(float(points(p)[:, 1].max()) for p in cr.posed_parts("bruno", rig, fig, frame_of(kit), seat))
    assert back == pytest.approx(rest)


@pytest.mark.parametrize("who", ["mae", "bruno"])
def test_head_and_body_are_one_surface_with_no_seam_at_the_neck(kit, rigs, who):
    cf = kit["cf"]
    rig = rigs[who]
    fig = cf.figure(rig)
    skin = fig.skin
    # one connected surface: every triangle reaches every other through shared edges
    tris = skin.triangles
    edges = np.sort(np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]]), axis=1)
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

    n = len(skin.front)
    graph = coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])), shape=(n, n))
    assert connected_components(graph, directed=False)[0] == 1
    # it covers the drawing's head and its body, as one outline
    union = Polygon(fig.parts.head).buffer(0).union(Polygon(fig.parts.body).buffer(0))
    rim = Polygon(skin.front[-cf.SPOKES_SKIN :, :2]).buffer(0)
    assert rim.symmetric_difference(union).area < 0.02 * union.area
    # where the head's outline crosses the body, the surface turns smoothly: no crease, no ring
    p = skin.front
    normal = np.cross(p[tris[:, 1]] - p[tris[:, 0]], p[tris[:, 2]] - p[tris[:, 0]])
    normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-12)
    centre = p[tris].mean(axis=1)
    head_line, body = Polygon(fig.parts.head).exterior, Polygon(fig.parts.body).buffer(-12.0)
    near = np.array([head_line.distance(ShapelyPoint(c[0], c[1])) < 8.0 and body.contains(ShapelyPoint(c[0], c[1]))
                     for c in centre])  # fmt: skip
    assert near.sum() > 50
    order = {tuple(e): k for k, e in enumerate(np.sort(tris[:, [0, 1]], axis=1).tolist())}
    worst = 0.0
    for k in np.nonzero(near)[0]:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            other = order.get(tuple(sorted((int(tris[k, a]), int(tris[k, b])))))
            if other is not None and other != k:
                worst = max(worst, float(np.degrees(np.arccos(np.clip(normal[k] @ normal[other], -1, 1)))))
    assert worst < 30.0
    # the head's weight runs from the body to the head without a step
    assert fig.weights.min() >= 0.0 and fig.weights.max() <= 1.0
    jump = np.abs(fig.weights[edges[:, 0]] - fig.weights[edges[:, 1]])
    assert jump.max() < 0.5


UNDERCUT = 0.5  # the most the front may fall back per reference pixel down under the chin: 27 degrees off the lens


@pytest.mark.parametrize("who", ["mae", "bruno"])
def test_the_chin_runs_down_into_the_chest_with_no_undercut(kit, rigs, who):
    """A head that stands out as a ball in front of the chest leaves a ledge under the chin, turned down from the
    light: on the frame it reads as a dark collar even with no line drawn. Down every column under the cheeks, from
    above the chin to the base, the front never falls back steeper than :data:`UNDERCUT`."""
    cf = kit["cf"]
    fig = cf.figure(rigs[who])
    depth = cf.front_of(fig.skin)
    head = Polygon(fig.parts.head)
    ys = np.arange(head.bounds[3] - 80.0, cf.BASE - 10.0, 2.0)
    for dx in (-90.0, -70.0, 70.0, 90.0):  # beside the muzzle, whose own relief is modelled
        near = -depth(np.full_like(ys, head.centroid.x + dx), ys)
        fall = np.diff(near) / 2.0
        assert fall.min() >= -UNDERCUT, (dx, float(ys[int(np.argmin(fall))]), float(fall.min()))


def test_the_flat_rest_arm_is_read_from_the_drawing(kit, rigs):
    cf = kit["cf"]
    for rig in rigs.values():
        flat = cf.flat_rest_arms(rig)
        torso = rig.look.drawing.torso
        for side in ("left", "right"):
            arm = flat[side]
            assert arm.width == torso.arm
            assert len(arm.path) >= 3 and (arm.path[0][0] < cf.CENTRE) == (side == "left")
    bear = cf.flat_rest_arms(rigs["bruno"])  # the flat's own numbers, measured off toon_torso.arm_path
    assert bear["left"].length == pytest.approx(77.6, abs=0.1)
    assert bear["right"].length == pytest.approx(81.9, abs=0.1)
    rabbit = cf.flat_rest_arms(rigs["mae"])
    assert rabbit["left"].length == pytest.approx(73.9, abs=0.1)
    assert rabbit["right"].length == pytest.approx(77.2, abs=0.1)


def test_an_arm_shows_only_where_it_is_in_front_of_the_skin(kit, rigs):
    cf = kit["cf"]
    fig = cf.figure(rigs["bruno"])
    chain = replace(fig.arms[0], lap=None, skin=None)  # the bare line: nothing laid on the lap
    joints = cf.reach(chain, chain.rest)
    ahead = cf.Joints(*(j + (0.0, 0.0, -400.0) for j in (joints.shoulder, joints.elbow, joints.wrist, joints.paw)))
    line, _ = cf.arm_line(chain, ahead)
    whole = np.linalg.norm(np.diff(line[:, :2], axis=0), axis=1).sum()
    assert cf.arm_shown(fig, chain, ahead) == pytest.approx(whole, rel=0.01)  # all in front: all of it shows
    behind = cf.Joints(*(j + (0.0, 0.0, 400.0) for j in (joints.shoulder, joints.elbow, joints.wrist, joints.paw)))
    assert cf.arm_shown(fig, chain, behind) == 0.0  # all inside or behind the body: none of it


@pytest.mark.parametrize("who", ["mae", "bruno"])
def test_the_resting_arm_folds_into_depth_and_shows_as_long_as_the_flats(kit, rigs, who):
    """The rigid bones (the Wow needs all their reach) fold at rest the way a seated arm does: the upper arm down
    the side inside the body, the forearm running down and forward onto the thigh. Seen from the front the arm shows
    from where it leaves the body to the wrist about as long as the flat draws it, the elbow inside the figure's
    outline, the arm as wide at the elbow as the flat's."""
    cf = kit["cf"]
    rig = rigs[who]
    fig = cf.figure(rig)
    flat = cf.flat_rest_arms(rig)
    outline = Polygon(fig.parts.body).buffer(0).union(Polygon(fig.parts.head).buffer(0))
    for chain in fig.arms:
        assert (chain.upper, chain.fore) == (cf.UPPER, cf.FORE)
        joints = cf.reach(chain, chain.rest)
        assert cf.arm_shown(fig, chain, joints) == pytest.approx(flat[chain.side].length, abs=1.0)
        elbow = ShapelyPoint(joints.elbow[0], joints.elbow[1])
        assert outline.buffer(-chain.radii[0]).contains(elbow)  # it does not poke out of the silhouette
        assert 2.0 * chain.radii[0] == pytest.approx(flat[chain.side].width)  # as wide at the elbow as the flat's arm


def test_a_shoulder_depth_that_cannot_show_the_flats_length_is_refused(kit, rigs, monkeypatch):
    """Each shoulder's depth is solved so its arm shows as long as the flat's; a depth range that holds no such depth
    stops the figure with the arm named, never a figure with the nearest arm."""
    cf = kit["cf"]
    monkeypatch.setattr(cf, "SHOULDER_BACK", (-5.0, 5.0))  # so far back the arm shows too short throughout
    with pytest.raises(cf.FigureError, match="left arm"):
        cf.figure.__wrapped__(rigs["mae"])  # built afresh, past the cache


WRIST_TAPER = (0.55, 0.8)  # the wrist's width over the elbow's: a forearm that narrows, never a roll of one width
FALL = 30.0  # degrees below level, at the least, that a resting forearm runs on screen from the elbow to the wrist


@pytest.mark.parametrize("who", ["mae", "bruno"])
def test_the_forearm_narrows_from_the_elbow_to_the_wrist(kit, rigs, who):
    """The upper arm keeps the elbow's width; from the elbow the forearm narrows all the way to the wrist."""
    cf = kit["cf"]
    fig = cf.figure(rigs[who])
    for chain in fig.arms:
        _, radii = cf.arm_line(chain, cf.reach(chain, chain.rest))
        elbow, wrist = radii[cf.ELBOW_AT], radii[-1]
        assert WRIST_TAPER[0] <= wrist / elbow <= WRIST_TAPER[1]
        assert np.all(np.diff(radii[cf.ELBOW_AT :]) < 0.0)  # narrowing at every step, no roll of one width
        assert np.allclose(radii[: cf.ELBOW_AT + 1], elbow)


def _paw(cf, chain, joints, who="bruno"):
    made = cf.arm_meshes(chain, joints, f"{who}-arm", f"{who}-pad")
    return made, made["paw"][0].vertices


@pytest.mark.parametrize("who", ["mae", "bruno"])
def test_the_paw_is_a_flattened_mitten_as_wide_and_tall_as_the_flats(kit, rigs, who):
    """Seen from the front the paw covers the flat paw's box: as wide, as tall, so as much wider than tall as the
    flat's; it is flat front to back, not a ball; its pad sits on its front and three toe marks on its lower front."""
    cf = kit["cf"]
    rig = rigs[who]
    fig = cf.figure(rig)
    boxes = cf._paws(rig)
    for chain in fig.arms:
        joints = cf.reach(chain, chain.rest)
        made, v = _paw(cf, chain, joints, who)
        (x0, y0), (x1, y1) = boxes[chain.side][0]
        width, height = np.ptp(v[:, 0]), np.ptp(v[:, 1])
        assert width == pytest.approx(x1 - x0, abs=1.0)
        assert height == pytest.approx(y1 - y0, abs=1.0)
        assert width / height == pytest.approx((x1 - x0) / (y1 - y0), rel=0.05)
        assert np.ptp(v[:, 2]) <= 0.65 * height  # flattened front to back: a mitten, not a ball
        toes = [m for m in made["pad"] if m.material == f"{who}-toe"]
        assert len(toes) == 1
        t = toes[0].vertices
        assert np.all(t[:, 1] > joints.paw[1])  # on the paw's lower half
        assert np.ptp(t[:, 0]) >= 0.4 * width  # three marks spread across it
        assert len({round(float(x)) for x in cf.toe_columns(chain)}) == 3


@pytest.mark.parametrize("who", ["mae", "bruno"])
def test_the_resting_paw_lies_down_and_forward_on_the_thigh(kit, rigs, who):
    """At rest the forearm runs down from the elbow at the side and forward onto the thigh, never level across the
    belly; the paw's toes point down and toward the lens."""
    cf = kit["cf"]
    fig = cf.figure(rigs[who])
    for chain in fig.arms:
        joints = cf.reach(chain, chain.rest)
        run = joints.wrist - joints.elbow
        fall = math.degrees(math.atan2(run[1], abs(run[0])))  # y is down
        assert fall >= FALL, (chain.side, fall)
        assert joints.wrist[2] < joints.elbow[2] - 20.0  # it comes forward
        _, v = _paw(cf, chain, joints, who)
        low, high = v[np.argmax(v[:, 1])], v[np.argmin(v[:, 1])]
        assert low[2] < high[2]  # the toes nearer the lens than the paw's top


@pytest.mark.parametrize("who", ["mae", "bruno"])
def test_the_paw_covers_the_forearms_end_and_its_whole_front_shows(kit, rigs, who):
    """As in the flat, the paw lies over its forearm's end: wherever the forearm's clay, as laid on the belly, runs
    within the paw's outline, its front is behind the paw's middle, so the paw's face covers it and no end of a tube
    shows on the pad. Every point of the paw that faces the lens lies in front of the skin, so the belly cuts no
    crescent out of it. Held at rest and with the paw raised."""
    cf = kit["cf"]
    fig = cf.figure(rigs[who])
    front = cf.front_of(fig.skin)
    for chain in fig.arms:
        for target in (chain.rest, chain.rest + np.array((0.0, -120.0, -40.0))):
            joints = cf.reach(chain, target)
            made, v = _paw(cf, chain, joints, who)
            outline = MultiPoint(v[:, :2]).convex_hull
            path, radii = cf.arm_line(chain, joints)
            under = contains_xy(outline, path[:, 0], path[:, 1])
            under[: cf.ELBOW_AT] = False
            assert under.any(), chain.side  # the forearm runs in under the paw
            assert np.all(path[under, 2] - radii[under] >= joints.paw[2]), chain.side
        joints = cf.reach(chain, chain.rest)
        made, v = _paw(cf, chain, joints, who)
        facing = made["paw"][0].normals[:, 2] < 0.0
        assert np.all(v[facing, 2] <= front(v[facing, 0], v[facing, 1]) + 1e-6), chain.side


@pytest.mark.parametrize("who", ["mae", "bruno"])
def test_the_resting_arm_shows_in_one_piece_and_its_shoulder_stays_under_the_skin(kit, rigs, who):
    """From the front a resting arm shows once, from where it leaves the body to the wrist: no sliver of the upper arm
    breaks the skin above it, and the shoulder's ball stays behind the skin's front."""
    cf = kit["cf"]
    fig = cf.figure(rigs[who])
    front = cf.front_of(fig.skin)
    for chain in fig.arms:
        joints = cf.reach(chain, chain.rest)
        assert len(cf.arm_pieces(fig, chain, joints)) == 1, chain.side
        s = chain.shoulder
        assert s[2] - chain.radii[0] >= float(front(np.array([s[0]]), np.array([s[1]]))[0])


def beside(chain_side: str, x: np.ndarray, edge: float) -> np.ndarray:
    """Where ``x`` falls short of a tuck's ``edge``: on the open side of the cover, which lies outward of it."""
    return x < edge if chain_side == "right" else x > edge


def test_an_arm_the_sofa_arm_covers_tucks_its_upper_arm_in_under_it(kit, rigs):
    """The sofa's arm covers Bruno's right side, as in the flat, so his right arm reads as tucked under it: none of
    its upper arm or shoulder shows beside the cover (a strip running up along its edge would show with no line to
    hide it in the plain look), and its forearm shows in one piece from the cover's edge to the paw. The shoulder sits
    just as deep as that takes, and the other arm keeps its own solve."""
    cf, study = kit["cf"], kit["study"]
    tuck = study.TUCKS["bruno"]
    fig, free = study.figure_of("bruno"), cf.figure(rigs["bruno"])
    chain = next(c for c in fig.arms if c.side == tuck.side)
    joints = cf.reach(chain, chain.rest)
    seen = cf.upper_seen(fig, chain, joints)
    assert len(seen) == 0 or not beside(chain.side, seen[:, 0], tuck.edge).any()
    line, shown = cf._shown(fig, chain, joints)
    out = shown & beside(chain.side, line[:, 0], tuck.edge)
    assert len(cf._pieces(line, out)) == 1
    assert abs(float(line[out, 0].max() if chain.side == "right" else line[out, 0].min()) - tuck.edge) <= 1.0
    nearer = replace(chain, shoulder=chain.shoulder - (0.0, 0.0, cf.TUCK_STEP))
    again = cf.upper_seen(fig, nearer, cf.reach(nearer, nearer.rest))
    assert len(again) and beside(chain.side, again[:, 0], tuck.edge).any()  # no deeper than it takes
    other = next(c for c in fig.arms if c.side != tuck.side)
    assert np.allclose(other.shoulder, next(c for c in free.arms if c.side != tuck.side).shoulder)


def test_the_tuck_lies_where_the_two_shot_draws_the_sofa_arm(kit, rigs):
    """The tuck's edge is the sofa arm stand-in's edge, as the two-shot sees it over Bruno's skin where his upper arm
    runs, a pixel or two inside it so nothing shows past the drawn arm."""
    study, cr = kit["study"], kit["cr"]
    performance = resting_performance(kit)
    room = type("R", (), {"takes": {"two": dict(TWO)}})()
    places = study.seats(room, performance)
    lens = cr.camera_of(TWO["eye"], TWO["look_at"], TWO["lens"])
    edge = study.cover_edge(places["bruno"], lens, study.figure_of("bruno"))
    assert study.TUCKS["bruno"].edge <= edge <= study.TUCKS["bruno"].edge + 3.0


def test_a_tuck_no_depth_can_keep_the_upper_arm_under_is_refused(kit, rigs):
    cf = kit["cf"]
    with pytest.raises(cf.FigureError, match="right arm"):
        cf.figure.__wrapped__(rigs["bruno"], cf.Tuck("right", 400.0))
    with pytest.raises(cf.FigureError, match="no side"):
        cf.Tuck("up", 400.0)


def test_the_ink_draws_one_outline_from_the_forearm_into_the_paw(kit, rigs):
    """The ID pass gives an arm its paw's colour, so the room's line runs round arm and paw as one shape and no ring
    is drawn where the forearm goes into the paw."""
    cr = kit["cr"]
    performance = resting_performance(kit)
    seat = cr.Seat((0.0, 0.0, 300.0), 0.16, False)
    parts = {
        "bruno": cr.posed_parts(
            "bruno", rigs["bruno"], kit["cf"].figure(rigs["bruno"]), performance.at("bruno", 0), seat
        )
    }
    meshes, _ = cr.id_materials(parts)
    by_part = {}
    k = 0
    for part in parts["bruno"]:
        by_part[part.id] = {meshes[k + i].material for i in range(len(part.meshes))}
        k += len(part.meshes)
    for side in ("left", "right"):
        assert by_part[f"bruno-arm-{side}"] == by_part[f"bruno-paw-{side}"] == by_part[f"bruno-pad-{side}"]


def test_each_figure_sits_on_its_cards_column_and_its_base_on_the_cushion(kit, rigs):
    """Each figure on its card's column, the sofa's arm in front of Bruno's right side as in the flat; each base on
    the cushion, behind its rounded front edge, so it presses into the seat and shadows it."""
    study, cr, cf = kit["study"], kit["cr"], kit["cf"]
    performance = resting_performance(kit)
    room = type("R", (), {"takes": {"two": dict(TWO)}})()
    places = study.seats(room, performance)
    lens = cr.camera_of(TWO["eye"], TWO["look_at"], TWO["lens"])
    x = float(cr.project([places["bruno"].at], lens)[0][0])
    assert x == pytest.approx(SEEN["two"]["bruno"][0], abs=1.5)
    assert float(cr.project([places["mae"].at], lens)[0][0]) > SEEN["two"]["mae"][0]  # her card's column cuts her
    for who in ("mae", "bruno"):
        posed = cr.posed(who, rigs[who], cf.figure(rigs[who]), performance.at(who, 0), places[who])
        v = np.concatenate([m.vertices for m in posed]) / 100.0
        base = v[:, 1] > -(cr.CUSHION_TOP - cr.SINK) - 0.005  # engine y is down: the lowest half centimetre
        assert v[base, 2].min() >= cr.CUSHION_FRONT + cr.CUSHION_EDGE


def silhouette_x(cr, meshes, lens) -> tuple[float, float]:
    xy = cr.project(np.concatenate([m.vertices for m in meshes]), lens)
    return float(xy[:, 0].min()), float(xy[:, 0].max())


def test_both_figures_sit_whole_inside_the_two_shot(kit, rigs):
    """Mae's card sits on a column the two-shot cuts at the frame's left edge, as the flat does: the clay moves her
    right along the cushion, just far enough that her whole silhouette keeps the frame's margin, and Bruno settles in
    front of her as before. The camera stays the room's, so the plates still fit it."""
    study, cr, cf = kit["study"], kit["cr"], kit["cf"]
    performance = resting_performance(kit)
    room = type("R", (), {"takes": {"two": dict(TWO)}})()
    places = study.seats(room, performance)
    lens = cr.camera_of(TWO["eye"], TWO["look_at"], TWO["lens"])
    seen = {
        who: silhouette_x(cr, cr.posed(who, rigs[who], cf.figure(rigs[who]), performance.at(who, 0), places[who]), lens)
        for who in places
    }
    assert seen["mae"][0] == pytest.approx(study.FRAME_MARGIN, abs=0.5)  # moved no further than it takes
    for lo, hi in seen.values():
        assert study.FRAME_MARGIN - 0.5 <= lo and hi <= cr.WIDTH - study.FRAME_MARGIN


def test_a_two_shot_frame_that_cuts_a_figure_is_refused(kit, rigs):
    study, cr, cf = kit["study"], kit["cr"], kit["cf"]
    performance = resting_performance(kit)
    room = type("R", (), {"takes": {"two": dict(TWO)}})()
    places = study.seats(room, performance)
    lens = cr.camera_of(TWO["eye"], TWO["look_at"], TWO["lens"])
    parts = {
        who: cr.posed_parts(who, rigs[who], cf.figure(rigs[who]), performance.at(who, 0), places[who]) for who in places
    }
    study.framed(parts, lens, 0)  # whole inside: nothing to refuse
    at = places["mae"].at
    cut = replace(places["mae"], at=(at[0] - 12.0, at[1], at[2]))  # 12 cm left: off the frame's edge
    parts["mae"] = cr.posed_parts("mae", rigs["mae"], cf.figure(rigs["mae"]), performance.at("mae", 0), cut)
    with pytest.raises(cr.RenderError, match="frame 7: mae"):
        study.framed(parts, lens, 7)


def test_the_drawn_arm_lies_over_the_clay_and_the_seat_strip_does_not(kit):
    """The flat's arm covers Bruno's right side: the front plate's arm, with its own line, goes over the finished
    frame, plain or inked. The seat strip beside it stays out, so the shadows the bases lay on the cushion stay."""
    cr = kit["cr"]
    assert len(cr.sofa()) == 4  # the arm stands in the passes: it bounces on him and the frame's arm covers him
    lens = cr.camera_of(TWO["eye"], TWO["look_at"], TWO["lens"])
    near = cr.sofa()[-1].vertices
    near = near[near[:, 2] < near[:, 2].min() + 1e-6]
    middle = cr.project(near, lens).mean(0).astype(int)
    front = np.zeros((cr.HEIGHT, cr.WIDTH, 4))
    front[:, :, :3] = (0.3, 0.1, 0.4)
    front[:, :, 3] = 1.0  # the whole plate opaque: only the arm may come through
    none = np.zeros((cr.HEIGHT, cr.WIDTH, 4))  # an ID pass with no figure in it
    arm = cr.drawn_arm(front, lens, none, [])
    assert arm[middle[1], middle[0], 3] == 1.0
    strip = (middle[1], middle[0] - 200)  # along the seat, left of the arm
    assert arm[strip[0], strip[1], 3] == 0.0
    picture = np.ones((cr.HEIGHT, cr.WIDTH, 4))
    out = cr.over(picture, arm)
    assert out[middle[1], middle[0], :3] == pytest.approx((0.3, 0.1, 0.4))
    assert out[strip[0], strip[1], :3] == pytest.approx((1.0, 1.0, 1.0))
    empty = cr.drawn_arm(np.zeros_like(front), lens, none, [])
    assert empty[..., 3].max() == 0.0  # a plate with no arm lays nothing


def test_the_drawn_arm_takes_in_its_inner_side_on_a_camera_that_sees_it(kit):
    """A lens left of the arm sees its inner side, which covers Bruno as its front does; the cushion beside it stays."""
    cr = kit["cr"]
    lens = cr.camera_of((-0.6, 0.75, -1.2), (-0.2, 0.5, 0.2), TWO["lens"])
    front = np.ones((cr.HEIGHT, cr.WIDTH, 4))
    arm = cr.drawn_arm(front, lens, np.zeros_like(front), [])
    side = cr.project([cr.engine((-0.19, 0.5, 0.25))], lens)[0].astype(int)
    assert arm[side[1], side[0], 3] == 1.0
    cushion = cr.project([cr.engine((-0.35, cr.CUSHION_TOP, 0.25))], lens)[0].astype(int)
    assert arm[cushion[1], cushion[0], 3] == 0.0
    # below the cushion's top the cushion hides the arm's inner side: a base resting by the arm is never cut there
    seat = cr.project([cr.engine((-0.23, cr.CUSHION_TOP + 0.005, 0.1))], lens)[0].astype(int)
    assert arm[seat[1], seat[0], 3] == 0.0


def test_the_drawn_arm_never_covers_a_paw_the_id_pass_shows_in_front_of_it(kit):
    """The ID pass draws the arm stand-in black, so a paw seen there, within the paw's own outline on the frame, is in
    front of the sofa's arm: the drawn arm and its line leave it clear. The forearm in the paw's colour beyond that
    outline, and Bruno's side, run under the flat's arm as in the flat, and it still covers them."""
    cr, ci = kit["cr"], kit["ci"]
    lens = cr.camera_of(TWO["eye"], TWO["look_at"], TWO["lens"])
    near = cr.sofa()[-1].vertices
    near = near[near[:, 2] < near[:, 2].min() + 1e-6]
    x, y = cr.project(near, lens).mean(0).astype(int)
    front = np.ones((cr.HEIGHT, cr.WIDTH, 4))
    ids = np.zeros((cr.HEIGHT, cr.WIDTH, 4))
    ids[..., 3] = 1.0
    ids[y - 20 : y + 20, x - 40 : x, :3] = ci.id_colour("bruno", "paw-right")  # the paw
    ids[y - 80 : y - 20, x - 40 : x, :3] = ci.id_colour("bruno", "paw-right")  # its forearm, above it
    ids[y - 20 : y + 20, x : x + 40, :3] = ci.id_colour("bruno", "skin")
    paw = np.array(((x - 40, y - 20), (x, y - 20), (x, y + 20), (x - 40, y + 20)), float)
    arm = cr.drawn_arm(front, lens, ids, [paw])
    assert np.all(arm[y - 18 : y + 18, x - 38 : x - 2, 3] == 0.0)  # the paw stays in front
    line = math.ceil(ci.ROOM_LINE.heavy / 2.0)  # the paw keeps its own line, on his side of its edge too
    assert np.all(arm[y - 18 : y + 18, x : x + line, 3] == 0.0)
    assert np.all(arm[y - 18 : y + 18, x + line + 1 : x + 38, 3] == 1.0)  # his side goes under
    assert np.all(arm[y - 78 : y - 20 - line - 1, x - 38 : x - 2, 3] == 1.0)  # so does the forearm


def test_the_room_line_is_read_from_the_rooms_own_plates(kit):
    ci = kit["ci"]
    assert ci.ROOM_LINE == ci.Line("#000000", 9.0, 4.0)  # lounge_plates.INK, INK_WIDTH, FINE_WIDTH


def test_the_ink_draws_the_rooms_line_round_the_figures_and_the_fine_one_inside(kit):
    ci = kit["ci"]
    ids = np.zeros((60, 120, 4))
    ids[..., 3] = 1.0
    ids[:, 40:, :3] = ci.id_colour("bruno", "skin")  # the figure from column 40
    ids[:, 80:, :3] = ci.id_colour("bruno", "arm-left")  # an arm on it from column 80
    plain = np.zeros((60, 120, 4))
    plain[..., :3], plain[..., 3] = 0.6, 1.0
    inked = ci.ink(plain, ids, ci.ROOM_LINE)
    row = inked[30, :, :3]
    line = np.all(np.abs(row - 0.0) < 0.02, axis=1)  # the room's ink is black
    heavy = np.nonzero(line[20:60])[0] + 20
    fine = np.nonzero(line[65:100])[0] + 65
    assert len(heavy) == pytest.approx(9, abs=1) and heavy.min() < 40 <= heavy.max()  # straddles the outline
    assert len(fine) == pytest.approx(4, abs=1)
    assert np.allclose(inked[30, :25, :3], 0.6) and np.allclose(inked[30, 50:70, :3], 0.6)  # nothing else changes
    assert np.allclose(inked[30, 110:, :3], 0.6)


def test_each_part_has_its_own_id_colour_and_the_figures_tell_apart(kit):
    ci = kit["ci"]
    colours = {(who, part): tuple(ci.id_colour(who, part)) for who in ("mae", "bruno") for part in ci.PARTS}
    assert len(set(colours.values())) == len(colours)
    assert all(any(c) for c in colours.values())  # none is the sofa's black
    for (who, _), colour in colours.items():
        assert (colour[2] > 0.5) == (who == "bruno")
    with pytest.raises(ci.InkError, match="no part"):
        ci.id_colour("mae", "tail")


def test_an_engine_pass_holds_the_gpu_lock(kit, tmp_path, monkeypatch):
    cr = kit["cr"]
    lock = tmp_path / "gpu.lock"
    monkeypatch.setenv("SRSTUDIO_GPU_LOCK", str(lock))
    seen = '"$(dirname "$0")/seen"'
    body = f'if flock -n "{lock}" true; then echo free > {seen}; else echo held > {seen}; fi; printf png > plate.png'
    monkeypatch.setenv("SRSTUDIO_ENGINE", str(fake_engine(tmp_path, body)))
    cr.render(small_plate(kit), tmp_path / "cache", "P", cr.Spent.new())
    assert (tmp_path / "seen").read_text().strip() == "held"


def test_a_pat_is_his_arm_toward_her_paw_through_the_shot_and_nothing_outside_it(kit):
    pf, reel = kit["pf"], kit["reel"]
    pat = 14.15
    assert pf.pat_hand(reel, pat, pat - 0.5, pat + 1.2, pat - 0.6) == ()
    before = pf.pat_hand(reel, pat, pat - 0.5, pat + 1.2, pat - 0.2)
    up = pf.pat_hand(reel, pat, pat - 0.5, pat + 1.2, pat + 0.04 + reel.PAT_EVERY)
    assert len(before) == len(up) == 1 and before[0].root == up[0].root
    assert up[0].degrees == pytest.approx(before[0].degrees + reel.PAT_RISE)
    assert before[0].root[0] < 165.0  # his arm on her side: the left chain's


# --- a reel of its own: the pipeline reads the staging of the reel it is bound to -------------------------------------


@pytest.fixture()
def grown(kit):
    """The pipeline bound to grown-on-me for one test, and back to it-autoplayed after it."""
    sys.path.insert(0, str(ROOT / "episodes"))
    try:
        import grown_on_me_data
    finally:
        sys.path.remove(str(ROOT / "episodes"))
    before = kit["study"].reel
    kit["study"].bind(grown_on_me_data)
    yield grown_on_me_data
    kit["study"].bind(before)


def test_grown_on_mes_speakers_are_names_or_roles_of_the_cast_bible(grown):
    """First delivery refuses a speaker the bible does not know (ADR 0069); the TV's voice is the role narrator."""
    from srstudio import bible, bible_check

    sys.path.insert(0, str(ROOT / "episodes"))
    try:
        from posts.grown_on_me import RELEASE
    finally:
        sys.path.remove(str(ROOT / "episodes"))
    library = bible.load(ROOT / "bible")
    world = bible_check.world_of_release(RELEASE)
    for sk in (grown.SKETCH, grown.VARIANT):
        unknown = [
            s.name
            for s in sk.speakers
            if not library.is_role(s.name) and not any(c.world == world for c in library.named(s.name))
        ]
        assert not unknown, f"{sk.slug}: {unknown} are neither characters of {world} nor roles of the bible"


def _placed(sk, takes: float = 0.5):
    """The sketch placed as its recording would place it: each line said at its scripted beat, ``takes`` long."""
    starts = {b.line: b.start for b in sk.beats if b.line is not None}
    return sketch_mod.place(sk, [[starts[k]] for k in range(len(sk.lines))], [starts[k] + takes for k in starts])


def test_grown_on_mes_last_click_comes_straight_off_fine_and_every_caption_holds(grown):
    beats = _placed(grown.SKETCH)
    fine = next(b for b in beats if b.line == len(grown.LINES) - 1)
    click = grown.clicks(beats)["off"]
    assert fine.start + 0.5 < click <= fine.start + 0.5 + sketch_mod.BLANK_GAP + 1e-6  # off the word, not later
    shown = [b for k, b in enumerate(beats) if k == 0 or beats[k - 1].caption != b.caption]
    for a, b in zip(shown, shown[1:], strict=False):
        if a.caption:
            assert b.start - a.start >= grown.SKETCH.caption_min - 1e-6, a.caption
    assert grown.SKETCH.end == pytest.approx(scripting_at(grown.SKETCH.beats, "off") + grown.DARK)


def test_grown_on_mes_acts_name_expressions_the_rigs_have(grown):
    from srstudio import toon

    for acts in (grown.ACTS, grown.VARIANT_ACTS):
        for who, row in acts.items():
            for act in row:
                assert act.eyes in toon.EYES and act.mouth in toon.MOUTHS and act.arms in toon.ARMS, (who, act)


def test_grown_on_mes_room_drops_dark_on_the_last_click(grown):
    for sk in (grown.SKETCH, grown.VARIANT):
        beats = _placed(sk)
        click = grown.clicks(beats)["off"]
        keys = grown.blackout(beats)
        assert keys[0] == (0.0, 0.0) and keys[-1] == (click, grown.BLACKOUT)
        assert all(v == 0.0 for t, v in keys if t < click)
    assert 0.5 <= grown.BLACKOUT < 1.0  # dark, and the two of them still there in it


def test_grown_on_mes_variant_ends_on_the_held_line_then_the_click(grown):
    beats = _placed(grown.VARIANT)
    assert beats[-1].event == "off" and beats[-1].caption == ""
    assert len(grown.VARIANT.lines) == len(grown.LINES) - 1
    assert grown.VARIANT.end == pytest.approx(scripting_at(grown.VARIANT.beats, "off") + grown.DARK)


def test_the_pipeline_takes_the_bound_reels_shot_names_and_places(kit, grown):
    pf, study = kit["pf"], kit["study"]
    assert study.reel is grown and study.study.reel is grown
    assert pf.shot_names(grown) == {grown.TWO: "two", grown.MAE_C: "mae", grown.BRUNO_C: "bruno", grown.MENU: "menu"}
    assert study.study.RIGS["mae"][1] == grown.MAE_AT and study.study.RIGS["bruno"][2] == grown.BRUNO_CLOSE


def test_binding_back_restores_the_reel_the_study_was_made_on(kit):
    study = kit["study"]
    assert study.reel.SLUG == "it-autoplayed" and study.study.reel.SLUG == "it-autoplayed"


def test_a_menu_shot_is_in_the_record_and_no_frame_of_it_is_rendered(kit):
    shots = [dict(name="two", start=0.0, end=0.1), dict(name="menu", start=0.1, end=0.2),
             dict(name="mae", start=0.2, end=0.25)]  # fmt: skip
    data = record(frames=6, shots=shots, cast={who: [resting_frame()] * 6 for who in ("mae", "bruno")})
    performance = kit["pf"].Performance.parse(data)
    assert [performance.shot(n) for n in range(6)] == ["two", "two", "two", "menu", "menu", "mae"]
    assert performance.rendered() == [0, 1, 2, 5]


def test_a_reels_own_keys_move_the_clay_and_its_hold_puts_the_remote_in_her_paw(kit, grown):
    pf = kit["pf"]
    beats = grown.SKETCH.beats
    px = 2.0
    blast = at_event(beats, "blast")
    for who in ("mae", "bruno"):
        lift, _, _, arms, _ = pf.gesture(grown, beats, who, blast + 0.2, "two", px)
        assert lift == pytest.approx(-grown.BLAST_LIFT / px) and arms == ()  # both jerk, on every camera
        assert pf.gesture(grown, beats, who, blast + 0.2, "mae", px)[0] == pytest.approx(lift)
    _, tilt, _, _, _ = pf.gesture(grown, beats, "bruno", blast + 0.2, "two", px)
    assert tilt == pytest.approx(grown.BLAST_TILT)
    slow = at_event(beats, "slow")
    assert pf.gesture(grown, beats, "mae", slow - 0.1, "mae", px)[2] == pytest.approx(0.0)
    assert pf.gesture(grown, beats, "mae", slow + 1.3, "mae", px)[2] == pytest.approx(grown.TURN_TO)
    assert pf.gesture(grown, beats, "mae", 1.0, "two", px)[4] == "remote"
    assert pf.gesture(grown, beats, "mae", grown.clicks(beats)["gone"], "mae", px)[4] == "remote-up"
    assert pf.gesture(grown, beats, "bruno", 1.0, "two", px)[4] == ""


def test_a_reel_without_keys_keeps_it_autoplayeds_gasp_and_hands(kit):
    pf, reel = kit["pf"], kit["reel"]
    beats = reel.SKETCH.beats
    lift, tilt, face, arms, holds = pf.gesture(reel, beats, "bruno", reel.GASP_SNAPS, "two", 2.0)
    assert (lift, tilt) == pf.body_motion(reel, beats, "bruno", reel.GASP_SNAPS, "two", 2.0)
    assert face == 0.0 and holds == ""
    sting = at_event(beats, "sting")
    assert len(pf.gesture(reel, beats, "bruno", sting + reel.WOW_LATE + 0.2, "two", 2.0)[3]) == 2


def at_event(beats, kind):
    from srstudio.scripting import at

    return at(beats, kind)


def test_the_held_remote_is_a_clay_part_in_the_paw_of_her_outer_arm(kit, rigs):
    cr, cf = kit["cr"], kit["cf"]
    rig, fig = rigs["mae"], cf.figure(rigs["mae"])
    rest = parts_by_id(cr.local_parts("mae", rig, fig, frame_of(kit)))
    held = parts_by_id(cr.local_parts("mae", rig, fig, frame_of(kit, holds="remote")))
    up = parts_by_id(cr.local_parts("mae", rig, fig, frame_of(kit, holds="remote-up")))
    assert "mae-remote" not in rest and "mae-remote" in held and "mae-remote" in up
    side = cr.HOLD_SIDE
    paw = points(held[f"mae-paw-{side}"]).mean(0)
    remote = points(held["mae-remote"])
    lo, hi = remote.min(0), remote.max(0)
    assert lo[0] < paw[0] < hi[0] and lo[1] < paw[1] < hi[1]  # it passes through her paw
    assert points(up[f"mae-paw-{side}"]).mean(0)[1] < paw[1] - 20.0  # raised to click
    other = "left" if side == "right" else "right"
    assert np.allclose(points(held[f"mae-paw-{other}"]), points(rest[f"mae-paw-{other}"]))
    names = {m.material for m in held["mae-remote"].meshes}
    assert names == {"mae-remote", "mae-remote-key"}
    assert {m.id for m in cr.materials("mae", rig, held["mae-remote"].meshes)} == names


def test_a_held_remote_and_a_gesture_on_the_same_arm_are_refused(kit, rigs):
    cr, cf = kit["cr"], kit["cf"]
    rig, fig = rigs["mae"], cf.figure(rigs["mae"])
    chain = next(c for c in fig.arms if c.side == cr.HOLD_SIDE)
    root = [float(chain.shoulder[0]), float(chain.shoulder[1])]
    arm = dict(root=root, degrees=90.0, length=60.0, width=20.0)
    with pytest.raises(cf.FigureError, match="two hands"):
        cr.local_parts("mae", rig, fig, frame_of(kit, holds="remote", arms=[arm]))


def test_the_remote_has_its_own_id_colour(kit):
    ci = kit["ci"]
    assert "remote" in ci.PARTS
    assert any(ci.id_colour("mae", "remote"))


def test_the_clay_staging_takes_out_the_flat_remote_and_keeps_the_tv(kit, grown):
    study = kit["study"]
    stood = study.stand_ins(grown)
    try:
        assert grown.toon_everyday.remote is not kit["study"].real_everyday.remote
        assert grown.toon_everyday.tv_browse is kit["study"].real_everyday.tv_browse
        assert grown.toon_pair.figure is study._nothing and grown.toon_bed.swung_arm is study._no_arm
    finally:
        stood.restore()
    assert grown.toon_everyday is kit["study"].real_everyday
