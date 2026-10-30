"""An episode: project, assets, timeline, soundtrack, cast, captions, mix, check and write."""

from __future__ import annotations

import importlib.util
import json
import os
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, TypeVar, cast
from urllib.parse import quote

from sr_core.scene import AudioMix, AudioTrack, CaptionTrack, Composition, Group, Layer, Scene
from sr_core.scene import Sequence as SceneSequence
from sr_core.scene._runtime import _attr_specs

from . import checks, digest, native, signature
from ._transaction import scene_transaction
from .canvas import Canvas, Keys, Palette, Signature
from .errors import SrstudioError
from .generated import PlacedClip, load_clips, verify
from .graphics import captions as _captions
from .layout import Crossing, SafeArea, check_overlays, find_engine
from .narration import narration_cues
from .rig import Actor, Performance
from .social import InstagramPost
from .soundtrack import MouthStyle, PhonemeStyle, Soundtrack, mouth_states, validate_wav
from .styles import CUTOUT, Style
from .timeline import Phrase, Take, Timeline

if TYPE_CHECKING:
    from .limbs.integration import LimbTrack

sha256 = digest.sha256


class EpisodeError(SrstudioError, ValueError):
    """An episode the builder cannot make as asked."""


class EpisodeFileError(EpisodeError, FileNotFoundError):
    """A file the episode needs (its caption font) is not in the project."""


class EpisodeArgumentError(EpisodeError, TypeError):
    """A call the episode cannot take as given: a mouth model the style has not, an option its audio source does
    not take."""


class SceneCheckError(EpisodeError):
    """The scene failed its SDK check; ``findings`` holds what the check found, one per line of the message. A build
    entry point (``srstudio build``) turns it into its exit status."""

    def __init__(self, findings: Sequence[object]):
        self.findings = tuple(findings)
        super().__init__("\n".join(str(f) for f in self.findings))


class _FromStyle:
    """Default of the ``EpisodeSpec`` fields a :class:`~srstudio.styles.Style` decides unless the episode sets them."""

    def __repr__(self) -> str:
        return "FROM_STYLE"


FROM_STYLE: Any = _FromStyle()


class _MixDefault:
    def __repr__(self) -> str:
        return "DEFAULT"


_MIX_DEFAULT = _MixDefault()


class _StyleNamer:
    """A callable spec default that can create an independent counter for each episode."""

    def __init__(self, factory: Callable[[], Callable[[str], str]]):
        self.factory = factory
        self._name = factory()

    def __call__(self, prefix: str) -> str:
        return self._name(prefix)

    def fresh(self) -> Callable[[str], str]:
        return self.factory()


def _document_at(scene: Scene, root: Path, destination: Path) -> bytes:
    """Rebase input URIs for a document written outside its project directory."""
    if root.resolve() == destination.resolve():
        return scene.to_bytes(layout="pretty")
    prefix = quote(Path(os.path.relpath(root.resolve(), destination.resolve())).as_posix(), safe="/")
    changed = []
    try:
        for node in scene.iter():
            for name, attr in _attr_specs(type(node)).items():
                value = node._attrs.get(name)
                if (
                    attr.spec != "xs:anyURI"
                    or name in ("path", "uri", "report")
                    or not value
                    or value.startswith(("/", "#"))
                    or re.match(r"^[A-Za-z][A-Za-z0-9+.-]+:", value)
                ):
                    continue
                changed.append((node, name, value))
                node._attrs[name] = f"{prefix}/{value}"
        return scene.to_bytes(layout="pretty")
    finally:
        for node, name, value in changed:
            node._attrs[name] = value


_AudioMethod = TypeVar("_AudioMethod", bound=Callable[..., Any])


def _audio_transaction(method: _AudioMethod) -> _AudioMethod:
    """Restore scene nodes and episode/canvas state if assembly fails."""

    @wraps(method)
    def wrapped(self, *args, **kwargs):
        missing = object()
        state = {
            name: getattr(self, name, missing)
            for name in ("_mix", "_master", "_master_kw", "track", "_cover_written", "_cover_variant")
        }
        lists = {name: (getattr(self, name), getattr(self, name).copy()) for name in ("caption_specs", "_cover_hidden")}
        if state["_master_kw"] is not missing:
            state["_master_kw"] = state["_master_kw"].copy()
        cast_state = self.cast.copy()
        try:
            with scene_transaction(self.scene, self.cv):
                return method(self, *args, **kwargs)
        except Exception:
            for name, value in state.items():
                if value is missing:
                    if hasattr(self, name):
                        delattr(self, name)
                else:
                    setattr(self, name, value)
            for name, (original, contents) in lists.items():
                original[:] = contents
                setattr(self, name, original)
            self.cast.clear()
            self.cast.update(cast_state)
            raise

    return cast(_AudioMethod, wrapped)


@dataclass
class EpisodeSpec:
    """What an episode is, before it is built.

    The style (``CUTOUT`` by default) decides the frame, the clock, the input file, the caption font, the
    mouth model and the id scheme; every one of those fields can still be set here and then wins. The
    palette must be one the style is drawn in, else :class:`~srstudio.styles.StyleError`.
    """

    slug: str
    title: str
    description: str
    root: Path
    seed: int
    background: str | None = None  # default: the palette's stage colour
    style: Style = CUTOUT
    palette: Palette | str | None = None  # default: the style's first palette; a name ("cafe") is accepted
    number: str = ""
    fps: int = FROM_STYLE
    width: int = FROM_STYLE
    height: int = FROM_STYLE
    language: str = "en"
    dialogue: str = FROM_STYLE
    audio: str | None = FROM_STYLE
    audio_credit: str = ""
    font: str | None = FROM_STYLE  # None (a silent style): no font asset, and Canvas.text is refused
    font_id: str | None = FROM_STYLE
    font_family: str | None = FROM_STYLE
    font_credit: str | None = FROM_STYLE
    font_license: str | None = FROM_STYLE
    output: str | None = None
    crf: str = "18"
    audio_bitrate: str = "192000"
    mouth_style: MouthStyle | PhonemeStyle | None = FROM_STYLE  # the style's model for the palette; None if silent
    generator: str = "srstudio on the sr-core Python scene SDK"
    extra: dict = field(default_factory=dict)
    # -- options the styles differ in; FROM_STYLE unless the episode overrides --------------------------
    quality: str = "final"
    font_policy: str | None = FROM_STYLE  # project/@fontPolicy, e.g. "pinned"
    font_weight: str | None = FROM_STYLE
    font_style: str | None = FROM_STYLE  # font/@fontStyle
    output_options: dict | None = None  # replaces the default output attributes (id and path stay)
    poster: dict | None = None  # output/poster attributes
    accessibility: dict | None = None  # metadata/accessibility attributes, merged over the style's
    namer: Callable[[str], str] | None = FROM_STYLE  # id scheme for anonymous nodes (default prefix-0001)
    local_time: bool = FROM_STYLE  # animations on the shot clock (sequence styles)
    safe_area: SafeArea | None = None  # declared and made the project's; the engine enforces it (SA01)
    # -- the signature marks (docs/decisions/0001-signature.md) ----------------------------------
    signature: bool = True  # False only for packages older than the convention
    signature_code: str = "SR-1028"  # project-wide; changing it is a decision, not a per-episode choice

    def __post_init__(self) -> None:
        st = self.style
        self.palette = st.palette(self.palette)
        if self.background is None:
            self.background = self.palette.background
        font = st.font
        for name, value in (
            ("fps", st.fps),
            ("width", st.width),
            ("height", st.height),
            ("dialogue", st.dialogue),
            ("audio", st.audio),
            ("font", font.src if font else None),
            ("font_id", font.id if font else None),
            ("font_family", font.family if font else None),
            ("font_weight", font.weight if font else None),
            ("font_style", font.style if font else None),
            ("font_credit", font.credit if font else None),
            ("font_license", font.license if font else None),
            ("font_policy", font.policy if font else None),
            ("local_time", st.local_time),
        ):
            if getattr(self, name) is FROM_STYLE:
                setattr(self, name, value)
        if self.mouth_style is FROM_STYLE:
            self.mouth_style = None if st.silent else st.mouth(self.palette)
        if self.namer is FROM_STYLE:
            self.namer = _StyleNamer(st.namer) if st.namer else None
        if st.accessibility or self.accessibility:
            self.accessibility = {**st.accessibility, **(self.accessibility or {})}


class Episode:
    """Build with the helpers, then :meth:`finish` checks and writes the document."""

    def __init__(self, spec: EpisodeSpec):
        self.spec = spec
        self.root = Path(spec.root)
        self.t = Timeline.load(self.root / spec.dialogue)
        self.track = Soundtrack(self.root / spec.audio) if spec.audio else None
        self.scene = Scene(version="auto")
        project_kw: dict[str, Any] = dict(
            width=spec.width,
            height=spec.height,
            fps=str(spec.fps),
            duration=self.t.duration,
            background=spec.background,
            seed=spec.seed,
            quality=spec.quality,
        )
        if spec.font_policy:
            project_kw["fontPolicy"] = spec.font_policy
        project = self.scene.add_project(**project_kw)
        if spec.safe_area:
            spec.safe_area.declare(self.scene, project)
        metadata = self.scene.add_metadata(
            title=spec.title, description=spec.description, generator=spec.generator, language=spec.language
        )
        if spec.accessibility:
            metadata.add_accessibility(**spec.accessibility)
        output_kw = (
            spec.output_options
            if spec.output_options is not None
            else dict(
                codec="h264",
                width=spec.width,
                height=spec.height,
                fps=str(spec.fps),
                preset="fast",
                crf=spec.crf,
                faststart=True,
                audioCodec="aac",
                audioBitrate=spec.audio_bitrate,
            )
        )
        self.output = output = self.scene.add_output(
            id="main", path=spec.output or f"renders/{spec.slug}.mp4", **output_kw
        )
        if spec.poster:
            output.add_poster(**spec.poster)
        self.cv = Canvas(
            self.scene,
            cast(Palette, spec.palette),  # resolved by EpisodeSpec.__post_init__
            font_asset=spec.font_id,
            width=spec.width,
            height=spec.height,
            namer=spec.namer.fresh() if isinstance(spec.namer, _StyleNamer) else spec.namer,
            local_time=spec.local_time,
            signature=Signature(spec.signature_code) if spec.signature else None,
        )
        self._mix: AudioMix | None = None
        self._cover_hidden: list[tuple[str, str, str]] = []  # (id, property, value) overridden in the cover variant
        self._cover_written = 0
        self._cover_variant: Any = None
        # Shot-sequence layouts add the font first and their audio per take; the interview family mixes one file.
        if spec.audio:
            audio_kw = dict(id="dialogue", src=spec.audio, sha256=sha256(self.root / spec.audio))
            if spec.audio_credit:
                audio_kw["credit"] = spec.audio_credit
            self.cv.assets.add_audio(**audio_kw)
        if spec.font is not None:
            self._add_font(spec.font)
        self.caption_specs: list[tuple[float, float, str, str]] = []
        self.cast: dict[str, Actor] = {}

    def _add_font(self, font: str) -> None:
        spec = self.spec
        font_file = self.root / font
        if not font_file.exists():
            style_font = spec.style.font
            google = style_font.google if style_font and font == style_font.src else None
            hint = (
                f"; fetch it with: srstudio fonts add {google.family!r} --weight {google.weight} "
                f"--into {font_file.parent}"
                if google
                else ""
            )
            raise EpisodeFileError(f"caption font {font_file} is missing{hint}")
        font_kw: dict[str, Any] = dict(
            id=spec.font_id,
            src=font,
            family=spec.font_family,
            weight=spec.font_weight,
            sha256=sha256(font_file),
            license=spec.font_license,
        )
        if spec.font_style:
            font_kw["fontStyle"] = spec.font_style
        if spec.font_credit:
            font_kw["credit"] = spec.font_credit
        self.cv.assets.add_font(**font_kw)

    # -- shortcuts ----------------------------------------------------------------------------
    @property
    def comp(self) -> Composition:
        return self.cv.comp

    @property
    def phrases(self) -> list[Phrase]:
        return self.t.phrases

    def P(self, i: int) -> Phrase:
        return self.t.phrases[i]

    @property
    def takes(self) -> list[Take]:
        return self.t.takes

    # -- shot sequences -------------------------------------------------------------------------------
    def sequence(self, id: str = "shots") -> SceneSequence:
        """A ``<sequence>`` whose children play one after another; see :meth:`shot`."""
        return self.comp.add_sequence(id=id)

    def shot(self, sequence: SceneSequence, take: Take, id: str | None = None, **kw: Any) -> Group:
        """One take's group in a sequence, as long as the take; animations inside run on its clock."""
        return sequence.add_group(id=id or f"shot-{take.id}", end=take.duration, **kw)

    # -- camera setups --------------------------------------------------------------------------
    @_audio_transaction
    def setup(self, builder: Callable[..., Group], shots: Sequence[tuple[float, float]], **slots: Any) -> Group:
        """A location gated to its shots: ``ep.setup(locations.office_wide, shots, at_desk=...)``.

        ``builder`` receives ``shots`` and gates its root group before drawing into it."""
        return builder(self.cv, self.comp, shots=shots, **slots)

    # -- performance helpers ------------------------------------------------------------------------
    def mouth(
        self,
        role: str,
        smile: Sequence[tuple[float, float]] = (),
        style: MouthStyle | None = None,
        speaking: Sequence[tuple[float, float]] | None = None,
    ) -> list[tuple[float, str]]:
        model = style or self.spec.mouth_style
        if model is None:
            raise EpisodeArgumentError(
                f"the {self.spec.style.name} style is silent and has no mouth model; pass style= for one"
            )
        if self.track is None:
            raise EpisodeError("this episode has no soundtrack; amplitude mouths need EpisodeSpec.audio")
        if not isinstance(model, MouthStyle):
            raise EpisodeArgumentError(
                f"amplitude mouths need a MouthStyle; the {self.spec.style.name} style speaks from character "
                "timestamps (srstudio.soundtrack.phoneme_states), so pass style= explicitly"
            )
        return mouth_states(self.track, self.t, role, self.spec.fps, smile=smile, style=model, speaking=speaking)

    def perform(
        self,
        actor: Actor,
        parent: Composition | Group | SceneSequence,
        x: float,
        y: float,
        scale: float,
        *,
        mouth: Sequence[tuple[float, str]] | None = None,
        smile: Sequence[tuple[float, float]] = (),
        blinks: Sequence[tuple[float, float]] = (),
        nods: Keys = (),
        limbs: Sequence[LimbTrack] = (),
        **extras: Any,
    ) -> Group:
        """Build ``actor`` with a performance assembled from keyword arguments."""
        states = mouth if mouth is not None else self.mouth(actor.role, smile=smile)
        perf = Performance(mouth=states, blinks=list(blinks), nods=list(nods), extras=extras, limbs=limbs)
        node = actor.build(parent, x, y, scale, perf)
        self.cast[actor.tag] = actor
        return node

    # -- captions, mix, markers -----------------------------------------------------------------------
    def captions(self, specs: Sequence[tuple[float, float, str, str]] | None = None, **style: Any) -> list[Layer]:
        """Caption layers for ``specs`` (default: one per phrase, ending on the next cut)."""
        specs = list(specs) if specs is not None else self.default_captions()
        layers = _captions(self.cv, specs, **style)
        self.caption_specs.extend(specs)
        return layers

    def native_captions(
        self,
        cues: Sequence[native.Cue] | None = None,
        *,
        look: native.CaptionLook = native.CAPTION_LOOK,
        mode: native.Mode = "burn",
        id: str = "captions",
    ) -> CaptionTrack:
        """The engine's own caption track (:func:`srstudio.native.caption_track`): ``cues`` default to the words
        of the spoken takes, else one per phrase; placed in the spec's safe area, every wrapped line measured with
        the episode font, burned into the main output (``mode="sidecar"`` writes a WebVTT beside it instead)."""
        if cues is None:
            cues = native.cues_from_takes(self.takes) if self.takes else native.cues_from_phrases(self.phrases)
        font = self.root / self.spec.font if self.spec.font else None
        track = native.caption_track(
            self.scene,
            cues,
            font_asset=self.cv.font_asset,
            safe_area=self.spec.safe_area,
            width=self.spec.width,
            height=self.spec.height,
            look=look,
            output=self.output,
            mode=mode,
            id=id,
            language=self.spec.language,
            font_data=font.read_bytes() if font is not None else None,
            canvas=self.cv,
        )
        self.caption_specs.extend((c.start, c.end, c.text, f"{id}-{i + 1}") for i, c in enumerate(cues))
        return track

    def default_captions(self, lead: float = 0.06, name: str = "dialogue-{n}") -> list[tuple[float, float, str, str]]:
        """Lead each phrase, hold until the next caption or a cut after speech, and end on reaction/duration.

        Caption scripts keep their explicit end times. A camera cut within a spoken phrase never truncates it.
        """
        if not (checks.number(lead) and lead >= 0):
            raise EpisodeError(f"caption lead must be finite and non-negative, got {lead}")
        out = []
        for i, p in enumerate(self.phrases):
            if p.role == "caption" and not self.t.takes:
                end = p.end
            elif i + 1 < len(self.phrases):
                boundary = max(p.end, self.phrases[i + 1].start - lead)
                end = next((c.time for c in self.t.cuts if p.end <= c.time <= boundary + 1e-9), boundary)
            else:
                end = max(p.end, self.t.beats.get("reaction_start", self.t.duration))
            out.append((max(0.0, p.start - lead), end, p.caption, name.format(n=i + 1)))
        return out

    def mix(
        self,
        loudness: str | None = None,
        true_peak: str | None = None,
        bit_depth: str | None | _MixDefault = _MIX_DEFAULT,
        sample_rate: int | None = None,
        channels: int | None = None,
        master_first: bool = True,
    ) -> AudioMix:
        """The ``<audioMix>`` with its master, created once; tracks are added with :meth:`add_track`.

        Explicit settings update an existing mix and master; omitted settings preserve them. The initial
        defaults are -16 LUFS, -1.5 dBTP, 24-bit, 48000 Hz and stereo. ``bit_depth=None`` removes the bit depth.
        ``master_first=False`` leaves the master to :meth:`master`, after the tracks (the interview family)."""
        if self._mix is None:
            depth = "24" if isinstance(bit_depth, _MixDefault) else bit_depth
            kw: dict[str, Any] = dict(
                sampleRate=sample_rate if sample_rate is not None else 48000,
                channels=channels if channels is not None else 2,
            )
            if depth:
                kw["bitDepth"] = depth
            self._mix = self.scene.add_audioMix(**kw)
            self._master_kw = dict(
                normalize="integrated",
                loudness=loudness if loudness is not None else "-16",
                truePeak=true_peak if true_peak is not None else "-1.5",
                limiter=True,
            )
            if master_first:
                self.master()
        else:
            if sample_rate is not None:
                self._mix.sampleRate = sample_rate
            if channels is not None:
                self._mix.channels = channels
            if not isinstance(bit_depth, _MixDefault):
                self._mix.bitDepth = cast(Literal["16", "24", "32"] | None, bit_depth)
            for attribute, value in (("loudness", loudness), ("truePeak", true_peak)):
                if value is not None:
                    self._master_kw[attribute] = value
                    if getattr(self, "_master", None) is not None:
                        setattr(self._master, attribute, value)
        return self._mix

    def master(self):
        if getattr(self, "_master", None) is None:
            self._master = self.mix().add_master(**self._master_kw)
        return self._master

    def add_track(self, id: str, asset: str, **kw):
        return self.mix().add_audioTrack(id=id, asset=asset, **kw)

    def audio_mix(self, track_id="synthetic-dialogue", loudness="-16", true_peak="-1.5", bit_depth: str | None = "24"):
        """The interview family's mix: one dialogue track over the whole episode."""
        mix = self.mix(loudness, true_peak, bit_depth=bit_depth, master_first=False)
        mix.add_audioTrack(id=track_id, asset="dialogue", role="dialogue", language=self.spec.language)
        self.master()
        return mix

    @_audio_transaction
    def generated_audio(
        self,
        clips: Sequence[PlacedClip] | None = None,
        *,
        loudness="-16",
        true_peak="-1.5",
        extra: Sequence[tuple[str, str, dict]] = (),
        bit_depth: str | None = "24",
    ):
        """The mix from resolved, pinned generated clips, one ``<audioTrack>`` each.

        ``clips`` default to the ``clips`` list of ``dialogue.json``. Each clip's file must still hash
        to its pinned SHA-256 (else :class:`~srstudio.generated.ResolveError`); its ``<generated>``
        asset carries the prompt, voice and digest, so the scene records what it plays. Mouths then
        follow the clips as the mix plays them. ``extra`` adds plain audio files as
        ``(asset id, path, track attributes)``, such as a room tone."""
        clips = list(clips) if clips is not None else load_clips(self.t.meta.get("clips"))
        if not clips:
            raise EpisodeError("generated_audio needs at least one clip")
        placed = []
        for clip in clips:
            path = verify(self.root, clip.generated, clip.sha256)
            placed.append((path, clip.placement))
        mix = self.mix(loudness, true_peak, bit_depth=bit_depth, master_first=False)
        for clip in clips:
            clip.generated.declare(self.cv.assets, clip.sha256)
            clip.placement.track(mix, f"track-{clip.generated.id}", clip.generated.id)
        for asset_id, src, track_kw in extra:
            self.cv.assets.add_audio(id=asset_id, src=src, sha256=sha256(self.root / src))
            mix.add_audioTrack(id=f"track-{asset_id}", asset=asset_id, **track_kw)
        self.master()
        self.track = Soundtrack.from_clips(placed, self.t.duration, rate=int(mix.sampleRate or 48000))
        return mix

    @_audio_transaction
    def take_audio(
        self,
        take,
        *,
        id: str | None = None,
        track_id: str | None = None,
        language: str | None = None,
        effects_gain=-3,
        **track_kw,
    ):
        """A take's own audio asset and mix track at the take's start (shot-sequence layouts)."""
        if not isinstance(take.audio, str) or not take.audio.strip():
            raise EpisodeFileError(f"take {take.id}: audio path is missing")
        audio_path = self.root / take.audio
        if not audio_path.is_file():
            raise EpisodeFileError(f"take {take.id}: audio file {audio_path} is missing or not a file")
        if audio_path.suffix.lower() == ".wav":
            validate_wav(audio_path)
        aid = id or f"audio-{take.id}"
        lang = None if take.is_effect else (language or self.spec.language)
        self.cv.assets.add_audio(id=aid, src=take.audio, **({"language": lang} if lang else {}))
        kw = dict(
            start=take.start,
            role="effects" if take.is_effect else "dialogue",
            gain=effects_gain if take.is_effect else 0,
        )
        if lang:
            kw["language"] = lang
        kw.update(track_kw)
        return self.add_track(track_id or f"track-{take.id}", aid, **kw)

    @property
    def audio_source(self) -> str:
        """What the project brings to play: ``"clips"`` (pinned generated clips listed in the input's ``clips``),
        ``"takes"`` (one audio file per take), ``"mixed"`` (one mixed file, ``EpisodeSpec.audio``) or ``"silent"``."""
        if self.t.meta.get("clips"):
            return "clips"
        if self.t.takes:
            return "takes"
        if self.spec.audio:
            return "mixed"
        return "silent"

    @_audio_transaction
    def audio(
        self,
        *,
        narration: Path | None = None,
        extra: Sequence[tuple[str, str, dict]] = (),
        take: Callable[[Any], dict] | None = None,
        track_id: str | None = None,
        loudness: str | None = None,
        true_peak: str | None = None,
        duck: float | None = None,
    ) -> AudioMix | None:
        """The mix of whatever the project plays (:attr:`audio_source`), mastered as the style says (``Style.mix``)
        unless ``loudness``/``true_peak`` are given. Returns ``None`` for a silent episode.

        * ``narration``: a verified ``narration.json`` (:func:`srstudio.narration.narration_cues`), one
          ``vo-NN`` asset and ``vo-track-NN`` track per cue; used when given, whatever else the project holds.
        * clips: :meth:`generated_audio`; ``extra`` adds plain files as ``(asset id, path, track attributes)``.
        * takes: :meth:`take_audio` for every take, with ``take(take)`` as its track attributes, then ``extra``.
        * mixed: :meth:`audio_mix` on ``track_id``.

        ``duck`` (dB, negative) lowers every ``music`` track by that much while any ``dialogue`` track plays, so a
        spoken line is never masked by the score (``duckUnder``/``duckAmount``; clips and takes only).

        An option the source does not take is an :class:`EpisodeArgumentError` (a ``TypeError``), so a misplaced
        argument is never ignored."""
        source = "narration" if narration is not None else self.audio_source
        allowed = {
            "narration": set(),
            "clips": {"extra", "duck"},
            "takes": {"extra", "take", "duck"},
            "mixed": {"track_id"},
            "silent": set(),
        }[source]
        options = (("extra", extra), ("take", take), ("track_id", track_id), ("duck", duck is not None))
        given = {name for name, value in options if value}
        if given - allowed:
            unknown = ", ".join(f"{k}=" for k in sorted(given - allowed))
            raise EpisodeArgumentError(f"a {source} project takes no {unknown}")
        style = self.spec.style.mix
        loud, peak = loudness or style.loudness, true_peak or style.true_peak
        if source == "silent":
            return None
        if source == "mixed":
            return self.audio_mix(track_id or "synthetic-dialogue", loud, peak, bit_depth=style.bit_depth)
        if duck is not None and not (checks.number(duck) and duck < 0):
            raise EpisodeError(f"duck {duck} must be a negative number of dB")
        if source == "clips":
            mix = self.generated_audio(loudness=loud, true_peak=peak, extra=extra, bit_depth=style.bit_depth)
            return _duck(mix, duck) if duck is not None else mix
        mix = self.mix(loud, peak, bit_depth=style.bit_depth)
        if source == "narration":
            lang = self.spec.language
            for cue in narration_cues(Path(narration), self.root):  # type: ignore[arg-type]
                self.cv.assets.add_audio(id=f"vo-{cue.id}", src=cue.audio, sha256=cue.sha256, language=lang)
                self.add_track(f"vo-track-{cue.id}", f"vo-{cue.id}", start=cue.start, role="dialogue", language=lang)
            return mix
        for t in self.takes:
            self.take_audio(t, **(take(t) if take else {}))
        for asset_id, src, track_kw in extra:
            self.cv.assets.add_audio(id=asset_id, src=src, sha256=sha256(self.root / src))
            self.add_track(f"track-{asset_id}", asset_id, **track_kw)
        return _duck(mix, duck) if duck is not None else mix

    @_audio_transaction
    def markers(self, specs=None, name="marker-{name}", extra: Sequence[tuple[str, float, str]] = ()):
        markers = self.scene.add_markers()
        for start, end, text, nm in specs if specs is not None else self.caption_specs:
            markers.add_marker(id=name.format(name=nm), time=start, duration=end - start, label=text.replace("\n", " "))
        for mid, time, label in extra:
            markers.add_marker(id=mid, time=time, label=label)
        return markers

    # -- finish -----------------------------------------------------------------------------------------
    def check(self):
        if importlib.util.find_spec("lxml") is not None:  # the XSD and Schematron checks need it
            return self.scene.check(schema=True)
        return self.scene.check()

    def check_overlays(self, document: Path, roots: Sequence[str], engine: Path | None = None) -> list[Crossing]:
        """Hold the overlay groups ``roots`` of the finished ``document`` inside the safe area: the engine does not
        measure vector graphics, so any crossing raises :class:`~srstudio.layout.LayoutError` (see
        :func:`~srstudio.layout.check_overlays`); the engine is found by :func:`~srstudio.layout.find_engine`."""
        return check_overlays(document, roots, engine=find_engine(engine), strict=True)

    def instagram(self, post: InstagramPost) -> Path:
        """Validate the Instagram caption of this episode and write it as ``<root>/ig.txt``."""
        return post.write(self.root)

    def hide_on_cover(self, *nodes) -> None:
        """Hide ``nodes`` (the burned-in text: a hook card, the captions) in the scene's ``cover`` variant, which
        :func:`srstudio.social.take_still` draws a cover's backdrop in, so the designed headline is not laid over a
        cut card or a ghost caption. Written by :meth:`finish`."""
        if not nodes:
            raise EpisodeError("hide_on_cover needs at least one node")
        for node in nodes:
            if node.id in [target for target, _, _ in self._cover_hidden]:
                raise EpisodeError(f"{node.id} is already hidden on the cover")
            if node.xml_name == "captionTrack":  # a caption track has no visibility: on the cover it goes to a sidecar
                self._cover_hidden.append((node.id, "mode", "sidecar"))
                outline = f"{node.id}-outline"  # a split outline is in the picture, so it hides as a node does
                if any(getattr(g, "id", None) == outline for g in self.cv.comp.find_all("group")):
                    self._cover_hidden.append((outline, "visible", "false"))
            else:
                self._cover_hidden.append((node.id, "visible", "false"))

    def finish(self, out: Path | None = None, report: Path | None = None, strict: bool = True) -> Path:
        """Check, write ``<slug>.scene.xml`` (and the findings report) and return the XML path; a check that finds an
        error (with ``strict``, any finding) is a :class:`SceneCheckError` and writes no scene."""
        out = Path(out) if out else self.root / f"{self.spec.slug}.scene.xml"
        report = Path(report) if report else out.with_name("sdk-validation.json")
        if out.resolve() == report.resolve() or (out.exists() and report.exists() and out.samefile(report)):
            raise EpisodeArgumentError("scene output and validation report must be different files")
        if len(self._cover_hidden) > self._cover_written:
            from .social import COVER_VARIANT

            if self._cover_variant is None:
                self._cover_variant = self.scene.add_parameters().add_variant(
                    id=COVER_VARIANT, label="cover backdrop, no burned text"
                )
            for target, prop, value in self._cover_hidden[self._cover_written :]:
                self._cover_variant.add_override(target=target, property=prop, value=value)
            self._cover_written = len(self._cover_hidden)
        findings = self.check()
        report.parent.mkdir(parents=True, exist_ok=True)
        report_rows = [{"severity": f.severity, "code": f.code, "message": str(f)} for f in findings]
        errors = [f for f in findings if f.severity == "error"]
        if errors or (strict and findings):
            report.write_text(json.dumps(report_rows, indent=2) + "\n")
            raise SceneCheckError(findings)
        document = _document_at(self.scene, self.root, out.parent)
        if self.cv.signature is not None and (absent := signature.missing(document)):
            error = signature.SignatureError(
                f"{self.spec.slug} is signed but its document has no {', '.join(absent)}: every location must draw "
                "both marks (ADR 0001), or the episode passes signature=False because its package predates them"
            )
            report_rows.append({"severity": "error", "code": "srstudio:signature", "message": str(error)})
            report.write_text(json.dumps(report_rows, indent=2) + "\n")
            raise error
        report.write_text(json.dumps(report_rows, indent=2) + "\n")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(document)
        print(
            f"{out.name}: {document.count(b'<shape ')} shapes, {document.count(b'<group ')} groups, "
            f"{len(self.caption_specs)} captions, {len(findings)} findings"
        )
        return out


def _duck(mix: AudioMix, amount: float) -> AudioMix:
    """Every ``music`` track of ``mix`` ducked ``amount`` dB under all its ``dialogue`` tracks."""
    tracks = [cast(AudioTrack, t) for t in mix.find_all("audioTrack")]
    spoken = [t.id for t in tracks if t.role == "dialogue" and t.id]
    music = [t for t in tracks if t.role == "music"]
    if not music:
        raise EpisodeError("duck: the mix has no music track to lower")
    if not spoken:
        raise EpisodeError("duck: the mix has no spoken track to duck under")
    for track in music:
        track.duckUnder = spoken
        track.duckAmount = amount
    return mix
