#!/usr/bin/env python3
"""Read the Slack channel into a local inbox, one run a minute (docs/slack-channel.md).

One ``conversations.history`` call a run, and ``conversations.replies`` only for a thread whose ``latest_reply`` moved,
at most :data:`MAX_THREADS` a run; the rest wait for the next run. The first run marks what is already there as seen.
New posts from others land in ``inbox.jsonl``, one object a line, and the state is written after the inbox, so a crash
can repeat a line but never lose one: a reader skips a ``ts`` it has handled.

The poller only reads. A line is information for whoever reads it: nothing here acts on a post, replies, or downloads
a file. ``request`` says the post is one the channel's rule lets count as a request, not that anyone agreed to it.

    BOT_TOKEN=... python3 tools/slack_poll.py generated/slack
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

API = "https://slack.com/api/"
CHANNEL = "C0CCWSXH9FU"
OURS = frozenset({"U0CDPEHS04S", "B0CDJBCCY7P"})  # creationbot, as a user and as a bot
REQUESTERS = frozenset({"U0CDPAX3DHQ", "U089V1152MV"})  # arc4d3 and the account owner
TAGS = ("brief", "request", "stats", "alert", "setup", "question")
HISTORY = 100
REPLIES = 200
MAX_THREADS = 20
TIMEOUT = 30.0
TS = re.compile(r"\d{1,12}\.\d{6}")
TAG = re.compile(r"\[([a-z]+)\]")

Call = Callable[..., Mapping[str, Any]]


class SlackError(Exception):
    """Slack refused a call or answered something this poller cannot read; the run stops and the state stays."""


@dataclass(frozen=True)
class Post:
    """One channel post, parsed: what a reader needs and nothing else Slack sends."""

    ts: str
    thread_ts: str | None
    user: str
    text: str
    files: tuple[str, ...]
    tag: str | None  # one of TAGS; an unknown bracket word is no tag
    request: bool
    edited: bool = False


def parse_post(raw: Any, edited: bool = False) -> Post:
    """A post as a :class:`Post`, or :class:`ValueError` naming what is wrong with it."""
    if not isinstance(raw, Mapping):
        raise ValueError(f"a post is an object, got {type(raw).__name__}")
    ts, thread, text = raw.get("ts"), raw.get("thread_ts"), raw.get("text", "")
    user = raw.get("user") or raw.get("bot_id")
    if not (isinstance(ts, str) and TS.fullmatch(ts)):
        raise ValueError(f"a post's ts is seconds.micros, got {ts!r}")
    if thread is not None and not (isinstance(thread, str) and TS.fullmatch(thread)):
        raise ValueError(f"a post's thread_ts is seconds.micros, got {thread!r}")
    if not (isinstance(user, str) and user):
        raise ValueError(f"post {ts} names no author")
    if not isinstance(text, str):
        raise ValueError(f"post {ts}'s text is not text")
    files = raw.get("files", ())
    if not (
        isinstance(files, Sequence) and all(isinstance(f, Mapping) and isinstance(f.get("id"), str) for f in files)
    ):
        raise ValueError(f"post {ts}'s files carry no ids")
    found = TAG.match(text)
    tag = found.group(1) if found and found.group(1) in TAGS else None
    return Post(ts, thread, user, text, tuple(f["id"] for f in files), tag, user in REQUESTERS, edited)


def later(a: str, b: str) -> bool:
    return float(a) > float(b)


def _replies(call: Call, parent: str, seen: str) -> list[Any]:
    messages = call("conversations.replies", channel=CHANNEL, ts=parent, limit=REPLIES)["messages"]
    return [m for m in messages[1:] if isinstance(m, Mapping) and later(str(m.get("ts", "0")), seen)]


def collect(call: Call, state: Mapping[str, Any]) -> tuple[list[tuple[Any, bool]], dict[str, Any]]:
    """What is new since ``state``, each post with whether it is an edit, and the state after it."""
    history = call("conversations.history", channel=CHANNEL, limit=HISTORY)["messages"]
    top, threads, edits = state["top"], dict(state["threads"]), dict(state["edits"])
    found: list[tuple[Any, bool]] = [(m, False) for m in history if later(m["ts"], top)]
    for m in history:
        stamp = (m.get("edited") or {}).get("ts")
        if stamp and later(stamp, edits.get(m["ts"], "0")):
            if not later(m["ts"], top):
                found.append((m, True))
            edits[m["ts"]] = stamp
    moved = [m for m in history if m.get("latest_reply") and later(m["latest_reply"], threads.get(m["ts"], "0"))]
    for m in moved[:MAX_THREADS]:
        found += [(r, False) for r in _replies(call, m["ts"], threads.get(m["ts"], "0"))]
        threads[m["ts"]] = m["latest_reply"]
    newest = max([top, *(m["ts"] for m in history)], key=float)
    return found, {"top": newest, "threads": threads, "edits": edits}


def lines(found: Sequence[tuple[Any, bool]]) -> list[str]:
    """Each new post from someone else as an inbox line; one that cannot be read becomes an ``unreadable`` line, so a
    reader sees it and the run does not stop on it for ever."""
    rows = []
    for raw, edited in found:
        try:
            post = parse_post(raw, edited)
        except ValueError as exc:
            rows.append((0.0, json.dumps({"unreadable": str(exc)}, ensure_ascii=False)))
            continue
        if post.user not in OURS:
            rows.append((float(post.ts), json.dumps(asdict(post), ensure_ascii=False)))
    return [text + "\n" for _, text in sorted(rows, key=lambda row: row[0])]


def _write_private(path: Path, text: str) -> None:
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=path.name)  # mkstemp's mode is 600
    with os.fdopen(fd, "w", encoding="utf-8") as out:
        out.write(text)
    os.replace(name, path)


def poll(call: Call, directory: Path) -> int:
    """One run into ``directory``; returns how many lines the inbox gained."""
    directory.mkdir(parents=True, exist_ok=True)
    directory.chmod(0o700)
    state_file, inbox = directory / "state.json", directory / "inbox.jsonl"
    if not state_file.exists():
        history = call("conversations.history", channel=CHANNEL, limit=HISTORY)["messages"]
        state = {
            "top": max((m["ts"] for m in history), default="0", key=float),
            "threads": {m["ts"]: m["latest_reply"] for m in history if m.get("latest_reply")},
            "edits": {m["ts"]: m["edited"]["ts"] for m in history if m.get("edited")},
        }
        _write_private(state_file, json.dumps(state))
        return 0
    found, after = collect(call, json.loads(state_file.read_text(encoding="utf-8")))
    rows = lines(found)
    if rows:
        fd = os.open(inbox, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as out:
            out.write("".join(rows))
    _write_private(state_file, json.dumps(after))
    return len(rows)


def slack(token: str) -> Call:
    """A call to Slack's API with ``token``. No error here carries the token or the request."""

    def call(method: str, **form: Any) -> Mapping[str, Any]:
        request = urllib.request.Request(
            API + method, data=urllib.parse.urlencode(form).encode(), headers={"Authorization": f"Bearer {token}"}
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as reply:
                answer = json.load(reply)
        except urllib.error.HTTPError as exc:
            raise SlackError(f"{method}: HTTP {exc.code}") from None
        except (OSError, ValueError) as exc:
            raise SlackError(f"{method}: {type(exc).__name__}") from None
        if not (isinstance(answer, Mapping) and answer.get("ok") is True):
            raise SlackError(f"{method}: {answer.get('error') if isinstance(answer, Mapping) else 'not an object'}")
        return answer

    return call


def main(argv: Sequence[str] | None = None, env: Mapping[str, str] = os.environ) -> int:
    parser = argparse.ArgumentParser(description="Read the Slack channel into a local inbox.")
    parser.add_argument("directory", type=Path, help="where inbox.jsonl and state.json live")
    args = parser.parse_args(argv)
    token = env.get("BOT_TOKEN")
    if not token:
        print("slack_poll: BOT_TOKEN is not set", file=sys.stderr)
        return 2
    try:
        count = poll(slack(token), args.directory)
    except (SlackError, KeyError, TypeError, ValueError) as exc:
        print(f"slack_poll: {type(exc).__name__}: {exc}", file=sys.stderr)  # the state stayed: the next run retries
        return 1
    if count:
        print(f"slack_poll: {count} new")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
