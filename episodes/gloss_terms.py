#!/usr/bin/env python3
"""Gloss 07 — Terms — builds the Gloss reel recorded by gloss_terms_audio.py (ADR 0030).

python3 gloss_terms.py PROJECT    # → PROJECT/<slug>.scene.xml
"""

from _gloss import build
from gloss_terms_audio import REEL

build(REEL, __file__)
