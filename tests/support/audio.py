"""What test_audio.py shares with other test modules."""

from __future__ import annotations

import hashlib
import json
import math
import shutil

from srstudio import EpisodeSpec
from srstudio.generated import PlacedClip, Placement
from support.generated import SPEECH, write_wav


def spec(root, **kw) -> EpisodeSpec:
    return EpisodeSpec(slug="t", title="t", description="t", root=root, seed=1, **kw)


def clips_project(project, tmp_path, role="dialogue"):
    root = tmp_path / "ep"
    shutil.copytree(project, root)
    wav = write_wav(root / "assets" / "generated" / "line-1.wav", [0.3 * math.sin(i / 7) for i in range(4800)])
    clip = PlacedClip(SPEECH, hashlib.sha256(wav.read_bytes()).hexdigest(), Placement(start=0.5, role=role))
    data = json.loads((root / "dialogue.json").read_text())
    data["clips"] = [clip.to_dict()]
    (root / "dialogue.json").write_text(json.dumps(data))
    write_wav(root / "assets" / "groove.wav", [0.1] * 4800)
    return root
