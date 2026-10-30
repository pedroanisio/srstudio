"""The Slack avatar of creationbot is one square frame Slack accepts."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("creationbot_avatar", ROOT / "tools" / "creationbot_avatar.py")
assert spec is not None and spec.loader is not None
avatar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(avatar)


def test_the_frame_is_a_square_slack_accepts():
    assert 512 <= avatar.SIZE <= 2000
    project = avatar.compose().find("project")
    size = project.attributes()
    assert int(size["width"]) == int(size["height"]) == avatar.SIZE


def test_the_document_is_valid_and_builds_the_same_every_time():
    scene = avatar.compose()
    scene.check()
    assert scene.to_bytes() == avatar.compose().to_bytes()


def test_the_bot_is_the_studio_cactus_with_a_lit_visor():
    document = avatar.compose().to_bytes().decode()
    assert avatar.EYE in document and avatar.VISOR in document and avatar.FLOWER in document
    assert "<text" not in document  # lettering would not survive the 36 px a chat row shows
