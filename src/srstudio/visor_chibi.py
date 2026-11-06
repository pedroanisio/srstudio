"""Proposed clay visor character: rigid joint rotations and emissive replacement eyes.

Coordinates follow Rafa: y down, z away from the camera, soles at zero. Each
piece is baked in its joint's frame; the visor and its eyes share the neck/head
transform. The host renders unique states once and gates them on its clock.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache

import numpy as np

from . import _character_contracts as cc
from . import clay, plates
from . import visor_chibi_geometry as geometry
from .canvas import Canvas
from .errors import SrstudioError
from .registry import Entry, register

EYES = ('neutral', 'blink', 'suspicious', 'surprised', 'smug', 'happy', 'sad', 'angry')
GAZES = ('ahead', 'left', 'right', 'up', 'down')
POSES = ('neutral', 'presenting', 'hands_on_hips', 'wave', 'shrug', 'point')
NECK = (0.0, -260.0, 0.0)
Point = tuple[float, float, float]


class VisorChibiError(SrstudioError, ValueError):
    """An unknown state, joint or rotation of the proposed visor puppet."""


class JointName(str, Enum):
    PELVIS = 'pelvis'
    CHEST = 'chest'
    NECK = 'neck'
    HEAD = 'head'
    LEFT_SHOULDER = 'left_shoulder'
    LEFT_ELBOW = 'left_elbow'
    LEFT_WRIST = 'left_wrist'
    RIGHT_SHOULDER = 'right_shoulder'
    RIGHT_ELBOW = 'right_elbow'
    RIGHT_WRIST = 'right_wrist'
    LEFT_HIP = 'left_hip'
    LEFT_KNEE = 'left_knee'
    LEFT_ANKLE = 'left_ankle'
    RIGHT_HIP = 'right_hip'
    RIGHT_KNEE = 'right_knee'
    RIGHT_ANKLE = 'right_ankle'


@dataclass(frozen=True)
class Joint:
    name: JointName
    parent: JointName | None
    offset: Point


J = JointName
JOINTS = (
    Joint(J.PELVIS, None, (0, -160, 0)),
    Joint(J.CHEST, J.PELVIS, (0, -52, 0)),
    Joint(J.NECK, J.CHEST, (0, -48, 0)),
    Joint(J.HEAD, J.NECK, (0, 0, 0)),
    *(
        joint
        for side, sign in (('left', -1), ('right', 1))
        for joint in (
            Joint(J(f'{side}_shoulder'), J.CHEST, (sign * 55, -20, 0)),
            Joint(J(f'{side}_elbow'), J(f'{side}_shoulder'), (0, 58, 0)),
            Joint(J(f'{side}_wrist'), J(f'{side}_elbow'), (0, 56, 0)),
            Joint(J(f'{side}_hip'), J.PELVIS, (sign * 25, 12, 0)),
            Joint(J(f'{side}_knee'), J(f'{side}_hip'), (0, 65, 0)),
            Joint(J(f'{side}_ankle'), J(f'{side}_knee'), (0, 65, 0)),
        )
    ),
)


@dataclass(frozen=True, init=False)
class Pose:
    """Immutable XYZ Euler degrees per joint; omitted rotations are zero.

    Local rotations compose as Rz @ Ry @ Rx, then inherit the parent frame.
    Translation and scale are deliberately absent, so a pose cannot stretch bones.
    """

    rotations: tuple[tuple[JointName, Point], ...]

    def __init__(self, rotations: Mapping[str, Point] | Mapping[JointName, Point] | None = None) -> None:
        checked: dict[JointName, Point] = {}
        for name, angles in (rotations or {}).items():
            try:
                joint = JointName(name)
            except (ValueError, TypeError) as exc:
                raise VisorChibiError(f'unknown joint {name!r}') from exc
            if (
                not isinstance(angles, (tuple, list))
                or len(angles) != 3
                or any(isinstance(a, bool) or not isinstance(a, (int, float)) or not math.isfinite(a) for a in angles)
            ):
                raise VisorChibiError(f'{name}: rotations must be three finite XYZ degrees')
            checked[joint] = tuple(float(a) for a in angles)  # type: ignore[assignment]
        object.__setattr__(self, 'rotations', tuple((j.name, checked[j.name]) for j in JOINTS if j.name in checked))


@dataclass(frozen=True)
class Face:
    eyes: str = 'neutral'
    gaze: str = 'ahead'

    def __post_init__(self) -> None:
        if self.eyes not in EYES:
            raise VisorChibiError(f'eyes must be one of {EYES}, got {self.eyes!r}')
        if self.gaze not in GAZES:
            raise VisorChibiError(f'gaze must be one of {GAZES}, got {self.gaze!r}')


def pose(name: str = 'neutral') -> Pose:
    """One named pose, expressed only as joint rotations."""
    if name not in POSES:
        raise VisorChibiError(f'pose must be one of {POSES}, got {name!r}')
    rows: dict[str, Point] = {}
    for side, sign in (('left', -1), ('right', 1)):
        rows[f'{side}_shoulder'] = (0, 0, -sign * 8)
    if name in ('hands_on_hips', 'presenting'):
        for side, sign in (('left', -1), ('right', 1)):
            rows[f'{side}_shoulder'] = (-8, 0, -sign * 48)
            rows[f'{side}_elbow'] = (-25, 0, sign * 110)
            rows[f'{side}_wrist'] = (0, sign * 15, -sign * 20)
    if name == 'presenting':
        rows.update(
            pelvis=(0, 0, -4),
            chest=(0, 0, 4),
            left_hip=(0, 0, 7),
            right_hip=(0, 0, -7),
            right_shoulder=(0, 0, -48),
            right_elbow=(0, 0, -82),
            right_wrist=(-90, 0, 130),
        )
    if name == 'wave':
        rows.update(right_shoulder=(0, 0, -100), right_elbow=(0, 0, -70), right_wrist=(0, 0, -8))
    if name == 'shrug':
        for side, sign in (('left', -1), ('right', 1)):
            rows[f'{side}_shoulder'] = (0, 0, -sign * 60)
            rows[f'{side}_elbow'] = (0, 0, -sign * 88)
            rows[f'{side}_wrist'] = (0, sign * 65, -sign * 30)
    if name == 'point':
        rows.update(right_shoulder=(0, 0, -120), right_elbow=(0, 0, 0), right_wrist=(0, 80, 0))
    return Pose(rows)


def _spin(angles: Point) -> np.ndarray:
    x, y, z = (math.radians(a) for a in angles)
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    return (
        np.array(((cz, -sz, 0), (sz, cz, 0), (0, 0, 1)))
        @ np.array(((cy, 0, sy), (0, 1, 0), (-sy, 0, cy)))
        @ np.array(((1, 0, 0), (0, cx, -sx), (0, sx, cx)))
    )


REST = pose('neutral')
REST_FACE = Face()


def transforms(state: Pose = REST) -> dict[JointName, np.ndarray]:
    rotations = dict(state.rotations)
    frames: dict[JointName, np.ndarray] = {}
    for joint in JOINTS:
        local = np.eye(4)
        local[:3, :3] = _spin(rotations.get(joint.name, (0, 0, 0)))
        local[:3, 3] = joint.offset
        frames[joint.name] = (np.eye(4) if joint.parent is None else frames[joint.parent]) @ local
    return frames


def joint_positions(state: Pose = REST) -> dict[JointName, np.ndarray]:
    return {name: matrix[:3, 3].copy() for name, matrix in transforms(state).items()}


def eyes(m: clay.Model, face: Face = REST_FACE) -> None:
    """Emissive shapes on the curved visor, in the same neck frame as the helmet."""
    with m.at(scale=geometry.HEAD_SCALE):
        geometry.eyes(m, face.eyes, face.gaze)


@lru_cache(maxsize=96)
def _base_meshes(state: Pose) -> tuple[clay.Mesh, ...]:
    """Reuse the unchanged suit, armor and glass across replacement eye states."""
    result = clay.Model()
    frames = transforms(state)
    for joint in JOINTS:
        local = clay.Model()
        geometry.piece(local, joint.name.value)
        matrix = frames[joint.name]
        for mesh in local.meshes():
            result.surface(
                mesh.material,
                mesh.vertices @ matrix[:3, :3].T + matrix[:3, 3],
                mesh.normals @ matrix[:3, :3].T,
                mesh.triangles,
                mesh.uvs,
            )
    return tuple(result.meshes())


@lru_cache(maxsize=96)
def meshes(state: Pose = REST, face: Face = REST_FACE) -> tuple[clay.Mesh, ...]:
    """Rigid pieces and replacement eyes inherit the same joint frames and normals."""
    local = clay.Model()
    eyes(local, face)
    matrix = transforms(state)[JointName.HEAD]
    eye_meshes = tuple(
        clay.Mesh(
            mesh.material,
            mesh.vertices @ matrix[:3, :3].T + matrix[:3, 3],
            mesh.normals @ matrix[:3, :3].T,
            mesh.triangles,
            mesh.uvs,
        )
        for mesh in local.meshes()
    )
    return tuple(sorted((*_base_meshes(state), *eye_meshes), key=lambda mesh: mesh.material))


CAMERA = plates.Camera((65, -228, -820), (0, -196, 0), 27, 6)


def plate(
    state: Pose = REST, face: Face = REST_FACE, *, width: int = 1080, height: int = 1920, head_only: bool = False
) -> plates.Plate:
    camera = plates.Camera((22, -350, -620), (0, -348, 0), 23, 4) if head_only else CAMERA
    if head_only:
        local = clay.Model()
        geometry.piece(local, 'head')
        eyes(local, face)
        matrix = transforms(state)[JointName.HEAD]
        used = tuple(
            clay.Mesh(
                mesh.material,
                mesh.vertices @ matrix[:3, :3].T + matrix[:3, 3],
                mesh.normals @ matrix[:3, :3].T,
                mesh.triangles,
                mesh.uvs,
            )
            for mesh in local.meshes()
        )
    else:
        used = meshes(state, face)
    return plates.Plate(
        width,
        height,
        camera,
        plates.stage_lights(warm=False, rim=True),
        (plates.Placed(used),),
        plates.materials_of(used, geometry.MATERIALS),
    )


def part_plates(name: str) -> tuple[plates.Plate, ...]:
    """Every plate referenced by the catalog specimen, in specimen order."""
    if name != 'visor-chibi':
        return ()
    return (
        *(plate(face=Face(eye)) for eye in EYES),
        *(plate(face=Face(gaze=g)) for g in GAZES[1:]),
        *(plate(pose(p)) for p in POSES[1:]),
    )


@register(
    'character',
    'visor-chibi',
    style='toon',
    summary='Proposed clay chibi: white armor, black suit and glowing visor eyes',
    contract=cc.character(
        limbs=False,
        expressions=False,
        parameters=(('m', cc.P(unit='Rafa model units')),),
        vocabularies=(
            ('eyes', EYES),
            ('gazes', GAZES),
            ('poses', POSES),
            ('joints', tuple(j.value for j in JointName)),
        ),
        constraints=(
            'This callable emits a complete static neutral clay model. '
            'Use joint rotations with meshes, and visor_chibi_host for plate performance.',
        ),
        operations=(
            cc.Operation(
                'face', Face, cc.PartContract(parameters=(('eyes', cc.P(enum=EYES)), ('gaze', cc.P(enum=GAZES))))
            ),
            cc.Operation('pose', pose, cc.PartContract(parameters=(('name', cc.P(enum=POSES)),))),
        ),
    ),
)
def body(m: clay.Model) -> None:
    """The complete neutral puppet; visor_chibi_host performs its plate animation."""
    for mesh in meshes():
        m.surface(mesh.material, mesh.vertices, mesh.normals, mesh.triangles, mesh.uvs)


def specimen(entry: Entry) -> Canvas:
    """The drawing fingerprint includes every face, gaze and named pose without rendering."""
    from .specimens import HOLD, _stage

    cv = _stage('toon', HOLD)
    drawings = part_plates(entry.name)
    for n, drawing in enumerate(drawings):
        shown = cv.group(cv.comp, cv.uid('visor-state'), opacity=0.0)
        cv.gate(shown, [(HOLD * n / len(drawings), HOLD * (n + 1) / len(drawings))])
        plates.place(cv, shown, drawing)
    return cv
