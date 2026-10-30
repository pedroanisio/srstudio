#!/usr/bin/env python3
"""Saga 17 — Typing — builds the Saga reel recorded by saga_typing_audio.py (ADR 0025).

python3 saga_typing.py PROJECT    # → PROJECT/<slug>.scene.xml
"""

from _saga import build
from saga_typing_audio import REEL

build(REEL, __file__)
