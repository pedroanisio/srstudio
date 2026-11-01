"""The ledger of the show's numbers (ADR 0074)."""

import json
import multiprocessing
import stat

import pytest

from srstudio import show_numbers
from srstudio.cli import main
from srstudio.show_numbers import Claim, NumberError, claim, ledger_path, read, set_base


@pytest.fixture
def path(tmp_path):
    return tmp_path / "okayville" / "numbers.json"


def write(path, **kw):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema": "1.0.0", "base": 10, "series": {}, "reels": {}, **kw}))


def test_nothing_is_claimed_until_someone_has_set_the_count(path):
    with pytest.raises(NumberError, match="no base"):
        claim(path, "first-reel")


def test_the_first_number_follows_the_count_and_the_next_follows_it(path):
    set_base(path, 200)
    assert claim(path, "first-reel").number == 201
    assert claim(path, "second-reel").number == 202


def test_a_claim_holds_its_number(path):
    set_base(path, 200)
    assert claim(path, "first-reel") == claim(path, "first-reel")
    claim(path, "second-reel")
    assert claim(path, "first-reel").number == 201


def test_a_dropped_number_stays_a_gap(path):
    set_base(path, 200)
    claim(path, "first-reel")
    claim(path, "second-reel")
    write(path, base=200, reels={"second-reel": {"number": 202}})
    assert claim(path, "third-reel").number == 203


def test_a_series_counts_on_its_own(path):
    set_base(path, 200)
    set_base(path, 18, series="Saga")
    assert claim(path, "plain-reel") == Claim(201)
    assert claim(path, "saga-one", series="Saga") == Claim(202, "Saga", 19)
    assert claim(path, "saga-two", series="Saga") == Claim(203, "Saga", 20)


def test_a_series_nobody_counted_is_refused(path):
    set_base(path, 200)
    with pytest.raises(NumberError, match="Saga has no base"):
        claim(path, "saga-one", series="Saga")
    assert read(path).reels == {}


def test_a_claim_cannot_move_to_another_series(path):
    set_base(path, 200)
    set_base(path, 18, series="Saga")
    claim(path, "plain-reel")
    with pytest.raises(NumberError, match="holds #201"):
        claim(path, "plain-reel", series="Saga")


def test_a_base_with_claims_on_it_cannot_move(path):
    set_base(path, 200)
    set_base(path, 18, series="Saga")
    claim(path, "saga-one", series="Saga")
    with pytest.raises(NumberError, match="already has claims"):
        set_base(path, 300)
    with pytest.raises(NumberError, match="already has claims"):
        set_base(path, 30, series="Saga")


def test_a_base_nobody_used_yet_can_be_corrected(path):
    set_base(path, 200)
    assert set_base(path, 205).base == 205


@pytest.mark.parametrize("bad", [-1, 1.5, True, "12"])
def test_a_base_that_is_no_count_is_refused(path, bad):
    with pytest.raises(NumberError, match="base"):
        set_base(path, bad)


def test_no_ledger_reads_as_empty(path):
    assert read(path) == show_numbers.Ledger()


def test_the_ledger_is_private(path):
    set_base(path, 1)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700


def test_the_ledger_sits_beside_the_renders(tmp_path):
    assert ledger_path(tmp_path / "renders") == tmp_path / "okayville" / "numbers.json"


@pytest.mark.parametrize(
    "document",
    [
        "not json",
        "[]",
        '{"schema": "9.0.0", "base": 1, "series": {}, "reels": {}}',
        '{"schema": "1.0.0", "base": 1, "series": {}}',
        '{"schema": "1.0.0", "base": 1, "series": {}, "reels": {}, "extra": 1}',
        '{"schema": "1.0.0", "base": "1", "series": {}, "reels": {}}',
        '{"schema": "1.0.0", "base": 1, "series": [], "reels": {}}',
        '{"schema": "1.0.0", "base": 1, "series": {}, "reels": {"a": {"number": true}}}',
        '{"schema": "1.0.0", "base": 1, "series": {}, "reels": {"a": {"number": 2, "colour": 1}}}',
        '{"schema": "1.0.0", "base": 1, "series": {}, "reels": {"a": {"number": 2}, "b": {"number": 2}}}',
        '{"schema": "1.0.0", "base": 5, "series": {}, "reels": {"a": {"number": 2}}}',
        '{"schema": "1.0.0", "base": null, "series": {}, "reels": {"a": {"number": 2}}}',
        '{"schema": "1.0.0", "base": 1, "series": {}, "reels": {"a": {"number": 2, "series": "Saga"}}}',
        '{"schema": "1.0.0", "base": 1, "series": {}, "reels": {"a": {"number": 2, "series": "Saga", '
        '"series_number": 1}}}',
        '{"schema": "1.0.0", "base": 1, "series": {"Saga": 0}, "reels": {"a": {"number": 2, "series": "Saga", '
        '"series_number": 1}, "b": {"number": 3, "series": "Saga", "series_number": 1}}}',
    ],
)
def test_a_ledger_that_cannot_be_trusted_is_refused_and_not_read_as_a_fresh_start(path, document):
    path.parent.mkdir(parents=True)
    path.write_text(document)
    with pytest.raises(NumberError):
        read(path)


def _claims(path, names, out):
    out.extend([claim(path, name).number for name in names])


def test_two_sessions_at_once_never_take_one_number(path):
    set_base(path, 0)
    context = multiprocessing.get_context("fork")
    with context.Manager() as manager:
        numbers = manager.list()
        workers = [
            context.Process(target=_claims, args=(path, [f"{who}-{i}" for i in range(20)], numbers))
            for who in ("left", "right", "other")
        ]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
        assert sorted(numbers) == list(range(1, 61))


def test_the_command_line_sets_claims_and_lists(path, capsys):
    ledger = ["--ledger", str(path)]
    assert main(["number", "claim", "first-reel", *ledger]) == 2
    assert "no base" in capsys.readouterr().err
    assert main(["number", "base", "200", *ledger]) == 0
    assert main(["number", "base", "18", "--series", "Saga", *ledger]) == 0
    capsys.readouterr()
    assert main(["number", "claim", "first-reel", *ledger]) == 0
    assert main(["number", "claim", "saga-one", "--series", "Saga", *ledger]) == 0
    assert capsys.readouterr().out.split("\n")[:2] == ["first-reel #201", "saga-one #202 Saga #19"]
    assert main(["number", "list", *ledger]) == 0
    said = capsys.readouterr().out
    assert "base 200" in said and "Saga base 18" in said and "first-reel #201" in said
