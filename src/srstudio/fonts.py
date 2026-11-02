"""Google Fonts for captions: fetched once, verified, pinned by SHA-256 and reused offline.

``install(GoogleFont("Poppins", 700), project / "assets" / "fonts")`` asks the Google Fonts CSS API for
the face, accepts exactly one ``@font-face`` that matches the request and points at a TrueType file on
``fonts.gstatic.com``, downloads it, and reads the file's own ``name`` and ``OS/2`` tables: the family,
weight and style it declares must be the ones requested. The licence comes from the ``google/fonts``
repository (OFL, Apache or UFL) and is stored beside the font. ``fonts.lock.json`` records the URL and
digest; a later install with the file in place makes no request, and a file whose digest changed is
refused. Nothing is written until every check passes, and what is written is private: mode 600 for the files, 700 for
the folder and any parent made for it. :func:`as_font` turns the result into the :class:`~srstudio.styles.Font` a style
or ``EpisodeSpec`` uses.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import struct
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .errors import SrstudioError

if TYPE_CHECKING:
    from .styles import Font

__all__ = [
    "MAX_BYTES",
    "FontError",
    "GoogleFont",
    "FontFacts",
    "Installed",
    "parse_css",
    "inspect_ttf",
    "text_width",
    "WordGap",
    "word_gaps",
    "install",
    "as_font",
    "fetch_url",
]

CSS_API = "https://fonts.googleapis.com/css2"
REPO = "https://raw.githubusercontent.com/google/fonts/main"
LICENCES = (("ofl", "OFL.txt", "OFL-1.1"), ("apache", "LICENSE.txt", "Apache-2.0"), ("ufl", "UFL.txt", "UFL-1.0"))
MAX_BYTES = 8 * 1024 * 1024
LOCK = "fonts.lock.json"
# An old browser agent: the CSS API then serves one TrueType file instead of WOFF2 subsets.
AGENT = "Mozilla/4.0 (compatible; srstudio)"

Fetch = Callable[[str], bytes]


class FontError(SrstudioError, RuntimeError):
    """A font request, response, file, licence or pin that cannot be trusted."""


@dataclass(frozen=True)
class GoogleFont:
    """One face of a Google Fonts family: ``GoogleFont("Poppins", 700)``."""

    family: str
    weight: int = 400
    italic: bool = False

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ]{0,63}", self.family or ""):
            raise FontError(f"font family {self.family!r} must be letters, digits and spaces")
        if self.weight not in range(100, 1000, 100):
            raise FontError(f"font weight {self.weight} must be one of 100, 200, ... 900")

    @property
    def css_url(self) -> str:
        family = urllib.parse.quote_plus(self.family)
        axis = f"ital,wght@1,{self.weight}" if self.italic else f"wght@{self.weight}"
        return f"{CSS_API}?family={family}:{axis}"

    @property
    def slug(self) -> str:
        base = f"{self.family.lower().replace(' ', '-')}-{self.weight}"
        return base + "-italic" if self.italic else base

    @property
    def repo_dir(self) -> str:
        return self.family.lower().replace(" ", "")


def fetch_url(url: str) -> bytes:
    """GET ``url`` (at most :data:`MAX_BYTES` + 1 bytes); network and HTTP failures become :class:`FontError`."""
    request = urllib.request.Request(url, headers={"User-Agent": AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310  (https URLs built above)
            return response.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise FontError(f"HTTP {exc.code} for {url}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise FontError(f"cannot fetch {url}: {exc}") from None


# -- the CSS ------------------------------------------------------------------------------------------------
_BLOCK = re.compile(r"@font-face\s*\{([^{}]*)\}")
_SRC = re.compile(r"url\((https://fonts\.gstatic\.com/[^)\s'\"]+\.ttf)\)\s+format\('truetype'\)")
_KNOWN = {"font-family", "font-style", "font-weight", "font-stretch", "font-display", "src"}


def parse_css(text: str, font: GoogleFont) -> str:
    """The TrueType URL of the single ``@font-face`` in ``text`` that matches ``font``; else :class:`FontError`."""
    blocks = _BLOCK.findall(text)
    rest = re.sub(r"/\*.*?\*/", "", _BLOCK.sub("", text), flags=re.S)
    if len(blocks) != 1 or rest.strip():
        raise FontError(f"expected exactly one @font-face, got {len(blocks)} (and {len(rest.strip())} other chars)")
    decl: dict[str, str] = {}
    for part in blocks[0].split(";"):
        if not part.strip():
            continue
        name, sep, value = part.partition(":")
        name = name.strip().lower()
        if not sep or name not in _KNOWN:
            raise FontError(f"unknown @font-face declaration {part.strip()!r}")
        decl[name] = value.strip()
    family = decl.get("font-family", "").strip("'\"")
    if family != font.family:
        raise FontError(f"the CSS describes family {family!r}, not {font.family!r}")
    if decl.get("font-weight") != str(font.weight):
        raise FontError(f"the CSS describes weight {decl.get('font-weight')!r}, not {font.weight}")
    style = "italic" if font.italic else "normal"
    if decl.get("font-style") != style:
        raise FontError(f"the CSS describes style {decl.get('font-style')!r}, not {style!r}")
    src = decl.get("src", "")
    match = _SRC.fullmatch(src)
    if not match:
        if "fonts.gstatic.com" not in src or not src.startswith("url(https://"):
            raise FontError(f"the font source {src!r} is not an https URL on fonts.gstatic.com")
        raise FontError(f"the font source {src!r} is not a single truetype file")
    return match.group(1)


# -- the font file -------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class FontFacts:
    """What a font file says about itself."""

    family: str
    weight: int
    italic: bool


def _tables(data: bytes) -> dict[bytes, bytes]:
    if len(data) < 12:
        raise FontError("font file too short for an sfnt header")
    if data[:4] not in (b"\x00\x01\x00\x00", b"true", b"OTTO"):
        raise FontError(f"not a TrueType/OpenType file (magic {data[:4]!r})")
    (count,) = struct.unpack(">H", data[4:6])
    if len(data) < 12 + 16 * count:
        raise FontError(f"font table directory of {count} entries runs past the file")
    out = {}
    for i in range(count):
        tag, _sum, offset, length = struct.unpack(">4sIII", data[12 + 16 * i : 28 + 16 * i])
        if offset + length > len(data):
            raise FontError(f"font table {tag!r} runs past the end of the file (table directory)")
        out[tag] = data[offset : offset + length]
    return out


def _names(table: bytes) -> dict[int, str]:
    if len(table) < 6:
        raise FontError("font 'name' table is truncated")
    _fmt, count, base = struct.unpack(">HHH", table[:6])
    found: dict[int, tuple[int, str]] = {}
    for i in range(count):
        at = 6 + 12 * i
        if at + 12 > len(table):
            raise FontError("font 'name' table records run past the table")
        platform, encoding, language, name_id, length, offset = struct.unpack(">HHHHHH", table[at : at + 12])
        raw = table[base + offset : base + offset + length]
        if platform == 3 and encoding in (1, 10):
            text, rank = raw.decode("utf-16-be", "replace"), 0 if language == 0x409 else 1
        elif platform == 1 and encoding == 0:
            text, rank = raw.decode("mac_roman", "replace"), 2
        else:
            continue
        if name_id not in found or rank < found[name_id][0]:
            found[name_id] = (rank, text)
    return {k: v for k, (_, v) in found.items()}


def inspect_ttf(data: bytes) -> FontFacts:
    """Family (typographic family when present), weight class and italic bit, from the file's own tables."""
    tables = _tables(data)
    if b"name" not in tables:
        raise FontError("font has no 'name' table")
    if b"OS/2" not in tables or len(tables[b"OS/2"]) < 64:
        raise FontError("font has no complete 'OS/2' table")
    names = _names(tables[b"name"])
    family = names.get(16) or names.get(1)
    if not family:
        raise FontError("font 'name' table has no family name")
    weight, selection = struct.unpack(">H", tables[b"OS/2"][4:6])[0], struct.unpack(">H", tables[b"OS/2"][62:64])[0]
    return FontFacts(family=family, weight=weight, italic=bool(selection & 1))


def _cmap(table: bytes) -> dict[int, int]:
    """Code point to glyph index from the first Unicode subtable in format 4 or 12 (what Google serves)."""
    (count,) = struct.unpack(">H", table[2:4])
    for i in range(count):
        platform, _enc, offset = struct.unpack(">HHI", table[4 + 8 * i : 12 + 8 * i])
        if platform not in (0, 3) or offset + 4 > len(table):
            continue
        (fmt,) = struct.unpack(">H", table[offset : offset + 2])
        out: dict[int, int] = {}
        if fmt == 4:
            (segx2,) = struct.unpack(">H", table[offset + 6 : offset + 8])
            n = segx2 // 2
            ends = struct.unpack(f">{n}H", table[offset + 14 : offset + 14 + segx2])
            starts = struct.unpack(f">{n}H", table[offset + 16 + segx2 : offset + 16 + 2 * segx2])
            deltas = struct.unpack(f">{n}h", table[offset + 16 + 2 * segx2 : offset + 16 + 3 * segx2])
            range_at = offset + 16 + 3 * segx2
            ranges = struct.unpack(f">{n}H", table[range_at : range_at + segx2])
            for k in range(n):
                for code in range(starts[k], min(ends[k], 0xFFFE) + 1):
                    if ranges[k] == 0:
                        out[code] = (code + deltas[k]) & 0xFFFF
                    else:
                        at = range_at + 2 * k + ranges[k] + 2 * (code - starts[k])
                        if at + 2 <= len(table):
                            (glyph,) = struct.unpack(">H", table[at : at + 2])
                            out[code] = (glyph + deltas[k]) & 0xFFFF if glyph else 0
            return out
        if fmt == 12:
            (groups,) = struct.unpack(">I", table[offset + 12 : offset + 16])
            for g in range(groups):
                first, last, glyph = struct.unpack(">III", table[offset + 16 + 12 * g : offset + 28 + 12 * g])
                for code in range(first, min(last, 0x10FFFF) + 1):
                    out[code] = glyph + code - first
            return out
    raise FontError("font 'cmap' has no Unicode subtable in format 4 or 12")


def text_width(data: bytes, text: str, size: float) -> float:
    """The advance width of ``text`` set in this font at ``size`` pixels: the sum of the glyph advances (no
    kerning), so a box drawn this wide holds the engine's run of the same text."""
    tables = _tables(data)
    for name in (b"head", b"cmap", b"hhea", b"hmtx"):
        if name not in tables:
            raise FontError(f"font has no {name.decode()!r} table")
    (upm,) = struct.unpack(">H", tables[b"head"][18:20])
    (metrics,) = struct.unpack(">H", tables[b"hhea"][34:36])
    if not upm or not metrics or len(tables[b"hmtx"]) < 4 * metrics:
        raise FontError("font 'head', 'hhea' or 'hmtx' table is inconsistent")
    cmap = _cmap(tables[b"cmap"])
    hmtx = tables[b"hmtx"]

    def advance(glyph: int) -> int:
        at = 4 * min(glyph, metrics - 1)
        return struct.unpack(">H", hmtx[at : at + 2])[0]

    return sum(advance(cmap.get(ord(ch), 0)) for ch in text) * size / upm


@dataclass(frozen=True)
class WordGap:
    """The background left between the words ``left`` and ``right`` of one line, in pixels."""

    left: str
    right: str
    px: float


def word_gaps(data: bytes, text: str, size: float, *, outline: float = 0.0) -> list[WordGap]:
    """The background between each two neighbouring words of ``text`` (lines split at ``\\n``) set in this font at
    ``size`` pixels, with an ``outline`` that wide drawn outside every letter: the right side bearing of the last
    letter, the advance of the spaces between, and the left side bearing of the next letter, from each glyph's box in
    the ``glyf`` table, less the outline reaching in from both words. Zero or less means the outlines meet and the
    two words read as one. Glyph advances only, no kerning, as :func:`text_width` measures."""
    tables = _tables(data)
    for name in (b"head", b"cmap", b"hhea", b"hmtx", b"loca", b"glyf"):
        if name not in tables:
            raise FontError(f"font has no {name.decode()!r} table")
    head, loca, glyf = tables[b"head"], tables[b"loca"], tables[b"glyf"]
    (upm,) = struct.unpack(">H", head[18:20])
    (long_loca,) = struct.unpack(">h", head[50:52])
    (metrics,) = struct.unpack(">H", tables[b"hhea"][34:36])
    if not upm or not metrics:
        raise FontError("font 'head' or 'hhea' table is inconsistent")
    cmap, hmtx = _cmap(tables[b"cmap"]), tables[b"hmtx"]

    def ink(ch: str) -> tuple[float, float]:
        """The letter's left and right side bearings, in pixels."""
        glyph = cmap.get(ord(ch), 0)
        if long_loca:
            start, end = struct.unpack(">II", loca[4 * glyph : 4 * glyph + 8])
        else:
            start, end = (2 * v for v in struct.unpack(">HH", loca[2 * glyph : 2 * glyph + 4]))
        if end <= start or end > len(glyf):
            raise FontError(f"no outline to measure for {ch!r}")
        x_min, _, x_max, _ = struct.unpack(">hhhh", glyf[start + 2 : start + 10])
        at = 4 * min(glyph, metrics - 1)
        (advance,) = struct.unpack(">H", hmtx[at : at + 2])
        return x_min * size / upm, (advance - x_max) * size / upm

    gaps = []
    for line in text.split("\n"):
        for left, spaces, right in re.findall(r"(\S+)(\s+)(?=(\S+))", line):
            px = ink(left[-1])[1] + text_width(data, spaces, size) + ink(right[0])[0] - 2 * outline
            gaps.append(WordGap(left, right, px))
    return gaps


# -- install -----------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Installed:
    path: Path
    sha256: str
    family: str
    weight: int
    italic: bool
    license: str
    license_file: Path
    url: str

    @property
    def request(self) -> GoogleFont:
        return GoogleFont(self.family, self.weight, self.italic)


_LOCK_KEYS = {"file", "sha256", "family", "weight", "italic", "license", "license_file", "url"}


def _read_lock(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise FontError(f"{path} is not JSON: {exc}") from None
    if not isinstance(data, dict) or not all(isinstance(v, dict) and set(v) == _LOCK_KEYS for v in data.values()):
        raise FontError(f"{path} does not hold font pins with exactly the keys {sorted(_LOCK_KEYS)}")
    return data


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _private_folder(folder: Path) -> None:
    """``folder`` at mode 700, with any parent that has to be made for it at 700 too; a parent already there is left."""
    missing = [p for p in (folder, *folder.parents) if not p.exists()]
    for path in reversed(missing):
        path.mkdir(mode=0o700, exist_ok=True)
    folder.chmod(0o700)


def _write_private(path: Path, data: bytes) -> None:
    """``data`` in ``path`` at mode 600, whatever mode a file already there had."""
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "wb") as out:
        os.fchmod(out.fileno(), 0o600)
        out.write(data)


def install(font: GoogleFont, folder: str | Path, *, fetch: Fetch | None = None) -> Installed:
    """The verified, pinned font file for ``font`` in ``folder``, downloading it only when it is not pinned there."""
    get = fetch if fetch is not None else fetch_url
    folder = Path(folder)
    lock = _read_lock(folder / LOCK)
    pin = lock.get(font.slug)
    if pin and (folder / pin["file"]).exists():
        path = folder / pin["file"]
        if _digest(path.read_bytes()) != pin["sha256"]:
            raise FontError(f"{path} no longer matches its pinned SHA-256 {pin['sha256']}")
        return Installed(
            path,
            pin["sha256"],
            pin["family"],
            pin["weight"],
            pin["italic"],
            pin["license"],
            folder / pin["license_file"],
            pin["url"],
        )
    css = get(font.css_url).decode("utf-8", "replace")
    url = parse_css(css, font)
    data = get(url)
    if len(data) > MAX_BYTES:
        raise FontError(f"{url} is larger than {MAX_BYTES} bytes")
    facts = inspect_ttf(data)
    if facts.family.casefold() != font.family.casefold():
        raise FontError(f"{url} is family {facts.family!r}, not {font.family!r}")
    if facts.weight != font.weight:
        raise FontError(f"{url} is weight {facts.weight}, not {font.weight}")
    if facts.italic != font.italic:
        raise FontError(f"{url} italic={facts.italic}, but italic={font.italic} was requested")
    licence = None
    for kind, name, spdx in LICENCES:
        try:
            text = get(f"{REPO}/{kind}/{font.repo_dir}/{name}")
        except FontError:
            continue
        if text.strip():
            licence = (spdx, text)
            break
    if licence is None:
        raise FontError(f"no licence for {font.family!r} in the google/fonts repository (ofl, apache, ufl)")
    spdx, text = licence
    _private_folder(folder)
    path = folder / f"{font.slug}.ttf"
    licence_path = folder / f"{font.family.lower().replace(' ', '-')}.{spdx.split('-')[0]}.txt"
    _write_private(path, data)
    _write_private(licence_path, text)
    got = Installed(path, _digest(data), font.family, font.weight, font.italic, spdx, licence_path, url)
    entry = {k: v for k, v in asdict(got).items() if k not in ("path", "license_file")}
    lock[font.slug] = {**entry, "file": path.name, "license_file": licence_path.name}
    _write_private(folder / LOCK, (json.dumps(lock, indent=2, sort_keys=True) + "\n").encode())
    return got


def as_font(installed: Installed, *, root: str | Path, id: str = "caption-font") -> Font:
    """The :class:`~srstudio.styles.Font` for an installed face, its ``src`` relative to the project ``root``."""
    from .styles import Font

    return Font(
        src=installed.path.resolve().relative_to(Path(root).resolve()).as_posix(),
        id=id,
        family=installed.family,
        weight=str(installed.weight),
        style="italic" if installed.italic else None,
        credit=f"{installed.family} (Google Fonts)",
        license=installed.license,
        google=installed.request,
    )
