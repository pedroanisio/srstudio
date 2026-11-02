---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0145: Convert static proxy passes within the composition budget

- Status: accepted (2026-11-01)
- Back to the [library README](../../README.md)

A proxy needs both rendered light and semantic part IDs before conversion.
Calling the standalone proxy renderer during preparation would conceal this
work from scene budgets and keep a private lighting owner. The composition
adapter instead snapshots geometry and a closed immutable recipe. Existing
recipes require an explicit `lighting="scene"` acknowledgement. The scene owns
illumination and projection; the ID pass deliberately uses emissive IDs with
black ambient light.

`proxy_jobs` derives the unique raw source keys and oversampled dimensions.
`prepare_proxy` verifies geometry, material references, complete job declarations,
aggregate resources and conversion working storage in a limited worker. It
reuses the verified plate preparation core with adapter-owned views and jobs.
Static ordinary plates retain their existing identities. Only a `PreparedProxy`
can carry these passes into bundle compilation; bare proxy `PreparedPlate`
records are refused.

Each layer selects one of `rgba`, `back`, `front` or `under`. Under parts have an
additional independent light/ID pair so hidden surfaces can be revealed behind
actors. Identical raw renders deduplicate across selected layers. Every source
is reverified before cache access. Cold renders and warm cache images use the
existing engine identity, PNG verification and nested process budgets.

PNG decoding and the existing proxy classification, tone/ink conversion and
premultiplied-alpha downsampling execute inside the worker. The PNG reader
shares strict stream verification with the cache checker and supports all five
standard RGBA8 row filters without a new decoder dependency. Resource limits
bound input, intermediates, output and execution. Conversion results must be
finite. Final bundles contain only selected output images.

The source identity includes conversion controls; raw render identities do not
include palette or grain controls that cannot affect those renders. A palette
change therefore reuses verified raw images but recomputes converted pixels.
Warm builds perform no engine work and still verify and convert their inputs.

Rejected alternatives include silently replacing authored recipe lights,
calling unbounded standalone proxy rendering, exposing live mutable recipe
mappings, decoding images in the unrestricted parent, and flattening back/front
into an ambiguous multi-pass layer. These respectively hide authorship changes,
work, input mutation, resource use and layer ordering.

This decision establishes a static adapter. Animated plates/proxies, cross-layer
shadow receivers, automatic internal occlusion, temporal-quality evidence and
operator style approval remain separate requirements. See the
[executable guide](../composition-preflight.md#prepare-a-static-proxy) and
[contract/render tests](../../tests/test_composition_proxy.py).
