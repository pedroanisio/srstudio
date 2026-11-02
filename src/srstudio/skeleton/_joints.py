"""The canonical joint table: srlocations' 55 mannequin joints and 103 controls, as data in srstudio's axes.

The table at ``assets/skeleton/humanoid.json`` (schema ``srstudio.skeleton-joints/1.1.0``) was read from srlocations
at the commit it records and converted once: offsets keep srlocations' shares of the height with y flipped to point
down, angles are radians, and each control carries the axis it turns about on its own side, so a mirrored joint
needs no rule at run time. ``srlocations_joints_digest`` is srlocations' own digest of the joint and control names,
SHA-256 of ``json.dumps([[joint, [control, ...]], ...])`` with the default separators, so moving the pin starts by
comparing it. srlocations is never imported.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from importlib import resources

from ..limbs.math3d import Quaternion, Vec3
from . import _strict as strict
from ._errors import SkeletonError, SkeletonSchemaError

JOINTS_SCHEMA = "srstudio.skeleton-joints/1.1.0"
NAME = re.compile(r"[a-z][a-z_]{0,63}")
COMMIT = re.compile(r"[0-9a-f]{40}")
DIGEST = re.compile(r"[0-9a-f]{64}")
REGIONS = ("torso", "head", "arm", "leg")
KINDS = ("rotate", "translate")
MAX_JOINTS, MAX_DOFS = 128, 6
MAX_TRANSLATION = 10.0  # metres a root channel may move the hips from the root frame
UNIT = 1e-9  # how far from unit length a stored axis or rotation may be after rounding to twelve digits


@dataclass(frozen=True)
class Dof:
    """One control on a joint. A ``rotate`` control turns by its value in radians about ``axis``, right-handed, in
    the joint's frame; a ``translate`` control (the root's only) moves the joint by its value in metres along
    ``axis`` in its parent's frame. ``low`` and ``high`` are the canonical limits."""

    name: str
    kind: str
    axis: Vec3
    low: float
    high: float


@dataclass(frozen=True)
class Joint:
    """One canonical bone. ``offset`` is its place on its parent at rest, as a share of the reference height;
    ``rest`` is the turn it keeps at zero (only the thumbs have one); ``tip`` is where a leaf bone ends, as a share
    of the height, for the head's crown, the toes and the last bone of each finger. ``side`` is -1 left, 0 middle,
    1 right, as srlocations has it."""

    name: str
    parent: str | None
    side: int
    region: str
    offset: Vec3
    rest: Quaternion
    dofs: tuple[Dof, ...]
    tip: Vec3 | None = None

    @property
    def controls(self) -> tuple[str, ...]:
        """Its controls as ``joint.dof`` keys, in the order they apply, the first outermost."""
        return tuple(f"{self.name}.{dof.name}" for dof in self.dofs)

    def dof(self, name: str) -> Dof:
        for dof in self.dofs:
            if dof.name == name:
                return dof
        raise SkeletonError(
            "no such control on this joint",
            code="skeleton.unknown",
            path=f"{self.name}.{name}",
            actual=name,
            expected=[d.name for d in self.dofs],
        )


@dataclass(frozen=True)
class JointTable:
    schema: str
    srlocations_commit: str
    srlocations_joints_digest: str
    reference_height_m: float
    head_radius: float
    joints: tuple[Joint, ...]
    sole_width: float  # the foot's sole across, as a share of the reference height
    sole_heel: float  # how far the sole reaches behind the ankle, as a share of the reference height

    @property
    def pelvis_share(self) -> float:
        """The hips over the soles at the T-stance, as a share of the reference height."""
        return 0.0 - self._offset_y("hips")

    @property
    def ankle_share(self) -> float:
        """The ankles over the soles at the T-stance, as a share of the reference height."""
        leg = sum(self._offset_y(f"right_{name}") for name in ("upper_leg", "lower_leg", "foot"))
        return self.pelvis_share - leg

    def _offset_y(self, name: str) -> float:
        return next(joint.offset.y for joint in self.joints if joint.name == name)


def joints_digest(joints: tuple[Joint, ...]) -> str:
    """srlocations' digest of a joint table's names: SHA-256 of ``json.dumps([[joint, [control, ...]], ...])``."""
    rows = [[joint.name, [dof.name for dof in joint.dofs]] for joint in joints]
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()


def _axis(value: object, path: str) -> Vec3:
    axis = strict.vector(value, path, 1.0)
    parts = (axis.x, axis.y, axis.z)
    if sorted(abs(v) for v in parts) != [0.0, 0.0, 1.0]:
        raise SkeletonSchemaError("an axis is one of +/-x, +/-y, +/-z", path=path, actual=value, expected="unit axis")
    return axis


def _dof(value: object, path: str, root: bool) -> Dof:
    data = strict.fields(value, path, ("name", "kind", "axis", "low", "high"), ("name", "kind", "axis", "low", "high"))
    name = strict.text(data["name"], path + ".name", NAME)
    kind = data["kind"]
    if kind not in KINDS or (kind == "translate" and not root):
        raise SkeletonSchemaError(
            "rotate, or translate on the root only", path=path + ".kind", actual=kind, expected=KINDS
        )
    bound = MAX_TRANSLATION if kind == "translate" else math.pi + UNIT
    low = strict.number(data["low"], path + ".low", -bound, bound)
    high = strict.number(data["high"], path + ".high", -bound, bound)
    if low > high:
        raise SkeletonSchemaError("low must not exceed high", path=path, actual=[low, high], expected="low <= high")
    return Dof(name, kind, _axis(data["axis"], path + ".axis"), low, high)


def _rest(value: object, path: str) -> Quaternion:
    parts = strict.items(value, path, 4, 4)
    numbers = [strict.number(v, f"{path}[{i}]", -1.0, 1.0) for i, v in enumerate(parts)]
    if abs(math.hypot(*numbers) - 1.0) > UNIT:
        raise SkeletonSchemaError("a rest turn is a unit quaternion [w, x, y, z]", path=path, actual=value)
    return Quaternion(*numbers)


def _joint(value: object, path: str, known: dict[str, Joint]) -> Joint:
    fields = ("name", "parent", "side", "region", "offset", "rest", "dofs", "tip")
    data = strict.fields(value, path, fields, fields[:-1])
    name = strict.text(data["name"], path + ".name", NAME)
    if name in known:
        raise SkeletonSchemaError("a joint is listed twice", path=path + ".name", actual=name)
    parent = data["parent"]
    if parent is None:
        if known:
            raise SkeletonSchemaError("only the first joint is the root", path=path + ".parent", actual=parent)
    elif not isinstance(parent, str) or parent not in known:
        raise SkeletonSchemaError("a parent is a joint listed before", path=path + ".parent", actual=parent)
    side = data["side"]
    if type(side) is not int or side not in (-1, 0, 1):
        raise SkeletonSchemaError("side is -1, 0 or 1", path=path + ".side", actual=side, expected=[-1, 0, 1])
    region = data["region"]
    if region not in REGIONS:
        raise SkeletonSchemaError("an unknown region", path=path + ".region", actual=region, expected=REGIONS)
    rows = strict.items(data["dofs"], path + ".dofs", 1, MAX_DOFS)
    dofs = tuple(_dof(row, f"{path}.dofs[{i}]", parent is None) for i, row in enumerate(rows))
    if len({dof.name for dof in dofs}) != len(dofs):
        raise SkeletonSchemaError("control names repeat on a joint", path=path + ".dofs", actual=[d.name for d in dofs])
    turns = [dof.axis for dof in dofs if dof.kind == "rotate"]
    if len({(abs(a.x), abs(a.y), abs(a.z)) for a in turns}) != len(turns):
        raise SkeletonSchemaError("a joint turns about distinct axes", path=path + ".dofs", actual=len(turns))
    tip = None if data.get("tip") is None else strict.vector(data["tip"], path + ".tip", 1.0)
    return Joint(
        name,
        parent,
        side,
        region,
        strict.vector(data["offset"], path + ".offset", 1.0),
        _rest(data["rest"], path + ".rest"),
        dofs,
        tip,
    )


def parse_joint_table(data: object) -> JointTable:
    """Decode an ``srstudio.skeleton-joints/1.x.y`` table without coercion; refuse a digest its names disagree with."""
    fields = (
        "schema",
        "srlocations_commit",
        "srlocations_joints_digest",
        "reference_height_m",
        "head_radius",
        "sole",
        "joints",
    )
    value = strict.fields(data, "table", fields, fields)
    schema = strict.schema(value["schema"], "schema", "srstudio.skeleton-joints", 1)
    commit = strict.text(value["srlocations_commit"], "srlocations_commit", COMMIT)
    digest = strict.text(value["srlocations_joints_digest"], "srlocations_joints_digest", DIGEST)
    height = strict.number(value["reference_height_m"], "reference_height_m", 0.1, 10.0)
    head = strict.number(value["head_radius"], "head_radius", 0.001, 1.0)
    sole = strict.fields(value["sole"], "sole", ("width", "heel"), ("width", "heel"))
    width = strict.number(sole["width"], "sole.width", 0.001, 1.0)
    heel = strict.number(sole["heel"], "sole.heel", 0.001, 1.0)
    known: dict[str, Joint] = {}
    for i, row in enumerate(strict.items(value["joints"], "joints", 1, MAX_JOINTS)):
        joint = _joint(row, f"joints[{i}]", known)
        known[joint.name] = joint
    joints = tuple(known.values())
    if joints_digest(joints) != digest:
        raise SkeletonSchemaError(
            "srlocations_joints_digest does not match the joint and control names",
            path="srlocations_joints_digest",
            actual=joints_digest(joints),
            expected=digest,
        )
    return JointTable(schema, commit, digest, height, head, joints, width, heel)


def read_joint_table(text: str) -> JointTable:
    """Read a joint table from strict JSON text."""
    return parse_joint_table(strict.read(text, "joint table"))


JOINT_TABLE = read_joint_table(resources.files("srstudio").joinpath("assets/skeleton/humanoid.json").read_text())
JOINTS: tuple[Joint, ...] = JOINT_TABLE.joints
BY_NAME = {joint.name: joint for joint in JOINTS}
CONTROLS: tuple[str, ...] = tuple(key for joint in JOINTS for key in joint.controls)
DOFS = {f"{joint.name}.{dof.name}": (joint, dof) for joint in JOINTS for dof in joint.dofs}
ORDER = {key: index for index, key in enumerate(CONTROLS)}


def joint(name: str) -> Joint:
    """The canonical joint called ``name``."""
    try:
        return BY_NAME[name]
    except (KeyError, TypeError):
        raise SkeletonError(
            "no such canonical joint",
            code="skeleton.unknown",
            path=str(name)[:64],
            actual=name,
            expected="a canonical joint name",
        ) from None
