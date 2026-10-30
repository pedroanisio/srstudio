"""What test_package.py shares with other test modules."""

from sr_core.scene import Scene

from srstudio import Canvas


def project(root, slug="demo", width=1080):
    folder = root / "episodes" / slug
    folder.mkdir(parents=True)
    scene = Scene(version="auto")
    scene.add_project(width=width, height=1920, fps="30", duration=2, background="#FFFFFF")
    cv = Canvas(scene)
    cv.group(cv.comp, "x")
    (folder / f"{slug}.scene.xml").write_bytes(scene.to_bytes())
    return folder
