"""What test_collage_group.py shares with other test modules."""

from srstudio.collage_group import Place

PLACES = {"rosa": Place(540.0, 1920.0, 0.5), "gary": Place(290.0, 1860.0, 0.55), "kai": Place(800.0, 1880.0, 0.5)}


REACTIONS = {
    "rosa": ({"start": 0.0, "eyes": "half", "mouth": "flat", "arms": "hold"},),
    "gary": ({"start": 0.0, "eyes": "open", "mouth": "grin", "arms": "point"},),
    "kai": (
        {"start": 0.0, "eyes": "side", "mouth": "flat", "arms": "down"},
        {"start": 2.5, "eyes": "wide", "mouth": "o", "arms": "face"},
    ),
}
