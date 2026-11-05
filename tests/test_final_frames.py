"""Final-master review is mandatory, hash bound and measured at native size."""

import dataclasses
import hashlib
import subprocess

import pytest

from srstudio import final_frame_gate as final_frames
from srstudio.framegraph import Box


@pytest.fixture
def master(tmp_path):
    path = tmp_path / 'master.mp4'
    subprocess.run(
        ['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=s=64x64:r=2:d=1', '-c:v', 'libx264', str(path)],
        check=True,
    )
    return path


def reviews(master):
    return tuple(
        final_frames.Review(
            master_sha256=hashlib.sha256(master.read_bytes()).hexdigest(),
            check=check,
            reviewer='human reviewer',
            evidence='full-size review of entire final master',
            verdict='PASS',
            defect_count=0,
            frame_count=2,
            width=64,
            height=64,
            observations=tuple(
                final_frames.Observation(
                    i,
                    i / 2,
                    'shot',
                    'focal',
                    '',
                    'sig-code',
                    'bug-or-story-prop',
                    Box(0, 0, 10, 10),
                    Box(34, 0, 44, 10),
                    'full-size crop',
                )
                for i in range(2)
            )
            if check in final_frames.REGION_CHECKS
            else (),
        )
        for check in final_frames.CHECKS
    )


def test_passing_master_and_report(master):
    result = final_frames.check_master(master, slug='slug', reviews=reviews(master))
    assert not result.refused
    assert len(result.frames) == 2 and result.width == 64 and result.height == 64
    assert result.master_sha256 == hashlib.sha256(master.read_bytes()).hexdigest()
    assert all(c.verdict == 'PASS' and c.review for c in result.checks)
    gap = next(c for c in result.checks if c.check == 'signature_clearance')
    assert gap.measured == gap.limit == 24.0
    assert 'slug' in result.lines()[0] and result.master_sha256 in result.lines()[0]


@pytest.mark.parametrize('check', final_frames.CHECKS)
def test_each_missing_check_refuses(master, check):
    result = final_frames.check_master(
        master, slug='slug', reviews=tuple(r for r in reviews(master) if r.check != check)
    )
    assert result.refused
    assert next(c for c in result.checks if c.check == check).verdict == 'FAIL'
    assert 'missing' in next(c for c in result.checks if c.check == check).reason


@pytest.mark.parametrize(
    'change',
    [
        {'master_sha256': '0' * 64},
        {'frame_count': 1},
        {'width': 32},
        {'verdict': 'FAIL'},
        {'height': None},
        {'height': float('nan')},
        {'height': float('inf')},
        {'reviewer': ''},
        {'evidence': ''},
    ],
)
def test_stale_or_invalid_evidence_refuses(master, change):
    rows = list(reviews(master))
    rows[0] = dataclasses.replace(rows[0], **change)
    assert final_frames.check_master(master, slug='slug', reviews=tuple(rows)).refused


@pytest.mark.parametrize('check', final_frames.REGION_CHECKS)
def test_mandatory_defect_refuses_even_with_pass_disposition(master, check):
    rows = tuple(
        dataclasses.replace(
            r,
            observations=tuple(
                dataclasses.replace(o, intruder='intruding-character', other=Box(9, 0, 20, 10)) for o in r.observations
            ),
        )
        if r.check == check
        else r
        for r in reviews(master)
    )
    result = final_frames.check_master(master, slug='slug', reviews=rows)
    failed = next(c for c in result.checks if c.check == check)
    assert failed.verdict == 'FAIL' and failed.observations[0].time == 0.0
    assert failed.observations[0].crop == Box(0, 0, 10, 10)


def test_inapplicable_requires_reason_and_cannot_excuse_full_size_review(master):
    rows = tuple(
        dataclasses.replace(r, verdict='INAPPLICABLE', reason='') if r.check == 'close_shot' else r
        for r in reviews(master)
    )
    assert final_frames.check_master(master, slug='slug', reviews=rows).refused
    rows = tuple(dataclasses.replace(r, reason='Format has no characters or close shots') for r in rows)
    assert not final_frames.check_master(master, slug='slug', reviews=rows).refused
    rows = tuple(
        dataclasses.replace(r, verdict='INAPPLICABLE', reason='none') if r.check == 'lessons.0034' else r for r in rows
    )
    assert final_frames.check_master(master, slug='slug', reviews=rows).refused


def test_unreadable_master_is_typed_error(tmp_path):
    with pytest.raises(final_frames.FinalFrameError):
        final_frames.check_master(tmp_path / 'missing.mp4', slug='slug')
