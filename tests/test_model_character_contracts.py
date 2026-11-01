"""Optional model characters keep body geometry separate from validated plate-face data."""

import pytest

from srstudio import pedro, registry


def test_optional_pedro_registration_describes_the_body_and_face_blend():
    contract = registry.describe('character', 'pedro')['contract']
    assert contract['capabilities']['expressions'] is False
    assert contract['capabilities']['head_motion'] is False
    assert contract['capabilities']['limbs'] is False
    props = contract['operations']['face']['arguments']['properties']
    assert props['toward']['enum'] == ['', *pedro.MOODS]
    assert props['share']['enum'] == list(pedro.SHARES)
    assert props['share']['x-unit'] == 'ratio'
    assert props['turn']['x-unit'] == 'degrees'
    assert 'needs a target mood' in ' '.join(contract['operations']['face']['constraints'])
    with pytest.raises(pedro.PedroError, match='needs a mood'):
        pedro.Face(share=props['share']['enum'][-1])
    face = pedro.Face(toward=props['toward']['enum'][-1], share=props['share']['enum'][-1])
    assert face.share == pedro.SHARES[-1]
