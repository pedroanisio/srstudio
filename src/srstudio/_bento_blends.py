"""Authored neutral/deadpan/concerned deformation for the opt-in Bento candidate.

Interpolate anatomical controls before clipping pupils and inking curves. These
three expressions share open-eye topology, zero pose tilt and no expression marks.
Other expressions require their own authored treatment and are deliberately absent.
"""

from dataclasses import dataclass, replace

from . import toon_bento as b
from .face_blends import FaceLayers, FacePose, FaceSample, _fail

_POSES = tuple(FacePose(name, b.MOODS[name].mouth) for name in ('neutral', 'deadpan', 'concerned'))


def _mix(a, z, t):
    return tuple(x + (y - x) * t for x, y in zip(a, z, strict=True))


@dataclass(frozen=True)
class BentoBlender:
    transitions = tuple((a, z) for a in _POSES for z in _POSES if a != z)

    def layers(self, sample: FaceSample) -> FaceLayers:
        if (sample.source, sample.target) not in self.transitions:
            raise _fail('blend.expressions', sample, self.transitions, 'face_blend.unsupported')
        if not 0 <= sample.weight <= 1:
            raise _fail('blend.weight', sample.weight, 'a normalized weight in 0..1')
        a, z, t = b.MOODS[sample.source.eyes], b.MOODS[sample.target.eyes], sample.weight
        if t in (0, 1):
            held = a if t == 0 else z
            return FaceLayers(
                tuple(b._eye_layers(held, None, 0, (0, 0)) + b._eye_layers(held, None, 1, (0, 0))),
                tuple(b._mouth_layers(held.mouth)),
            )
        held = replace(
            a,
            gaze=_mix(a.gaze, z.gaze, t),
            lids=_mix(a.lids, z.lids, t),
            brows=_mix(a.brows, z.brows, t),
            angles=_mix(a.angles, z.angles, t),
        )
        brow_a = b._FLAT_BROW if a.name in b.LEVEL_BROWS else b._BROW
        brow_z = b._FLAT_BROW if z.name in b.LEVEL_BROWS else b._BROW
        brow = tuple(_mix(x, y, t) for x, y in zip(brow_a, brow_z, strict=True))
        eyes = []
        for side in (0, 1):
            layers = b._eye_layers(held, None, side, (0, 0))
            # In this authored family, the final two layers are brow and glasses.
            place = b._moved(b._EYE_X[side], 239.0 + held.brows[side], held.angles[side])
            eyes.extend([*layers[:-2], b._line(brow, b.DARK_FUR, 8.5, place), layers[-1]])
        mouth = tuple(
            _mix(x, y, t) for x, y in zip(b._LINE_MOUTHS[a.mouth][0], b._LINE_MOUTHS[z.mouth][0], strict=True)
        )
        return FaceLayers(tuple(eyes), (b._line(mouth, b.THROAT, 4.5),))
