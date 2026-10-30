"""``srstudio serve``: a read-only server for the catalog site, with the byte ranges a browser needs to seek a video.

Every request goes over real loopback sockets to a server on an ephemeral port. ``http.client`` sends the request
target as written, so traversal is tested the way an attacker would send it, not as a browser normalises it.
"""

import http.client
import os
import socket
import threading
from pathlib import Path

import pytest

from srstudio import catalog_server as server
from srstudio.cli import main

VIDEO = bytes(range(256)) * 4  # 1024 bytes
NAME = "0123456789abcdef0123456789abcdef"


@pytest.fixture
def site(tmp_path) -> Path:
    root = tmp_path / "site"
    (root / "media").mkdir(parents=True)
    (root / "index.html").write_text("<!doctype html><title>catálogo</title>", encoding="utf-8")
    (root / "catalog.json").write_text("{}")
    (root / "media" / f"{NAME}.mp4").write_bytes(VIDEO)
    for ext in ("jpg", "png", "ttf", "mp3", "js", "css", "bin"):
        (root / "media" / f"{NAME}.{ext}").write_bytes(b"x")
    (root / "media" / "empty.mp4").write_bytes(b"")
    (root / ".index.html.partial").write_text("a build in progress")
    (tmp_path / "secret.txt").write_text("outside the site")
    return root


@pytest.fixture
def get(site):
    httpd = server.make_server(site, "127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    def request(target: str, method: str = "GET", **headers: str):
        conn = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=10)
        conn.putrequest(method, target, skip_accept_encoding=True)
        for key, value in headers.items():
            conn.putheader(key.replace("_", "-"), value)
        conn.endheaders()
        response = conn.getresponse()
        body = response.read()
        conn.close()
        return response, body

    yield request
    httpd.shutdown()
    httpd.server_close()
    thread.join()


def test_the_index_is_served_at_the_root_and_never_stored_stale(get):
    response, body = get("/")
    assert response.status == 200 and "catálogo" in body.decode("utf-8")
    assert response.getheader("Content-Type") == "text/html; charset=utf-8"
    assert response.getheader("Cache-Control") == "no-cache"
    assert get("/index.html?v=1#top")[0].status == 200


def test_media_may_be_cached_forever_since_their_names_are_their_content(get):
    response, body = get(f"/media/{NAME}.mp4")
    assert response.status == 200 and body == VIDEO
    assert response.getheader("Cache-Control") == "public, max-age=31536000, immutable"
    assert response.getheader("Accept-Ranges") == "bytes" and response.getheader("Content-Length") == "1024"
    assert response.getheader("X-Content-Type-Options") == "nosniff"


@pytest.mark.parametrize(
    "path, kind",
    [
        (f"media/{NAME}.mp4", "video/mp4"),
        (f"media/{NAME}.jpg", "image/jpeg"),
        (f"media/{NAME}.png", "image/png"),
        (f"media/{NAME}.ttf", "font/ttf"),
        (f"media/{NAME}.mp3", "audio/mpeg"),
        (f"media/{NAME}.js", "text/javascript; charset=utf-8"),
        (f"media/{NAME}.css", "text/css; charset=utf-8"),
        (f"media/{NAME}.bin", "application/octet-stream"),
        ("catalog.json", "application/json"),
    ],
)
def test_content_types(get, path, kind):
    assert get(f"/{path}")[0].getheader("Content-Type") == kind


@pytest.mark.parametrize(
    "header, status, content_range, body",
    [
        ("bytes=0-1023", 206, "bytes 0-1023/1024", VIDEO),
        ("bytes=0-0", 206, "bytes 0-0/1024", VIDEO[:1]),
        ("bytes=100-199", 206, "bytes 100-199/1024", VIDEO[100:200]),
        ("bytes=1000-", 206, "bytes 1000-1023/1024", VIDEO[1000:]),
        ("bytes=1000-99999", 206, "bytes 1000-1023/1024", VIDEO[1000:]),  # a last byte past the end is clamped
        ("bytes=-24", 206, "bytes 1000-1023/1024", VIDEO[-24:]),
        ("bytes=-99999", 206, "bytes 0-1023/1024", VIDEO),
        ("BYTES=0-1", 206, "bytes 0-1/1024", VIDEO[:2]),  # range units are case-insensitive
    ],
)
def test_a_satisfiable_range_is_a_206(get, header, status, content_range, body):
    response, got = get(f"/media/{NAME}.mp4", Range=header)
    assert (response.status, response.getheader("Content-Range"), got) == (status, content_range, body)
    assert response.getheader("Content-Length") == str(len(body))
    assert response.getheader("Content-Type") == "video/mp4"


@pytest.mark.parametrize(
    "header",
    ["bytes=1024-", "bytes=5000-6000", "bytes=-0", "bytes=9-3", "bytes=abc", "bytes=", "bytes=-", "bytes=1-2-3"],
)
def test_a_bad_or_unsatisfiable_range_is_a_416(get, header):
    response, body = get(f"/media/{NAME}.mp4", Range=header)
    assert (response.status, response.getheader("Content-Range"), body) == (416, "bytes */1024", b"")
    assert response.getheader("Content-Length") == "0"


@pytest.mark.parametrize("header", ["seconds=0-1", "bytes=0-1,5-6", "items 0-1"])
def test_a_range_the_server_does_not_do_is_ignored_for_the_whole_file(get, header):
    response, body = get(f"/media/{NAME}.mp4", Range=header)  # a server must ignore units it does not understand
    assert (response.status, response.getheader("Content-Range"), body) == (200, None, VIDEO)


def test_an_empty_file(get):
    assert get("/media/empty.mp4")[0].status == 200
    assert get("/media/empty.mp4", Range="bytes=0-")[0].status == 416
    response, body = get("/media/empty.mp4", Range="bytes=-5")
    assert (response.status, body) == (200, b"")


def test_head_sends_the_headers_of_get_and_no_body(get):
    response, body = get(f"/media/{NAME}.mp4", "HEAD")
    assert (response.status, body, response.getheader("Content-Length")) == (200, b"", "1024")
    response, body = get(f"/media/{NAME}.mp4", "HEAD", Range="bytes=0-9")
    assert (response.status, body, response.getheader("Content-Range")) == (206, b"", "bytes 0-9/1024")


def test_a_validator_answers_304_and_guards_a_resumed_range(get):
    etag = get("/index.html")[0].getheader("ETag")
    assert etag and get("/index.html", If_None_Match=etag)[0].status == 304
    assert get("/index.html", If_None_Match='"other"')[0].status == 200
    video = get(f"/media/{NAME}.mp4")[0].getheader("ETag")
    assert get(f"/media/{NAME}.mp4", Range="bytes=0-1", If_Range=video)[0].status == 206
    assert get(f"/media/{NAME}.mp4", Range="bytes=0-1", If_Range='"old"')[0].status == 200  # it changed: all of it


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH", "OPTIONS", "TRACE", "CONNECT"])
def test_it_is_read_only(get, site, method):
    response, _ = get("/index.html", method)
    assert (response.status, response.getheader("Allow")) == (405, "GET, HEAD")
    assert (site / "index.html").exists()


@pytest.mark.parametrize(
    "target",
    [
        "/../secret.txt",
        "/media/../../secret.txt",
        "/..%2fsecret.txt",
        "/%2e%2e/secret.txt",
        "/%2E%2E%2Fsecret.txt",
        "/media/..%2f..%2fsecret.txt",
    ],
)
def test_traversal_is_refused(get, target):
    response, body = get(target)
    assert response.status == 403 and b"outside the site" not in body


def test_an_absolute_path_stays_inside_the_site(get, tmp_path):
    response, body = get("/" + str(tmp_path / "secret.txt"))
    assert response.status == 404 and b"outside the site" not in body
    response, body = get("//" + str(tmp_path / "secret.txt").lstrip("/"))
    assert response.status == 404 and b"outside the site" not in body


def test_a_symlink_out_of_the_site_is_refused_and_one_inside_it_is_served(get, site, tmp_path):
    (site / "media" / "out.txt").symlink_to(tmp_path / "secret.txt")
    (site / "media" / "folder").symlink_to(tmp_path)
    (site / "media" / "in.mp4").symlink_to(site / "media" / f"{NAME}.mp4")
    assert get("/media/out.txt")[0].status == 403
    assert get("/media/folder/secret.txt")[0].status == 403
    assert get("/media/in.mp4")[1] == VIDEO


@pytest.mark.parametrize("target", ["/media/", "/media", "/nothing.html", "/media/nothing.mp4", "/.index.html.partial"])
def test_folders_are_not_listed_and_hidden_or_missing_files_are_not_found(get, target):
    response, body = get(target)
    assert response.status == 404 and NAME.encode() not in body


@pytest.mark.parametrize("target", ["/%00", "/index.html%00.jpg", "/%ff"])
def test_a_path_that_is_not_a_name_is_a_bad_request(get, target):
    assert get(target)[0].status == 400


def test_an_index_replaced_by_a_rebuild_is_served_at_once(get, site):
    new = site / ".new"
    new.write_text("new")
    os.replace(new, site / "index.html")
    assert get("/")[1] == b"new"


def test_a_client_that_leaves_mid_download_does_not_take_the_server_down(site):
    (site / "media" / "big.mp4").write_bytes(b"x" * (32 << 20))
    httpd = server.make_server(site, "127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    port = httpd.server_address[1]
    with socket.create_connection(("127.0.0.1", port), timeout=10) as sock:
        sock.sendall(b"GET /media/big.mp4 HTTP/1.1\r\nHost: x\r\n\r\n")
        sock.recv(1024)
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request("GET", "/catalog.json")
    assert conn.getresponse().status == 200
    conn.close()
    httpd.shutdown()
    httpd.server_close()
    thread.join()


def test_a_folder_that_is_not_a_built_site_is_refused(tmp_path):
    with pytest.raises(server.ServeError, match="index.html"):
        server.make_server(tmp_path, "127.0.0.1", 0)


def test_serve_reports_a_missing_site_and_a_taken_port(tmp_path, site, capsys):
    assert main(["serve", str(tmp_path / "none")]) == 2
    assert "srstudio serve:" in capsys.readouterr().err
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        assert main(["serve", str(site), "--port", str(taken.getsockname()[1])]) == 2
    assert "srstudio serve:" in capsys.readouterr().err


def test_serve_runs_until_interrupted_and_warns_off_loopback(site, capsys, monkeypatch):
    calls = []

    class Server:
        server_address = ("0.0.0.0", 8765)

        def serve_forever(self):
            calls.append("served")
            raise KeyboardInterrupt

        def server_close(self):
            calls.append("closed")

    monkeypatch.setattr(server, "make_server", lambda root, host, port: calls.append((host, port)) or Server())
    assert main(["serve", str(site)]) == 0
    assert calls == [("127.0.0.1", 8765), "served", "closed"]  # the default bind is loopback
    assert "no authentication" not in capsys.readouterr().err
    assert main(["serve", str(site), "--host", "0.0.0.0", "--port", "9"]) == 0
    assert "no authentication" in capsys.readouterr().err


def test_the_default_bind_is_loopback():
    assert server.HOST == "127.0.0.1" and server.PORT == 8765
