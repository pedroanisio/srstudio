"""``srstudio.catalog_data``: the catalog.json schema, its strict reader and its semantic checks."""

import copy
import json

import pytest

from srstudio import catalog_data as cd

HASH = "0123456789abcdef0123456789abcdef"
VIDEO, POSTER, IMAGE = f"media/{HASH}.mp4", f"media/{HASH}.jpg", f"media/{HASH[::-1]}.jpg"
SPECIMEN = f"media/{HASH}.png"


def document() -> dict:
    """The smallest catalog that uses every kind of reference."""
    return {
        "schema_version": cd.SCHEMA_VERSION,
        "measured": True,
        "unmeasured": ["take-home"],
        "engine": ["Simulação física"],
        "styles": [
            {"slug": "soft", "name": "Soft", "title": "Blob", "text_html": "<i>Pose</i>", "summary": "A blob.",
             "videos": ["camera-off"], "parts": ["pip"]},
        ],
        "videos": [
            {"slug": "camera-off", "title": "Camera Off", "number": "08", "lede": "Câmera.",
             "highlights_html": ["<b>x</b>"], "style": "soft", "source": "library", "measured": True, "parts": ["pip"],
             "format": "9:16", "fps": 30, "duration": 12.5, "width": 1080, "height": 1920, "effects": 1,
             "src": VIDEO, "poster": POSTER,
             "lines": [{"t": 0.5, "who": "pip", "voice": "Will", "text": "Hi.", "sfx": False}]},
            {"slug": "take-home", "title": "Take Home", "number": "", "lede": "", "highlights_html": [], "style": "",
             "source": "library", "measured": False, "parts": [], "format": "9:16", "fps": 30.0, "duration": 5.0,
             "width": 1080, "height": 1920, "effects": 0, "src": VIDEO, "poster": POSTER, "lines": []},
            {"slug": "wifi", "title": "Wi-Fi", "number": "05", "lede": "", "highlights_html": [], "style": "",
             "source": "package", "measured": False, "parts": [], "format": "9:16", "fps": 30.0, "duration": 5.0,
             "width": 1080, "height": 1920, "effects": 0, "poster": POSTER, "lines": []},
        ],
        "parts": [
            {"name": "pip", "kind": "character", "title": "Pip", "style": "soft", "summary": "The blob.",
             "videos": ["camera-off"], "specimen": {"src": SPECIMEN, "width": 480, "height": 480},
             "gallery": [{"name": "Pip", "note_html": "O <i>blob</i>.", "voice": "Will",
                          "still": {"src": IMAGE, "width": 300, "height": 400, "label": "", "video": "camera-off"},
                          "poses": [{"src": IMAGE, "width": 200, "height": 200, "label": "dança",
                                     "video": "camera-off"}]}],
             "sheet": [{"src": IMAGE, "width": 300, "height": 320, "label": "stand", "video": ""}]},
            {"name": "juno", "kind": "character", "title": "juno", "style": "", "summary": "Unused.", "videos": [],
             "refused": "Só existe sobre uma cena."},
        ],
    }  # fmt: skip


def test_a_document_parses_into_typed_values():
    catalog = cd.parse(document())
    assert isinstance(catalog, cd.Catalog) and catalog.styles[0].videos == ("camera-off",)
    video = catalog.videos[0]
    assert isinstance(video.fps, float) and video.lines == (cd.Line(0.5, "pip", "Will", "Hi."),)
    pip = catalog.parts[0]
    assert pip.gallery[0].poses[0].label == "dança" and pip.sheet[0].video == ""
    assert catalog.parts[1].gallery == () and catalog.parts[1].sheet == ()  # optional fields take their default
    assert cd.media_of(catalog) == {VIDEO, POSTER, IMAGE, SPECIMEN}
    assert pip.specimen == cd.Still(SPECIMEN, 480, 480) and not pip.refused
    assert catalog.parts[1].specimen is None and catalog.parts[1].refused == "Só existe sobre uma cena."


def test_a_document_survives_the_round_trip_byte_for_byte():
    text = cd.dumps(cd.parse(document()))
    assert cd.dumps(cd.parse(json.loads(text))) == text


def edited(change) -> dict:
    doc = copy.deepcopy(document())
    change(doc)
    return doc


def sets(path, value):
    """A change that sets ``value`` at ``path`` in the document."""

    def change(doc):
        node = doc
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value

    return change


def deletes(path):
    def change(doc):
        node = doc
        for key in path[:-1]:
            node = node[key]
        del node[path[-1]]

    return change


@pytest.mark.parametrize(
    "change, match",
    [
        (sets(["extra"], 1), "unknown"),
        (sets(["videos", 0, "colour"], "red"), "unknown"),
        (sets(["videos", 0, "lines", 0, "mood"], "ok"), "unknown"),
        (sets(["parts", 0, "gallery", 0, "still", "zoom"], 2), "unknown"),
        (deletes(["schema_version"]), "missing"),
        (deletes(["videos", 0, "slug"]), "missing"),
        (deletes(["parts", 0, "gallery", 0, "still"]), "missing"),
        (sets(["videos"], {}), "expected a list"),
        (sets(["videos", 0], []), "expected an object"),
        (sets(["videos", 0, "duration"], "12"), "finite number"),
        (sets(["videos", 0, "duration"], True), "finite number"),
        (sets(["videos", 0, "duration"], float("nan")), "finite number"),
        (sets(["videos", 0, "duration"], float("inf")), "finite number"),
        (sets(["videos", 0, "width"], 10.5), "expected int"),
        (sets(["videos", 0, "width"], True), "expected int"),
        (sets(["videos", 0, "measured"], 1), "expected bool"),
        (sets(["videos", 0, "title"], 8), "expected str"),
        (sets(["videos", 0, "title"], None), "expected str"),
        (sets(["videos", 0, "src"], 3), "expected str"),
    ],
)
def test_a_document_of_the_wrong_shape_is_refused(change, match):
    with pytest.raises(cd.CatalogError, match=match):
        cd.parse(edited(change))


def test_a_document_that_is_not_an_object_is_refused():
    with pytest.raises(cd.CatalogError, match="object"):
        cd.parse([])


@pytest.mark.parametrize(
    "change, match",
    [
        (sets(["schema_version"], "1.0"), "major.minor.patch"),
        (sets(["schema_version"], "2.0.0"), "reader"),
        (sets(["videos", 1, "slug"], "camera-off"), "twice"),
        (sets(["parts", 1, "name"], "pip"), "twice"),
        (sets(["videos", 0, "parts"], ["pip", "pip"]), "twice"),
        (sets(["videos", 0, "source"], "bootleg"), "source"),
        (sets(["videos", 0, "style"], "baroque"), "baroque"),
        (sets(["videos", 0, "parts"], ["ghost"]), "ghost"),
        (sets(["videos", 0, "parts"], ["juno"]), "list it back"),
        (sets(["parts", 0, "videos"], ["take-home"]), "list it back"),
        (sets(["parts", 0, "videos"], ["camera-off", "ghost"]), "ghost"),
        (sets(["parts", 0, "kind"], "crowd"), "kind"),
        (sets(["parts", 0, "style"], "baroque"), "baroque"),
        (sets(["parts", 0, "gallery", 0, "still", "src"], "data:image/png;base64,AAAA"), "media/"),
        (sets(["parts", 0, "gallery", 0, "still", "video"], "ghost"), "ghost"),
        (sets(["parts", 0, "sheet", 0, "width"], 0), "still"),
        (sets(["videos", 0, "src"], None), "src and poster"),
        (sets(["videos", 0, "src"], "../../secret.mp4"), "media/"),
        (sets(["videos", 0, "poster"], "http://example.com/x.jpg"), "media/"),
        (sets(["videos", 0, "source"], "package"), "no file"),
        (sets(["videos", 2, "poster"], None), "package video needs its poster"),
        (sets(["videos", 2, "src"], VIDEO), "no file"),
        (sets(["videos", 2, "poster"], "../poster.jpg"), "media/"),
        (sets(["videos", 2, "source"], "no-render"), "no file"),
        (deletes(["parts", 0, "specimen"]), "neither a specimen nor a reason"),
        (sets(["parts", 1, "refused"], ""), "neither a specimen nor a reason"),
        (sets(["parts", 0, "refused"], "Não."), "both a specimen and a reason"),
        (sets(["parts", 0, "specimen", "src"], "http://example.com/x.png"), "media/"),
        (sets(["videos", 1, "parts"], ["pip"]), "not measured|cannot claim"),
        (sets(["videos", 0, "duration"], -1), "negative"),
        (sets(["videos", 0, "lines", 0, "t"], -0.1), "before the start"),
        (sets(["styles", 0, "videos"], []), "videos"),
        (sets(["styles", 0, "parts"], []), "parts"),
        (sets(["unmeasured"], ["ghost"]), "ghost"),
        (sets(["unmeasured"], ["camera-off"]), "marked measured"),
    ],
)
def test_a_document_that_breaks_a_semantic_rule_is_refused(change, match):
    with pytest.raises(cd.CatalogError, match=match):
        cd.parse(edited(change))


def test_load_checks_that_the_media_sit_beside_the_document(tmp_path):
    (tmp_path / "media").mkdir()
    path = tmp_path / "catalog.json"
    path.write_text(cd.dumps(cd.parse(document())), encoding="utf-8")
    with pytest.raises(cd.CatalogError, match="missing"):
        cd.load(path)
    for url in (VIDEO, POSTER, IMAGE, SPECIMEN):
        (tmp_path / url).write_bytes(b"x")
    assert cd.load(path).schema_version == cd.SCHEMA_VERSION


def test_an_unreadable_document_is_refused(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text("{not json")
    with pytest.raises(cd.CatalogError, match="catalog.json"):
        cd.load(path)
    with pytest.raises(cd.CatalogError, match="missing"):
        cd.load(tmp_path / "missing.json")


# -- versions ---------------------------------------------------------------------------------------------
PROOF = "proofs/0123456789abcdef/index.html"


def version(number, **fields) -> dict:
    return {"number": number, "date": "2026-10-30", "note": "Traced.", "status": "approved", "default": False,
            "part": "pip", **fields}  # fmt: skip


def versioned() -> dict:
    """Pip with an old version, its default, and a proposed one that has no drawing yet."""
    doc = document()
    doc["pinned"] = True
    doc["styles"][0]["parts"] = ["pip", "pip@2"]
    pip = doc["parts"][0]
    pip["versions"] = [
        version(1, pins=["camera-off"]),
        version(2, part="pip@2", default=True, proof=PROOF, proof_path="generated/proofs/pip/index.html",
                approval={"date": "2026-10-30", "words": "approved"}, pins=["not-rendered-yet"]),
        version(3, status="proposed", part="", proof_path="generated/proofs/gone.mp4"),
    ]  # fmt: skip
    doc["parts"].insert(1, {"name": "pip@2", "kind": "character", "title": "Pip 2", "style": "soft",
                            "summary": "The blob, inked.", "videos": [], "version_of": "pip",
                            "specimen": {"src": SPECIMEN, "width": 480, "height": 480}})  # fmt: skip
    return doc


def test_a_part_carries_its_versions_and_each_version_part_names_its_part():
    catalog = cd.parse(versioned())
    pip, inked = catalog.parts[0], catalog.parts[1]
    assert catalog.pinned and [v.number for v in pip.versions] == [1, 2, 3]
    assert inked.version_of == "pip" and inked.versions == ()
    old, current, proposed = pip.versions
    assert (old.default, current.default, proposed.default) == (False, True, False)
    assert current.approval == cd.Approval("2026-10-30", "approved") and proposed.approval is None
    assert old.pins == ("camera-off",) and proposed.proof == "" and proposed.proof_path
    assert PROOF in cd.media_of(catalog)
    assert cd.parse(document()).parts[0].versions == () and not cd.parse(document()).pinned


def test_a_document_with_versions_survives_the_round_trip_byte_for_byte():
    text = cd.dumps(cd.parse(versioned()))
    assert cd.dumps(cd.parse(json.loads(text))) == text


@pytest.mark.parametrize(
    "change, match",
    [
        (sets(["parts", 0, "versions", 0, "colour"], "red"), "unknown"),
        (sets(["parts", 0, "versions", 2, "number"], 4), "1, 2, 3"),
        (sets(["parts", 0, "versions", 0, "status"], "draft"), "status"),
        (sets(["parts", 0, "versions", 0, "default"], True), "one default"),
        (sets(["parts", 0, "versions", 1, "default"], False), "one default"),
        (sets(["parts", 0, "versions", 2, "default"], True), "one default|proposed"),
        (sets(["parts", 0, "versions", 2, "approval"], {"date": "2026-10-30", "words": "yes"}), "proposed"),
        (sets(["parts", 0, "versions", 2, "pins"], ["camera-off"]), "proposed"),
        (sets(["parts", 0, "versions", 1, "part"], ""), "drawing"),
        (sets(["parts", 0, "versions", 1, "part"], "ghost"), "ghost"),
        (sets(["parts", 0, "versions", 1, "part"], "juno"), "juno"),
        (sets(["parts", 0, "versions", 1, "proof"], "../secret.mp4"), "proof"),
        (sets(["parts", 0, "versions", 1, "proof"], "proofs/0123456789abcdef/../../x"), "proof"),
        (sets(["parts", 2, "version_of"], "ghost"), "ghost"),
        (sets(["parts", 2, "version_of"], "pip"), "list it"),
        (sets(["parts", 1, "versions"], [version(1, part="pip@2", default=True)]), "version_of|own versions"),
        (sets(["parts", 0, "versions", 0, "pins"], ["camera-off", "camera-off"]), "twice"),
    ],
)
def test_versions_that_break_a_rule_are_refused(change, match):
    doc = versioned()
    change(doc)
    with pytest.raises(cd.CatalogError, match=match):
        cd.parse(doc)


def test_the_default_is_the_highest_approved_version():
    doc = versioned()
    doc["parts"][0]["versions"][0]["default"] = True
    doc["parts"][0]["versions"][1]["default"] = False
    with pytest.raises(cd.CatalogError, match="highest approved"):
        cd.parse(doc)


def test_a_part_with_only_a_proposed_version_has_no_default():
    doc = document()
    doc["parts"][0]["versions"] = [version(1, status="proposed")]
    assert not cd.parse(doc).parts[0].versions[0].default


def test_load_checks_that_a_proof_sits_beside_the_document(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text(cd.dumps(cd.parse(versioned())), encoding="utf-8")
    for url in (VIDEO, POSTER, IMAGE, SPECIMEN):
        (tmp_path / url).parent.mkdir(exist_ok=True)
        (tmp_path / url).write_bytes(b"x")
    with pytest.raises(cd.CatalogError, match="missing"):
        cd.load(path)
    (tmp_path / PROOF).parent.mkdir(parents=True)
    (tmp_path / PROOF).write_bytes(b"x")
    assert cd.load(path).pinned
