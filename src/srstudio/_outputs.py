"""Stage related output files and restore existing files if installation fails."""

from __future__ import annotations

import os
import shutil
import tempfile
from contextlib import ExitStack
from pathlib import Path


def write_outputs(outputs: list[tuple[Path, bytes]], *, overwrite: bool) -> None:
    """Install each file from its own filesystem, restoring earlier files on an ordinary OS error."""
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
        installed: list[tuple[Path, Path, Path | None]] = []
        try:
            for target, source, backup in staged:
                if not overwrite:
                    try:
                        os.link(source, target)
                    except FileExistsError as exc:
                        raise FileExistsError(f'{target}: already exists; use overwrite=True to replace it') from exc
                    installed.append((target, source, None))
                    continue
                saved = None
                if target.exists() or target.is_symlink():
                    # A reserved regular file prevents accidentally moving a directory into the backup.
                    backup.touch()
                    os.replace(target, backup)
                    saved = backup
                if saved is not None:
                    installed.append((target, source, saved))
                os.replace(source, target)
                if saved is None:
                    installed.append((target, source, None))
        except OSError as original_error:
            rollback_errors = []
            for target, source, saved in reversed(installed):
                try:
                    if saved is not None:
                        os.replace(saved, target)
                    elif overwrite:
                        target.unlink(missing_ok=True)
                    else:
                        if os.path.samestat(target.lstat(), source.stat()):
                            target.unlink()
                except FileNotFoundError:
                    if saved is not None:
                        rollback_errors.append(f'{target}: backup disappeared')
                except OSError as exc:
                    rollback_errors.append(f'{target}: {exc}')
            if rollback_errors:
                preserve = True
                raise OSError(
                    f"output rollback failed ({'; '.join(rollback_errors)}); backups retained in "
                    f"{', '.join(str(folder) for folder in folders)}"
                ) from original_error
            raise
