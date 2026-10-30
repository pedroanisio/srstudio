"""An interview episode's caption face: DejaVu Sans Bold by default, or an opt-in Google Font installed and pinned
into the project, never a silent fall back to DejaVu when the Google Font cannot be installed."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from srstudio import EpisodeSpec, fonts
from srstudio import interview as I
from srstudio.fonts import GoogleFont
from srstudio.sample import SYSTEM_FONTS
from support.interview import make

BOLD = next(f for f in SYSTEM_FONTS if f.exists())  # DejaVu Sans Bold stands in for any served face
FACE = GoogleFont("DejaVu Sans", 700)
TTF_URL = "https://fonts.gstatic.com/s/dejavusans/v1/bold.ttf"


class Web:
    """A fake fetcher: url → bytes, recording every request; a missing url is a 404."""

    def __init__(self, pages: dict[str, bytes]):
        self.pages, self.asked = pages, []

    def __call__(self, url: str) -> bytes:
        self.asked.append(url)
        if url not in self.pages:
            raise fonts.FontError(f"{url}: HTTP 404")
        return self.pages[url]


def google() -> Web:
    css = (
        "@font-face {\n  font-family: 'DejaVu Sans';\n  font-style: normal;\n  font-weight: 700;\n"
        f"  src: url({TTF_URL}) format('truetype');\n}}\n"
    )
    return Web(
        {
            FACE.css_url: css.encode(),
            TTF_URL: BOLD.read_bytes(),
            f"{fonts.REPO}/ofl/{FACE.repo_dir}/OFL.txt": b"SIL Open Font License 1.1",
        }
    )


def test_the_default_face_is_dejavu_copied_with_its_notice(tmp_path):
    path = I.caption_face(make(), tmp_path)
    assert path == tmp_path / "DejaVuSans-Bold.ttf" and path.read_bytes() == BOLD.read_bytes()
    assert (tmp_path / "FONT-LICENSE.txt").exists() and not (tmp_path / I.FONT_DIR).exists()


def test_a_google_face_is_installed_pinned_and_licensed_and_dejavu_is_not_copied(tmp_path):
    path = I.caption_face(make(font=FACE), tmp_path, fetch=google())
    folder = tmp_path / I.FONT_DIR
    assert path == folder / "dejavu-sans-700.ttf"
    lock = json.loads((folder / fonts.LOCK).read_text())
    assert lock["dejavu-sans-700"]["url"] == TTF_URL and (folder / "dejavu-sans.OFL.txt").exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == [I.FONT_DIR]  # no DejaVu copy, no DejaVu notice


@pytest.mark.parametrize(
    "web, match",
    [
        (Web({}), "HTTP 404"),  # the face cannot be fetched at all
        (Web({FACE.css_url: b"<html>quota exceeded</html>"}), "caption font"),  # the CSS is not a face
    ],
)
def test_a_google_face_that_will_not_install_stops_with_a_typed_error_and_no_dejavu(tmp_path, web, match):
    with pytest.raises(I.InterviewError, match=match):
        I.caption_face(make(font=FACE), tmp_path, fetch=web)
    assert not (tmp_path / "DejaVuSans-Bold.ttf").exists() and not (tmp_path / "FONT-LICENSE.txt").exists()


def test_a_font_that_is_not_a_google_font_request_is_refused_when_made():
    with pytest.raises(I.InterviewError, match="GoogleFont"):
        make(font="Noto Sans")


def test_the_build_installs_the_face_before_any_request_is_made(tmp_path, monkeypatch):
    """A face that will not install stops the build before the engine resolves (and pays for) a single clip."""
    monkeypatch.setattr(fonts, "fetch_url", Web({}))
    root = tmp_path / "project"
    with pytest.raises(I.InterviewError, match="caption font"):
        I.build(make(font=FACE), root, engine=tmp_path / "no-engine", schedule=lambda s, e: I.Schedule([], {}))
    assert not (root / "test-interview.audio.scene.xml").exists() and not (root / "dialogue.json").exists()


def test_the_episode_spec_takes_the_pinned_face_offline(tmp_path):
    I.caption_face(make(font=FACE), tmp_path / "assets", fetch=google())
    fields = I.spec_font(FACE, tmp_path)
    assert fields == dict(
        font=f"assets/{I.FONT_DIR}/dejavu-sans-700.ttf",
        font_id="caption-font",
        font_family="DejaVu Sans",
        font_weight="700",
        font_style=None,
        font_credit="DejaVu Sans (Google Fonts)",
        font_license="OFL-1.1",
    )
    spec = EpisodeSpec(slug="face", number="00", title="Face", description="", root=tmp_path, seed=1, **fields)
    assert (spec.font_family, spec.font_weight, spec.font_license) == ("DejaVu Sans", "700", "OFL-1.1")
    assert (tmp_path / spec.font).read_bytes() == BOLD.read_bytes()


def test_the_episode_spec_refuses_a_face_the_record_step_has_not_pinned(tmp_path):
    with pytest.raises(I.InterviewError, match="not pinned"):
        I.spec_font(FACE, tmp_path)
    assert not (tmp_path / "assets").exists() or not any(Path(tmp_path / "assets").rglob("*.ttf"))
