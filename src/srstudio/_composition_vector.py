"""Verify closed vector payloads and bound their complete animation envelopes before emission."""

from __future__ import annotations

import io
import math
import re
import xml.etree.ElementTree as ET

from sr_core.scene import Scene, read

from . import _composition_text as text_assets
from . import composition as c
from . import layout
from ._composition_preflight import _binding
from .errors import SrstudioError

MAX_XML_BYTES = 8 * 1024**2
_TRANSFORM = {'x', 'y', 'rotation', 'scaleX', 'scaleY', 'anchorX', 'anchorY'}
_NODE = _TRANSFORM | {'id', 'name', 'start', 'end', 'visible', 'opacity'}
_ALLOWED = {
    'scene': {'version'},
    'project': {'width', 'height', 'fps', 'duration', 'seed', 'fontPolicy'},
    'assets': set(),
    'font': {'id', 'src', 'family', 'weight', 'sha256', 'license'},
    'text': {
        'id',
        'text',
        'fontAsset',
        'width',
        'height',
        'size',
        'color',
        'align',
        'verticalAlign',
        'lineHeight',
        'letterSpacing',
        'direction',
        'language',
        'wrap',
        'overflow',
    },
    'layer': _NODE | {'asset'},
    'composition': set(),
    'paints': set(),
    'linearGradient': {'id', 'x1', 'y1', 'x2', 'y2', 'units', 'spread', 'interpolationSpace'},
    'radialGradient': {'id', 'cx', 'cy', 'r', 'fx', 'fy', 'units', 'spread', 'interpolationSpace'},
    'stop': {'offset', 'color', 'opacity'},
    'group': _NODE | {'timeOffset', 'timeScale'},
    'shape': _NODE
    | {
        'shape',
        'width',
        'height',
        'path',
        'fill',
        'stroke',
        'strokeWidth',
        'strokeCap',
        'strokeJoin',
        'miterLimit',
        'fillRule',
        'radius',
        'dashArray',
        'dashOffset',
    },
    'animate': {'property', 'defaultInterpolation', 'timeBase', 'extrapolateBefore', 'extrapolateAfter'},
    'key': {'time', 'value', 'interpolation'},
}
_MONOTONE = {'linear', 'hold'} | {
    f'{kind}-{direction}'
    for kind in ('sine', 'quad', 'cubic', 'quart', 'quint', 'expo', 'circ')
    for direction in ('in', 'out', 'in-out')
}
_PAINT = re.compile(r'url\(#([^()]+)\)\Z')


def _fail(path: str, actual: object, expected: object) -> c.CompositionError:
    return c._fail('payload.' + path, actual, expected, 'composition.payload')


def _number(value: str, path: str) -> float:
    try:
        result = float(value)
    except ValueError as error:
        raise _fail(path, value, 'a finite scalar in source units') from error
    if not math.isfinite(result) or abs(result) > 1e9:
        raise _fail(path, value, 'a finite scalar with magnitude <= 1e9')
    return result


def _tree(binding: c.AssetBinding, xml: bytes) -> ET.Element:
    if type(xml) is not bytes or len(xml) > min(MAX_XML_BYTES, binding.memory_bytes // 8):
        raise _fail('xml', None, 'immutable UTF-8 XML within the declared memory allowance and 8 MiB cap')
    try:
        text = xml.decode('utf-8')
        if '<!' in text or '\x00' in text:
            raise _fail('xml', None, 'XML without DTDs, entity declarations or NUL bytes')
        depth = count = 0
        parser = ET.iterparse(io.BytesIO(xml), events=('start', 'end'))
        root = None
        for event, node in parser:
            if root is None:
                root = node
            depth += 1 if event == 'start' else -1
            count += event == 'start'
            if depth > 64 or count > binding.nodes:
                raise _fail('nodes', count, 'at most the declared nodes and 64 nested elements')
        assert root is not None  # empty XML raises ParseError
        return root
    except (ET.ParseError, UnicodeError) as error:
        raise _fail('xml', None, 'well-formed UTF-8 XML') from error


def _animation(node: ET.Element, binding: c.AssetBinding) -> None:
    prop = node.get('property', '')
    if binding.duration is None or prop not in _TRANSFORM | {'opacity', 'visible'}:
        raise _fail('animate.property', prop, 'bounded transform/opacity/visibility keys with a source duration')
    if node.get('timeBase', 'composition') not in ('composition', 'local'):
        raise _fail('animate.timeBase', node.get('timeBase'), 'composition or local seconds')
    if any(node.get(name, 'hold') != 'hold' for name in ('extrapolateBefore', 'extrapolateAfter')):
        raise _fail('animate', None, 'held endpoint extrapolation')
    default = node.get('defaultInterpolation', 'linear')
    if default not in _MONOTONE:
        raise _fail('animate.defaultInterpolation', default, 'a supported non-overshooting interpolation')
    previous = -1.0
    for key in node:
        time = _number(key.get('time', ''), 'key.time')
        if not previous < time <= binding.duration or time < 0:
            raise _fail('key.time', time, 'ordered, unique keys within the source duration')
        previous = time
        if key.get('interpolation', default) not in _MONOTONE:
            raise _fail('key.interpolation', key.get('interpolation'), 'a supported non-overshooting interpolation')
        value = key.get('value', '')
        if prop == 'visible':
            if value not in ('true', 'false', '0', '1'):
                raise _fail('key.value', value, 'a visibility boolean')
        else:
            number = _number(value, 'key.value')
            if prop == 'opacity' and not 0 <= number <= 1:
                raise _fail('key.value', number, 'opacity in [0, 1]')


def _range(node: ET.Element, prop: str, default: float = 0) -> tuple[float, float]:
    values = [_number(node.get(prop, str(default)), prop)]
    for animation in node.findall('animate'):
        if animation.get('property') == prop:
            values.extend(_number(k.attrib['value'], prop) for k in animation)
    return min(values), max(values)


def _transform(box: layout.Box, node: ET.Element) -> layout.Box:
    # Independent interval arithmetic deliberately overestimates correlated
    # tracks. A varying rotation uses a full disc, including interior extrema.
    ax, ay = _range(node, 'anchorX'), _range(node, 'anchorY')
    xs: tuple[float, ...] = (box.x0 - ax[1], box.x1 - ax[0])
    ys: tuple[float, ...] = (box.y0 - ay[1], box.y1 - ay[0])
    xs = tuple(x * s for x in xs for s in _range(node, 'scaleX', 1))
    ys = tuple(y * s for y in ys for s in _range(node, 'scaleY', 1))
    low, high = _range(node, 'rotation')
    if low == high:
        angle = math.radians(low)
        cos, sin = math.cos(angle), math.sin(angle)
        rotated = layout.Box.around((cos * x - sin * y, sin * x + cos * y) for x in xs for y in ys)
    else:
        radius = max(math.hypot(x, y) for x in xs for y in ys)
        rotated = layout.Box(-radius, -radius, radius, radius)
    x, y = _range(node, 'x'), _range(node, 'y')
    return layout.Box(rotated.x0 + x[0], rotated.y0 + y[0], rotated.x1 + x[1], rotated.y1 + y[1])


def _envelope(node: ET.Element, texts: dict[str, layout.Box]) -> layout.Box | None:
    if node.tag == 'layer':
        box = texts[node.attrib['asset']]
    elif node.tag == 'shape':
        size = tuple(_number(node.get(a, '0'), a) for a in ('width', 'height'))
        if node.get('shape') != 'path' and (
            min(size) <= 0 or 'width' not in node.attrib or 'height' not in node.attrib
        ):
            raise _fail('shape', node.get('id'), 'explicit positive shape dimensions')
        box = layout.shape_bounds(node, (size[0], size[1]))
    else:
        children = [_envelope(child, texts) for child in node if child.tag in ('group', 'shape', 'layer')]
        boxes = [box for box in children if box is not None]
        if not boxes:
            return None
        box = layout.Box(
            min(b.x0 for b in boxes), min(b.y0 for b in boxes), max(b.x1 for b in boxes), max(b.y1 for b in boxes)
        )
    return _transform(box, node)


def prepare_vector(binding: c.AssetBinding, xml: bytes, *, fonts: tuple[c.VectorFont, ...] = ()) -> c.PreparedVector:
    if type(binding) is not c.AssetBinding or binding.backend != 'vector':
        raise _fail('binding', None, 'a vector AssetBinding')
    binding.__post_init__()
    # Preparation verifies the pin independently; preflight also checks the
    # selected scene style. Host payload provenance is not inferred from XML.
    from . import parts
    from ._composition_review import check_source

    try:
        if binding.candidate is None:
            _binding(binding, parts.get(binding.part).style)
        else:
            _binding(binding, binding.candidate.style, purpose='candidate-review')
        from . import _composition_forms as forms

        resource_bytes = text_assets.validate(fonts) + forms.size(binding.forms)
        if type(xml) is not bytes or 8 * (len(xml) + resource_bytes) > binding.memory_bytes:
            raise _fail(
                'memory_bytes',
                binding.memory_bytes,
                'memory for XML, fonts, licenses and form fields with eightfold working allowance',
            )
        root = _tree(binding, xml)
        digest = c.vector_source_digest(c.VectorSource(binding.id, xml, fonts), forms=binding.forms)
        check_source(binding, digest)
        if root.tag != 'scene':
            raise _fail('scene', root.tag, 'a scene document')
        paints = {n.get('id') for n in root.findall('./paints/*')}
        parents = {child: parent for parent in root.iter() for child in parent}
        for node in root.iter():
            if node.tag not in _ALLOWED or set(node.attrib) - _ALLOWED[node.tag]:
                raise c._fail(
                    'payload.' + node.tag,
                    tuple(node.attrib),
                    'supported closed vector features',
                    'composition.capability',
                )
            if node.text and node.text.strip():
                raise _fail(node.tag, None, 'no embedded expressions or text content')
            if node.tag in ('group', 'shape', 'layer'):
                animations = [n.get('property') for n in node.findall('animate')]
                if len(set(animations)) != len(animations):
                    raise _fail('animate.property', animations, 'one track per property')
                for name in _TRANSFORM | {'start', 'end', 'timeOffset', 'timeScale'}:
                    if name in node.attrib:
                        _number(node.attrib[name], name)
                if binding.duration is None and any(
                    name in node.attrib and (name == 'end' or float(node.attrib[name]) != default)
                    for name, default in (('start', 0), ('end', 0), ('timeOffset', 0), ('timeScale', 1))
                ):
                    raise _fail('duration', None, 'a source duration for timed content')
            if node.tag == 'animate':
                if parents[node].tag not in ('group', 'shape', 'layer'):
                    raise _fail('animate', parents[node].tag, 'animation owned by a timed drawing node')
                _animation(node, binding)
            if node.tag in ('linearGradient', 'radialGradient', 'stop'):
                for name in ('x1', 'y1', 'x2', 'y2', 'cx', 'cy', 'r', 'fx', 'fy', 'offset', 'opacity'):
                    if name in node.attrib:
                        _number(node.attrib[name], name)
            for name in ('fill', 'stroke', 'color'):
                value = node.get(name, '')
                if value.startswith('url('):
                    match = _PAINT.fullmatch(value)
                    if match is None or match[1] not in paints:
                        raise _fail(name, value, 'a local gradient reference')
        scene = read(xml)
        if not isinstance(scene, Scene):
            raise _fail('scene', root.tag, 'a scene document')
        errors = scene.check(schema=True)
        if errors:
            raise _fail('schema', [str(e) for e in errors[:8]], 'a schema-valid vector source')
        project, content = root.find('project'), root.find('composition')
        if project is None or content is None:
            raise _fail('scene', None, 'a project and composition')
        if binding.duration is not None and _number(project.get('duration', '0'), 'duration') < binding.duration:
            raise _fail('duration', binding.duration, 'a duration within the source project')
        forms.verify(root, binding)
        texts = text_assets.verify(root, fonts)
        box = _envelope(content, texts)
        if box is None:
            raise _fail('composition', None, 'at least one bounded drawing')
        measured = c.Bounds((box.x0, box.y0, 0), (box.x1, box.y1, 0))
        if any(a > b + 1e-9 for a, b in zip(binding.bounds.minimum, measured.minimum, strict=True)) or any(
            a < b - 1e-9 for a, b in zip(binding.bounds.maximum, measured.maximum, strict=True)
        ):
            raise _fail('bounds', measured, 'a complete animation envelope inside the declared source bounds')
        return c.PreparedVector(binding, xml, digest, measured, len(list(root.iter())), fonts)
    except c.CompositionError:
        raise
    except (SrstudioError, ValueError, OverflowError) as error:
        raise _fail('source', None, 'a supported, valid bounded drawing') from error
