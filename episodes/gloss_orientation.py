#!/usr/bin/env python3
"""Gloss 01 — Orientation — builds the Gloss reel recorded by gloss_orientation_audio.py (ADR 0030).

python3 gloss_orientation.py PROJECT    # → PROJECT/<slug>.scene.xml
"""

from _gloss import build
from gloss_orientation_audio import REEL

build(REEL, __file__)
