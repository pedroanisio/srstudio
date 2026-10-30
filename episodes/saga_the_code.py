#!/usr/bin/env python3
"""Saga 13 — The Code — builds the Saga reel recorded by saga_the_code_audio.py (ADR 0025).

python3 saga_the_code.py PROJECT    # → PROJECT/<slug>.scene.xml
"""

from _saga import build
from saga_the_code_audio import REEL

build(REEL, __file__)
