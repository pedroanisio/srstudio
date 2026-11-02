"""Contact events belong to the shared world clock, including camera and parent poses."""

import importlib
from pathlib import Path

import pytest


@pytest.fixture
def proof(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    return importlib.import_module('examples.drawing_proof')


def test_events_join_the_regular_clock_once_without_retiming_samples(proof):
    frames = proof.schedule(fps=2, events=(5, 1.2, 1.2, 0))
    assert [frame.time for frame in frames] == sorted({i / 2 for i in range(12)} | {1.2})
    assert all(frame == proof.sample(frame.time) for frame in frames)
    assert proof.schedule(events=()) == proof.schedule()


@pytest.mark.parametrize('events', [None, [], '1.2', (True,), (-0.1,), (6,), (float('nan'),), (1,) * 33])
def test_invalid_or_unbounded_events_are_refused(proof, events):
    with pytest.raises(ValueError, match='events'):
        proof.schedule(events=events)
