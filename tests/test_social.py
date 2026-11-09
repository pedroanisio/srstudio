"""Disclosure for opt-in new reels leaves legacy captions unchanged."""

import pytest

from srstudio import social


def test_disclosure_names_each_voice_and_code_drawing():
    assert social.disclosure(("Alice", "Bob")) == "Synthetic voices: Alice, Bob; drawn in code."


@pytest.mark.parametrize("voices", [(), ("",), ("Alice", " "), ("Alice\nBob",), "Alice"])
def test_disclosure_refuses_missing_or_malformed_voice_names(voices):
    with pytest.raises(social.DisclosureError):
        social.disclosure(voices)


@pytest.mark.parametrize(
    "credit", ["", "drawn in code", "Synthetic voices: Alice", "Synthetic voices: Bob; drawn in code."]
)
def test_partial_credit_is_a_typed_error(credit):
    post = social.InstagramPost("Title", "Description", credit=credit)
    with pytest.raises(social.DisclosureError):
        social.require_disclosure(post, ("Alice",))


def test_complete_credit_passes_and_legacy_empty_credit_still_validates():
    social.require_disclosure(
        social.InstagramPost("Title", "Description", credit=social.disclosure(("Alice",))), ("Alice",)
    )
    social.InstagramPost("Title", "Description").validate()
