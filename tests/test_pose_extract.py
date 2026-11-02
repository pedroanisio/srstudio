"""The pose extraction tool (ADR 0203), without the estimator: it keeps one dancer by place and by the colours of
their clothes, writes a lost frame rather than a neighbour, and writes only a record srstudio's reader accepts, outside
the repository, directory 700 and file 600. Running the estimator itself needs its own interpreter and a video of real
people, so no test runs it."""

import importlib.util
import stat
import sys
from pathlib import Path

import numpy as np
import pytest

from srstudio import pose_track as pt
from support.pose_records import MODEL, record

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pose_extract", ROOT / "tools" / "pose_extract.py")
assert spec is not None and spec.loader is not None
tool = importlib.util.module_from_spec(spec)
sys.modules["pose_extract"] = tool
spec.loader.exec_module(tool)

W, H = 400, 300
GREY, RED, BLUE = (180, 180, 180), (200, 30, 30), (30, 30, 200)


def body(cx: float, cy: float, torso: float = 40.0, crop: bool = False, seen: float = 0.9) -> "tool.Candidate":
    """A body standing upright with its torso's middle at (cx, cy) pixels."""
    image = np.zeros((33, 5))
    image[:, 3:] = seen
    places = {
        "left_shoulder": (cx + 12, cy - torso / 2),
        "right_shoulder": (cx - 12, cy - torso / 2),
        "left_hip": (cx + 8, cy + torso / 2),
        "right_hip": (cx - 8, cy + torso / 2),
        "left_knee": (cx + 9, cy + torso * 1.4),
        "right_knee": (cx - 9, cy + torso * 1.4),
    }
    image[:, :2] = (cx, cy)
    for name, (x, y) in places.items():
        image[tool.LANDMARK[name], :2] = (x, y)
    return tool.Candidate(image, np.zeros((33, 3)), crop)


def picture(*people: tuple[float, float, tuple[int, int, int]]) -> np.ndarray:
    """A frame with one coloured block per person (torso and legs), on a dark floor."""
    rgb = np.full((H, W, 3), 20, np.uint8)
    for cx, cy, colour in people:
        rgb[int(cy - 22) : int(cy + 60), int(cx - 14) : int(cx + 14)] = colour
    return rgb


def test_a_body_has_a_centre_a_size_and_a_box():
    b = body(100, 120)
    assert np.allclose(b.centre, (100, 120)) and b.size == pytest.approx(40 * tool.BODY)
    x0, y0, x1, y1 = b.box(W, H)
    assert 0 < x0 < x1 < 1 and 0 < y0 < y1 < 1


def test_clothes_tell_two_dancers_apart():
    rgb = picture((100, 120, GREY), (300, 120, RED))
    grey, red = tool.signature(rgb, body(100, 120)), tool.signature(rgb, body(300, 120))
    assert grey.torso is not None and grey.legs is not None and red.seen
    assert tool.distance(grey, grey) == pytest.approx(0.0, abs=1e-6)
    assert tool.distance(grey, red) > 0.8
    unseen = tool.signature(rgb, body(100, 120, seen=0.1))
    assert not unseen.seen and tool.distance(grey, unseen) is None
    legs_only = tool.Colours(None, grey.legs)
    assert tool.distance(grey, legs_only) == pytest.approx(0.0, abs=1e-6)
    learned = legs_only.blend(red, 0.5)
    assert learned.torso is red.torso and 0 < tool.distance(learned, red) < tool.distance(grey, red)


def test_the_central_large_body_is_picked_first_and_followed():
    tracker = tool.Tracker(W, H)
    rgb = picture((90, 120, RED), (210, 120, GREY), (330, 120, BLUE))
    bodies = [body(90, 120), body(210, 120), body(330, 120)]
    colours = [tool.signature(rgb, b) for b in bodies]
    first = tracker.step(bodies, colours)
    assert first is not None and first.index == 1 and tracker.started
    rgb = picture((95, 120, RED), (220, 122, GREY), (330, 120, BLUE))
    moved = [body(95, 120), body(220, 122), body(330, 120)]
    match = tracker.step(moved, [tool.signature(rgb, b) for b in moved])
    assert match is not None and match.index == 1 and match.appearance < 0.1 and match.position < 0.2


def test_the_dancers_colours_settle_over_the_first_matches_and_fill_the_regions_first_unseen():
    tracker = tool.Tracker(W, H)
    usual = tool.signature(picture((200, 120, GREY)), body(200, 120))
    red = tool.signature(picture((200, 120, RED)), body(200, 120))
    assert usual.torso is not None and red.torso is not None
    odd = tool.Colours((0.8 * usual.torso + 0.2 * red.torso).astype(np.float32), None)
    assert 0.3 < tool.distance(odd, usual) < tool.APPEARANCE_LIMIT
    tracker.step([body(200, 120)], [odd])
    assert tracker.colours is not None and tracker.colours.legs is None
    for _ in range(tool.SETTLE - 1):
        assert tracker.step([body(200, 120)], [usual]) is not None
    assert tracker.colours.legs is not None and tool.distance(tracker.colours, usual) < 0.15
    late = tool.Tracker(W, H)
    late.step([body(200, 120)], [tool.Colours(usual.torso, None)])
    late.settled = tool.SETTLE
    shifted = tool.Colours(red.torso, usual.legs)
    match = late.step([body(200, 120)], [tool.Colours(odd.torso, usual.legs)])
    assert match is not None and match.appearance is not None and match.appearance > tool.LEARN_LIMIT
    assert late.colours is not None and late.colours.torso is usual.torso and late.colours.legs is usual.legs
    assert late.step([body(200, 120)], [shifted]) is None


def test_a_neighbour_in_the_dancers_place_is_refused_and_the_frame_is_lost():
    tracker = tool.Tracker(W, H)
    rgb = picture((200, 120, GREY))
    tracker.step([body(200, 120)], [tool.signature(rgb, body(200, 120))])
    rgb = picture((205, 120, RED))
    assert tracker.step([body(205, 120)], [tool.signature(rgb, body(205, 120))]) is None
    assert tracker.lost == 1
    assert tracker.step([], []) is None and tracker.lost == 2


def test_a_far_jump_is_refused_until_the_dancer_has_been_lost_long_enough():
    tracker = tool.Tracker(W, H, "point", (0.2, 0.4))
    rgb = picture((80, 120, GREY))
    tracker.step([body(80, 120, torso=20)], [tool.signature(rgb, body(80, 120, torso=20))])
    far = picture((330, 120, GREY))
    assert tracker.step([body(330, 120, torso=20)], [tool.signature(far, body(330, 120, torso=20))]) is None
    for _ in range(tool.REACQUIRE_AFTER):
        tracker.step([], [])
    found = tracker.step([body(330, 120, torso=20)], [tool.signature(far, body(330, 120, torso=20))])
    assert found is not None and found.position > tool.POSITION_CAP


def test_a_central_pick_lands_a_jump_only_near_the_middle_of_the_frame():
    rgb = picture((200, 120, GREY), (330, 120, GREY), (250, 120, GREY))
    side, middle = body(330, 120), body(250, 120)
    tracker = tool.Tracker(W, H)
    tracker.step([body(200, 120)], [tool.signature(rgb, body(200, 120))])
    for _ in range(tool.REACQUIRE_AFTER):
        tracker.step([], [])
    assert tracker.step([side], [tool.signature(rgb, side)]) is None
    found = tracker.step([side, middle], [tool.signature(rgb, side), tool.signature(rgb, middle)])
    assert found is not None and found.index == 1 and found.position > tool.JUMP
    for x in (270, 290, 310, 330):  # steps, not jumps, may leave the middle
        moved = picture((x, 120, GREY))
        assert tracker.step([body(x, 120)], [tool.signature(moved, body(x, 120))]) is not None


def test_a_jump_never_lands_on_a_smaller_body_behind_the_dancer():
    tracker = tool.Tracker(W, H, "point", (0.5, 0.4))
    rgb = picture((200, 120, GREY))
    for _ in range(3):
        tracker.step([body(200, 120)], [tool.signature(rgb, body(200, 120))])
    behind = body(250, 120, torso=28)
    assert tracker.step([behind], [tool.signature(picture((250, 120, GREY)), behind)]) is None
    near = body(250, 120)
    assert tracker.step([near], [tool.signature(picture((250, 120, GREY)), near)]) is not None


def test_a_point_pick_takes_the_nearest_body_and_unseen_clothes_wait():
    tracker = tool.Tracker(W, H, "point", (0.2, 0.4))
    rgb = picture((80, 120, RED), (210, 120, GREY))
    bodies = [body(80, 120), body(210, 120)]
    hidden = tool.Colours(None, None)
    assert tracker.step(bodies, [hidden, hidden]) is None and not tracker.started
    match = tracker.step(bodies, [tool.signature(rgb, b) for b in bodies])
    assert match is not None and match.index == 0
    with pytest.raises(tool.ExtractError):
        tool.Tracker(W, H, "point")
    with pytest.raises(tool.ExtractError):
        tracker.step(bodies, [hidden])
    with pytest.raises(tool.ExtractError):
        tool.Tracker(W, H).predicted()


def test_a_body_whose_clothes_are_hidden_is_kept_by_place_alone_for_a_bounded_run():
    tracker = tool.Tracker(W, H)
    rgb = picture((200, 120, GREY))
    tracker.step([body(200, 120)], [tool.signature(rgb, body(200, 120))])
    hidden = tool.Colours(None, None)
    pair = [body(202, 121), body(202, 121, crop=True)]
    match = tracker.step(pair, [hidden, hidden])
    assert match is not None and match.index == 1 and match.appearance is None and tracker.blind == 1
    for _ in range(tool.BLIND_RUN - 1):
        assert tracker.step([body(202, 121)], [hidden]) is not None
    assert tracker.step([body(202, 121)], [hidden]) is None and tracker.lost == 1
    tracker.step([body(202, 121)], [tool.signature(rgb, body(202, 121))])
    assert tracker.blind == 0 and tracker.lost == 0


def test_a_hidden_body_is_not_kept_when_another_stands_near_or_it_is_far():
    tracker = tool.Tracker(W, H)
    rgb = picture((200, 120, GREY))
    tracker.step([body(200, 120)], [tool.signature(rgb, body(200, 120))])
    hidden = tool.Colours(None, None)
    crowd = [body(202, 120), body(250, 120)]
    assert tracker.step(crowd, [hidden, hidden]) is None
    assert tracker.step([body(260, 120)], [hidden]) is None and tracker.blind == 0


def test_the_crop_follows_the_predicted_place_and_prefers_a_crop_reading_on_a_tie():
    tracker = tool.Tracker(W, H)
    assert tracker.crop() is None
    rgb = picture((200, 120, GREY))
    tracker.step([body(200, 120)], [tool.signature(rgb, body(200, 120))])
    x0, y0, x1, y1 = tracker.crop()
    assert x0 < 200 < x1 and y0 < 120 < y1
    pair = [body(200, 120), body(200, 120, crop=True)]
    match = tracker.step(pair, [tool.signature(rgb, b) for b in pair])
    assert match is not None and match.index == 1


def test_a_lost_frame_keeps_its_clock_and_a_found_one_its_landmarks():
    lost = tool.frame_entry(3, 30.0, None, None, W, H)
    assert lost == {
        "index": 3,
        "t_s": 0.1,
        "image": None,
        "world": None,
        "box": None,
        "position": None,
        "appearance": None,
        "repeat": False,
    }
    entry = tool.frame_entry(4, 30.0, body(200, 120), tool.Match(0, 0.05, 0.1), W, H)
    assert len(entry["image"]) == 33 and entry["image"][0][:2] == [0.5, 0.4] and entry["position"] == 0.05


def _data(frames):
    estimator = {"name": "synthetic", "version": "1", "model": "m", "model_sha256": MODEL, "licence": "Apache-2.0"}
    source = {"sha256": "ab" * 32, "bytes": 5, "width": W, "height": H, "fps": 30.0, "frames": len(frames)}
    return tool.record(estimator=estimator, source=source, pick="central", point=None, start_frame=0, frames=frames)


def test_the_record_is_checked_and_written_outside_the_repository_privately(tmp_path):
    frames = [tool.frame_entry(i, 30.0, body(200, 120), tool.Match(0, 0.0, 0.0), W, H) for i in range(3)]
    out = tool.write(_data(frames), tmp_path / "study" / "track.json")
    assert pt.load(out).found == 3
    assert stat.S_IMODE(out.stat().st_mode) == 0o600 and stat.S_IMODE(out.parent.stat().st_mode) == 0o700
    with pytest.raises(tool.ExtractError, match="never committed"):
        tool.write(_data(frames), ROOT / "generated" / "track.json")


def test_a_record_the_reader_refuses_is_never_written(tmp_path):
    frames = [tool.frame_entry(i, 30.0, body(200, 120), tool.Match(0, 0.0, 0.0), W, H) for i in range(3)]
    frames[1]["image"][0][3] = 2.0
    with pytest.raises(pt.RecordValueError):
        tool.write(_data(frames), tmp_path / "track.json")
    assert not (tmp_path / "track.json").exists()
    assert pt.from_data(record(5)).found == 5


def test_the_model_must_match_its_pinned_digest(tmp_path):
    with pytest.raises(tool.ExtractError, match="one of"):
        tool.model_file(tmp_path, "lite")
    with pytest.raises(tool.ExtractError, match="missing"):
        tool.model_file(tmp_path, "heavy")
    (tmp_path / "pose_landmarker_heavy.task").write_bytes(b"not the model")
    with pytest.raises(tool.ExtractError, match="pinned"):
        tool.model_file(tmp_path, "heavy")


@pytest.mark.parametrize(("text", "pick"), [("central", ("central", None)), ("0.4,0.6", ("point", (0.4, 0.6)))])
def test_a_pick_is_central_or_a_point_in_the_frame(text, pick):
    assert tool.parse_pick(text) == pick


@pytest.mark.parametrize("text", ["tallest", "0.4", "1.5,0.2"])
def test_a_bad_pick_is_refused(text):
    with pytest.raises(tool.ExtractError):
        tool.parse_pick(text)


class _Mark:
    def __init__(self, x, y, z=0.0, visibility=0.9, presence=None):
        self.x, self.y, self.z, self.visibility, self.presence = x, y, z, visibility, presence


class _Result:
    def __init__(self, n):
        self.pose_landmarks = [[_Mark(0.5, 0.25)] * 33] * n
        self.pose_world_landmarks = [[_Mark(0.1, -0.2, 0.3)] * 33] * n


def test_estimator_poses_become_candidates_in_pixels_of_the_whole_frame():
    whole = tool.bodies_from(_Result(2), W, H)
    assert len(whole) == 2 and whole[0].image[0, :2].tolist() == [200, 75] and whole[0].image[0, 4] == 0.0
    crop = tool.bodies_from(_Result(1), W, H, (100, 50, 200, 100), crop=True)
    assert crop[0].crop and crop[0].image[0, :2].tolist() == [200, 75] and crop[0].world[0].tolist() == [0.1, -0.2, 0.3]


# --- repeated pictures (ADR 0204) -------------------------------------------------------------------------------------


def grey(seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, 256, (96, 128), dtype=np.uint8)


def test_the_same_picture_again_is_a_repeat_even_through_compression_noise():
    still = grey()
    noisy = np.clip(still.astype(int) + np.random.default_rng(1).integers(-1, 2, still.shape), 0, 255).astype(np.uint8)
    assert tool.repeats(still, still) and tool.repeats(still, noisy)


def test_a_moved_hand_or_a_broad_change_is_a_new_grey():
    still = grey()
    moved = still.copy()
    moved[40:48, 60:68] = 255 - moved[40:48, 60:68]  # one block changes a lot: a hand moved
    assert not tool.repeats(still, moved)
    faint = np.clip(still.astype(int) + 3, 0, 255).astype(np.uint8)  # every block changes a little: a fade
    assert not tool.repeats(still, faint)


def test_pictures_of_other_sizes_are_refused():
    with pytest.raises(tool.ExtractError):
        tool.repeats(grey(), grey()[:50])
    with pytest.raises(tool.ExtractError):
        tool.repeats(np.zeros((4, 4), np.uint8), np.zeros((4, 4), np.uint8))


def test_a_repeat_carries_its_clock_and_no_observation_and_the_reader_takes_it():
    entry = tool.repeat_entry(5, 30.0)
    assert entry["repeat"] is True and entry["t_s"] == round(5 / 30, 6) and entry["world"] is None
    first = tool.frame_entry(0, 30.0, body(200, 120), tool.Match(0, 0.05, 0.1), W, H)
    data = _data([first, *(tool.frame_entry(i, 30.0, None, None, W, H) for i in range(1, 5)), entry])
    assert data["schema"] == "srstudio.pose-track/1.1.0"
    track = pt.from_data(data)
    assert track.frames[5].repeat and track.repeats == 1
