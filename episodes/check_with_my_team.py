#!/usr/bin/env python3
"""Check With My Team — the Stick style (traced stick figures on painted sets, outlined captions) in srstudio.

python3 check_with_my_team.py PROJECT --package DIR   # verify the unpacked .vpkg and copy its inputs in
python3 check_with_my_team.py PROJECT                 # the silent master, element for element the shipped scene
python3 check_with_my_team.py PROJECT --voice         # the voiced and scored master, with a card and a button

Every package file is checked against the SHA-256 in ``vpkg.json`` before anything is copied; the package's
scene and render are not copied, the scene is drawn here with :mod:`srstudio.stick` from the package's measured
data (poses, icons, lettering, foliage, script). ``--voice`` builds the same picture as ``scene.silent.xml`` and
adds what ``check_with_my_team_audio.py`` wrote with :func:`srstudio.dub.dub` into ``scene.xml``: the line of each
caption's phrase as dialogue (manifest verified by :func:`srstudio.narration.narration_cues`) and the song as a
bed, quiet under the desk scenes and up from the cut to the garden. The voiced picture differs from the
package's only in its words: from the loop point (``LOOP``, frame 230, where the recording starts over) the desk
does not say the line again; a card over the dance and the button at the desk replace the repeat
(:func:`check_with_my_team_audio.shown`), and the hook is shown on the opening only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path

from check_with_my_team_audio import END, shown
from instagram_posts import POSTS
from srstudio import STICK, Episode, EpisodeSpec, dub, stick, subtitles
from srstudio.narration import narration_cues

SILENT = "scene.silent.xml"
SKIP = {"Check_With_My_Team.mp4", "scene.xml"}  # the shipped master and scene; both are made here
CREDIT = "Voice-over by ElevenLabs premade voice Chris; music composed with ElevenLabs Music."
REVEAL, BACK = 29 / 12, 115 / 12  # the cut to the garden and the cut back to the desk
TRACED_POSE = 36  # the yard pose the badge drawings were traced from: they are turned back by its head angle
GEMINI = stick.Gradient(
    "gemini-gradient", ((0, "#9758c8"), (0.5, "#776bd1"), (1, "#3b93df")), 595, 780, 710, 890
)  # fmt: skip
FACES = (("chatgpt", "#70a599", 47, None), ("gemini", "#fffefd", None, GEMINI), ("claude", "#e67c4c", 42, None))
MUSIC_FIELDS = dict(
    audio=str,
    sha256=str,
    model=str,
    seed=int,
    bpm=(int, float),
    measured_bpm=(int, float),
    phase=(int, float),
    offset=(int, float),
    loud=list,
    quiet_gain=(int, float),
    loud_gain=(int, float),
    heard=str,
)


def unpack(package: Path, target: Path) -> None:
    """Copy ``package/project`` (but its scene and render) to ``target`` after every listed file matched its
    SHA-256; nothing on failure."""
    package, target = Path(package), Path(target)
    files = json.loads((package / "vpkg.json").read_text())["files"]
    project = package / "project"
    for f in files:
        path = project / f["path"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != f["sha256"]:
            raise dub.DubError(f"package file {f['path']} is missing or does not match vpkg.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(dir=target.parent, prefix=f".{target.name}-"))
    try:
        for f in files:
            if f["path"] in SKIP:
                continue
            dst = staging / f["path"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(project / f["path"], dst)
        staging.rename(target)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def music_tracks(root: Path, duration: float) -> list[dub.Track]:
    """The bed described by ``music.json``, every field checked and the song's SHA-256 matched."""
    doc = json.loads((root / "music.json").read_text())
    if not isinstance(doc, dict):
        raise dub.DubError("music.json: expected an object")
    missing = sorted(set(MUSIC_FIELDS) - set(doc))
    unknown = sorted(set(doc) - set(MUSIC_FIELDS))
    if missing or unknown:
        raise dub.DubError(f"music.json: missing {missing}, unknown {unknown}")
    for name, kind in MUSIC_FIELDS.items():
        value = doc[name]
        if (
            isinstance(value, bool)
            or not isinstance(value, kind)
            or (isinstance(value, float) and not math.isfinite(value))
        ):  # type: ignore[arg-type]
            raise dub.DubError(f"music.json: {name} has the wrong type ({value!r})")
    loud = doc["loud"]
    if not all(isinstance(s, list) and len(s) == 2 and all(isinstance(v, (int, float)) for v in s) for s in loud):
        raise dub.DubError(f"music.json: loud must be a list of [start, end] pairs, got {loud!r}")
    path = (root / doc["audio"]).resolve()
    if not path.is_relative_to(root.resolve()):
        raise dub.DubError(f"music.json: {doc['audio']} must be inside {root}")
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != doc["sha256"]:
        raise dub.DubError(f"music.json: {doc['audio']} is missing or its sha256 does not match")
    return dub.music_bed(
        "music",
        doc["audio"],
        doc["sha256"],
        offset=float(doc["offset"]),
        duration=duration,
        loud=[(float(a), float(b)) for a, b in loud],
        quiet_gain=float(doc["quiet_gain"]),
        loud_gain=float(doc["loud_gain"]),
        end_fade=0.5,  # the button is the end
    )


def badges(icons: Mapping[str, stick.Icon], traced: float) -> list[stick.Badge]:
    """The three badge heads, left to right, their drawings traced at head angle ``traced``."""
    missing = [name for name, *_ in FACES if name not in icons]
    if missing:
        raise stick.StickDataError(f"icons: missing {missing}")
    return [stick.Badge(icons[name], face, radius, traced, gradient) for name, face, radius, gradient in FACES]


def build(root: Path, out: Path, *, voiced: bool = False) -> Path:
    """The silent picture in the Stick style, written to ``out``: the package's, or with ``voiced`` the words of
    the voiced cut."""
    ep = Episode(
        EpisodeSpec(
            slug="scene",
            title="Check With My Team — Recreation",
            description="Silent native-vector recreation of the user-supplied two-scene cartoon. "
            "The AI team dances in a garden.",
            signature=False,  # shipped before ADR 0001; the package must reproduce element for element
            root=root,
            seed=1336,
            style=STICK,
            language="en-US",
            output="Check_With_My_Team.mp4",
            output_options=dict(
                codec="h264",
                container="mp4",
                fps="24",
                crf="17",
                preset="medium",
                pixelFormat="yuv420p",
                faststart=True,
                report="qa/render-report.json",
            ),
            accessibility=dict(
                description="A seated stick figure checks with a team represented by a person and ChatGPT, Gemini "
                "and Claude icons. The team dances. On-screen captions carry the dialogue."
            ),
        )
    )
    cv, comp, duration = ep.cv, ep.comp, ep.t.duration
    assets = root / "assets"
    poses = stick.load_poses(assets / "poses.json")
    traced = poses[TRACED_POSE]
    if not isinstance(traced, stick.YardPose):
        raise stick.StickDataError(f"pose {TRACED_POSE} must be a yard pose: the badges were traced from it")
    letters = stick.load_lettering(assets / "lettering.json", ("hook", "team_outline", "team_fill"))
    desk = [(0.0, REVEAL), (BACK, duration)]
    for start, end in desk:
        stick.room(cv, cv.group(comp, cv.uid("group"), start=start, end=end))
    stick.yard(cv, cv.group(comp, cv.uid("group"), start=REVEAL, end=BACK), stick.load_plates(assets / "foliage.json"),
               ep.spec.seed)  # fmt: skip
    stick.figures(cv, comp, poses, badges(stick.load_icons(assets / "icons.json"), traced.angle), duration)
    lettered = [stick.hook(cv, comp, letters["hook"], start, end) for start, end in (desk[:1] if voiced else desk)]
    lettered.append(stick.headline(cv, comp, letters["team_outline"], letters["team_fill"], REVEAL, BACK))
    lines = stick.load_script(root / "script.json")
    if voiced:
        if duration < END:
            raise stick.StickDataError(f"the picture lasts {duration:.3f} s; the button needs {END:.3f} s")
        size = lines[0].size
        lines = [
            stick.Line(c.start, c.end, c.text, size) for c in shown(json.loads((root / "script.json").read_text()))
        ]
        # The published cut's cover is drawn from this scene without its burned-in text; the package's silent
        # scene stays element for element the shipped one.
        spoken = cv.group(comp, "spoken-words")
        stick.captions(cv, spoken, lines)
        ep.hide_on_cover(*lettered, spoken)
    else:
        stick.captions(cv, comp, lines)
    subtitles.write_srt(root / "Check_With_My_Team.srt", [(q.start, q.end, q.text) for q in lines])
    ep.instagram(POSTS["check-with-my-team"])
    return ep.finish(out, root / "qa" / "sdk-validation.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("project", type=Path)
    parser.add_argument("--package", type=Path, help="the unpacked check-with-my-team .vpkg folder")
    parser.add_argument("--voice", action="store_true", help="dub narration.json and music.json, end at the loop")
    args = parser.parse_args(argv)
    os.umask(0o077)  # generated outputs are private: folders 700, files 600
    root = args.project.resolve()
    if args.package is not None:
        unpack(args.package, root)
        print(f"{root}: package verified and copied")
        return 0
    if not args.voice:
        build(root, root / "scene.xml")
        return 0
    build(root, root / SILENT, voiced=True)
    duration = END
    voice = [
        dub.Track(f"vo-{c.id}", c.audio, c.sha256, start=c.start, role="dialogue", language="en-US")
        for c in narration_cues(root / "narration.json", root)
    ]
    try:
        tracks = voice + music_tracks(root, duration)
        dub.dub(root / SILENT, root / "scene.xml", tracks, credit=CREDIT, duration=duration)
    except dub.DubError as exc:
        raise SystemExit(f"dub: {exc}") from None
    words = shown(json.loads((root / "script.json").read_text()))
    subtitles.write_srt(root / "Check_With_My_Team.srt", [(c.start, c.end, c.text) for c in words])
    print(f"{root / 'scene.xml'}: {len(voice)} lines and the music bed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
