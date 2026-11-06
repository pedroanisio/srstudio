"""The documentation's declaration counts are regenerated from a clean default registry."""

import subprocess
import sys
from pathlib import Path


def test_documented_contract_coverage_matches_the_installed_catalog():
    root = Path(__file__).parents[1]
    result = subprocess.run(
        [sys.executable, str(root / 'tools/update_contract_coverage.py'), '--check'],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
