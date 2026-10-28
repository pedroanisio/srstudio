#!/usr/bin/env python3
"""The Printer — the square Ink style (shot sequence, pen stroke), rebuilt with srstudio."""

from _common import project_root
from instagram_posts import POSTS
from srstudio import INK, Episode, EpisodeSpec, ink, subtitles

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="scene",
        title="The Printer — scene-render recreation",
        description=(
            "Procedural recreation of the user-supplied Mark Kacy printer cartoon, with new synthesized performances."
        ),
        signature=False,  # shipped before ADR 0001; the package must reproduce element for element
        root=ROOT,
        seed=1330,
        style=INK,
        language="en-US",
        output="Printer_Recreation.mp4",
        output_options=dict(
            codec="h264",
            container="mp4",
            fps="24",
            crf="18",
            preset="medium",
            pixelFormat="yuv420p",
            audioBitrate="192000",
            faststart=True,
            report="qa/render-report.json",
        ),
        poster=dict(time=36, path="Printer_Cover.jpg", format="jpeg", quality=".95"),
        accessibility=dict(description="Black and white cartoon with on-screen dialogue and external SRT captions."),
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
ep.mix(loudness="-14", true_peak="-1.5", bit_depth=None)

srt = []
for take in t.takes:
    g = ep.shot(shots, take)
    if take.shot == "desk":
        ink.desk_shot(cv, g, take)
    elif take.shot == "human":
        ink.closeup(cv, g, take, zoom=1.46 if take.mood not in ("angry", "scream") else 1.53, gesture=take.id == "18")
    elif take.shot in ("printer", "printer-close"):
        pg = ink.printer_shot(cv, g, take, close=take.shot == "printer-close")
        sc = 1.42 if take.shot == "printer-close" else 1.19
        if take.id == "15":  # the slow creep of "you're playing by my rules now"
            for prop in ("scaleX", "scaleY"):
                cv.keys(pg, prop, [(0, sc), (take.duration, sc * 1.07)], kind="sine-in-out")
        if take.id == "19":  # MAGENTA!
            for prop in ("scaleX", "scaleY"):
                cv.keys(pg, prop, [(0, 1.19), (0.12, 1.30), (0.24, 1.24)], kind="cubic-out")
    elif take.shot == "wide":
        ink.wide_shot(cv, g, take)
    cues = [(0, take.duration, take.text)] if take.is_effect else subtitles.chunk_words(take.words, take.duration)
    for start, end, text in cues:
        ink.caption(
            cv, g, text, start=start, end=end, y=84, size=70 if take.id == "19" else 40 if take.is_effect else 48
        )
        srt.append((take.start + start, take.start + end, text))
    ep.take_audio(take, pan=-0.08 if take.actor == "human" else 0.08, fadeIn=".003", fadeOut=".008")

cv.assets.add_audio(id="beep", src="audio/error-beep.wav")
ep.add_track("error-tone", "beep", start=t.take("19").start + 0.12, role="effects", gain=-8)
subtitles.write_srt(ROOT / "Printer_Captions.srt", srt)
ep.instagram(POSTS["scene"])
ep.finish(ROOT / "scene.xml", ROOT / "qa" / "sdk-validation.json")
