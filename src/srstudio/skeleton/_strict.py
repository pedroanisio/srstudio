"""Strict reading shared by the joint table and the profile: one JSON object, closed fields, exact types."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

from .. import checks
from ..limbs.math3d import Vec3
from ._errors import SkeletonSchemaError

MAX_RECORD_BYTES = 1_000_000  # the joint table is about 30 kB; a profile is a few kB
UNBOUNDED = 1e6  # for a number whose real bound the caller checks itself
SEMVER = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    found: dict[str, Any] = {}
    for key, value in pairs:
        if key in found:
            raise SkeletonSchemaError("a key is repeated", path=key, actual=key, expected="unique keys")
        found[key] = value
    return found


def _constant(name: str) -> float:
    raise SkeletonSchemaError("JSON allows no NaN or Infinity", path="$", actual=name, expected="finite numbers")


def read(text: str, what: str) -> dict[str, Any]:
    """One strict JSON object: no repeated key, no NaN or Infinity, at most MAX_RECORD_BYTES."""
    if not isinstance(text, str) or len(text.encode()) > MAX_RECORD_BYTES:
        raise SkeletonSchemaError(f"a {what} is JSON text of at most {MAX_RECORD_BYTES} bytes", path="$")
    try:
        data = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
    except json.JSONDecodeError as exc:
        raise SkeletonSchemaError(f"not JSON: {exc.msg}", path="$", actual=exc.pos, expected="JSON") from exc
    if not isinstance(data, dict):
        raise SkeletonSchemaError(f"a {what} is one JSON object", path="$", actual=type(data).__name__)
    return data


def fields(value: object, path: str, allowed: tuple[str, ...], required: tuple[str, ...]) -> Mapping[str, Any]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise SkeletonSchemaError("expected an object", path=path, actual=type(value).__name__, expected="object")
    unknown = sorted(set(value) - set(allowed))
    missing = sorted(set(required) - set(value))
    if unknown or missing:
        raise SkeletonSchemaError(
            f"unknown fields {unknown}, missing fields {missing}",
            path=path,
            actual=sorted(value),
            expected={"allowed": list(allowed), "required": list(required)},
        )
    return value


def number(value: object, path: str, low: float, high: float) -> float:
    if not checks.number(value) or not low <= value <= high:
        raise SkeletonSchemaError(
            f"expected a finite number in {low}..{high}", path=path, actual=value, expected=[low, high]
        )
    return float(value)


def text(value: object, path: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise SkeletonSchemaError(
            "expected a string of the stated pattern", path=path, actual=value, expected=pattern.pattern
        )
    return value


def items(value: object, path: str, low: int, high: int) -> list[Any]:
    if not isinstance(value, list) or not low <= len(value) <= high:
        raise SkeletonSchemaError(
            f"expected an array of {low}..{high} items", path=path, actual=type(value).__name__, expected=[low, high]
        )
    return value


def vector(value: object, path: str, bound: float) -> Vec3:
    parts = items(value, path, 3, 3)
    return Vec3(*(number(v, f"{path}[{i}]", -bound, bound) for i, v in enumerate(parts)))


def schema(value: object, path: str, name: str, major: int) -> str:
    if not isinstance(value, str) or not value.startswith(name + "/"):
        raise SkeletonSchemaError("not this schema", path=path, actual=value, expected=f"{name}/{major}.x.y")
    version = SEMVER.fullmatch(value[len(name) + 1 :])
    if version is None or int(version.group(1)) != major:
        raise SkeletonSchemaError("a schema major this reader does not know", path=path, actual=value, expected=major)
    return value
