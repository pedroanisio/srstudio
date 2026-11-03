"""A fresh agent can discover the complete built-in catalog without knowing module imports."""

import json
import subprocess
import sys


def test_fresh_catalog_includes_rafa_before_explicit_import():
    result = subprocess.run(
        [
            sys.executable,
            '-c',
            '''
import json
from srstudio import registry
before = sorted((e.kind, e.name) for e in registry.entries())
from srstudio import rafa_host
after = sorted((e.kind, e.name) for e in registry.entries())
print(json.dumps([before, after]))
''',
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    before, after = json.loads(result.stdout)
    assert ['character', 'rafa'] in before
    assert ['location', 'rafa-breakroom'] in before
    assert ['prop', 'rafa-mug'] in before
    assert before == after
