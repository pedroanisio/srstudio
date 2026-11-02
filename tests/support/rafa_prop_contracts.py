"""Actual static Rafa builders and their exported mesh identities."""

from functools import lru_cache

from srstudio import clay, rafa, registry

BUILDERS = {**rafa.PROPS, **rafa.ROOMS}
ENTRIES = tuple(e for e in registry.entries() if e.name in BUILDERS)
PRINTS = {
    'rafa-mug': {'mug-label'},
    'rafa-phone': {'phone-screen'},
    'rafa-bills': {'bill-label'},
    'rafa-lunchbox': {'lunch-label'},
    'rafa-tote': {'tote-label', 'receipt'},
    'rafa-kitchen': {'home-print'},
    'rafa-breakroom': {'office-poster'},
}


@lru_cache(maxsize=7)
def meshes(name):
    model = clay.Model()
    result = BUILDERS[name](model)
    assert result is None
    return model.meshes()


def identity(name):
    return {mesh.material: mesh.sha256 for mesh in meshes(name)}
