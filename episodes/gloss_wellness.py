#!/usr/bin/env python3
"""Gloss 06 — Wellness — builds the Gloss reel recorded by gloss_wellness_audio.py (ADR 0030).

python3 gloss_wellness.py PROJECT    # → PROJECT/<slug>.scene.xml
"""

from _gloss import build
from gloss_wellness_audio import REEL

build(REEL, __file__)
