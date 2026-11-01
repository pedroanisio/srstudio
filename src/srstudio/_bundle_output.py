"""Publish a new private directory in one non-replacing Linux rename operation."""

from __future__ import annotations

import ctypes
import errno
import os
import secrets
from pathlib import Path

from ._outputs import _check_directory, pinned_directories


def rename_new(parent_fd: int, source: str, target: str) -> None:
    library = ctypes.CDLL(None, use_errno=True)
    operation = getattr(library, 'renameat2', None)
    if operation is None:
        raise OSError(errno.ENOSYS, 'atomic directory publication requires renameat2(RENAME_NOREPLACE)')
    operation.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    operation.restype = ctypes.c_int
    if operation(parent_fd, os.fsencode(source), parent_fd, os.fsencode(target), 1) != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), target)


def publish(output: Path, files: dict[str, bytes]) -> None:
    if (
        not isinstance(output, Path)
        or output.name in ('', '.', '..')
        or not files
        or any(
            type(name) is not str
            or '/' in name
            or '\\' in name
            or '\x00' in name
            or name in ('', '.', '..')
            or type(data) is not bytes
            for name, data in files.items()
        )
    ):
        raise ValueError('a new directory and flat immutable file contents are required')
    with pinned_directories((output,), private=True) as directories:
        parent_fd = directories[output.parent]
        name = '.srstudio-bundle-' + secrets.token_hex(12)
        os.mkdir(name, 0o700, dir_fd=parent_fd)
        try:
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
        except OSError:
            os.rmdir(name, dir_fd=parent_fd)
            raise
        installed = False
        try:
            for filename, content in files.items():
                file_fd = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
                with os.fdopen(file_fd, 'wb') as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
            os.fsync(fd)
            _check_directory(output.parent, parent_fd)
            rename_new(parent_fd, name, output.name)
            installed = True
        finally:
            # The opened directory follows its rename. Delete only an unpublished
            # stage; never remove files from the complete published destination.
            try:
                if not installed:
                    for filename in files:
                        try:
                            os.unlink(filename, dir_fd=fd)
                        except FileNotFoundError:
                            pass
                    os.rmdir(name, dir_fd=parent_fd)
            finally:
                os.close(fd)
