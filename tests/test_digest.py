"""One file hash for the whole library (srstudio.digest)."""

from __future__ import annotations

import hashlib

import pytest

from srstudio import digest, episode, generated, narration, package, social


def test_sha256_is_the_hex_digest_of_the_files_bytes_read_in_blocks(tmp_path):
    data = bytes(range(256)) * 9000  # larger than one read block
    path = tmp_path / "f.bin"
    path.write_bytes(data)
    assert digest.sha256(path) == hashlib.sha256(data).hexdigest()
    assert digest.sha256(str(path)) == hashlib.sha256(data).hexdigest()


def test_an_empty_file_hashes_to_the_empty_digest(tmp_path):
    (tmp_path / "e").write_bytes(b"")
    assert digest.sha256(tmp_path / "e") == hashlib.sha256(b"").hexdigest()


def test_a_missing_file_is_an_error_not_a_digest(tmp_path):
    with pytest.raises(FileNotFoundError):
        digest.sha256(tmp_path / "missing")


@pytest.mark.parametrize(
    "alias", [episode.sha256, package.sha256, generated.sha256_of, narration.sha256_of, social._sha]
)
def test_every_module_hashes_with_the_one_function(alias):
    assert alias is digest.sha256
