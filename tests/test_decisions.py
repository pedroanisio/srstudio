"""Every decision record the code cites exists: an ``ADR NNNN`` or a ``NNNN-name.md`` under ``src/`` or ``episodes/``
resolves to a file in ``docs/decisions/``, so a reader sent to a decision always finds it.
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
