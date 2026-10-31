"""The lock on the cast bible: a persona changes only with a new version, and a new version says why (ADR 0069).

``bible/lock.json`` holds a digest of every record of ``cast.json`` and ``relationships.json`` for one version. Editing
a character, pair, place, rule or clash without raising the version, adding a record under a patch version, or
raising the version without a ``CHANGELOG.md`` section is refused. ``srstudio bible lock`` rewrites the lock under the
same rules, so a drifting persona cannot be locked in by accident. Plain code, no model.

The lock stops a silent edit. It does not stop someone who edits ``lock.json`` by hand; that edit is in the diff a
reviewer reads.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from . import bible
from .bible import SEMVER, BibleError

__all__ = ["LOCK", "LockError", "check", "digests", "problems", "write"]

LOCK = "lock.json"
SCHEMA = "1.0.0"
DIGEST = re.compile(r"[0-9a-f]{64}")


class LockError(BibleError):
    """The bible and its lock disagree, or the lock cannot be read or written."""


def _digest(record: Any) -> str:
    text = json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _keyed(records: Any, label: str, key: str, where: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for i, record in enumerate(records if isinstance(records, list) else []):
        name = record.get(key) if isinstance(record, dict) else None
        if not isinstance(name, str) or not name:
            raise LockError(f"{where}[{i}] has no {key}, so it cannot be locked")
        out[f"{label}:{name}"] = record
    return out


def digests(folder: Path) -> tuple[str, dict[str, str]]:
    """The bible's version and a digest per record, read from the two files without the loader's other rules."""
    cast, pairs = bible.documents(folder)
    records: dict[str, Any] = {"roles": cast.get("roles")}
    records.update(_keyed(cast.get("characters"), "character", "slug", "cast.json.characters"))
    records.update(_keyed(cast.get("places"), "place", "slug", "cast.json.places"))
    records.update(_keyed(cast.get("rules"), "rule", "id", "cast.json.rules"))
    records.update(_keyed(cast.get("clashes"), "clash", "id", "cast.json.clashes"))
    for i, pair in enumerate(pairs.get("relationships") or []):
        if not isinstance(pair, dict) or not {"a", "b"} <= set(pair):
            raise LockError(f"relationships.json.relationships[{i}] has no a and b, so it cannot be locked")
        records[f"pair:{pair['a']}+{pair['b']}"] = pair
    return cast["version"], {k: _digest(v) for k, v in sorted(records.items())}


def _read(folder: Path) -> tuple[str, dict[str, str]]:
    path = Path(folder) / LOCK
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LockError(f"{path}: cannot read: {exc}; run srstudio bible lock") from exc
    if not isinstance(data, dict) or set(data) != {"schema", "version", "digests"}:
        raise LockError(f"{path}: expected exactly schema, version and digests")
    if data["schema"] != SCHEMA:
        raise LockError(f"{path}: schema {data['schema']!r} is not {SCHEMA}")
    version, held = data["version"], data["digests"]
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        raise LockError(f"{path}: version {version!r} is not a semantic version")
    if not isinstance(held, dict) or not all(
        isinstance(k, str) and isinstance(v, str) and DIGEST.fullmatch(v) for k, v in held.items()
    ):
        raise LockError(f"{path}: digests must map a record to a sha256 hex digest")
    return version, held


def _triple(version: str) -> tuple[int, int, int]:
    major, minor, patch = (int(n) for n in version.split("."))
    return major, minor, patch


def _bump(old: str, new: str) -> str:
    """How far ``new`` is above ``old``: ``same``, ``patch``, ``minor``, ``major``, or ``back`` when it is below."""
    a, b = _triple(old), _triple(new)
    if b < a:
        return "back"
    if b == a:
        return "same"
    return "major" if b[0] > a[0] else "minor" if b[1] > a[1] else "patch"


def _changelog(folder: Path, version: str) -> list[str]:
    try:
        text = (Path(folder) / "CHANGELOG.md").read_text(encoding="utf-8")
    except OSError as exc:
        return [f"CHANGELOG.md cannot be read: {exc}"]
    if re.search(rf"^## {re.escape(version)}$", text, re.MULTILINE):
        return []
    return [f"CHANGELOG.md has no '## {version}' section saying what this version changed"]


def problems(folder: Path) -> list[str]:
    """Every way the bible has moved away from its lock; empty when the lock holds."""
    version, now = digests(folder)
    try:
        locked, held = _read(folder)
    except LockError as exc:
        return [str(exc)]
    added = sorted(set(now) - set(held))
    removed = sorted(set(held) - set(now))
    changed = sorted(k for k in set(now) & set(held) if now[k] != held[k])
    found = _changelog(folder, version)
    kind = _bump(locked, version)
    if kind == "back":
        found.append(f"version {version} is below the locked {locked}")
    elif kind == "same":
        found += [f"{k}: added without a version bump (locked {locked})" for k in added]
        found += [f"{k}: removed without a version bump (locked {locked})" for k in removed]
        found += [f"{k}: changed without a version bump (locked {locked})" for k in changed]
    else:
        found.append(f"the bible is version {version} and the lock {locked}; run srstudio bible lock")
        if added and kind == "patch":
            found += [f"{k}: a new record needs a minor version, not a patch" for k in added]
    return found


def check(folder: Path) -> None:
    """Raise :class:`LockError` unless the bible still matches its lock."""
    found = problems(folder)
    if found:
        raise LockError("; ".join(found))


def write(folder: Path) -> int:
    """Lock the bible as it is. Refused under the same rules ``check`` applies; returns the number of records."""
    version, now = digests(folder)
    path = Path(folder) / LOCK
    if path.exists():
        found = [p for p in problems(folder) if "run srstudio bible lock" not in p]
        if found:
            raise LockError("; ".join(found))
    else:
        found = _changelog(folder, version)
        if found:
            raise LockError("; ".join(found))
    document = {"schema": SCHEMA, "version": version, "digests": now}
    path.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return len(now)
