"""Social captions for a finished episode: a typed Instagram post, the ``ig.txt`` it is written to, and its cover.

The post is data first (title, description, credit, hashtags, thumbnail) and text second, so a caption can be
checked against Instagram's limits before anyone pastes it. ``ig.txt`` is the plain-text rendering:
title, blank line, description, blank line, credit, blank line, hashtags on one line.

A delivery (:meth:`InstagramPost.deliver`) writes ``ig.txt`` and ``cover.jpg`` side by side. The cover is the post's
designed :class:`~srstudio.thumbnail.Thumbnail`: its backdrop is the frame of the rendered video on screen at the
thumbnail's time (:func:`take_frame`, which refuses a time past the last frame and a blank frame), and the engine
draws the headline over it at the video's own size. An episode that hides its burned-in text (hook cards, captions)
in a ``cover`` variant of its scene (:meth:`srstudio.episode.Episode.hide_on_cover`) names that scene, and the
backdrop is drawn from it instead (:func:`take_still`): the same frame, without the text the headline would fight.

A caption carries at most :data:`HASHTAG_LIMIT` hashtags. Instagram cut its cap from 30 to 5 on 18 December 2025, after
most of the published reels were written, and a published post stays as it went out, so a post can still be written
with more (:data:`PUBLISHED_HASHTAG_LIMIT`) and the first delivery is what holds the limit: :func:`hashtag_excess` says
why a caption is over it, and :func:`refuse_hashtags` refuses, in ``deliver`` and ``publish_pilots.py`` (ADR 0065).

The publish gate (:func:`publish`, :func:`check_delivery`) records what each delivery was made from in
``delivery.json``. A post's :func:`fingerprint` holds the cover's drawing (the composed document at the video's own
size and the fixed render steps), not the source of the code that drew it (ADR 0037).
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import re
import struct
import subprocess
import tempfile
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, NamedTuple

from . import checks, digest, gpu
from . import thumbnail as drawing
from .errors import SrstudioError
from .thumbnail import Thumbnail, ThumbnailError, covered, render

__all__ = [
    "InstagramPost",
    "InstagramPostError",
    "CoverError",
    "VideoInfo",
    "probe",
    "video_size",
    "take_frame",
    "take_still",
    "COVER_VARIANT",
    "Item",
    "Drift",
    "DeliveryError",
    "ManifestVersionError",
    "Migration",
    "fingerprint",
    "render_steps",
    "read_manifest",
    "check_delivery",
    "publish",
    "migrate_manifest",
    "MANIFEST",
    "MANIFEST_VERSION",
    "LEGACY_VERSION",
    "LEGACY_LAYOUTS",
    "LEGACY_LAYOUT_7CDAFF4",
    "LEGACY_LAYOUT_F7C86D3",
    "BACKDROP_ARGS",
    "FRAME_SLACK",
    "CAPTION_LIMIT",
    "HASHTAG_LIMIT",
    "PUBLISHED_HASHTAG_LIMIT",
    "HashtagError",
    "hashtag_excess",
    "refuse_hashtags",
    "TITLE_LIMIT",
    "FILE_NAME",
    "COVER_NAME",
]

CAPTION_LIMIT = 2200  # characters Instagram accepts in one caption
HASHTAG_LIMIT = 5  # hashtags Instagram accepts in one caption, since 18 December 2025
PUBLISHED_HASHTAG_LIMIT = 30  # its cap before that: a published post stays valid under it, so a rebuild still writes
TITLE_LIMIT = 125  # characters shown in the feed before "… more"
FILE_NAME = "ig.txt"
COVER_NAME = "cover.jpg"
BLANK = 3.0  # a frame whose luma varies less than this (standard deviation, 0-255) is blank: a fade, a black cut
FRAME_SLACK = 1e-6  # the frame on screen at t is floor(t × fps + FRAME_SLACK), so t = n / fps is frame n
BACKDROP_ARGS = ("-fps_mode", "passthrough", "-frames:v", "1", "-q:v", "2")  # how take_frame writes its frame
_HASHTAG = re.compile(r"#[^\W\d_]\w*", re.UNICODE)  # whole tag: fullmatch, so no trailing newline
_TAG_IN_TEXT = re.compile(r"(?<![\w#])#\w*[^\W\d]\w*", re.UNICODE)  # a tag anywhere in a caption; "#1" is no tag


class InstagramPostError(SrstudioError, ValueError):
    """The post breaks one of Instagram's limits or the house rules; ``problems`` lists every reason."""

    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


class CoverError(SrstudioError, ValueError):
    """The backdrop cannot be taken: the video cannot be read, the time is outside it, or the frame is blank."""


@dataclass(frozen=True)
class VideoInfo:
    """What :func:`probe` reads from a video's first video stream."""

    width: int
    height: int
    fps: float
    duration: float
    frames: int


def _run(cmd: list[str], what: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError) as e:
        detail = getattr(e, "stderr", b"") or b""
        raise CoverError(f"{what}: {detail.decode(errors='replace').strip() or e}") from e


def probe(video: Path, *, ffprobe: str = "ffprobe") -> VideoInfo:
    """The size, frame rate, duration and frame count of ``video``'s first video stream."""
    out = _run(
        [ffprobe, "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
         "stream=width,height,avg_frame_rate,nb_read_frames:format=duration", "-of", "json", str(video)],
        f"cannot read {video}",
    ).stdout  # fmt: skip
    try:
        data = json.loads(out)
        stream = data["streams"][0]
        num, den = (int(x) for x in stream["avg_frame_rate"].split("/"))
        fps = num / den if den else 0.0
        frames = int(stream.get("nb_read_frames") or 1)
        duration = float(data.get("format", {}).get("duration") or frames / fps)
        info = VideoInfo(int(stream["width"]), int(stream["height"]), fps, duration, frames)
    except (KeyError, IndexError, ValueError, ZeroDivisionError) as e:
        raise CoverError(f"cannot read {video}: unexpected ffprobe output ({e})") from e
    if info.width <= 0 or info.height <= 0 or info.fps <= 0:
        raise CoverError(f"cannot read {video}: {info}")
    return info


def _boxes(read: Callable[[int, int], bytes], start: int, end: int) -> Iterator[tuple[bytes, int, int]]:
    """Each ISO media box from ``start`` to ``end``: its type and the bounds of its payload. Raises ValueError for a
    box that is cut short or runs past ``end``."""
    pos = start
    while pos < end:
        head = read(pos, 16)
        if len(head) < 8:
            raise ValueError(f"the box at byte {pos} is cut short")
        size, kind = struct.unpack(">I4s", head[:8])
        body = pos + 8
        if size == 1:  # a 64-bit size follows the type
            if len(head) < 16:
                raise ValueError(f"the box at byte {pos} is cut short")
            size, body = struct.unpack(">Q", head[8:])[0], pos + 16
        elif size == 0:  # the box runs to the end
            size = end - pos
        if size < body - pos or pos + size > end:
            raise ValueError(f"the {kind.decode(errors='replace')!r} box at byte {pos} does not fit")
        yield kind, body, pos + size
        pos += size


def _child(read: Callable[[int, int], bytes], start: int, end: int, kind: bytes) -> tuple[int, int]:
    """The payload bounds of the first ``kind`` box from ``start`` to ``end``."""
    for found, body, stop in _boxes(read, start, end):
        if found == kind:
            return body, stop
    raise ValueError(f"it has no {kind.decode()!r} box")


def video_size(video: Path) -> tuple[int, int]:
    """The width and height of ``video``'s first video track, read from its MP4 index without running ffprobe: the
    size in the track's sample entry, which is the size :func:`probe` reports for every video :meth:`deliver`
    accepts. Raises :class:`CoverError` for a file that is not an MP4 with a sized video track."""
    video = Path(video)
    try:
        with video.open("rb") as f:

            def from_file(offset: int, n: int) -> bytes:
                f.seek(offset)
                return f.read(n)

            start, stop = _child(from_file, 0, video.stat().st_size, b"moov")
            index = from_file(start, stop - start)

        def read(offset: int, n: int) -> bytes:
            return index[offset : offset + n]

        for kind, body, end in _boxes(read, 0, len(index)):
            if kind != b"trak":
                continue
            mdia = _child(read, body, end, b"mdia")
            hdlr, _ = _child(read, *mdia, b"hdlr")
            if read(hdlr + 8, 4) != b"vide":  # after version, flags and pre_defined: the handler type
                continue
            stsd, stsd_end = _child(read, *_child(read, *_child(read, *mdia, b"minf"), b"stbl"), b"stsd")
            entry = stsd + 8  # after version, flags and the entry count
            if entry + 36 > stsd_end:
                raise ValueError("its video sample entry is cut short")
            # a visual sample entry: size, type, 6 reserved, data reference, 16 pre-defined, then width and height
            width, height = struct.unpack(">HH", read(entry + 32, 4))
            if not (width and height):
                raise ValueError("its video sample entry has no size")
            return width, height
        raise ValueError("it has no video track")
    except (OSError, ValueError, struct.error) as e:
        raise CoverError(f"cannot read the size of {video.name}: {e}") from e


def _spread(image: Path, ffmpeg: str) -> float:
    """The standard deviation of the luma of ``image`` shrunk to 64 px wide."""
    raw = _run([ffmpeg, "-v", "error", "-i", str(image), "-vf", "scale=64:-2,format=gray", "-f", "rawvideo", "-"],
               f"cannot read the cover {image}").stdout  # fmt: skip
    if not raw:
        raise CoverError(f"the cover {image} has no pixels")
    mean = sum(raw) / len(raw)
    return math.sqrt(sum((v - mean) ** 2 for v in raw) / len(raw))


def _frame(video: Path, at: float, ffprobe: str) -> tuple[VideoInfo, int]:
    """``video``'s facts and the index of its frame on screen at ``at`` seconds, floor(at × fps)."""
    if not checks.number(at) or at < 0:
        raise CoverError(f"frame time must be a number of seconds >= 0, got {at!r}")
    info = probe(video, ffprobe=ffprobe)
    index = math.floor(at * info.fps + FRAME_SLACK)
    if index >= info.frames:
        raise CoverError(
            f"frame time {at} s is after the last frame of {video.name} ({info.frames} frames at {info.fps:g} fps)"
        )
    return info, index


def take_frame(video: Path, at: float, out: Path, *, ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe") -> VideoInfo:
    """Write the frame of ``video`` on screen at ``at`` seconds to the image ``out`` and return the video's facts.

    The frame is selected by its index, floor(at × fps), not by seeking, so it is exactly that frame, at the video's
    size. Raises :class:`CoverError` for a time outside the video or a blank frame, and then leaves no ``out``."""
    info, index = _frame(video, at, ffprobe)
    out = Path(out)
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        still = Path(tmp) / out.name
        select = [ffmpeg, "-v", "error", "-y", "-i", str(video), "-vf", f"select=eq(n\\,{index})", *BACKDROP_ARGS,
                  str(still)]  # fmt: skip
        _run(select, f"cannot take frame {index} of {video}")
        if not still.exists():
            raise CoverError(f"ffmpeg wrote no frame {index} of {video}")
        spread = _spread(still, ffmpeg)
        if spread < BLANK:
            raise CoverError(f"frame {index} of {video.name} at {at} s is blank (luma spread {spread:.1f})")
        still.replace(out)
    out.chmod(0o600)
    return info


COVER_VARIANT = "cover"  # the scene variant a cover's backdrop is drawn in


def take_still(
    scene: Path,
    video: Path,
    at: float,
    out: Path,
    *,
    engine: str | Path,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
) -> VideoInfo:
    """Draw the frame of ``video`` on screen at ``at`` seconds from its ``scene`` document, in the scene's
    :data:`COVER_VARIANT`, into the PNG ``out``, and return the video's facts.

    The frame is the one :func:`take_frame` would take (its index at the video's rate, drawn at that frame's time).
    Raises :class:`CoverError` for a missing scene, a time outside the video, a scene without the variant, a still of
    another size than the video, or a blank still, and then leaves no ``out``."""
    scene, out = Path(scene), Path(out)
    if not scene.is_file():
        raise CoverError(f"no scene {scene} to draw the cover from: build the project first")
    info, index = _frame(video, at, ffprobe)
    if f'<variant id="{COVER_VARIANT}"'.encode() not in scene.read_bytes():
        raise CoverError(f"{scene.name} has no {COVER_VARIANT} variant to draw the cover's backdrop in")
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        still = Path(tmp) / "still.png"
        with gpu.held():
            _run([str(engine), "render", str(scene.resolve()), "--variant", COVER_VARIANT, "-t",
                  f"{index / info.fps:.6f}", "-o", str(still.resolve())],
                 f"the engine cannot draw frame {index} of {scene.name}")  # fmt: skip
        if not still.exists():
            raise CoverError(f"the engine wrote no frame {index} of {scene.name}")
        size = _run([ffprobe, "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x",
                     str(still)], f"cannot read the still of {scene.name}").stdout.decode().strip()  # fmt: skip
        if size != f"{info.width}x{info.height}":
            raise CoverError(f"{scene.name} draws {size}, but {video.name} is {info.width}x{info.height}")
        spread = _spread(still, ffmpeg)
        if spread < BLANK:
            raise CoverError(f"frame {index} of {scene.name} at {at} s is blank (luma spread {spread:.1f})")
        still.replace(out)
    out.chmod(0o600)
    return info


def hashtag_excess(caption: str) -> str:
    """Why the caption text ``caption`` is over :data:`HASHTAG_LIMIT`, or an empty string when it is not. The whole
    text counts, as it does for Instagram: a tag in the description is a tag."""
    count = len(_TAG_IN_TEXT.findall(caption))
    return f"{count} hashtags; Instagram accepts {HASHTAG_LIMIT}" if count > HASHTAG_LIMIT else ""


@dataclass(frozen=True)
class InstagramPost:
    title: str
    description: str
    hashtags: tuple[str, ...] = ()
    credit: str = ""
    language: str = "en-US"
    extra: dict = field(default_factory=dict)  # anything a publisher wants to carry along (alt text...)
    thumbnail: Thumbnail | None = None  # the designed cover; needed to deliver
    credit_last: bool = False  # new deliveries may put credit after hashtags (ADR 0250)

    def problems(self) -> list[str]:
        out = []
        title, description = self.title.strip(), self.description.strip()
        if not title:
            out.append("title is empty")
        if "\n" in title:
            out.append("title spans more than one line")
        if len(title) > TITLE_LIMIT:
            out.append(f"title has {len(title)} characters; the feed shows {TITLE_LIMIT} before folding")
        if not description:
            out.append("description is empty")
        if len(self.hashtags) > PUBLISHED_HASHTAG_LIMIT:
            out.append(f"{len(self.hashtags)} hashtags; no caption ever went out with over {PUBLISHED_HASHTAG_LIMIT}")
        bad = [h for h in self.hashtags if not _HASHTAG.fullmatch(h)]
        if bad:
            out.append(f"hashtags must be '#' plus letters, digits or '_' and start with a letter: {bad}")
        lowered = [h.lower() for h in self.hashtags]
        if len(set(lowered)) != len(lowered):
            out.append("duplicate hashtags")
        if self.thumbnail is not None:
            out += [f"thumbnail: {p}" for p in self.thumbnail.problems()]
        n = len(self.text())
        if n > CAPTION_LIMIT:
            out.append(f"caption has {n} characters; Instagram accepts {CAPTION_LIMIT}")
        return out

    def validate(self) -> InstagramPost:
        problems = self.problems()
        if problems:
            raise InstagramPostError(problems)
        return self

    def text(self) -> str:
        blocks = [self.title.strip(), self.description.strip()]
        if self.credit.strip() and not self.credit_last:
            blocks.append(self.credit.strip())
        if self.hashtags:
            blocks.append(" ".join(self.hashtags))
        if self.credit.strip() and self.credit_last:
            blocks.append(self.credit.strip())
        return "\n\n".join(blocks) + "\n"

    def write(self, folder: Path, name: str = FILE_NAME) -> Path:
        """Validate, then write the caption as ``<folder>/ig.txt`` (mode 600) and return its path."""
        self.validate()
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / name
        path.write_text(self.text(), encoding="utf-8")
        path.chmod(0o600)
        return path

    def deliver(
        self,
        folder: Path,
        video: Path,
        *,
        font: Path,
        engine: str | Path,
        ffmpeg: str = "ffmpeg",
        ffprobe: str = "ffprobe",
        scene: Path | None = None,
        keep_clear: Iterable[tuple[float, float, float, float]] = (),
    ) -> tuple[Path, Path]:
        """Write ``ig.txt`` and ``cover.jpg`` (the :attr:`thumbnail` over its frame of ``video``, drawn from the
        ``cover`` variant of ``scene`` when one is given) into ``folder``.

        The cover is drawn before the caption is written: a post without a thumbnail, an invalid post, a time outside
        the video, a blank frame, a headline that does not fit or a failed render raise, and leave no file. ``font``
        is the headline's TrueType file and ``engine`` the scene-render binary. ``keep_clear`` names boxes of the
        frame, in px, that must stay visible (the faces): a headline or kicker landing on one raises in the same way,
        and it reads no part of the post's fingerprint."""
        problems = self.problems() + (
            ["thumbnail is missing; a delivery needs a cover"] if self.thumbnail is None else []
        )
        if problems:
            raise InstagramPostError(problems)
        assert self.thumbnail is not None
        folder = Path(folder)
        created = not folder.exists()
        folder.mkdir(parents=True, exist_ok=True)
        try:
            with tempfile.TemporaryDirectory(dir=folder) as tmp:
                backdrop = Path(tmp) / "backdrop.png"
                at = self.thumbnail.at
                info = (
                    take_frame(video, at, backdrop, ffmpeg=ffmpeg, ffprobe=ffprobe)
                    if scene is None
                    else take_still(scene, video, at, backdrop, engine=engine, ffmpeg=ffmpeg, ffprobe=ffprobe)
                )
                width, height = video_size(video)  # the size the gate fingerprints the cover at
                if (width, height) != (info.width, info.height):
                    raise CoverError(f"{Path(video).name} decodes at {info.width}x{info.height}, but its index says "
                                     f"{width}x{height}")  # fmt: skip
                hidden = covered(self.thumbnail, Path(font).read_bytes(), width, height, keep_clear)
                if hidden:
                    raise ThumbnailError(f"the headline or kicker covers {hidden}; move the focus or the place")
                cover = render(self.thumbnail, backdrop, folder / COVER_NAME, font=font, engine=engine,
                               width=info.width, height=info.height, ffmpeg=ffmpeg)  # fmt: skip
        except BaseException:  # whatever fails, a folder made for this delivery is not left behind
            if created and not any(folder.iterdir()):
                folder.rmdir()
            raise
        return self.write(folder), cover


# -- the publish gate: what was delivered, and whether it still matches -----------------------------------------
MANIFEST = "delivery.json"
MANIFEST_VERSION = "1.1.0"  # 1.1.0: the post fingerprint holds the cover's drawing, not the layout source
LEGACY_VERSION = "1.0.0"
# The SHA-256 of each thumbnail.py source a 1.0.0 entry hashed as its "layout". The two draw the same covers: f7c86d3
# only imported SrstudioError and made it a base of ThumbnailError. The set is closed (ADR 0037): the drawing
# fingerprint is the only scheme after the migration, and no later source is ever added.
# thumbnail.py as 7cdaff4 wrote it: `git show f7c86d3^:src/srstudio/thumbnail.py | sha256sum`
LEGACY_LAYOUT_7CDAFF4 = "cee600d0102510c78586d39ac0c449c6a0a5959af04c6f97bfcd509971b86c09"
# thumbnail.py as f7c86d3 left it: `git show f7c86d3:src/srstudio/thumbnail.py | sha256sum`
LEGACY_LAYOUT_F7C86D3 = "96dfe994aa02fb4eb4028ffd5030aa7721463a810e7624de25d46737acee4f64"
LEGACY_LAYOUTS = frozenset({LEGACY_LAYOUT_7CDAFF4, LEGACY_LAYOUT_F7C86D3})
_ENTRY_KEYS = {"render", "post", "ig", "cover"}


class DeliveryError(SrstudioError, ValueError):
    """The delivery cannot start (a render is missing) or its manifest cannot be trusted."""


class HashtagError(DeliveryError):
    """A caption on its first delivery carries more hashtags than Instagram accepts."""


def refuse_hashtags(excess: Mapping[str, str]) -> None:
    """Raise :class:`HashtagError` naming every slug in ``excess`` (slug to :func:`hashtag_excess`) with a reason."""
    said = [f"{slug}: {why}" for slug, why in excess.items() if why]
    if said:
        raise HashtagError("the hashtag limit refuses: " + "; ".join(said))


class ManifestVersionError(DeliveryError):
    """The manifest is of another version. A 1.0.0 one is migrated (:func:`migrate_manifest`); none is delivered
    over."""


@dataclass(frozen=True)
class Drift:
    """One way a delivered folder no longer matches what would be published now."""

    name: str  # the video's folder name, or "*" for the manifest itself
    reason: str

    def __str__(self) -> str:
        return f"{self.name}: {self.reason}"


class Item(NamedTuple):
    """One published video: its post, its render, and the scene its cover is drawn from (None: the video's frame)."""

    post: InstagramPost
    video: Path
    scene: Path | None = None


Items = dict[str, Item]  # video name -> what is delivered for it


_sha = digest.sha256


def render_steps() -> dict[str, Any]:
    """The fixed steps between a post and its cover besides the composed document: how the backdrop frame is chosen
    and written, the scene variant it is drawn in, and how the engine and the encoder make the JPEG."""
    return {
        "frame": FRAME_SLACK,
        "backdrop": list(BACKDROP_ARGS),
        "variant": COVER_VARIANT,
        "engine": list(drawing.ENGINE_ARGS),
        "encoder": list(drawing.ENCODER_ARGS),
    }


def fingerprint(post: InstagramPost, video: Path, font: Path, scene: Path | None = None) -> str:
    """What the delivered files are made from besides the video's frames: the caption, the thumbnail spec, the
    headline font, the cover's drawing (the document :func:`~srstudio.thumbnail.compose` lays out at ``video``'s size,
    with the sources :func:`~srstudio.thumbnail.render` gives it), the :func:`render_steps` and, when the cover is drawn
    from it, the scene document. Any change to one of them changes this digest; an edit to the code that changes none
    of them does not. Runs no engine, ffmpeg or ffprobe. Raises :class:`CoverError` for a font that cannot be read or
    a video whose size cannot be read, and :class:`~srstudio.thumbnail.ThumbnailError` for a thumbnail that cannot be
    laid out."""
    try:
        font_bytes = Path(font).read_bytes()
    except OSError as e:
        raise CoverError(f"the headline font {font} cannot be read: {e.strerror or e}") from None
    cover = None
    if post.thumbnail is not None:
        width, height = video_size(video)
        document = drawing.compose(post.thumbnail, backdrop=drawing.BACKDROP_FILE, font=drawing.FONT_FILE,
                                   font_bytes=font_bytes, width=width, height=height)  # fmt: skip
        cover = hashlib.sha256(document.to_bytes()).hexdigest()
    data = {
        "text": post.text(),
        "thumbnail": asdict(post.thumbnail) if post.thumbnail is not None else None,
        "font": hashlib.sha256(font_bytes).hexdigest(),
        "cover": cover,
        "steps": render_steps(),
    }
    if scene is not None:
        data["scene"] = _sha(scene) if Path(scene).is_file() else "missing"
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _legacy_fingerprint(post: InstagramPost, font: Path, scene: Path | None, layout: str) -> str:
    """The 1.0.0 post fingerprint, as delivered before ADR 0037: ``layout`` was the hash of the layout source."""
    data = {
        "text": post.text(),
        "thumbnail": asdict(post.thumbnail) if post.thumbnail is not None else None,
        "font": _sha(font),
        "layout": layout,
    }
    if scene is not None:
        data["scene"] = _sha(scene) if Path(scene).is_file() else "missing"
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _load(path: Path) -> tuple[Any, dict[str, dict[str, str]]]:
    """The version and the entries of the manifest at ``path``, of any version. Raises :class:`DeliveryError` for
    a manifest that cannot be read, unknown fields or a malformed entry."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise DeliveryError(f"{path} cannot be read: {e}") from e
    if not isinstance(data, dict) or set(data) != {"version", "videos"}:
        raise DeliveryError(f"{path} must hold exactly 'version' and 'videos'")
    videos = data["videos"]
    if not isinstance(videos, dict):
        raise DeliveryError(f"{path}: 'videos' must be an object")
    for name, entry in videos.items():
        if not isinstance(entry, dict) or set(entry) != _ENTRY_KEYS:
            raise DeliveryError(f"{path}: entry {name!r} must hold exactly {sorted(_ENTRY_KEYS)}")
        if not all(isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v) for v in entry.values()):
            raise DeliveryError(f"{path}: entry {name!r} holds a value that is not a SHA-256")
    return data["version"], videos


def read_manifest(out: Path) -> dict[str, dict[str, str]]:
    """The entries of ``<out>/delivery.json``; an absent manifest is empty. Raises :class:`ManifestVersionError` for
    a manifest of another version and :class:`DeliveryError` for unknown fields or a malformed entry."""
    path = Path(out) / MANIFEST
    if not path.exists():
        return {}
    version, videos = _load(path)
    if version == LEGACY_VERSION:
        raise ManifestVersionError(f"{path} is version {LEGACY_VERSION!r}, whose post fingerprints hash the layout "
                                   "source; run instagram_posts.py migrate (ADR 0037)")  # fmt: skip
    if version != MANIFEST_VERSION:
        raise ManifestVersionError(f"{path} is version {version!r}; this srstudio reads {MANIFEST_VERSION}")
    return videos


@contextmanager
def _locked(out: Path) -> Iterator[None]:
    """Hold the delivery's exclusive lock: one writer of ``delivery.json`` at a time."""
    lock = Path(out) / (MANIFEST + ".lock")
    with lock.open("a") as held:
        lock.chmod(0o600)
        fcntl.flock(held, fcntl.LOCK_EX)
        yield


def _write(out: Path, entries: dict[str, dict[str, str]]) -> None:
    """Replace ``<out>/delivery.json`` (mode 600) in one step; the caller holds the lock."""
    manifest = Path(out) / MANIFEST
    tmp = manifest.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"version": MANIFEST_VERSION, "videos": dict(sorted(entries.items()))}, indent=2) + "\n",
                   encoding="utf-8")  # fmt: skip
    tmp.chmod(0o600)
    tmp.replace(manifest)


def check_delivery(
    items: Items, out: Path, *, font: Path, frozen: Mapping[str, str] | None = None, held: Collection[str] = ()
) -> list[Drift]:
    """Every way ``out`` differs from delivering ``items`` now; an empty list means the delivery is current.

    A video drifts when its render is missing or changed since its cover was made, its post or thumbnail (or the
    font or the cover's drawing) changed, its ``ig.txt`` or ``cover.jpg`` is missing or was edited, or it was never
    delivered. A delivered folder whose video is no longer in ``items`` drifts too. ``frozen`` maps a published
    video to the fingerprint its post draws now that the operator accepted (ADR 0040): its delivery is current at
    that drawing and no other, and every other check still holds. A ``held`` video was stopped before its first
    delivery (ADR 0140): it owes no delivery, and one that was delivered all the same drifts. Raises
    :class:`DeliveryError` when ``frozen`` or ``held`` names a video not in ``items``. Runs no engine, ffmpeg or
    ffprobe."""
    out = Path(out)
    frozen = _frozen(items, frozen)
    held = _held(items, held)
    try:
        delivered = read_manifest(out)
    except DeliveryError as e:
        return [Drift("*", str(e))]
    drift = []
    for name, (post, video, scene) in sorted(items.items()):
        entry = delivered.get(name)
        if name in held:
            if entry is not None:
                drift.append(Drift(name, "held, but delivered: release the hold or take the delivery back"))
            continue
        if not Path(video).is_file():
            drift.append(Drift(name, f"no render at {video}"))
            continue
        if entry is None:
            drift.append(Drift(name, "never delivered"))
            continue
        if _sha(video) != entry["render"]:
            drift.append(Drift(name, "the video was re-rendered after its cover was made"))
        try:
            now = fingerprint(post, video, font, scene)
        except (CoverError, ThumbnailError) as e:
            drift.append(Drift(name, f"the cover cannot be drawn now: {e}"))
        else:
            if now not in (entry["post"], frozen.get(name)):
                drift.append(
                    Drift(name, "the post, its thumbnail, its scene, the font or the layout changed since delivery")
                )
        for key, file in (("ig", FILE_NAME), ("cover", COVER_NAME)):
            path = out / name / file
            if not path.is_file():
                drift.append(Drift(name, f"{file} is missing"))
            elif _sha(path) != entry[key]:
                drift.append(Drift(name, f"{file} was changed after delivery"))
    for name in sorted(set(delivered) - set(items)):
        drift.append(Drift(name, "delivered, but no longer published"))
    return drift


def _frozen(items: Items, frozen: Mapping[str, str] | None) -> dict[str, str]:
    frozen = dict(frozen or {})
    unknown = sorted(set(frozen) - set(items))
    if unknown:
        raise DeliveryError(f"frozen names a video that is not published: {', '.join(unknown)}")
    return frozen


def _held(items: Items, held: Collection[str]) -> frozenset[str]:
    unknown = sorted(set(held) - set(items))
    if unknown:
        raise DeliveryError(f"held names a video that is not published: {', '.join(unknown)}")
    return frozenset(held)


def publish(
    items: Items,
    out: Path,
    *,
    font: Path,
    engine: str | Path,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
    only: Collection[str] | None = None,
    frozen: Mapping[str, str] | None = None,
    held: Collection[str] = (),
) -> list[Path]:
    """Deliver every item that drifted, record ``<out>/delivery.json`` and return the folders written.

    Every render must exist before anything is written. A video no longer in ``items`` is dropped from the
    manifest (its folder is left for the operator to remove). After this, :func:`check_delivery` is empty.

    ``only`` names the videos to deliver: the others keep their manifest entries as they are (and need no
    render), so :func:`check_delivery` still reports whatever drifted among them. It needs a readable manifest.

    A ``frozen`` video current at its accepted drawing is not delivered again: its files and entry stay as
    published. A ``held`` video is passed over, and naming one in ``only`` raises :class:`DeliveryError`."""
    out = Path(out)
    frozen = _frozen(items, frozen)
    held = _held(items, held)
    if only is not None:
        unknown = sorted(set(only) - set(items))
        if unknown:
            raise DeliveryError(f"not a published video: {', '.join(unknown)}")
        if not only:
            raise DeliveryError("only must name at least one video")
        stopped = sorted(set(only) & held)
        if stopped:
            raise DeliveryError(f"held, not delivered: {', '.join(stopped)}")
    chosen = (set(items) if only is None else set(only)) - held
    missing = sorted(name for name, item in items.items() if name in chosen and not Path(item.video).is_file())
    if missing:
        raise DeliveryError(f"no render for: {', '.join(missing)}")
    try:
        delivered = read_manifest(out)
    except ManifestVersionError:
        raise  # a manifest of another version is migrated or left alone, never delivered over
    except DeliveryError:
        if only is not None:
            raise  # the entries of the videos left alone cannot be kept from a manifest that cannot be read
        delivered = {}  # an unreadable manifest is replaced: every item is delivered again below
    stale = (
        {d.name for d in check_delivery(items, out, font=font, frozen=frozen, held=held)} if delivered else set(items)
    )
    out.mkdir(parents=True, exist_ok=True)
    out.chmod(0o700)
    written, entries = [], {}
    for name, (post, video, scene) in sorted(items.items()):
        folder = out / name
        if name not in chosen:
            if name in delivered:
                entries[name] = delivered[name]
            continue
        if name not in stale and "*" not in stale:
            entries[name] = delivered[name]  # current: what was recorded is what is there
            continue
        post.deliver(folder, video, font=font, engine=engine, ffmpeg=ffmpeg, ffprobe=ffprobe, scene=scene)
        folder.chmod(0o700)
        written.append(folder)
        entries[name] = {"render": _sha(video), "post": fingerprint(post, video, font, scene),
                         "ig": _sha(folder / FILE_NAME), "cover": _sha(folder / COVER_NAME)}  # fmt: skip
    with _locked(out):  # the covers above render unlocked
        if only is not None:  # another delivery may have written its videos since the read above: keep them
            now = read_manifest(out)
            entries = {name: now[name] for name in items if name not in chosen and name in now} | {
                name: entries[name] for name in chosen
            }
        _write(out, entries)
    return written


class Migration(NamedTuple):
    """What :func:`migrate_manifest` did, or would do: the entries rewritten, and each entry kept with why."""

    migrated: list[str]
    kept: list[tuple[str, str]]


def _plan(items: Items, path: Path, font: Path) -> tuple[Migration, dict[str, dict[str, str]]]:
    """The migration of the 1.0.0 manifest at ``path`` and the entries it leaves."""
    version, videos = _load(path)
    if version == MANIFEST_VERSION:
        raise DeliveryError(f"{path} is already version {MANIFEST_VERSION}; there is nothing to migrate")
    if version != LEGACY_VERSION:
        raise ManifestVersionError(f"{path} is version {version!r}; only a {LEGACY_VERSION} manifest is migrated")
    migrated, kept, entries = [], [], dict(videos)
    for name, entry in sorted(videos.items()):
        item = items.get(name)
        if item is None:
            kept.append((name, "no longer published"))
            continue
        post, video, scene = item
        if not Path(video).is_file():
            kept.append((name, f"no render at {video}"))
        elif entry["post"] not in {_legacy_fingerprint(post, font, scene, layout) for layout in LEGACY_LAYOUTS}:
            kept.append((name, f"its post is not the {LEGACY_VERSION} fingerprint of the post now: the post, its "
                               "thumbnail, its scene or the font changed since delivery"))  # fmt: skip
        else:
            try:
                now = fingerprint(post, video, font, scene)
            except (CoverError, ThumbnailError) as e:
                kept.append((name, f"the cover cannot be drawn now: {e}"))
            else:
                entries[name] = entry | {"post": now}
                migrated.append(name)
    return Migration(migrated, kept), entries


def migrate_manifest(items: Items, out: Path, *, font: Path, dry_run: bool = False) -> Migration:
    """Move ``<out>/delivery.json`` from version 1.0.0 to :data:`MANIFEST_VERSION` once, on proof (ADR 0037).

    An entry's ``post`` is rewritten to :func:`fingerprint` only when it equals the 1.0.0 fingerprint of the post
    now, recomputed with one of the :data:`LEGACY_LAYOUTS`: then the delivery was made from exactly this post, font
    and scene.
    Every other entry is kept as it was, so :func:`check_delivery` still reports it. ``render``, ``ig`` and
    ``cover`` are never changed, and nothing is drawn or delivered. The manifest is read and replaced under the
    delivery lock, in one step. ``dry_run`` returns the same plan and writes nothing, not even the lock. Raises
    :class:`DeliveryError` for a missing manifest, one that cannot be read or one that is not version 1.0.0, and for a
    font that cannot be read: without it no entry could be proven, and a 1.1.0 manifest is never migrated again."""
    path = Path(out) / MANIFEST
    if not path.is_file():
        raise DeliveryError(f"{out} has no {MANIFEST} to migrate")
    try:
        Path(font).read_bytes()
    except OSError as e:
        raise DeliveryError(
            f"the headline font {font} cannot be read ({e.strerror or e}); nothing is migrated"
        ) from None
    if dry_run:
        return _plan(items, path, font)[0]
    with _locked(out):
        result, entries = _plan(items, path, font)
        _write(out, entries)
    return result
