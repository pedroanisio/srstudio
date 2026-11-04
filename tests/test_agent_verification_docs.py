"""Commands and inline test paths in the verification guide refer to this checkout."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_inline_verification_test_references_exist():
    text = (ROOT / 'docs/authoring-verification.md').read_text()
    references = set(re.findall(r'(?<![\w/])(tests/[\w/]+\.py)', text))
    assert references
    assert not [name for name in references if not (ROOT / name).is_file()]


def test_verification_guide_supplies_executable_agent_recipes():
    text = (ROOT / 'docs/authoring-verification.md').read_text()
    assert 'python -m pytest' in text
    assert '--require-check' in text
    assert 'skipped' in text
