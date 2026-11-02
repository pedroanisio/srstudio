"""The clay look study (examples/clay_sofa): Mae and Bruno as clay figures seated in the sofa room.

The figures keep the drawing: each part's outline is the drawn outline, the face is the rig's own layers, the arms at
rest are the pose's own. They sit on the room's cushion, as the room's cameras see it (checked against the room
record's own projection), without passing through the arm or each other. The performance record of the reel is read
strictly, and the passes are put together as the study says. The engine runs only as a stand-in script here: the study
renders its passes outside this suite.
"""

import json
import os
import stat
import sys
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import Polygon

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
        import clay_figure
        import clay_room
        import clay_sofa_study
        import performance
    finally:
        sys.path[:] = path
        os.umask(mask)
    return dict(cf=clay_figure, cr=clay_room, study=clay_sofa_study, pf=performance)


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
        volumes = [fig.body, fig.head, *fig.ears, *(limb.volume for limb in cf.limbs(rig, "desk"))]
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
    pictures = [cf.head_textures(rig, fig, face)[0] for face in (rest, talking, blinking)]
    assert pictures[0].shape == pictures[1].shape == pictures[2].shape
    assert not np.array_equal(pictures[0], pictures[1]) and not np.array_equal(pictures[0], pictures[2])
    assert rest.key() != talking.key() != blinking.key()


def test_the_paws_lie_on_the_lap_and_a_pose_the_study_does_not_model_is_refused(kit, rigs):
    cf = kit["cf"]
    for rig in rigs.values():
        fig = cf.figure(rig)
        limbs = cf.limbs(rig, "desk")
        assert len(limbs) == 4  # two forearms, two paws
        for k, limb in enumerate(limbs):  # each part lies on the body and on the parts laid before it
            surface = cf._surface(fig.body.front, [earlier.volume.front for earlier in limbs[:k]])
            rim = limb.volume.back[-cf.SPOKES :]
            under = surface(rim[:, 0], rim[:, 1])
            assert (rim[:, 2] >= under - 1e-6).all()  # its rim on what it lies on or in it, never in front of it
            assert (limb.volume.front[:, 2] < under.min()).any()  # and the limb stands out of it
        with pytest.raises(cf.FigureError, match="type"):
            cf.limbs(rig, "type")


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


def test_a_seat_keeps_the_card_size_its_back_on_the_sofa_and_the_arm_clear(kit, rigs):
    cr = kit["cr"]
    lens = cr.camera_of(TWO["eye"], TWO["look_at"], TWO["lens"])
    fig = kit["cf"].figure(rigs["bruno"])
    back_at, right = 0.5, -0.2
    seat = cr.seat_of(fig, (-0.391, 0.374, 0.3), lens, 1.2, False, back_at, right)
    x, _, z = seat.at[0] / 100.0, seat.at[1], seat.at[2] / 100.0
    per = seat.per / 100.0
    assert z + fig.body.depth[1] * per == pytest.approx(back_at, abs=1e-4)
    assert x + (fig.body.front[:, 0].max() - cr.SEAT_X) * per <= right + 1e-6
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


def test_the_pair_sits_clear_of_the_arm_and_of_each_other(kit, rigs, tmp_path):
    study, cr = kit["study"], kit["cr"]
    performance = resting_performance(kit)
    room = type("R", (), {"takes": {"two": dict(TWO)}})()
    places = study.seats(room, performance)
    posed = {
        who: cr.posed(
            who, rigs[who], kit["cf"].figure(rigs[who]), performance.at(who, 0), places[who], study.COATS[who]
        )
        for who in ("mae", "bruno")
    }
    assert cr.clearance(posed["bruno"], posed["mae"]) >= study.GAP - 0.0006
    right = max(float(m.vertices[:, 0].max()) for m in posed["bruno"] if "body" in m.material) / 100.0
    assert right <= cr.ARM_INNER
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
               arms=[])  # fmt: skip
    row.update(change)
    return row


def record(**change) -> dict:
    data = dict(
        schema="clay-sofa.performance/1.1.0",
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
        (record(schema="clay-sofa.performance/1.0.0"), "schema"),
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
    assert (out[:, 1:8, 0] < 0.8 * 0.6).all()  # darkened by its shadow
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
    assert study.frames_of(0.0, 4.6) == (0, 110)
    assert study.frames_of(4.6, 6.65) == (111, 159)
    assert study.frames_of(6.65, 7.95) == (160, 190)
    assert [study.take_of(n) for n in (0, 110, 111, 159, 160, 190)] == ["two", "two", "mae", "mae", "bruno", "bruno"]


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


def test_the_study_writes_nothing_others_can_read(kit, tmp_path):
    cr = kit["cr"]
    mask = os.umask(0o077)
    try:
        cr.write(tmp_path / "sub" / "f.png", picture(0.5))
    finally:
        os.umask(mask)
    assert stat.S_IMODE((tmp_path / "sub").stat().st_mode) == 0o700
    assert stat.S_IMODE((tmp_path / "sub" / "f.png").stat().st_mode) == 0o600
    assert json.loads(json.dumps(asdict(resting_performance(kit))))["schema"].endswith("1.1.0")
