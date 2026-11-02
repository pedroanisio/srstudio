"""Approved files are write-once (ADR 0170).

A file whose bytes were approved, paid for or delivered (a master, a voice take, a composed song, a package version)
is never replaced by a re-run of the tool that made it: the approval belongs to those bytes. A re-run that should
leave a second candidate writes it beside the first, under the next free name.

- :func:`write_once` writes bytes to a path where nothing is, and raises :class:`WriteOnceError` otherwise.
- :func:`write_same` is :func:`write_once` for derived bytes: a path that already holds exactly these bytes passes.
- :func:`install_once` moves a finished file (an engine's encode) to a path where nothing is.
- :func:`next_free`, :func:`write_next` and :func:`install_next` take ``excerpt.wav``, then ``excerpt-v2.wav``...

The check and the create are one operation. The bytes are written to a private stage beside the target, flushed,
and given the target's name with ``link(2)``, which fails when anything has that name, a symbolic link included,
dangling or not. So two processes cannot both win a path, and no reader ever sees a half-written file under the final
name. Where the file system has no hard links, the name is claimed with ``O_CREAT | O_EXCL`` instead, which refuses
the same things, and the bytes are copied into it.
"""

from __future__ import annotations

import errno
import os
import secrets
import shutil
import stat
from pathlib import Path

from .errors import SrstudioError

__all__ = [
    "MOST",
    "WriteOnceError",
    "install_next",
    "install_once",
    "must_be_free",
    "next_free",
    "write_next",
    "write_once",
    "write_same",
]

MOST = 10_000  # the most names next_free tries: a folder with more candidates than this is a fault to look at
_NO_LINKS = frozenset({errno.EPERM, errno.EOPNOTSUPP, errno.EXDEV, errno.EMLINK, errno.ENOSYS})


class WriteOnceError(SrstudioError, FileExistsError):
    """Something already has the path an approved file would take, and approved files are never replaced."""


def _taken(path: Path, why: str = "exists") -> WriteOnceError:
    return WriteOnceError(
        f"{path} {why}: an approved file is never replaced; write the new one beside it (files.next_free)",
        code="files.exists",
        path=str(path),
        remedy="Write the new file under srstudio.files.next_free(path), or move the old one away by hand.",
    )


def _payload(data: bytes | bytearray | memoryview | str, encoding: str) -> bytes:
    return data.encode(encoding) if isinstance(data, str) else bytes(data)


def _stage_name(target: Path) -> Path:
    return target.parent / f".{target.name}.{secrets.token_hex(8)}.part"


def _claim(source: Path, target: Path) -> None:
    """Give ``source``'s bytes the name ``target``, which must be free; ``source`` stays as it is."""
    try:
        os.link(source, target)
        return
    except FileExistsError:
        raise _taken(target) from None
    except OSError as e:
        if e.errno not in _NO_LINKS:
            raise
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        fd = os.open(target, flags, stat.S_IMODE(source.stat().st_mode))
    except FileExistsError:
        raise _taken(target) from None
    try:
        with os.fdopen(fd, "wb") as out, source.open("rb") as given:
            shutil.copyfileobj(given, out)
            out.flush()
            os.fsync(out.fileno())
    except BaseException:
        target.unlink(missing_ok=True)  # the name was ours alone, and the copy did not finish
        raise


def write_once(path: str | os.PathLike[str], data: bytes | bytearray | memoryview | str, *,
               encoding: str = "utf-8", mode: int = 0o666) -> Path:  # fmt: skip
    """Write ``data`` (bytes, or text in ``encoding``) to ``path`` and return it; :class:`WriteOnceError` when
    anything has that name. ``mode`` is filtered by the umask, as ``open`` does. A failure leaves no file."""
    target = Path(path)
    payload = _payload(data, encoding)
    if os.path.lexists(target):
        raise _taken(target)
    stage = _stage_name(target)
    fd = os.open(stage, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, mode)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(payload)
            out.flush()
            os.fsync(out.fileno())
        _claim(stage, target)
    finally:
        stage.unlink(missing_ok=True)
    return target


def write_same(path: str | os.PathLike[str], data: bytes | bytearray | memoryview | str, *,
               encoding: str = "utf-8", mode: int = 0o666) -> Path:  # fmt: skip
    """:func:`write_once`, except that a regular file already holding exactly these bytes passes: for bytes derived
    from an approved file (a WAV decoded from its take), which two runs make alike. Other bytes, or a link, raise."""
    target = Path(path)
    payload = _payload(data, encoding)
    try:
        return write_once(target, payload, mode=mode)
    except WriteOnceError:
        if target.is_symlink() or not target.is_file():
            raise
        if target.read_bytes() != payload:
            raise _taken(target, "holds other bytes") from None
        return target


def install_once(source: str | os.PathLike[str], path: str | os.PathLike[str]) -> Path:
    """Move the finished regular file ``source`` to ``path``, which must be free, and return ``path``. Both must be on
    one file system (a stage beside the target). A refusal leaves ``source`` where it was."""
    given, target = Path(source), Path(path)
    if given.is_symlink() or not given.is_file():
        raise WriteOnceError(f"{given} is not a regular file to install", code="files.source", path=str(given))
    if os.path.lexists(target):
        raise _taken(target)
    _claim(given, target)
    given.unlink()
    return target


def must_be_free(path: str | os.PathLike[str]) -> Path:
    """``path`` when nothing has that name, else :class:`WriteOnceError`: the check a costly run makes before it
    starts, so a file it could never install is never paid for. It only looks: the install claims the name."""
    target = Path(path)
    if os.path.lexists(target):
        raise _taken(target)
    return target


def next_free(path: str | os.PathLike[str], suffix: str = "-v") -> Path:
    """``path`` when nothing has that name, else the first free ``<stem><suffix>N<ext>`` for N = 2, 3...: the stem
    keeps every dot but the last (``a.scene.mp4`` gives ``a.scene-v2.mp4``). It only looks: :func:`write_next` claims.
    A symbolic link, dangling or not, takes its name. After :data:`MOST` names, :class:`WriteOnceError`."""
    target = Path(path)
    if not os.path.lexists(target):
        return target
    stem, ext = os.path.splitext(target.name)
    for n in range(2, MOST + 2):
        candidate = target.with_name(f"{stem}{suffix}{n}{ext}")
        if not os.path.lexists(candidate):
            return candidate
    raise WriteOnceError(f"no free name for {target} in {MOST} tries", code="files.full", path=str(target))


def write_next(path: str | os.PathLike[str], data: bytes | bytearray | memoryview | str, *, suffix: str = "-v",
               encoding: str = "utf-8", mode: int = 0o666) -> Path:  # fmt: skip
    """:func:`write_once` to :func:`next_free`, taking the next name when another process claims one first."""
    payload = _payload(data, encoding)
    for _ in range(MOST):
        try:
            return write_once(next_free(path, suffix), payload, mode=mode)
        except WriteOnceError as e:
            if e.to_dict()["code"] != "files.exists":
                raise
    raise WriteOnceError(f"no free name for {path} in {MOST} tries", code="files.full", path=str(path))


def install_next(source: str | os.PathLike[str], path: str | os.PathLike[str], *, suffix: str = "-v") -> Path:
    """:func:`install_once` to :func:`next_free`, taking the next name when another process claims one first."""
    for _ in range(MOST):
        try:
            return install_once(source, next_free(path, suffix))
        except WriteOnceError as e:
            if e.to_dict()["code"] != "files.exists":
                raise
    raise WriteOnceError(f"no free name for {path} in {MOST} tries", code="files.full", path=str(path))
