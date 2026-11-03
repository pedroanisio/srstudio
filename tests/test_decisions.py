"""Every decision record the code cites exists: an ``ADR NNNN`` or a ``NNNN-name.md`` under ``src/``
resolves to a file in ``docs/decisions/``, so a reader sent to a decision always finds it, and finds only one: no two
records share a number, and none takes a number ``reserved.json`` holds for a branch's record.
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DECISIONS = ROOT / "docs" / "decisions"
NUMBER = re.compile(r"\bADR (\d{4})\b")
FILE = re.compile(r"\b(\d{4}-[a-z0-9-]+\.md)\b")


def _unresolved(text: str, names: set[str]) -> set[str]:
    """The citations in ``text`` that name no file in ``names``: numbers as ``ADR NNNN``, files by name."""
    numbers = {name[:4] for name in names}
    missing = {f"ADR {n}" for n in NUMBER.findall(text) if n not in numbers}
    return missing | {f for f in FILE.findall(text) if f not in names}


def _shared(names: set[str]) -> dict[str, list[str]]:
    """The numbers that more than one record in ``names`` carries, each with its records."""
    held: dict[str, list[str]] = {}
    for name in sorted(names):
        held.setdefault(name[:4], []).append(name)
    return {number: records for number, records in held.items() if len(records) > 1}


def _reserved(path: Path = DECISIONS / "reserved.json") -> dict[str, str]:
    """The reserved numbers and the record name each is held for, from ``docs/decisions/reserved.json``."""
    data = json.loads(path.read_text())
    if set(data) != {"schema_version", "about", "reservations"} or not data["schema_version"].startswith("1."):
        raise ValueError(f"reserved.json has fields {sorted(data)} at schema {data.get('schema_version')!r}")
    held: dict[str, str] = {}
    for row in data["reservations"]:
        if set(row) != {"number", "name", "owner", "reserved"} or not re.fullmatch(r"\d{4}", row["number"]):
            raise ValueError(f"reserved.json: malformed reservation {row!r}")
        if row["number"] in held:
            raise ValueError(f"reserved.json: {row['number']} is reserved twice")
        held[row["number"]] = row["name"]
    return held


def _squatted(names: set[str], held: dict[str, str]) -> set[str]:
    """The records in ``names`` that carry a reserved number under another name."""
    return {n for n in names if n[:4] in held and n != f"{n[:4]}-{held[n[:4]]}.md"}


def _sources() -> list[Path]:
    return sorted(p for top in ("src",) for p in (ROOT / top).rglob("*.py"))


@pytest.mark.static  # a source scan: its time is the processor's (ADR 0225)
def test_every_cited_decision_record_exists():
    names = {p.name for p in DECISIONS.glob("*.md")}
    missing = {
        f"{path.relative_to(ROOT)}: {cite}" for path in _sources() for cite in _unresolved(path.read_text(), names)
    }
    assert not missing, sorted(missing)


def test_the_scan_reads_the_citations_it_checks():
    text = "\n".join(p.read_text() for p in _sources())
    assert "0026" in NUMBER.findall(text)
    assert "0001-signature.md" in FILE.findall(text)


def test_a_missing_record_is_reported_by_number_and_by_file():
    names = {"0001-signature.md", "0026-collage-style.md"}
    text = "signed (ADR 0001); see ADR 0026, ADR 0027 and ``0026-collage-style.md``, ``0028-gone.md``"
    assert _unresolved(text, names) == {"ADR 0027", "0028-gone.md"}


def test_no_two_records_share_a_number():
    assert not _shared({p.name for p in DECISIONS.glob("*.md")})


def test_a_shared_number_is_reported_with_both_records():
    names = {"0196-authored-vector-form-lighting.md", "0196-dance-style-from-reference-video.md", "0197-solved.md"}
    assert _shared(names) == {
        "0196": ["0196-authored-vector-form-lighting.md", "0196-dance-style-from-reference-video.md"]
    }


def test_no_record_takes_a_number_reserved_for_another():
    assert not _squatted({p.name for p in DECISIONS.glob("*.md")}, _reserved())


def test_a_reserved_number_is_free_only_to_its_own_record():
    held = {"0203": "dance-style-from-reference-video"}
    names = {"0203-dance-style-from-reference-video.md", "0203-shadow-masks.md", "0204-other.md"}
    assert _squatted(names, held) == {"0203-shadow-masks.md"}


@pytest.mark.parametrize(
    "rows",
    [
        [{"number": "203", "name": "x", "owner": "o", "reserved": "2026-11-02"}],
        [{"number": "0203", "name": "x", "owner": "o"}],
        [
            {"number": "0203", "name": "x", "owner": "o", "reserved": "d"},
            {"number": "0203", "name": "y", "owner": "o", "reserved": "d"},
        ],
    ],
    ids=["short-number", "missing-field", "reserved-twice"],
)
def test_a_malformed_reservation_list_is_refused(tmp_path, rows):
    path = tmp_path / "reserved.json"
    path.write_text(json.dumps({"schema_version": "1.0.0", "about": "", "reservations": rows}))
    with pytest.raises(ValueError, match="reserved"):
        _reserved(path)
