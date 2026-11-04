"""The ledger of the show's numbers (ADR 0074)."""

import json
import multiprocessing
import stat

import pytest

from srstudio import show_numbers, social
from srstudio.cli import main
from srstudio.show_numbers import (
    Claim,
    EpisodeDocument,
    NumberError,
    claim,
    episode_document,
    ledger_path,
    place,
    read,
    release_claim,
    series_key,
    series_slug,
    set_base,
)


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
    try:
        out.send([claim(path, name).number for name in names])
    finally:
        out.close()


def test_two_sessions_at_once_never_take_one_number(path):
    set_base(path, 0)
    context = multiprocessing.get_context("fork")
    # One-way pipes use no listening socket or manager process. The ledger is still
    # claimed by three independent processes exercising its real file lock.
    pipes = [context.Pipe(duplex=False) for _ in range(3)]
    workers = [
        context.Process(target=_claims, args=(path, [f"{who}-{i}" for i in range(20)], sender))
        for who, (_, sender) in zip(("left", "right", "other"), pipes, strict=True)
    ]
    try:
        for worker, (_, sender) in zip(workers, pipes, strict=True):
            worker.start()
            sender.close()
        numbers = []
        for receiver, _ in pipes:
            assert receiver.poll(10), 'claim worker did not return its numbers'
            numbers.extend(receiver.recv())
        for worker in workers:
            worker.join(timeout=10)
            assert worker.exitcode == 0
        assert sorted(numbers) == list(range(1, 61))
        assert sorted(entry.number for entry in read(path).reels.values()) == sorted(numbers)
    finally:
        for worker in workers:
            if worker.is_alive():
                worker.terminate()
            if worker.pid is not None:
                worker.join(timeout=10)
        for receiver, sender in pipes:
            receiver.close()
            sender.close()


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


def test_the_publishing_side_s_counts_give_the_numbers_it_named(path):
    """arc4d3, Slack 1793501087.434969: first numbered reel #193, Saga next #19, Gloss next #10."""
    set_base(path, 192)
    set_base(path, 18, series="Saga")
    set_base(path, 9, series="Gloss")
    assert claim(path, "plain-reel") == Claim(193)
    assert claim(path, "saga-next", series="Saga") == Claim(194, "Saga", 19)
    assert claim(path, "gloss-next", series="Gloss") == Claim(195, "Gloss", 10)


@pytest.mark.parametrize(
    "series", ["saga", "SAGA", "Saga#", "juno-and-pip", "Juno &", "Juno  Pip", "& Pip", "Juno & pip"]
)
def test_a_series_is_named_as_its_cover_names_it(path, series):
    with pytest.raises(NumberError, match="capitalised"):
        set_base(path, 18, series=series)


@pytest.mark.parametrize(
    ("claimed", "document"),
    [
        (Claim(193), {"number": 193, "series": "", "series_number": 0}),
        (Claim(194, "Saga", 19), {"number": 194, "series": "saga", "series_number": 19}),
        (Claim(195, "Gloss", 10), {"number": 195, "series": "gloss", "series_number": 10}),
    ],
)
def test_the_episode_document_is_exactly_what_the_posting_job_reads(claimed, document):
    assert episode_document(claimed) == document
    assert list(episode_document(claimed)) == ["number", "series", "series_number"]
    assert EpisodeDocument.__required_keys__ == set(document)
    assert json.dumps(episode_document(Claim(193))) == '{"number": 193, "series": "", "series_number": 0}'


@pytest.mark.parametrize(
    "broken",
    [
        Claim(0),
        Claim(True),
        Claim(193, "Saga"),
        Claim(193, "", 4),
        Claim(193, "saga", 4),
        Claim(193, "Saga", -1),
        Claim(193, brief="Send-V1"),
    ],
)
def test_a_claim_outside_the_contract_writes_no_document(broken):
    with pytest.raises(NumberError):
        episode_document(broken)


# -- the brief a reel was made to (ADR 0080) ---------------------------------------------------------------------------
def test_a_brief_is_recorded_in_the_ledger_and_reaches_the_episode_document(path):
    set_base(path, 200)
    held = claim(path, "send-reel", brief="send-v1")
    assert held == Claim(201, brief="send-v1")
    assert json.loads(path.read_text())["reels"]["send-reel"] == {"number": 201, "brief": "send-v1"}
    assert read(path).reels["send-reel"] == held
    assert episode_document(held) == {"number": 201, "series": "", "series_number": 0, "brief": "send-v1"}


def test_a_series_reel_keeps_its_brief_after_its_place(path):
    set_base(path, 200)
    set_base(path, 18, series="Saga")
    assert json.dumps(episode_document(claim(path, "saga-one", series="Saga", brief="send-v1"))) == (
        '{"number": 201, "series": "saga", "series_number": 19, "brief": "send-v1"}'
    )


def test_a_reel_with_no_brief_keeps_todays_row_and_document(path):
    set_base(path, 200)
    held = claim(path, "plain-reel")
    assert json.loads(path.read_text())["reels"]["plain-reel"] == {"number": 201}
    assert list(episode_document(held)) == ["number", "series", "series_number"]


@pytest.mark.parametrize("brief", ["Send-v1", "send v1", "-send", "send-", "send--v1", "send_v1", "send/v1", " "])
def test_a_brief_that_is_no_slug_is_refused_and_claims_nothing(path, brief):
    set_base(path, 200)
    with pytest.raises(NumberError, match="brief"):
        claim(path, "send-reel", brief=brief)
    assert read(path).reels == {}


def test_a_ledger_written_before_briefs_still_reads_and_moves_up_on_the_next_write(path):
    write(path, schema="1.0.0", base=200, reels={"old-reel": {"number": 201}})
    assert read(path).reels == {"old-reel": Claim(201)}
    claim(path, "new-reel", brief="send-v1")
    document = json.loads(path.read_text())
    assert document["schema"] == show_numbers.SCHEMA == "1.3.0"
    assert document["reels"]["old-reel"] == {"number": 201}


# -- the day a timely reel is due ---------------------------------------------------------------------------
def test_a_due_day_is_recorded_and_reaches_the_episode_document(path):
    set_base(path, 200)
    held = claim(path, "clocks", post_by="2026-11-02")
    assert held == Claim(201, post_by="2026-11-02")
    assert json.loads(path.read_text())["reels"]["clocks"] == {"number": 201, "post_by": "2026-11-02"}
    assert read(path).reels["clocks"].post_by == "2026-11-02"
    assert episode_document(held) == {"number": 201, "series": "", "series_number": 0, "post_by": "2026-11-02"}


def test_a_held_claim_takes_a_due_day_later_and_keeps_its_number(path):
    set_base(path, 200)
    claim(path, "clocks", brief="send-v1")
    claim(path, "other")
    assert claim(path, "clocks", post_by="2026-11-02") == Claim(201, brief="send-v1", post_by="2026-11-02")
    assert claim(path, "clocks") == Claim(201, brief="send-v1", post_by="2026-11-02")
    assert read(path).reels["other"].number == 202


@pytest.mark.parametrize("day", ["tomorrow", "2026-13-01", "2026-02-30", "2026/11/02", "20261102", " 2026-11-02"])
def test_a_due_day_that_is_no_date_is_refused_and_claims_nothing(path, day):
    set_base(path, 200)
    with pytest.raises(NumberError, match="post_by"):
        claim(path, "clocks", post_by=day)
    assert "clocks" not in read(path).reels


def test_a_due_day_the_ledger_cannot_vouch_for_is_refused(path):
    write(path, schema="1.2.0", base=200, reels={"reel": {"number": 201, "post_by": "soon"}})
    with pytest.raises(NumberError, match="post_by"):
        read(path)


def test_a_first_day_is_recorded_and_reaches_the_episode_document(path):
    set_base(path, 200)
    held = claim(path, "clocks", post_by="2026-11-27", not_before="2026-11-20")
    assert held == Claim(201, post_by="2026-11-27", not_before="2026-11-20")
    assert json.loads(path.read_text())["reels"]["clocks"]["not_before"] == "2026-11-20"
    assert read(path).reels["clocks"].not_before == "2026-11-20"
    assert episode_document(held)["not_before"] == "2026-11-20"


def test_a_held_claim_takes_a_first_day_later_and_keeps_its_due_day(path):
    set_base(path, 200)
    claim(path, "clocks", post_by="2026-11-27")
    assert claim(path, "clocks", not_before="2026-11-20") == Claim(201, post_by="2026-11-27", not_before="2026-11-20")
    assert claim(path, "clocks") == Claim(201, post_by="2026-11-27", not_before="2026-11-20")


def test_a_reel_due_before_its_first_day_is_refused_and_claims_nothing(path):
    set_base(path, 200)
    with pytest.raises(NumberError, match="not_before"):
        claim(path, "clocks", post_by="2026-11-20", not_before="2026-11-27")
    assert "clocks" not in read(path).reels


def test_a_later_first_day_cannot_pass_the_due_day_a_held_claim_has(path):
    set_base(path, 200)
    claim(path, "clocks", post_by="2026-11-20")
    with pytest.raises(NumberError, match="not_before"):
        claim(path, "clocks", not_before="2026-11-27")
    assert read(path).reels["clocks"].not_before == ""


def test_a_first_day_that_is_no_date_is_refused(path):
    set_base(path, 200)
    with pytest.raises(NumberError, match="not_before"):
        claim(path, "clocks", not_before="soon")


def test_a_first_day_the_ledger_cannot_vouch_for_is_refused(path):
    write(path, schema="1.3.0", base=200, reels={"reel": {"number": 201, "not_before": "soon"}})
    with pytest.raises(NumberError, match="not_before"):
        read(path)


def test_a_ledger_holding_a_reel_due_before_its_first_day_is_refused(path):
    row = {"number": 201, "post_by": "2026-11-20", "not_before": "2026-11-27"}
    write(path, schema="1.3.0", base=200, reels={"reel": row})
    with pytest.raises(NumberError, match="not_before"):
        read(path)


def test_a_brief_the_ledger_cannot_vouch_for_is_refused(path):
    write(path, schema="1.1.0", base=200, reels={"reel": {"number": 201, "brief": "Not A Slug"}})
    with pytest.raises(NumberError, match="brief"):
        read(path)


def test_a_claim_answers_again_without_its_brief_but_cannot_change_it(path):
    set_base(path, 200)
    held = claim(path, "send-reel", brief="send-v1")
    assert claim(path, "send-reel") == held
    assert claim(path, "send-reel", brief="send-v1") == held
    with pytest.raises(NumberError, match="send-v1"):
        claim(path, "send-reel", brief="send-v2")


def test_a_brief_cannot_be_added_to_a_claim_made_without_one(path):
    set_base(path, 200)
    claim(path, "plain-reel")
    with pytest.raises(NumberError, match="holds #201"):
        claim(path, "plain-reel", brief="send-v1")


def test_the_command_line_claims_with_a_brief_and_lists_it(path, capsys):
    ledger = ["--ledger", str(path)]
    assert main(["number", "base", "200", *ledger]) == 0
    capsys.readouterr()
    assert main(["number", "claim", "send-reel", "--brief", "send-v1", *ledger]) == 0
    assert capsys.readouterr().out == "send-reel #201 send-v1\n"
    assert main(["number", "claim", "bad-reel", "--brief", "Send V1", *ledger]) == 2
    assert "brief" in capsys.readouterr().err


# -- giving a claim back (ADR 0080) ------------------------------------------------------------------------------------
def test_a_released_claim_is_gone_and_returns_what_it_held(path):
    set_base(path, 200)
    claim(path, "kept-reel")
    held = claim(path, "dropped-reel")
    assert release_claim(path, "dropped-reel", delivered=()) == held
    assert list(read(path).reels) == ["kept-reel"]


def test_the_last_number_given_back_is_taken_by_the_next_claim(path):
    set_base(path, 200)
    claim(path, "first-reel")
    claim(path, "second-reel")
    release_claim(path, "second-reel", delivered=())
    assert claim(path, "third-reel").number == 202


def test_a_number_given_back_below_a_later_claim_stays_a_gap(path):
    set_base(path, 200)
    claim(path, "first-reel")
    claim(path, "second-reel")
    release_claim(path, "first-reel", delivered=())
    assert claim(path, "third-reel").number == 203


def test_a_series_place_comes_back_with_its_number(path):
    set_base(path, 200)
    set_base(path, 18, series="Saga")
    claim(path, "saga-one", series="Saga")
    release_claim(path, "saga-one", delivered=())
    assert claim(path, "saga-two", series="Saga") == Claim(201, "Saga", 19)


def test_a_delivered_reel_keeps_its_claim(path):
    set_base(path, 200)
    held = claim(path, "out-reel")
    with pytest.raises(NumberError, match="out-reel.*delivered"):
        release_claim(path, "out-reel", delivered={"out-reel"})
    assert read(path).reels == {"out-reel": held}


def test_a_reel_with_no_claim_has_nothing_to_give_back(path):
    set_base(path, 200)
    with pytest.raises(NumberError, match="no claim"):
        release_claim(path, "never-reel", delivered=())


@pytest.fixture
def folders(path):
    """The delivery folder and the outbox where the command looks, beside the ledger."""
    root = path.parent.parent
    (root / "renders" / "ig").mkdir(parents=True)
    (root / "outbox").mkdir()
    return root / "renders" / "ig", root / "outbox"


def test_the_command_line_releases_a_claim_on_a_reel_never_delivered(path, folders, capsys):
    ledger = ["--ledger", str(path)]
    main(["number", "base", "200", *ledger])
    main(["number", "claim", "unposted-reel", *ledger])
    capsys.readouterr()
    assert main(["number", "release", "unposted-reel", *ledger]) == 0
    assert capsys.readouterr().out == "released unposted-reel #201\n"
    assert read(path).reels == {}


@pytest.mark.parametrize("seen", ["ig-folder", "ig-manifest", "outbox-folder"])
def test_the_command_line_refuses_a_reel_the_delivery_or_the_outbox_shows(path, folders, capsys, seen):
    deliveries, box = folders
    if seen == "ig-folder":
        (deliveries / "out-reel").mkdir()
    elif seen == "ig-manifest":
        (deliveries / "delivery.json").write_text(
            json.dumps(
                {
                    "version": social.MANIFEST_VERSION,
                    "videos": {"out-reel": dict.fromkeys(("render", "post", "ig", "cover"), "0" * 64)},
                }
            )
        )
    else:
        (box / "out-reel").mkdir()
    ledger = ["--ledger", str(path)]
    main(["number", "base", "200", *ledger])
    held = main(["number", "claim", "out-reel", *ledger])
    assert held == 0
    capsys.readouterr()
    assert main(["number", "release", "out-reel", *ledger]) == 2
    assert "delivered" in capsys.readouterr().err
    assert list(read(path).reels) == ["out-reel"]


def test_the_command_line_refuses_when_it_cannot_see_the_deliveries(path, capsys):
    """Folders it cannot find say nothing about what went out, so they clear no one."""
    ledger = ["--ledger", str(path)]
    main(["number", "base", "200", *ledger])
    main(["number", "claim", "some-reel", *ledger])
    capsys.readouterr()
    assert main(["number", "release", "some-reel", *ledger]) == 2
    assert "not a folder" in capsys.readouterr().err
    assert list(read(path).reels) == ["some-reel"]


def test_the_command_line_needs_a_slug_to_release(path, capsys):
    assert main(["number", "release", "--ledger", str(path)]) == 2
    assert "slug" in capsys.readouterr().err


# -- a series named in more words, and a place given after the claim (ADR 0233) ---------------------------------------
@pytest.mark.parametrize(
    ("name", "slug", "key"),
    [
        ("Saga", "saga", "Saga"),
        ("Gloss", "gloss", "Gloss"),
        ("Juno & Pip", "juno-and-pip", "juno-and-pip"),
        ("Small Print", "small-print", "small-print"),
    ],
)
def test_a_series_name_has_one_slug_and_the_ledger_keeps_one_word_names_as_they_were(name, slug, key):
    assert series_slug(name) == slug
    assert series_key(name) == key


@pytest.mark.parametrize(
    "name", ["", " ", "juno-and-pip", "Juno_Pip", "Juno & Pip!", "Juno and pip", "Juno &", None, 7]
)
def test_a_series_name_that_is_not_capitalised_words_has_no_slug(name):
    with pytest.raises(NumberError, match="capitalised words"):
        series_slug(name)


def test_a_show_named_in_more_words_is_kept_by_its_slug_and_reaches_the_episode_document(path):
    set_base(path, 214)
    set_base(path, 0, series="Juno & Pip")
    held = claim(path, "jp-one", series="Juno & Pip", brief="series-v1")
    assert held == Claim(215, "juno-and-pip", 1, "series-v1")
    stored = json.loads(path.read_text())
    assert stored["series"] == {"juno-and-pip": 0}
    assert stored["reels"]["jp-one"] == {
        "number": 215,
        "series": "juno-and-pip",
        "series_number": 1,
        "brief": "series-v1",
    }
    assert claim(path, "jp-one", series="Juno & Pip") == held
    assert episode_document(held) == {"number": 215, "series": "juno-and-pip", "series_number": 1, "brief": "series-v1"}


def test_a_one_word_series_writes_the_ledger_and_the_document_it_always_did(path):
    set_base(path, 192)
    set_base(path, 18, series="Saga")
    held = claim(path, "saga-next", series="Saga")
    assert json.loads(path.read_text())["reels"]["saga-next"] == {"number": 193, "series": "Saga", "series_number": 19}
    assert episode_document(held) == {"number": 193, "series": "saga", "series_number": 19}


@pytest.mark.parametrize("key", ["juno_and_pip", "Juno & Pip", "juno-and-Pip", "-juno", "juno-"])
def test_a_ledger_key_that_is_neither_a_name_nor_a_slug_writes_no_document(key):
    with pytest.raises(NumberError, match="neither"):
        episode_document(Claim(216, key, 2))


def test_a_show_without_its_place_writes_no_document():
    with pytest.raises(NumberError, match="go together"):
        episode_document(Claim(216, "juno-and-pip", 0))


@pytest.fixture
def show(path):
    set_base(path, 214)
    set_base(path, 0, series="Juno & Pip")
    claim(path, "jp-one", brief="series-v1")
    claim(path, "jp-two", brief="series-v1")
    return path


def test_a_claim_gets_its_place_in_a_show_and_keeps_its_number_and_brief(show):
    second = place(show, "jp-two", "Juno & Pip", 2, delivered=())
    assert second == Claim(216, "juno-and-pip", 2, "series-v1")
    assert read(show).reels["jp-two"] == second
    assert place(show, "jp-two", "Juno & Pip", 2, delivered=()) == second
    assert place(show, "jp-one", "Juno & Pip", 1, delivered=()) == Claim(215, "juno-and-pip", 1, "series-v1")
    assert claim(path=show, slug="jp-three", series="Juno & Pip") == Claim(217, "juno-and-pip", 3)


@pytest.mark.parametrize(
    ("slug", "series", "number", "delivered", "message"),
    [
        ("jp-nine", "Juno & Pip", 2, (), "has no claim"),
        ("jp-two", "Juno & Pip", 2, ("jp-two",), "was delivered"),
        ("jp-two", "Small Print", 2, (), "has no base"),
        ("jp-two", "Juno & Pip", 0, (), "from 1"),
        ("jp-two", "Juno & Pip", True, (), "from 1"),
        ("jp-two", "", 2, (), "capitalised words"),
        ("jp-two", "juno-and-pip", 2, (), "capitalised words"),
    ],
)
def test_a_place_is_refused_and_the_ledger_is_left_as_it_was(show, slug, series, number, delivered, message):
    before = show.read_bytes()
    with pytest.raises(NumberError, match=message):
        place(show, slug, series, number, delivered=delivered)
    assert show.read_bytes() == before


def test_a_place_taken_or_a_reel_already_placed_is_refused(show):
    place(show, "jp-one", "Juno & Pip", 1, delivered=())
    with pytest.raises(NumberError, match="held by jp-one"):
        place(show, "jp-two", "Juno & Pip", 1, delivered=())
    with pytest.raises(NumberError, match="already"):
        place(show, "jp-one", "Juno & Pip", 3, delivered=())


def test_the_cli_places_a_claim_in_a_show(show, capsys):
    root = show.parent.parent
    (root / "renders" / "ig").mkdir(parents=True)
    (root / "outbox").mkdir()
    args = ["number", "place", "jp-two", "--series", "Juno & Pip", "--series-number", "2", "--ledger", str(show)]
    assert main(args) == 0
    assert capsys.readouterr().out.strip() == "jp-two #216 juno-and-pip #2 series-v1"
    assert main(["number", "place", "jp-one", "--series", "Juno & Pip", "--ledger", str(show)]) == 2
    assert "takes --series and --series-number" in capsys.readouterr().err


@pytest.mark.parametrize("number", [1, 3])
def test_a_place_at_or_under_the_series_base_is_refused(path, number):
    set_base(path, 214)
    set_base(path, 3, series="Juno & Pip")
    claim(path, "jp-two", brief="series-v1")
    before = path.read_bytes()
    with pytest.raises(NumberError, match="at or under"):
        place(path, "jp-two", "Juno & Pip", number, delivered=())
    assert path.read_bytes() == before
    assert place(path, "jp-two", "Juno & Pip", 4, delivered=()) == Claim(215, "juno-and-pip", 4, "series-v1")
