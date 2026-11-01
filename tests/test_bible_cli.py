"""``srstudio bible`` reports faults by exit status and never checks a reel that is already published (ADR 0069)."""

import argparse
import json

import pytest

from srstudio import bible_cli
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from support.bible_docs import locked


def release(slug: str, *recurring: str) -> Release:
    post = InstagramPost(title="t", description="Rex and Fern spoke.", hashtags=("#a",))
    return Release(slug, post, tags=Tags("money-services", "other-person", "recognition", recurring=recurring))


def parse(*argv: str) -> argparse.Namespace:
    root = argparse.ArgumentParser()
    bible_cli.add_parser(root.add_subparsers(dest="cmd", required=True))
    return root.parse_args(["bible", *argv])


@pytest.fixture
def world(tmp_path, monkeypatch):
    episodes = tmp_path / "episodes"
    (episodes / "cleaning-fee").mkdir(parents=True)
    (episodes / "cleaning-fee" / "script.json").write_text(json.dumps([{"speaker": "rex", "text": "Teamwork!"}]))
    outbox = tmp_path / "outbox.json"
    outbox.write_text(json.dumps({"version": 1, "videos": {"cleaning-fee": {}}}))
    found = {"cleaning-fee": release("cleaning-fee", "rex"), "new-reel": release("new-reel", "bruno")}
    monkeypatch.setattr(bible_cli.releases, "load", lambda folder: found)
    library = locked(tmp_path / "bible")
    base = [
        "--library",
        str(library),
        "--episodes",
        str(episodes),
        "--outbox",
        str(outbox),
        "--releases",
        str(tmp_path),
    ]
    return base, found, tmp_path


def test_inventory_counts_the_published_reels_and_lists_who_recurs(world, capsys):
    base, _, _ = world
    assert bible_cli.run(parse(*base, "inventory", "--threshold", "1")) == 0
    out = capsys.readouterr().out
    assert out.startswith("1 published reels") and "rex\tokayville\t1" in out


def test_verify_passes_a_bible_whose_facts_hold_and_fails_one_whose_quote_is_not_in_the_reel(world, capsys):
    base, _, tmp = world
    assert bible_cli.run(parse(*base, "verify")) == 0
    document = json.loads((tmp / "bible" / "cast.json").read_text())
    document["characters"][0]["canon"][0]["quote"] = "Not a line anywhere"
    (tmp / "bible" / "cast.json").write_text(json.dumps(document))
    assert bible_cli.run(parse(*base, "verify")) == 1
    assert "no line says 'Not a line anywhere'" in capsys.readouterr().out


def test_check_flags_a_name_the_bible_lacks_in_an_unpublished_release(world, capsys):
    base, _, _ = world
    assert bible_cli.run(parse(*base, "check")) == 1
    out = capsys.readouterr().out
    assert "new-reel: unknown-name: 'bruno'" in out and "1 unpublished releases" in out


def test_check_never_looks_at_a_published_reel_even_when_it_disagrees(world, capsys):
    base, found, _ = world
    found["cleaning-fee"] = release("cleaning-fee", "bruno")  # published, so frozen
    assert bible_cli.run(parse(*base, "check", "--only", "cleaning-fee")) == 0
    assert "0 unpublished releases" in capsys.readouterr().out


def test_check_reads_a_brief_and_wants_its_cast_line(world, capsys):
    base, _, tmp = world
    good, bad = tmp / "good.md", tmp / "bad.md"
    good.write_text("Cast: rex, fern\n")
    bad.write_text("A story about a dog.\n")
    only = ["--only", "none"]
    assert bible_cli.run(parse(*base, "check", *only, "--brief", str(good))) == 0
    assert bible_cli.run(parse(*base, "check", *only, "--brief", str(bad))) == 1
    assert "cites no cast" in capsys.readouterr().out


def test_a_brief_that_cannot_be_read_is_an_input_error_not_a_pass(world, capsys):
    base, _, tmp = world
    assert bible_cli.run(parse(*base, "check", "--only", "none", "--brief", str(tmp / "missing.md"))) == 2


def test_a_missing_manifest_is_an_input_error(world, capsys):
    base, _, tmp = world
    base[base.index("--outbox") + 1] = str(tmp / "nope.json")
    assert bible_cli.run(parse(*base, "verify")) == 2
    assert "cannot read the delivery manifest" in capsys.readouterr().err


def test_render_without_fonts_or_engine_is_an_input_error(world, monkeypatch, capsys):
    base, _, tmp = world
    monkeypatch.delenv("SRSTUDIO_FONTS", raising=False)
    monkeypatch.delenv("SRSTUDIO_ENGINE", raising=False)
    monkeypatch.setattr(bible_cli.shutil, "which", lambda _: None)
    args = parse(*base, "render", str(tmp / "out"), "--model", "m", "--cache", str(tmp), "--work", str(tmp))
    assert bible_cli.run(args) == 2
    assert "set --fonts and --engine" in capsys.readouterr().err


def test_lock_writes_the_lock_and_verify_names_a_bible_that_drifted_from_it(world, capsys):
    base, _, tmp = world
    (tmp / "bible" / "lock.json").unlink()
    assert bible_cli.run(parse(*base, "lock")) == 0
    assert "locked" in capsys.readouterr().out and (tmp / "bible" / "lock.json").exists()
    assert bible_cli.run(parse(*base, "verify")) == 0
    document = json.loads((tmp / "bible" / "cast.json").read_text())
    document["characters"][0]["look"]["palette"] = "purple"
    (tmp / "bible" / "cast.json").write_text(json.dumps(document))
    assert bible_cli.run(parse(*base, "verify")) == 1
    assert "changed without a version bump" in capsys.readouterr().out
    assert bible_cli.run(parse(*base, "lock")) == 2  # refused: the persona changed and the version did not
    assert "changed without a version bump" in capsys.readouterr().err


def test_gaps_lists_a_name_that_recurs_with_no_sheet_and_exits_1(world, capsys):
    base, found, _ = world
    found["cleaning-fee"] = release("cleaning-fee", "rex", "bruno")
    found["other-reel"] = release("other-reel", "rex", "bruno")
    (world[2] / "outbox.json").write_text(json.dumps({"version": 1, "videos": {"cleaning-fee": {}, "other-reel": {}}}))
    assert bible_cli.run(parse(*base, "gaps")) == 1
    out = capsys.readouterr().out
    assert "missing: bruno (okayville) is on 2 published reels with no sheet" in out
    assert "placeholders waiting" in out
