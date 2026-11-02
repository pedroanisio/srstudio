"""Bounded immutable print recipes and worker-only compilation with actual font metadata."""

from __future__ import annotations

import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, replace

from sr_core.scene import Scene, read

from . import composition as c
from . import fonts, plates
from ._composition_png import MAX_BYTES
from ._composition_preflight import _digest, _id

MAX_PRINTS = 128
_COLOR = re.compile(r'#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?\Z')


def _fail(expected: str) -> c.CompositionError:
    return c._fail('plate.print', None, expected, 'composition.payload')


def validate(item: c.PlatePrint) -> int:
    if type(item) is not c.PlatePrint or type(item.id) is not str:
        raise _fail('a PlatePrint with an identifier')
    _id(item.id, 'print.id')
    recipe = item.recipe
    if (
        type(recipe) is not plates.Print
        or type(item.font) is not bytes
        or not 1 <= len(item.font) <= MAX_BYTES
        or type(item.license) is not str
        or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.+-]{0,127}', item.license)
    ):
        raise _fail('an exact Print recipe, immutable bounded font bytes and an explicit license identifier')
    if (
        any(type(n) is not int or not 2 <= n <= 8192 for n in (recipe.width, recipe.height))
        or recipe.width * recipe.height * 4 > MAX_BYTES
        or type(recipe.lines) is not tuple
        or len(recipe.lines) > MAX_PRINTS
        or type(recipe.background) is not str
        or not _COLOR.fullmatch(recipe.background)
        or type(recipe.border) is not str
        or recipe.border
        and not _COLOR.fullmatch(recipe.border)
    ):
        raise _fail('bounded dimensions, at most eight MiB of RGBA pixels, 128 immutable lines and hex colors')
    count = 0
    for line in recipe.lines:
        if (
            type(line) is not plates.Line
            or type(line.text) is not str
            or not line.text.strip()
            or len(line.text) > 4096
            or not set(line.text) <= plates.PRINTABLE
            or any(
                type(n) not in (int, float) or not math.isfinite(n) or abs(n) > 8192
                for n in (line.x, line.y, line.size)
            )
            or not 0 < line.size <= 8192
            or type(line.color) is not str
            or not _COLOR.fullmatch(line.color)
        ):
            raise _fail('typed bounded English lines with finite coordinates, positive size and hex color')
        count += len(line.text.encode('utf-8'))
    if count > 32768:
        raise _fail('at most 32768 text bytes per print')
    return len(item.font) + len(json.dumps(asdict(recipe), separators=(',', ':')).encode('utf-8')) + len(item.license)


def definition(item: c.PlatePrint) -> dict:
    return {'recipe': asdict(item.recipe), 'font': hashlib.sha256(item.font).hexdigest(), 'license': item.license}


def snapshot(recipe: plates.Print, font: bytes | None, license: str | None) -> c.PlatePrint:
    # Validation gives callers a typed refusal for missing/untyped font inputs.
    item = c.PlatePrint('label', recipe, font, license)  # type: ignore[arg-type]
    validate(item)
    return replace(item, id='print_' + _digest(definition(item)))


def prepare(source: c.PlateSource) -> tuple[dict[str, str], dict[str, bytes], int]:
    """Compile closed label scenes without rendering, only inside the bounded worker."""
    labels = {item.id: item for item in source.prints}
    if len(labels) != len(source.prints) or set(labels) != {m.print for m in source.materials if m.print}:
        raise _fail('unique print records matching exactly the material references')
    if any(m.print and m.color_map for m in source.materials):
        raise _fail('only one color map or printed label per material')
    paths, resources = {}, {}
    nodes = 0
    for item in source.prints:
        validate(item)
        try:
            facts = fonts.inspect_ttf(item.font)
        except fonts.FontError as error:
            raise _fail('a valid TrueType font with readable family, weight and style metadata') from error
        if facts.italic:
            raise _fail('an upright font for the printed-label adapter')
        font_path = 'fonts/' + hashlib.sha256(item.font).hexdigest() + '.ttf'
        root = ET.fromstring(plates._print_document(item.recipe, item.font))
        font = root.find('assets/font')
        assert font is not None
        font.set('src', '../' + font_path)
        font.set('family', facts.family)
        font.set('weight', str(facts.weight))
        font.set('license', item.license)
        xml = ET.tostring(root, encoding='utf-8', xml_declaration=True)
        scene = read(xml)
        assert isinstance(scene, Scene)
        errors = scene.check(schema=True)
        if errors:
            raise _fail('a schema-valid printed label: ' + str(errors[:3]))
        name = 'prints/' + hashlib.sha256(xml).hexdigest()
        paths[item.id] = name + '.png'
        resources[name + '.scene.xml'] = xml
        resources[font_path] = item.font
        nodes += sum(1 for _ in root.iter())
        if sum(map(len, resources.values())) > MAX_BYTES:
            raise _fail('at most eight MiB of compiled label resources')
    return paths, resources, nodes
