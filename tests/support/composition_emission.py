"""The engine's own evaluation of an emitted scene, shared by the emission and timeline tests."""

import json
import subprocess


def evaluate(engine, path, time):
    result = subprocess.run(
        [str(engine), 'eval', str(path), '--time', str(time), '--json'],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return json.loads(result.stdout)['result']['nodes']
