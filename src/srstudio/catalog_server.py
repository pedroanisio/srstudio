"""``srstudio serve``: the catalog site over HTTP, read-only, on the standard library alone (ADR 0046).

A browser will not seek in a video unless the server answers byte ranges, and ``http.server``'s file handler does
not, so this one does: 206 with ``Content-Range``, and 416 for a range that is bad or past the end. It serves GET
and HEAD from inside the site folder and nothing else: traversal and symlinks out of the folder are refused, hidden
files (a build's partial writes) and folders are not found, and no folder is listed. Media names follow their
content, so they may be cached forever; ``index.html`` and ``catalog.json`` are revalidated on every load.

There is no authentication, so the default bind is loopback.
"""

from __future__ import annotations

import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from typing import BinaryIO
from urllib.parse import unquote

from .errors import SrstudioError

HOST = "127.0.0.1"
PORT = 8765
INDEX = "index.html"
TYPES = {
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json",
    ".mp3": "audio/mpeg",
    ".mp4": "video/mp4",
    ".png": "image/png",
    ".ttf": "font/ttf",
}
FOREVER = "public, max-age=31536000, immutable"
_BLOCK = 1 << 20
_RANGE = re.compile(r"bytes=(\d*)-(\d*)", re.IGNORECASE)


class ServeError(SrstudioError):
    """A site that cannot be served."""


class Unsatisfiable(SrstudioError):
    """A byte range that is bad or lies past the end: the 416 case."""


def parse_range(header: str, size: int) -> tuple[int, int] | None:
    """The first and last byte ``header`` asks for, or None for the whole file: the header is absent, names a unit
    this server does not do (which a server must ignore), or lists several ranges (which it may)."""
    if not header or not header.lower().startswith("bytes=") or "," in header:
        return None
    m = _RANGE.fullmatch(header.strip())
    if m is None or not (m[1] or m[2]):
        raise Unsatisfiable
    if not m[1]:  # the last n bytes
        tail = int(m[2])
        if tail == 0:
            raise Unsatisfiable
        return (max(size - tail, 0), size - 1) if size else None
    first = int(m[1])
    last = int(m[2]) if m[2] else size - 1
    if first >= size or last < first:
        raise Unsatisfiable
    return first, min(last, size - 1)


class Handler(BaseHTTPRequestHandler):
    server_version = "srstudio"
    sys_version = ""
    protocol_version = "HTTP/1.1"  # keep-alive: a video's many ranges share a connection
    timeout = 60  # an idle or stalled client gives its thread back
    root: Path  # the resolved site folder, set by make_server

    def do_GET(self) -> None:
        self._serve(body=True)

    def do_HEAD(self) -> None:
        self._serve(body=False)

    def _read_only(self) -> None:
        self._empty(405, Allow="GET, HEAD")

    do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = do_TRACE = do_CONNECT = _read_only

    def log_request(self, code: int | str = "-", size: int | str = "-") -> None:
        """A page load is hundreds of requests: log the failures only."""
        if int(code) >= 400:
            super().log_request(code, size)

    def _empty(self, status: int, **headers: str) -> None:
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key.replace("_", "-"), value)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _resolve(self) -> Path:
        """The file a request names, inside the site. :class:`OSError` subclasses and ``ValueError`` say why not."""
        raw = self.path.split("?", 1)[0].split("#", 1)[0]
        name = unquote(raw, errors="strict")
        if "\0" in name:
            raise ValueError("a NUL in the path")
        parts = PurePosixPath(name.replace("\\", "/")).parts
        parts = tuple(p for p in parts if p != "/")
        if ".." in parts:
            raise PermissionError(name)
        if any(p.startswith(".") for p in parts):
            raise FileNotFoundError(name)
        path = (self.root.joinpath(*parts) if parts else self.root / INDEX).resolve()
        if not path.is_relative_to(self.root):
            raise PermissionError(name)
        if not path.is_file():
            raise FileNotFoundError(name)
        return path

    def _serve(self, *, body: bool) -> None:
        try:
            path = self._resolve()
            f = path.open("rb")
        except (ValueError, UnicodeDecodeError):
            return self._empty(400)
        except PermissionError:
            return self._empty(403)
        except OSError:  # missing, or removed since it was resolved
            return self._empty(404)
        with f:  # the open file, not the name: a rebuild's os.replace cannot change what is being sent
            self._send(path, f, body)

    def _send(self, path: Path, f: BinaryIO, body: bool) -> None:
        st = os.fstat(f.fileno())
        etag = f'"{st.st_size:x}-{st.st_mtime_ns:x}"'
        headers = {
            "Accept-Ranges": "bytes",
            "Cache-Control": FOREVER if path.relative_to(self.root).parts[0] == "media" else "no-cache",
            "ETag": etag,
            "X-Content-Type-Options": "nosniff",
        }
        if self.headers.get("If-None-Match") == etag:
            return self._empty(304, **{k.replace("-", "_"): v for k, v in headers.items()})
        wanted = self.headers.get("Range", "")
        if self.headers.get("If-Range", etag) != etag:
            wanted = ""  # the file changed since the part the client holds: it needs all of it
        try:
            span = parse_range(wanted, st.st_size)
        except Unsatisfiable:
            return self._empty(416, Content_Range=f"bytes */{st.st_size}")
        first, length = (0, st.st_size) if span is None else (span[0], span[1] - span[0] + 1)
        self.send_response(200 if span is None else 206)
        self.send_header("Content-Type", TYPES.get(path.suffix.lower(), "application/octet-stream"))
        self.send_header("Content-Length", str(length))
        if span is not None:
            self.send_header("Content-Range", f"bytes {span[0]}-{span[1]}/{st.st_size}")
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()
        if not body:
            return
        f.seek(first)
        left = length
        try:
            while left and (block := f.read(min(_BLOCK, left))):
                self.wfile.write(block)
                left -= len(block)
        except (BrokenPipeError, ConnectionResetError):  # a video seek abandons the range it was reading
            self.close_connection = True


def make_server(site: Path, host: str = HOST, port: int = PORT) -> ThreadingHTTPServer:
    """A bound server for a built site. :class:`ServeError` when ``site`` is not one; :class:`OSError` when the
    address cannot be bound."""
    root = Path(site).resolve()
    if not (root / INDEX).is_file():
        raise ServeError(f"{site} has no {INDEX}: build it with srstudio page --site")
    handler = type("SiteHandler", (Handler,), {"root": root})
    return ThreadingHTTPServer((host, port), handler)


def serve(site: Path, host: str = HOST, port: int = PORT) -> None:
    """Serve ``site`` until interrupted."""
    httpd = make_server(site, host, port)
    print(f"http://{host}:{httpd.server_address[1]}/  {site}", flush=True)
    if host not in ("127.0.0.1", "::1", "localhost"):
        print(f"srstudio serve: bound to {host} with no authentication", file=sys.stderr)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
