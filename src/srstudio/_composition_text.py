"""Closed native text assets, immutable fonts and content-addressed portable resources."""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterable

from . import composition as c
from . import fonts, layout
from ._composition_preflight import _digest, _id

MAX_BYTES = 8 * 1024**2
MAX_FONTS = 16


def fail(expected: str) -> c.CompositionError:
    return c._fail('payload.text', None, expected, 'composition.payload')


def validate(items: tuple[c.VectorFont, ...]) -> int:
    if type(items) is not tuple or len(items) > MAX_FONTS:
        raise fail('an immutable tuple of at most 16 VectorFont records')
    size = 0
    seen = set()
    for item in items:
        if type(item) is not c.VectorFont or type(item.id) is not str:
            raise fail('VectorFont records with string IDs')
        _id(item.id, 'fonts.id')
        if item.id in seen:
            raise fail('unique font IDs')
        seen.add(item.id)
        if (
            type(item.data) is not bytes
            or not 1 <= len(item.data) <= MAX_BYTES
            or type(item.license_text) is not str
            or not item.license_text.strip()
            or len(item.license_text) > 65536
            or '\x00' in item.license_text
        ):
            raise fail('immutable bounded font bytes and a nonempty UTF-8 license notice of at most 64 KiB')
        try:
            notice = item.license_text.encode('utf-8')
        except UnicodeError as error:
            raise fail('a UTF-8 license notice') from error
        if len(notice) > 65536:
            raise fail('at most 64 KiB of license bytes')
        size += len(item.data) + len(notice)
    if size > MAX_BYTES:
        raise fail('at most eight MiB of combined fonts and licenses')
    return size


def source_digest(source: c.VectorSource) -> str:
    if type(source) is not c.VectorSource or type(source.xml) is not bytes or len(source.xml) > MAX_BYTES:
        raise fail('a VectorSource with at most eight MiB of immutable XML')
    if len(source.xml) + validate(source.fonts) > MAX_BYTES:
        raise fail('at most eight MiB of XML, font and license buffers')
    xml = hashlib.sha256(source.xml).hexdigest()
    if not source.fonts:
        return xml
    return _digest(
        {
            'schema': 'srstudio.vector-source/1.0.0',
            'xml': xml,
            'fonts': [
                {
                    'id': f.id,
                    'font': hashlib.sha256(f.data).hexdigest(),
                    'license': hashlib.sha256(f.license_text.encode('utf-8')).hexdigest(),
                }
                for f in sorted(source.fonts, key=lambda f: f.id)
            ],
        }
    )


def paths(font: c.VectorFont) -> tuple[str, str]:
    return (
        'font-' + hashlib.sha256(font.data).hexdigest() + '.ttf',
        'license-' + hashlib.sha256(font.license_text.encode('utf-8')).hexdigest() + '.txt',
    )


def resources(assets: Iterable[c.PreparedVector]) -> tuple[c.BundleResource, ...]:
    result = {}
    for asset in assets:
        for font in asset.fonts:
            path, notice = paths(font)
            result[path] = font.data
            result[notice] = font.license_text.encode('utf-8')
    return tuple(c.BundleResource(name, data) for name, data in sorted(result.items()))


def _local(value: str) -> bool:
    return bool(re.fullmatch(r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*', value)) and all(
        part not in ('.', '..') for part in value.split('/')
    )


def verify(root: ET.Element, items: tuple[c.VectorFont, ...]) -> dict[str, layout.Box]:
    """Verify metadata without opening source paths. Explicit clipping bounds glyph overflow."""
    supplied = {f.id: f for f in items}
    declared = root.findall('assets/font')
    if len(declared) != len(supplied) or {f.get('id') for f in declared} != supplied.keys():
        raise fail('exactly one supplied VectorFont for every declared font')
    if declared and root.find('project').get('fontPolicy') != 'pinned':  # type: ignore[union-attr]
        raise fail('fontPolicy="pinned" on text source projects')
    for node in declared:
        font = supplied[node.attrib['id']]
        facts = fonts.inspect_ttf(font.data)
        tables = fonts._tables(font.data)
        if not {b'glyf', b'loca'} <= tables.keys() or tables.keys() & {
            b'sbix',
            b'CBDT',
            b'CBLC',
            b'EBDT',
            b'EBLC',
            b'EBSC',
            b'COLR',
            b'CPAL',
            b'SVG ',
        }:
            raise fail('TrueType outline fonts without bitmap, color or SVG glyph tables')
        if (
            facts.italic
            or node.get('family') != facts.family
            or node.get('weight') != str(facts.weight)
            or node.get('sha256') != hashlib.sha256(font.data).hexdigest()
            or not _local(node.get('src', ''))
            or not _local(node.get('license', ''))
        ):
            raise fail('upright font metadata matching actual bytes, SHA-256 and safe relative resource labels')
    boxes = {}
    used = set()
    count = 0
    for node in root.findall('assets/text'):
        font_id = node.get('fontAsset')
        if font_id not in supplied or node.get('overflow') != 'clip':
            raise fail('an explicit local fontAsset and overflow="clip" for bounded native text')
        used.add(font_id)
        text = node.get('text', '')
        count += len(text.encode('utf-8'))
        if not text or len(text) > 4096 or count > 32768:
            raise fail('nonempty text, at most 4096 characters per asset and 32768 total UTF-8 bytes')
        width, height = (float(node.get(a, '0')) for a in ('width', 'height'))
        if not (0 < width <= 8192 and 0 < height <= 8192):
            raise fail('explicit text width and height in (0, 8192]')
        boxes[node.attrib['id']] = layout.Box(0, 0, width, height)
    if used != supplied.keys():
        raise fail('every supplied font referenced by a native text asset')
    for node in root.iter('layer'):
        if node.get('asset') not in boxes:
            raise fail('layers referencing only local native text assets')
    return boxes


def portable(root: ET.Element, items: tuple[c.VectorFont, ...]) -> ET.Element:
    """Rewrite resource labels only after verification; preserve all native text layout attributes."""
    supplied = {f.id: f for f in items}
    for node in root.findall('assets/font'):
        path, notice = paths(supplied[node.attrib['id']])
        node.set('src', path)
        node.set('license', notice)
    return root


def scope(source: ET.Element, prefix: str) -> None:
    mapping = {n.attrib['id']: prefix + '__' + n.attrib['id'] for n in source.iter() if 'id' in n.attrib}
    for node in source.iter():
        if 'id' in node.attrib:
            node.set('id', mapping[node.attrib['id']])
        for name in ('asset', 'fontAsset'):
            if name in node.attrib:
                node.set(name, mapping[node.attrib[name]])
        for name in ('fill', 'stroke', 'color'):
            value = node.get(name, '')
            if value.startswith('url(#'):
                node.set(name, f'url(#{mapping[value[5:-1]]})')
