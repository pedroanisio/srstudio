"""The test suite's own shape: a test module is a leaf that only pytest imports. Shared helpers live in
``tests/support`` and shared fixtures in ``tests/conftest.py``, so no module under ``tests/`` imports a ``test_``
module.
"""

import ast
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent


def _test_imports(source: str) -> list[str]:
    """The ``test_`` modules ``source`` imports, at any depth (an import inside a function counts)."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module]
        elif isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        else:
            continue
        found += [name for name in names if name.split(".")[0].startswith("test_")]
    return found


@pytest.mark.static  # a source scan: its time is the processor's (ADR 0225)
def test_no_module_under_tests_imports_a_test_module():
    offenders = {
        f"{path.relative_to(TESTS)}: {name}"
        for path in sorted(TESTS.rglob("*.py"))
        for name in _test_imports(path.read_text())
    }
    assert not offenders, sorted(offenders)


def test_an_import_of_a_test_module_is_found_at_any_depth():
    source = (
        "import json\n"
        "import test_a\n"
        "from test_b import x\n"
        "from support.c import y\n"
        "from srstudio import test_names\n"
        "def f():\n"
        "    from test_d.e import z\n"
    )
    assert _test_imports(source) == ["test_a", "test_b", "test_d.e"]
