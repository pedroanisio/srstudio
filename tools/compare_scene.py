#!/usr/bin/env python3
"""Compare two scene XMLs structurally.

Elements are compared in document order with their attributes and text; numbers are rounded to five
decimals. ``metadata`` is ignored (it records the generator), and ``animate``/``expression`` children
are canonicalised to the end of their parent: scene-render evaluates them by property, so their
position among sibling shapes has no effect on the picture.

    python3 tools/compare_scene.py ORIGINAL.scene.xml REBUILT.scene.xml
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from collections.abc import Iterator

IGNORE_TAGS = frozenset({"metadata"})
FLOATING = frozenset({"animate", "expression"})


def _norm(value: str):
    try:
        return round(float(value), 5)
    except ValueError:
        return value


def flatten(path: str) -> list[tuple[int, str, dict, str]]:
    root = ET.parse(path).getroot()
    out: list[tuple[int, str, dict, str]] = []

    def children(el: ET.Element) -> Iterator[ET.Element]:
        fixed = [c for c in el if c.tag not in FLOATING]
        floating = [c for c in el if c.tag in FLOATING]
        yield from fixed
        yield from floating

    def walk(el: ET.Element, depth: int) -> None:
        if el.tag in IGNORE_TAGS:
            return
        out.append((depth, el.tag, {k: _norm(v) for k, v in el.attrib.items()}, (el.text or "").strip()))
        for c in children(el):
            walk(c, depth + 1)

    walk(root, 0)
    return out


def diff(original: str, rebuilt: str) -> list[str]:
    """Human-readable lines for every differing position; empty when the scenes agree."""
    a, b = flatten(original), flatten(rebuilt)
    lines = []
    for i, (x, y) in enumerate(zip(a, b, strict=False)):  # unequal lengths are reported below
        if x != y:
            lines.append(f"#{i} original d{x[0]} <{x[1]} {x[2]}> {x[3]!r}")
            lines.append(f"#{i} rebuilt  d{y[0]} <{y[1]} {y[2]}> {y[3]!r}")
    if len(a) != len(b):
        lines.append(f"element count differs: original {len(a)}, rebuilt {len(b)}")
    return lines


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(__doc__)
        return 2
    lines = diff(argv[0], argv[1])
    total = len(flatten(argv[0]))
    print(f"{argv[0]}: {total} elements; differing positions: {len(lines) // 2}")
    for line in lines[:16]:
        print("  " + line)
    return 1 if lines else 0


if __name__ == "__main__":
    raise SystemExit(main())
