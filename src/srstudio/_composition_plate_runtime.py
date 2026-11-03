"""Bounded public plate preparation and strict reply validation in the parent."""

from __future__ import annotations

from dataclasses import asdict

from . import _composition_plate_wire as payload
from . import _composition_wire as wire
from . import composition as c
from ._composition_runtime import _call


def prepare_plate(plan: c.ValidatedScenePlan, layer: str, source: c.PlateSource) -> c.PreparedPlate:
    payload.validate_source(source)
    c.plate_view(plan, layer, meters_per_unit=source.meters_per_unit)
    if next(item.asset for item in plan.spec.layers if item.id == layer) != source.id:
        raise c._fail('source.id', source.id, 'the source for the requested layer', 'composition.reference')
    response = _call(
        {
            'schema': wire.SCHEMA,
            'operation': 'prepare-plate',
            'plan': asdict(plan),
            'layer': layer,
            'source': payload.source_encode(source),
        },
        plan.spec.budget,
    )
    wire.fields(response, {'schema', 'status', 'prepared'})
    return payload.prepared_decode(response['prepared'], plan, layer, source)
