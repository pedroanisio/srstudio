"""Closed, size-bounded JSON for composition workers; never pickle executable objects."""

from __future__ import annotations

import base64
import binascii
import json
from dataclasses import asdict
from typing import TypeVar

from . import composition as c
from ._composition_parse import _bounded_tree, _record
from ._composition_vector import MAX_XML_BYTES
from .errors import SrstudioError, diagnostic

SCHEMA = 'srstudio.composition-worker/1.0.0'
MAX_WIRE_BYTES = 16 * 1024**2
T = TypeVar('T', bound=c._Record)


def fail(actual: object, expected: object) -> c.CompositionError:
    return c._fail('worker.protocol', actual, expected, 'composition.worker.protocol')


def fields(value: object, names: set[str]) -> dict:
    if type(value) is not dict or set(value) != names:
        raise fail(None, 'exact worker fields: ' + ', '.join(sorted(names)))
    return value


def _unique(items: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in items:
        if key in result:
            raise fail(key, 'a field declared once')
        result[key] = value
    return result


def loads(raw: bytes) -> dict:
    if type(raw) is not bytes or len(raw) > MAX_WIRE_BYTES:
        raise fail(None, f'at most {MAX_WIRE_BYTES} encoded bytes')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique)
    except (ValueError, RecursionError, UnicodeError) as error:
        if isinstance(error, c.CompositionError):
            raise
        raise fail(None, 'bounded UTF-8 JSON') from error
    if type(value) is not dict or value.get('schema') != SCHEMA:
        raise fail(None, SCHEMA)
    return value


def dumps(value: dict) -> bytes:
    result = json.dumps(value, separators=(',', ':'), allow_nan=False).encode('utf-8')
    if len(result) > MAX_WIRE_BYTES:
        raise fail(len(result), f'at most {MAX_WIRE_BYTES} encoded bytes')
    return result


def record(kind: type[T], value: object) -> T:
    _bounded_tree(value, set(), [0, 0])
    return _record(kind, value, 'worker.' + kind.__name__)


def xml_encode(value: bytes) -> str:
    if type(value) is not bytes or len(value) > MAX_XML_BYTES:
        raise fail(None, 'immutable XML bytes within the eight MiB cap')
    return base64.b64encode(value).decode('ascii')


def xml_decode(value: object) -> bytes:
    if type(value) is not str or len(value) > 4 * ((MAX_XML_BYTES + 2) // 3):
        raise fail(None, 'bounded base64 XML')
    try:
        result = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as error:
        raise fail(None, 'valid base64 XML') from error
    if len(result) > MAX_XML_BYTES:
        raise fail(len(result), 'at most eight MiB of XML')
    return result


def prepared_metadata(asset: c.PreparedVector) -> dict:
    if (
        type(asset.bounds) is not c.Bounds
        or type(asset.digest) is not str
        or len(asset.digest) != 64
        or type(asset.nodes) is not int
        or not 1 <= asset.nodes <= asset.binding.nodes
    ):
        raise fail(None, 'typed immutable prepared-payload evidence')
    asset.bounds.__post_init__()
    return {'digest': asset.digest, 'bounds': asdict(asset.bounds), 'nodes': asset.nodes}


def prepared(binding: c.AssetBinding, xml: bytes, value: object) -> c.PreparedVector:
    data = fields(value, {'digest', 'bounds', 'nodes'})
    if (
        type(data['digest']) is not str
        or len(data['digest']) != 64
        or type(data['nodes']) is not int
        or not 1 <= data['nodes'] <= binding.nodes
    ):
        raise fail(None, 'a SHA-256 identity and bounded node count')
    return c.PreparedVector(binding, xml, data['digest'], record(c.Bounds, data['bounds']), data['nodes'])


def read_diagnostic(value: object) -> dict:
    data = fields(value, {'schema', 'code', 'path', 'message', 'actual', 'expected', 'remedy', 'context', 'residual'})
    _bounded_tree(data, set(), [0, 0])
    if data['schema'] != 'srstudio.diagnostic/1.0.0' or any(
        type(data[name]) is not str for name in ('code', 'message')
    ):
        raise fail(None, 'a typed SDK diagnostic')
    if any(data[name] is not None and type(data[name]) is not str for name in ('path', 'remedy')):
        raise fail(None, 'optional diagnostic path and remedy strings')
    if type(data['context']) is not dict:
        raise fail(None, 'diagnostic context fields')
    return data


def cause_encode(error: BaseException | None, depth: int = 0) -> dict | None:
    if error is None or depth >= 4:
        return None
    return {
        'type': type(error).__module__ + '.' + type(error).__name__,
        'diagnostic': diagnostic(error),
        'cause': cause_encode(error.__cause__, depth + 1),
    }


def cause_decode(value: object, depth: int = 0) -> SrstudioError | None:
    if value is None:
        return None
    if depth >= 4:
        raise fail(None, 'at most four underlying failures')
    data = fields(value, {'type', 'diagnostic', 'cause'})
    if type(data['type']) is not str or len(data['type']) > 256:
        raise fail(None, 'a bounded diagnostic type name')
    details = read_diagnostic(data['diagnostic'])
    # Literal imports only: a reply cannot name code for the host to import.
    from . import layout, parts
    from .head_motion import HeadMotionError
    from .limbs.errors import LimbError
    from .plates import PlateError

    classes = (
        parts.PartError,
        parts.UnknownVersionError,
        parts.NotApprovedError,
        parts.UnverifiedBuilderError,
        layout.PathError,
        layout.RegionError,
        layout.LayoutError,
        HeadMotionError,
        LimbError,
        PlateError,
    )
    known = {cls.__module__ + '.' + cls.__name__: cls for cls in classes}
    cls = known.get(data['type'], SrstudioError)
    error = cls(details['message'])
    error._diagnostic_details.update({key: details[key] for key in ('code', 'path', 'actual', 'expected', 'remedy')})
    if isinstance(error, LimbError):
        error.code = details['code']
        error.context = details['context']
        error.residual = details['residual']
    error.__cause__ = cause_decode(data['cause'], depth + 1)
    return error
