"""The plates of the Pedro drives, Pedro flies piece: his figure turned from the lens, at each look the piece needs."""

from srstudio.pedro import Face

# name -> (face, degrees from the lens, dress, glasses). -90 is his profile with the nose to the left.
PLATES = {
    "car-calm": (Face(), -90.0, "blazer", False),
    "car-blink": (Face(lid="shut"), -90.0, "blazer", False),
    "car-up": (Face(mood="raised-brow", nod=-3.0), -90.0, "blazer", False),
    "car-brow": (Face(mood="raised-brow"), -90.0, "blazer", False),
    "car-turn": (Face(mood="raised-brow"), -60.0, "blazer", False),
    "car-lens": (Face(mood="smile"), -35.0, "blazer", False),
    "jet-calm": (Face(), -90.0, "puffer", True),
    "jet-smile": (Face(mood="smile"), -90.0, "puffer", True),
    "jet-blink": (Face(mood="smile", lid="shut"), -90.0, "puffer", True),
    "jet-turn": (Face(mood="smile"), -60.0, "puffer", True),
    "jet-lens": (Face(mood="smile"), -35.0, "puffer", True),
}
