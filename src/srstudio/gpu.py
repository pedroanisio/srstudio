"""One GPU job at a time (ADR 0171).

This machine has one GPU, and the test gate, plate path-tracing, proxy rebuilds, the paintover and clay studies and
every encode share it. Two renders at once run the card out of memory: the gate's proxy warm rebuild failed with the
engine's "Not enough memory left" while another render held the GPU, and passed alone. So every engine call the
library makes that uses the GPU (``render``, ``encode``, ``--hw software`` included, since its frames are rendered on
the GPU before libx264 compresses them) runs inside :func:`held`.

:func:`held` takes an exclusive ``flock(2)`` on one file, :func:`lock_path`: ``$SRSTUDIO_GPU_LOCK``, else
:data:`DEFAULT_LOCK`, in ``/run/lock``, the place the file-system hierarchy gives to locks on devices shared by many
programs. It is one file for the whole machine, every worktree, venv and session alike, and it lives on a tmpfs, so
a reboot clears it; a lock dies with the process that held it, so a crash never leaves the GPU taken. The wait is
bounded: :func:`wait_seconds`, ``$SRSTUDIO_GPU_WAIT`` or :data:`DEFAULT_WAIT`, polled every :data:`POLL` seconds by
this code. Past it, :class:`GpuBusyError` names who holds the lock and who waits, read from ``/proc/locks`` and each
process's command line. The lock is re-entrant within a process, so a call inside another one does not wait for
itself; it is taken around each engine call alone, never around a wait on a worker, so a worker never waits for its
parent.

The idea is pnkit's: ``~/heavy.lock`` around every heavy render, and ``tools/vm_preflight.py`` naming its holders.
"""

from __future__ import annotations

import fcntl
import math
import os
import threading
import time
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from .errors import SrstudioError

__all__ = [
    "DEFAULT_LOCK",
    "DEFAULT_WAIT",
    "LOCK_ENV",
    "POLL",
    "WAIT_ENV",
    "GpuBusyError",
    "GpuLockError",
    "Holder",
    "held",
    "holders",
    "lock_path",
    "wait_seconds",
]

LOCK_ENV = "SRSTUDIO_GPU_LOCK"
WAIT_ENV = "SRSTUDIO_GPU_WAIT"
DEFAULT_LOCK = Path("/run/lock/srstudio-gpu.lock")
DEFAULT_WAIT = 900.0  # seconds: pnkit's heavy.lock wait; a clay path-trace or a full encode fits inside it
POLL = 0.25  # seconds between two tries
_COMMAND = 200  # characters of a holder's command line kept


class GpuLockError(SrstudioError, ValueError):
    """The lock cannot be taken as asked: a wait that is not a finite number of seconds, or a lock file that cannot
    be opened."""


@dataclass(frozen=True)
class Holder:
    """A process on the lock: ``pid``, its command line (``?`` once it is gone), and whether it is still waiting."""

    pid: int
    command: str
    waiting: bool


class GpuBusyError(SrstudioError, TimeoutError):
    """Another process kept the GPU for the whole wait. ``holders`` names it, and whoever else waits."""

    def __init__(self, path: Path, waited: float, found: list[Holder]) -> None:
        names = "; ".join(f"pid {h.pid}{' (waiting)' if h.waiting else ''}: {h.command}" for h in found) or "unknown"
        super().__init__(
            f"the GPU lock {path} was held for the whole wait (waited {waited:.1f} s) by {names}",
            code="gpu.busy",
            path=str(path),
            actual=[{"pid": h.pid, "command": h.command, "waiting": h.waiting} for h in found],
            remedy=f"Wait for the holder to finish, or set {WAIT_ENV} to wait longer; never run two renders at once.",
        )
        self.holders = tuple(found)


def lock_path(env: Mapping[str, str] | None = None) -> Path:
    """``$SRSTUDIO_GPU_LOCK``, else :data:`DEFAULT_LOCK`."""
    given = (os.environ if env is None else env).get(LOCK_ENV)
    return Path(given) if given else DEFAULT_LOCK


def _seconds(value: object, said: str) -> float:
    try:
        seconds = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise GpuLockError(f"{said} must be a number of seconds, got {value!r}", code="gpu.wait") from None
    if not math.isfinite(seconds) or seconds < 0:
        raise GpuLockError(f"{said} must be a finite number of seconds, at least 0, got {value!r}", code="gpu.wait")
    return seconds


def wait_seconds(env: Mapping[str, str] | None = None) -> float:
    """``$SRSTUDIO_GPU_WAIT``, else :data:`DEFAULT_WAIT`: a finite number of seconds, at least 0."""
    given = (os.environ if env is None else env).get(WAIT_ENV)
    return DEFAULT_WAIT if given is None else _seconds(given, WAIT_ENV)


def _device(path: Path) -> str | None:
    """The ``major:minor:inode`` ``/proc/locks`` gives the file at ``path``, in its own format."""
    try:
        info = os.stat(path)
    except OSError:
        return None
    return f"{os.major(info.st_dev):02x}:{os.minor(info.st_dev):02x}:{info.st_ino}"


def _command(pid: int, proc: Path) -> str:
    try:
        argv = (proc / str(pid) / "cmdline").read_bytes()
    except OSError:
        return "?"
    said = " ".join(part.decode("utf-8", "replace") for part in argv.split(b"\0") if part)
    return said[:_COMMAND] or "?"


def holders(
    path: Path, *, locks: str | None = None, device: str | None = None, proc: Path = Path("/proc")
) -> list[Holder]:
    """Who holds the lock file at ``path``, then who waits for it, from ``/proc/locks`` (or ``locks``) matched by its
    device and inode (or ``device``). Best effort, for a message: a process can leave between two reads."""
    where = device or _device(Path(path))
    if where is None:
        return []
    if locks is None:
        try:
            locks = (proc / "locks").read_text()
        except OSError:
            return []
    found: list[Holder] = []
    for line in locks.splitlines():
        words = line.split()
        waiting = "->" in words[:2]
        for i, word in enumerate(words):
            if word in ("READ", "WRITE") and i + 2 < len(words) and words[i + 2] == where and words[i + 1].isdigit():
                pid = int(words[i + 1])
                found.append(Holder(pid, _command(pid, proc), waiting))
                break
    return sorted(found, key=lambda h: h.waiting)


class _State:
    """This process's hold on each lock file: its descriptor and how deep the calls go."""

    def __init__(self) -> None:
        self.guard = threading.Lock()
        self.pid = os.getpid()
        self.held: dict[Path, tuple[int, int]] = {}

    def mine(self) -> dict[Path, tuple[int, int]]:
        if self.pid != os.getpid():  # a forked child shares the parent's descriptor, not its hold
            self.pid, self.held = os.getpid(), {}
        return self.held


_STATE = _State()


def _open(path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        return os.open(path, os.O_RDONLY | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW, 0o644)
    except OSError as e:
        raise GpuLockError(f"cannot open the GPU lock {path}: {e}", code="gpu.lock", path=str(path)) from None


@contextmanager
def held(
    *,
    wait: float | None = None,
    path: Path | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> Iterator[None]:
    """Hold the GPU for the ``with`` block: take the lock at ``path`` (:func:`lock_path`), waiting up to ``wait``
    seconds (:func:`wait_seconds`), else raise :class:`GpuBusyError`. Re-entrant within a process."""
    bound = wait_seconds() if wait is None else _seconds(wait, "wait")
    where = Path(path) if path is not None else lock_path()
    with _STATE.guard:
        mine = _STATE.mine()
        if where in mine:
            fd, depth = mine[where]
            mine[where] = (fd, depth + 1)
            fd = -1
        else:
            fd = _open(where)
    if fd != -1:
        try:
            _take(fd, where, bound, clock, sleep)
        except BaseException:
            os.close(fd)
            raise
        with _STATE.guard:
            _STATE.mine()[where] = (fd, 1)
    try:
        yield
    finally:
        with _STATE.guard:
            mine = _STATE.mine()
            if where in mine:
                fd, depth = mine[where]
                if depth > 1:
                    mine[where] = (fd, depth - 1)
                else:
                    del mine[where]
                    os.close(fd)  # closing the last descriptor gives the lock back


def _take(fd: int, where: Path, bound: float, clock: Callable[[], float], sleep: Callable[[float], None]) -> None:
    start = clock()
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            left = bound - (clock() - start)
            if left <= 0:
                raise GpuBusyError(where, clock() - start, holders(where)) from None
            sleep(min(POLL, left))
