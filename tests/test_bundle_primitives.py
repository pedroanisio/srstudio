"""PNG verification and directory publication enforce the bundle's byte boundaries."""

import struct
import zlib

import numpy as np
import pytest

from srstudio import composition as c
from srstudio import plates


def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))


def png(raw=None):
    return (
        b'\x89PNG\r\n\x1a\n'
        + chunk(b'IHDR', struct.pack('>IIBBBBB', 2, 2, 8, 6, 0, 0, 0))
        + chunk(b'IDAT', zlib.compress(bytes(18) if raw is None else raw))
        + chunk(b'IEND', b'')
    )


def test_png_validation_checks_a_complete_decodable_frame(tmp_path):
    from srstudio._composition_png import verify

    path = plates.write_png(tmp_path / 'image.png', np.zeros((2, 2, 4), np.uint8))
    assert len(verify(path.read_bytes(), 2, 2)) == 64


@pytest.mark.parametrize('bad', ['crc', 'tail', 'missing', 'bomb', 'filter', 'dimensions', 'signature', 'compressed'])
def test_invalid_pngs_are_typed_refusals(bad):
    from srstudio._composition_png import verify

    data = png()
    if bad == 'crc':
        data = data[:-1] + bytes([data[-1] ^ 1])
    elif bad == 'tail':
        data += b'extra'
    elif bad == 'missing':
        data = data[:-12]
    elif bad == 'bomb':
        data = png(bytes(100000))
    elif bad == 'filter':
        data = png(b'\x05' + bytes(17))
    elif bad == 'signature':
        data = b'not png'
    elif bad == 'compressed':
        data = data[:33] + chunk(b'IDAT', b'invalid') + chunk(b'IEND', b'')
    with pytest.raises(c.CompositionError):
        verify(data, 3 if bad == 'dimensions' else 2, 2)


def test_directory_publication_refuses_even_an_existing_empty_destination(tmp_path):
    from srstudio._bundle_output import publish

    target = tmp_path / 'bundle'
    target.mkdir()
    before = target.stat().st_ino
    with pytest.raises(FileExistsError):
        publish(target, {'scene.xml': b'complete'})
    assert target.stat().st_ino == before and list(target.iterdir()) == []
    assert list(tmp_path.iterdir()) == [target]


def test_directory_publication_is_complete_and_private(tmp_path):
    from srstudio._bundle_output import publish

    target = tmp_path / 'bundle'
    publish(target, {'scene.xml': b'scene', 'image.png': b'image'})
    assert sorted(p.name for p in target.iterdir()) == ['image.png', 'scene.xml']
    assert target.stat().st_mode & 0o777 == 0o700
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in target.iterdir())


def test_directory_publication_refuses_resource_path_traversal(tmp_path):
    from srstudio._bundle_output import publish

    with pytest.raises(ValueError):
        publish(tmp_path / 'bundle', {'../escape': b'bad'})
    assert list(tmp_path.iterdir()) == []


def test_stage_name_reuse_cannot_delete_published_files(tmp_path, monkeypatch):
    import os

    from srstudio import _bundle_output as output

    install = output.rename_new

    def reuse(fd, source, target):
        install(fd, source, target)
        os.mkdir(source, dir_fd=fd)

    monkeypatch.setattr(output, 'rename_new', reuse)
    output.publish(tmp_path / 'bundle', {'scene.xml': b'complete'})
    assert (tmp_path / 'bundle' / 'scene.xml').read_bytes() == b'complete'
    assert len(list(tmp_path.glob('.srstudio-bundle-*'))) == 1


def test_stage_open_failure_removes_the_empty_stage(tmp_path, monkeypatch):
    from srstudio import _bundle_output as output

    original = output.os.open

    def refuse_stage(path, *args, **kwargs):
        if isinstance(path, str) and path.startswith('.srstudio-bundle-'):
            raise OSError('cannot open stage')
        return original(path, *args, **kwargs)

    monkeypatch.setattr(output.os, 'open', refuse_stage)
    with pytest.raises(OSError, match='cannot open stage'):
        output.publish(tmp_path / 'bundle', {'scene.xml': b'complete'})
    assert list(tmp_path.iterdir()) == []
