"""Photo placement records remain public and resolvable without importing the episode builder first."""

import json
import pickle
import subprocess
import sys

from srstudio.collage_group import Place


def test_cold_photo_import_resolves_the_actual_place_type():
    code = '''
import json
from collections.abc import Mapping
from typing import get_type_hints
from srstudio import collage_photo
from srstudio.collage_group import Place
assert get_type_hints(collage_photo.print_photo)['places'] == Mapping[str, Place]
print(json.dumps({'module': Place.__module__, 'name': Place.__qualname__}))
'''
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {'module': 'srstudio.collage_group', 'name': 'Place'}


def test_public_place_pickle_and_projection_remain_compatible():
    place = Place(400, 1800, 0.5)
    assert place.transform() == (130, 840)
    assert place.seen((540, 1920)) == (400, 1800)
    restored = pickle.loads(pickle.dumps(place))
    assert type(restored) is Place and restored == place
    assert Place.__module__ == 'srstudio.collage_group'
