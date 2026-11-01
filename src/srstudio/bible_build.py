"""Write the cast bible folder: data, a sheet per character with its drawing, the diagram, the pages (ADR 0069).

Nothing here decides a fact. ``cast.json`` and ``relationships.json`` are the source; this module reads them, asks the
catalog for each approved drawing, asks the engine for the diagram, and writes the files with directory mode 700 and
file mode 600, the mode for files a tool produces.
"""

from __future__ import annotations

import shutil
from collections.abc import Mapping
from pathlib import Path

from . import bible_diagram, bible_render, catalog_specimens
from .bible import Bible, Character
from .cast_card import Lettering
from .errors import SrstudioError

__all__ = ["BibleBuildError", "build", "drawing_of"]

COPIED = ("cast.json", "relationships.json", "CHANGELOG.md")


class BibleBuildError(SrstudioError):
    """The folder cannot be written: a missing source file or a drawing the catalog does not have."""


def drawing_of(character: Character, specimens: Mapping[str, Path]) -> Path | None:
    """The picture of ``character``'s first approved drawing: ``part@version`` when registered so, else ``part``."""
    for d in character.look.drawing:
        for key in (f"{d.part}@{d.version}", d.part):
            if key in specimens:
                return specimens[key]
    return None


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)


def _folder(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.chmod(0o700)


def build(
    library: Path,
    out: Path,
    bible: Bible,
    *,
    model: str,
    order: list[str],
    specimens: Mapping[str, Path],
    faces: Lettering,
    engine: Path,
    work: Path,
) -> dict[str, int]:
    """Write the bible folder at ``out`` from ``library``; returns the crossings left in each world's diagram.

    A character with an approved drawing the catalog cannot show is a :class:`BibleBuildError`, never a sheet without
    its picture. A placeholder has no drawing and gets none."""
    for name in COPIED:
        if not (library / name).is_file():
            raise BibleBuildError(f"{library}: {name} is missing")
    _folder(out)
    sheets = out / "characters"
    _folder(sheets)
    written = []
    for character in bible.characters:
        picture = drawing_of(character, specimens)
        if character.look.drawing and picture is None:
            parts = ", ".join(f"{d.part}@{d.version}" for d in character.look.drawing)
            raise BibleBuildError(f"{character.slug}: the catalog has no picture of {parts}")
        link = None
        if picture is not None:
            target = sheets / f"{character.slug}.png"
            shutil.copyfile(picture, target)
            target.chmod(0o600)
            link = target.name
        _write(
            sheets / f"{character.slug}.md",
            bible_render.sheet(character, model=model, version=bible.version, order=order, drawing=link),
        )
        written.append(character.slug)
    for name in COPIED:
        shutil.copyfile(library / name, out / name)
        (out / name).chmod(0o600)
    _write(out / "canon.md", bible_render.canon(bible, model=model))
    _write(out / "world.md", bible_render.world(bible, model=model))
    _write(out / "open-decisions.md", bible_render.open_decisions(bible, model=model))
    _write(out / "README.md", bible_render.readme(bible, model=model, sheets=written))
    return bible_diagram.render(bible, out / "relationships.png", faces, engine, work)


def specimens_of(engine: Path, cache: Path, episodes: Path) -> dict[str, Path]:
    """Every part's picture from the catalog's specimen renderer, keyed as the registry names the part."""
    shelf = catalog_specimens.render_all(engine, cache, episodes)
    return {name: s.png for name, s in shelf.done.items()}
