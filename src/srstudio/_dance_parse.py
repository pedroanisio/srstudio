"""Strict readers for the dance data: ``srstudio.dance-moves/1.0.0`` and ``srstudio.dance-routine/1.0.0``.

Text is untrusted until it parses: one JSON object of at most ``MAX_BYTES`` (no NaN or Infinity, no repeated key), no
unknown or missing field, no wrong type (a boolean is not a number, a float is not a bar), no number that is not finite,
and at most ``MAX_MOVES`` moves. The typed model then checks what the schema cannot say (ADR 0186).
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable, Mapping
from functools import cache
from importlib.resources import files
from pathlib import Path
from types import MappingProxyType
from typing import TypeVar

from ._dance_model import Contact, DanceError, Entry, Move, Pattern, Routine

__all__ = [
    "LIBRARIES",
    "MOVES_SCHEMA",
    "ROUTINE_SCHEMA",
    "DanceDataError",
    "DanceSchemaError",
    "dump_routine",
    "load_moves",
    "library",
    "load_routine",
    "moves",
    "parse_moves",
    "parse_routine",
]

MOVES_SCHEMA = "srstudio.dance-moves/1.0.0"
ROUTINE_SCHEMA = "srstudio.dance-routine/1.0.0"
MAX_BYTES = 1_000_000
MAX_MOVES = 256
_SCHEMA = re.compile(r"(srstudio\.dance-(?:moves|routine))/(\d+)\.(\d+)\.(\d+)\Z")
_T = TypeVar("_T")


class DanceDataError(DanceError):
    """Dance text that is not one strict JSON document of its schema."""


class DanceSchemaError(DanceDataError):
    """A dance document of another schema, or of a major version this reader does not read."""


def _no_constant(name: str) -> float:
    raise DanceDataError(f"{name} is not a JSON number", code="dance.json", path="$")


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    keys = [k for k, _ in pairs]
    repeated = sorted({k for k in keys if keys.count(k) > 1})
    if repeated:
        raise DanceDataError(f"a JSON object repeats the key(s) {repeated}", code="dance.json", path="$")
    return dict(pairs)


def _document(text: str | bytes, schema: str) -> dict[str, object]:
    if not isinstance(text, (str, bytes)):
        raise DanceDataError(f"dance data is JSON text, not {type(text).__name__}", path="$")
    if len(text) > MAX_BYTES:
        raise DanceDataError(f"dance data is at most {MAX_BYTES} bytes, not {len(text)}", path="$")
    if isinstance(text, bytes):
        try:
            text = text.decode("utf-8")
        except UnicodeDecodeError as error:
            raise DanceDataError(f"dance data is UTF-8 text: {error}", path="$") from None
    try:
        data = json.loads(text, parse_constant=_no_constant, object_pairs_hook=_unique)
    except (json.JSONDecodeError, RecursionError) as error:
        raise DanceDataError(f"dance data is one JSON object: {error}", code="dance.json", path="$") from None
    top = _fields(data, "$", ("schema",), ("generated_by", "moves", "track_bars", "beats_per_bar", "entries"))
    found = _SCHEMA.match(top["schema"]) if isinstance(top["schema"], str) else None
    if not found or found.group(1) != schema.split("/")[0]:
        raise DanceSchemaError(f"$.schema {top['schema']!r} is not {schema}", code="dance.schema", path="$.schema")
    if found.group(2) != schema.split("/")[1].split(".")[0]:
        raise DanceSchemaError(
            f"this reader reads {schema} and its minors, not {top['schema']}", code="dance.schema", path="$.schema"
        )
    if "generated_by" in top:
        made = _fields(top["generated_by"], "$.generated_by", ("tool", "model"))
        _text(made["tool"], "$.generated_by.tool")
        _text(made["model"], "$.generated_by.model")
    return top


def _fields(value: object, path: str, required: tuple[str, ...], optional: tuple[str, ...] = ()) -> dict[str, object]:
    if not isinstance(value, dict):
        raise DanceDataError(f"{path} is a JSON object, not {type(value).__name__}", path=path)
    unknown = sorted(set(value) - set(required) - set(optional))
    if unknown:
        raise DanceDataError(f"{path} has unknown field(s) {unknown}", code="dance.unknown", path=path, actual=unknown)
    missing = [k for k in required if k not in value]
    if missing:
        raise DanceDataError(f"{path} lacks field(s) {missing}", code="dance.missing", path=path, actual=missing)
    return value


def _list(value: object, path: str, most: int) -> list[object]:
    if not isinstance(value, list):
        raise DanceDataError(f"{path} is a JSON list, not {type(value).__name__}", path=path)
    if len(value) > most:
        raise DanceDataError(f"{path} holds at most {most} items, not {len(value)}", path=path)
    return value


def _number(value: object, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise DanceDataError(f"{path} is a finite number, not {value!r}", code="dance.type", path=path, actual=value)
    return value


def _whole(value: object, path: str) -> int:
    if type(value) is not int:
        raise DanceDataError(f"{path} is a whole number, not {value!r}", code="dance.type", path=path, actual=value)
    return value


def _text(value: object, path: str) -> str:
    if not isinstance(value, str) or len(value) > 512:
        raise DanceDataError(f"{path} is text of at most 512 characters", code="dance.type", path=path)
    return value


def _flag(value: object, path: str) -> bool:
    if type(value) is not bool:
        raise DanceDataError(f"{path} is true or false, not {value!r}", code="dance.type", path=path, actual=value)
    return value


def _pairs(value: object, path: str, most: int) -> tuple[tuple[str, float], ...]:
    data = _fields(value, path, (), tuple(value) if isinstance(value, dict) else ())
    if len(data) > most:
        raise DanceDataError(f"{path} holds at most {most} entries", path=path)
    return tuple((k, _number(v, f"{path}.{k}")) for k, v in data.items())


def _built(path: str, build: Callable[[], _T]) -> _T:
    try:
        return build()
    except DanceError as error:
        raise type(error)(f"{path}: {error}", code="dance.value", path=path) from error


_PATTERN = ("target", "amplitude", "cycles", "per", "phase", "waveform", "snap")
_NUMERIC = frozenset({"amplitude", "cycles", "phase", "snap", "swing", "intensity", "bias"})


def _pattern(value: object, path: str) -> Pattern:
    p = _fields(value, path, _PATTERN, ("swing", "intensity", "bias"))
    numbers = {k: _number(v, f"{path}.{k}") for k, v in p.items() if k in _NUMERIC}
    target, per, waveform = (_text(p[k], f"{path}.{k}") for k in ("target", "per", "waveform"))
    return _built(path, lambda: Pattern(target=target, per=per, waveform=waveform, **numbers))


def _contact(value: object, path: str) -> Contact:
    c = _fields(value, path, ("foot", "from", "to"))
    foot = _text(c["foot"], f"{path}.foot")
    start, end = _number(c["from"], f"{path}.from"), _number(c["to"], f"{path}.to")
    return _built(path, lambda: Contact(foot, start, end))


def _move(value: object, path: str) -> Move:
    m = _fields(value, path, ("name", "support", "patterns"), ("description", "loop_beats", "lags", "contacts"))
    name, support = _text(m["name"], f"{path}.name"), _text(m["support"], f"{path}.support")
    description = _text(m.get("description", ""), f"{path}.description")
    patterns = tuple(
        _pattern(p, f"{path}.patterns[{i}]") for i, p in enumerate(_list(m["patterns"], f"{path}.patterns", 128))
    )
    loop = _number(m.get("loop_beats", 1.0), f"{path}.loop_beats")
    lags = _pairs(m.get("lags", {}), f"{path}.lags", 16)
    contacts = tuple(
        _contact(c, f"{path}.contacts[{i}]") for i, c in enumerate(_list(m.get("contacts", []), f"{path}.contacts", 16))
    )
    return _built(path, lambda: Move(name, support, patterns, loop, lags, contacts, description))


def parse_moves(text: str | bytes) -> Mapping[str, Move]:
    """The moves of a ``srstudio.dance-moves/1.x`` document, by name in file order."""
    top = _document(text, MOVES_SCHEMA)
    _fields(top, "$", ("schema", "moves"), ("generated_by",))
    out: dict[str, Move] = {}
    for i, item in enumerate(_list(top["moves"], "$.moves", MAX_MOVES)):
        move = _move(item, f"$.moves[{i}]")
        if move.name in out:
            raise DanceDataError(f"$.moves[{i}]: move {move.name!r} is named twice", path=f"$.moves[{i}].name")
        out[move.name] = move
    if not out:
        raise DanceDataError("$.moves holds at least one move", path="$.moves")
    return MappingProxyType(out)


def _read(path: str | Path) -> bytes:
    try:
        with open(path, "rb") as handle:
            return handle.read(MAX_BYTES + 1)
    except OSError as error:
        raise DanceDataError(f"cannot read dance data {path}: {error}", path=str(path)) from None


def load_moves(path: str | Path) -> Mapping[str, Move]:
    return parse_moves(_read(path))


@cache
def moves() -> Mapping[str, Move]:
    """The shipped presets, from ``assets/dance/moves.json``."""
    return library("moves")


LIBRARY_NAME = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
LIBRARIES = ("moves", "fein")


@cache
def library(name: str) -> Mapping[str, Move]:
    """A shipped move library by name, from ``assets/dance/<name>.json``: ``moves`` (the presets) or ``fein`` (the
    moves transcribed from the FE!N choreography, ADR 0212). An unknown name is refused before any file is read."""
    if not isinstance(name, str) or not LIBRARY_NAME.match(name) or name not in LIBRARIES:
        raise DanceDataError(f"library {name!r} is one of {LIBRARIES}", path="library", actual=name, expected=LIBRARIES)
    return parse_moves(files("srstudio").joinpath(f"assets/dance/{name}.json").read_bytes())


def _entry(value: object, path: str, library: Mapping[str, Move]) -> Entry:
    e = _fields(value, path, ("bars", "move"), ("intensity", "mirror", "transition_beats", "expression", "hold"))
    bars = _list(e["bars"], f"{path}.bars", 2)
    if len(bars) != 2:
        raise DanceDataError(f"{path}.bars is [start, end]", path=f"{path}.bars")
    start, end = _whole(bars[0], f"{path}.bars[0]"), _whole(bars[1], f"{path}.bars[1]")
    name = _text(e["move"], f"{path}.move")
    if name not in library:
        raise DanceDataError(f"{path}.move {name!r} is not a known move", code="dance.move", path=f"{path}.move")
    intensity = _number(e.get("intensity", 1.0), f"{path}.intensity")
    mirror = _flag(e.get("mirror", False), f"{path}.mirror")
    transition = _number(e.get("transition_beats", 0.0), f"{path}.transition_beats")
    expression = _text(e["expression"], f"{path}.expression") if "expression" in e else None
    hold = _pairs(e.get("hold", {}), f"{path}.hold", 64)
    return _built(path, lambda: Entry(start, end, library[name], intensity, mirror, transition, expression, hold))


def parse_routine(text: str | bytes, library: Mapping[str, Move]) -> Routine:
    """A ``srstudio.dance-routine/1.x`` document, its moves looked up by name in ``library``."""
    top = _document(text, ROUTINE_SCHEMA)
    _fields(top, "$", ("schema", "track_bars", "entries"), ("generated_by", "beats_per_bar"))
    bars = _whole(top["track_bars"], "$.track_bars")
    per_bar = _whole(top.get("beats_per_bar", 4), "$.beats_per_bar")
    items = _list(top["entries"], "$.entries", 512)
    entries = tuple(_entry(item, f"$.entries[{i}]", library) for i, item in enumerate(items))
    return _built("$", lambda: Routine(bars, entries, per_bar))


def load_routine(path: str | Path, library: Mapping[str, Move]) -> Routine:
    return parse_routine(_read(path), library)


def dump_routine(routine: Routine) -> str:
    """``routine`` as a ``srstudio.dance-routine/1.0.0`` document, its moves by name: :func:`parse_routine` on the
    same library reads it back equal. A field at its default is left out."""
    if not isinstance(routine, Routine):
        raise DanceDataError(f"only a Routine is written, not {type(routine).__name__}", path="$")
    entries = []
    for e in routine.entries:
        entry: dict[str, object] = {"bars": [e.start_bar, e.end_bar], "move": e.move.name}
        if e.intensity != 1.0:
            entry["intensity"] = e.intensity
        if e.mirror:
            entry["mirror"] = True
        if e.transition_beats:
            entry["transition_beats"] = e.transition_beats
        if e.expression is not None:
            entry["expression"] = e.expression
        if e.hold:
            entry["hold"] = dict(e.hold)
        entries.append(entry)
    document = {
        "schema": ROUTINE_SCHEMA,
        "track_bars": routine.track_bars,
        "beats_per_bar": routine.beats_per_bar,
        "entries": entries,
    }
    return json.dumps(document, indent=2, allow_nan=False) + "\n"
