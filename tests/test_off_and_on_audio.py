"""The song of Off and On: Remy sings his refrain in the composed jingle, climbing from the machine to the lights
to himself; the spoken lines and the props' effects land where the jingle has no lyrics, and the cuts follow the
gags (the pipeline itself is tested in test_song.py and test_compose.py)."""

import sys
from pathlib import Path

import pytest

EPISODES = Path(__file__).resolve().parent.parent / "episodes"
WORDS_A_SECOND = 2.6  # a generous speaking rate: a line lasts at most its words at this rate, plus a breath


@pytest.fixture(scope="module")
def song():
    sys.path.insert(0, str(EPISODES))
    try:
        import off_and_on_audio
    finally:
        sys.path.pop(0)
    return off_and_on_audio


def lyric_free(plan):
    """The spans without lyrics, adjacent lyric-free chunks merged."""
    spans: list[list[float]] = []
    for c, (lo, hi) in zip(plan.chunks, plan.windows(), strict=True):
        if c.lines:
            continue
        if spans and spans[-1][1] == lo:
            spans[-1][1] = hi
        else:
            spans.append([lo, hi])
    return [tuple(s) for s in spans]


def spoken(song):
    """(start, generous end) of every spoken line."""
    out = []
    for line in song.SONG.lines:
        if line.at is not None:
            start = song.GROOVE.at(*line.at)
            out.append((start, start + 0.3 + len(line.text.split()) / WORDS_A_SECOND / line.speed))
    return out


def test_remy_sings_in_the_composition_and_everyone_else_speaks(song):
    s = song.SONG
    assert s.composition is not None and s.composition.role == "remy"
    assert all(s.sung(line) == (line.role == "remy") for line in s.lines)
    assert set(s.voices) == {line.role for line in s.lines} - {"remy"}


def test_the_refrains_climb_from_the_machine_to_the_lights_to_remy(song):
    sung = [line.text for line in song.SONG.lines if line.role == "remy"]
    assert sung == list(song.REFRAINS) == [text for text, _ in song.PLAN.sung()]
    for refrain, target in zip(song.REFRAINS, ("it", "lights", "me"), strict=True):
        assert target in [w.strip("!,.?").lower() for w in refrain.split()], refrain
    # The model folds refrains that sound alike into one hook (it sang "Turn it off" for "Turn him off" and
    # "Turn Pip off" on every seed tried), so no two refrains share a run of three words; a lone short name
    # ("Pip") came back as "then", "yeah", "flip" or "dip", so none is sung.
    assert not any("pip" in r.lower() for r in song.REFRAINS)
    runs = [{tuple(r.lower().split()[i : i + 3]) for i in range(len(r.split()) - 2)} for r in song.REFRAINS]
    assert not any(runs[i] & runs[j] for i in range(3) for j in range(i + 1, 3))


def test_every_chunk_is_whole_bars_on_the_episode_tempo(song):
    bar = 4 * 60 / song.GROOVE.bpm
    for chunk in song.PLAN.chunks:
        assert chunk.seconds % bar == 0, chunk.name
        assert f"{song.GROOVE.bpm:g} BPM" in chunk.styles, chunk.name
    assert song.SONG.lines_end == song.PLAN.seconds


def test_every_spoken_line_fits_inside_a_chunk_without_lyrics(song):
    free = lyric_free(song.PLAN)
    for a, b in spoken(song):
        assert any(lo <= a and b <= hi for lo, hi in free), (a, b)


def test_the_props_click_where_there_are_no_lyrics(song):
    free = lyric_free(song.PLAN)
    for fx in song.SONG.effects:
        if fx.id in ("machine-reset", "coffee-brew", "screen-dies"):
            start = song.GROOVE.at(*fx.at) - fx.early
            assert any(lo <= start and start + fx.longest <= hi for lo, hi in free), fx.id
            assert not any(a < start + fx.longest and start < b for a, b in spoken(song)), fx.id


def test_the_cuts_follow_the_gags(song):
    at = song.GROOVE.at
    cuts = {at(*when): angle for when, angle in song.CUTS}
    times = sorted(cuts)
    assert times[0] == 0 and len(times) == len(song.CUTS)

    def angle(t):
        return cuts[max(c for c in times if c <= t)]

    fx = {e.id: at(*e.at) for e in song.SONG.effects}
    assert angle(fx["machine-reset"]) == angle(fx["coffee-brew"]) == "break"
    assert angle(fx["lights-off"]) == "dark" and angle(fx["lights-on"]) == "break"
    assert angle(fx["screen-dies"]) == "meeting"
    windows = dict(zip((c.name for c in song.PLAN.chunks), song.PLAN.windows(), strict=True))
    for chunk in ("Fix It", "Fix Me"):  # Remy is on screen while he sings
        assert angle(windows[chunk][0]) == "meeting", chunk
    assert all(not a < c < b for c in times for a, b in spoken(song))  # no cut lands inside a spoken line
    assert set(song.extra({e.id: 0.0 for e in song.SONG.effects})) >= {"camera_cuts", "screen_dies_start"}
