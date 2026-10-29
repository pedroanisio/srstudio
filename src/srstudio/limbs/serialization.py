"""Strict versioned JSON motion documents. Unknown fields and type coercions are rejected before use."""

from __future__ import annotations

import json
import os
import tempfile
import types
from dataclasses import MISSING, asdict, fields, is_dataclass
from pathlib import Path
from typing import Any, Union, get_args, get_origin, get_type_hints

from .errors import LimbError
from .math3d import number
from .motion import Motion

SCHEMA = "srstudio.limbs/1.0.0"
MAX_BYTES = 5 * 1024 * 1024
MAX_ITEMS = 100000


def _decode(kind: Any, value: object, where: str, budget: list[int], depth: int = 0) -> Any:
    budget[0] -= 1
    if budget[0] < 0 or depth > 32:
        raise LimbError(f"{where}: motion document exceeds its decoding bound", code="budget")
    origin, args = get_origin(kind), get_args(kind)
    if origin in (types.UnionType, Union):
        for candidate in args:
            try:
                return _decode(candidate, value, where, budget, depth + 1)
            except LimbError as error:
                if error.code == "budget":
                    raise
        raise LimbError(f"{where}: value does not match the declared union type")
    if kind is type(None):
        if value is not None:
            raise LimbError(f"{where}: expected null")
        return None
    if kind is float:
        return number(value, where)
    if kind in (str, int, bool):
        if type(value) is not kind:
            raise LimbError(f"{where}: expected {kind.__name__}, got {type(value).__name__}")
        return value
    if origin is tuple:
        if not isinstance(value, (list, tuple)) or len(value) > 10000:
            raise LimbError(
                f"{where}: expected an array within the 10000 item bound",
                code="budget" if isinstance(value, (list, tuple)) else "invalid",
            )
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(_decode(args[0], item, f"{where}[{i}]", budget, depth + 1) for i, item in enumerate(value))
        if len(value) != len(args):
            raise LimbError(f"{where}: expected {len(args)} array elements")
        return tuple(
            _decode(t, item, f"{where}[{i}]", budget, depth + 1)
            for i, (t, item) in enumerate(zip(args, value, strict=True))
        )
    if isinstance(kind, type) and is_dataclass(kind):
        if not isinstance(value, dict):
            raise LimbError(f"{where}: expected a {kind.__name__} object")
        definitions = {f.name: f for f in fields(kind)}
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
        return kind(
            **{name: _decode(hints[name], item, f"{where}.{name}", budget, depth + 1) for name, item in value.items()}
        )
    raise LimbError(f"{where}: unsupported persisted type {kind}")


def motion_dict(motion: Motion) -> dict:
    return {"schema": SCHEMA, "generatedBy": "srstudio.limbs", "motion": asdict(motion)}


def parse_motion(data: object) -> Motion:
    if not isinstance(data, dict):
        raise LimbError("motion document must be an object")
    unknown = set(data) - {"schema", "generatedBy", "motion"}
    if unknown:
        raise LimbError(f"motion document has unknown fields {sorted(unknown)}")
    if data.get("schema") != SCHEMA:
        raise LimbError(f"motion document needs schema {SCHEMA}")
    if "generatedBy" in data and not isinstance(data["generatedBy"], str):
        raise LimbError("motion generatedBy must be a string")
    if "motion" not in data:
        raise LimbError("motion document is missing motion")
    result: Motion = _decode(Motion, data["motion"], "motion", [MAX_ITEMS])
    return result


def load_motion(path: str | Path) -> Motion:
    try:
        with Path(path).open("rb") as file:
            raw = file.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise LimbError("motion file exceeds the 5 MiB size limit", code="budget")
        data = json.loads(raw)
    except (OSError, ValueError) as error:
        if isinstance(error, LimbError):
            raise
        raise LimbError(f"cannot read motion document: {error}", code="io") from error
    return parse_motion(data)


def save_motion(motion: Motion, path: str | Path) -> Path:
    document = motion_dict(motion)
    parse_motion(document)
    data = json.dumps(document, indent=2, allow_nan=False) + "\n"
    if len(data.encode()) > MAX_BYTES:
        raise LimbError("motion file exceeds the 5 MiB size limit", code="budget")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".motion-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(data)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return path
