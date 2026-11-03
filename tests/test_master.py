"""A master is encoded beside its place and installed write-once (ADR 0170): a re-run whose strict check fails can no
longer replace a good master."""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from srstudio import files, master
from srstudio.cli import main

SCENE = '<scene><project fps="24"/><output id="main" path="renders/{slug}.mp4" report="qa/r.json"/></scene>'


def project(tmp_path: Path, slug: str = "reel", outputs: str | None = None) -> Path:
    folder = tmp_path / "episodes" / slug
    folder.mkdir(parents=True)
    scene = folder / f"{slug}.scene.xml"
    scene.write_text(outputs or SCENE.format(slug=slug))
    return scene


def fake_engine(tmp_path: Path, code: int, body: str = "master bytes", write: bool = True) -> Path:
    """Writes each output the way scene-render does: under --out-dir, at the document's relative path."""
    engine = tmp_path / f"engine-{code}-{abs(hash(body))}"
    made = f'mkdir -p "$out/renders" && printf %s "{body}" > "$out/renders/$slug.mp4"' if write else ":"
    engine.write_text(
        "#!/bin/sh\n"
        'slug=$(basename "$2" .scene.xml); out=""\n'
        'prev=""; for a in "$@"; do [ "$prev" = "--out-dir" ] && out="$a"; prev="$a"; done\n'
        f"{made}\n"
        'echo "args: $*"\n'
        f"echo engine-said >&2\nexit {code}\n"
    )
    engine.chmod(engine.stat().st_mode | stat.S_IXUSR)
    return engine


def leftovers(out: Path) -> list[str]:
    return sorted(p.name for p in out.iterdir() if p.name.startswith("."))


def test_a_master_is_encoded_into_a_stage_and_installed(tmp_path):
    scene, out = project(tmp_path), tmp_path / "generated"
    done = master.encode(scene, out, engine=fake_engine(tmp_path, 0), args=("--strict", "--hw", "software"))
    assert done.paths == (out / "renders" / "reel.mp4",) and done.returncode == 0
    assert (out / "renders" / "reel.mp4").read_text() == "master bytes"
    assert "--strict --hw software --out-dir" in done.output and "engine-said" in done.output
    assert leftovers(out) == []


def test_a_strict_finding_keeps_its_master_for_the_record_and_reports_the_exit(tmp_path):
    scene, out = project(tmp_path), tmp_path / "generated"
    done = master.encode(scene, out, engine=fake_engine(tmp_path, 1, "with findings"))
    assert done.returncode == 1 and done.paths[0].read_text() == "with findings"


def test_a_re_run_never_replaces_the_master_and_spends_no_encode(tmp_path):
    scene, out = project(tmp_path), tmp_path / "generated"
    master.encode(scene, out, engine=fake_engine(tmp_path, 0, "the good master"))
    ran = []

    def never(*a, **kw):
        ran.append(a)
        raise AssertionError("encoded over an approved master")

    with pytest.raises(files.WriteOnceError, match="reel.mp4 exists"):
        master.encode(scene, out, engine=fake_engine(tmp_path, 1, "a failed re-run"), run=never)
    assert ran == [] and (out / "renders" / "reel.mp4").read_text() == "the good master"


def test_next_writes_the_new_master_beside_the_old_one(tmp_path):
    scene, out = project(tmp_path), tmp_path / "generated"
    master.encode(scene, out, engine=fake_engine(tmp_path, 0, "the good master"))
    done = master.encode(scene, out, engine=fake_engine(tmp_path, 1, "a failed re-run"), next_name=True)
    assert done.paths == (out / "renders" / "reel-v2.mp4",) and done.returncode == 1
    assert (out / "renders" / "reel.mp4").read_text() == "the good master"
    assert (out / "renders" / "reel-v2.mp4").read_text() == "a failed re-run"


def test_a_master_that_appears_during_the_encode_is_kept_and_the_new_one_goes_beside_it(tmp_path):
    scene, out = project(tmp_path), tmp_path / "generated"
    engine = fake_engine(tmp_path, 0, "late")

    def racing(argv, **kw):
        (out / "renders").mkdir(parents=True, exist_ok=True)
        (out / "renders" / "reel.mp4").write_text("another session's master")
        return master.subprocess.run(argv, **kw)

    with pytest.raises(files.WriteOnceError, match="reel-v2.mp4"):
        master.encode(scene, out, engine=engine, run=racing)
    assert (out / "renders" / "reel.mp4").read_text() == "another session's master"
    assert (out / "renders" / "reel-v2.mp4").read_text() == "late"
    assert leftovers(out) == []


def test_an_engine_that_writes_no_master_is_a_typed_error_and_leaves_no_stage(tmp_path):
    scene, out = project(tmp_path), tmp_path / "generated"
    with pytest.raises(master.MasterError, match=r"wrote no master \(exit 3\)[\s\S]*engine-said"):
        master.encode(scene, out, engine=fake_engine(tmp_path, 3, write=False))
    assert leftovers(out) == []


@pytest.mark.parametrize("bad", [("-o", "x.mp4"), ("--path", "x.mp4"), ("--path=x.mp4",), ("--out-dir", "y")])
def test_an_output_place_in_the_engine_arguments_is_refused(tmp_path, bad):
    scene = project(tmp_path)
    with pytest.raises(master.MasterError, match="chooses where the master goes"):
        master.encode(scene, tmp_path / "g", engine=fake_engine(tmp_path, 0), args=bad)


@pytest.mark.parametrize(
    "outputs, said",
    [
        ("<scene/>", "declares no output"),
        ('<scene><output id="a" path="/abs/x.mp4"/></scene>', "relative"),
        ('<scene><output id="a" path="../x.mp4"/></scene>', "relative"),
        ('<scene><output id="a"/></scene>', "relative"),
        ("<scene", "not a scene document"),
    ],
)
def test_a_document_whose_outputs_cannot_be_staged_is_refused(tmp_path, outputs, said):
    scene = project(tmp_path, outputs=outputs)
    with pytest.raises(master.MasterError, match=said):
        master.encode(scene, tmp_path / "g", engine=fake_engine(tmp_path, 0))


def test_the_command_installs_and_exits_with_the_engine_status(tmp_path, capsys):
    scene, out = project(tmp_path), tmp_path / "generated"
    argv = ["master", str(scene), "--out-dir", str(out), "--engine", str(fake_engine(tmp_path, 1)), "--", "--strict"]
    assert main(argv) == 1
    printed = capsys.readouterr()
    assert str(out / "renders" / "reel.mp4") in printed.out and "--strict" in printed.out
    assert main(argv) == 2
    assert "never replaced" in capsys.readouterr().err
    assert main([*argv[:-2], "--next", "--", "--strict"]) == 1
    assert (out / "renders" / "reel-v2.mp4").is_file()


def test_the_command_needs_an_output_folder(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("SRSTUDIO_RENDERS", raising=False)
    assert main(["master", str(project(tmp_path)), "--engine", str(fake_engine(tmp_path, 0))]) == 2
    assert "--out-dir" in capsys.readouterr().err
    monkeypatch.setenv("SRSTUDIO_RENDERS", str(tmp_path / "gen" / "renders"))
    assert main(["master", str(tmp_path / "episodes" / "reel" / "reel.scene.xml"),
                 "--engine", str(fake_engine(tmp_path, 0))]) == 0  # fmt: skip
    assert (tmp_path / "gen" / "renders" / "reel.mp4").is_file()
