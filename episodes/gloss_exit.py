#!/usr/bin/env python3
"""Gloss 05 — Exit — builds the Gloss reel recorded by gloss_exit_audio.py (ADR 0030).

python3 gloss_exit.py PROJECT    # → PROJECT/<slug>.scene.xml
"""

from _gloss import build
from gloss_exit_audio import REEL

build(REEL, __file__)
