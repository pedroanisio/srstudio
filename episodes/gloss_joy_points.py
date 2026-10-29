#!/usr/bin/env python3
"""Gloss 02 — Joy Points — builds the Gloss reel recorded by gloss_joy_points_audio.py (ADR 0030).

python3 gloss_joy_points.py PROJECT    # → PROJECT/<slug>.scene.xml
"""

from _gloss import build
from gloss_joy_points_audio import REEL

build(REEL, __file__)
