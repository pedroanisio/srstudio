"""Fixed cup rests and a bounded shoulder swing that clears their contact plane.

One inclined rest stands on the floor in each painter window. Its top matches
the held cup's actual bottom; its world pose never follows the moving carrier.
The rest constrains the arm's rigid shoulder placement during pickup/return.
It does not change bone lengths, finger/cup registration or the native torso.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

import numpy as np
from examples.acting_continuity import carry_motion, cup_mesh
from examples.drawing_attached import attached_mesh, shoulder_frame
from examples.drawing_hand import hand_recipe

from srstudio import clay, proxy
from srstudio import composition as c
from srstudio.limbs import Quaternion, Vec3
from srstudio.limbs.motion import Motion

SUPPORT_TONES = ('#454c56', '#697683', '#93a3b0', '#c5d0d8')
MAX_CLEARANCE_SWING = 0.03  # Radians; a larger correction needs a newly authored reach.


def supported_recipe() -> proxy.Recipe:
    original = hand_recipe()
    return replace(original, tones={**original.tones, 'support': SUPPORT_TONES})


def _bottom(cup: clay.Mesh) -> np.ndarray:
    # hand_mesh closes the side faces with these final, coplanar vertices.
    return cup.vertices[-(len(cup_mesh().faces) - 1) :]


def _face(model: clay.Model, points: np.ndarray, normal: np.ndarray) -> None:
    triangles = [(0, i, i + 1) for i in range(1, len(points) - 1)]
    if np.dot(np.cross(points[1] - points[0], points[2] - points[0]), normal) < 0:
        triangles = [(a, d, b) for a, b, d in triangles]
    model.surface('support', points, np.tile(normal, (len(points), 1)), triangles)


def _stand(cup: clay.Mesh) -> clay.Mesh:
    bottom, normal = _bottom(cup), cup.normals[-1]
    center = bottom.mean(axis=0)
    rim = center + (bottom - center) * 1.45
    under = rim + normal * 3
    if normal[1] < 0.85 or under[:, 1].max() >= -6:
        raise ValueError('cup rest needs an upward-facing top above the ground')
    model = clay.Model()
    _face(model, rim, -normal)
    _face(model, under, normal)
    for i in range(len(rim)):
        j = (i + 1) % len(rim)
        outward = (rim[i] + rim[j]) / 2 - center
        outward /= np.linalg.norm(outward)
        _face(model, np.array((rim[i], rim[j], under[j], under[i])), outward)
    # The stem enters the three-centimeter top, and the wider foot ends at y=0.
    top = center + normal * 2
    model.cylinder('support', (float(top[0]), float((top[1] - 4) / 2), float(top[2])), 3, float(-4 - top[1]))
    model.cylinder('support', (float(top[0]), -2, float(top[2])), 14, 4)
    return model.meshes()[0]


def _clearance(meshes: tuple[clay.Mesh, ...], rest: clay.Mesh, shoulder: np.ndarray) -> tuple[clay.Mesh, ...]:
    cup = next(mesh for mesh in meshes if mesh.material == 'cup')
    center, normal = _bottom(rest).mean(axis=0), rest.normals[-1]
    if np.max((cup.vertices - center) @ normal) <= 1e-9:
        return meshes
    # Choose the shoulder axis whose positive rotation lifts the cup away
    # from the rest. A rigid swing keeps every arm/digit length and grip point.
    radial = _bottom(cup).mean(axis=0) - shoulder
    axis = np.cross(normal, radial)
    if np.linalg.norm(axis) < 1e-9:
        raise ValueError('cup clearance needs an authored shoulder swing axis')
    direction = Vec3(*axis).unit()

    def matrix(angle: float) -> np.ndarray:
        rotation = Quaternion.axis_angle(direction, angle)
        axes = [rotation.rotate(v) for v in (Vec3(1, 0, 0), Vec3(0, 1, 0), Vec3(0, 0, 1))]
        return np.array([(axis.x, axis.y, axis.z) for axis in axes]).T

    def depth(angle: float) -> float:
        moved = (cup.vertices - shoulder) @ matrix(angle).T + shoulder
        return float(np.max((moved - center) @ normal))

    low, high = 0.0, MAX_CLEARANCE_SWING
    if depth(high) > 0:
        raise ValueError('cup clearance exceeds the authored shoulder swing envelope')
    for _ in range(32):
        middle = (low + high) / 2
        if depth(middle) > 0:
            low = middle
        else:
            high = middle
    rotation = matrix(high)
    return tuple(
        replace(mesh, vertices=(mesh.vertices - shoulder) @ rotation.T + shoulder, normals=mesh.normals @ rotation.T)
        for mesh in meshes
    )


def supported_mesh(
    time: float, *, placement: Callable[[float], c.Transform], motion: Motion | None = None
) -> tuple[clay.Mesh, ...]:
    """The hand/cup and fixed floor support, in the existing centimeter clay basis."""
    if type(time) not in (int, float) or not 0 <= time <= 6:
        raise ValueError('support time must lie in 0..6 seconds')
    motion = motion or carry_motion()
    attachment = motion.attachments[0]
    reference = attachment.attach if time < 3 else attachment.release
    rest = next(mesh for mesh in attached_mesh(reference, placement=placement, motion=motion) if mesh.material == 'cup')
    stand = _stand(rest)
    meshes = attached_mesh(time, placement=placement, motion=motion)
    if attachment.attach < time < attachment.release:
        point = shoulder_frame(time, placement=placement(time)).origin
        meshes = _clearance(meshes, rest, np.array((point.x, point.y, -point.z)))
    return (*meshes, stand)
