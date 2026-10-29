"""Every refusal in the limb package is exercised: invalid input fails as a typed LimbError at its own guard."""

from contextlib import contextmanager
from dataclasses import replace

import pytest
from shapely.errors import GEOSException
from shapely.geometry import MultiPolygon, box
from sr_core.scene import Scene

from srstudio import Canvas
from srstudio.limbs import (
    HUMAN,
    ArmProfile,
    Camera,
    Frame,
    HandControl,
    LimbError,
    Quaternion,
    Vec3,
    adapters,
    compile,
    correctives,
    geometry,
    reach,
    serialization,
)
from srstudio.limbs.adapters import Capabilities, VectorAdapter, register_adapter
from srstudio.limbs.compile import BakeOptions, Occlusion, bake, compile_motion
from srstudio.limbs.constraints import hand_pose
from srstudio.limbs.correctives import ContourCorrection, ContourKey
from srstudio.limbs.evaluation import measure
from srstudio.limbs.integration import LimbTrack, prepare_tracks
from srstudio.limbs.interaction import Participant, bake_interaction
from srstudio.limbs.model import DigitProfile, HandProfile
from srstudio.limbs.motion import Action, Attachment, Contact, Motion, Target, TransformKey, TransformTrack
from srstudio.limbs.projection import Projected
from srstudio.limbs.props import clearance
from srstudio.limbs.serialization import motion_dict, parse_motion, save_motion
from srstudio.limbs.validation import audit

TRIANGLE = ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0))


def canvas():
    scene = Scene(version="auto")
    scene.add_project(width=320, height=320, fps="24", duration=2)
    return Canvas(scene, font_asset=None)


def motion(*actions, **options):
    return Motion(ArmProfile(), HUMAN, actions or (Action("point", 0, 2),), **options)


def still(point):
    return TransformTrack.constant(Frame(point))


@contextmanager
def refused(match, code="invalid"):
    """Assert the guard's own message and code, so a different, earlier refusal cannot satisfy the test."""
    with pytest.raises(LimbError, match=match) as caught:
        yield caught
    assert caught.value.code == code


@pytest.fixture
def registry(monkeypatch):
    """A private adapter registry, so adapters registered by one test never leak into another."""
    monkeypatch.setattr(adapters, "_ADAPTERS", dict(adapters._ADAPTERS))


# math3d


def test_vector_division_by_zero_and_zero_directions_are_refused():
    with refused("division by zero"):
        Vec3(1, 2, 3) / 0
    with refused("direction must not be zero"):
        Vec3().unit()
    with refused("zero quaternion"):
        Quaternion(0, 0, 0, 0)


# model


@pytest.mark.parametrize(
    ("make", "match"),
    [
        (lambda: ArmProfile(elbow_limit=(-0.1, 1.0)), "elbow_limit must lie inside"),
        (lambda: ArmProfile(elbow_limit=(0.0, 4.0)), "elbow_limit must lie inside"),
        (lambda: DigitProfile("x", Vec3(), ()), "one to eight phalanges"),
        (lambda: DigitProfile("x", Vec3(), (0.1,) * 9), "one to eight phalanges"),
        (lambda: DigitProfile("x", Vec3(), (0.1, 0.0)), "phalanx lengths must be positive"),
        (lambda: DigitProfile("x", Vec3(), (0.1, 0.1), max_flex=(1.0,)), "same size"),
        (lambda: HandProfile("h", 0.0, 0.3, HUMAN.digits), "hand dimensions must be positive"),
        (lambda: HandProfile("h", 0.3, 0.3, ()), "one to sixteen uniquely named digits"),
        (lambda: HandProfile("h", 0.3, 0.3, HUMAN.digits[:1] * 2), "one to sixteen uniquely named digits"),
        (lambda: HandControl(curls=(("index", 0.1), ("index", 0.2))), "finger curl overrides must be unique"),
    ],
)
def test_anatomy_refuses_out_of_range_profiles(make, match):
    with refused(match):
        make()


def test_hand_pose_lookup_names_the_missing_digit():
    pose = motion().sample(0.5).hand
    with refused("hand has no digit 'claw'"):
        pose.digit("claw")


# constraints


def test_reach_and_hand_construction_refuse_unknown_policies_sides_and_digits():
    with refused("unknown reach policy 'loose'"):
        reach(ArmProfile(), Vec3(0, 1, 0), policy="loose")
    with refused("hand side must be left or right"):
        hand_pose(HUMAN, HandControl(), Frame(), side="up")
    with refused("absent from the hand profile"):
        hand_pose(HUMAN, HandControl(curls=(("claw", 0.5),)), Frame())
    with refused("exceed limits or topology of index", code="joint-limit"):
        hand_pose(HUMAN, HandControl(joints=(("index", (3.0, 3.0, 3.0)),)), Frame())
    with refused("exceed limits or topology of index", code="joint-limit"):
        hand_pose(HUMAN, HandControl(joints=(("index", (0.1,)),)), Frame())


# motion


@pytest.mark.parametrize(
    ("make", "match"),
    [
        (lambda: TransformKey(-1, Frame()), "transform key time must be non-negative"),
        (lambda: TransformTrack(()), "one to 10000 keys"),
        (lambda: Target(Vec3(), space="screen"), "target space must be relative or world"),
        (lambda: Action("point", stroke=0), "gesture phases need a stroke"),
        (lambda: Action("point", preparation=0.4, stroke=0.4, hold=0.2), "positive recovery time"),
        (lambda: Contact("c", 1.0, 0.5, still(Vec3())), "ordered non-negative times"),
        (lambda: Attachment("a", 1.0, 1.0, Frame()), "ordered non-negative times"),
        (lambda: Attachment("a", 0.0, 1.0, Frame(), tolerance=-1), "tolerance must be non-negative"),
        (lambda: motion(reach_policy="loose"), "unknown reach policy"),
        (lambda: motion(Action("point", 0, 2), Action("wave", 1, 2)), "ordered without overlap"),
        (
            lambda: motion(attachments=(Attachment("a", 0, 1, Frame()), Attachment("a", 0, 1, Frame()))),
            "attachment names must be unique",
        ),
        (lambda: motion(contacts=(Contact("c", 3, 4, still(Vec3())),)), "contact c must lie inside one action"),
        (
            lambda: motion(contacts=(Contact("c", 0.5, 1, still(Vec3()), digit="claw"),)),
            "contact names an unknown digit claw",
        ),
    ],
)
def test_motion_parts_refuse_inconsistent_timing_and_references(make, match):
    with refused(match):
        make()


def test_motion_refuses_more_than_ten_thousand_actions():
    actions = tuple(Action("rest", i, 1) for i in range(10001))
    with refused("too many actions"):
        motion(*actions)


def test_attachment_that_would_turn_the_prop_at_acquisition_is_refused():
    hand = motion(Action("grasp", 0, 2)).sample(1.0).hand.frame
    turned = Frame(hand.origin, hand.rotation * Quaternion.axis_angle(Vec3(0, 0, 1), 0.5))
    with refused("prop cup would rotate at acquisition", code="contact"):
        motion(Action("grasp", 0, 2), attachments=(Attachment("cup", 1.0, 1.5, turned),))


def test_motion_sampling_refuses_negative_time_and_unknown_props():
    m = motion()
    with refused("sample time must be non-negative"):
        m.sample(-0.1)
    with refused("unknown attached prop 'cup'"):
        m.prop_frame("cup", 0.5)


def test_joint_overrides_that_do_not_fit_the_hand_are_refused_when_blended():
    absent = motion(Action("point", 0, 2, control=HandControl(joints=(("claw", (0.1,)),))))
    with refused("joint overrides name an absent digit"):
        absent.sample(1.0)
    short = motion(Action("point", 0, 2, control=HandControl(joints=(("index", (0.1,)),))))
    with refused("joint overrides must match the hand topology"):
        short.sample(1.0)


def test_a_clamped_contact_that_cannot_be_reached_reports_its_residual():
    goal = Vec3(0, 10, 0)
    # Orient the contact like the clamped wrist, so only the unreached position can fail.
    wrist = reach(ArmProfile(), goal, pole=Vec3(1, 0, 0), policy="clamp").frame.rotation
    far = Contact("far", 0.5, 1.5, TransformTrack.constant(Frame(goal, wrist)))
    m = motion(contacts=(far,), reach_policy="clamp")
    with refused("contact far has residual", code="contact") as caught:
        m.sample(1.0)
    assert caught.value.residual == pytest.approx(10 - ArmProfile().length)


# projection, props, geometry


@pytest.mark.parametrize(
    ("make", "match", "code"),
    [
        (lambda: Projected([1.0, 2.0], 0.0, 1.0), "immutable x/y pair", "projection"),
        (lambda: Camera(projection="fisheye"), "orthographic or perspective", "invalid"),
        (lambda: Camera(scale=0), "camera scale must be positive", "invalid"),
        (lambda: Camera(near=-1), "camera near must be positive", "invalid"),
        (lambda: Camera(origin=(0, 0, 0)), "camera origin must contain x and y", "invalid"),
    ],
)
def test_projection_refuses_malformed_cameras_and_points(make, match, code):
    with refused(match, code):
        make()


def test_clearance_refuses_a_non_positive_limb_radius():
    with refused("limb collision radius must be positive"):
        clearance(motion().sample(0.5), 0, ())


def test_geometry_refuses_degenerate_contours_and_sizes():
    with refused("fewer than three distinct vertices", code="projection"):
        geometry._hull([(0.0, 0.0), (1.0, 1.0), (0.0, 0.0), (1.0, 1.0)])
    with refused("ribbon needs matching points and widths"):
        geometry.ribbon(((0.0, 0.0),), (1.0,))
    with refused("ribbon needs matching points and widths"):
        geometry.ribbon(((0.0, 0.0), (1.0, 0.0)), (1.0,))
    with refused("a limb contour needs at least three points"):
        geometry.path(((0.0, 0.0), (1.0, 1.0)))
    sample = motion().sample(0.5)
    with refused("limb width and hand thickness must be positive"):
        geometry.project_pose(sample, Camera(), width=0)
    with refused("limb width and hand thickness must be positive"):
        geometry.project_pose(sample, Camera(), width=0.2, thickness=-1)


def test_finger_union_failures_from_the_geometry_engine_become_typed_errors(monkeypatch):
    def failing(_):
        raise GEOSException("TopologyException: side location conflict")

    monkeypatch.setattr(geometry, "unary_union", failing)
    with refused("finger contour union failed: TopologyException", code="geometry"):
        geometry.tube(((0.0, 0.0), (10.0, 0.0)), (2.0, 2.0))
    monkeypatch.setattr(geometry, "unary_union", lambda _: MultiPolygon([box(0, 0, 1, 1), box(3, 0, 4, 1)]))
    with refused("did not produce one valid surface", code="geometry"):
        geometry.tube(((0.0, 0.0), (10.0, 0.0)), (2.0, 2.0))


# correctives


@pytest.mark.parametrize(
    ("make", "match"),
    [
        (lambda: ContourKey(0, TRIANGLE[:2]), "3..1024 vertices"),
        (lambda: ContourKey(0, TRIANGLE * 342), "3..1024 vertices"),
        (lambda: ContourKey(0, ((0.0, 0.0, 0.0), (1.0, 0.0), (0.0, 1.0))), "vertices need x and y"),
        (lambda: ContourCorrection("palm", (ContourKey(0, TRIANGLE),), mirror=1), "mirror must be boolean"),
    ],
)
def test_corrective_contours_refuse_malformed_keys(make, match):
    with refused(match):
        make()


def test_corrective_blending_refuses_a_zero_length_contour():
    with refused("cannot blend a zero-length contour"):
        correctives._corresponding(((0.0, 0.0),) * 3, TRIANGLE)
    with refused("cannot blend a zero-length contour"):
        correctives._corresponding(TRIANGLE, ((0.0, 0.0),) * 3)


# validation


def _evidence():
    m = motion()
    samples = (m.sample(0.5), m.sample(1.0))
    return m, samples, tuple(geometry.project_pose(s, Camera(), width=0.18) for s in samples)


def test_quality_audit_refuses_missing_disordered_and_invisible_evidence():
    m, samples, poses = _evidence()
    with refused("matching nonempty samples"):
        audit((), (), m.arm)
    with refused("matching nonempty samples"):
        audit(samples, poses[:1], m.arm)
    with refused("strictly increasing time order"):
        audit(samples[::-1], poses[::-1], m.arm)
    with refused("no visible geometry"):
        audit(samples, tuple(p.select(set()) for p in poses), m.arm)


def test_quality_audit_refuses_a_stretched_bone():
    m, samples, poses = _evidence()
    arm = samples[0].arm
    stretched = replace(samples[0], arm=replace(arm, elbow=arm.elbow + Vec3(0, 0.1, 0)))
    with refused("bone-length or contact tolerance", code="quality") as caught:
        audit((stretched,), poses[:1], m.arm)
    assert caught.value.residual > 0.01


# compile and integration


@pytest.mark.parametrize(
    ("options", "match"),
    [
        ({"fps": 0}, "fps must be an integer in 1..120"),
        ({"fps": 24.0}, "fps must be an integer in 1..120"),
        ({"max_frames": 100001}, "max_frames must be an integer"),
        ({"max_nodes": True}, "max_nodes must be an integer"),
        ({"duration": 0}, "bake duration must be positive"),
        ({"duration": -1.0}, "bake duration must be positive"),
        ({"offset": -0.5}, "bake offset must be non-negative"),
    ],
)
def test_bake_options_refuse_out_of_range_settings(options, match):
    with refused(match):
        BakeOptions(**options)


def test_frame_count_refuses_a_non_positive_resolved_duration():
    # Public callers resolve the duration from validated options or action ends; the helper still owns its bound.
    with refused("resolved bake duration must be positive"):
        compile._frame_count(0.0, BakeOptions())


@pytest.mark.parametrize(
    ("make", "match"),
    [
        (lambda: Occlusion("", 0, 1), "part pattern"),
        (lambda: Occlusion("digit:*", 0, 1, layer="top"), "behind, body or front layer"),
        (lambda: Occlusion("palm", 1, 1), "ordered and non-negative"),
        (lambda: Occlusion("palm", -1, 1), "ordered and non-negative"),
        (lambda: Occlusion("palm", 0, 1, visible=1), "visibility must be boolean"),
    ],
)
def test_occlusion_rules_refuse_malformed_spans(make, match):
    with refused(match):
        make()


def _limited(name, **capabilities):
    register_adapter(name, VectorAdapter(name, "#ffffff", "#ffffff", capabilities=Capabilities(**capabilities)))


def test_baking_refuses_adapters_without_digits_or_contours(registry):
    _limited("mitten", articulated_digits=False)
    _limited("skin-only", deformation=("skin",))
    with refused("adapter mitten does not support articulated digits"):
        bake(canvas(), None, motion(), id="arm", style="mitten")
    with refused("adapter skin-only does not support contour deformation"):
        bake(canvas(), None, motion(), id="arm", style="skin-only")


def test_compilation_refuses_unknown_backends_budgets_and_missing_skin(registry):
    _limited("contour-only")
    cv = canvas()
    with refused("unknown limb backend 'gpu'"):
        compile_motion(cv, cv.comp, motion(), id="arm", backend="gpu")
    with refused("native limb budget exceeded", code="budget"):
        compile_motion(cv, cv.comp, motion(), id="arm", options=BakeOptions(max_nodes=100))
    with refused("adapter contour-only does not support skin deformation", code="capability"):
        compile_motion(cv, cv.comp, motion(), id="arm", style="contour-only", deformation="skin")


def test_adapter_registration_requires_a_name_a_draw_method_and_capabilities(registry):
    adapter = adapters.adapter_for("toon")
    for name, candidate in (("", adapter), ("drawless", object()), ("implicit", replace(adapter, capabilities=None))):
        with refused("needs a name, draw method and explicit Capabilities"):
            register_adapter(name, candidate)


@pytest.mark.parametrize(
    ("options", "match"),
    [
        ({"backend": "gpu"}, "unknown limb backend gpu"),
        ({"backend": "native", "occlusion": (Occlusion("palm", 0, 1),)}, "separated body/head layers"),
        (
            {"backend": "native", "correctives": (ContourCorrection("palm", (ContourKey(0, TRIANGLE),)),)},
            "artist corrections",
        ),
        ({"deformation": "cloth"}, "unknown limb deformation 'cloth'"),
    ],
)
def test_limb_tracks_refuse_unknown_backends_and_unsupported_native_layers(options, match):
    with refused(match):
        LimbTrack(motion(), **options)


def test_prepared_tracks_need_a_positive_character_end():
    with refused("character end must be positive"):
        prepare_tracks(canvas(), (LimbTrack(motion()),), 0)


def test_interaction_refuses_participants_whose_adapter_cannot_draw_them(registry):
    _limited("mitten", articulated_digits=False)
    _limited("flat", perspective=False)
    _limited("skin-only", deformation=("skin",))
    cv = canvas()
    for style, camera in (("mitten", Camera()), ("flat", Camera(projection="perspective")), ("skin-only", Camera())):
        with refused(f"adapter {style} cannot draw the requested interaction", code="capability"):
            bake_interaction(cv, cv.comp, (Participant("hand", motion(), style=style),), (), id="i", camera=camera)


# serialization


def _document(**motion_fields):
    document = motion_dict(motion())
    document["motion"].update(motion_fields)
    return document


@pytest.mark.parametrize(
    ("document", "match"),
    [
        ([], "motion document must be an object"),
        ({"schema": serialization.SCHEMA, "extra": 1}, r"unknown fields \['extra'\]"),
        ({"schema": serialization.SCHEMA, "generatedBy": 5, "motion": {}}, "generatedBy must be a string"),
        ({"schema": serialization.SCHEMA, "generatedBy": "test"}, "missing motion"),
    ],
)
def test_motion_documents_refuse_malformed_envelopes(document, match):
    with refused(match):
        parse_motion(document)


def test_union_fields_refuse_values_matching_no_declared_type():
    document = _document()
    document["motion"]["actions"][0]["pole"] = "elbow-out"
    with refused(r"motion.actions\[0\].pole: value does not match the declared union type"):
        parse_motion(document)


def test_fixed_arrays_refuse_the_wrong_number_of_elements():
    document = _document()
    document["motion"]["arm"]["elbow_limit"] = [0.0]
    with refused(r"motion.arm.elbow_limit: expected 2 array elements"):
        parse_motion(document)


def test_the_decoding_budget_is_enforced_even_inside_a_union():
    with refused("exceeds its decoding bound", code="budget"):
        serialization._decode(Vec3 | None, {"x": 0, "y": 0, "z": 0}, "pole", [2])
    # Twelve decoded values per full key: 10000 keys exceed the 100000-item bound before any is constructed.
    frame = {"origin": {"x": 0.0, "y": 0.0, "z": 0.0}, "rotation": {"w": 1.0, "x": 0.0, "y": 0.0, "z": 0.0}}
    document = _document(root={"keys": [{"time": float(i), "frame": frame} for i in range(10000)]})
    with refused("exceeds its decoding bound", code="budget"):
        parse_motion(document)


def test_the_decoder_refuses_types_it_cannot_persist():
    with refused("unsupported persisted type"):
        serialization._decode(dict, {}, "extra", [10])


def test_saving_refuses_a_motion_that_would_exceed_the_file_size_limit(tmp_path):
    base = motion(Action("grasp", 0, 2))
    hand = base.sample(1.0).hand.frame
    # Escaped astral-plane names make each attachment large while staying inside the item budget.
    names = ("\U0001f600" * 124 + f"{i:04d}" for i in range(2400))
    heavy = replace(base, attachments=tuple(Attachment(name, 1.0, 1.5, hand) for name in names))
    with refused("exceeds the 5 MiB size limit", code="budget"):
        save_motion(heavy, tmp_path / "heavy.json")
    assert not list(tmp_path.iterdir())


# evaluation


def oversized():
    # 53 paths of about 1 MB each: every attribute stays small enough for the schema check, the whole is not.
    cv = canvas()
    d = "M0 0" + " L1 1" * 200_000
    for _ in range(53):
        cv.path(cv.comp, d, "#ffffff")
    return cv.scene


def test_measurement_refuses_a_scene_beyond_its_byte_bound():
    with refused("exceeds the 50 MiB bound", code="budget"):
        measure("oversized", oversized, repeats=1)
