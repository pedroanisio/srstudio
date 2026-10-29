#!/usr/bin/env python3
"""Work Training Be Like — the portrait Cel style (traced drawings, measured camera, lettering) in srstudio.

python3 mushroom_training.py PROJECT            # the silent master, element for element the shipped scene
python3 mushroom_training.py PROJECT --voice    # the narrated master: narration.json (mushroom_training_audio.py),
                                                # the keyboard sinking and heard on every keystroke, the project
                                                # held past the last caption so the last line is heard whole
"""

import sys
from dataclasses import replace

from _common import project_root
from instagram_posts import POSTS
from srstudio import CEL, Episode, EpisodeSpec, cel, errors, subtitles
from srstudio.narration import effect_cues, manifest_duration

ROOT = project_root(__file__)
ASSETS = ROOT / "assets"
VOICED = "--voice" in errors.flags(sys.argv[2:], ("--voice",))
NARRATION = "Narrated with ElevenLabs premade voice Alice; synthesised keyboard foley."
# the laptop keyboard in drawing pixels: the ink is one compound path, so the keyboard face (and the key rows it
# carries) is what sinks on each keystroke, inside the ink frame that stays (srstudio.cel.Pressed)
KEYBOARD = (505.0, 988.0, 648.0, 1056.0)
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
captions = cel.load_captions(ROOT / "script.json")
duration = t.duration
pressed = None
if VOICED:
    # the narration at its own pace outlasts the last caption: hold the last drawing and caption until it ends
    duration = max(duration, manifest_duration(ROOT / "narration.json"))
    runs[-1] = replace(runs[-1], end=duration)
    captions[-1] = replace(captions[-1], end=duration)
    effects = effect_cues(ROOT / "narration.json", ROOT)
    taps = tuple(t for fx in effects if fx.id == "typing" for t in fx.taps)  # the keyboard sinks on the keystrokes
    pressed = cel.Pressed(KEYBOARD, taps)
    ep.scene.find("project").duration = duration
world = cel.world(cv, ep.comp, camera, duration)
cel.room(cv, world, camera, cel.load_camera(ASSETS / "room-camera.json"), duration)
cel.traced(cv, world, runs, cel.load_drawings(ASSETS, runs), pressed=pressed)
for caption in captions:
    cel.lettering(cv, ep.comp, caption)
if VOICED:
    ep.audio(narration=ROOT / "narration.json")
    for fx in effects:
        cv.assets.add_audio(id=f"fx-{fx.id}", src=fx.audio, sha256=fx.sha256)
        ep.add_track(f"fx-track-{fx.id}", f"fx-{fx.id}", start=fx.start, role="effects", gain=fx.gain_db)

subtitles.write_srt(ROOT / "Mushroom_Training_Captions.srt", [(p.start, p.end, p.caption) for p in t.phrases])
ep.instagram(POSTS["mushroom-training"])
ep.finish(ROOT / "scene.xml", ROOT / "qa" / "sdk-validation.json")
