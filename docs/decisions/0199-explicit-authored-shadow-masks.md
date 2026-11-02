---
generated-by: OpenAI Codex (GPT-6)
---

# 0199: Authored shadow masks name their caster, receiver and directional light

The hybrid candidate's ground mark has no validated relationship to its caster or receiver. The drawing
contract permits authored masks bound to a pose; it does not permit treating any dark image as a proven shadow.

`LayerSpec.shadow_mask` carries a closed `ShadowMask` record. Its caster must request the same receiver,
the receiver must precede the mask, and the mask must precede the caster. Exactly one mask covers each
requesting caster's entire interval. The mask is parented to its receiver. This explicit relation preserves
the prior refusal for an unsupported shadow request instead of silently omitting it.

The receiver and mask use actual static convex `FormPath` geometry. Plane and containment checks follow their
complete world transforms. A named caster anchor projects along a positive directional light onto the receiver
plane and must agree with a named anchor inside the mask. Source-time anchor keys share the contact budget.
Because directional projection onto a fixed plane is affine, endpoint checks at the union of linear source
keys bound the complete intervals. Each timeline configuration revalidates the complete source interval;
arbitrary moving silhouettes are not inferred from sampled anchors.

Geometry alone cannot prove that an emitter draws a mask. The bounded preparation worker also rejects invisible
fills or ancestors, native timing/visibility animation, and mask strokes outside the declared footprint. Static
and timeline assemblers repeat that verification. Bundles validate it before raster cache access or rendering.

Rejected alternatives: projecting an asset's bounding box would invent a caster silhouette; a flat RGBA plate
does not define a receiver plane; allowing arbitrary alpha images would provide no measured world registration;
accepting an invisible shape would satisfy metadata while omitting the requested drawing.

Unused optional fields are omitted from semantic identity and metadata cost accounting. Existing unshadowed
static and timeline XML, plan hashes and cost estimates have frozen regression fingerprints.

The adapter supports authored masks, not physical shadows, self-shadowing, curved/concave receivers or changing
local polygon topology. The full hybrid scene must integrate this contract and independently pass its rendered
occlusion, palette, continuity, full-size review and operator adoption gates.
