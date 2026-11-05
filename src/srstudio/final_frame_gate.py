"""Hash-bound full-size final-master review and native-pixel measurements (ADR 0247).

Scene geometry cannot clear this gate. Observations are human-identified visible
regions on the decoded final master, including camera transforms and occlusion.
No review is created here. Missing, stale or incomplete evidence refuses staging.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .frame_gates import FrameGateError
from .framegraph import Box

__all__ = ['CheckResult', 'FinalFrameError', 'FinalFrameResult', 'Observation', 'Review', 'check_master']

CHECKS = (
    'anatomy',
    'show',
    'captions',
    'safe_areas',
    'marks',
    'staging',
    'close_shot',
    'signature_clearance',
    'signature_props',
    'lessons.0034',
    'lessons.0035',
)
REGION_CHECKS = ('close_shot', 'signature_clearance', 'signature_props')
CLEARANCE = 24.0
RECORD = 'final-frame-review.json'
Verdict = Literal['PASS', 'FAIL', 'INAPPLICABLE']


class FinalFrameError(FrameGateError):
    """A master or its typed review evidence cannot be read."""


@dataclass(frozen=True)
class DecodedFrame:
    index: int
    time: float
    sha256: str


@dataclass(frozen=True)
class Observation:
    """Visible final-frame regions, in native pixels. ``crop`` is the full-size
    crop rectangle, recoverable using frame index and the bound master hash.
    ``other`` is the bug or a visible story-prop region, independently reviewed.
    A close shot names its focal character; an intruder always fails.
    """

    frame: int
    time: float
    shot: str
    focal: str
    intruder: str
    mark_id: str
    other_id: str
    crop: Box
    other: Box | None
    evidence: str
    reason: str = ''


@dataclass(frozen=True)
class Review:
    """A human record keyed by master hash and check, covering every decoded
    frame at native size. INAPPLICABLE requires a format-specific reason;
    lessons.0034 and lessons.0035 always require a full-size human review.
    Region checks enumerate every relevant mark/prop/character on each frame.
    Use an inapplicable record for a format with no such content.
    """

    master_sha256: str
    check: str
    reviewer: str
    evidence: str
    width: int
    height: int
    frame_count: int
    verdict: Verdict
    reason: str = ''
    observations: tuple[Observation, ...] = ()
    defect_count: int | None = None


@dataclass(frozen=True)
class CheckResult:
    slug: str
    check: str
    verdict: Verdict
    measured: float | None
    limit: float | None
    master_sha256: str
    reason: str
    review: Review | None
    observations: tuple[Observation, ...] = ()


@dataclass(frozen=True)
class FinalFrameResult:
    slug: str
    master_sha256: str
    width: int
    height: int
    frames: tuple[DecodedFrame, ...]
    checks: tuple[CheckResult, ...]

    @property
    def refused(self) -> bool:
        return any(c.verdict == 'FAIL' for c in self.checks)

    def lines(self) -> list[str]:
        lines = [
            f'frames {self.slug}: {"REFUSED" if self.refused else "PASS"} sha256={self.master_sha256} '
            f'{self.width}x{self.height} frames={len(self.frames)}'
        ]
        for c in self.checks:
            lines.append(
                f'  {c.check}: {c.verdict} measured={c.measured} limit={c.limit}; {c.reason}; '
                f'review={c.review.evidence if c.review else "missing"}'
            )
            for o in c.observations:
                lines.append(
                    f'    shot={o.shot} frame={o.frame} time={o.time:g}s focal={o.focal} '
                    f'intruder={o.intruder} mark={o.mark_id} other={o.other_id} '
                    f'crop={tuple(o.crop)} other_region={tuple(o.other) if o.other else None} '
                    f'evidence={o.evidence} reason={o.reason}'
                )
        return lines


def _edge_gap(a: Box, b: Box) -> float:
    """Shortest Euclidean edge distance of two visible bounding regions."""
    if not isinstance(a, Box) or not isinstance(b, Box):
        raise FinalFrameError('missing typed visible bounds')
    if not all(type(v) in (int, float) and math.isfinite(v) for v in (*a, *b)):
        raise FinalFrameError('missing or non-finite visible bounds')
    if a.area <= 0 or b.area <= 0:
        raise FinalFrameError('empty visible bounds')
    return math.hypot(max(a.left - b.right, b.left - a.right, 0), max(a.top - b.bottom, b.top - a.bottom, 0))


def _hash(path: Path) -> str:
    try:
        with path.open('rb') as stream:
            digest = hashlib.sha256()
            while block := stream.read(1024 * 1024):
                digest.update(block)
            return digest.hexdigest()
    except OSError as exc:
        raise FinalFrameError(f'{path}: {exc}') from exc


def _decode(master: Path, ffmpeg: str, ffprobe: str) -> tuple[int, int, tuple[DecodedFrame, ...]]:
    try:
        probed = subprocess.run(
            [
                ffprobe,
                '-v',
                'error',
                '-select_streams',
                'v:0',
                '-show_streams',
                '-show_frames',
                '-show_entries',
                'stream=width,height:frame=best_effort_timestamp_time',
                '-of',
                'json',
                str(master),
            ],
            check=True,
            capture_output=True,
        )
        data = json.loads(probed.stdout)
        (stream,) = data['streams']
        width, height = stream['width'], stream['height']
        if type(width) is not int or type(height) is not int or min(width, height) <= 0:
            raise ValueError('missing native frame dimensions')
        times = [float(f['best_effort_timestamp_time']) for f in data['frames']]
        if not times or any(not math.isfinite(t) or t < 0 for t in times):
            raise ValueError('missing or non-finite frame timestamps')
        if any(b <= a for a, b in zip(times, times[1:], strict=False)):
            raise ValueError('non-increasing frame timestamps')
        size = width * height * 3
        frames = []
        # Stream native RGB frames: no fps filter, resize, sampled contact sheet or whole-movie allocation.
        with tempfile.TemporaryFile() as errors:
            with subprocess.Popen(
                [
                    ffmpeg,
                    '-v',
                    'error',
                    '-i',
                    str(master),
                    '-map',
                    '0:v:0',
                    '-vsync',
                    '0',
                    '-f',
                    'rawvideo',
                    '-pix_fmt',
                    'rgb24',
                    '-',
                ],
                stdout=subprocess.PIPE,
                stderr=errors,
            ) as process:
                assert process.stdout is not None
                for index, time in enumerate(times):
                    raw = process.stdout.read(size)
                    if len(raw) != size:
                        process.kill()
                        raise ValueError(f'incomplete decoded frame {index}')
                    frames.append(DecodedFrame(index, time, hashlib.sha256(raw).hexdigest()))
                if process.stdout.read(1):
                    process.kill()
                    raise ValueError('decoded frame count does not match timestamps')
                if process.wait() != 0:
                    raise ValueError('ffmpeg could not decode the master')
        return width, height, tuple(frames)
    except (OSError, subprocess.CalledProcessError, ValueError, KeyError, TypeError) as exc:
        raise FinalFrameError(f'{master}: final-frame decode: {exc}') from exc


def _judge(review: Review, frames: tuple[DecodedFrame, ...], width: int, height: int) -> tuple[float | None, str, bool]:
    if type(review.reason) is not str:
        raise FinalFrameError('review reason must be text')
    if review.verdict not in ('PASS', 'FAIL', 'INAPPLICABLE'):
        raise FinalFrameError('invalid review disposition')
    if not all(type(v) is str and v.strip() for v in (review.reviewer, review.evidence)):
        raise FinalFrameError('missing human reviewer or evidence')
    if any(type(v) is not int for v in (review.width, review.height, review.frame_count)):
        raise FinalFrameError('review dimensions and frame count must be integers')
    if (review.width, review.height, review.frame_count) != (width, height, len(frames)):
        raise FinalFrameError('stale full-size review coverage')
    if review.verdict == 'FAIL':
        return None, review.reason or 'human review confirms a mandatory defect', True
    if review.verdict == 'INAPPLICABLE':
        if review.check.startswith('lessons.') or not isinstance(review.reason, str) or not review.reason.strip():
            raise FinalFrameError('missing justified format-specific inapplicability reason')
        return None, review.reason, False
    if review.check not in REGION_CHECKS:
        if type(review.defect_count) is not int or review.defect_count < 0:
            raise FinalFrameError('missing or invalid reviewed defect count')
        return (
            float(review.defect_count),
            review.reason or 'full-size human review of every decoded frame',
            review.defect_count > 0,
        )
    if not isinstance(review.observations, tuple) or any(not isinstance(o, Observation) for o in review.observations):
        raise FinalFrameError('missing typed frame observations')
    if any(type(o.frame) is not int for o in review.observations):
        raise FinalFrameError('invalid measured frame index')
    if {o.frame for o in review.observations} != set(range(len(frames))):
        raise FinalFrameError('missing required per-frame region review')
    gaps: list[float] = []
    failures: list[str] = []
    for o in review.observations:
        if type(o.frame) is not int or not 0 <= o.frame < len(frames):
            raise FinalFrameError('invalid measured frame index')
        if type(o.time) not in (int, float) or not math.isfinite(o.time) or o.time != frames[o.frame].time:
            raise FinalFrameError('missing, non-finite or stale measured frame time')
        if not all(type(v) is str and v.strip() for v in (o.shot, o.evidence)):
            raise FinalFrameError('missing shot or full-size crop evidence')
        if review.check == 'close_shot':
            _edge_gap(o.crop, o.crop)  # validate the full-size crop even without an intruder
            if o.crop.within(width, height) != o.crop:
                raise FinalFrameError('visible region lies outside decoded frame')
            if not isinstance(o.focal, str) or not o.focal.strip() or type(o.intruder) is not str:
                raise FinalFrameError('missing character ownership review')
            if o.intruder:
                failures.append(f'frame {o.frame} at {o.time:g}s: {o.intruder} intrudes on {o.focal}')
        else:
            if o.other is None:
                _edge_gap(o.crop, o.crop)
                if o.crop.within(width, height) != o.crop:
                    raise FinalFrameError('full-size crop lies outside decoded frame')
                if type(o.reason) is not str or not o.reason.strip() or o.mark_id or o.other_id:
                    raise FinalFrameError('missing bug/prop/signature geometry or per-frame inapplicability reason')
                continue
            gap = _edge_gap(o.crop, o.other)
            if any(b.within(width, height) != b for b in (o.crop, o.other)):
                raise FinalFrameError('visible region lies outside decoded frame')
            if not all(type(v) is str and v.strip() for v in (o.mark_id, o.other_id)):
                raise FinalFrameError('missing signature or bug/prop IDs')
            gaps.append(gap)
            overlaps = (
                o.crop.left < o.other.right
                and o.other.left < o.crop.right
                and o.crop.top < o.other.bottom
                and o.other.top < o.crop.bottom
            )
            if (review.check == 'signature_clearance' and gap < CLEARANCE) or (
                review.check == 'signature_props' and overlaps
            ):
                failures.append(f'frame {o.frame} at {o.time:g}s: {o.mark_id}/{o.other_id} gap={gap:g}px')
    value = (
        float(sum(bool(o.intruder) for o in review.observations))
        if review.check == 'close_shot'
        else min(gaps)
        if gaps
        else None
    )
    reason = '; '.join(failures)
    if value is None and not failures:
        reason = 'inapplicable on every reviewed frame: ' + '; '.join(sorted({o.reason for o in review.observations}))
    return value, reason, bool(failures)


def check_master(
    master: Path,
    *,
    slug: str,
    reviews: Sequence[Review] = (),
    review_path: Path | None = None,
    ffmpeg: str = 'ffmpeg',
    ffprobe: str = 'ffprobe',
) -> FinalFrameResult:
    """Public pre-staging suite, shared unchanged by delivery and pilot callers.

    All mandatory checks refuse absent/stale evidence. The equivalent human
    final-frame checker supports formats the scene engine cannot evaluate.
    Review observations never take geometry from a scene or infer identity
    from its medium. Results include every check, even justified inapplicability.
    """
    if review_path is not None:
        if reviews:
            raise FinalFrameError('supply typed reviews or a review path, not both')
        reviews = _read_reviews(review_path)
    before = _hash(master)
    if any(not isinstance(r, Review) for r in reviews):
        raise FinalFrameError('expected typed human Review records')
    width, height, frames = _decode(master, ffmpeg, ffprobe)
    if _hash(master) != before:
        raise FinalFrameError('master changed while decoding')
    results = []
    for check in CHECKS:
        matches = [r for r in reviews if r.check == check]
        review = matches[0] if len(matches) == 1 else None
        value: float | None = None
        verdict: Verdict = 'FAIL'
        try:
            if review is None:
                raise FinalFrameError('missing or duplicate required human review')
            if review.master_sha256 != before:
                raise FinalFrameError('stale review: master sha256 differs')
            value, reason, failed = _judge(review, frames, width, height)
            if not failed:
                verdict = review.verdict
                if value is None and check in ('signature_clearance', 'signature_props'):
                    verdict = 'INAPPLICABLE'
            if not reason:
                reason = 'all reviewed final-frame regions pass'
        except FinalFrameError as exc:
            reason = str(exc)
        results.append(
            CheckResult(
                slug,
                check,
                verdict,
                value,
                CLEARANCE if check == 'signature_clearance' else 0.0,
                before,
                reason,
                review,
                review.observations if review else (),
            )
        )
    return FinalFrameResult(slug, before, width, height, frames, tuple(results))


def _read_reviews(path: Path) -> tuple[Review, ...]:
    """Read typed evidence; absent evidence remains missing. Never create records."""
    if not path.exists():
        return ()
    try:
        data = json.loads(path.read_bytes())
        if not isinstance(data, list):
            raise ValueError('expected a list of human review records')
        result = []
        for record in data:
            observations = tuple(
                Observation(
                    **(o | {'crop': Box(*o['crop']), 'other': Box(*o['other']) if o['other'] is not None else None})
                )
                for o in record.get('observations', [])
            )
            result.append(Review(**(record | {'observations': observations})))
        return tuple(result)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        raise FinalFrameError(f'{path}: invalid final-frame review: {exc}') from exc
