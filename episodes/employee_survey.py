#!/usr/bin/env python3
"""Anonymous Employee Survey — the portrait Toon style (a flat cartoon cat at a laptop, pill captions) in srstudio.

python3 employee_survey.py PROJECT --init     # script.json, assets/poses.json and the pinned Comic Neue
python3 employee_survey.py PROJECT            # the silent master on the reference timing
python3 employee_survey.py PROJECT --voice    # the narrated master: narration.json (employee_survey_audio.py),
                                              # captions and expressions moved to the narrator's words, the
                                              # keyboard heard between the lines, the typing frames swapping on it
"""

import sys
from functools import partial

from _common import project_root
from employee_survey_data import FLASH, SEGMENTS, flashes, write_project
from instagram_posts import POSTS
from srstudio import TOON, Episode, EpisodeSpec, fonts, subtitles, toon
from srstudio.narration import effect_cues, manifest_duration

ROOT = project_root(__file__)
FLAGS = set(sys.argv[2:])
if "--init" in FLAGS:
    write_project(ROOT, TOON.font.google)
    sys.exit(0)
VOICED = "--voice" in FLAGS
NARRATION = "Narrated with ElevenLabs premade voice Brian; synthesised keyboard and camera foley."
ep = Episode(
    EpisodeSpec(
        slug="employee-survey",
        title="Anonymous Employee Survey — Reference Match (Toon)",
        description=(
            "Vector recreation of the.nope.cat's survey reel in the Toon style: a flat cartoon cat whose expression "
            "swaps per cue, with each phrase in a white pill. " + (NARRATION if VOICED else "Silent master.")
        ),
        root=ROOT,
        seed=1028,
        style=TOON,
        dialogue="voiced/script.json" if VOICED else "script.json",
        language="en-US",
        output_options=dict(
            codec="h264",
            container="mp4",
            fps="24",
            crf="17",
            preset="medium",
            pixelFormat="yuv420p",
            faststart=True,
            report="qa/render-report.json",
            **(dict(audioCodec="aac", audioBitrate="192000") if VOICED else {}),
        ),
        accessibility=dict(
            description="A blue cartoon cat at a laptop answers an anonymous employee survey; its answers appear "
            "as captions. "
            + (f"{NARRATION} Text transcript bundled." if VOICED else "Silent master; transcript bundled.")
        ),
    )
)
cv, t = ep.cv, ep.t
poses = toon.load_poses(ROOT / ("voiced/poses.json" if VOICED else "assets/poses.json"))
lines = toon.load_script(ROOT / ep.spec.dialogue)
duration = t.duration
taps: tuple[float, ...] = ()
flash_times = flashes(SEGMENTS)
if VOICED:
    duration = max(duration, manifest_duration(ROOT / "narration.json"))
    effects = effect_cues(ROOT / "narration.json", ROOT)
    taps = tuple(t for fx in effects if fx.id == "typing" for t in fx.taps)
    flash_times = [fx.start for fx in effects if fx.id == "click"]
    ep.scene.find("project").duration = duration
toon.room(cv, ep.comp)
toon.cat(cv, ep.comp, poses, duration, taps)
toon.desk(cv, ep.comp)
for at in flash_times:  # the laptop's camera fires: one white frame-full for three frames
    cv.rect(cv.group(ep.comp, cv.uid("g"), start=at, end=at + FLASH), 0, 0, cv.width, cv.height, cv.white)
font_bytes = (ROOT / TOON.font.src).read_bytes()
toon.captions(cv, ep.comp, lines, partial(fonts.text_width, font_bytes, size=toon.CAPTION_SIZE))
if VOICED:
    ep.audio(narration=ROOT / "narration.json")
    for fx in effects:
        cv.assets.add_audio(id=f"fx-{fx.id}", src=fx.audio, sha256=fx.sha256)
        ep.add_track(f"fx-track-{fx.id}", f"fx-{fx.id}", start=fx.start, role="effects", gain=fx.gain_db)

subtitles.write_srt(ROOT / "employee-survey.srt", [(p.start, p.end, p.caption) for p in t.phrases])
ep.instagram(POSTS["employee-survey"])
ep.finish()
