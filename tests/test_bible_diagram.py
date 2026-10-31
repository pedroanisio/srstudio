"""The relationship diagram is laid out by code that leaves no name over another, and refuses what it cannot draw."""

import pytest

from srstudio import bible
from srstudio import bible_diagram as diagram
from srstudio.cast_card import Lettering
from srstudio.sample import SYSTEM_FONTS
from support.bible_docs import cast_document, character, pair, pairs_document, write

FIXTURE = next(f for f in SYSTEM_FONTS if f.exists()).read_bytes()  # measures the names; never a face of the picture
FACES = Lettering(FIXTURE, FIXTURE)


def panel(names: list[str], edges: list[tuple[str, str]]) -> diagram.Panel:
    return diagram.Panel("okayville", {n: n.capitalize() for n in names}, {e: ("work", 1) for e in edges})


def test_a_relation_has_the_kind_of_the_first_word_it_holds():
    assert diagram.kind_of("father and son")[0] == "family"
    assert diagram.kind_of("Coworkers at the office")[0] == "work"
    assert diagram.kind_of("barista and customer")[0] == "service"
    assert diagram.kind_of("a rivalry")[0] == "other"
    assert diagram.kind_of("")[0] == "other"


def test_two_lines_cross_only_away_from_a_shared_end():
    square = {"a": (0, 0), "b": (10, 10), "c": (0, 10), "d": (10, 0), "e": (20, 5)}
    assert diagram.crossings(square, [("a", "b"), ("c", "d")]) == 1
    assert diagram.crossings(square, [("a", "b"), ("a", "d")]) == 0  # a shared end is not a crossing
    assert diagram.crossings(square, [("a", "d"), ("d", "e")]) == 0
    assert diagram.crossings(square, [("a", "b"), ("c", "d"), ("a", "d")]) == 1


def test_names_overlap_when_their_boxes_are_closer_than_the_gap():
    size = {"a": (100, 50), "b": (100, 50), "c": (100, 50)}
    where = {"a": (0, 0), "b": (110, 0), "c": (300, 0)}
    assert diagram.overlaps(where, size) == 1  # a and b: 110 apart, boxes 100 wide, gap 14
    assert diagram.overlaps(where, size, gap=0) == 0


def test_the_layout_is_the_same_every_run_and_leaves_no_name_over_another():
    names = ["a", "b", "c", "d", "e", "f"]
    edges = [("a", "b"), ("b", "c"), ("c", "d"), ("d", "e"), ("e", "f"), ("a", "f"), ("a", "d")]
    size = {n: (150.0, 70.0) for n in names}
    first = diagram.layout(panel(names, edges), size, 900, 700, seeds=20)
    assert first == diagram.layout(panel(names, edges), size, 900, 700, seeds=20)
    assert diagram.overlaps(first, size) == 0
    assert all(0 <= x <= 900 and 0 <= y <= 700 for x, y in first.values())


def test_the_layout_keeps_the_seed_with_the_fewest_crossings_so_a_tree_has_none():
    names = ["a", "b", "c", "d", "e"]
    edges = [("a", "b"), ("a", "c"), ("a", "d"), ("d", "e")]
    size = {n: (120.0, 60.0) for n in names}
    where = diagram.layout(panel(names, edges), size, 800, 600, seeds=40)
    assert diagram.crossings(where, edges) == 0


def test_a_panel_that_cannot_fit_without_overlap_is_refused_instead_of_drawn_over():
    names = [f"n{i}" for i in range(12)]
    size = {n: (400.0, 200.0) for n in names}
    with pytest.raises(diagram.DiagramError, match="no layout of 12 names fits"):
        diagram.layout(panel(names, []), size, 500, 300, seeds=5)


def test_panels_group_the_pairs_by_world_and_name_each_kind(tmp_path):
    cast = cast_document()
    cast["characters"].append(character("sam"))
    pairs = pairs_document()
    pairs["relationships"] = [pair("fern", "rex", relation="coworkers"), pair("fern", "sam", relation="neighbours")]
    got = diagram.panels(bible.load(write(tmp_path, cast, pairs)))
    assert [p.world for p in got] == ["okayville"]
    assert got[0].edges[("fern", "rex")] == ("work", 1)
    assert got[0].edges[("fern", "sam")] == ("friends", 1)
    assert set(got[0].names) == {"fern", "rex", "sam"}


def test_a_pair_across_two_worlds_is_refused_because_the_worlds_share_no_canon(tmp_path):
    cast = cast_document()
    cast["characters"].append(character("gus", world="gloss"))
    pairs = pairs_document()
    pairs["relationships"] = [pair("gus", "rex")]
    with pytest.raises(diagram.DiagramError, match="gloss to okayville|okayville to gloss"):
        diagram.panels(bible.load(write(tmp_path, cast, pairs)))


def test_the_scene_has_a_panel_per_world_every_name_and_a_legend_and_no_crossing_in_a_pair(tmp_path):
    scene, left = diagram.compose(bible.load(write(tmp_path)), FACES)
    xml = scene.to_bytes().decode()
    assert left == {"okayville": 0}
    for text in ("Okayville", "Fern", "Rex", "Lines", "friends"):  # the pair are neighbours
        assert text in xml
    assert 'height="' in xml


def test_a_bible_with_no_relationship_has_no_diagram(tmp_path):
    pairs = pairs_document()
    pairs["relationships"] = []
    with pytest.raises(diagram.DiagramError, match="no relationship"):
        diagram.compose(bible.load(write(tmp_path, pairs=pairs)), FACES)
