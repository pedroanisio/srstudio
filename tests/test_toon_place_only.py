"""``--place-only`` moves the beats onto the recording already there, and re-makes everything placed from them: the
foley and ``narration.json``. A click tied to a beat follows the beat. A project whose manifest cannot be re-made is
refused by name, and two records from the same takes write the same files."""

import json
import math
import shutil
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from srstudio import foley, music, sketch, toon_sketch
from srstudio.voice import MODEL, Alignment
from support.sketch import SK, FakeClient, confirm_stub

SEED, NOTE = 7, "Narrated by a test tone."
MOVED = replace(SK, caption_min=2.5, tail=0.0)  # a cue change that moves beats on the same recording


def copy_clip(src, dst, clip_in, clip_out, length, gain_db, ffmpeg):
    shutil.copy(src, dst)
    return length


def ding(beats, end):
    """A sound on every placed beat: whichever beat a cue moves, the bed must move with it."""
    return (toon_sketch.Sound("ding", foley.REMOTE_CLICK, tuple(b.start for b in beats), -12.0),)


def record(root: Path, sk: sketch.Sketch = SK) -> None:
    """What ``record_episode`` writes, with a client that says each line as a tone instead of the cloud."""
    rec = sketch.record(sk, root, FakeClient(root), confirm=confirm_stub, conform_clip=copy_clip)
    effects = toon_sketch.sound_effects(rec.beats, rec.end, rec.speech, root, SEED, ding)
    (root / "narration.json").write_text(json.dumps(sketch.manifest(sk, rec, effects, MODEL, NOTE), indent=2) + "\n")


def place_only(root: Path, sk: sketch.Sketch) -> int:
    return toon_sketch.recorder(sk, SEED, NOTE, "Doc", sounds=ding)([str(root), "--place-only"], {})


def written(root: Path) -> dict[str, bytes]:
    """The beats, the lips, the foley and the mix's inputs a record or a re-placement leaves; the takes the client said
    are its cache."""
    names = ["narration.json", *(f"voiced/{n}" for n in ("beats.json", "script.json", "poses.json", "mouths.json"))]
    names += [str(p.relative_to(root)) for p in sorted((root / "audio").glob("*.wav"))]
    return {name: (root / name).read_bytes() for name in names}


def test_place_only_after_a_cue_moves_re_makes_the_sound_tied_to_the_beat(tmp_path):
    record(tmp_path)
    before, _ = sketch.load_beats(tmp_path / "voiced" / "beats.json")
    assert place_only(tmp_path, MOVED) == 0
    beats, end = sketch.load_beats(tmp_path / "voiced" / "beats.json")
    assert [b.start for b in beats] != [b.start for b in before]  # the cue did move a beat
    expected = foley.write_bursts(
        tmp_path / "expected.wav", [b.start for b in beats], end, foley.REMOTE_CLICK, seed=SEED
    )
    assert (tmp_path / "audio" / "ding.wav").read_bytes() == expected.read_bytes()
    manifest = json.loads((tmp_path / "narration.json").read_text())
    entry = next(e for e in manifest["effects"] if e["id"] == "ding")
    assert entry["sha256"] == sketch.sha256_of(tmp_path / "audio" / "ding.wav")
    assert manifest["caption_duration"] == MOVED.end and manifest["voice_note"] == NOTE


def test_place_only_with_no_cue_changed_writes_what_the_record_wrote_byte_for_byte(tmp_path):
    record(tmp_path)
    recorded = written(tmp_path)
    assert place_only(tmp_path, SK) == 0
    assert written(tmp_path) == recorded


def test_place_only_after_a_cue_moves_writes_what_a_new_record_of_it_would(tmp_path):
    """Re-placing on the takes already there and recording again on the same takes give the same project."""
    placed, again = tmp_path / "placed", tmp_path / "again"
    placed.mkdir()
    again.mkdir()
    record(placed)
    assert place_only(placed, MOVED) == 0
    record(again, MOVED)
    assert written(placed) == written(again)


@pytest.mark.parametrize(
    ("spoil", "said"),
    [
        (lambda root: (root / "narration.json").unlink(), "narration.json"),
        (lambda root: (root / "narration.json").write_text("[]"), "narration.json"),
        (lambda root: (root / "narration.json").write_text('{"voice": {}, "items": "lines"}'), "items"),
        (lambda root: (root / "narration.json").write_text('{"items": []}'), "voice"),
    ],
)
def test_place_only_refuses_a_manifest_it_cannot_re_make_and_names_it(tmp_path, spoil, said):
    record(tmp_path)
    spoil(tmp_path)
    beats = (tmp_path / "voiced" / "beats.json").read_bytes()
    with pytest.raises(toon_sketch.PlaceOnlyError, match=said):
        place_only(tmp_path, MOVED)
    assert (tmp_path / "voiced" / "beats.json").read_bytes() == beats  # refused before anything is moved


def test_place_only_refuses_a_manifest_of_other_lines(tmp_path):
    record(tmp_path)
    manifest = json.loads((tmp_path / "narration.json").read_text())
    manifest["items"] = manifest["items"][:2]
    (tmp_path / "narration.json").write_text(json.dumps(manifest))
    with pytest.raises(toon_sketch.PlaceOnlyError, match="2 lines"):
        place_only(tmp_path, MOVED)


def test_two_records_from_the_same_takes_write_the_same_beats_foley_and_mix_inputs(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    record(first)
    record(second)
    assert written(first) == written(second)


class SlowClient(FakeClient):
    """Says each line as a tone of ``per_word`` seconds a word at 44.1 kHz: lengths whose placed ends need a seventh
    decimal, where summing before rounding and rounding before summing part by a microsecond."""

    def __init__(self, folder: Path, per_word: float):
        super().__init__(folder)
        self.per_word = per_word

    def synthesize(self, text, voice, settings):
        self.requests.append((text, voice.name, settings.speed))
        seconds, rate = self.per_word * len(text.split()), 44100
        tone = [0.5 * math.sin(2 * math.pi * 220 * k / rate) for k in range(int(seconds * rate))]
        wav = self.folder / f"{voice.name}-{len(self.requests)}.wav"
        music.write_wav(wav, [0.0] * int(0.05 * rate) + tone, rate)
        self.said[wav] = text
        starts = tuple(round(0.05 + k * seconds / len(text), 6) for k in range(len(text)))
        ends = tuple(round(s + seconds / len(text), 6) for s in starts)
        return SimpleNamespace(wav=wav, alignment=Alignment(tuple(text), starts, ends))


@pytest.mark.parametrize("per_word", [0.3685, 0.4096, 0.437, 0.5055, 0.6288])
def test_a_beat_placed_again_lands_on_the_microsecond_the_record_placed_it(tmp_path, per_word):
    """The record places from the rounded start and length voiced/speech.json keeps, as a re-placement reads them."""
    sketch.record(SK, tmp_path, SlowClient(tmp_path, per_word), confirm=confirm_stub, conform_clip=copy_clip)
    beats = (tmp_path / "voiced" / "beats.json").read_bytes()
    sketch.place_again(SK, tmp_path)
    assert (tmp_path / "voiced" / "beats.json").read_bytes() == beats
