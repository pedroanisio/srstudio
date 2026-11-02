"""Ink drawn on a finished 3D group from flat id colours, in the same document and under the same cameras.

:func:`ink_pass` copies each visible object of a group into a group above it, in an unlit colour that stands for what
the eye reads as one surface, and the engine's 2D effects on that group turn colour changes into lines. A line therefore
follows the model, not the brightness of the picture, so light and texture cannot draw one. Rigs are not copied: a
copy stays parented to the rig its original uses, so the two passes cannot drift and the keys exist once.

Colours group by ``families``, a material's name to the surface it belongs to, because materials are cut for shading
and not for drawing: a head's scalp and cheek are two materials and one skin. Meshes on one parent in one family share
a colour, and a primitive keeps its own. An id material is always double-sided, or a face wound the wrong way would
draw in the lit pass and vanish from this one.

The shaders live in ``assets/shaders`` (:func:`shaders` puts them beside a scene) and are pinned by ``vendored.json``.
Refused input raises :class:`InkPassError` before the scene changes.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

from sr_core.scene import Element, Group

from . import checks
from .errors import SrstudioError

__all__ = ["Ink", "InkPassError", "id_colour", "ink_pass", "shaders"]

_SHADERS = ("clean.fs", "ink.fs")


class InkPassError(SrstudioError, ValueError):
    """A group or a setting an ink pass cannot be drawn from."""


@dataclass(frozen=True)
class Ink:
    """How the lines look: ``radius`` in pixels, ``wobble`` and ``vary`` for a drawn hand, and an sRGB ``colour``."""

    pixels: tuple[int, int] = (1080, 1920)
    radius: float = 1.0
    wobble: float = 0.0
    vary: float = 0.0
    colour: tuple[float, float, float] = (0.035, 0.03, 0.07)

    def __post_init__(self) -> None:
        if not all(checks.number(v) and v > 0 for v in (*self.pixels, self.radius)):
            raise InkPassError(f"pixels and radius must be positive, got {self.pixels} and {self.radius!r}")
        if not all(checks.number(v) and v >= 0 for v in (self.wobble, self.vary)):
            raise InkPassError(f"wobble and vary cannot be negative, got {self.wobble!r} and {self.vary!r}")
        if not all(checks.number(v) and 0 <= v <= 1 for v in self.colour):
            raise InkPassError(f"an ink colour runs from 0 to 1, got {self.colour}")

    @property
    def params(self) -> dict[str, float]:
        red, green, blue = self.colour
        return {
            "pixelsX": self.pixels[0],
            "pixelsY": self.pixels[1],
            "radius": self.radius,
            "vary": self.vary,
            "wobble": self.wobble,
            "inkR": red,
            "inkG": green,
            "inkB": blue,
        }


def id_colour(key: str) -> str:
    """The flat colour of a surface, a function of its key alone."""
    return "#" + hashlib.sha256(key.encode()).hexdigest()[:6]


def _find(node: Element, id_: str) -> Element | None:
    for child in node.elements():
        if child.attributes().get("id") == id_:
            return child
        found = _find(child, id_)
        if found is not None:
            return found
    return None


def _ids(node: Element) -> set[str]:
    own = {node.attributes()["id"]} if "id" in node.attributes() else set()
    return own.union(*(_ids(child) for child in node.elements()))


def _copy(node: Element, **changes: str) -> Element:
    attrs = {**node.attributes(), **changes}
    made = type(node)(xml_name=node.xml_name, **attrs)
    for child in node.elements():
        made.add(_copy(child))
    return made


def _surface(item: Element, families: Mapping[str, str]) -> str:
    attrs = item.attributes()
    if attrs["primitive"] != "mesh":
        return attrs["id"]
    material = attrs["material"]
    return f"{attrs.get('parent', '')}|{families.get(material, material)}"


def _child(root: Element, name: str) -> Any:
    for node in root.elements():
        if node.xml_name == name:
            return node
    return getattr(root, f"add_{name}")()


def ink_pass(
    scene: Element,
    world: str,
    *,
    ink: Ink | None = None,
    families: Mapping[str, str] | None = None,
    name: str = "ink",
    prefix: str = "i-",
) -> Element:
    """Draw ink over the 3D group ``world`` of ``scene``; returns the new group, placed straight above it."""
    ink = Ink() if ink is None else ink
    families = {} if families is None else families
    if not name or not prefix:
        raise InkPassError(f"a pass needs a name and a prefix, got {name!r} and {prefix!r}")
    source = _find(scene, world)
    if source is None or not isinstance(source, Group):
        raise InkPassError(f"there is no group {world!r} in this scene")
    items = [n for n in source.elements() if n.xml_name == "object3D"]
    drawn = [n for n in items if n.attributes().get("visible") != "false"]
    if not drawn:
        raise InkPassError(f"the group {world!r} has nothing visible to draw ink on")
    known = _ids(scene)
    wanted = {name, f"{name}-clean", f"{name}-lines", *(prefix + n.attributes()["id"] for n in drawn)}
    if wanted & known:
        raise InkPassError(f"{sorted(wanted & known)[0]!r} is already in this scene")
    copied = {n.attributes()["id"] for n in drawn}
    colours: dict[str, str] = {}
    copies = []
    for item in drawn:
        attrs = item.attributes()
        key = _surface(item, families)
        colour = id_colour(key)
        material = colours.setdefault(colour, f"{prefix}id-{colour[1:]}")
        changes = {"id": prefix + attrs["id"], "material": material}
        if attrs.get("parent") in copied:
            changes["parent"] = prefix + attrs["parent"]
        made = _copy(item, **changes)
        for attribute in ("castShadow", "receiveShadow"):
            if attribute in made.attributes():
                delattr(made, attribute)
        copies.append(made)
    materials = _child(scene, "materials")
    for colour, material in colours.items():
        if material not in known:
            materials.add_material(id=material, baseColor=colour, unlit=True, doubleSided=True)
    effects = _child(scene, "effects")
    cleaned = effects.add_effect(id=f"{name}-clean", type="shader", src="clean.fs")
    lines = effects.add_effect(id=f"{name}-lines", type="shader", src="ink.fs")
    for setting, value in ink.params.items():
        if setting in ("pixelsX", "pixelsY"):
            cleaned.add_param(name=setting, value=str(value))
        lines.add_param(name=setting, value=str(value))
    group = Group(id=name, effects=f"{name}-clean {name}-lines")
    for made in copies:
        group.add(made)
    owner = source.owner
    assert owner is not None
    owner.add(group)
    nodes = owner.nodes
    nodes.remove(group)
    nodes.insert(nodes.index(source) + 1, group)
    return group


def shaders(folder: Path) -> list[Path]:
    """Put the pinned shaders in ``folder``, beside a scene that names them."""
    home = resources.files("srstudio") / "assets" / "shaders"
    written = []
    for name in _SHADERS:
        target = folder / name
        target.write_bytes((home / name).read_bytes())
        written.append(target)
    return written
