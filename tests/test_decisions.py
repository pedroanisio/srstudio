"""Every decision record the code cites exists: an ``ADR NNNN`` or a ``NNNN-name.md`` under ``src/`` or ``episodes/``
resolves to a file in ``docs/decisions/``, so a reader sent to a decision always finds it, and finds only one: no two
records share a number.
"""

import re
from pathlib import Path

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


def _sources() -> list[Path]:
    return sorted(p for top in ("src", "episodes") for p in (ROOT / top).rglob("*.py"))


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
