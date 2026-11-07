"""Strict versioned JSON motion documents. Unknown fields and type coercions are rejected before use."""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
import types
from dataclasses import MISSING, asdict, fields, is_dataclass
from pathlib import Path
from typing import Any, Union, get_args, get_origin, get_type_hints

from .errors import LimbError
from .math3d import Quaternion, number
from .motion import Action, Motion, MotionStyle

SCHEMA = "srstudio.limbs/1.4.0"
JOIN_SCHEMA = "srstudio.limbs/1.3.0"
TRANSFORM_SCHEMA = "srstudio.limbs/1.2.0"
ANATOMY_SCHEMA = "srstudio.limbs/1.1.0"
LEGACY_SCHEMA = "srstudio.limbs/1.0.0"
MAX_BYTES = 5 * 1024 * 1024
MAX_ITEMS = 100000
MAX_DEPTH = 64
_STRUCTURE = re.compile(r'"(?:[^"\\]|\\.)*"?|[\[\]{}]', re.DOTALL)


def _decode(
    kind: Any,
    value: object,
    where: str,
    budget: list[int],
    depth: int = 0,
    *,
    solved: bool = False,
    legacy_envelope: bool = False,
) -> Any:
    budget[0] -= 1
    if budget[0] < 0 or depth > 32:
        raise LimbError(f"{where}: motion document exceeds its decoding bound", code="budget")
    origin, args = get_origin(kind), get_args(kind)
    if origin in (types.UnionType, Union):
        # Optional fields have one real shape: a failed nested decode is actionable, not a union mismatch.
        if type(None) in args:
            if value is None:
                return None
            non_null = tuple(candidate for candidate in args if candidate is not type(None))
            if len(non_null) == 1:
                return _decode(
                    non_null[0], value, where, budget, depth + 1, solved=solved, legacy_envelope=legacy_envelope
                )
        for candidate in args:
            try:
                return _decode(
                    candidate, value, where, budget, depth + 1, solved=solved, legacy_envelope=legacy_envelope
                )
            except LimbError as error:
                if error.code == "budget":
                    raise
        raise LimbError(f"{where}: value does not match the declared union type")
    if kind is type(None):
        if value is not None:
            raise LimbError(f"{where}: expected null")
        return None
    if kind is float:
        try:
            return number(value, where)
        except LimbError as error:
            raise LimbError(
                str(error),
                path=where,
                actual=value,
                expected='a finite number excluding booleans',
                remedy='Replace this field with a finite numeric value.',
            ) from error
    if kind in (str, int, bool):
        if type(value) is not kind:
            raise LimbError(
                f"{where}: expected {kind.__name__}, got {type(value).__name__}",
                path=where,
                actual=value,
                expected=kind.__name__,
                remedy='Use the declared JSON field type.',
            )
        return value
    if origin is tuple:
        if not isinstance(value, (list, tuple)) or len(value) > 10000:
            raise LimbError(
                f"{where}: expected an array within the 10000 item bound",
                code="budget" if isinstance(value, (list, tuple)) else "invalid",
            )
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(
                _decode(
                    args[0], item, f"{where}[{i}]", budget, depth + 1, solved=solved, legacy_envelope=legacy_envelope
                )
                for i, item in enumerate(value)
            )
        if len(value) != len(args):
            raise LimbError(f"{where}: expected {len(args)} array elements")
        return tuple(
            _decode(t, item, f"{where}[{i}]", budget, depth + 1, solved=solved, legacy_envelope=legacy_envelope)
            for i, (t, item) in enumerate(zip(args, value, strict=True))
        )
    if isinstance(kind, type) and is_dataclass(kind):
        if not isinstance(value, dict):
            raise LimbError(f"{where}: expected a {kind.__name__} object")
        definitions = {f.name: f for f in fields(kind)}
        if len(value) > len(definitions) or any(not isinstance(key, str) for key in value):
            raise LimbError(f"{where}: too many or unknown object fields")
        unknown = set(value) - definitions.keys()
        if unknown:
            raise LimbError(f"{where}: unknown fields {sorted(unknown)}")
        missing = [
            name
            for name, f in definitions.items()
            if f.default is MISSING and f.default_factory is MISSING and name not in value
        ]
        if missing:
            raise LimbError(f"{where}: missing required fields {missing}")
        hints = get_type_hints(kind)
        decoded = {
            name: _decode(
                hints[name], item, f"{where}.{name}", budget, depth + 1, solved=solved, legacy_envelope=legacy_envelope
            )
            for name, item in value.items()
        }
        if kind is MotionStyle and legacy_envelope:
            if 'envelope' in value:
                raise LimbError(f'{where}.envelope requires motion schema srstudio.limbs/1.4.0')
            decoded['envelope'] = 'legacy'
        if kind is Action and legacy_envelope and 'style' not in decoded:
            decoded['style'] = MotionStyle(envelope='legacy')
        try:
            result = kind(**decoded)
            if solved and kind is Quaternion:
                components = {name: decoded.get(name, definitions[name].default) for name in ('w', 'x', 'y', 'z')}
                if abs(math.hypot(*components.values()) - 1) > 1e-8:
                    raise LimbError('solved rotations must already be unit quaternions')
                # Do not renormalize already solved geometry on each save/load cycle.
                for name, component in components.items():
                    object.__setattr__(result, name, component)
            return result
        except LimbError as error:
            raise LimbError(
                f'{where}: {error.message}', code=error.code, residual=error.residual, context=error.context
            ) from error
    raise LimbError(f"{where}: unsupported persisted type {kind}")


def motion_dict(motion: Motion) -> dict:
    from ._motion_keyed import _KeyedMotion, document

    if isinstance(motion, _KeyedMotion):
        return document(motion)
    # Decoding through the declared field types writes 0 for a float field as 0.0, so a saved file reloads and
    # saves again byte for byte.
    typed: Motion = _decode(Motion, asdict(motion), "motion", [MAX_ITEMS])
    payload = asdict(typed)
    schema = SCHEMA
    if typed.actions and all(a.style.envelope == 'legacy' for a in typed.actions):
        schema = JOIN_SCHEMA
        for action in payload['actions']:
            del action['style']['envelope']

    def json_data(value):
        if isinstance(value, dict):
            return {key: json_data(child) for key, child in value.items()}
        if isinstance(value, tuple):
            return [json_data(child) for child in value]
        return value

    return {"schema": schema, "generatedBy": "srstudio.limbs", "motion": json_data(payload)}


def parse_motion(data: object) -> Motion:
    from ._motion_keyed import MAX_ITEMS as KEYED_ITEMS
    from ._motion_keyed import SCHEMA as KEYED_SCHEMA
    from ._motion_keyed import _KeyedMotion

    if not isinstance(data, dict):
        raise LimbError("motion document must be an object")
    if len(data) > 3 or any(not isinstance(key, str) for key in data):
        raise LimbError("motion document has too many or unknown object fields")
    unknown = set(data) - {"schema", "generatedBy", "motion"}
    if unknown:
        raise LimbError(f"motion document has unknown fields {sorted(unknown)}")
    if data.get("schema") not in (SCHEMA, JOIN_SCHEMA, TRANSFORM_SCHEMA, ANATOMY_SCHEMA, LEGACY_SCHEMA, KEYED_SCHEMA):
        raise LimbError(f"motion document needs schema {SCHEMA}")
    if "generatedBy" in data and not isinstance(data["generatedBy"], str):
        raise LimbError("motion generatedBy must be a string")
    if "motion" not in data:
        raise LimbError("motion document is missing motion")
    if data['schema'] == KEYED_SCHEMA:
        if not isinstance(data['motion'], dict) or set(data['motion']) != {'arm', 'hand', 'played', 'fps'}:
            raise LimbError('keyed motion requires exactly arm, hand, played and fps')
        return _decode(_KeyedMotion, data['motion'], 'motion', [KEYED_ITEMS], solved=True)
    result: Motion = _decode(Motion, data["motion"], "motion", [MAX_ITEMS], legacy_envelope=data["schema"] != SCHEMA)
    if data["schema"] == LEGACY_SCHEMA and any("bend_axis" in digit for digit in data["motion"]["hand"]["digits"]):
        raise LimbError("custom bend axes require motion schema srstudio.limbs/1.1.0")
    if data['schema'] in (ANATOMY_SCHEMA, LEGACY_SCHEMA):
        tracks = [data['motion'].get('root', {}), *(c['target'] for c in data['motion'].get('contacts', []))]
        if any(
            'interpolation' in track or any('velocity' in k or 'angular_velocity' in k for k in track.get('keys', []))
            for track in tracks
        ):
            raise LimbError('transform interpolation and velocities require motion schema srstudio.limbs/1.2.0')
    if data['schema'] not in (SCHEMA, JOIN_SCHEMA) and 'joins' in data['motion']:
        raise LimbError('action joins require motion schema srstudio.limbs/1.3.0')
    return result


def _nesting(text: str) -> None:
    """Bound array/object nesting before parsing; the standard parser recurses once per level."""
    depth = 0
    for token in _STRUCTURE.finditer(text):
        symbol = token.group()
        if symbol in "[{":
            depth += 1
            if depth > MAX_DEPTH:
                raise LimbError(f"document exceeds the {MAX_DEPTH}-level nesting bound", code="budget")
        elif symbol in "]}":
            depth -= 1


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise LimbError(f"document repeats the object key {key[:128]!r}; duplicate keys are ambiguous")
        result[key] = value
    return result


def read_document(path: str | Path, kind: str = "motion") -> object:
    """Read one bounded UTF-8 JSON document: size and nesting are checked before parsing, duplicate keys refused."""
    try:
        with Path(path).open("rb") as file:
            raw = file.read(MAX_BYTES + 1)
    except OSError as error:
        raise LimbError(f"cannot read {kind} document: {error}", code="io") from error
    if len(raw) > MAX_BYTES:
        raise LimbError(f"{kind} file exceeds the 5 MiB size limit", code="budget")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise LimbError(f"{kind} document is not UTF-8: {error}") from error
    _nesting(text)
    try:
        return json.loads(text, object_pairs_hook=_unique)
    except LimbError:
        raise
    except ValueError as error:
        raise LimbError(f"cannot read {kind} document: {error}", code="io") from error


def load_motion(path: str | Path) -> Motion:
    return parse_motion(read_document(path))


def save_motion(motion: Motion, path: str | Path) -> Path:
    document = motion_dict(motion)
    parse_motion(document)
    data = json.dumps(document, indent=2, allow_nan=False) + "\n"
    if len(data.encode()) > MAX_BYTES:
        raise LimbError("motion file exceeds the 5 MiB size limit", code="budget")
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, temporary = tempfile.mkstemp(prefix=".motion-", suffix=".json", dir=path.parent)
    except OSError as error:
        raise LimbError(f"cannot write motion document: {error}", code="io") from error
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(data)
        os.replace(temporary, path)
    except BaseException as error:
        Path(temporary).unlink(missing_ok=True)
        if isinstance(error, OSError):
            raise LimbError(f"cannot write motion document: {error}", code="io") from error
        raise
    return path
