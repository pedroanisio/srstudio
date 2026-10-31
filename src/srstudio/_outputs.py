"""Stage related output files and preserve recoverable versions if installation fails."""

from __future__ import annotations

import os
import secrets
import shutil
import stat
import tempfile
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path


@contextmanager
def pinned_directories(paths: tuple[Path, ...], *, private: bool = False) -> Iterator[dict[Path, int]]:
    """Keep output directories open from the input checks through installation; a failure inside the block takes back
    the directories made here that stayed empty, so a build that wrote nothing leaves no folder."""
    with ExitStack() as stack:
        result: dict[Path, int] = {}
        created: list[Path] = []
        for path in paths:
            parent = path.parent
            if parent in result:
                continue
            missing: list[Path] = []
            directory = parent
            while not directory.exists():
                missing.append(directory)
                directory = directory.parent
            for directory in reversed(missing):
                directory.mkdir(mode=0o700 if private else 0o777, exist_ok=True)
                created.append(directory)
            fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            stack.callback(os.close, fd)
            result[parent] = fd
        try:
            yield result
        except BaseException:
            for directory in reversed(created):
                with suppress(OSError):  # a directory holding a report stays, and so do its parents
                    directory.rmdir()
            raise


def _check_directory(path: Path, fd: int) -> None:
    try:
        current = path.stat()
        opened = os.fstat(fd)
        if (current.st_dev, current.st_ino) == (opened.st_dev, opened.st_ino):
            return
    except OSError:
        pass
    raise OSError(f'{path}: output directory changed during the build')


def _write_pinned(
    outputs: list[tuple[Path, bytes]], *, overwrite: bool, directories: dict[Path, int], private: bool
) -> None:
    """Install using directory-relative syscalls so renamed directories cannot redirect writes."""
    with ExitStack() as stack:
        stages: list[tuple[Path, int, str, int]] = []
        preserve = False

        def cleanup(parent_fd: int, folder: str, stage_fd: int) -> None:
            if not preserve:
                for name in ('new', 'old'):
                    try:
                        os.unlink(name, dir_fd=stage_fd)
                    except FileNotFoundError:
                        pass
                os.rmdir(folder, dir_fd=parent_fd)

        for target, content in outputs:
            parent_fd = directories[target.parent]
            _check_directory(target.parent, parent_fd)
            if not overwrite:
                try:
                    os.stat(target.name, dir_fd=parent_fd, follow_symlinks=False)
                except FileNotFoundError:
                    pass
                else:
                    raise FileExistsError(f'{target}: already exists; use overwrite=True to replace it')
            folder = '.srstudio-output-' + secrets.token_hex(12)
            os.mkdir(folder, 0o700, dir_fd=parent_fd)
            stage_fd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
            stack.callback(os.close, stage_fd)
            stack.callback(cleanup, parent_fd, folder, stage_fd)
            fd = os.open('new', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600 if private else 0o666, dir_fd=stage_fd)
            with os.fdopen(fd, 'wb') as source:
                source.write(content)
            stages.append((target, parent_fd, folder, stage_fd))

        changes: list[tuple[Path, int, str, int, bool, bool]] = []
        try:
            for target, parent_fd, folder, stage_fd in stages:
                _check_directory(target.parent, parent_fd)
                backed_up = False
                if overwrite:
                    try:
                        os.stat(target.name, dir_fd=parent_fd, follow_symlinks=False)
                    except FileNotFoundError:
                        pass
                    else:
                        # Reserve a regular destination so a directory cannot become a backup.
                        fd = os.open('old', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=stage_fd)
                        os.close(fd)
                        os.replace(target.name, 'old', src_dir_fd=parent_fd, dst_dir_fd=stage_fd)
                        backed_up = True
                        changes.append((target, parent_fd, folder, stage_fd, True, False))
                        mode = stat.S_IMODE(os.stat('old', dir_fd=stage_fd).st_mode)
                        os.chmod('new', mode & 0o600 if private else mode, dir_fd=stage_fd)
                try:
                    os.link('new', target.name, src_dir_fd=stage_fd, dst_dir_fd=parent_fd)
                except FileExistsError as exc:
                    raise FileExistsError(f'{target}: appeared during output installation') from exc
                if backed_up:
                    changes[-1] = (target, parent_fd, folder, stage_fd, True, True)
                else:
                    changes.append((target, parent_fd, folder, stage_fd, False, True))
            for target, parent_fd, _, _ in stages:
                _check_directory(target.parent, parent_fd)
        except OSError as original:
            retained: list[str] = []
            published: list[str] = []
            for target, parent_fd, folder, stage_fd, backed_up, installed in reversed(changes):
                try:
                    _check_directory(target.parent, parent_fd)
                    output_name = str(target)
                    backup_name = str(target.parent / folder / 'old')
                except OSError:
                    try:
                        moved = Path(os.readlink(f'/proc/self/fd/{parent_fd}'))
                        output_name = f'{moved / target.name} (moved directory)'
                        backup_name = f'{moved / folder / "old"} (moved directory)'
                    except OSError:
                        output_name = f'{target.name} in moved directory formerly at {target.parent}'
                        backup_name = f'{folder}/old in moved directory formerly at {target.parent}'
                if not backed_up:
                    if installed:
                        published.append(output_name)
                    continue
                try:
                    os.link('old', target.name, src_dir_fd=stage_fd, dst_dir_fd=parent_fd, follow_symlinks=False)
                except OSError:
                    retained.append(backup_name)
                    if installed:
                        published.append(output_name)
            preserve = bool(retained)
            details = []
            if published:
                details.append(f"preserved published output(s): {', '.join(published)}")
            if retained:
                details.append(f"prior output backup(s) retained at: {', '.join(retained)}")
            if details:
                cls = FileExistsError if isinstance(original, FileExistsError) else OSError
                raise cls(f"{original}; {'; '.join(details)}") from original
            raise


@dataclass
class _Change:
    target: Path
    backup: Path | None = None
    installed: bool = False


def write_outputs(
    outputs: list[tuple[Path, bytes]],
    *,
    overwrite: bool,
    follow_symlinks: bool = True,
    directories: dict[Path, int] | None = None,
    private: bool = False,
) -> None:
    """Install related files without deleting published paths during error recovery.

    A prior version that cannot be restored without replacing another writer's file remains in its
    private backup directory. The exception identifies any published files and retained backups.
    """
    if directories is not None:
        _write_pinned(outputs, overwrite=overwrite, directories=directories, private=private)
        return
    if not overwrite:
        for target, _ in outputs:
            if target.exists() or target.is_symlink():
                raise FileExistsError(f'{target}: already exists; use overwrite=True to replace it')

    with ExitStack() as stack:
        preserve = False
        folders: list[Path] = []

        def cleanup(folder: Path) -> None:
            if not preserve:
                shutil.rmtree(folder, ignore_errors=True)

        staged: list[tuple[Path, Path, Path]] = []
        for path, content in outputs:
            # Callers that have already checked resolved targets can prevent later redirection.
            target = path.resolve() if overwrite and follow_symlinks and path.is_symlink() else path
            target.parent.mkdir(parents=True, exist_ok=True)
            folder = Path(tempfile.mkdtemp(prefix='.srstudio-output-', dir=target.parent))
            folders.append(folder)
            stack.callback(cleanup, folder)
            source, backup = folder / 'new', folder / 'old'
            source.write_bytes(content)
            staged.append((target, source, backup))

        changes: list[_Change] = []
        try:
            for target, source, backup in staged:
                if not overwrite:
                    try:
                        os.link(source, target)
                    except FileExistsError as exc:
                        raise FileExistsError(f'{target}: already exists; use overwrite=True to replace it') from exc
                    changes.append(_Change(target, installed=True))
                    continue
                change = _Change(target)
                if target.exists() or target.is_symlink():
                    # A reserved regular file prevents accidentally moving a directory into the backup.
                    backup.touch()
                    os.replace(target, backup)
                    change.backup = backup
                    changes.append(change)
                    source.chmod(stat.S_IMODE(backup.stat().st_mode))
                try:
                    os.link(source, target)
                except FileExistsError as exc:
                    raise FileExistsError(f'{target}: appeared during output installation') from exc
                change.installed = True
                if change.backup is None:
                    changes.append(change)
        except OSError as original_error:
            retained: list[str] = []
            preserved_outputs: list[str] = []
            for change in reversed(changes):
                if change.backup is None:
                    if change.installed:
                        preserved_outputs.append(str(change.target))
                    continue
                # Restore only if the destination is absent. Never replace a path another writer may own.
                try:
                    os.link(change.backup, change.target, follow_symlinks=False)
                except OSError:
                    retained.append(str(change.backup))
                    if change.installed:
                        preserved_outputs.append(str(change.target))
            if retained:
                preserve = True
            messages = []
            if preserved_outputs:
                messages.append(f"preserved published output(s): {', '.join(preserved_outputs)}")
            if retained:
                messages.append(f"prior output backup(s) retained at: {', '.join(retained)}")
            if messages:
                message = f"{original_error}; {'; '.join(messages)}"
                if isinstance(original_error, FileExistsError):
                    raise FileExistsError(message) from original_error
                raise OSError(message) from original_error
            raise
