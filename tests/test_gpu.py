"""One GPU job at a time (ADR 0171): an flock over one file, a bounded wait, and a typed error that names the holder."""

from __future__ import annotations

import ast
import multiprocessing
import os
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from srstudio import gpu
from srstudio.errors import SrstudioError


@pytest.fixture
def lock(tmp_path, monkeypatch) -> Path:
    path = tmp_path / "gpu.lock"
    monkeypatch.setenv(gpu.LOCK_ENV, str(path))
    return path


def _hold(path: str, ready: object, release: object) -> None:
    with gpu.held(wait=5.0, path=Path(path)):
        ready.set()  # type: ignore[attr-defined]
        release.wait(30)  # type: ignore[attr-defined]


def _try(path: str, wait: float, results: object) -> None:
    try:
        with gpu.held(wait=wait, path=Path(path)):
            results.put(("held", os.getpid()))  # type: ignore[attr-defined]
    except gpu.GpuBusyError as e:
        results.put(("busy", [(h.pid, h.command, h.waiting) for h in e.holders]))  # type: ignore[attr-defined]


def _holder(path: Path):
    context = multiprocessing.get_context("fork")
    ready, release = context.Event(), context.Event()
    process = context.Process(target=_hold, args=(str(path), ready, release))
    process.start()
    assert ready.wait(30), "the holder never took the lock"
    return context, process, release


def test_a_held_lock_refuses_another_process_and_names_the_holder(lock):
    context, holder, release = _holder(lock)
    try:
        results = context.Queue()
        other = context.Process(target=_try, args=(str(lock), 0.0, results))
        other.start()
        outcome, said = results.get(timeout=30)
        other.join(30)
        assert outcome == "busy"
        (pid, command, waiting), *_ = said
        assert pid == holder.pid and not waiting and "python" in command.lower()
    finally:
        release.set()
        holder.join(30)


def test_a_released_lock_is_taken_by_the_process_that_waits(lock):
    context, holder, release = _holder(lock)
    results = context.Queue()
    waiter = context.Process(target=_try, args=(str(lock), 30.0, results))
    waiter.start()
    release.set()
    holder.join(30)
    outcome, pid = results.get(timeout=30)
    waiter.join(30)
    assert (outcome, pid) == ("held", waiter.pid)


def test_the_error_is_typed_and_says_who_holds_the_gpu(lock):
    context, holder, release = _holder(lock)
    try:
        with pytest.raises(gpu.GpuBusyError) as raised, gpu.held(wait=0.0):
            pass
    finally:
        release.set()
        holder.join(30)
    error = raised.value
    assert isinstance(error, SrstudioError) and isinstance(error, TimeoutError)
    assert f"pid {holder.pid}" in str(error) and str(lock) in str(error)
    assert error.to_dict()["code"] == "gpu.busy" and error.holders[0].pid == holder.pid


def test_the_wait_is_bounded_by_ordinary_code(lock):
    """The clock and the sleep are injected: the wait polls until the bound, then stops, however long a holder keeps
    the lock. No wall clock is read."""
    context, holder, release = _holder(lock)
    now, slept = [100.0], []

    def clock() -> float:
        return now[0]

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        now[0] += seconds

    try:
        with pytest.raises(gpu.GpuBusyError, match=r"waited 2\.0 s"), gpu.held(wait=2.0, clock=clock, sleep=sleep):
            pass
    finally:
        release.set()
        holder.join(30)
    assert sum(slept) == pytest.approx(2.0) and max(slept) <= gpu.POLL


def test_a_free_lock_is_taken_at_once_and_given_back(lock):
    with gpu.held(wait=0.0):
        assert lock.exists()
        assert [h.pid for h in gpu.holders(lock)] == [os.getpid()]
    assert gpu.holders(lock) == []


def test_the_lock_is_reentrant_within_a_process(lock):
    with gpu.held(wait=0.0), gpu.held(wait=0.0):
        assert [h.pid for h in gpu.holders(lock)] == [os.getpid()]
    assert gpu.holders(lock) == []


def test_an_error_inside_gives_the_lock_back(lock):
    with pytest.raises(RuntimeError), gpu.held(wait=0.0):
        raise RuntimeError("the engine failed")
    assert gpu.holders(lock) == []


def test_the_place_and_the_wait_come_from_the_environment(monkeypatch, tmp_path):
    monkeypatch.delenv(gpu.LOCK_ENV, raising=False)
    monkeypatch.delenv(gpu.WAIT_ENV, raising=False)
    assert gpu.lock_path() == gpu.DEFAULT_LOCK and gpu.wait_seconds() == gpu.DEFAULT_WAIT
    monkeypatch.setenv(gpu.LOCK_ENV, str(tmp_path / "x.lock"))
    monkeypatch.setenv(gpu.WAIT_ENV, "12.5")
    assert gpu.lock_path() == tmp_path / "x.lock" and gpu.wait_seconds() == 12.5


@pytest.mark.parametrize("bad", ["", "soon", "-1", "nan", "inf"])
def test_a_wait_that_is_not_a_finite_number_of_seconds_is_refused(monkeypatch, bad):
    monkeypatch.setenv(gpu.WAIT_ENV, bad)
    with pytest.raises(gpu.GpuLockError, match=gpu.WAIT_ENV):
        gpu.wait_seconds()
    with pytest.raises(gpu.GpuLockError):
        gpu.held(wait=float(bad) if bad in ("-1", "nan", "inf") else None).__enter__()


def test_a_lock_place_that_is_a_link_is_refused(tmp_path):
    (tmp_path / "real").write_text("")
    (tmp_path / "gpu.lock").symlink_to(tmp_path / "real")
    with pytest.raises(gpu.GpuLockError, match="cannot open"), gpu.held(wait=0.0, path=tmp_path / "gpu.lock"):
        pass


LOCKS = """\
1: FLOCK  ADVISORY  WRITE 4242 00:1a:777 0 EOF
1: -> FLOCK  ADVISORY  WRITE 4343 00:1a:777 0 EOF
2: POSIX  ADVISORY  READ 9 fc:01:777 128 128
3: FLOCK  ADVISORY  WRITE 5 00:1a:778 0 EOF
garbage
"""


def test_holders_are_read_from_proc_locks_by_device_and_inode(tmp_path):
    proc = tmp_path / "proc"
    for pid, argv in ((4242, b"scene-render\x00encode\x00a.scene.xml\x00"), (4343, b"python\x00-m\x00pytest\x00")):
        (proc / str(pid)).mkdir(parents=True)
        (proc / str(pid) / "cmdline").write_bytes(argv)
    found = gpu.holders(tmp_path / "x", locks=LOCKS, device="00:1a:777", proc=proc)
    assert found == [
        gpu.Holder(4242, "scene-render encode a.scene.xml", False),
        gpu.Holder(4343, "python -m pytest", True),
    ]
    assert gpu.holders(tmp_path / "x", locks=LOCKS, device="00:1a:999", proc=proc) == []
    gone = gpu.holders(tmp_path / "x", locks=LOCKS, device="00:1a:778", proc=proc)
    assert gone == [gpu.Holder(5, "?", False)]


def test_a_missing_lock_file_has_no_holders(tmp_path):
    assert gpu.holders(tmp_path / "absent.lock") == []


# -- the call sites ---------------------------------------------------------------------------------------------------
REPO = Path(__file__).resolve().parents[1]
GPU_VERBS = {"render", "encode"}  # measured: validate, eval, resolve, captions, inspect and scopes open no GPU device
UNDER_LOCK = {("src/srstudio/plates.py", "_invoke_renderer")}  # called only from _engine_render, inside the lock


def _held(node: ast.With) -> bool:
    return any(
        isinstance(item.context_expr, ast.Call)
        and isinstance(item.context_expr.func, ast.Attribute)
        and item.context_expr.func.attr == "held"
        and isinstance(item.context_expr.func.value, ast.Name)
        and item.context_expr.func.value.id == "gpu"
        for item in node.items
    )


def _engine_commands(tree: ast.AST) -> Iterator[tuple[ast.FunctionDef | ast.AsyncFunctionDef, ast.expr, bool]]:
    """Each command literal ``[engine, "render" | "encode", ...]`` in a function, the function, and whether a
    ``with gpu.held()`` holds the literal or, when the command is built first and run after, holds a part of the
    function."""

    def walk(node: ast.AST, function, inside: bool) -> Iterator:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                yield from walk(child, child, False)
                continue
            here = inside or (isinstance(child, ast.With) and _held(child))
            if (
                function is not None
                and isinstance(child, ast.List | ast.Tuple)
                and len(child.elts) > 1
                and not isinstance(child.elts[0], ast.Constant)
                and isinstance(child.elts[1], ast.Constant)
                and child.elts[1].value in GPU_VERBS
            ):
                anywhere = any(isinstance(n, ast.With) and _held(n) for n in ast.walk(function))
                yield function, child, here or anywhere
            yield from walk(child, function, here)

    yield from walk(tree, None, False)


def _sources() -> list[Path]:
    library, episodes, tools = REPO / "src" / "srstudio", REPO / "episodes", REPO / "tools"
    return sorted([*library.glob("*.py"), *episodes.rglob("*.py"), *tools.glob("*.py")])


def test_every_engine_call_that_uses_the_gpu_takes_the_lock():
    """A control that can fail: a new ``render`` or ``encode`` call outside the lock fails here."""
    seen, missing = [], []
    for path in _sources():
        name = path.relative_to(REPO).as_posix()
        for function, literal, locked in _engine_commands(ast.parse(path.read_text(), name)):
            seen.append(f"{name}:{function.name}")
            if not locked and (name, function.name) not in UNDER_LOCK:
                missing.append(f"{name}:{literal.lineno} {function.name}")
    assert missing == []
    assert {
        "src/srstudio/master.py:encode",
        "src/srstudio/plates.py:_invoke_renderer",
        "src/srstudio/frames.py:at_size",
        "src/srstudio/social.py:take_still",
        "src/srstudio/benchmark.py:_render_frames",
    } <= set(seen)


def test_the_scan_finds_a_call_outside_the_lock():
    tree = ast.parse(
        "def bad(engine):\n    subprocess.run([engine, 'render', 'a.scene.xml'])\n"
        "def good(engine):\n    with gpu.held():\n        subprocess.run([engine, 'encode', 'a.scene.xml'])\n"
        "def other(engine):\n    subprocess.run([engine, 'validate', 'a.scene.xml'])\n"
    )
    assert [(f.name, locked) for f, _, locked in _engine_commands(tree)] == [("bad", False), ("good", True)]


def _mine_while(lock: Path) -> list[int]:
    return [h.pid for h in gpu.holders(lock) if not h.waiting]


def test_a_master_encode_holds_the_lock_while_the_engine_runs(lock, tmp_path):
    from srstudio import master

    folder = tmp_path / "episodes" / "reel"
    folder.mkdir(parents=True)
    scene = folder / "reel.scene.xml"
    scene.write_text('<scene><output id="main" path="renders/reel.mp4"/></scene>')
    during: list[list[int]] = []

    def run(command, **_kw):
        during.append(_mine_while(lock))
        out = Path(command[command.index("--out-dir") + 1]) / "renders"
        out.mkdir(parents=True)
        (out / "reel.mp4").write_bytes(b"m")
        return subprocess.CompletedProcess(command, 0, "", "")

    master.encode(scene, tmp_path / "generated", engine="scene-render", run=run)
    assert during == [[os.getpid()]] and gpu.holders(lock) == []


def test_a_plate_render_holds_the_lock_and_waits_outside_its_budget(lock, tmp_path, monkeypatch):
    from srstudio import plates

    during: list[list[int]] = []
    monkeypatch.setattr(plates, "_invoke_renderer", lambda *_a: during.append(_mine_while(lock)))
    plates._engine_render(Path("scene-render"), tmp_path / "a.scene.xml", tmp_path / "a.png")
    assert during == [[os.getpid()]] and gpu.holders(lock) == []


def test_a_busy_gpu_stops_a_plate_render_before_the_engine_with_the_typed_error(lock, tmp_path, monkeypatch):
    from srstudio import plates

    called: list[object] = []
    monkeypatch.setattr(plates, "_invoke_renderer", lambda *_a: called.append(_a))
    monkeypatch.setenv(gpu.WAIT_ENV, "0")
    context, holder, release = _holder(lock)
    try:
        with pytest.raises(gpu.GpuBusyError, match=f"pid {holder.pid}"):
            plates._engine_render(Path("scene-render"), tmp_path / "a.scene.xml", tmp_path / "a.png")
    finally:
        release.set()
        holder.join(30)
    assert called == []
