#!/usr/bin/env python3
"""Saga 04 — Card Reader — builds the Saga reel recorded by saga_card_reader_audio.py (ADR 0025).

python3 saga_card_reader.py PROJECT    # → PROJECT/<slug>.scene.xml
"""

from _saga import build
from saga_card_reader_audio import REEL

build(REEL, __file__)
