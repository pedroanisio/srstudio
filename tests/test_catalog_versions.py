"""``srstudio.catalog_versions``: a part's history as the catalog holds it, read through the parts module."""

import os
import stat
from pathlib import Path

import pytest

from srstudio import catalog_data as cd
from srstudio import catalog_page as cp
from srstudio import catalog_versions as cv
from srstudio import parts, registry, specimens

DIGEST = "ab" * 32
KNOWN = {"pip", "pip@2", "pip@3", "juno"}


def version(number, **fields) -> parts.Version:
    base = {"date": "2026-10-30", "note": "Traced.", "status": "approved", "proof": "", "drawing": DIGEST}
    return parts.Version(number=number, **(base | fields))


def inked(number=2) -> parts.Version:
    approval = parts.Approval("2026-10-30", "approved, lets add version")
    return version(number, proof="generated/proofs/pip/pip.mp4", approval=approval)


def table(*versions, name="pip") -> dict[str, parts.Part]:
    return {name: parts.Part(name, "character", "toon", versions)}


def history(records, pins=None, proof=lambda path: f"media/{'0' * 32}.mp4", known=KNOWN):
    return cv.history(records, known, pins, proof)


def test_every_field_of_a_version_reaches_the_catalog():
    pip = history(table(version(1), inked()), {"camera-off": {"pip": 2}})["pip"]
    assert [v.number for v in pip] == [1, 2]
    assert pip[0] == cd.PartVersion(1, "2026-10-30", "Traced.", "approved", False, "pip")
    assert pip[1] == cd.PartVersion(
        2, "2026-10-30", "Traced.", "approved", True, "pip@2",
        approval=cd.Approval("2026-10-30", "approved, lets add version"),
        proof=f"media/{'0' * 32}.mp4", proof_path="generated/proofs/pip/pip.mp4", pins=("camera-off",),
    )  # fmt: skip


def test_a_versions_head_rig_reaches_the_catalog_with_its_own_proof():
    approval = parts.Approval("2026-10-31", "approved the rigs")
    rig = parts.Rig("2026-10-31", "Head on its neck.", "approved", "generated/rigs/index.html", DIGEST, approval)
    proposed = parts.Rig("2026-11-01", "A redraw.", "proposed", "", "")
    seen = []
    pip = history(
        table(
            version(1),
            inked(),
            version(3, status="proposed", drawing="", rig=rig),
            version(4, status="proposed", drawing="", rig=proposed),
        ),
        proof=lambda p: seen.append(p) or "proofs/x",
    )["pip"]
    assert pip[0].rig is None and pip[1].rig is None
    assert pip[2].rig == cd.VersionRig(
        "2026-10-31", "Head on its neck.", "approved", cd.Approval("2026-10-31", "approved the rigs"),
        "proofs/x", "generated/rigs/index.html",
    )  # fmt: skip
    assert pip[3].rig == cd.VersionRig("2026-11-01", "A redraw.", "proposed", None, "", "")
    assert "generated/rigs/index.html" in seen


def test_a_proposed_version_shows_as_proposed_and_is_never_the_default():
    pip = history(table(version(1), inked(), version(3, status="proposed", proof="generated/x/index.html")))["pip"]
    assert [(v.status, v.default) for v in pip] == [("approved", False), ("approved", True), ("proposed", False)]


def test_a_part_with_only_proposed_versions_has_no_default():
    assert not history(table(version(1, status="proposed")))["pip"][0].default


def test_a_proposed_version_with_no_drawing_yet_names_no_part():
    pip = history(table(version(1), version(2, status="proposed", drawing="")), known={"pip"})["pip"]
    assert pip[1].part == "" and pip[1].status == "proposed"


def test_a_proof_not_on_this_machine_keeps_its_path_and_no_link():
    pip = history(table(version(1), inked()), proof=lambda path: "")["pip"]
    assert (pip[1].proof, pip[1].proof_path) == ("", "generated/proofs/pip/pip.mp4")


def test_pins_go_to_the_pinned_version_in_slug_order():
    pins = {"zebra": {"pip": 1}, "alpha": {"pip": 1}, "mid": {"pip": 2}, "other": {"juno": 1}}
    records = {**table(version(1), inked()), **table(version(1), name="juno")}
    got = history(records, pins)
    assert (got["pip"][0].pins, got["pip"][1].pins, got["juno"][0].pins) == (("alpha", "zebra"), ("mid",), ("other",))


def test_a_pin_the_table_cannot_place_is_refused_by_name():
    with pytest.raises(cd.CatalogError, match="reel pins pip version 9"):
        history(table(version(1)), {"reel": {"pip": 9}})
    with pytest.raises(cd.CatalogError, match="reel pins ghost version 1"):
        history(table(version(1)), {"reel": {"ghost": 1}})


def test_a_record_for_an_unregistered_part_is_refused_by_name():
    with pytest.raises(cd.CatalogError, match="nobody"):
        history(table(version(1), name="nobody"))


def test_the_part_a_later_version_belongs_to_is_read_from_the_histories():
    assert cv.owners(history(table(version(1), inked()))) == {"pip@2": "pip"}


def test_the_real_table_and_the_real_releases_make_a_history_the_document_accepts():
    specimens.load_parts()
    pins = cv.read_pins(Path(__file__).parents[1] / "episodes" / "posts")
    assert pins and "toon-rabbit" in {name for pinned in pins.values() for name in pinned}
    known = {x.name for x in registry.entries()}
    got = cv.history(parts.load(), known, pins, lambda path: "")
    assert [v.number for v in got["toon-fox"]] == [1, 2] and got["toon-fox"][1].default
    assert got["toon-fox"][1].part == "toon-fox@2" and cv.owners(got)["toon-fox@2"] == "toon-fox"
    assert got["toon-bear"][0].pins  # published reels pin it


def test_a_folder_of_releases_that_cannot_be_read_is_refused(tmp_path):
    (tmp_path / "broken.py").write_text("RELEASE = 3\n")
    with pytest.raises(cd.CatalogError, match="releases in"):
        cv.read_pins(tmp_path)


# -- proofs in the site -----------------------------------------------------------------------------------
@pytest.fixture
def machine(tmp_path) -> Path:
    root = tmp_path / "work"
    page = root / "generated" / "proofs" / "critters"
    page.mkdir(parents=True)
    (page / "index.html").write_text('<video src="./goat.mp4"></video>')
    (page / "goat.mp4").write_bytes(b"goat")
    (page / "manifest.jsonl").write_text("{}")
    (page / ".hidden.mp4").write_bytes(b"no")
    (root / "generated" / "proofs" / "pip.mp4").write_bytes(b"pip")
    return root


def shelf(machine, tmp_path) -> tuple[cp.Proofs, cp.MediaStore]:
    media = cp.MediaStore(tmp_path / "site" / "media")
    return cp.Proofs(machine, tmp_path / "site" / "proofs", media.add), media


def test_a_page_proof_is_placed_with_the_files_beside_it(machine, tmp_path):
    proofs, _ = shelf(machine, tmp_path)
    url = proofs.url("generated/proofs/critters/index.html")
    placed = tmp_path / "site" / url
    assert cd._PROOF.fullmatch(url) and placed.read_text().startswith("<video")
    assert sorted(p.name for p in placed.parent.iterdir()) == ["goat.mp4", "index.html"]  # what the server can type
    assert stat.S_IMODE(placed.stat().st_mode) == 0o600 and stat.S_IMODE(placed.parent.stat().st_mode) == 0o700


def test_a_file_proof_is_a_media_file(machine, tmp_path):
    proofs, _ = shelf(machine, tmp_path)
    url = proofs.url("generated/proofs/pip.mp4")
    assert url.startswith("media/") and (tmp_path / "site" / url).read_bytes() == b"pip"


@pytest.mark.parametrize("pointer", ["generated/proofs/gone.mp4", "generated/proofs/gone/index.html", "../outside.mp4"])
def test_a_proof_that_is_not_on_this_machine_or_not_under_the_root_has_no_link(machine, tmp_path, pointer):
    (machine.parent / "outside.mp4").write_bytes(b"secret")
    proofs, _ = shelf(machine, tmp_path)
    assert proofs.url(pointer) == ""


def test_a_second_build_follows_the_proof_and_drops_what_left(machine, tmp_path):
    page = "generated/proofs/critters/index.html"
    proofs, _ = shelf(machine, tmp_path)
    url = proofs.url(page)
    source = machine / "generated" / "proofs" / "critters"
    (source / "goat.mp4").unlink()
    (source / "index.html").write_text("redrawn")
    os.utime(source / "index.html", (2_000_000_000, 2_000_000_000))
    again, _ = shelf(machine, tmp_path)
    assert again.url(page) == url
    assert (tmp_path / "site" / url).read_text() == "redrawn"
    assert sorted(p.name for p in (tmp_path / "site" / url).parent.iterdir()) == ["index.html"]


def test_prune_removes_a_proof_nothing_links(machine, tmp_path):
    proofs, _ = shelf(machine, tmp_path)
    url = proofs.url("generated/proofs/critters/index.html")
    nothing, _ = shelf(machine, tmp_path)
    nothing.prune()
    assert not (tmp_path / "site" / url).exists()
