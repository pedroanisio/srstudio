"""The new-reel policy is explicit and checks document and evaluated frame zero."""

import dataclasses
import xml.etree.ElementTree as ET

import pytest

from srstudio import Episode, EpisodeSpec, locations, show
from srstudio.canvas import Signature
from srstudio.framegraph import Frame, Node, drawings
from srstudio.releases import Release
from srstudio.show_gate import new_reel_defects, title_frame_defects
from srstudio.social import InstagramPost, disclosure
from srstudio.thumbnail import ShowCover

POLICY = show.NewReelPolicy(("Alice",))


def reel(series=""):
    return Release(
        "new-reel",
        InstagramPost(
            "One situation",
            "Description",
            credit=disclosure(("Alice",)),
            thumbnail=ShowCover("TITLE", 1, number=212, series=series, series_number=1 if series else 0),
        ),
    )


def scene(extra="", duration="24"):
    return f'<scene><project duration="{duration}"/>{extra}</scene>'.encode()


def test_policy_accepts_24_seconds_and_no_chip_or_code():
    assert new_reel_defects(reel(), scene(), POLICY) == []


@pytest.mark.parametrize(
    "extra, duration, reason",
    [
        ('<group id="sig-code"/>', "24", "signature"),
        ('<group id="sig-code-2"/>', "24", "signature"),
        ('<group id="show-bug-212"/>', "24", "chip"),
        ('', "24.001", "24"),
    ],
)
def test_policy_refuses_code_chip_and_excess_runtime(extra, duration, reason):
    assert any(reason in p for p in new_reel_defects(reel(), scene(extra, duration), POLICY))


def test_series_requires_situation_title_and_oneoff_uses_caption_first_line():
    with pytest.raises(show.NewReelPolicyError, match="situation"):
        POLICY.expected_title(reel("Saga").post)
    assert POLICY.expected_title(reel().post) == "One situation"
    assert show.NewReelPolicy(("Alice",), "Ready in five").expected_title(reel("Saga").post) == "Ready in five"


@pytest.mark.parametrize("title", ["", "two\nlines", " leading "])
def test_policy_refuses_invalid_situation_title(title):
    with pytest.raises(show.NewReelPolicyError):
        show.NewReelPolicy(("Alice",), title)


def title_frame(text="One situation", draw=True, opacity=1, time=0):
    return Frame(
        time, 1080, 1920, (Node(show.TITLE_ID + "-layer", None, "layer", (1, 0, 0, 1, 0, 0), opacity, draw, text),)
    )


def test_frame_zero_title_must_equal_expected_and_be_live():
    assert title_frame_defects(title_frame(), "One situation") == []
    for frame in [
        title_frame("wrong"),
        title_frame(draw=False),
        title_frame(opacity=0),
        title_frame(time=1),
        Frame(0, 1080, 1920, ()),
    ]:
        assert title_frame_defects(frame, "One situation")


def test_default_is_cactus_only_and_explicit_legacy_code_still_draws(project):
    assert Signature().code is None
    ep = Episode(EpisodeSpec(slug="new-reel", title="t", description="d", root=project, seed=1))
    assert ep.spec.signature_code is None
    locations.office_wide(ep.cv, ep.comp)
    assert not ET.fromstring(ep.scene.to_bytes()).findall('.//group[@id="sig-code"]')
    old = Episode(dataclasses.replace(ep.spec, signature_code="SR-1028"))
    locations.office_wide(old.cv, old.comp)
    assert ET.fromstring(old.scene.to_bytes()).find('.//group[@id="sig-code"]') is not None


def test_title_helper_draws_in_safe_area_and_refuses_overlong_line(project):
    ep = Episode(EpisodeSpec(slug="new-reel", title="t", description="d", root=project, seed=1, new_reel_policy=POLICY))
    ep.title_card(reel().post)
    root = ET.fromstring(ep.scene.to_bytes())
    asset = root.find(f'.//text[@id="{show.TITLE_ID}"]')
    assert asset.get("text") == reel().post.title
    assert float(asset.get("size")) >= 0.02 * ep.spec.height
    layer = root.find(f'.//layer[@id="{show.TITLE_ID}-layer"]')
    area = ep.spec.safe_area.region(ep.spec.width, ep.spec.height)
    assert float(layer.get("x")) >= area.x0 and float(layer.get("y")) >= area.y0
    assert float(layer.get("x")) + float(asset.get("width")) <= area.x1
    assert float(layer.get("y")) + float(asset.get("height")) <= area.y1
    assert drawings(ep.scene.to_bytes())
    other = Episode(dataclasses.replace(ep.spec, slug="other"))
    with pytest.raises(show.NewReelPolicyError, match="fit"):
        other.title_card(dataclasses.replace(reel().post, title="Very long words " * 100))


def test_series_title_comes_from_spec_and_must_match_policy(project):
    policy = show.NewReelPolicy(("Alice",), "Ready in five")
    ep = Episode(
        EpisodeSpec(
            slug="new-reel",
            title="t",
            description="d",
            root=project,
            seed=1,
            situation_title="Ready in five",
            new_reel_policy=policy,
        )
    )
    ep.title_card(reel("Saga").post)
    assert b'Ready in five' in ep.scene.to_bytes()
    wrong = Episode(dataclasses.replace(ep.spec, situation_title="Wrong"))
    with pytest.raises(show.NewReelPolicyError):
        wrong.title_card(reel("Saga").post)


def test_default_signature_gate_requires_cactus_only():
    from srstudio import signature

    assert signature.missing(b'<scene><group id="sig-cactus"/></scene>') == []
    assert signature.missing(b'<scene/>') == ["sig-cactus"]
    assert signature.missing(b'<scene><group id="sig-cactus"/></scene>', code="SR-1028") == ["sig-code"]


@pytest.mark.parametrize("duration", ["nan", "inf", "0", "-1"])
def test_nonfinite_or_nonpositive_runtime_is_refused(duration):
    assert new_reel_defects(reel(), scene(duration=duration), POLICY)


def test_opt_in_build_omits_chip_but_legacy_build_keeps_it(project, tmp_path):
    policy_spec = EpisodeSpec(slug="new-reel", title="t", description="d", root=project, seed=1, new_reel_policy=POLICY)
    ep = Episode(policy_spec)
    locations.office_wide(ep.cv, ep.comp)
    ep.title_card(reel().post)
    with show.stamping(212):
        written = ep.finish(tmp_path / "new.scene.xml")
    assert b'show-bug-212' not in written.read_bytes()
    legacy = Episode(dataclasses.replace(policy_spec, new_reel_policy=None, signature_code="SR-1028"))
    locations.office_wide(legacy.cv, legacy.comp)
    with show.stamping(212):
        written = legacy.finish(tmp_path / "legacy.scene.xml")
    assert b'show-bug-212' in written.read_bytes() and b'sig-code' in written.read_bytes()


def test_empty_credit_is_rejected_by_the_policy_with_typed_error():
    from srstudio.social import DisclosureError

    bad = dataclasses.replace(reel(), post=dataclasses.replace(reel().post, credit=""))
    with pytest.raises(DisclosureError):
        new_reel_defects(bad, scene(), POLICY)


def test_spec_with_code_is_rejected_by_title_helper(project):
    ep = Episode(
        EpisodeSpec(
            slug="new-reel",
            title="t",
            description="d",
            root=project,
            seed=1,
            new_reel_policy=POLICY,
            signature_code="SR-1028",
        )
    )
    with pytest.raises(show.NewReelPolicyError, match="signature_code=None"):
        ep.title_card(reel().post)


def test_opted_in_caption_write_refuses_empty_credit_before_writing(project):
    from srstudio.social import DisclosureError

    ep = Episode(EpisodeSpec(slug="new-reel", title="t", description="d", root=project, seed=1, new_reel_policy=POLICY))
    with pytest.raises(DisclosureError):
        ep.instagram(dataclasses.replace(reel().post, credit=""))


def test_title_opens_the_reel_and_leaves_the_picture_after_its_hold(project):
    """The title is an opening, not a band over the whole reel: drawn at frame 0, gone after TITLE_HOLD."""
    ep = Episode(EpisodeSpec(slug="new-reel", title="t", description="d", root=project, seed=1, new_reel_policy=POLICY))
    ep.title_card(reel().post)
    panel = ET.fromstring(ep.scene.to_bytes()).find(f'.//group[@id="{show.TITLE_ID}-panel"]')
    keys = [(float(k.get("time")), float(k.get("value"))) for k in panel.iter() if k.get("time") is not None]
    assert keys and keys[0] == (0.0, 1.0)
    assert keys[-1][1] == 0.0 and keys[-1][0] <= show.TITLE_HOLD + 0.1
