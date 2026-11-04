"""The ledger of the show's numbers: who holds which number, kept where every batch's session reads it (ADR 0074).

A number is burned into the picture, so it has to be known before a reel's final render. It is claimed then, once, and
kept for good: the release carries it in git, and this ledger keeps two sessions building at once from taking the same
one. ``base`` is the count of reels ahead of the first numbered one, a fact only the publishing side holds, so nothing
is claimed until someone has set it; a series has its own. A reel dropped after its claim leaves a gap: a number is
never reused once it is on the feed, because a gap there costs less than two reels with one number. A claim on a reel
that was never delivered is not a used number, and :func:`release_claim` gives it back (ADR 0080).

A claim can also name the ``brief`` the reel was made to, which the posting job reads beside its number (ADR 0080),
the ``post_by`` day a timely reel is due, which sends it ahead of the number order, and the ``not_before`` day it may
first post.

A series has a display name, as a cover says it (``Saga``, ``Juno & Pip``), and a stable slug, as ``episode.json`` says
it (``saga``, ``juno-and-pip``; :func:`series_slug`). The ledger keeps a one-word series under its name, as it always
has, and a longer one under its slug (:func:`series_key`), so the published records keep their keys (ADR 0233). A claim
taken before its series was known gets its place with :func:`place`, until the reel is delivered.

The ledger is a file under ``generated/``: JSON of a fixed schema, read strictly, written whole under a lock.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import tempfile
from collections.abc import Collection, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import date
from pathlib import Path
from typing import Any, TypedDict

from .errors import SrstudioError

__all__ = [
    "FILE",
    "SCHEMA",
    "Claim",
    "EpisodeDocument",
    "Ledger",
    "NumberError",
    "claim",
    "episode_document",
    "ledger_path",
    "place",
    "read",
    "release_claim",
    "series_key",
    "series_slug",
    "set_base",
]

FILE = "numbers.json"
SCHEMA = "1.3.0"  # 1.1.0 added a reel's optional brief, 1.2.0 its optional post_by, 1.3.0 its optional not_before
_READS = ("1.0.0", "1.1.0", "1.2.0", SCHEMA)
_LOCK = ".numbers.lock"
_SERIES = re.compile(r"[A-Z][a-z]+")  # one capitalised word, as a cover names it and the ledger has always kept it
_NAME = re.compile(r"[A-Z][a-z]+(?:(?: &)? [A-Z][a-z]+)*")  # capitalised words, an & between two: Saga, Juno & Pip
_SLUG = re.compile(r"[a-z]+(?:-[a-z]+)+")  # a longer series as the ledger keeps it: juno-and-pip
_BRIEF = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")  # lower-case words joined by hyphens, as send-v1
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}")  # date.fromisoformat alone also reads 20261102
_OPTIONAL = frozenset({"series", "series_number", "brief", "post_by", "not_before"})


class NumberError(SrstudioError, ValueError):
    """A ledger that cannot be trusted, or a claim or a base it refuses."""


@dataclass(frozen=True)
class Claim:
    """The number reel ``slug`` holds on the account, its place in ``series`` when it has one, the ``brief`` it was
    made to when it names one, the ``post_by`` day it is due when it is timely, and the ``not_before`` day it may first
    post."""

    number: int
    series: str = ""
    series_number: int = 0
    brief: str = ""
    post_by: str = ""
    not_before: str = ""


class _Brief(TypedDict, total=False):
    brief: str
    post_by: str
    not_before: str


class EpisodeDocument(_Brief):
    """``episode.json``, beside a numbered video: what the posting job reads, the three required fields on every reel.
    ``series`` is the series' slug (:func:`series_slug`), empty for a reel in no series, whose ``series_number`` is 0.
    ``brief`` is there only when the reel names one, and ``post_by`` and ``not_before`` only on a timely reel, so a
    reel without them keeps the document it always had."""

    number: int
    series: str
    series_number: int


def series_slug(name: str) -> str:
    """The stable slug of the series a cover names ``name``: ``Saga`` is ``saga``, ``Juno & Pip`` is ``juno-and-pip``.
    A name that is not capitalised words, with at most an ``&`` between two of them, is a :class:`NumberError`."""
    if not isinstance(name, str) or not _NAME.fullmatch(name):
        raise NumberError(f"series {name!r} must be capitalised words, as Saga or Juno & Pip")
    return "-".join("and" if word == "&" else word.lower() for word in name.split(" "))


def series_key(name: str) -> str:
    """What the ledger keeps for the series named ``name``: a one-word series its name, as it always has (``Saga``),
    and a longer one its slug (``juno-and-pip``), so no published record changes its key."""
    slug = series_slug(name)
    return name if _SERIES.fullmatch(name) else slug


def _document_series(key: str) -> str:
    """The slug ``episode.json`` carries for the series the ledger keeps as ``key``."""
    if _SERIES.fullmatch(key):
        return key.lower()
    if _SLUG.fullmatch(key):
        return key
    raise NumberError(f"series {key!r} is neither one capitalised word, as Saga, nor a slug, as juno-and-pip")


def _check_brief(brief: str) -> str:
    if not _BRIEF.fullmatch(brief):
        raise NumberError(f"brief {brief!r} must be lower-case words joined by hyphens, as send-v1")
    return brief


def _check_day(name: str, day: str) -> str:
    try:
        if not _DAY.fullmatch(day):
            raise ValueError
        date.fromisoformat(day)
    except ValueError:
        raise NumberError(f"{name} {day!r} must be a day, as 2026-11-02") from None
    return day


def _check_window(post_by: str, not_before: str) -> None:
    if post_by and not_before and not_before > post_by:
        raise NumberError(f"not_before {not_before} falls after post_by {post_by}")


def episode_document(claim: Claim) -> EpisodeDocument:
    """The posting job's document of ``claim``; a claim outside that contract is a :class:`NumberError`."""
    if type(claim.number) is not int or claim.number < 1:
        raise NumberError(f"a reel's number is a whole number from 1, got {claim.number!r}")
    named = bool(claim.series)
    if named != (claim.series_number != 0):
        raise NumberError(f"series {claim.series!r} and series_number {claim.series_number!r} go together")
    if type(claim.series_number) is not int or claim.series_number < 0:
        raise NumberError(f"series_number must be a whole number, got {claim.series_number!r}")
    document: EpisodeDocument = {
        "number": claim.number,
        "series": _document_series(claim.series) if named else "",
        "series_number": claim.series_number,
    }
    if claim.brief:
        document["brief"] = _check_brief(claim.brief)
    if claim.post_by:
        document["post_by"] = _check_day("post_by", claim.post_by)
    if claim.not_before:
        document["not_before"] = _check_day("not_before", claim.not_before)
    _check_window(claim.post_by, claim.not_before)
    return document


@dataclass(frozen=True)
class Ledger:
    base: int | None = None
    series: Mapping[str, int] = field(default_factory=dict)  # each series' base
    reels: Mapping[str, Claim] = field(default_factory=dict)  # slug -> its claim

    def __post_init__(self) -> None:
        if self.base is None and self.reels:
            raise NumberError("a ledger with claims needs its base")
        numbers = [c.number for c in self.reels.values()]
        if len(set(numbers)) != len(numbers):
            raise NumberError("two reels hold one number")
        if numbers and min(numbers) <= (self.base or 0):
            raise NumberError(f"a claim at or under the base {self.base}")
        places = [(c.series, c.series_number) for c in self.reels.values() if c.series]
        if len(set(places)) != len(places):
            raise NumberError("two reels hold one place in a series")
        for series, place in places:
            if series not in self.series or place <= self.series[series]:
                raise NumberError(f"{series} #{place} is not above that series' base")

    def next_number(self) -> int:
        """The number the next claim takes."""
        if self.base is None:
            raise NumberError(
                "the ledger has no base: set it once, with srstudio number base N, from the publishing side's count of "
                "original reels on the feed and queued ahead of the first numbered reel"
            )
        return max([self.base, *(c.number for c in self.reels.values())]) + 1

    def next_in(self, series: str) -> int:
        """The place the next episode of ``series`` takes."""
        if series not in self.series:
            raise NumberError(f"{series} has no base: set it with srstudio number base N --series {series}")
        held = (c.series_number for c in self.reels.values() if c.series == series)
        return max([self.series[series], *held]) + 1


def ledger_path(renders: Path) -> Path:
    """The ledger beside ``renders``, so every worktree of one checkout reads the same file."""
    return Path(renders).resolve().parent / "okayville" / FILE


def _whole(value: object, what: str, least: int) -> int:
    if type(value) is not int or value < least:
        raise NumberError(f"{what} must be a whole number from {least}, got {value!r}")
    return value


def _fields(value: Any, where: str, required: set[str], optional: frozenset[str] = frozenset()) -> dict:
    if not isinstance(value, dict):
        raise NumberError(f"{where} is not an object")
    missing, unknown = required - set(value), set(value) - required - optional
    if missing or unknown:
        raise NumberError(f"{where}: missing {sorted(missing)}, unknown {sorted(unknown)}")
    return value


def _day_field(slug: str, row: Mapping[str, Any], name: str) -> str:
    if name not in row:
        return ""
    if not isinstance(row[name], str):
        raise NumberError(f"reel {slug}: {name} {row[name]!r} is not text")
    return _check_day(name, row[name])


def _claim(slug: str, value: Any) -> Claim:
    row = _fields(value, f"reel {slug}", {"number"}, _OPTIONAL)
    series, place = row.get("series", ""), row.get("series_number", 0)
    if not isinstance(series, str) or bool(series) != (place != 0):
        raise NumberError(f"reel {slug}: series {series!r} and series_number {place!r} go together")
    brief = ""
    if "brief" in row:
        if not isinstance(row["brief"], str):
            raise NumberError(f"reel {slug}: brief {row['brief']!r} is not text")
        brief = _check_brief(row["brief"])
    post_by, not_before = _day_field(slug, row, "post_by"), _day_field(slug, row, "not_before")
    _check_window(post_by, not_before)
    number = _whole(row["number"], f"reel {slug}'s number", 1)
    return Claim(number, series, _whole(place, f"reel {slug}'s place", 0), brief, post_by, not_before)


def read(path: Path) -> Ledger:
    """The ledger at ``path``, or an empty one when it was never written. A ledger that does not parse, or that says
    anything this schema does not, is a :class:`NumberError`: a duplicate number must not pass as a fresh start."""
    path = Path(path)
    if not path.exists():
        return Ledger()
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise NumberError(f"{path} cannot be read: {e}") from None
    row = _fields(document, str(path), {"schema", "base", "series", "reels"})
    if row["schema"] not in _READS:
        raise NumberError(f"{path}: schema {row['schema']!r}, this srstudio reads {', '.join(_READS)}")
    base = None if row["base"] is None else _whole(row["base"], "base", 0)
    if not isinstance(row["series"], dict) or not isinstance(row["reels"], dict):
        raise NumberError(f"{path}: series and reels are objects")
    series = {str(k): _whole(v, f"{k}'s base", 0) for k, v in row["series"].items()}
    reels = {str(k): _claim(k, v) for k, v in row["reels"].items()}
    return Ledger(base, series, reels)


def _write(path: Path, ledger: Ledger) -> None:
    rows: dict[str, dict[str, int | str]] = {}
    for slug, c in sorted(ledger.reels.items(), key=lambda kv: kv[1].number):
        rows[slug] = {
            "number": c.number,
            **({"series": c.series, "series_number": c.series_number} if c.series else {}),
            **({"brief": c.brief} if c.brief else {}),
            **({"post_by": c.post_by} if c.post_by else {}),
            **({"not_before": c.not_before} if c.not_before else {}),
        }
    text = json.dumps({"schema": SCHEMA, "base": ledger.base, "series": dict(ledger.series), "reels": rows}, indent=2)
    done, name = tempfile.mkstemp(prefix=f".{FILE}-", dir=path.parent)  # mode 600
    with os.fdopen(done, "w", encoding="utf-8") as out:
        out.write(text + "\n")
    Path(name).replace(path)


@contextmanager
def _locked(path: Path) -> Iterator[Ledger]:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (path.parent / _LOCK).open("a") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        yield read(path)


def set_base(path: Path, base: int, series: str = "") -> Ledger:
    """Set the count ahead of the first number, or of ``series``' first. It is a fact and moves no claim: a base is
    refused once anything was claimed on it."""
    _whole(base, "base", 0)
    series = series_key(series) if series else ""
    path = Path(path)
    with _locked(path) as ledger:
        if series:
            if any(c.series == series for c in ledger.reels.values()):
                raise NumberError(f"{series} already has claims on its base {ledger.series[series]}")
            new = replace(ledger, series={**ledger.series, series: base})
        else:
            if ledger.reels:
                raise NumberError(f"the ledger already has claims on its base {ledger.base}")
            new = replace(ledger, base=base)
        _write(path, new)
        return new


def claim(path: Path, slug: str, series: str = "", brief: str = "", post_by: str = "", not_before: str = "") -> Claim:
    """The number of reel ``slug``, taken the first time and the same one every time after. Asking for another series
    than the one claimed is refused: the first would stay on its render. So is another ``brief``; asked with none, a
    claim answers with the one it holds. ``post_by`` sets the day a timely reel is due and ``not_before`` the first day
    it may post, on a new claim or a held one, and the second may not fall after the first. ``series`` is the name a
    cover gives it, as Saga or Juno & Pip."""
    path = Path(path)
    series = series_key(series) if series else ""
    if brief:
        _check_brief(brief)
    if post_by:
        _check_day("post_by", post_by)
    if not_before:
        _check_day("not_before", not_before)
    _check_window(post_by, not_before)
    with _locked(path) as ledger:
        held = ledger.reels.get(slug)
        if held is not None:
            if held.series != series:
                raise NumberError(f"{slug} holds #{held.number} in series {held.series!r}, not {series!r}")
            if brief and held.brief != brief:
                raise NumberError(f"{slug} holds #{held.number} on brief {held.brief!r}, not {brief!r}")
            dated = replace(held, post_by=post_by or held.post_by, not_before=not_before or held.not_before)
            _check_window(dated.post_by, dated.not_before)
            if dated == held:
                return held
            _write(path, replace(ledger, reels={**ledger.reels, slug: dated}))
            return dated
        new = Claim(ledger.next_number(), series, ledger.next_in(series) if series else 0, brief, post_by, not_before)
        _write(path, replace(ledger, reels={**ledger.reels, slug: new}))
        return new


def release_claim(path: Path, slug: str, delivered: Collection[str]) -> Claim:
    """Give back the claim of reel ``slug`` and return what it held, for a reel never delivered: an unposted claim is
    not a used number. ``delivered`` is every reel known to have gone out; one of those keeps its number for good. The
    next claim counts from the highest number still held, so a number given back under a later claim stays a gap."""
    path = Path(path)
    if slug in delivered:
        raise NumberError(f"{slug} was delivered, so its number is used and stays")
    with _locked(path) as ledger:
        held = ledger.reels.get(slug)
        if held is None:
            raise NumberError(f"{slug} has no claim to release")
        _write(path, replace(ledger, reels={k: v for k, v in ledger.reels.items() if k != slug}))
        return held


def place(path: Path, slug: str, series: str, series_number: int, delivered: Collection[str]) -> Claim:
    """Give reel ``slug``, claimed in no series, its place ``series_number`` in the series named ``series`` (as Juno &
    Pip), and return its claim: a reel is claimed before its show is settled, and its place is part of what its cover
    says. Asked again with the same place, it answers with the claim. A reel already in a series, one in ``delivered``
    (its cover went out without the place), a place taken or at or under the series' base, and a series with no base
    are refused, and the number never moves."""
    key = series_key(series)
    _whole(series_number, "series_number", 1)
    path = Path(path)
    with _locked(path) as ledger:
        held = ledger.reels.get(slug)
        if held is None:
            raise NumberError(f"{slug} has no claim: claim its number first, with srstudio number claim {slug}")
        if (held.series, held.series_number) == (key, series_number):
            return held
        if held.series:
            raise NumberError(f"{slug} holds #{held.number} as {held.series} #{held.series_number} already")
        if slug in delivered:
            raise NumberError(f"{slug} was delivered without a series, so its cover stays as it went out")
        if key not in ledger.series:
            raise NumberError(f"{key} has no base: set it with srstudio number base N --series {series!r}")
        if series_number <= ledger.series[key]:
            raise NumberError(f"{key} #{series_number} is at or under the series' base, {ledger.series[key]}")
        taken = [s for s, c in ledger.reels.items() if (c.series, c.series_number) == (key, series_number)]
        if taken:
            raise NumberError(f"{key} #{series_number} is held by {taken[0]}")
        new = replace(held, series=key, series_number=series_number)
        _write(path, replace(ledger, reels={**ledger.reels, slug: new}))
        return new
