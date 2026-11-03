"""Phone buzz sampling has a deterministic preflight bound and representable turnover phases."""

import pytest

from srstudio import cutout_call as call
from srstudio import registry
from support.saga import canvas


@pytest.mark.parametrize('buzzes', [((0, 0.13),), ((0, 0.04), (1, 1.08))])
def test_buzz_budget_counts_initial_terminal_and_all_spans_before_drawing(monkeypatch, buzzes):
    monkeypatch.setattr(call, 'MAX_BUZZ_KEYS', 5, raising=False)
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(call.CutoutCallError, match='budget'):
        call.desk_phone(cv, cv.comp, buzzes=buzzes)
    assert cv.scene.to_bytes() == before


def test_exact_buzz_budget_preserves_small_valid_motion(monkeypatch):
    monkeypatch.setattr(call, 'MAX_BUZZ_KEYS', 5, raising=False)
    cv = canvas()
    assert call.desk_phone(cv, cv.comp, buzzes=((0, 0.1),)) is not None


def test_turnover_cannot_collapse_its_two_phases_before_drawing():
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(call.CutoutCallError, match='phase'):
        call.desk_phone(cv, cv.comp, turns=1e16)
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize('buzzes', [((0, 1e308),), ((1e16, 1e16 + 2),)])
def test_extreme_buzzes_are_refused_before_scene_mutation(buzzes):
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(call.CutoutCallError):
        call.desk_phone(cv, cv.comp, buzzes=buzzes)
    assert cv.scene.to_bytes() == before


def test_span_collection_is_bounded_even_for_an_endless_input(monkeypatch):
    monkeypatch.setattr(call, 'MAX_BUZZ_KEYS', 5)
    consumed = []

    def spans():
        i = 0
        while True:
            consumed.append(i)
            yield (i, i + 0.01)
            i += 1

    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(call.CutoutCallError, match='budget'):
        call.desk_phone(cv, cv.comp, buzzes=spans())
    assert len(consumed) == 3 and cv.scene.to_bytes() == before


def test_discovery_names_the_real_sample_budget():
    data = registry.describe('prop', 'desk-phone')['contract']
    assert str(call.MAX_BUZZ_KEYS) in ' '.join(data['constraints'])
