#!/usr/bin/env python3
"""Saga 19, Your Half: builds the Saga reel recorded by your_half_audio.py (ADR 0025).

python3 your_half.py PROJECT    # → PROJECT/your-half.scene.xml
"""

from _saga import build
from your_half_audio import REEL

build(REEL, __file__)
