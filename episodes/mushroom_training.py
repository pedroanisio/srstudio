#!/usr/bin/env python3
"""Work Training Be Like — the portrait Cel style (traced drawings, measured camera, lettering) in srstudio.

python3 mushroom_training.py PROJECT            # the silent master, element for element the shipped scene
python3 mushroom_training.py PROJECT --voice    # plus the narration of narration.json (mushroom_training_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import POSTS
from mushroom_training_audio import narration_cues
from srstudio import CEL, Episode, EpisodeSpec, cel, subtitles

ROOT = project_root(__file__)
ASSETS = ROOT / "assets"
VOICED = "--voice" in sys.argv[2:]
NARRATION = "Narrated with ElevenLabs premade voice Alice."
ep = Episode(
    EpisodeSpec(
        slug="scene",
        title="Work Training Be Like — Reference Match v2",
        description=(
            "Silent vector reconstruction of the user-supplied Under Studio cartoon. "
            "Caption lettering is editable vector outlines." + (f" {NARRATION}" if VOICED else "")
        ),
        signature=False,  # shipped before ADR 0001; the package must reproduce element for element
        root=ROOT,
        seed=1332,
        style=CEL,
        language="en-US",
        font_policy="pinned",  # the shipped project declares it although no font is used
        output="Mushroom_Training_Visual_Match.mp4",
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
            description="Mushroom at a desk with the supplied training dialogue on screen. "
            + (f"{NARRATION} Text transcript bundled." if VOICED else "Silent master; text transcript bundled.")
        ),
    )
)
cv, t = ep.cv, ep.t

camera = cel.load_camera(ASSETS / "camera.json")
runs = cel.load_runs(ASSETS / "poses.json")
world = cel.world(cv, ep.comp, camera, t.duration)
cel.room(cv, world, camera, cel.load_camera(ASSETS / "room-camera.json"), t.duration)
cel.traced(cv, world, runs, cel.load_drawings(ASSETS, runs))
for caption in cel.load_captions(ROOT / "script.json"):
    cel.lettering(cv, ep.comp, caption)

if VOICED:
    ep.mix(loudness="-16", true_peak="-1.5")
    for cue in narration_cues(ROOT / "narration.json", ROOT):
        cv.assets.add_audio(id=f"vo-{cue.id}", src=cue.audio, sha256=cue.sha256, language="en-US")
        ep.add_track(f"vo-track-{cue.id}", f"vo-{cue.id}", start=cue.start, role="dialogue", language="en-US")

subtitles.write_srt(ROOT / "Mushroom_Training_Captions.srt", [(p.start, p.end, p.caption) for p in t.phrases])
ep.instagram(POSTS["mushroom-training"])
ep.finish(ROOT / "scene.xml", ROOT / "qa" / "sdk-validation.json")
