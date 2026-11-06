"""Regenerate the bounded default-catalog coverage table in the discovery guide; --check detects drift."""

from __future__ import annotations

import argparse
from pathlib import Path

from srstudio import registry

START = '<!-- contract-coverage:start -->'
END = '<!-- contract-coverage:end -->'
GUIDE = Path(__file__).resolve().parents[1] / 'docs/authoring-discovery.md'


def render() -> str:
    report = registry.contract_coverage()
    lines = [
        '| Kind | Registered | Explicit contracts | Complete data shapes | Runtime bindings | With examples '
        '| With units | With clocks | With anchors |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |',
    ]
    for kind, counts in report['kinds'].items():
        values = [
            counts[name]
            for name in (
                'registered',
                'explicit_contracts',
                'data_shape_complete',
                'with_runtime_bindings',
                'with_examples',
                'with_units',
                'with_clocks',
                'with_anchors',
            )
        ]
        lines.append('| ' + kind + ' | ' + ' | '.join(str(value) for value in values) + ' |')
    return '\n'.join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    text = GUIDE.read_text()
    before, found, rest = text.partition(START)
    _, closed, after = rest.partition(END)
    if not found or not closed:
        parser.error('discovery guide is missing its contract-coverage markers')
    updated = before + START + '\n' + render() + '\n' + END + after
    if updated == text:
        return 0
    if args.check:
        print('Contract coverage changed; run python tools/update_contract_coverage.py.')
        return 1
    GUIDE.write_text(updated)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
