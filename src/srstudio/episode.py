"""An episode: project, assets, timeline, soundtrack, cast, captions, mix, check and write."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from sr_core.scene import AudioMix, Scene

from .canvas import Canvas, Palette, Signature
from .generated import PlacedClip, load_clips, verify
from .graphics import captions as _captions
from .layout import SafeArea
from .narration import narration_cues
from .rig import Actor, Performance
from .social import InstagramPost
from .soundtrack import MouthStyle, PhonemeStyle, Soundtrack, mouth_states
from .styles import CUTOUT, Style
from .timeline import Timeline


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class _FromStyle:
    """Default of the ``EpisodeSpec`` fields a :class:`~srstudio.styles.Style` decides unless the episode sets them."""

    def __repr__(self) -> str:
        return "FROM_STYLE"


FROM_STYLE: Any = _FromStyle()


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
            self.namer = st.namer() if st.namer else None
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
        output = self.scene.add_output(id="main", path=spec.output or f"renders/{spec.slug}.mp4", **output_kw)
        if spec.poster:
            output.add_poster(**spec.poster)
        self.cv = Canvas(
            self.scene,
            cast(Palette, spec.palette),  # resolved by EpisodeSpec.__post_init__
            font_asset=spec.font_id,
            width=spec.width,
            height=spec.height,
            namer=spec.namer,
            local_time=spec.local_time,
            signature=Signature(spec.signature_code) if spec.signature else None,
        )
        self._mix: AudioMix | None = None
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
            raise FileNotFoundError(f"caption font {font_file} is missing{hint}")
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
    def comp(self):
        return self.cv.comp

    @property
    def phrases(self):
        return self.t.phrases

    def P(self, i: int):
        return self.t.phrases[i]

    @property
    def takes(self):
        return self.t.takes

    # -- shot sequences -------------------------------------------------------------------------------
    def sequence(self, id: str = "shots"):
        """A ``<sequence>`` whose children play one after another; see :meth:`shot`."""
        return self.comp.add_sequence(id=id)

    def shot(self, sequence, take, id: str | None = None, **kw):
        """One take's group in a sequence, as long as the take; animations inside run on its clock."""
        return sequence.add_group(id=id or f"shot-{take.id}", end=take.duration, **kw)

    # -- camera setups --------------------------------------------------------------------------
    def setup(self, builder, shots: Sequence[tuple[float, float]], **slots):
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
    ):
        model = style or self.spec.mouth_style
        if model is None:
            raise TypeError(f"the {self.spec.style.name} style is silent and has no mouth model; pass style= for one")
        if self.track is None:
            raise ValueError("this episode has no soundtrack; amplitude mouths need EpisodeSpec.audio")
        if not isinstance(model, MouthStyle):
            raise TypeError(
                f"amplitude mouths need a MouthStyle; the {self.spec.style.name} style speaks from character "
                "timestamps (srstudio.soundtrack.phoneme_states), so pass style= explicitly"
            )
        return mouth_states(self.track, self.t, role, self.spec.fps, smile=smile, style=model, speaking=speaking)

    def perform(self, actor: Actor, parent, x, y, scale, *, mouth=None, smile=(), blinks=(), nods=(), **extras):
        """Build ``actor`` with a performance assembled from keyword arguments."""
        states = mouth if mouth is not None else self.mouth(actor.role, smile=smile)
        perf = Performance(mouth=states, blinks=list(blinks), nods=list(nods), extras=extras)
        node = actor.build(parent, x, y, scale, perf)
        self.cast[actor.tag] = actor
        return node

    # -- captions, mix, markers -----------------------------------------------------------------------
    def captions(self, specs: Sequence[tuple[float, float, str, str]] | None = None, **style):
        """Caption layers for ``specs`` (default: one per phrase, ending on the next cut)."""
        specs = list(specs) if specs is not None else self.default_captions()
        self.caption_specs.extend(specs)
        return _captions(self.cv, specs, **style)

    def default_captions(self, lead: float = 0.06, name="dialogue-{n}"):
        out = []
        for i, p in enumerate(self.phrases):
            end = self.t.cuts[i + 1].time if i + 1 < len(self.t.cuts) and i < len(self.phrases) - 1 else self.t.reaction
            out.append((p.start - lead, end, p.caption, name.format(n=i + 1)))
        return out

    def mix(
        self,
        loudness="-16",
        true_peak="-1.5",
        bit_depth: str | None = "24",
        sample_rate=48000,
        channels=2,
        master_first: bool = True,
    ):
        """The ``<audioMix>`` with its master, created once; tracks are added with :meth:`add_track`.

        ``master_first=False`` leaves the master to :meth:`master`, after the tracks (the interview family)."""
        if self._mix is None:
            kw = dict(sampleRate=sample_rate, channels=channels)
            if bit_depth:
                kw["bitDepth"] = bit_depth
            self._mix = self.scene.add_audioMix(**kw)
            self._master_kw = dict(normalize="integrated", loudness=loudness, truePeak=true_peak, limiter=True)
            if master_first:
                self.master()
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
            raise ValueError("generated_audio needs at least one clip")
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

    def audio(
        self,
        *,
        narration: Path | None = None,
        extra: Sequence[tuple[str, str, dict]] = (),
        take: Callable[[Any], dict] | None = None,
        track_id: str | None = None,
        loudness: str | None = None,
        true_peak: str | None = None,
    ) -> AudioMix | None:
        """The mix of whatever the project plays (:attr:`audio_source`), mastered as the style says (``Style.mix``)
        unless ``loudness``/``true_peak`` are given. Returns ``None`` for a silent episode.

        * ``narration``: a verified ``narration.json`` (:func:`srstudio.narration.narration_cues`), one
          ``vo-NN`` asset and ``vo-track-NN`` track per cue; used when given, whatever else the project holds.
        * clips: :meth:`generated_audio`; ``extra`` adds plain files as ``(asset id, path, track attributes)``.
        * takes: :meth:`take_audio` for every take, with ``take(take)`` as its track attributes, then ``extra``.
        * mixed: :meth:`audio_mix` on ``track_id``.

        An option the source does not take is a ``TypeError``, so a misplaced argument is never ignored."""
        source = "narration" if narration is not None else self.audio_source
        allowed = {
            "narration": set(),
            "clips": {"extra"},
            "takes": {"extra", "take"},
            "mixed": {"track_id"},
            "silent": set(),
        }[source]
        given = {name for name, value in (("extra", extra), ("take", take), ("track_id", track_id)) if value}
        if given - allowed:
            raise TypeError(f"a {source} project takes no {', '.join(f'{k}=' for k in sorted(given - allowed))}")
        style = self.spec.style.mix
        loud, peak = loudness or style.loudness, true_peak or style.true_peak
        if source == "silent":
            return None
        if source == "mixed":
            return self.audio_mix(track_id or "synthetic-dialogue", loud, peak, bit_depth=style.bit_depth)
        if source == "clips":
            return self.generated_audio(loudness=loud, true_peak=peak, extra=extra, bit_depth=style.bit_depth)
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
        return mix

    def markers(self, specs=None, name="marker-{name}", extra: Sequence[tuple[str, float, str]] = ()):
        markers = self.scene.add_markers()
        for start, end, text, nm in specs if specs is not None else self.caption_specs:
            markers.add_marker(id=name.format(name=nm), time=start, duration=end - start, label=text.replace("\n", " "))
        for mid, time, label in extra:
            markers.add_marker(id=mid, time=time, label=label)
        return markers

    # -- finish -----------------------------------------------------------------------------------------
    def check(self):
        try:
            import lxml  # noqa: F401

            return self.scene.check(schema=True)
        except ImportError:
            return self.scene.check()

    def instagram(self, post: InstagramPost) -> Path:
        """Validate the Instagram caption of this episode and write it as ``<root>/ig.txt``."""
        return post.write(self.root)

    def finish(self, out: Path | None = None, report: Path | None = None, strict: bool = True) -> Path:
        """Check, write ``<slug>.scene.xml`` (and the findings report) and return the XML path."""
        findings = self.check()
        out = Path(out) if out else self.root / f"{self.spec.slug}.scene.xml"
        report = Path(report) if report else out.with_name("sdk-validation.json")
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(
            json.dumps([{"severity": f.severity, "code": f.code, "message": str(f)} for f in findings], indent=2) + "\n"
        )
        errors = [f for f in findings if f.severity == "error"]
        if errors or (strict and findings):
            raise SystemExit("\n".join(str(f) for f in findings))
        document = self.scene.to_bytes(layout="pretty")
        out.write_bytes(document)
        print(
            f"{out.name}: {document.count(b'<shape ')} shapes, {document.count(b'<group ')} groups, "
            f"{len(self.caption_specs)} captions, {len(findings)} findings"
        )
        return out
