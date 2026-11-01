#!/usr/bin/env python3
"""Saga 20 — Store Credit: builds the scene from the recording (:mod:`store_credit_audio`).

python3 store_credit.py PROJECT
"""

from __future__ import annotations

from _saga import build
from store_credit_audio import REEL

if __name__ == "__main__":
    build(REEL, __file__)
