"""Instagram captions: typed limits, the ig.txt layout, the episode hook, and every shipped post is valid."""

import sys
from pathlib import Path

import pytest

from srstudio import Episode, EpisodeSpec
from srstudio.social import CAPTION_LIMIT, HASHTAG_LIMIT, InstagramPost, InstagramPostError

EPISODES = Path(__file__).resolve().parent.parent / "episodes"

GOOD = InstagramPost(
    title="Greatest weakness? Honesty.",
    description="Episode 01.\nContains one strong word.",
    credit="Voices: ElevenLabs.",
    hashtags=("#TheInterview", "#officehumor"),
)


def test_text_layout_is_title_description_credit_hashtags():
    assert GOOD.text() == (
        "Greatest weakness? Honesty.\n\nEpisode 01.\nContains one strong word.\n\n"
        "Voices: ElevenLabs.\n\n#TheInterview #officehumor\n"
    )
    assert InstagramPost(title="t", description="d").text() == "t\n\nd\n"
    assert GOOD.validate() is GOOD


@pytest.mark.parametrize(
    "post,needle",
    [
        (InstagramPost(title="", description="d"), "title is empty"),
        (InstagramPost(title="a\nb", description="d"), "more than one line"),
        (InstagramPost(title="x" * 126, description="d"), "126 characters"),
        (InstagramPost(title="t", description="  "), "description is empty"),
        (
            InstagramPost(title="t", description="d", hashtags=tuple(f"#t{i}" for i in range(HASHTAG_LIMIT + 1))),
            "31 hashtags",
        ),
        (
            InstagramPost(title="t", description="d", hashtags=("#ok", "no-hash", "#1starts", "#with space")),
            "must be '#'",
        ),
        (InstagramPost(title="t", description="d", hashtags=("#Same", "#same")), "duplicate"),
        (InstagramPost(title="t", description="d" * CAPTION_LIMIT), f"Instagram accepts {CAPTION_LIMIT}"),
    ],
)
def test_limits_raise_a_typed_error_listing_the_problem(post, needle):
    with pytest.raises(InstagramPostError) as info:
        post.validate()
    assert any(needle in p for p in info.value.problems)


def test_write_refuses_an_invalid_post_and_leaves_no_file(tmp_path):
    with pytest.raises(InstagramPostError):
        InstagramPost(title="", description="d").write(tmp_path / "x")
    assert not (tmp_path / "x" / "ig.txt").exists()


def test_episode_writes_ig_txt_in_its_root(project):
    ep = Episode(EpisodeSpec(slug="t", title="t", description="t", root=project, seed=1, background="#D5DFDF"))
    path = ep.instagram(GOOD)
    assert path == project / "ig.txt" and path.read_text(encoding="utf-8") == GOOD.text()
    assert path.stat().st_mode & 0o777 == 0o600


def test_every_shipped_post_is_valid_and_maps_to_a_video(tmp_path):
    sys.path.insert(0, str(EPISODES))
    try:
        import instagram_posts as posts
    finally:
        sys.path.pop(0)
    assert set(posts.POSTS) == set(posts.VIDEOS)
    for slug, post in posts.POSTS.items():
        assert post.problems() == [], slug
    written = posts.write_all(tmp_path / "ig")
    assert sorted(p.parent.name for p in written) == sorted(posts.VIDEOS.values())
    assert all(p.name == "ig.txt" and p.read_text(encoding="utf-8").endswith("\n") for p in written)


def test_every_episode_script_ships_its_post():
    scripts = [p for p in sorted(EPISODES.glob("*.py")) if "ep.finish()" in p.read_text(encoding="utf-8")]
    assert scripts
    missing = [p.name for p in scripts if "ep.instagram(POSTS[" not in p.read_text(encoding="utf-8")]
    assert missing == []
