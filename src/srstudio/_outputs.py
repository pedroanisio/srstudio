"""Stage related output files and preserve recoverable versions if installation fails."""

from __future__ import annotations

import os
import shutil
import stat
import tempfile
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path


@dataclass
class _Change:
    target: Path
    backup: Path | None = None
    installed: bool = False


def write_outputs(outputs: list[tuple[Path, bytes]], *, overwrite: bool) -> None:
    """Install related files without deleting published paths during error recovery.

    A prior version that cannot be restored without replacing another writer's file remains in its
    private backup directory. The exception identifies any published files and retained backups.
    """
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
            # Preserve the existing write-through behavior for symlinks when replacement is allowed.
            target = path.resolve() if overwrite and path.is_symlink() else path
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
