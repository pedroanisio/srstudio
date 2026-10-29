"""Every error the library raises shares one base, :class:`srstudio.errors.SrstudioError`, and keeps the built-in
base it had (``ValueError`` for bad data, ``RuntimeError`` for a missing key or a provider failure), so a caller
can catch the library's errors at once without losing the finer handlers."""

import ast
import importlib
import pkgutil
from pathlib import Path

import pytest

import srstudio
from srstudio import errors, voice
from srstudio.errors import FlagError, MissingKeyError, ProviderHTTPError, SrstudioError

SRC = Path(srstudio.__file__).resolve().parent


def _error_classes():
    for info in pkgutil.iter_modules([str(SRC)]):
        if info.name == "__main__":  # runs the command line
            continue
        module = importlib.import_module(f"srstudio.{info.name}")
        for node in ast.parse((SRC / f"{info.name}.py").read_text()).body:
            if isinstance(node, ast.ClassDef):
                cls = getattr(module, node.name)
                if isinstance(cls, type) and issubclass(cls, BaseException):
                    yield f"{info.name}.{node.name}", cls


ERRORS = dict(_error_classes())


def test_the_library_defines_its_errors():
    assert len(ERRORS) >= 45 and "sketch.SketchError" in ERRORS and "usage.UsageError" in ERRORS


@pytest.mark.parametrize("name", sorted(ERRORS))
def test_every_library_error_is_a_srstudio_error(name):
    assert issubclass(ERRORS[name], SrstudioError)


@pytest.mark.parametrize(
    ("name", "builtin"),
    [
        ("sketch.SketchError", ValueError),
        ("styles.StyleError", ValueError),
        ("usage.UsageError", RuntimeError),
        ("fonts.FontError", RuntimeError),
        ("catalog_page.CatalogError", Exception),
        ("voice.TranscriptMismatch", ValueError),
    ],
)
def test_an_error_keeps_its_builtin_base(name, builtin):
    assert issubclass(ERRORS[name], builtin)


def test_the_package_exports_the_base():
    assert srstudio.SrstudioError is SrstudioError


def test_a_missing_key_is_a_typed_runtime_error(tmp_path):
    (tmp_path / "line.wav").write_bytes(b"RIFF not yet heard")
    client = voice.ElevenLabsClient(tmp_path, "", model="m", seed=1)
    with pytest.raises(MissingKeyError, match="ELEVENLABS_API_KEY is required for speech-to-text") as err:
        client.transcribe(tmp_path / "line.wav")
    assert isinstance(err.value, RuntimeError) and isinstance(err.value, SrstudioError)


def test_a_provider_http_failure_is_a_typed_runtime_error():
    assert issubclass(ProviderHTTPError, RuntimeError) and issubclass(ProviderHTTPError, SrstudioError)


def test_flags_accepts_the_known_ones():
    assert errors.flags(["--voice"], {"--init", "--voice"}) == {"--voice"}
    assert errors.flags([], {"--voice"}) == set()


@pytest.mark.parametrize("argv", [["--voiced"], ["--voice", "-v"], ["voice"]])
def test_flags_refuses_a_typo_instead_of_building_the_silent_cut(argv):
    with pytest.raises(FlagError, match=r"unknown flag.*known: --init, --voice"):
        errors.flags(argv, {"--voice", "--init"})
    assert issubclass(FlagError, ValueError)
