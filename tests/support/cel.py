"""What test_cel.py shares with other test modules."""

import json
from pathlib import Path

D = 1.5


CAM = [
    {"time": 0.0, "bbox": [240.0, 912.0, 407.0, 1047.0], "scale": 1.0, "tx": 0.0, "ty": 0.0},
    {"time": 0.5, "bbox": [240.0, 912.0, 407.0, 1047.0], "scale": 1.1, "tx": -20.0, "ty": -30.0},
    {"time": 1.0, "bbox": [240.0, 912.0, 407.0, 1047.0], "scale": 1.25, "tx": -40.123456, "ty": -60.0},
]


ROOM = [
    {"time": 0.0, "scale": 1.0, "tx": 0.0, "ty": 0.0},
    {"time": 0.5, "scale": 1.05, "tx": -10.0, "ty": -15.0},
    {"time": 1.0, "scale": 1.1, "tx": -20.0, "ty": -30.0},
]


RUNS = {
    "poses": [{"name": "a", "time": 0, "feature": [1.0, 2.0, 0.1], "raised": True}],
    "runs": [{"name": "a", "start": 0.0, "end": 0.5}, {"name": "b", "start": 0.5, "end": D}],
    "features": [[1.0, 2.0, 0.1]],
}


POSE_A = [{"fill": "#240102", "path": "M 0 0 L 10 0 L 10 10 Z"}, {"fill": "#c73a2f", "path": "M 2 2 L 8 2 L 8 8 Z"}]


POSE_B = [{"fill": "#240102", "path": "M 0 0 L 12 0 L 12 12 Z"}]


CAPTIONS = [
    {
        "id": "c1",
        "start": 0.0833,
        "end": 0.75,
        "text": "Hello there...",
        "phase": "opening",
        "sample_time": 0.4,
        "boxes": [{"x": 100, "y": 200, "w": 300, "h": 60, "fill": "#2b87ab", "glyphs": "M 1 1 L 2 2 Z"}],
    },
    {
        "id": "c2",
        "start": 0.8,
        "end": D,
        "text": "Second line.",
        "caption": "Second\nline",
        "phase": "test",
        "sample_time": 1.0,
        "boxes": [
            {"x": 100, "y": 200, "w": 300, "h": 60, "fill": "#2b87ab", "glyphs": "M 1 1 L 2 2 Z"},
            {"x": 100, "y": 270, "w": 200, "h": 60, "glyphs": "M 3 3 L 4 4 Z"},
        ],
    },
]


def silent_project(root: Path) -> Path:
    assets = root / "assets"
    assets.mkdir(exist_ok=True)
    (root / "script.json").write_text(json.dumps(CAPTIONS))
    (assets / "camera.json").write_text(json.dumps(CAM))
    (assets / "room-camera.json").write_text(json.dumps(ROOM))
    (assets / "poses.json").write_text(json.dumps(RUNS))
    (assets / "a.json").write_text(json.dumps(POSE_A))
    (assets / "b.json").write_text(json.dumps(POSE_B))
    return root


BOX = (40.0, 40.0, 60.0, 60.0)
