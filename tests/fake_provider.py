"""The real ``srstudio.provider`` behind fake ElevenLabs transports, for the engine integration tests.

The engine runs it as ``SR_PROVIDER_SRSTUDIO_ELEVENLABS``. ``FAKE_MP3`` is the audio every request
returns, ``FAKE_HEARD`` what the recogniser hears (default: the line spoken), and each run appends
one line per paid call to ``FAKE_LOG``.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fakes import FakeElevenLabs  # noqa: E402
from srstudio import provider  # noqa: E402

mp3 = Path(os.environ["FAKE_MP3"]).read_bytes()
fake = FakeElevenLabs(mp3, effect_mp3=mp3, heard=os.environ.get("FAKE_HEARD"))
answer, code = provider.run(sys.stdin.read(), os.environ, provider.client_factory(**fake.transports()))
with open(os.environ["FAKE_LOG"], "a") as log:
    for kind, _ in fake.calls:
        log.write(kind + "\n")
print(json.dumps(answer))
sys.exit(code)
