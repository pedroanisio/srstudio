"""The cast: two office rigs, two café rigs and a pigeon.

Each actor reads its gestures from ``Performance.extras``; the keys are documented on the
class. Register a new character with ``@register("character", "name")`` on an ``Actor``
subclass or on a plain ``fn(cv, parent, ...)``.
"""

from __future__ import annotations

from . import _character_contracts as cc
from . import checks
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register
from .rig import Actor, Performance


class CastError(SrstudioError, ValueError):
    """An actor was asked for a pose it does not draw."""


def _pairs(value: object, name: str, *, spans: bool = False) -> None:
    if not isinstance(value, (list, tuple)):
        raise CastError(f"{name}: expected a sequence of pairs")
    for pair in value:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise CastError(f"{name}: expected pairs of finite numbers")
        if not (checks.number(pair[0]) and checks.number(pair[1]) and pair[0] >= 0):
            raise CastError(f"{name}: expected a non-negative time and a finite value")
        if spans and pair[1] < pair[0]:
            raise CastError(f"{name}: span end must be at or after start")


def _options(perf: Performance, allowed: frozenset[str]) -> None:
    unknown = set(perf.extras) - allowed
    if unknown:
        raise CastError(
            f"unknown performance option(s) {', '.join(sorted(unknown))}; known: {', '.join(sorted(allowed))}"
        )
    for name in ("forearm", "pupils"):
        if name in perf.extras and perf.extras[name] is not None:
            _pairs(perf.extras[name], name)
    if "brows" in perf.extras and perf.extras["brows"] is not None:
        brows = perf.extras["brows"]
        if not isinstance(brows, (list, tuple)) or len(brows) != 2:
            raise CastError("brows: expected left and right key sequences")
        for side in brows:
            _pairs(side, "brows")
    if "pointing" in perf.extras and perf.extras["pointing"] is not None:
        _pairs(perf.extras["pointing"], "pointing", spans=True)
    if "facepalm" in perf.extras and perf.extras["facepalm"] is not None:
        _pairs([perf.extras["facepalm"]], "facepalm", spans=True)
    if "held_cup" in perf.extras and perf.extras["held_cup"] is not None:
        _pairs(perf.extras["held_cup"], "held_cup", spans=True)
    if "hide_right_arm_at" in perf.extras and perf.extras["hide_right_arm_at"] is not None:
        checks.non_negative(
            perf.extras["hide_right_arm_at"], CastError, "hide_right_arm_at: expected a finite time >= 0"
        )
    if "skin" in perf.extras and (not isinstance(perf.extras["skin"], str) or not perf.extras["skin"]):
        raise CastError("skin: expected a nonempty colour string")
    if "name" in perf.extras and perf.extras["name"] is not None and not isinstance(perf.extras["name"], str):
        raise CastError("name: expected badge text or None")


SIDES = ("left", "right")  # the screen sides an arm can be left off


def _free_sides(perf: Performance) -> tuple[str, ...]:
    """The screen sides a reel draws its own arm on, refused unless they are sides."""
    free = perf.extras.get("free_arms", ())
    if isinstance(free, str) or not set(free) <= set(SIDES):
        raise CastError(f"free_arms names screen sides, {' and '.join(SIDES)}; got {free!r}")
    return tuple(free)


class OfficeActor(Actor):
    """Shared body of the interview series: white shirt, dark tie, head radius 100.

    extras: ``arms`` = ``"static"`` (one stroke for both arms) or ``"articulated"`` (a
    right-arm group with a forearm that can rotate at the elbow); ``legs`` = ``"seated"`` draws
    trousers and shoes below the torso, for a bench, and ``"standing"`` trousers straight down to the shoes,
    :data:`STANDING_LEGS` below the torso (default: none, the desk hides them); ``tie`` = ``"loose"`` pulls the knot
    down, off centre, under an open collar: a character who has stopped trying (default: the tie as drawn);
    ``free_arms`` = screen sides (``left``, ``right``) drawn with no arm, for a reel to reach with
    (:mod:`srstudio.cutout_reach`).
    """

    bottom = 312
    supports_limbs = True
    eye_xs = (-37, 31)
    LEGS = ("seated", "standing")
    STANDING_LEGS = 336  # from the torso's bottom to the soles, standing
    TIES = ("loose",)
    extra_options = frozenset({"arms", "legs", "tie", "free_arms"})

    def validate_performance(self, perf: Performance) -> None:
        _options(perf, self.extra_options)
        if perf.extras.get("arms", "static") not in ("static", "articulated"):
            raise CastError("arms: expected 'static' or 'articulated'")
        tie = perf.extras.get("tie")
        if tie is not None and tie not in self.TIES:
            raise CastError(f"unknown tie {tie!r}; known: {', '.join(self.TIES)}")
        legs = perf.extras.get("legs")
        if legs is not None and legs not in self.LEGS:
            raise CastError(f"unknown legs pose {legs!r}; known: {', '.join(self.LEGS)}")
        if _free_sides(perf) and perf.extras.get("arms", "static") == "articulated":
            raise CastError("free_arms: an articulated arm cannot be left out")

    def draw_body(self, g, perf: Performance):
        cv, ink, white, clear = self.cv, self.cv.ink, self.cv.white, self.cv.clear
        bottom = self.bottom
        legs = perf.extras.get("legs")
        if legs is not None:
            if legs not in self.LEGS:
                raise CastError(f"unknown legs pose {legs!r}; known: {', '.join(self.LEGS)}")
            legs_group = cv.group(g, f"{self.tag_base}-legs")
            if legs == "standing":
                self.draw_standing_legs(legs_group)
            else:
                self.draw_seated_legs(legs_group)
        cv.rect(g, -10, 92, 20, 34, white, ink, 4)
        cv.path(
            g, f"M-64 {bottom} L-68 154 Q-69 124 -39 120 Q-4 113 38 120 Q68 126 68 154 L64 {bottom}Z", white, ink, 4.5
        )
        replaced = self.replaced_arms(perf) | frozenset(_free_sides(perf))  # legacy arm names, by screen side
        if perf.limbs or replaced:
            if "left" not in replaced:
                cv.path(g, f"M-66 148 L-87 235 L-79 {bottom}", stroke=ink, sw=5)
            if "right" not in replaced:
                cv.path(g, f"M67 148 L86 233 L77 {bottom}", stroke=ink, sw=5)
        elif perf.extras.get("arms", "static") == "articulated":
            cv.path(g, f"M-66 148 L-87 235 L-79 {bottom}", stroke=ink, sw=5)
            self.right_arm = cv.group(g, f"{self.tag_base}-right-arm")
            cv.path(self.right_arm, "M67 148 L86 233", stroke=ink, sw=5)
            self.forearm = cv.group(self.right_arm, f"{self.tag_base}-forearm", x=86, y=233)
            cv.path(self.forearm, f"M0 0 L-9 {bottom - 233}", stroke=ink, sw=5)
            self.draw_arm_gestures(perf)
        else:
            cv.path(g, f"M-66 148 L-87 235 L-79 {bottom} M67 148 L86 233 L77 {bottom}", stroke=ink, sw=5)
        if perf.extras.get("tie") == "loose":
            cv.path(g, "M-30 122 L0 160 L30 122", stroke=ink, sw=3.5)  # the collar, open
            cv.path(g, "M-4 166 L20 170 L16 196 L-8 192Z", ink, clear, 0)  # the knot, down and off centre
            cv.path(g, "M-6 196 L14 200 L9 300 L-6 312 L-16 296Z", ink, clear, 0)
        else:
            cv.path(g, "M-11 120 L11 120 L8 146 L-8 146Z", ink, clear, 0)
            cv.path(g, "M-8 149 L8 149 L13 268 L0 292 L-13 268Z", ink, clear, 0)

    def draw_seated_legs(self, legs):
        """Knees towards the camera, shins down to the path, as the seated café actors sit."""
        cv, ink, b = self.cv, self.cv.ink, self.bottom
        cv.path(legs, f"M-55 {b - 10} L-78 {b + 35} L-80 {b + 192} L-37 {b + 192} L-38 {b + 57} L-7 {b + 10}Z",
                "#3F4652", ink, 4)  # fmt: skip
        cv.path(legs, f"M55 {b - 10} L82 {b + 36} L88 {b + 192} L45 {b + 192} L40 {b + 57} L7 {b + 10}Z",
                "#3F4652", ink, 4)  # fmt: skip
        cv.path(legs, f"M-86 {b + 187} Q-50 {b + 182} -32 {b + 198} L-24 {b + 214} L-96 {b + 214}Z", ink, ink, 3)
        cv.path(legs, f"M40 {b + 187} Q76 {b + 182} 96 {b + 198} L102 {b + 214} L32 {b + 214}Z", ink, ink, 3)

    def draw_standing_legs(self, legs):
        """Trouser legs straight down from the torso to shoes turned out a little, :data:`STANDING_LEGS` long."""
        cv, ink, b, s = self.cv, self.cv.ink, self.bottom, self.STANDING_LEGS
        cv.path(legs, f"M-62 {b - 10} L-66 {b + s - 22} L-14 {b + s - 22} L-6 {b + 20} L6 {b + 20} L14 {b + s - 22} "
                      f"L66 {b + s - 22} L62 {b - 10}Z", "#3F4652", ink, 4)  # fmt: skip
        cv.path(legs, f"M0 {b + 30} L0 {b + s - 30}", stroke="#2C323B", sw=3)  # the seam between the legs
        cv.path(legs, f"M-70 {b + s - 26} Q-30 {b + s - 30} -10 {b + s - 14} L-8 {b + s} L-84 {b + s}Z", ink, ink, 3)
        cv.path(legs, f"M10 {b + s - 26} Q46 {b + s - 30} 72 {b + s - 14} L84 {b + s} L8 {b + s}Z", ink, ink, 3)

    def draw_arm_gestures(self, perf: Performance):
        """Hook for the articulated arm; see the subclasses."""

    def draw_head(self, head, perf: Performance):
        self.cv.ellipse(head, -100, -100, 200, 200, self.cv.white, self.cv.ink, 5.5)

    def draw_blink(self, closed, perf: Performance):
        for x in self.eye_xs:
            self.cv.path(closed, f"M{x - 12} -20 Q{x} -9 {x + 12} -20", stroke=self.cv.ink, sw=3.8)


@register(
    "character",
    "manager",
    summary="The interviewer: glasses-free, receding hairline, raised brows, facepalm",
    examples=(
        'from srstudio import get\n'
        'actor = get("character", "manager")(ep.cv)\n'
        'node = ep.perform(actor, ep.comp, 540, 800, 1.0, mouth=[(0, "rest")])',
    ),
    contract=cc.character(limbs=True, expressions=True),
)
class Manager(OfficeActor):
    """extras: ``brows`` = (left_keys, right_keys) rotation; ``pupils`` = y keys;
    ``hide_right_arm_at`` = time; ``facepalm`` = (start, end)."""

    role = "manager"
    extra_options = OfficeActor.extra_options | {"brows", "pupils", "hide_right_arm_at", "facepalm"}
    bottom = 312
    eye_xs = (-37, 31)

    def draw_arm_gestures(self, perf):
        t = perf.extras.get("hide_right_arm_at")
        if t is not None:
            self.cv.keys(self.right_arm, "opacity", [(0, 1), (t, 0)])

    def draw_head(self, head, perf):
        super().draw_head(head, perf)
        cv, ink, clear = self.cv, self.cv.ink, self.cv.clear
        cv.path(head, "M-94 -31 Q-77 -94 -19 -101 Q18 -109 45 -86 Q9 -98 -40 -72 Q-74 -58 -94 -31Z", ink, clear, 0)
        brows = perf.extras.get("brows")
        if brows:
            left = cv.path(head, "M-62 -43 Q-43 -53 -26 -46", stroke=ink, sw=4.7)
            right = cv.path(head, "M11 -46 Q30 -55 48 -44", stroke=ink, sw=4.7)
            cv.keys(left, "rotation", brows[0], hold=False)
            cv.keys(right, "rotation", brows[1], hold=False)
        else:
            cv.path(head, "M-62 -43 Q-43 -53 -26 -46 M11 -46 Q30 -55 48 -44", stroke=ink, sw=4.7)

    def draw_eyes(self, eyes, perf):
        cv, ink, white = self.cv, self.cv.ink, self.cv.white
        for x in self.eye_xs:
            cv.ellipse(eyes, x - 26, -45, 52, 55, white, ink, 3.7)
            pupil = cv.ellipse(eyes, x - 11, -31, 20, 26, ink)
            if perf.extras.get("pupils"):
                cv.keys(pupil, "y", perf.extras["pupils"], hold=False)
        cv.path(eyes, "M-11 -24 Q-2 -32 6 -24", stroke=ink, sw=3.3)

    def draw_blink(self, closed, perf):
        cv = self.cv
        for x in self.eye_xs:
            cv.ellipse(closed, x - 26, -45, 52, 55, cv.white, cv.ink, 3.7)
            cv.path(closed, f"M{x - 12} -20 Q{x} -9 {x + 12} -20", stroke=cv.ink, sw=3.8)

    def after_head(self, g, perf):
        span = perf.extras.get("facepalm")
        if not span:
            return
        start, end = span
        cv = self.cv
        palm = cv.group(g, f"{self.tag_base}-facepalm")
        palm.start = start
        palm.end = end
        cv.keys(palm, "opacity", [(0, 0), (start, 0), (start + 0.10, 1)], hold=False)
        cv.keys(palm, "y", [(0, 40), (start, 40), (start + 0.20, 0)], hold=False)
        cv.path(palm, "M67 148 Q112 171 117 110 Q110 42 51 -18", stroke=cv.ink, sw=5)
        cv.path(
            palm,
            "M39 0 Q33 -9 37 -26 L39 -43 Q40 -49 44 -46 L45 -28 L47 -48 Q50 -55 54 -48 L54 -29 L59 "
            "-45 Q64 -50 67 -43 L64 -24 Q73 -32 76 -25 Q78 -20 69 -9 L62 3 Q53 10 39 0Z",
            cv.white,
            cv.ink,
            2.5,
        )
        self.facepalm = palm


@register(
    "character",
    "candidate",
    summary="The applicant: quiff, dot eyes, a forearm that raises one finger",
    contract=cc.character(limbs=True, expressions=True),
)
class Candidate(OfficeActor):
    """extras: ``forearm`` = rotation keys at the elbow; ``pointing`` = spans the raised finger shows."""

    role = "candidate"
    extra_options = OfficeActor.extra_options | {"forearm", "pointing"}
    bottom = 330
    eye_xs = (-32, 37)

    def draw_arm_gestures(self, perf):
        cv = self.cv
        if perf.extras.get("forearm"):
            cv.keys(self.forearm, "rotation", perf.extras["forearm"], hold=False)
        if perf.extras.get("pointing"):
            pointing = cv.group(self.forearm, f"{self.tag_base}-pointing-hand")
            cv.gate(pointing, perf.extras["pointing"])
            cv.path(
                pointing,
                "M-18 91 Q-19 84 -13 83 Q-7 82 -5 89 L-3 100 L-4 121 Q-9 128 -14 122 L-14 106 Q-26 "
                "106 -27 99 Q-27 93 -18 91Z",
                cv.white,
                cv.ink,
                2.5,
            )
            self.pointing = pointing

    def draw_head(self, head, perf):
        super().draw_head(head, perf)
        cv, ink = self.cv, self.cv.ink
        cv.path(
            head,
            "M-50 -91 Q-25 -139 17 -121 Q35 -116 42 -109 Q7 -111 -37 -95 M-29 -91 Q3 -104 29 -103",
            stroke=ink,
            sw=3.7,
        )
        cv.path(head, "M-49 -47 Q-30 -57 -11 -48 M17 -48 Q37 -58 55 -47", stroke=ink, sw=4)

    def draw_eyes(self, eyes, perf):
        for x in self.eye_xs:
            self.cv.ellipse(eyes, x - 6, -26, 12, 15, self.cv.ink)


@register(
    "character",
    "rosa",
    summary="Rosa the neighbour: grey bob, round glasses, a cardigan with her name stitched on its pocket",
    contract=cc.character(limbs=True, expressions=True),
)
class Rosa(OfficeActor):
    """An office-family actor (white face, ink line, ``legs`` and ``arms`` as :class:`OfficeActor`) in a blouse and
    a terracotta cardigan. extras: ``stitch`` = the name stitched over her pocket, 1 to :data:`STITCH` characters
    (default ROSA); ``None`` stitches nothing and draws no text layer."""

    role = "rosa"
    extra_options = OfficeActor.extra_options | {"stitch"}
    bottom = 312
    eye_xs = (-34, 36)
    STITCH = 6
    CARDIGAN = "#B4574A"

    def validate_performance(self, perf: Performance) -> None:
        stitch = perf.extras.get("stitch", "ROSA")
        if stitch is not None and not (isinstance(stitch, str) and stitch.strip() and len(stitch) <= self.STITCH):
            raise CastError(f"the stitch is 1 to {self.STITCH} characters or None, got {stitch!r}")
        super().validate_performance(perf)

    def draw_body(self, g, perf):
        super().draw_body(g, perf)
        cv, ink, b = self.cv, self.cv.ink, self.bottom
        cv.path(g, "M-16 119 L16 119 L6 210 L-6 210Z", "#F4EEE2", ink, 3)  # the blouse, over the shirt's tie
        cv.path(g, f"M-64 {b} L-68 154 Q-69 124 -39 120 L-16 119 L-6 214 L-4 {b}Z", self.CARDIGAN, ink, 4)
        cv.path(g, f"M64 {b} L68 154 Q68 126 38 120 L16 119 L6 214 L4 {b}Z", self.CARDIGAN, ink, 4)
        cv.path(g, "M-58 160 Q-50 150 -40 146", stroke="#D98576", sw=4, opacity=0.8)  # the lit shoulder
        for yy in (236, 268, 300):
            cv.ellipse(g, -13, yy - 5, 10, 10, "#F1D9A8", ink, 1.5)
        cv.rect(g, 14, 238, 46, 40, "#9C4539", ink, 2.5, radius=5)  # the pocket
        stitch = perf.extras.get("stitch", "ROSA")
        if stitch is not None:
            cv.text(g, f"{self.tag_base}-stitch", stitch, 10, 214, 56, 22, 15, "#FBE7C6")

    def draw_head(self, head, perf):
        super().draw_head(head, perf)
        cv, ink = self.cv, self.cv.ink
        cv.path(head, "M-108 22 Q-124 -118 0 -118 Q124 -118 108 22 Q98 30 86 22 Q92 -54 34 -78 Q-30 -60 -88 -40 "
                      "Q-92 0 -86 22 Q-98 30 -108 22Z", "#C8CBD1", ink, 4.5)  # fmt: skip  # the bob and its fringe
        cv.path(head, "M-60 -98 Q-20 -112 30 -102", stroke="#E6E8EC", sw=5, opacity=0.8)
        cv.path(head, "M-50 -40 Q-34 -48 -18 -42 M22 -42 Q38 -49 54 -41", stroke=ink, sw=3.6)

    def draw_eyes(self, eyes, perf):
        cv, ink = self.cv, self.cv.ink
        for x in self.eye_xs:
            cv.ellipse(eyes, x - 6, -27, 12, 15, ink)
            cv.ellipse(eyes, x - 24, -40, 48, 44, cv.clear, ink, 3.2)  # round glasses
        cv.path(eyes, "M-10 -20 Q1 -27 12 -20", stroke=ink, sw=3)


# ---------------------------------------------------------------- café cast


class CafeActor(Actor):
    """The café family: skin tone, wardrobe, round blink arcs; tag ``role-cafe`` or ``role-park``.

    extras: ``skin`` colour override; ``free_arms`` = screen sides (``left``, ``right``) drawn with no arm, no hand and
    nothing held, for a reel to reach with (:mod:`srstudio.cutout_reach`). ``seated`` is a constructor argument.
    """

    mouth_stroke = 3.5
    supports_limbs = True
    skin = "#F1D0AA"
    extra_options = frozenset({"skin", "free_arms"})

    def validate_performance(self, perf: Performance) -> None:
        _options(perf, self.extra_options)
        _free_sides(perf)

    def arms_left_out(self, perf: Performance) -> frozenset[str]:
        """The screen sides this actor does not draw an arm on: a limb track's, or a reel's own."""
        return self.replaced_arms(perf) | frozenset(_free_sides(perf))

    def __init__(self, canvas: Canvas, role: str | None = None, tag: str | None = None, seated: bool = False):
        role = role or self.role
        super().__init__(canvas, role, tag or f"{role}-{'park' if seated else 'cafe'}")
        self.seated = seated

    @property
    def blink_id(self) -> str:
        return f"{self.tag_base}-blink"

    def draw_blink(self, closed, perf):
        for xx in (-38, 38):
            self.cv.path(closed, f"M{xx - 9} 5 q9 8 18 0", stroke=self.cv.ink, sw=3.5)

    def draw_mouths(self, head):
        cv, ink, clear = self.cv, self.cv.ink, self.cv.clear
        return {
            "rest": cv.path(head, "M-8 47 L9 47", stroke=ink, sw=3.5),
            "round": cv.ellipse(head, -6, 38, 12, 18, ink),
            "open": cv.path(head, "M-15 38 Q0 32 15 38 Q13 58 0 58 Q-13 56 -15 38Z", ink, clear, 0),
            "small": cv.ellipse(head, -11, 41, 22, 9, ink),
            "smile": cv.path(head, "M-21 37 Q0 61 24 35", stroke=ink, sw=3.5),
        }


@register(
    "character",
    "barista",
    summary="Ava the barista: bun, apron, name tag, hoop earrings",
    contract=cc.character(limbs=True, expressions=True),
)
class Barista(CafeActor):
    """extras: ``name`` on the badge (default AVA); ``legs`` = ``True`` draws her down to the soles, 489 under her
    origin as the customer stands, for a shot with no counter in front of her (default: the counter hides them)."""

    role = "barista"
    extra_options = CafeActor.extra_options | {"name", "legs"}
    skin = "#C28A65"

    def validate_performance(self, perf: Performance) -> None:
        super().validate_performance(perf)
        if not isinstance(perf.extras.get("legs", False), bool):
            raise CastError(f"legs is True or False, got {perf.extras['legs']!r}")

    def draw_body(self, g, perf):
        cv, ink = self.cv, self.cv.ink
        skin = perf.extras.get("skin", self.skin)
        if perf.extras.get("legs"):
            cv.path(g, "M-53 310 L-51 467 L-9 467 L4 344 L15 468 L57 468 L55 310Z", "#2F3A40", ink, 4)
            cv.path(g, "M-54 462 Q-21 457 -6 475 L-4 489 L-66 489Z", "#2A211C", ink, 4)
            cv.path(g, "M15 462 Q49 456 70 475 L72 489 L11 489Z", "#2A211C", ink, 4)
        cv.rect(g, -10, 91, 20, 39, skin, ink, 3)
        cv.path(g, "M-68 322 L-73 150 Q-74 121 -44 116 L43 116 Q74 121 75 150 L68 322Z", "#F5EAD4", ink, 4)
        cv.path(g, "M-43 119 L-54 327 L57 327 L43 119 L24 119 L22 154 L-23 154 L-25 119Z", "#366761", ink, 3)
        replaced = self.arms_left_out(perf)  # legacy arm names, by screen side
        if replaced or perf.limbs:
            if "left" not in replaced:
                cv.path(g, "M-66 140 L-104 212 L-119 229", stroke=ink, sw=5)
            if "right" not in replaced:
                cv.path(g, "M68 141 L101 205 L117 208", stroke=ink, sw=5)
        else:
            cv.path(g, "M-66 140 L-104 212 L-119 229 M68 141 L101 205 L117 208", stroke=ink, sw=5)
        if "left" not in replaced:
            cv.ellipse(g, -128, 217, 20, 23, skin, ink, 2.5)
        if "right" not in replaced:
            cv.ellipse(g, 108, 197, 21, 22, skin, ink, 2.5)
        cv.rect(g, -28, 237, 57, 45, "#2C5853", ink, 2, radius=8)
        name = perf.extras.get("name", "AVA")
        if name:  # None leaves the tag blank: no text layer for a close-up to push out of the safe area
            cv.text(g, f"{name.lower()}-name", name, -24, 173, 48, 23, 13, "#F3E3BE")

    def draw_head(self, head, perf):
        cv, ink, clear = self.cv, self.cv.ink, self.cv.clear
        skin = perf.extras.get("skin", self.skin)
        cv.path(head, "M-97 -64 Q-134 -12 -111 73 Q-76 123 0 109 Q78 120 112 71 Q133 -11 97 -64Z", "#51382F", ink, 4)
        cv.ellipse(head, -48, -151, 101, 96, "#51382F", ink, 4)
        for xx, yy in [(-38, -130), (-10, -145), (21, -137), (39, -112)]:
            cv.path(head, f"M{xx} {yy} q-13 7 0 17", stroke="#73503E", sw=3)
        cv.ellipse(head, -109, -6, 24, 34, skin, ink, 3)
        cv.ellipse(head, 86, -6, 24, 34, skin, ink, 3)
        cv.ellipse(head, -105, 21, 19, 22, clear, "#E1BD66", 4)
        cv.ellipse(head, 88, 21, 19, 22, clear, "#E1BD66", 4)
        cv.ellipse(head, -98, -99, 196, 204, skin, ink, 5)
        cv.path(
            head,
            "M-98 -26 Q-109 -105 -28 -111 Q51 -128 99 -35 Q68 -28 45 -66 Q4 -18 -52 -36 Q-71 -41 -98 -26Z",
            "#51382F",
            ink,
            4,
        )
        cv.line(head, 41, -85, 60, -70, "#E1BD66", 4)
        cv.path(head, "M-56 -38 Q-39 -48 -23 -39 M22 -39 Q41 -49 58 -38", stroke=ink, sw=3.5)

    def draw_eyes(self, eyes, perf):
        cv, ink = self.cv, self.cv.ink
        for xx in (-38, 38):
            cv.ellipse(eyes, xx - 7, -22, 14, 18, ink)
            cv.path(eyes, f"M{xx - 8} -20 l-6 -5 M{xx + 7} -20 l5 -5", stroke=ink, sw=2)


@register(
    "character",
    "customer",
    summary="Milo the customer: beanie, stubble, phone in hand, standing or seated",
    contract=cc.character(limbs=True, expressions=True),
)
class Customer(CafeActor):
    """extras: ``held_cup`` = spans the takeaway cup is in hand (standing only; seated always holds it)."""

    role = "customer"
    extra_options = CafeActor.extra_options | {"held_cup"}
    skin = "#F1D0AA"

    def draw_body(self, g, perf):
        from .props import coffee_cup

        cv, ink = self.cv, self.cv.ink
        skin = perf.extras.get("skin", self.skin)
        if self.seated:
            cv.path(g, "M-53 293 L-78 335 L-80 492 L-37 492 L-38 357 L-7 315Z", "#385063", ink, 4)
            cv.path(g, "M53 293 L100 336 L133 488 L89 494 L64 361 L8 315Z", "#385063", ink, 4)
            cv.path(g, "M-83 487 Q-46 482 -29 498 L-20 514 L-92 514Z", "#A7784D", ink, 4)
            cv.path(g, "M88 487 Q125 483 148 500 L155 513 L83 513Z", "#A7784D", ink, 4)
        else:
            cv.path(g, "M-53 326 L-51 467 L-9 467 L4 344 L15 468 L57 468 L55 327Z", "#385063", ink, 4)
            cv.path(g, "M-54 462 Q-21 457 -6 475 L-4 489 L-66 489Z", "#A7784D", ink, 4)
            cv.path(g, "M15 462 Q49 456 70 475 L72 489 L11 489Z", "#A7784D", ink, 4)
        cv.rect(g, -10, 91, 20, 39, skin, ink, 3)
        bottom = 300 if self.seated else 345
        cv.path(g, f"M-72 {bottom} L-76 145 Q-74 117 -46 113 L44 113 Q74 117 76 145 L71 {bottom}Z", "#527B90", ink, 4.5)
        cv.path(g, "M-62 111 Q-27 155 0 152 Q31 152 64 111 L78 137 Q39 186 0 173 Q-42 183 -78 138Z", "#3D6178", ink, 3)
        cv.line(g, -12, 145, -17, 195, "#E9E2CC", 2.5)
        cv.line(g, 14, 145, 18, 192, "#E9E2CC", 2.5)
        cv.rect(g, -43, 236, 86, 47, "#426C82", ink, 2.5, radius=12)
        replaced = self.arms_left_out(perf)  # legacy arm names, by screen side
        if replaced or perf.limbs:
            if "left" not in replaced:
                cv.path(g, "M-72 143 L-103 213 L-122 212", stroke=ink, sw=5)
            if "right" not in replaced:
                cv.path(g, "M73 144 L100 204 L125 181", stroke=ink, sw=5)
        else:
            cv.path(g, "M-72 143 L-103 213 L-122 212 M73 144 L100 204 L125 181", stroke=ink, sw=5)
        phone, held = None, None
        if "left" not in replaced:
            cv.ellipse(g, -131, 204, 20, 24, skin, ink, 2.5)
        if "right" not in replaced:
            cv.ellipse(g, 116, 171, 22, 25, skin, ink, 2.5)
        if "left" not in replaced:
            phone = cv.group(g, f"{self.tag}-phone", x=-133, y=179, rotation=-12)
            cv.rect(phone, 0, 0, 33, 58, "#293F49", ink, 2.5, radius=6)
            cv.rect(phone, 5, 7, 23, 41, "#B7D5CD", radius=2)
            cv.line(phone, 11, 52, 23, 52, "#A3B8B3", 1.5)
        if "right" not in replaced:
            held = coffee_cup(cv, g, 130, 163, 0.62, 8)
        if not self.seated and perf.extras.get("held_cup") is not None:
            cv.gate(held, perf.extras["held_cup"])
        self.phone, self.cup = phone, held

    def draw_head(self, head, perf):
        cv, ink = self.cv, self.cv.ink
        skin = perf.extras.get("skin", self.skin)
        cv.ellipse(head, -101, -101, 202, 207, skin, ink, 5.5)
        cv.path(head, "M-100 -48 Q-105 -139 0 -139 Q107 -140 102 -48Z", "#C99043", ink, 5)
        for xx in [-70, -45, -20, 5, 30, 55, 78]:
            cv.line(head, xx, -105, xx, -68, "#B37B35", 2.5)
        cv.rect(head, -102, -62, 204, 37, "#D9A34F", ink, 4, radius=9)
        cv.line(head, -88, -43, 88, -43, "#E9BE72", 3)
        cv.path(head, "M-58 -12 Q-40 -22 -23 -13 M23 -18 Q42 -36 60 -22", stroke=ink, sw=4)

    def draw_eyes(self, eyes, perf):
        for xx in (-38, 39):
            self.cv.ellipse(eyes, xx - 6, 1, 12, 17, self.cv.ink)

    def draw_face_front(self, head, perf):
        for xx, yy in [(-43, 65), (-29, 77), (-12, 83), (8, 84), (29, 77), (43, 65)]:
            self.cv.line(head, xx, yy, xx + 2, yy + 7, "#8F6B4D", 1.7, opacity=0.6)


@register(
    "character",
    "pigeon",
    summary="A park pigeon; mirrored with a negative scaleX, nods by rotation keys",
    contract=cc.character(
        limbs=False,
        expressions=False,
        parameters=(
            *cc.POSITION,
            (
                'nods',
                cc.P(
                    type=tuple[tuple[float, float], ...],
                    items=cc.P(prefix_items=(cc.seconds('canvas'), cc.P(unit='degrees'))),
                ),
            ),
            ('flip', cc.P(type=bool)),
            ('id', cc.P(type=str)),
        ),
    ),
)
def pigeon(cv: Canvas, parent, x=1000, y=1556, scale=0.83, flip=True, nods=(), id="pigeon"):
    ink = cv.ink
    bird = cv.group(parent, id, x=x, y=y, scaleX=-scale if flip else scale, scaleY=scale)
    if nods:
        cv.keys(bird, "rotation", nods, hold=False)
    cv.path(bird, "M0 -10 L-40 -32 L-28 4 L25 36Z", "#6B858D", ink, 3)
    cv.ellipse(bird, 0, -55, 105, 99, "#8DA3A7", ink, 3)
    cv.path(bird, "M15 -15 Q36 -64 80 -32 Q98 -8 66 26 Q44 35 15 -15Z", "#68878F", ink, 2)
    cv.ellipse(bird, 54, -99, 59, 61, "#789498", ink, 3)
    cv.path(bird, "M109 -73 L129 -64 L109 -57Z", "#D9A657", ink, 2)
    cv.ellipse(bird, 85, -83, 11, 12, "#FAF4D9", ink, 1.4)
    cv.ellipse(bird, 91, -80, 5, 6, ink)
    cv.line(bird, 39, 38, 36, 62, "#A87F47", 4)
    cv.line(bird, 76, 39, 81, 61, "#A87F47", 4)
    cv.path(bird, "M24 65 L38 60 L49 65 M69 65 L81 60 L96 65", stroke="#A87F47", sw=3)
    return bird
