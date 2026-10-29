#!/usr/bin/env python3
"""Gloss 03 — Trust Exercise — builds the Gloss reel recorded by gloss_trust_fall_audio.py (ADR 0030).

python3 gloss_trust_fall.py PROJECT    # → PROJECT/<slug>.scene.xml
"""

from _gloss import build
from gloss_trust_fall_audio import REEL

build(REEL, __file__)
