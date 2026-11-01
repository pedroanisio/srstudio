"""A rigid proxy drawn as cel plates (ADR 0088): typed views and recipes, bands and ink, layers split for the people
and the wheels, refusals before any render, and a camera that lands where the engine draws."""

import numpy as np
import pytest

from srstudio import clay, plates, proxy

MINT = ("#6aa98a", "#8fd3ad", "#b4ecc8", "#e9fff3")
TAN = ("#b58a60", "#deb58c", "#eccba7", "#f6e2c8")
BLACK = ("#0c0a10", "#17141d", "#2a2733", "#4a4656")
RECIPE = proxy.Recipe(
    tones={"body": MINT, "seat": TAN, "tire": BLACK, "well": BLACK},
    behind=frozenset({"seat"}),
    under=frozenset({"tire"}),
    quiet=(("tire", "well"),),
)
VIEW = proxy.View((300.0, -80.0, -500.0), (0.0, -60.0, 0.0), 24.0, size=(270, 480))


def ball(material="body", at=(0.0, -60.0, 0.0), r=20.0):
    model = clay.Model()
    model.ell(material, at, (r, r, r))
    return model.meshes()


def test_a_view_refuses_a_lens_or_a_frame_that_cannot_exist():
    for bad in (dict(fov=0.0), dict(fov=180.0), dict(stretch=0.0), dict(size=(0, 100)), dict(size=(101, 100))):
        kw = dict(position=(0.0, 0.0, -10.0), target=(0.0, 0.0, 0.0), fov=20.0) | bad
        with pytest.raises(proxy.ProxyError):
            proxy.View(**kw)
    with pytest.raises(proxy.ProxyError):
        proxy.View((1.0, 1.0, 1.0), (1.0, 1.0, 1.0), 20.0)


def test_a_point_behind_the_lens_is_refused():
    with pytest.raises(proxy.ProxyError, match="behind the lens"):
        VIEW.project([VIEW.position])


def test_a_recipe_refuses_what_it_cannot_draw():
    for bad in (
        dict(tones={}),
        dict(tones={"a": ("#000",) * 4}),
        dict(tones={"a": MINT}, behind=frozenset({"b"})),
        dict(tones={"a": MINT}, under=frozenset({"b"})),
        dict(tones={"a": MINT}, quiet=(("a", "b"),)),
        dict(tones={"a": MINT}, thresholds=(0.5, 0.4, 0.6)),
        dict(tones={"a": MINT}, oversample=0),
        dict(tones={f"p{k}": MINT for k in range(65)}),
    ):
        with pytest.raises(proxy.ProxyError):
            proxy.Recipe(**bad)


def test_a_mesh_outside_the_recipe_is_refused_before_any_render(tmp_path):
    never = tmp_path / "no-engine"
    with pytest.raises(proxy.ProxyError, match="unknown"):
        proxy.layers(ball("glass"), VIEW, RECIPE, engine=never, cache=tmp_path / "cache")
    assert not (tmp_path / "cache").exists()


def test_a_recipe_with_no_mesh_under_the_car_is_refused_before_any_render(tmp_path):
    with pytest.raises(proxy.ProxyError, match="no mesh"):
        proxy.layers(ball("body"), VIEW, RECIPE, engine=tmp_path / "no-engine", cache=tmp_path / "cache")


def test_every_part_keeps_a_colour_clear_of_the_tone_curve():
    recipe = proxy.Recipe(tones={f"p{k}": MINT for k in range(64)})
    colours = [recipe.ids[name] for name in recipe.names]
    assert len(set(colours)) == 64
    assert max(max(colour) for colour in colours) * proxy.ID_GAIN < 200


def test_a_blended_edge_pixel_is_refilled_from_its_neighbours():
    body, seat, stray = (np.array(RECIPE.ids[n]) * proxy.ID_GAIN for n in ("body", "seat", "tire"))
    ids = np.zeros((12, 12, 4), np.uint8)
    ids[..., 3] = 255
    ids[:, :6, :3], ids[:, 6:, :3] = body, seat
    ids[5, 6, :3] = stray
    part = proxy.read_parts(ids, RECIPE)
    assert set(np.unique(part)) == {RECIPE.names.index("body"), RECIPE.names.index("seat")}


def test_the_light_lands_on_the_palette_and_ink_runs_where_parts_meet_but_not_inside_a_family():
    part = np.zeros((40, 40), int)
    part[:, 20:] = RECIPE.names.index("seat")
    part[:, :20] = RECIPE.names.index("body")
    ids = np.zeros((40, 40, 4), np.uint8)
    ids[..., 3] = 255
    ids[..., :3] = (np.array([RECIPE.ids[RECIPE.names[k]] for k in range(4)]) * proxy.ID_GAIN)[part]
    lit = np.full((40, 40, 4), 255, np.uint8)
    rgba, seen = proxy.composite(lit, ids, RECIPE)
    assert (seen == part).all()
    assert rgba[20, 2, :3] == pytest.approx(proxy.rgb(MINT[3]), abs=2 / 255)
    assert rgba[20, 38, :3] == pytest.approx(proxy.rgb(TAN[3]), abs=2 / 255)
    assert rgba[20, 20, :3] == pytest.approx(proxy.rgb(RECIPE.ink.colour), abs=30 / 255)
    quiet = np.full((40, 40), RECIPE.names.index("tire"))
    quiet[:, 20:] = RECIPE.names.index("well")
    ids[..., :3] = (np.array([RECIPE.ids[RECIPE.names[k]] for k in range(4)]) * proxy.ID_GAIN)[quiet]
    rgba, _ = proxy.composite(lit, ids, RECIPE)
    assert rgba[20, 20, :3] == pytest.approx(proxy.rgb(BLACK[3]), abs=2 / 255)


def test_the_plates_leave_a_hole_for_what_goes_under_with_no_ink_left_on_the_road():
    tire = RECIPE.names.index("tire")
    part = np.full((60, 60), -1)
    part[:30] = RECIPE.names.index("body")
    part[30:50, 20:40] = tire
    back, front = proxy.split(np.ones((60, 60, 4)), part, RECIPE)
    assert back[40, 30, 3] == 0 and front[40, 30, 3] == 0
    assert back[10, 30, 3] == 1 and front[10, 30, 3] == 1
    assert back[51, 30, 3] == 0


def test_what_a_tyre_encloses_goes_with_the_tyre():
    part = np.full((60, 60), -1)
    part[20:50, 20:50] = RECIPE.names.index("tire")
    part[30:34, 30:34] = RECIPE.names.index("well")
    back, front = proxy.split(np.ones((60, 60, 4)), part, RECIPE)
    assert back[32, 32, 3] == 0 and front[32, 32, 3] == 0


def test_what_stands_behind_the_people_stays_on_the_back_plate_only():
    part = np.full((60, 60), RECIPE.names.index("seat"))
    part[:, 30:] = RECIPE.names.index("body")
    back, front = proxy.split(np.ones((60, 60, 4)), part, RECIPE)
    assert back[30, 5, 3] == 1 and front[30, 5, 3] == 0
    assert front[30, 50, 3] == 1


def test_a_disc_is_found_only_when_it_faces_the_lens():
    view = proxy.View((0.0, -50.0, -600.0), (0.0, -50.0, 0.0), 20.0, size=(540, 960))
    assert view.disc((0.0, -50.0, -70.0), 17.0, facing=-1) is not None
    assert view.disc((0.0, -50.0, 70.0), 17.0, facing=1) is None


def test_a_disc_turned_by_its_groups_lands_where_the_lens_puts_it():
    view = proxy.View((420.0, -60.0, -220.0), (250.0, -80.0, -115.0), 18.0, stretch=1.16)
    centre = (100.0, -25.0, -67.0)
    radius = 17.0
    disc = view.disc(centre, radius, facing=-1)
    a, b = np.radians((disc.tilt, disc.turn))

    def turn(r):
        return np.array([[np.cos(r), -np.sin(r)], [np.sin(r), np.cos(r)]])

    matrix = turn(a) @ np.diag((disc.stretch, disc.squash)) @ turn(b)
    assert 0 < disc.squash <= disc.stretch
    for dx, dy in ((radius, 0.0), (0.0, radius), (-radius * 0.6, radius * 0.8)):
        seen = view.project([(centre[0] + dx, centre[1] + dy, centre[2])])[0] - (disc.x, disc.y)
        assert matrix @ (dx, dy) == pytest.approx(seen, abs=5.0)


def test_the_view_lands_within_a_pixel_of_what_the_engine_draws(scene_render, tmp_path):
    """The registration gate of DRAWING.md: plates.Camera and View.project agree on a frame, off axis and stretched."""
    spots = {"a": (-40.0, -20.0, -30.0), "b": (30.0, -130.0, 40.0), "c": (80.0, -40.0, -30.0)}
    recipe = proxy.Recipe(tones={name: MINT for name in spots})
    view = proxy.View((260.0, -70.0, -420.0), (20.0, -80.0, 0.0), 20.0, stretch=1.1, size=(270, 480))
    meshes = [mesh for name, at in spots.items() for mesh in ball(name, at, 7.0)]
    _, part = proxy.picture(meshes, view, recipe, engine=scene_render, cache=tmp_path)
    size = recipe.oversample
    for name, at in spots.items():
        rows, cols = np.nonzero(part == recipe.names.index(name))
        assert len(rows) > 400, name
        seen = np.array([cols.mean() + 0.5, rows.mean() + 0.5]) / size
        assert np.linalg.norm(seen - view.project([at])[0]) <= 1.0, name


def test_layers_are_the_same_bytes_on_a_warm_rebuild_and_render_nothing_new(scene_render, tmp_path, monkeypatch):
    meshes = [*ball("body"), *ball("tire", (0.0, -25.0, -60.0), 20.0), *ball("seat", (0.0, -90.0, 0.0), 10.0)]
    view = proxy.View((300.0, -80.0, -500.0), (0.0, -60.0, 0.0), 24.0, size=(136, 240))
    first = proxy.layers(meshes, view, RECIPE, engine=scene_render, cache=tmp_path)
    assert first.back.shape == first.front.shape == first.under.shape == (240, 136, 4)

    run = plates.subprocess.run

    def refuse(command, *args, **kw):
        assert str(scene_render) not in map(str, command), "a warm rebuild rendered"
        return run(command, *args, **kw)

    monkeypatch.setattr(plates.subprocess, "run", refuse)
    second = proxy.layers(meshes, view, RECIPE, engine=scene_render, cache=tmp_path)
    assert (first.back == second.back).all() and (first.under == second.under).all()
    first.write(tmp_path / "out", "shot")
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == ["shot-back.png", "shot-front.png", "shot-under.png"]
