"""Shared bits of the interview series (episodes 01–04)."""

import sys
from pathlib import Path

VOICES_CREDIT = "Dialogue performed with ElevenLabs premade voices Eric and Will."
WIDE_ANGLES = {"wide", "manager-reaction", "reaction"}


def project_root(file: str) -> Path:
    """The project folder: first argument, else the folder of the script."""
    return Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(file).resolve().parent


def office_shots(t):
    wide = t.shots(WIDE_ANGLES)
    close = t.shots(lambda a: a not in WIDE_ANGLES)
    return wide, close
