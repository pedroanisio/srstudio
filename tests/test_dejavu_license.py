"""Every copy of DejaVu Sans Bold srstudio writes carries the font's full copyright and permission notice.

The DejaVu fonts are Bitstream Vera with public-domain changes; the Vera licence requires its copyright, trademark
and permission notices "in all copies of one or more of the Font Software typefaces"."""

import ast
from pathlib import Path

import pytest

from srstudio import sample

ROOT = Path(__file__).resolve().parents[1]
DEBIAN = Path("/usr/share/doc/fonts-dejavu-core/copyright")
SOURCES = [p for folder in ("src", "examples", "episodes") for p in sorted((ROOT / folder).rglob("*.py"))]
# The notices the licence makes a condition of every copy, and the conditions themselves.
REQUIRED = (
    "Copyright (c) 2003 by Bitstream, Inc. All Rights Reserved.",
    "Bitstream Vera is a trademark of Bitstream, Inc.",
    "DejaVu changes are in public domain.",
    "The above copyright and trademark notices and this permission notice shall\n"
    "be included in all copies of one or more of the Font Software typefaces.",
    'are renamed to names not containing either the words "Bitstream" or the word\n"Vera".',
    "no\ncopy of one or more of the Font Software typefaces may be sold by itself.",
    'THE FONT SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND',
    "without prior written authorization from the Gnome Foundation or Bitstream\nInc., respectively.",
)


def test_the_notice_and_every_other_package_file_ship_in_the_wheel():
    tomllib = pytest.importorskip("tomllib")  # Python 3.11+; the project still supports 3.10
    patterns = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["setuptools"]["package-data"]["srstudio"]
    package = ROOT / "src" / "srstudio"
    declared = {path for pattern in patterns for path in package.glob(pattern) if path.is_file()}
    data = {p for p in package.rglob("*") if p.is_file() and p.suffix not in (".py", ".pyc")}
    assert package / sample.DEJAVU_LICENSE_FILE in data and data <= declared


def debian_notice(copyright_file: str) -> str:
    """The ``Files: *`` stanza of a Debian machine-readable copyright file, as the plain text it encodes."""
    stanza = copyright_file.split("\nFiles: *\n", 1)[1].split("\n\n", 1)[0]
    copyright_lines, license_lines = stanza.split("\nLicense: bitstream-vera\n")
    holders = [line.strip() for line in copyright_lines.removeprefix("Copyright: ").splitlines()]
    body = ["" if line == " ." else line[1:].rstrip() for line in license_lines.splitlines()]
    return "\n".join(holders) + "\n\n" + "\n".join(body) + "\n"


def test_the_library_ships_the_full_bitstream_vera_notice():
    text = sample.dejavu_license()
    for part in REQUIRED:
        assert part in text


def test_the_shipped_notice_is_debians_dejavu_stanza_word_for_word():
    if not DEBIAN.is_file():
        pytest.skip("no fonts-dejavu-core copyright file on this host to compare the shipped notice with")
    assert sample.dejavu_license().endswith(debian_notice(DEBIAN.read_text()))


def test_copy_dejavu_writes_the_font_and_the_full_notice_beside_it(tmp_path):
    font = tmp_path / "DejaVuSans-Bold.ttf"
    font.write_bytes(b"glyphs")
    assets = tmp_path / "assets"
    assets.mkdir()
    target = sample.copy_dejavu(font, assets, "font.ttf")
    assert target == assets / "font.ttf" and target.read_bytes() == b"glyphs"
    assert (assets / "FONT-LICENSE.txt").read_text() == sample.dejavu_license()


def test_the_sample_project_ships_the_full_notice_with_its_font(tmp_path, monkeypatch):
    font = tmp_path / "system" / "DejaVuSans-Bold.ttf"
    font.parent.mkdir()
    font.write_bytes(b"glyphs")
    monkeypatch.setattr(sample, "SYSTEM_FONTS", (font,))
    data = sample.write_sample_project(tmp_path / "project", [sample.Line("A", "Hello there.")])
    assert data["font_real"]
    assert (tmp_path / "project" / "assets" / "FONT-LICENSE.txt").read_text() == sample.dejavu_license()


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_source_writes_a_url_only_dejavu_note(path):
    assert "dejavu-fonts.github.io/License.html" not in path.read_text()


def _copies_a_system_font(node: ast.AST) -> bool:
    names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
    attrs = {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)}
    return "SYSTEM_FONTS" in names | attrs and bool({"copyfile", "copy", "copy2"} & attrs)


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: str(p.relative_to(ROOT)))
def test_every_function_that_copies_a_system_font_writes_it_with_the_notice(path):
    tree = ast.parse(path.read_text())
    for fn in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
        if fn.name != "copy_dejavu" and _copies_a_system_font(fn):
            called = {n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", None)
                      for n in ast.walk(fn) if isinstance(n, ast.Call)}  # fmt: skip
            assert "copy_dejavu" in called, f"{path.name}:{fn.lineno} {fn.name} copies DejaVu without its notice"
