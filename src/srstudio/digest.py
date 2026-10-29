"""One file hash for the whole library: packages, deliveries, generated assets and caches all name a file by
:func:`sha256`."""

from __future__ import annotations

import hashlib
from pathlib import Path

__all__ = ["sha256"]


def sha256(path: str | Path) -> str:
    """The hex SHA-256 of the file at ``path``, read in 1 MiB blocks so a video never sits whole in memory."""
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()
