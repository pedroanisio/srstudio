"""A recorded timeline that keeps every prosody target, shared by test_prosody.py and test_prosody_gate.py."""


def item(id, actor, text, start, duration, first, last, words, stressed=(), direction=None, spread=3.5, hz=150.0):
    """A recorded take: ``words`` are (db, hz) per heard word over ``first``..``last``."""
    return {
        "id": id, "actor": actor, "text": text, "start": start, "duration": duration,
        "prosody": {"first": first, "last": last, "words_per_second": round(len(words) / (last - first), 3),
                    "median_hz": hz, "spread_st": spread,
                    "words": [{"text": f"w{k}", "db": db, "hz": f} for k, (db, f) in enumerate(words)],
                    "stressed": [dict(s) for s in stressed]},
    } | ({"direction": direction} if direction else {})  # fmt: skip


LANDED = {"word": "Discipline", "heard": True, "at": 0, "db": 8.0, "st": 4.98, "landed": True}


def timeline() -> dict:
    """A reel that keeps every target: a question answered after 0.5 s, a reply after 0.55 s (the median at a change
    of speaker 0.525 s), a punchline and button after 1.2 s and 0.6 s to the end. The answer and the punchline are
    key lines whose stressed word (named, or the loudest) stands out; the punchline's lift and weight are over the
    reel's other lines'."""
    return {
        "duration": 6.3,
        "items": [
            item("01", "dev", "Did you feed the dog?", 0.0, 1.6, 0.1, 1.3,
                 [(-20, 150), (-20, 150), (-19, 150), (-20, 150), (-19, 152)]),
            item("02", "ana", "Dog food.", 1.6, 1.3, 0.2, 1.0, [(-23, 150), (-16, 190)]),
            item("03", "dev", "Then what?", 2.9, 2.0, 0.25, 0.9, [(-20, 150), (-19.5, 151)]),
            item("04", "ana", "Discipline, mostly.", 4.9, 1.4, 0.1, 0.8, [(-12, 200), (-22, 150)], [LANDED],
                 {"punchline": "Discipline"}),
        ],
    }  # fmt: skip
