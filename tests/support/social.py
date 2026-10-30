"""What test_social.py shares with other test modules."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from srstudio.sample import SYSTEM_FONTS
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

FONT = next(f for f in SYSTEM_FONTS if f.exists())  # DejaVu Sans Bold, the fixture font


def needs_ffmpeg():
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        pytest.skip("needs ffmpeg and ffprobe")


def video(path: Path, *, seconds: float = 1, fps: int = 10, size: str = "64x112", lum: str = "X*2+N*10") -> Path:
    """A small lossless video whose frame n has a horizontal ramp brightened by 10 per frame (or ``lum``)."""
    needs_ffmpeg()
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"nullsrc=s={size}:r={fps}:d={seconds}",
         "-vf", f"geq=lum='{lum}':cb=128:cr=128", "-c:v", "libx264", "-qp", "0", "-pix_fmt", "yuv420p", str(path)],
        check=True,
    )  # fmt: skip
    return path


def engine() -> str:
    found = os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")
    if not found:
        pytest.skip("needs SRSTUDIO_ENGINE")
    return found


def tall(path: Path, lum: str = "X/3+Y/5+N*10") -> Path:
    """A portrait clip big enough for a headline in the fixture font."""
    return video(path, seconds=1, fps=4, size="540x960", lum=lum)


def post(headline: str = "Hi", at: float = 0.3, **kw) -> InstagramPost:
    return InstagramPost(title="t", description="d", thumbnail=Thumbnail(headline, at, kicker="K"), **kw)
