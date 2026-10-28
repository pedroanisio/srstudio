"""srstudio: a reusable, extensible kit for scene-render episodes on the sr-core scene SDK.

    from srstudio import Episode, EpisodeSpec, cast, locations, props, graphics, camera

Build an episode from its ``dialogue.json`` and soundtrack, place registered characters in
registered locations, add graphics and captions, and ``finish()`` to check and write the
``.scene.xml``. ``srstudio.registry.catalog()`` lists everything available.
"""

from . import (  # noqa: F401  (registers builders)
    blob,
    camera,
    cast,
    cel,
    graphics,
    ink,
    layout,
    locations,
    music,
    props,
    registry,
    signature,
    styles,
    subtitles,
)
from .canvas import CAFE, LINEN, MONO, OFFICE, WARM, Canvas, Palette, Signature, flat_counter, shared_counter
from .episode import Episode, EpisodeSpec
from .layout import VERTICAL, SafeArea
from .registry import catalog, get, register
from .rig import Actor, Performance
from .social import InstagramPost, InstagramPostError
from .soundtrack import (
    CAFE_MOUTH,
    INK_MOUTH,
    OFFICE_MOUTH,
    SOFT_MOUTH,
    MouthStyle,
    PhonemeStyle,
    Soundtrack,
    mouth_states,
    phoneme_states,
)
from .styles import CEL, CUTOUT, INK, SOFT, STYLES, Font, Style, StyleError
from .timeline import Take, Timeline

__version__ = "0.1.0"
__all__ = [
    "Episode",
    "EpisodeSpec",
    "Style",
    "StyleError",
    "Font",
    "CUTOUT",
    "INK",
    "SOFT",
    "CEL",
    "STYLES",
    "styles",
    "Canvas",
    "Palette",
    "Signature",
    "signature",
    "OFFICE",
    "CAFE",
    "MONO",
    "WARM",
    "LINEN",
    "shared_counter",
    "flat_counter",
    "Actor",
    "Performance",
    "Timeline",
    "Take",
    "Soundtrack",
    "MouthStyle",
    "PhonemeStyle",
    "OFFICE_MOUTH",
    "CAFE_MOUTH",
    "INK_MOUTH",
    "SOFT_MOUTH",
    "mouth_states",
    "phoneme_states",
    "catalog",
    "get",
    "register",
    "cast",
    "locations",
    "props",
    "graphics",
    "camera",
    "ink",
    "blob",
    "cel",
    "music",
    "subtitles",
    "layout",
    "SafeArea",
    "VERTICAL",
    "registry",
    "InstagramPost",
    "InstagramPostError",
]
