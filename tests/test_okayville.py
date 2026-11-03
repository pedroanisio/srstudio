"""The account is Okayville, @okayville.tv, and nothing a new reel renders or captions carries the old handle.

Every word a reel can draw or post comes from the release data or from a source file in this repository: a script, a
data file, a part of the library, or the skill and references an author copies from. So the old name is searched in
both, whichever video it would end up in. Pixels and text put together at run time are not read here.
"""

import re
from dataclasses import asdict
from pathlib import Path

import pytest

from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

ROOT = Path(__file__).resolve().parent.parent
RETIRED = re.compile(rb"tuxmeme", re.IGNORECASE)
TREES = ("src", "examples")  # what the library draws and captions with; srstudio-episodes checks the reels
GUIDES = tuple(str(p.relative_to(ROOT)) for p in sorted((ROOT / "docs").glob("authoring-*.md"))) + (
    "docs/slack-channel.md",
)  # Every guide an author copies from; srstudio-episodes checks its own docs/, the episode history among them.
RECORDS = ("notes.md", "sources.md")  # what a pilot's author wrote down about its build: never drawn or captioned
GUARDS = ["src/srstudio/cast_card.py"]  # holds the name to refuse it on a card: test_cast_card proves that refusal


def carrying(root: Path, trees: tuple[str, ...]) -> list[str]:
    """Every file under ``trees`` of ``root`` that holds the old name, in any case."""
    files = (p for tree in trees for p in (root / tree).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    drawn = (p for p in files if p.name not in RECORDS)
    return sorted(str(p.relative_to(root)) for p in drawn if RETIRED.search(p.read_bytes()))


def said(post: InstagramPost) -> str:
    """Everything of ``post`` that reaches a viewer or the posting job: the caption, the cover spec and the extras."""
    return "\n".join((post.text(), str(asdict(post.thumbnail) if post.thumbnail else ""), str(post.extra)))


def test_no_source_a_reel_is_built_from_carries_the_old_name():
    assert carrying(ROOT, TREES) == GUARDS


def test_the_search_reads_the_trees_it_claims():
    assert (ROOT / "src/srstudio/social.py").is_file() and (ROOT / "examples").is_dir()


@pytest.mark.parametrize("line", ["@tuxmeme", "follow @TuxMeme on Instagram", 'CREDIT = "tuxmeme"'])
def test_the_search_finds_the_old_name_in_any_file_and_any_case(tmp_path, line):
    (tmp_path / "episodes/posts").mkdir(parents=True)
    (tmp_path / "episodes/posts/new_reel.py").write_text(line)
    (tmp_path / "episodes/clean.py").write_text("@okayville.tv")
    assert carrying(tmp_path, ("episodes",)) == ["episodes/posts/new_reel.py"]


def test_the_search_skips_nothing_but_bytecode_and_build_records(tmp_path):
    (tmp_path / "src/__pycache__").mkdir(parents=True)
    (tmp_path / "src/__pycache__/old.pyc").write_bytes(b"tuxmeme")
    (tmp_path / "src/notes.md").write_bytes(b"No character of @tuxmeme.")
    (tmp_path / "src/card.svg").write_bytes(b"\xff<text>@tuxmeme</text>")
    assert carrying(tmp_path, ("src",)) == ["src/card.svg"]


def test_the_guides_an_author_copies_from_do_not_carry_the_old_name():
    for guide in GUIDES:
        assert not RETIRED.search((ROOT / guide).read_bytes()), guide


@pytest.mark.parametrize(
    "post",
    [
        InstagramPost(title="Follow @tuxmeme", description="d"),
        InstagramPost(title="t", description="More at @TuxMeme"),
        InstagramPost(title="t", description="d", credit="@tuxmeme"),
        InstagramPost(title="t", description="d", hashtags=("#tuxmeme",)),
        InstagramPost(title="t", description="d", extra={"alt": "a @tuxmeme end card"}),
        InstagramPost(title="t", description="d", thumbnail=Thumbnail("@tuxmeme", at=1.0)),
    ],
)
def test_the_check_on_a_release_reads_every_place_a_post_can_carry_it(post):
    assert RETIRED.search(said(post).encode())
