"""Drawing primitives on top of ``sr_core.scene``.

A :class:`Canvas` owns the scene, its ``<assets>``, ``<paints>``, ``<effects>`` and ``<composition>``,
and hands out ids, gradients, shapes, text layers, effects, text animators and keyframes. Every builder in the
library (cast, locations, props, graphics) only ever talks to a canvas, so a new item
needs nothing but these few calls.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Literal

from sr_core.scene import Animate, Scene, SchemaValueError

from . import checks, drawing_events
from ._counter import Counter
from ._transaction import scene_transaction
from .errors import SrstudioError, _brief
from .held_keys import held_key, project_fps
from .native import NativeError

CLEAR = "#00000000"


class CanvasError(SrstudioError, ValueError):
    """A drawing call the canvas cannot make: an unnamed effect, an undefined symbol, text without a font, a
    visibility span that runs backwards."""


class KeyTimeError(CanvasError, SchemaValueError):
    """Invalid key time with SDK repair fields and the existing schema-error catch contract."""

    def __reduce__(self):
        # SchemaValueError's reducer rebuilds only the base schema exception. Keep
        # this subtype and its explicit SDK repair fields when crossing processes.
        return type(self), self.args, self.__dict__


Align = Literal["start", "center", "end", "justify"]


@dataclass(frozen=True)
class Palette:
    """The ink, paper and clear colours a family of drawings shares."""

    ink: str
    white: str
    clear: str = CLEAR
    shade: str = "#BEBEBE"  # the one mid tone of a monochrome family
    name: str = ""  # how a Style and EpisodeSpec refer to it
    background: str = ""  # the stage colour an episode in this palette starts from


OFFICE = Palette(ink="#111314", white="#FEFEFC", name="office", background="#D5DFDF")
CAFE = Palette(ink="#243234", white="#FFF9EB", name="cafe", background="#F0DDC0")
MONO = Palette(ink="#282828", white="#FFFFFF", shade="#BEBEBE", name="mono", background="#FFFFFF")
WARM = Palette(ink="#231E19", white="#FFFFFF", shade="#E9D3C3", name="warm", background="#F3DFCF")
# Cel: traced fills on a greige wall; the one mid tone is the teal of the lettering boxes, white is the lettering
LINEN = Palette(ink="#240102", white="#fffaf5", shade="#2b87ab", name="linen", background="#c5bbb0")
# Stick: heavy near-black ink, white caption text, the warm brown line the sets are outlined in, on a sand wall
DAYLIGHT = Palette(ink="#070708", white="#ffffff", shade="#665541", name="daylight", background="#bda77a")
# Toon: near-black ink, white caption pills, the cat's blue as the one mid tone, on a cream-to-peach wall
PEACH = Palette(ink="#0b0a0d", white="#ffffff", shade="#5bb7db", name="peach", background="#f8ead9")
# Saga: deep-space navy ink, cream lettering, the gold of rim lights and the sung caption word, on the void
VOID = Palette(ink="#0b0d1a", white="#fff4dc", shade="#f2b84b", name="void", background="#070914")
# Gloss: plum ink on glossy pastel vinyl, hot-pink shade, a lavender sky (ADR 0030)
PLASTIC = Palette(ink="#2a1f3d", white="#fff8ee", shade="#ff5fa2", name="plastic", background="#e9defa")


@dataclass(frozen=True)
class Signature:
    """What signs an episode (ADR 0001): the recurring code; the cactus needs no parameter."""

    code: str = "SR-1028"


def shared_counter(start: int = 0) -> Callable[[str], str]:
    """An id namer with one counter for every prefix: ``g1, p2, e3, txt4``..."""
    return Counter(None, start)


def flat_counter(prefix: str = "v", start: int = 0) -> Callable[[str], str]:
    """An id namer with one counter and one prefix for every node, whatever the caller asks: ``v1, v2, v3``..."""
    return Counter(prefix, start)


Keys = Sequence[tuple[float, float | int | str]]
Spans = Iterable[tuple[float, float]]


def _visibility_keys(spans: Spans) -> list[tuple[float, int]]:
    """One union of spans, shared by visibility gates and complementary rig layers."""
    intervals = []
    if not isinstance(spans, Iterable) or isinstance(spans, (str, bytes)):
        raise CanvasError(
            'visibility spans must be iterable pairs',
            code='canvas.visibility.shape',
            path='visibility',
            actual=spans,
            expected='an iterable of (start, end) pairs',
            remedy='Provide finite time spans, or an empty iterable to keep the layer hidden.',
        )
    for index, span in enumerate(spans):
        if not isinstance(span, (tuple, list)) or len(span) != 2:
            raise CanvasError(
                'a visibility span needs a start and end',
                code='canvas.visibility.shape',
                path=f'visibility[{index}]',
                actual=span,
                expected='a (start, end) pair',
                remedy='Supply exactly two finite seconds for each visibility span.',
            )
        start, end = span
        if not (checks.number(start) and checks.number(end) and 0 <= start <= end):
            raise CanvasError(
                f"visibility span {_brief(start)}..{_brief(end)} must be finite with 0 <= start <= end",
                code='canvas.visibility.time',
                path=f'visibility[{index}]',
                actual=span,
                expected='finite seconds with 0 <= start <= end',
                remedy='Order the endpoints and use nonnegative seconds on the owning canvas clock.',
            )
        if end > start:
            intervals.append((float(start), float(end)))
    merged: list[tuple[float, float]] = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    events = {0.0: 0}
    for start, end in merged:
        events[start] = 1
        events[end] = 0
    return sorted(events.items())


class Canvas:
    """The scene plus the helpers every builder needs."""

    def __init__(
        self,
        scene: Scene,
        palette: Palette = OFFICE,
        font_asset: str | None = "caption-font",
        width: int = 1080,
        height: int = 1920,
        namer: Callable[[str], str] | None = None,
        local_time: bool = False,
        signature: Signature | None = None,
        bleed: bool = False,
        held_frames: bool = False,
    ):
        self.scene = scene
        self.palette = palette
        self.font_asset = font_asset
        self.width = width
        self.height = height
        self.namer = namer
        self.local_time = local_time  # animations default to timeBase="local" (shot sequences)
        self.signature = signature  # None: an unsigned build (srstudio.signature draws nothing)
        self.bleed = bleed  # far planes blurred past the frame's edge (srstudio.look.sheet); False as published
        # held keys half a frame before the frame that first shows them (ADR 0216); False keeps the published
        # round(t, 6), which lands a change on a frame time one frame late whenever the rounding goes up
        self.held_frames = held_frames
        self._held_rate: Fraction | None = None  # the project's frame rate, read at the first held key
        self._sig_ids: dict[str, int] = {}
        self._assets = None
        self._paints = None
        self.comp = scene.add_composition()
        self._serial = 0
        self._gradients: dict[
            str, tuple[str, tuple[tuple[float, str], ...], tuple[float, ...], str | None, str | None]
        ] = {}
        self._symbols: dict[str, Any] = {}
        self._symbol_root: Any = None
        self._effects: dict[str, tuple[str, dict[str, Any]]] = {}
        self._effect_root: Any = None
        self._frozen = 0  # inside Canvas.frozen(): every key holds its value at 0 s
        self._frozen_hidden: set[Any] = set()
        self.anatomy: dict[tuple[str, str], str] = {}  # (rule, part): what a build drew against the anatomy rules
        self.limbs: dict[tuple[str, Any], Any] = {}  # (node id, side): whose hand it is (srstudio.anatomy_ledger.Limb)

    @property
    def assets(self):
        """``<assets>``, created on first use so a silent, font-less scene has none."""
        if self._assets is None:
            self._assets = self.scene.add_assets()
        return self._assets

    @property
    def paints(self):
        """``<paints>``, created on the first gradient so a flat drawing has none."""
        if self._paints is None:
            self._paints = self.scene.add_paints()
        return self._paints

    # -- colours -----------------------------------------------------------------------
    @property
    def ink(self) -> str:
        return self.palette.ink

    @property
    def white(self) -> str:
        return self.palette.white

    @property
    def clear(self) -> str:
        return self.palette.clear

    @property
    def shade(self) -> str:
        return self.palette.shade

    def note_anatomy(self, rule: str, part: str, detail: str) -> None:
        """Note that this build drew ``part`` against ``rule`` of the anatomy rules; see :mod:`srstudio.anatomy_ledger`,
        which refuses the reel when it finishes."""
        self.anatomy[(rule, part)] = detail

    # -- ids and paints ------------------------------------------------------------------
    def uid(self, prefix: str) -> str:
        """``prefix-0001``, ``prefix-0002``...: stable ids for anonymous shapes (or the ``namer``'s own)."""
        if self.namer is not None:
            return drawing_events.allocated(self.namer(prefix))
        self._serial += 1
        return drawing_events.allocated(f"{prefix}-{self._serial:04d}")

    def grad(
        self,
        name: str,
        stops: Sequence[tuple[float, str]],
        xy=(0, 0, 1, 1),
        *,
        units: str | None = None,
        interpolation_space: str | None = "srgb",
    ) -> str:
        """A named linear gradient; identical declarations reuse it, conflicting settings raise NativeError."""
        return self._gradient(name, "linearGradient", stops, xy, units, interpolation_space)

    def rgrad(
        self,
        name: str,
        stops: Sequence[tuple[float, str]],
        circle=(0.5, 0.5, 0.5),
        *,
        units: str | None = None,
        interpolation_space: str | None = "srgb",
    ) -> str:
        """A named radial gradient about ``circle`` (cx, cy, r as fractions of the painted box); returns the
        ``url(#name)`` paint. Identical declarations reuse it; conflicting settings raise NativeError."""
        return self._gradient(name, "radialGradient", stops, circle, units, interpolation_space)

    def _gradient(
        self,
        name: str,
        kind: str,
        stops: Sequence[tuple[float, str]],
        geometry: Sequence[float],
        units: str | None,
        interpolation_space: str | None,
    ) -> str:
        definition = (
            kind,
            tuple((offset, color) for offset, color in stops),
            tuple(geometry),
            units,
            interpolation_space,
        )
        if name in self._gradients:
            if self._gradients[name] != definition:
                raise NativeError(f"gradient {name!r} is already declared with different settings")
            return f"url(#{name})"
        axes = ("x1", "y1", "x2", "y2") if kind == "linearGradient" else ("cx", "cy", "r")
        attrs: dict[str, Any] = dict(zip(axes, geometry, strict=True))
        if units is not None:
            attrs["units"] = units
        if interpolation_space is not None:
            attrs["interpolationSpace"] = interpolation_space
        builder = self.paints.add_linearGradient if kind == "linearGradient" else self.paints.add_radialGradient
        g = builder(id=name, **attrs)
        for offset, color in definition[1]:
            g.add_stop(offset=offset, color=color)
        self._gradients[name] = definition
        return f"url(#{name})"

    def effect(self, name: str, type: str, **attrs) -> str:
        """A named ``<effect>`` of ``type`` (blur, drop-shadow, inner-shadow, directional-blur, vignette...);
        returns its id for a node's ``effects`` or :meth:`apply`. Created once per name: a second call with the same
        type and settings returns the first, other settings under the same name are refused."""
        if not name.strip():
            raise CanvasError("an effect needs a name")
        if name in self._effects:
            if self._effects[name] != (type, attrs):
                raise NativeError(
                    f"effect {name!r} is already declared as {self._effects[name][0]} with other settings"
                )
            return name
        if self._effect_root is None:
            self._effect_root = self.scene.add_effects()
        self._effect_root.add_effect(id=name, type=type, **attrs)
        self._effects[name] = (type, attrs)
        return name

    # -- shapes -------------------------------------------------------------------------
    def path(self, parent, d: str, fill: str | None = None, stroke: str | None = None, sw: float = 3, **kw):
        fill = self.clear if fill is None else fill
        stroke = self.ink if stroke is None else stroke
        if sw and stroke != self.clear:
            kw.update(strokeCap="round", strokeJoin="round")
        return self._freeze_lifetime(
            parent.add_shape(
                id=self.uid("path"),
                shape="path",
                path=d,
                width=str(self.width),
                height=str(self.height),
                fill=fill,
                stroke=stroke,
                strokeWidth=sw,
                **kw,
            )
        )

    def rect(self, parent, x, y, w, h, fill, stroke: str | None = None, sw: float = 0, radius: float | None = 0, **kw):
        """A rectangle; ``radius=None`` leaves the attribute out (the Cel convention)."""
        stroke = self.clear if stroke is None else stroke
        if radius is not None:
            kw["radius"] = radius
        return self._freeze_lifetime(
            parent.add_shape(
                id=self.uid("rect"),
                shape="rect",
                x=x,
                y=y,
                width=w,
                height=h,
                fill=fill,
                stroke=stroke,
                strokeWidth=sw,
                **kw,
            )
        )

    def ellipse(self, parent, x, y, w, h, fill, stroke: str | None = None, sw: float = 0, **kw):
        stroke = self.clear if stroke is None else stroke
        return self._freeze_lifetime(
            parent.add_shape(
                id=self.uid("ellipse"),
                shape="ellipse",
                x=x,
                y=y,
                width=w,
                height=h,
                fill=fill,
                stroke=stroke,
                strokeWidth=sw,
                **kw,
            )
        )

    def line(self, parent, x1, y1, x2, y2, color: str | None = None, width: float = 3, **kw):
        return self.path(
            parent, f"M{x1:g} {y1:g} L{x2:g} {y2:g}", stroke=self.ink if color is None else color, sw=width, **kw
        )

    def _freeze_lifetime(self, node):
        if self._frozen and (node.start is not None or node.end is not None):
            visible_at_zero = (node.start is None or node.start <= 0) and (node.end is None or node.end > 0)
            node.start = None
            node.end = None
            if not visible_at_zero:
                node.visible = False
                self._frozen_hidden.add(node)
        return node

    def group(self, parent, id: str, **kw):
        return self._freeze_lifetime(parent.add_group(id=id, **kw))

    # -- symbols --------------------------------------------------------------------------
    def symbol(self, id: str, draw: Callable[[Any], object]) -> str:
        """Define the symbol ``id`` the first time, drawn by ``draw(symbol)``; later calls reuse it.

        A symbol without size or duration takes the document's, so static scenery needs neither. The engine
        draws each instance into an offscreen at the symbol's frame size and transforms that texture: an
        instance magnified by a camera move is sampled, not redrawn, and its edges soften. A failed drawing
        restores the scene and canvas caches so the same symbol can be retried."""
        if id not in self._symbols:
            with scene_transaction(self.scene, self):
                if self._symbol_root is None:
                    self._symbol_root = self.scene.add_symbols()
                self._symbols[id] = element = self._symbol_root.add_symbol(id=id)
                draw(element)
        return id

    def instance(self, parent, id: str, symbol: str, **kw):
        """Place ``symbol``; the engine scopes the ids inside it as ``id/inner``."""
        if symbol not in self._symbols:
            raise CanvasError(f"no symbol {symbol!r}: define it with Canvas.symbol first")
        return self._freeze_lifetime(parent.add_instance(id=id, symbol=symbol, **kw))

    # -- text ---------------------------------------------------------------------------
    def require_font(self, what: str, error: type[Exception] = CanvasError) -> str:
        """The caption font asset; a silent canvas (no font) raises ``error`` saying ``what`` needs it."""
        if self.font_asset is None:
            raise error(f"this canvas has no caption font; {what}")
        return self.font_asset

    def text(
        self, parent, name: str, value: str, x, y, w, h, size, color: str = "#FFFFFF", align: Align = "center", **kw
    ):
        """A text asset plus the layer that shows it; ``name`` is the asset id, ``name-layer`` the layer."""
        if self.font_asset is None:
            raise CanvasError("this canvas has no caption font (a silent style); set EpisodeSpec.font to draw text")
        self.assets.add_text(
            id=name,
            text=value,
            width=w,
            height=h,
            size=str(size),
            fontAsset=self.font_asset,
            color=color,
            align=align,
            verticalAlign="middle",
            lineHeight="1.12",
            **kw,
        )
        return parent.add_layer(id=name + "-layer", asset=name, x=x, y=y)

    def animate_text(self, layer, preset: str, **kw):
        """An engine text animator on a text ``layer`` (``pop``, ``typewriter``, ``word-by-word``, ``wave``...);
        ``presetStart``, ``presetDuration``, ``unit``, ``order``, ``stagger``... pass through."""
        if layer.xml_name != "layer" or layer.asset is None:
            raise NativeError(f"a text animator needs a text layer, not <{layer.xml_name} id={layer.id!r}>")
        self._refuse_frozen(f"the {preset!r} text animator")
        return layer.add_textAnimator(preset=preset, **kw)

    # -- effects --------------------------------------------------------------------------
    def apply(self, node, *effects: str):
        """Add declared ``effects`` to ``node`` (a layer, group, instance...), after the ones it has."""
        missing = [e for e in effects if e not in self._effects]
        if missing:
            raise NativeError(f"no effect {missing[0]!r}: declare it with Canvas.effect first")
        have = list(node.effects or [])
        node.effects = " ".join(have + [e for e in effects if e not in have])
        return node

    # -- animation ------------------------------------------------------------------------
    def keys(
        self, node, prop: str, values: Keys, hold: bool = True, *, kind: str | None = None, local: bool | None = None
    ):
        """Keyframes on ``prop``; ``hold`` steps between values, otherwise they interpolate linearly.

        ``kind`` names any schema interpolation (``sine-in-out``, ``cubic-out``...) and overrides ``hold``;
        ``local`` puts the keys on the shot's clock (``timeBase="local"``), default from the canvas.
        On a ``held_frames`` canvas a held key lands half a project frame before the first frame at or after its
        time (:func:`srstudio.held_keys.held_key`), and of two changes that frame would show, the later stays.
        The complete animation is built off-scene; invalid input leaves the scene unchanged."""
        if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
            raise CanvasError(
                f'keys on {_brief(prop)}: expected a sequence of key pairs',
                code='canvas.keys.shape',
                path=f'keys.{prop}',
                actual=values,
                expected='a sequence of (second, value) pairs',
                remedy='Provide a finite sequence of timed values.',
            )
        for i, row in enumerate(values):
            path = f'keys.{prop}[{i}]'
            if not isinstance(row, (tuple, list)) or len(row) != 2:
                raise CanvasError(
                    f'keys on {_brief(prop)}: expected a (second, value) pair',
                    code='canvas.keys.shape',
                    path=path,
                    actual=row,
                    expected='a (second, value) pair',
                    remedy='Give every key exactly one numeric time and one value.',
                )
            time, value = row
            if not checks.number(time):
                raise KeyTimeError(
                    f'keys on {_brief(prop)}: time must be finite',
                    code='canvas.keys.time',
                    path=path + '[0]',
                    actual=time,
                    expected='a finite numeric second, excluding booleans',
                    remedy='Replace the key time with a finite second on the selected canvas clock.',
                )
            if isinstance(value, (float, int)) and not isinstance(value, bool) and not checks.number(value):
                raise CanvasError(
                    f'keys on {_brief(prop)} at {time}: numeric values must be finite',
                    code='canvas.keys.value',
                    path=path + '[1]',
                    actual=value,
                    expected='a finite numeric value',
                    remedy='Replace the nonfinite or unrepresentable key value before emitting the animation.',
                )
        ordered = sorted(values, key=lambda kv: kv[0])
        if not ordered:
            raise CanvasError(
                f'keys on {_brief(prop)}: no keys to animate',
                code='canvas.keys.empty',
                path=f'keys.{prop}',
                actual=values,
                expected='at least one (second, value) pair',
                remedy='Provide a held key or omit this animation.',
            )
        kw: dict[str, Any] = {"property": prop, "defaultInterpolation": kind or ("hold" if hold else "linear")}
        if self.local_time if local is None else local:
            kw["timeBase"] = "local"
        if self.held_frames and kw["defaultInterpolation"] == "hold":
            if self._held_rate is None:
                self._held_rate = project_fps(self.scene)
            rate = self._held_rate
            shown = {held_key(float(t), rate): value for t, value in ordered}  # the later of one frame's changes
            timed = sorted(shown.items(), key=lambda kv: kv[0])
        else:
            timed = [(round(float(t), 6), value) for t, value in ordered]
        a = Animate(**kw)
        for t, value in timed:
            a.add_key(time=t, value=str(value))
        if self._frozen:
            value = _at_zero(ordered, hold and kind is None, prop)
            if prop == "visible" and node in self._frozen_hidden:
                value = "false"
            a = Animate(**kw)
            a.add_key(time=0, value=str(value))
        node.add(a)
        return a

    @contextmanager
    def frozen(self) -> Iterator[Canvas]:
        """Draw still: inside the block every :meth:`keys` call (and so :meth:`gate` and :meth:`pop_in`) keeps one
        key at its value at 0 s. Groups, shapes and instances created through the canvas hold their visibility at
        0 s, including timed pose runs. Expressions and text animators cannot be held still and are refused.
        Direct mutations through the underlying scene SDK bypass these canvas guarantees."""
        self._frozen += 1
        try:
            yield self
        finally:
            self._frozen -= 1
            if not self._frozen:
                self._frozen_hidden.clear()

    def _refuse_frozen(self, what: str) -> None:
        if self._frozen:
            raise CanvasError(f"a frozen drawing cannot hold {what} still")

    def gate(self, node, spans: Spans, *, local: bool | None = None):
        """Visible in the union of finite, non-negative ``spans``; overlaps and touching spans merge.

        ``local`` selects the animation clock as in :meth:`keys`, defaulting to ``Canvas.local_time``.
        """
        return self.keys(node, "opacity", _visibility_keys(spans), local=local)

    def pop_in(
        self,
        node,
        at: float,
        rest: float = 1.0,
        from_: float = 0.92,
        over: float = 1.03,
        rise: float = 0.10,
        settle: float = 0.22,
    ):
        """The overshoot used by every card: scale ``from_`` → ``over`` → ``rest`` starting at ``at``."""
        values = [(0, from_), (at, from_), (at + rise, over), (at + settle, rest)]
        self.keys(node, "scaleX", values, hold=False)
        self.keys(node, "scaleY", values, hold=False)

    def expression(self, node, prop: str, js: str):
        self._refuse_frozen(f"the expression on {prop!r}")
        node.add_expression(property=prop).content = js


def _at_zero(ordered: Sequence[tuple[float, Any]], hold: bool, prop: str) -> Any:
    """The value keys ``ordered`` by time give at 0 s: the first key's before it, the last at or before 0 s with
    hold keys; a curve between a key before 0 s and one after it is refused rather than evaluated."""
    if not ordered:
        raise CanvasError(f"keys on {prop!r}: no keys to hold")
    before = [v for t, v in ordered if t <= 0]
    if not before:
        return ordered[0][1]
    after = [t for t, _ in ordered if t > 0]
    last = max(t for t, _ in ordered if t <= 0)
    if after and last < 0 and not hold:
        raise CanvasError(f"keys on {prop!r}: a frozen drawing cannot hold a curve that runs across 0 s still")
    return before[-1]
