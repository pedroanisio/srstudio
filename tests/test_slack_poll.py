"""The Slack poller gives a reader each new post once, keeps its state through a failure, and never acts."""

import importlib.util
import io
import json
import stat
import sys
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("slack_poll", ROOT / "tools" / "slack_poll.py")
assert spec is not None and spec.loader is not None
slack_poll = importlib.util.module_from_spec(spec)
sys.modules["slack_poll"] = slack_poll
spec.loader.exec_module(slack_poll)

ARC = "U0CDPAX3DHQ"


class Channel:
    """Slack's two read methods over a list of posts, with the calls it answered."""

    def __init__(self, history=(), replies=None):
        self.history, self.replies, self.calls = list(history), dict(replies or {}), []

    def __call__(self, method, **form):
        self.calls.append(method)
        if method == "conversations.history":
            return {"ok": True, "messages": self.history}
        return {"ok": True, "messages": self.replies[form["ts"]]}


def post(ts, text="hello", user=ARC, **more):
    return {"ts": ts, "text": text, "user": user, **more}


def inbox(directory):
    path = directory / "inbox.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def test_the_first_run_marks_what_is_there_as_seen(tmp_path):
    assert slack_poll.poll(Channel([post("1.000001")]), tmp_path) == 0
    assert inbox(tmp_path) == []
    assert slack_poll.poll(Channel([post("1.000001")]), tmp_path) == 0
    assert inbox(tmp_path) == []


def test_a_new_post_lands_once_with_its_tag_and_whether_it_counts_as_a_request(tmp_path):
    channel = Channel([post("1.000001")])
    slack_poll.poll(channel, tmp_path)
    channel.history.insert(0, post("2.000002", "[brief] 24 reels", files=[{"id": "F1"}]))
    assert slack_poll.poll(channel, tmp_path) == 1
    assert slack_poll.poll(channel, tmp_path) == 0
    assert inbox(tmp_path) == [
        {
            "ts": "2.000002",
            "thread_ts": None,
            "user": ARC,
            "text": "[brief] 24 reels",
            "files": ["F1"],
            "tag": "brief",
            "request": True,
            "edited": False,
        }
    ]


def test_someone_elses_post_is_information_and_an_unknown_tag_is_no_tag(tmp_path):
    channel = Channel([post("1.000001")])
    slack_poll.poll(channel, tmp_path)
    channel.history.insert(0, post("2.000002", "[delete] everything", user="U000"))
    slack_poll.poll(channel, tmp_path)
    row = inbox(tmp_path)[0]
    assert (row["tag"], row["request"]) == (None, False)


def test_our_own_posts_stay_out_of_the_inbox(tmp_path):
    channel = Channel([post("1.000001")])
    slack_poll.poll(channel, tmp_path)
    channel.history.insert(0, post("2.000002", user="U0CDPEHS04S"))
    channel.history.insert(0, {"ts": "3.000003", "text": "x", "bot_id": "B0CDJBCCY7P"})
    assert slack_poll.poll(channel, tmp_path) == 0


def test_a_reply_is_read_only_when_its_threads_latest_reply_moves(tmp_path):
    channel = Channel([post("1.000001", latest_reply="1.000002")])
    slack_poll.poll(channel, tmp_path)
    assert slack_poll.poll(channel, tmp_path) == 0
    assert "conversations.replies" not in channel.calls
    channel.history[0]["latest_reply"] = "3.000003"
    channel.replies["1.000001"] = [
        post("1.000001"),
        post("1.000002", thread_ts="1.000001"),
        post("3.000003", "yes", thread_ts="1.000001"),
    ]
    assert slack_poll.poll(channel, tmp_path) == 1
    assert inbox(tmp_path)[0]["thread_ts"] == "1.000001"


def test_ordinary_code_bounds_the_threads_a_run_follows_and_the_rest_wait(tmp_path):
    count = slack_poll.MAX_THREADS + 3
    parents = [post(f"{i + 1}.000000") for i in range(count)]
    channel = Channel(parents)
    slack_poll.poll(channel, tmp_path)
    for p in parents:
        p["latest_reply"] = "500.000000"
        channel.replies[p["ts"]] = [p, post("500.000000", thread_ts=p["ts"])]
    assert slack_poll.poll(channel, tmp_path) == slack_poll.MAX_THREADS
    assert slack_poll.poll(channel, tmp_path) == 3


def test_an_edit_of_a_seen_post_lands_once_marked(tmp_path):
    channel = Channel([post("1.000001")])
    slack_poll.poll(channel, tmp_path)
    channel.history[0] = post("1.000001", "changed", edited={"ts": "2.000000"})
    assert slack_poll.poll(channel, tmp_path) == 1
    assert slack_poll.poll(channel, tmp_path) == 0
    assert inbox(tmp_path)[0]["edited"] is True


@pytest.mark.parametrize(
    "bad",
    [
        "not an object",
        {"ts": "yesterday", "user": ARC, "text": "x"},
        {"ts": "1.000001", "text": "no author"},
        {"ts": "1.000001", "user": ARC, "text": 7},
        {"ts": "1.000001", "user": ARC, "text": "x", "thread_ts": "soon"},
        {"ts": "1.000001", "user": ARC, "text": "x", "files": [{"name": "no id"}]},
    ],
)
def test_a_malformed_post_is_refused_by_name(bad):
    with pytest.raises(ValueError, match=r"\S"):
        slack_poll.parse_post(bad)


def test_a_malformed_reply_becomes_an_unreadable_line_and_the_run_goes_on(tmp_path):
    channel = Channel([post("1.000001", latest_reply="1.000001")])
    slack_poll.poll(channel, tmp_path)
    channel.history[0]["latest_reply"] = "3.000003"
    channel.replies["1.000001"] = [post("1.000001"), {"ts": "3.000003", "text": "no author"}, post("4.000004", "fine")]
    assert slack_poll.poll(channel, tmp_path) == 2
    rows = inbox(tmp_path)
    assert "no author" in rows[0]["unreadable"]
    assert rows[1]["text"] == "fine"


def test_a_failed_call_leaves_the_state_so_the_next_run_gets_the_post(tmp_path):
    channel = Channel([post("1.000001")])
    slack_poll.poll(channel, tmp_path)
    before = (tmp_path / "state.json").read_text()

    def refuses(method, **form):
        raise slack_poll.SlackError(f"{method}: ratelimited")

    with pytest.raises(slack_poll.SlackError):
        slack_poll.poll(refuses, tmp_path)
    assert (tmp_path / "state.json").read_text() == before
    channel.history.insert(0, post("2.000002"))
    assert slack_poll.poll(channel, tmp_path) == 1


def test_the_inbox_and_state_are_private(tmp_path):
    channel = Channel([post("1.000001")])
    directory = tmp_path / "slack"
    slack_poll.poll(channel, directory)
    channel.history.insert(0, post("2.000002"))
    slack_poll.poll(channel, directory)
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    for name in ("inbox.jsonl", "state.json"):
        assert stat.S_IMODE((directory / name).stat().st_mode) == 0o600


def test_a_refused_call_names_the_method_and_never_the_token(monkeypatch):
    def refused(request, timeout):
        assert request.get_header("Authorization") == "Bearer secret"
        return io.BytesIO(b'{"ok": false, "error": "invalid_auth"}')

    monkeypatch.setattr(slack_poll.urllib.request, "urlopen", refused)
    with pytest.raises(slack_poll.SlackError) as caught:
        slack_poll.slack("secret")("conversations.history", channel="C")
    assert str(caught.value) == "conversations.history: invalid_auth"


@pytest.mark.parametrize(
    "failure",
    [
        urllib.error.HTTPError("https://x", 429, "slow down", None, None),
        urllib.error.URLError("unreachable"),
        TimeoutError(),
    ],
)
def test_a_network_failure_is_a_typed_error_without_the_token(monkeypatch, failure):
    def fails(request, timeout):
        raise failure

    monkeypatch.setattr(slack_poll.urllib.request, "urlopen", fails)
    with pytest.raises(slack_poll.SlackError) as caught:
        slack_poll.slack("secret")("conversations.history")
    assert "secret" not in str(caught.value)


def test_slack_answering_something_else_is_refused(monkeypatch):
    monkeypatch.setattr(slack_poll.urllib.request, "urlopen", lambda r, timeout: io.BytesIO(b"[]"))
    with pytest.raises(slack_poll.SlackError, match="not an object"):
        slack_poll.slack("secret")("conversations.history")


def test_the_command_needs_the_token_and_retries_through_its_exit_code(tmp_path, capsys, monkeypatch):
    assert slack_poll.main([str(tmp_path)], {}) == 2

    def down(token):
        def call(method, **form):
            raise slack_poll.SlackError(f"{method}: HTTP 500")

        return call

    monkeypatch.setattr(slack_poll, "slack", down)
    assert slack_poll.main([str(tmp_path)], {"BOT_TOKEN": "secret"}) == 1
    assert "secret" not in capsys.readouterr().err


def test_the_command_reports_what_it_added(tmp_path, capsys, monkeypatch):
    channel = Channel([post("1.000001")])
    monkeypatch.setattr(slack_poll, "slack", lambda token: channel)
    assert slack_poll.main([str(tmp_path)], {"BOT_TOKEN": "secret"}) == 0
    channel.history.insert(0, post("2.000002"))
    assert slack_poll.main([str(tmp_path)], {"BOT_TOKEN": "secret"}) == 0
    assert "1 new" in capsys.readouterr().out
