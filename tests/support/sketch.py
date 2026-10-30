"""What test_sketch.py shares with other test modules."""

from dataclasses import replace

from srstudio.sketch import Beat, Line, Sketch, Speaker
from srstudio.voice import Voice, VoiceSettings

SET = VoiceSettings(0.5, 0.75, 0.3)


SPEAKERS = (
    Speaker("rex", Voice("rex", "IKne3meq5aSn8XLyUdCD", "Charlie"), SET, "dog"),
    Speaker("boss", Voice("boss", "JBFqnCBsd6RMkjVDRZzb", "George"), SET),
)


LINES = (
    Line("rex", "The report is due at nine."),
    Line("boss", "How is it going?"),
    Line("rex", "Great. Almost done."),
)


BEATS = (
    Beat(0.0, "dog", "Due at 9", "wide", "open", "desk", 0, 0),
    Beat(1.5, "dog", "Due at 9", "half", "flat", "type"),
    Beat(3.0, "dog", "How is it going?", "shock", "o", "desk", 1, 0, "buzz"),
    Beat(4.5, "dog", "Great", "half", "grin", "desk", 2, 0),
    Beat(5.5, "dog", "Almost done", "half", "grin", "crossed", 2, 1),
    Beat(7.0, "frog", "", "closed", "none", "face", event="clock:01:00"),
)


SK = Sketch("test-sketch", "Test sketch", SPEAKERS, LINES, BEATS, 9.0)


def with_beats(change):
    return replace(SK, beats=tuple(change(list(BEATS))))
