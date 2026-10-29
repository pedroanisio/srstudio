#!/usr/bin/env python3
"""Saga 03 — Group Chat — builds the Saga reel recorded by saga_group_chat_audio.py (ADR 0025).

python3 saga_group_chat.py PROJECT    # → PROJECT/<slug>.scene.xml
"""

from _saga import build
from saga_group_chat_audio import REEL

build(REEL, __file__)
