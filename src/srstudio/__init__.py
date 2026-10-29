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
    lipsync,
    locations,
    music,
    props,
    registry,
    signature,
    soft_props,
    stick,
    stick_car,
    styles,
    subtitles,
    toon,
    toon_cast,
    toon_props,
    toon_sets,
)
from .canvas import (
    CAFE,
    DAYLIGHT,
    LINEN,
    MONO,
    OFFICE,
    PEACH,
    WARM,
    Canvas,
    Palette,
    Signature,
    flat_counter,
    shared_counter,
)
from .episode import Episode, EpisodeSpec
from .layout import VERTICAL, SafeArea
from .lipsync import SPEECH_MOUTH
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
from .styles import CEL, CUTOUT, INK, SOFT, STICK, STYLES, TOON, Font, Mix, Style, StyleError
from .thumbnail import Thumbnail, ThumbnailError
from .timeline import Take, Timeline

__version__ = "0.1.0"
__all__ = [
    "Episode",
    "EpisodeSpec",
    "Style",
    "Mix",
    "StyleError",
    "Font",
    "CUTOUT",
    "INK",
    "SOFT",
    "CEL",
    "STICK",
    "TOON",
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
    "DAYLIGHT",
    "PEACH",
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
    "SPEECH_MOUTH",
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
    "Thumbnail",
    "ThumbnailError",
]
