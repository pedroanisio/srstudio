"""Reusable spatial arm and hand performance, independent of drawing style."""

from .constraints import forward, hand_pose, reach
from .errors import Diagnostic, LimbError
from .math3d import Frame, Quaternion, Vec3
from .model import (
    GRIPPER,
    HANDS,
    HUMAN,
    MITTEN,
    PAW,
    THREE_FINGER,
    ArmPose,
    ArmProfile,
    HandControl,
    HandPose,
    HandProfile,
)
from .projection import Affine, Camera

__all__ = [
    "Affine",
    "ArmPose",
    "ArmProfile",
    "Camera",
    "Diagnostic",
    "Frame",
    "GRIPPER",
    "HANDS",
    "HUMAN",
    "HandControl",
    "HandPose",
    "HandProfile",
    "LimbError",
    "MITTEN",
    "PAW",
    "Quaternion",
    "THREE_FINGER",
    "Vec3",
    "forward",
    "hand_pose",
    "reach",
]
