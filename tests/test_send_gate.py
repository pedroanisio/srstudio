"""The send test's no-bait rule (ADR 0080): a reel on it never asks to be sent, in the caption or on screen."""

import pytest

from srstudio import releases, send_gate
from srstudio.releases import Release, ReleaseError, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

POST = InstagramPost(title="A title", description="A description.")
TAGS = Tags("family", "other-person", "recognition")
SENT = Tags("family", "other-person", "recognition", send_to="mum", send_line="You did this to me.")


def project(tmp_path, slug="a-b", on_screen="Fine", cues=()):
    folder = tmp_path / slug
    folder.mkdir()
    (folder / f"{slug}.scene.xml").write_text(f'<scene><assets><text id="t" text="{on_screen}"/></assets></scene>')
    if cues:
        rows = [f"{i}\n00:00:0{i},000 --> 00:00:0{i},900\n{cue}\n" for i, cue in enumerate(cues, 1)]
        (folder / f"{slug}.srt").write_text("\n".join(rows))


def reasons(release, tmp_path, briefs=None):
    drift = send_gate.bait_drift({release.slug: release}, tmp_path, briefs or {})
    return [(d.name, d.reason) for d in drift]


@pytest.mark.parametrize(
    "phrase", ["tag a friend", "Tag Someone", "SEND THIS TO", "share this with", "Send it to", "send  this\nto"]
)
def test_each_phrase_in_any_case_is_bait(phrase):
    assert len(send_gate.bait(f"Honestly, {phrase} your mum.")) == 1


@pytest.mark.parametrize("line", ["Resend it tomorrow.", "We tag friends here.", "Send this now.", "Send it."])
def test_a_line_that_only_looks_like_bait_passes(line):
    assert send_gate.bait(line) == []


def test_a_reel_with_a_recipient_may_not_ask_in_its_caption(tmp_path):
    project(tmp_path)
    post = InstagramPost(title="A title", description="Send this to your mum.")
    assert reasons(Release("a-b", post, tags=SENT), tmp_path) == [("a-b", 'its caption says "send this to"')]


def test_a_holdout_is_held_to_it_by_its_brief_alone(tmp_path):
    project(tmp_path)
    post = InstagramPost(title="Tag a friend", description="A description.")
    release = Release("a-b", post, tags=TAGS)
    assert reasons(release, tmp_path, {"a-b": "send-v1"}) == [("a-b", 'its caption says "tag a friend"')]


def test_text_in_the_scene_is_read(tmp_path):
    project(tmp_path, on_screen="SHARE THIS WITH HIM")
    assert reasons(Release("a-b", POST, tags=SENT), tmp_path) == [("a-b", 'its screen says "share this with"')]


def test_a_spoken_caption_is_read_across_two_cues(tmp_path):
    project(tmp_path, cues=("Go on, send it", "to your mum."))
    assert reasons(Release("a-b", POST, tags=SENT), tmp_path) == [("a-b", 'its screen says "send it to"')]


def test_the_cover_is_read(tmp_path):
    project(tmp_path)
    post = InstagramPost(title="A title", description="A description.", thumbnail=Thumbnail("TAG SOMEONE\nNOW", 1.0))
    assert reasons(Release("a-b", post, tags=SENT), tmp_path) == [("a-b", 'its cover says "tag someone"')]


def test_a_reel_off_the_send_test_is_not_read_at_all(tmp_path):
    post = InstagramPost(title="Tag a friend", description="Send this to your mum.")
    assert reasons(Release("a-b", post, tags=TAGS), tmp_path) == []
    assert reasons(Release("a-b", post), tmp_path, {"a-b": "other-brief"}) == []


def test_the_recipient_test_s_arm_alone_does_not_put_a_reel_on_the_send_test(tmp_path):
    """Forty-eight delivered releases carry ``recipient`` as an A/B arm; it is not who the reel is sent to."""
    post = InstagramPost(title="Tag a friend", description="A description.")
    arm = Tags("family", "other-person", "recognition", test="sp-hook_motion", arm="a", recipient="a")
    assert reasons(Release("a-b", post, tags=arm), tmp_path) == []


def test_a_clean_reel_passes(tmp_path):
    project(tmp_path, cues=("You did this to me.",))
    assert reasons(Release("a-b", POST, tags=SENT), tmp_path) == []


def test_a_reel_on_the_test_with_no_scene_is_refused_not_skipped(tmp_path):
    assert reasons(Release("a-b", POST, tags=SENT), tmp_path) == [
        ("a-b", "a-b.scene.xml is missing: its on-screen text cannot be read")
    ]


def test_a_scene_that_does_not_parse_is_refused_by_name(tmp_path):
    project(tmp_path)
    (tmp_path / "a-b" / "a-b.scene.xml").write_text("<scene")
    [(name, reason)] = reasons(Release("a-b", POST, tags=SENT), tmp_path)
    assert name == "a-b" and "not a scene document" in reason


def test_tags_carry_who_it_is_sent_to_and_the_line():
    assert (SENT.send_to, SENT.send_line) == ("mum", "You did this to me.")
    assert (TAGS.send_to, TAGS.send_line) == ("", "")


@pytest.mark.parametrize(
    "kw",
    [
        {"send_to": "mum"},
        {"send_line": "You did this."},
        {"send_to": " ", "send_line": "x"},
        {"send_to": "mum", "send_line": " "},
    ],
)
def test_who_and_the_line_go_together(kw):
    with pytest.raises(ReleaseError, match="send_to"):
        Tags("family", "other-person", "recognition", **kw)


def test_a_person_in_the_ab_arm_is_pointed_at_send_to():
    with pytest.raises(ReleaseError, match="send_to"):
        releases.Tags("family", "other-person", "recognition", test="opening", arm="a", recipient="mum")
