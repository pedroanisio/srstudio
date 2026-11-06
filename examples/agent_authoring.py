"""Build agent recipe previews with source JSON and scoped evidence. Requires a fresh output directory."""

import argparse
import hashlib
import json
from pathlib import Path

from sr_core.scene import Scene

from srstudio import Canvas, authoring


def build(output: Path, *, recipe: str | None = None) -> list[Path]:
    rows = authoring.recipes()['items']
    selected = [r for r in rows if recipe is None or r['id'] == recipe]
    if not selected:
        raise ValueError(f'Unknown recipe {recipe!r}')
    output.mkdir(parents=True, exist_ok=False)
    paths = []
    for row in selected:
        scene = Scene(version='auto')
        scene.add_project(width=1080, height=1920, fps='24', duration=2, background='#f4f0e9')
        cv = Canvas(scene, width=1080, height=1920, font_asset=None)
        authoring.compile_request(cv, cv.comp, authoring.parse_request(row['request']), id=row['id'])
        findings = scene.check(schema=True)
        if findings:
            raise ValueError(str(findings))
        path = output / (row['id'] + '.xml')
        raw = scene.to_bytes(layout='pretty')
        path.write_bytes(raw)
        report = {
            **row['evidence'],
            'recipe': row['id'],
            'scope': row['scope'],
            'sdk_findings': [],
            'scene_sha256': hashlib.sha256(raw).hexdigest(),
            'request': row['request'],
        }
        path.with_suffix('.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
        paths.append(path)
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--recipe')
    args = parser.parse_args()
    for path in build(args.output, recipe=args.recipe):
        print(path)


if __name__ == '__main__':
    main()
