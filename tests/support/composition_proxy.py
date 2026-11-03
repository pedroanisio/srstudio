"""A plan for one static proxy source, shared by the proxy tests and the timeline tests."""

from dataclasses import replace

from srstudio import composition as c
from support.composition import plate_plan


def plan_for(item, *, passes=('rgba',)):
    base = plate_plan()
    binding = replace(
        base.bindings[0],
        backend='proxy',
        nodes=512,
        memory_bytes=64 * 1024**2,
        plates=c.proxy_jobs(item, width=64, height=64, memory_bytes=8 * 1024**2),
    )
    spec = replace(base.spec, layers=(replace(base.spec.layers[0], passes=passes),))
    return c.preflight(spec, (binding,))
