"""What test_voice.py shares with other test modules."""


class Binary:
    def __init__(self, audio=b"", exc=None):
        self.audio, self.exc, self.calls = audio, exc, []

    def __call__(self, url, payload, headers):
        self.calls.append((url, payload, headers))
        if self.exc:
            raise self.exc
        return self.audio, "sfx-1"
