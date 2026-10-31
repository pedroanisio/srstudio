"""The folder builder writes the exact file set at modes 700 and 600, and refuses a drawing the catalog lacks."""

import stat

import pytest

from srstudio import bible, bible_build, bible_diagram
from srstudio.cast_card import Lettering
from support.bible_docs import cast_document, placeholder, write

MODEL = "Claude Sonnet 5.5 (claude-sonnet-5-5)"
FACES = Lettering(b"", b"")


@pytest.fixture
def library(tmp_path):
    cast = cast_document()
    cast["characters"].append(placeholder("rafa"))
    folder = write(tmp_path / "library", cast)
    (folder / "CHANGELOG.md").write_text("# Changelog\n")
    return folder


def picture(tmp_path):
    path = tmp_path / "dog.png"
    path.write_bytes(b"png")
    return path


def draw(monkeypatch):
    def fake(b, out, faces, engine, work):
        out.write_bytes(b"png")
        out.chmod(0o600)
        return {"okayville": 0}

    monkeypatch.setattr(bible_diagram, "render", fake)


def build(library, tmp_path, specimens):
    return bible_build.build(
        library,
        tmp_path / "out",
        bible.load(library),
        model=MODEL,
        order=["cleaning-fee"],
        specimens=specimens,
        faces=FACES,
        engine=tmp_path / "engine",
        work=tmp_path / "work",
    )


def test_the_folder_has_exactly_the_files_of_the_spec_at_the_modes_files_a_tool_writes_have(
    tmp_path, library, monkeypatch
):
    draw(monkeypatch)
    assert build(library, tmp_path, {"toon-dog@1": picture(tmp_path)}) == {"okayville": 0}
    out = tmp_path / "out"
    names = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    assert names == [
        "CHANGELOG.md",
        "README.md",
        "canon.md",
        "cast.json",
        "characters/fern.md",
        "characters/fern.png",
        "characters/rafa.md",
        "characters/rex.md",
        "characters/rex.png",
        "open-decisions.md",
        "relationships.json",
        "relationships.png",
        "world.md",
    ]
    for path in out.rglob("*"):
        assert stat.S_IMODE(path.stat().st_mode) == (0o700 if path.is_dir() else 0o600), path
    assert "![Rex](rex.png)" in (out / "characters/rex.md").read_text()
    assert "![" not in (out / "characters/rafa.md").read_text()  # a placeholder has no drawing


def test_a_part_that_has_no_version_suffix_in_the_catalog_is_still_found(tmp_path, library, monkeypatch):
    draw(monkeypatch)
    build(library, tmp_path, {"toon-dog": picture(tmp_path)})
    assert (tmp_path / "out/characters/rex.png").is_file()


def test_an_approved_drawing_the_catalog_cannot_show_is_refused_instead_of_a_sheet_without_its_picture(
    tmp_path, library, monkeypatch
):
    draw(monkeypatch)
    with pytest.raises(bible_build.BibleBuildError, match="rex: the catalog has no picture of toon-dog@1"):
        build(library, tmp_path, {})
    assert not (tmp_path / "out/characters/rex.md").exists()


def test_a_library_missing_its_changelog_is_refused_before_anything_is_written(tmp_path, library, monkeypatch):
    draw(monkeypatch)
    (library / "CHANGELOG.md").unlink()
    with pytest.raises(bible_build.BibleBuildError, match="CHANGELOG.md is missing"):
        build(library, tmp_path, {"toon-dog@1": picture(tmp_path)})
    assert not (tmp_path / "out").exists()
