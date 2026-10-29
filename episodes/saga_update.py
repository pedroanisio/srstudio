#!/usr/bin/env python3
"""Saga 05 — Update — builds the Saga reel recorded by saga_update_audio.py (ADR 0025).

python3 saga_update.py PROJECT    # → PROJECT/<slug>.scene.xml
"""

from _saga import build
from saga_update_audio import REEL

build(REEL, __file__)
