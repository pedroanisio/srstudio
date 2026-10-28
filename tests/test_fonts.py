"""Google Fonts: request, typed CSS parse, font-file verification, licence, pinning and offline reuse."""

import json
import struct

import pytest

from srstudio import fonts
from srstudio.fonts import FontError, GoogleFont
from srstudio.sample import SYSTEM_FONTS

BOLD = next(f for f in SYSTEM_FONTS if f.exists())  # DejaVu Sans Bold, the fixture font
TTF_URL = "https://fonts.gstatic.com/s/dejavusans/v1/bold.ttf"


def css(family="DejaVu Sans", weight=700, style="normal", url=TTF_URL, fmt="truetype"):
    return (
        "@font-face {\n"
        f"  font-family: '{family}';\n  font-style: {style};\n  font-weight: {weight};\n"
        f"  src: url({url}) format('{fmt}');\n}}\n"
    )


class Web:
    """A fake fetcher: url → bytes, recording every request; a missing url is a 404."""

    def __init__(self, pages):
        self.pages, self.asked = pages, []

    def __call__(self, url: str) -> bytes:
        self.asked.append(url)
        if url not in self.pages:
            raise FontError(f"HTTP 404 for {url}")
        return self.pages[url]


def web(**over):
    font = GoogleFont("DejaVu Sans", 700)
    pages = {
        font.css_url: css().encode(),
        TTF_URL: BOLD.read_bytes(),
        "https://raw.githubusercontent.com/google/fonts/main/ofl/dejavusans/OFL.txt": b"SIL Open Font License 1.1",
    }
    pages.update(over)
    return Web(pages)


# -- the request ------------------------------------------------------------------------------------
def test_a_request_names_family_weight_and_style():
    f = GoogleFont("Poppins", 700)
    assert f.css_url == "https://fonts.googleapis.com/css2?family=Poppins:wght@700"
    assert GoogleFont("Open Sans", 400, italic=True).css_url == (
        "https://fonts.googleapis.com/css2?family=Open+Sans:ital,wght@1,400"
    )
    assert f.slug == "poppins-700" and GoogleFont("Open Sans", 400, italic=True).slug == "open-sans-400-italic"
    assert f.repo_dir == "poppins" and GoogleFont("Open Sans").repo_dir == "opensans"


@pytest.mark.parametrize(
    "kw, match",
    [
        (dict(family=""), "family"),
        (dict(family="X;rm"), "family"),
        (dict(weight=450), "weight"),
        (dict(weight=1000), "weight"),
    ],
)
def test_a_bad_request_is_refused(kw, match):
    with pytest.raises(FontError, match=match):
        GoogleFont(**{"family": "Poppins", **kw})


# -- the CSS -------------------------------------------------------------------------------------------------
def test_the_css_yields_the_one_truetype_url():
    assert fonts.parse_css(css(), GoogleFont("DejaVu Sans", 700)) == TTF_URL


@pytest.mark.parametrize(
    "text, match",
    [
        ("", "one @font-face"),
        (css() + css(), "one @font-face"),
        (css(family="Comic Sans"), "family"),
        (css(weight=400), "weight"),
        (css(style="italic"), "style"),
        (css(url="https://evil.example/x.ttf"), "fonts.gstatic.com"),
        (css(url="http://fonts.gstatic.com/x.ttf"), "fonts.gstatic.com"),
        (css(fmt="woff2", url="https://fonts.gstatic.com/x.woff2"), "truetype"),
        (css().replace("font-weight: 700;", "font-weight: 700; unicode-range: U+0000-00FF;"), "unknown"),
    ],
)
def test_unexpected_css_is_refused(text, match):
    with pytest.raises(FontError, match=match):
        fonts.parse_css(text, GoogleFont("DejaVu Sans", 700))


# -- the font file -------------------------------------------------------------------------------------------
def test_the_font_file_reports_its_own_family_weight_and_style():
    facts = fonts.inspect_ttf(BOLD.read_bytes())
    assert facts.family == "DejaVu Sans" and facts.weight == 700 and facts.italic is False


@pytest.mark.parametrize(
    "data, match",
    [
        (b"", "too short"),
        (b"wOF2" + b"\0" * 40, "not a TrueType"),
        (struct.pack(">IHHHH", 0x00010000, 40, 0, 0, 0), "table directory"),
    ],
)
def test_a_damaged_font_file_is_refused(data, match):
    with pytest.raises(FontError, match=match):
        fonts.inspect_ttf(data)


def test_a_font_without_its_name_or_os2_table_is_refused():
    data = bytearray(BOLD.read_bytes())
    n = struct.unpack(">H", data[4:6])[0]
    for i in range(n):  # rename the 'name' table tag so it cannot be found
        at = 12 + 16 * i
        if data[at : at + 4] == b"name":
            data[at : at + 4] = b"nam_"
    with pytest.raises(FontError, match="'name' table"):
        fonts.inspect_ttf(bytes(data))


# -- install ----------------------------------------------------------------------------------------------------
def test_install_fetches_verifies_pins_and_then_works_offline(tmp_path):
    w = web()
    got = fonts.install(GoogleFont("DejaVu Sans", 700), tmp_path / "fonts", fetch=w)
    assert got.path == tmp_path / "fonts" / "dejavu-sans-700.ttf" and got.path.read_bytes() == BOLD.read_bytes()
    assert (got.family, got.weight, got.license, got.url) == ("DejaVu Sans", 700, "OFL-1.1", TTF_URL)
    assert (tmp_path / "fonts" / "dejavu-sans.OFL.txt").read_text() == "SIL Open Font License 1.1"
    lock = json.loads((tmp_path / "fonts" / "fonts.lock.json").read_text())
    assert lock["dejavu-sans-700"]["sha256"] == got.sha256 and lock["dejavu-sans-700"]["url"] == TTF_URL
    offline = Web({})
    again = fonts.install(GoogleFont("DejaVu Sans", 700), tmp_path / "fonts", fetch=offline)
    assert again == got and offline.asked == []


def test_a_pinned_font_that_changed_on_disk_is_refused(tmp_path):
    fonts.install(GoogleFont("DejaVu Sans", 700), tmp_path, fetch=web())
    (tmp_path / "dejavu-sans-700.ttf").write_bytes(b"tampered")
    with pytest.raises(FontError, match="SHA-256"):
        fonts.install(GoogleFont("DejaVu Sans", 700), tmp_path, fetch=Web({}))


def test_a_served_file_that_is_not_the_requested_weight_is_refused(tmp_path):
    request = GoogleFont("DejaVu Sans", 400)  # the CSS promises 400, the file is the bold cut
    w = Web({request.css_url: css(weight=400).encode(), TTF_URL: BOLD.read_bytes()})
    with pytest.raises(FontError, match="weight 700, not 400"):
        fonts.install(request, tmp_path, fetch=w)


def test_a_font_with_a_different_family_is_refused_and_nothing_is_written(tmp_path):
    request = GoogleFont("Poppins", 700)
    w = Web({request.css_url: css(family="Poppins").encode(), TTF_URL: BOLD.read_bytes()})
    with pytest.raises(FontError, match="'DejaVu Sans', not 'Poppins'"):
        fonts.install(request, tmp_path, fetch=w)
    assert list(tmp_path.iterdir()) == []


def test_licences_are_looked_up_in_every_google_fonts_folder(tmp_path):
    base = "https://raw.githubusercontent.com/google/fonts/main"
    w = web()
    del w.pages[f"{base}/ofl/dejavusans/OFL.txt"]
    w.pages[f"{base}/apache/dejavusans/LICENSE.txt"] = b"Apache License 2.0"
    assert fonts.install(GoogleFont("DejaVu Sans", 700), tmp_path / "a", fetch=w).license == "Apache-2.0"
    del w.pages[f"{base}/apache/dejavusans/LICENSE.txt"]
    with pytest.raises(FontError, match="no licence"):
        fonts.install(GoogleFont("DejaVu Sans", 700), tmp_path / "b", fetch=w)
    assert not (tmp_path / "b").exists()


def test_an_oversized_download_is_refused(tmp_path):
    with pytest.raises(FontError, match="larger than"):
        fonts.install(GoogleFont("DejaVu Sans", 700), tmp_path, fetch=web(**{TTF_URL: b"\0" * (fonts.MAX_BYTES + 1)}))


def test_the_installed_font_becomes_a_style_font(tmp_path):
    got = fonts.install(GoogleFont("DejaVu Sans", 700), tmp_path / "assets" / "fonts", fetch=web())
    font = fonts.as_font(got, root=tmp_path, id="caption-font")
    assert (font.src, font.id, font.family, font.weight, font.license) == (
        "assets/fonts/dejavu-sans-700.ttf",
        "caption-font",
        "DejaVu Sans",
        "700",
        "OFL-1.1",
    )
    assert font.google == GoogleFont("DejaVu Sans", 700)


def test_the_cli_adds_a_font(tmp_path, monkeypatch, capsys):
    from srstudio.cli import main

    monkeypatch.setattr(fonts, "fetch_url", web())
    assert main(["fonts", "add", "DejaVu Sans", "--weight", "700", "--into", str(tmp_path)]) == 0
    assert "dejavu-sans-700.ttf" in capsys.readouterr().out
    assert main(["fonts", "add", "DejaVu Sans", "--weight", "450", "--into", str(tmp_path)]) == 2
