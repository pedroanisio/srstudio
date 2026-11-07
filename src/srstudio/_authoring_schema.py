"""Authoring schemas share their closed record shapes with the executable adapters."""

from ._authoring_contracts import argument_constraints
from ._authoring_records import FAMILIES
from ._motion_schemas import _record_shapes, keyed_schema, procedural_schema
from .character_clips import Placement
from .document_schemas import _object
from .limbs.interaction import PropMesh


def document():
    definitions = {}

    def scoped(shape, defs, prefix):
        def rewrite(node):
            if isinstance(node, list):
                return [rewrite(v) for v in node]
            if isinstance(node, dict):
                return {
                    k: v.replace('#/$defs/', '#/$defs/' + prefix) if k == '$ref' else rewrite(v)
                    for k, v in node.items()
                }
            return node

        definitions.update({prefix + name: rewrite(value) for name, value in defs.items()})
        return rewrite(shape)

    shapes = []
    for i, record in enumerate([r for r, _ in FAMILIES.values()] + [Placement, PropMesh]):
        rows, defs = _record_shapes(record, limit=10000, string_limit=16384)
        shapes.append(scoped(rows[0], defs, f'input{i}_'))
    motions = []
    for version in ('1.0.0', '1.1.0', '1.2.0', '1.3.0', '1.4.0'):
        shape = procedural_schema(version)
        motions.append(scoped(shape, shape.pop('$defs'), 'motion' + version.replace('.', '_') + '_'))
    shape = keyed_schema('1.0.0')
    motions.append(scoped(shape, shape.pop('$defs'), 'keyed_'))
    motion = {'anyOf': motions}
    interval = _object(
        {
            name: {'type': 'number', 'minimum': 0, 'x-unit': 'seconds', 'x-timebase': 'parent', 'x-role': role}
            for name, role in (('start_s', 'start'), ('end_s', 'end'))
        },
        ('start_s', 'end_s'),
    )
    base = {'schema': {'const': 'srstudio.authoring/1.0.0'}, 'interval': interval, 'placement': shapes[-2]}
    branches = []
    for shape, (_, names) in zip(shapes, FAMILIES.values(), strict=False):
        required = ('schema', 'task', 'interval', 'character')
        if definitions[shape['$ref'].removeprefix('#/$defs/')].get('required'):
            required += ('arguments',)
        for name in names:
            branches.append(
                _object(
                    {
                        **base,
                        'task': {'const': 'character'},
                        'character': {'const': name},
                        'arguments': {'allOf': [shape, argument_constraints(name)]},
                    },
                    required,
                )
            )
    for task in ('gesture', 'carry'):
        props = {
            **base,
            'task': {'const': task},
            'motion': motion,
            'style': {'enum': ['toon', 'gloss', 'stick', 'cutout']},
            'fps': {'type': 'integer', 'minimum': 1, 'maximum': 120},
        }
        required = ('schema', 'task', 'interval', 'motion')
        if task == 'carry':
            props.update(mesh=shapes[-1], attachment={'type': 'string', 'minLength': 1, 'maxLength': 128})
            required += ('mesh', 'attachment')
        branches.append(_object(props, required))
    return {
        'oneOf': branches,
        '$defs': definitions,
        'x-runtime-constraints': [
            'Parse to enforce finite values, local source times, 600-second intervals and 100000-value bounds.',
            'Compile to enforce selected rig capabilities, geometry and sampling budgets.',
            'Canvas and parent are separate runtime bindings, never JSON fields.',
        ],
    }
