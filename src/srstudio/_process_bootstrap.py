"""Standalone stdlib launcher: install hard limits before importing or executing the workload.

Executed by filename with Python isolation enabled; importing srstudio here would
allocate its runtime before the limit was installed.
"""

from __future__ import annotations

import os
import resource
import sys


def main() -> None:
    requested = int(sys.argv[1])
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    limit = min(v for v in (requested, soft, hard) if v != resource.RLIM_INFINITY)
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    command = sys.argv[2:]
    if command[0].startswith('--file-bytes='):
        requested_file = int(command.pop(0).split('=', 1)[1])
        soft, hard = resource.getrlimit(resource.RLIMIT_FSIZE)
        file_limit = min(v for v in (requested_file, soft, hard) if v != resource.RLIM_INFINITY)
        resource.setrlimit(resource.RLIMIT_FSIZE, (file_limit, file_limit))
    os.execvpe(command[0], command, os.environ)


if __name__ == '__main__':
    main()
