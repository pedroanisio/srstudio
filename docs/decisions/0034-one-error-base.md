---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0034: Every library error shares one base, and a builder refuses a flag it does not know

- Status: accepted; implemented 2026-10-29 (`srstudio.errors`: `SrstudioError`, `MissingKeyError`,
  `ProviderHTTPError`, `FlagError`, `flags`; `tests/test_errors.py`, `tests/test_sketch_builders.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

The library defined about 45 error classes with no common base. Most subclassed `ValueError`, some
`RuntimeError`, one `Exception`. A caller could not catch "any srstudio error" without also catching unrelated
built-in errors. Two failures had no type of their own:

- **A missing API key** raised a bare `RuntimeError` from the ElevenLabs client, the song composer and the voice
  confirmation, indistinguishable from any other runtime failure.
- **A provider HTTP error** was also a bare `RuntimeError`.

Builders read their flags with `"--voice" in sys.argv[2:]`. A typo such as `--voiced` was ignored and built the
silent cut of a narrated episode, with no error.

## Decision

- **`SrstudioError` is the base of every error class in `src/srstudio`.** Each class keeps the built-in base it
  had (`SketchError(SrstudioError, ValueError)`), so existing `except ValueError` handlers still catch bad data.
  `srstudio.SrstudioError` is exported from the package.
- **Typed provider errors.** `MissingKeyError` and `ProviderHTTPError` subclass `SrstudioError` and
  `RuntimeError`. A missing key and an HTTP failure now raise these. The HTTP error carries the provider's message
  only, as before.
- **Builder flags are checked.** `errors.flags(argv, known)` returns the given flags or raises `FlagError` naming
  the unknown ones and the known ones. The Toon and Collage sketch builders and the hand-written builders
  (`employee_survey.py`, `mushroom_training.py`) call it before building anything.
- **A test enforces the base.** `tests/test_errors.py` imports every module in the package and asserts that every
  exception class it defines is a `SrstudioError`, so a new module cannot add an error outside the hierarchy.

## Rejected alternatives

- **Replace the built-in bases with `SrstudioError` alone.** That would break every caller and test that catches
  `ValueError` or `RuntimeError`, for no gain.
- **One generic `SrstudioError` raised everywhere.** Each module's own class is how tests and callers tell
  failures apart; the base adds a catch-all without removing them.
- **argparse in every builder.** The builders take one or two flags each, and most of them are thin scripts over
  a shared library build. `errors.flags` gives the same refusal in one line.

## Consequences

- An application can catch `SrstudioError` at its boundary and handle every library failure in one place.
- A new error class must subclass `SrstudioError`, or `tests/test_errors.py` fails.
- A mistyped builder flag stops the build with the list of valid flags, instead of producing a silent master.
