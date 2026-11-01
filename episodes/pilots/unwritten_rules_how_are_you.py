#!/usr/bin/env python3
"""The Unwritten Rules, how are you: Rafa's pilot of the talking-head show (see unwritten_rules_how_are_you_data.py).

python3 unwritten_rules_how_are_you.py PROJECT --init     # script.json and the pinned Fraunces
python3 unwritten_rules_how_are_you.py PROJECT            # the silent master on the scripted timing
python3 unwritten_rules_how_are_you.py PROJECT --voice    # the voiced master from the recording

A pilot, not an Okayville reel: it has no release and no post, and it renders outside the Instagram folder. His plates
render into SRSTUDIO_PLATES, by default ``plates`` beside SRSTUDIO_RENDERS.
"""

import os
import sys
from functools import lru_cache, partial
from pathlib import Path

from unwritten_rules_how_are_you_data import (
    ACCESSIBILITY,
    ACTS,
    DESCRIPTION,
    NARRATION,
    OUTPUT,
    SEED,
    SIGN_OFF,
    SKETCH,
    TINTS,
    VERSIONS,
    overlay,
    validate_sketch,
)

from srstudio import host_kit, rafa_host, rafa_reel, toon
from srstudio.fonts import text_width
from srstudio.layout import VERTICAL
from srstudio.toon_sketch import Staging, build

validate_sketch()
ROOT = Path(sys.argv[1]).resolve()
VOICED = "--voice" in sys.argv
RENDERS = rafa_reel.Renders(
    Path(os.environ["SRSTUDIO_ENGINE"]),
    Path(os.environ.get("SRSTUDIO_PLATES", Path(os.environ["SRSTUDIO_RENDERS"]).parent / "plates")),
    Path(os.environ["SRSTUDIO_FONTS"]),
)


@lru_cache(maxsize=1)
def plan_of(end: float):
    return host_kit.head_plan(ROOT, end, VOICED, cast=rafa_host.CAST, style=rafa_host.MOTION)


def words():
    return host_kit.spoken(ROOT, rafa_host.CAST) if VOICED else ()


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    dress=rafa_reel.stage(ACTS, plan_of, RENDERS, ROOT),
    versions=VERSIONS,
    desk=lambda cv, parent: None,  # the worktop is on his plates
    style=host_kit.HOST,
    bare=rafa_host.CAST.characters,
    captions=lambda *_: None,  # the engine's track, added to the built episode below
    camera=rafa_reel.framing(ACTS),
    finish=host_kit.finish,
    overlay=partial(overlay, root=ROOT, renders=RENDERS),
    safe_area=VERTICAL,
    output=OUTPUT,
    crf="25",
)
ep = build(ROOT, STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    font = (ROOT / ep.spec.font).read_bytes()
    ep.hide_on_cover(
        *host_kit.captions(
            ep, toon.load_script(ROOT / ep.spec.dialogue), partial(text_width, font), words(), (SIGN_OFF,)
        )
    )
    ep.finish()
