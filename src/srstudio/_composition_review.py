"""Explicit candidate provenance and content pins; no approval-table mutation."""

from __future__ import annotations

import json
import re
from dataclasses import asdict

from . import composition as c


def candidate_identity(binding: c.AssetBinding, style: str, purpose: str) -> dict:
    candidate = binding.candidate
    assert candidate is not None
    if (
        purpose != 'candidate-review'
        or not re.fullmatch(r'candidate\.[A-Za-z_][A-Za-z0-9_.-]{0,117}', binding.part)
        or candidate.style != style
        or not re.fullmatch(r'[a-f0-9]{64}', candidate.source_digest)
    ):
        raise c._fail(
            f'bindings.{binding.id}.candidate',
            asdict(candidate),
            'explicit candidate-review purpose, candidate.<name>, matching style and exact source SHA-256',
            'composition.candidate',
        )
    return {'part': binding.part, 'version': binding.version, 'candidate': asdict(candidate), 'approval': None}


def check_source(binding: c.AssetBinding, digest: str) -> None:
    if binding.candidate is not None and binding.candidate.source_digest != digest:
        raise c._fail(
            f'bindings.{binding.id}.candidate.source_digest',
            digest,
            binding.candidate.source_digest,
            'composition.candidate',
        )


def _description(plan: c.ValidatedScenePlan) -> dict:
    return {
        'schema': 'srstudio.candidate-review/1.0.0',
        'purpose': plan.purpose,
        'plan_digest': plan.digest,
        'style': asdict(plan.spec.style),
        'candidates': [
            {'asset': b.id, 'part': b.part, 'version': b.version, **asdict(b.candidate), 'approval': None}
            for b in plan.bindings
            if b.candidate is not None
        ],
    }


def describe(plan: c.ValidatedScenePlan) -> dict:
    if c.preflight(plan.spec, plan.bindings, purpose=plan.purpose) != plan:
        raise c._fail('plan', plan.digest, 'the current reproducible preflight result', 'composition.version')
    return _description(plan)


def mark(xml: bytes, plan: c.ValidatedScenePlan) -> bytes:
    """A non-rendering provenance comment travels with every review scene."""
    if plan.purpose == 'production':
        return xml
    data = json.dumps(_description(plan), sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    data = data.replace('--', r'\u002d\u002d')  # XML comments cannot contain double hyphens.
    return xml.replace(b'?>', b'?>\n<!-- ' + data.encode('ascii') + b' -->', 1)
