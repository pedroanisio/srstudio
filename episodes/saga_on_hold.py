#!/usr/bin/env python3
"""Saga — builds the Saga reel recorded by saga_on_hold_audio.py (ADR 0025).

python3 saga_on_hold.py PROJECT    # → PROJECT/<slug>.scene.xml
"""

from _saga import build
from saga_on_hold_audio import REEL

build(REEL, __file__)
