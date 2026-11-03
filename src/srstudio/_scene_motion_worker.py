"""Standalone timeline worker; the host installs process limits before execution."""

from __future__ import annotations

import sys
from pathlib import Path


def dispatch(raw: bytes) -> dict:
    from srstudio import _composition_wire as wire
    from srstudio import _scene_motion_wire as tw
    from srstudio._scene_motion_emit import compile_timeline

    result = compile_timeline(wire.loads(raw, maximum=tw.MAX_WIRE_BYTES))
    return {
        'schema': wire.SCHEMA,
        'status': 'ok',
        'xml': wire.xml_encode(result.xml),
        'digest': result.digest,
        'plan_digest': result.plan_digest,
        'nodes': result.nodes,
    }


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from srstudio._composition_worker import main
    from srstudio._scene_motion_wire import MAX_WIRE_BYTES

    main(dispatch, maximum=MAX_WIRE_BYTES)
