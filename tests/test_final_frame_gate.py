"""Final-master review is mandatory, hash-bound and measured in native pixels."""

import dataclasses
import hashlib
import subprocess

import pytest

from srstudio import final_frame_gate as gate
from srstudio.framegraph import Box


@pytest.fixture
def master(tmp_path):
    path = tmp_path / 'short.mp4'
    subprocess.run(
        [
            'ffmpeg',
            '-v',
            'error',
            '-f',
            'lavfi',
            '-i',
            'color=black:s=64x64:r=2:d=1',
            '-c:v',
            'libx264',
            '-pix_fmt',
            'yuv420p',
            str(path),
        ],
        check=True,
    )
    return path


def reviews(result):
    return tuple(
        gate.Review(
            result.master_sha256,
            check,
            'test reviewer',
            'fixture evidence',
            result.width,
            result.height,
            len(result.frames),
            'PASS',
            defect_count=0,
            observations=tuple(
                gate.Observation(
                    f.index,
                    f.time,
                    'shot',
                    'focal',
                    '',
                    'sig-code',
                    'bug',
                    Box(0, 0, 10, 10),
                    Box(34, 0, 44, 10),
                    'reviewed full-size frame',
                )
                for f in result.frames
            )
            if check in ('close_shot', 'signature_clearance', 'signature_props')
            else (),
        )
        for check in gate.CHECKS
    )


def test_full_size_passing_master_and_report(master):
    missing = gate.check_master(master, slug='short')
    assert missing.refused
    assert missing.master_sha256 == hashlib.sha256(master.read_bytes()).hexdigest()
    assert (missing.width, missing.height, len(missing.frames)) == (64, 64, 2)
    result = gate.check_master(master, slug='short', reviews=reviews(missing))
    assert not result.refused
    assert all(c.verdict == 'PASS' for c in result.checks)
    clearance = next(c for c in result.checks if c.check == 'signature_clearance')
    assert clearance.measured == 24 and clearance.limit == 24
    assert clearance.master_sha256 == result.master_sha256
    assert clearance.observations[0].mark_id == 'sig-code'
    assert clearance.observations[0].other_id == 'bug'
    assert clearance.observations[0].time == 0
    assert clearance.observations[0].crop == Box(0, 0, 10, 10)
    assert 'short' in result.lines()[0]


@pytest.mark.parametrize('check', gate.CHECKS)
def test_every_missing_stale_or_failed_review_refuses(master, check):
    result = gate.check_master(master, slug='short')
    records = reviews(result)
    for changes in ({'master_sha256': '0' * 64}, {'verdict': 'FAIL'}, {'frame_count': 1}, {'evidence': ''}):
        changed = tuple(dataclasses.replace(r, **changes) if r.check == check else r for r in records)
        assert gate.check_master(master, slug='short', reviews=changed).refused
    assert gate.check_master(master, slug='short', reviews=tuple(r for r in records if r.check != check)).refused


@pytest.mark.parametrize('check', ['close_shot', 'signature_clearance', 'signature_props'])
def test_confirmed_intrusion_clearance_and_prop_obstruction_refuse(master, check):
    result = gate.check_master(master, slug='short')
    records = reviews(result)
    changed = []
    for r in records:
        if r.check == check:
            changes = {'intruder': 'other-character'} if check == 'close_shot' else {'other': Box(9, 0, 20, 10)}
            r = dataclasses.replace(r, observations=tuple(dataclasses.replace(o, **changes) for o in r.observations))
        changed.append(r)
    report = gate.check_master(master, slug='short', reviews=changed)
    assert report.refused
    failed = next(c for c in report.checks if c.check == check)
    assert failed.verdict == 'FAIL' and failed.observations
    assert failed.observations[0].focal == 'focal'


@pytest.mark.parametrize('value', [float('nan'), float('inf'), None])
def test_invalid_or_missing_geometry_is_refused(master, value):
    result = gate.check_master(master, slug='short')
    records = reviews(result)
    changed = tuple(
        dataclasses.replace(
            r, observations=tuple(dataclasses.replace(o, crop=Box(value, 0, 10, 10)) for o in r.observations)
        )
        if r.check == 'signature_clearance'
        else r
        for r in records
    )
    assert gate.check_master(master, slug='short', reviews=changed).refused


def test_missing_frames_duplicate_reviews_and_unjustified_skip_refuse(master):
    result = gate.check_master(master, slug='short')
    records = reviews(result)
    assert gate.check_master(master, slug='short', reviews=(*records, records[0])).refused
    for changes in ({'observations': ()}, {'verdict': 'INAPPLICABLE', 'reason': ''}):
        changed = tuple(dataclasses.replace(r, **changes) if r.check == 'close_shot' else r for r in records)
        assert gate.check_master(master, slug='short', reviews=changed).refused


def test_decode_failure_has_typed_error(tmp_path):
    with pytest.raises(gate.FinalFrameError):
        gate.check_master(tmp_path / 'absent.mp4', slug='absent')


def test_review_file_is_optional_input_but_mandatory_evidence(master, tmp_path):
    assert gate.check_master(master, slug='short', review_path=tmp_path / 'missing.json').refused
    malformed = tmp_path / 'malformed.json'
    malformed.write_text('{}')
    with pytest.raises(gate.FinalFrameError, match='invalid final-frame review'):
        gate.check_master(master, slug='short', review_path=malformed)
    records = reviews(gate.check_master(master, slug='short'))
    with pytest.raises(gate.FinalFrameError, match='not both'):
        gate.check_master(master, slug='short', reviews=records, review_path=malformed)


@pytest.mark.parametrize('count', [None, float('nan'), float('inf'), True, '0', -1, 1])
def test_missing_invalid_or_positive_reviewed_defect_count_refuses(master, count):
    records = reviews(gate.check_master(master, slug='short'))
    records = tuple(dataclasses.replace(r, defect_count=count) if r.check == 'anatomy' else r for r in records)
    assert gate.check_master(master, slug='short', reviews=records).refused


def test_anatomy_body_path_requires_close_shot_review_on_explicit_final_master(master, tmp_path, monkeypatch):
    from srstudio import anatomy_gate
    from srstudio.releases import Release
    from srstudio.social import InstagramPost

    releases = {'short': Release('short', InstagramPost('t', 'd'))}
    first = {'short': 'short'}
    assert anatomy_gate.body_defects(releases, tmp_path, first, 'unused', final_masters={'short': master})
    records = reviews(gate.check_master(master, slug='short'))
    monkeypatch.setattr(gate, '_read_reviews', lambda path: records)
    assert anatomy_gate.body_defects(releases, tmp_path, first, 'unused', final_masters={'short': master}) == []


def test_master_delivery_boundary_refuses_even_without_prosody_binding(master, tmp_path, monkeypatch):
    from srstudio import master_gate
    from srstudio.releases import Release
    from srstudio.social import InstagramPost

    monkeypatch.setattr(master_gate, 'judge', lambda *args, **kwargs: master_gate.Reading('short', False))
    result = master_gate.read(
        {'short': Release('short', InstagramPost('t', 'd'))}, tmp_path, tmp_path, {'short': 'short'}
    )
    assert result['short'].refused
    assert master_gate.refusals(result)
    assert any('sha256=' in line for line in master_gate.lines(result))
