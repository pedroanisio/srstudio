#!/usr/bin/env python3
"""Saga 15 — Call Juno — builds the Saga reel recorded by saga_call_juno_audio.py (ADR 0025).

python3 saga_call_juno.py PROJECT    # → PROJECT/<slug>.scene.xml
"""

from _saga import build
from saga_call_juno_audio import REEL

build(REEL, __file__)
