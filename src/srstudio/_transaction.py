"""Rollback scene and canvas changes made by an unsuccessful authoring call."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from copy import copy
from typing import Any

from sr_core.scene import Element

from ._counter import Counter


@contextmanager
def scene_transaction(scene: Any, canvas: Any = None) -> Iterator[None]:
    nodes = list(scene.iter())
    snapshots = [
        (node, node._attrs.copy(), [child if isinstance(child, Element) else copy(child) for child in node.nodes])
        for node in nodes
    ]
    fields = (
        'namer',
        '_assets',
        '_paints',
        '_serial',
        '_sig_ids',
        '_gradients',
        '_symbols',
        '_symbol_root',
        '_effects',
        '_effect_root',
    )
    canvas_state = {name: getattr(canvas, name) for name in fields} if canvas is not None else {}
    namer = canvas.namer if canvas is not None else None
    count = namer.count if isinstance(namer, Counter) else None
    for name, value in canvas_state.items():
        if isinstance(value, dict):
            canvas_state[name] = value.copy()
    try:
        yield
    except Exception:
        # Detach original nodes even if a callback moved them into a new parent, then rebuild their
        # original child lists. Keeping the original objects preserves references held by callers.
        for node in nodes[1:]:
            if node.owner is not None:
                node.owner.nodes.remove(node)
        for node in nodes:
            node.nodes.clear()
        for node, attrs, children in snapshots:
            node._attrs.clear()
            node._attrs.update(attrs)
            node.nodes.extend(children)
        scene._index = None  # attribute restoration may have changed IDs
        for name, value in canvas_state.items():
            setattr(canvas, name, value)
        if isinstance(namer, Counter) and count is not None:
            namer.count = count
        raise
