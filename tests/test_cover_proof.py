"""A cover proof draws anywhere but the publish folder, and lists what the gates find without stopping."""

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from srstudio import caption_gate, cover_proof, releases
from srstudio.social import Drift


@dataclass
class Post:
    """Stands in for the post: drawing a cover needs a real master and the engine, which a unit test has not."""

    calls: list = field(default_factory=list)

    def deliver(self, folder, video, **kw):
        self.calls.append((Path(folder), Path(video), kw))


@dataclass
class Reel:
    slug: str = "reel"
    video_name: str = "reel"
    scene_file: str = "reel.scene.xml"
    post: Post = field(default_factory=Post)


@pytest.fixture
def renders(tmp_path):
    folder = tmp_path / "renders"
    (folder / "ig" / "reel").mkdir(parents=True)
    (folder / "reel.mp4").write_bytes(b"")
    return folder


def kit(tmp_path, renders):
    return dict(renders=renders, episodes=tmp_path / "episodes", font=tmp_path / "f.ttf", engine=tmp_path / "engine")


@pytest.mark.parametrize("inside", ["ig", "ig/reel", "elsewhere/../ig"])
def test_the_publish_folder_is_refused_however_it_is_spelled(tmp_path, renders, inside):
    with pytest.raises(cover_proof.CoverProofError, match="publish folder"):
        cover_proof.refuse_outbox(renders / inside, renders)


def test_a_link_into_the_publish_folder_is_refused(tmp_path, renders):
    link = tmp_path / "proof"
    link.symlink_to(renders / "ig")
    with pytest.raises(cover_proof.CoverProofError, match="publish folder"):
        cover_proof.refuse_outbox(link, renders)


def test_a_refused_proof_draws_nothing(tmp_path, renders):
    reel = Reel()
    with pytest.raises(cover_proof.CoverProofError):
        cover_proof.proof(reel, renders / "ig", **kit(tmp_path, renders))
    assert reel.post.calls == []


def test_a_reel_not_rendered_is_named(tmp_path, renders):
    (renders / "reel.mp4").unlink()
    with pytest.raises(cover_proof.CoverProofError, match="not rendered"):
        cover_proof.proof(Reel(), tmp_path / "proofs", **kit(tmp_path, renders))


def test_findings_are_listed_and_the_cover_is_still_drawn(tmp_path, renders, monkeypatch):
    held = Drift("reel", "stick-poster is held at the pin gate")
    monkeypatch.setattr(releases, "unpinned", lambda *a: [held])
    monkeypatch.setattr(releases, "doubled_captions", lambda *a: [])
    monkeypatch.setattr(caption_gate, "check_releases", lambda *a, **k: [])
    reel = Reel()
    result = cover_proof.proof(reel, tmp_path / "proofs", **kit(tmp_path, renders))
    assert result.drift == (held,)
    assert result.folder == tmp_path / "proofs" / "reel"
    assert reel.post.calls[0][0] == result.folder and reel.post.calls[0][1] == renders / "reel.mp4"
    assert reel.post.calls[0][2]["scene"] is None  # no scene built: the frame comes from the master
