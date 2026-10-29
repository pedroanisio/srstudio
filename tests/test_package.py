"""Every original episode ships a ``.vpkg.zip``: packed from its project, verified, and validated by the engine."""

import json
import subprocess
import wave
import zipfile

import pytest
from sr_core.scene import Scene, read, write

from srstudio import Canvas, package
from srstudio.social import InstagramPost


def post(title: str = "Five Years") -> InstagramPost:
    return InstagramPost(title=title, description="An interview that goes wrong.\n\nSecond paragraph.", credit="")


def project(root, slug="demo", width=1080):
    folder = root / "episodes" / slug
    folder.mkdir(parents=True)
    scene = Scene(version="auto")
    scene.add_project(width=width, height=1920, fps="30", duration=2, background="#FFFFFF")
    cv = Canvas(scene)
    cv.group(cv.comp, "x")
    (folder / f"{slug}.scene.xml").write_bytes(scene.to_bytes())
    return folder


def manifest(zip_path):
    return json.loads(zipfile.ZipFile(zip_path).read("vpkg.json"))


# -- the manifest ------------------------------------------------------------------------------------------------------
def test_the_manifest_names_the_package_its_primary_scene_and_the_render():
    m = package.manifest("five-years", post(), version="1.0.0", engine_version="0.8.0")
    assert m["format"] == "scene-video-package" and m["package"]["id"] == "five-years"
    assert m["package"]["title"] == "Five Years" and m["package"]["description"] == "An interview that goes wrong."
    assert m["scenes"] == [{"path": "five-years.scene.xml", "role": "primary", "generatedBy": "srstudio"}]
    [step] = m["pipeline"]["steps"]
    assert step["render"] == {"scene": "five-years.scene.xml", "output": "main", "to": "renders/five-years.mp4"}
    assert m["engines"] == [{"id": "rs", "version": "0.8.0", "tested": "full"}]


@pytest.mark.parametrize("slug", ["Printer_Recreation", "", "a b"])
def test_a_slug_the_format_cannot_name_is_refused(slug):
    with pytest.raises(package.PackageError, match="id"):
        package.manifest(slug, post(), version="1.0.0", engine_version="0.8.0")


# -- packing with the real tools ---------------------------------------------------------------------------------------
def test_pack_writes_a_verified_private_package_the_engine_validates(scene_render, tmp_path):
    folder = project(tmp_path)
    out = tmp_path / "vpkg"
    path = package.pack(folder, out, post(), engine=scene_render)
    assert path == out / "demo-1.0.0.vpkg.zip"
    assert path.stat().st_mode & 0o777 == 0o600 and out.stat().st_mode & 0o777 == 0o700
    m = manifest(path)
    assert m["package"]["version"] == "1.0.0"
    assert package.scene_sha(path) == package.sha256(folder / "demo.scene.xml")
    assert sorted(p.name for p in out.iterdir()) == ["demo-1.0.0.vpkg.zip"]  # no scratch left behind


def test_an_unchanged_scene_keeps_its_package_and_a_changed_one_gets_the_next_patch(scene_render, tmp_path):
    folder = project(tmp_path)
    out = tmp_path / "vpkg"
    first = package.pack(folder, out, post(), engine=scene_render)
    stamp = first.stat().st_mtime_ns
    assert package.pack(folder, out, post(), engine=scene_render) == first and first.stat().st_mtime_ns == stamp
    scene = folder / "demo.scene.xml"
    scene.write_bytes(scene.read_bytes().replace(b'id="x"', b'id="y"'))
    second = package.pack(folder, out, post(), engine=scene_render)
    assert second == out / "demo-1.0.1.vpkg.zip"
    assert package.scene_sha(second) == package.sha256(scene)
    assert first.is_file()  # an earlier version is kept, never overwritten


def audio_project(root):
    folder = project(root)
    (folder / "assets").mkdir()
    with wave.open(str(folder / "assets" / "tone.wav"), "wb") as w:
        w.setparams((1, 2, 48000, 0, "NONE", "not compressed"))
        w.writeframes(b"\x01\x00" * 48000)
    scene = read(folder / "demo.scene.xml")
    scene.add_assets().add_audio(id="tone", src="assets/tone.wav")
    write(scene, folder / "demo.scene.xml")
    return folder


def test_replacing_an_unpinned_asset_repackages_its_current_bytes(scene_render, tmp_path):
    folder = audio_project(tmp_path)
    out = tmp_path / "vpkg"
    first = package.pack(folder, out, post(), engine=scene_render)
    xml = (folder / "demo.scene.xml").read_bytes()
    audio = folder / "assets" / "tone.wav"
    with wave.open(str(audio), "wb") as w:
        w.setparams((1, 2, 48000, 0, "NONE", "not compressed"))
        w.writeframes(b"\x02\x00" * 48000)
    second = package.pack(folder, out, post(), engine=scene_render)
    assert second != first and second.name == "demo-1.0.1.vpkg.zip"
    assert (folder / "demo.scene.xml").read_bytes() == xml
    with zipfile.ZipFile(second) as z:
        assert z.read("project/assets/tone.wav") == audio.read_bytes()
    assert package.pack(folder, out, post(), engine=scene_render) == second


@pytest.mark.parametrize("change", ["add", "edit", "delete"])
def test_supporting_files_are_part_of_package_freshness(scene_render, tmp_path, change):
    folder = project(tmp_path)
    notes = folder / "notes.txt"
    if change != "add":
        notes.write_text("original")
    out = tmp_path / "vpkg"
    first = package.pack(folder, out, post(), engine=scene_render)
    if change == "delete":
        notes.unlink()
    else:
        notes.write_text("updated")
    second = package.pack(folder, out, post(), engine=scene_render)
    assert second != first
    listed = {f["path"] for f in manifest(second)["files"]}
    assert ("notes.txt" in listed) == (change != "delete")


def test_a_missing_referenced_asset_cannot_reuse_an_older_package(scene_render, tmp_path):
    folder = audio_project(tmp_path)
    out = tmp_path / "vpkg"
    first = package.pack(folder, out, post(), engine=scene_render)
    (folder / "assets" / "tone.wav").unlink()
    with pytest.raises(package.PackageError, match="pack failed"):
        package.pack(folder, out, post(), engine=scene_render)
    assert list(out.iterdir()) == [first]


def test_changed_package_metadata_gets_a_new_version(scene_render, tmp_path):
    folder = project(tmp_path)
    out = tmp_path / "vpkg"
    first = package.pack(folder, out, post(), engine=scene_render)
    second = package.pack(folder, out, post("Revised title"), engine=scene_render)
    assert second != first
    assert manifest(second)["package"]["title"] == "Revised title"


def test_a_project_without_its_scene_is_refused(tmp_path):
    folder = tmp_path / "episodes" / "demo"
    folder.mkdir(parents=True)
    with pytest.raises(package.PackageError, match="scene"):
        package.pack(folder, tmp_path / "vpkg", post())


# -- failure paths ----------------------------------------------------------------------------------------------------
class Runner:
    """Answers each command with the next code; a code of None runs the real command."""

    def __init__(self, *codes):
        self.codes, self.calls = list(codes), []

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        code = self.codes.pop(0) if self.codes else None
        if code is None:
            return subprocess.run(cmd, **kw)
        return subprocess.CompletedProcess(cmd, code, "", f"{cmd[1]}: it broke\n")


@pytest.mark.parametrize(
    "codes, match",
    [
        ((1,), "version"),  # the engine cannot say which version it is
        ((0,), "version"),  # it answers, but with no version in it
        ((None, 1), "pack failed"),
        ((None, None, 1), "verify failed"),
        ((None, None, None, 1), "valid"),
    ],
)
def test_a_failing_pack_verify_or_engine_check_is_a_typed_error_and_leaves_no_package(request, tmp_path, codes, match):
    engine = request.getfixturevalue("scene_render") if None in codes else None  # None runs the real command
    folder = project(tmp_path)
    out = tmp_path / "vpkg"
    with pytest.raises(package.PackageError, match=match):
        package.pack(folder, out, post(), engine=engine, run=Runner(*codes))
    assert not out.exists() or list(out.iterdir()) == []  # no package and no scratch


def test_an_injected_runner_answers_for_the_engine_so_none_is_resolved(tmp_path, monkeypatch):
    monkeypatch.delenv("SRSTUDIO_ENGINE", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path))  # no scene-render to find
    runner = Runner(1)
    with pytest.raises(package.PackageError, match="version"):
        package.pack(project(tmp_path), tmp_path / "vpkg", post(), run=runner)
    assert runner.calls == [["scene-render", "--version"]]


def test_missing_tools_are_a_typed_error(tmp_path):
    folder = project(tmp_path)
    with pytest.raises(package.PackageError, match="scenerender-vpkg"):
        package.pack(folder, tmp_path / "vpkg", post(), tool=tmp_path / "nope")
    with pytest.raises(package.PackageError, match="engine"):
        package.pack(folder, tmp_path / "vpkg", post(), engine=tmp_path / "nope")


def test_a_package_whose_manifest_lies_about_its_scene_is_refused(tmp_path):
    bad = tmp_path / "demo-1.0.0.vpkg.zip"
    with zipfile.ZipFile(bad, "w") as z:
        z.writestr("vpkg.json", json.dumps({"scenes": [{"path": "demo.scene.xml", "role": "primary"}], "files": []}))
    with pytest.raises(package.PackageError, match="primary scene"):
        package.scene_sha(bad)
    (tmp_path / "junk.vpkg.zip").write_bytes(b"not a zip")
    with pytest.raises(package.PackageError, match="zip"):
        package.scene_sha(tmp_path / "junk.vpkg.zip")
