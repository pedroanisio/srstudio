---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0072: Pedro, a parametric rebuild of the operator's sculpt, shot as replacement plates

- Status: proposed
- Deciders: the operator (pedroanisio) alone; implementation drafted by Claude Opus 5.5 in Claude Code
- Builds on [ADR 0068](0068-rafa-clay-host-on-plates.md) (plates), [ADR 0050](0050-organic-head-motion.md) (head motion)
  and [ADR 0020](0020-toon-lip-synced-cast.md) (lip sync)
- Back to the [library README](../../README.md)

## Context

The operator asked for his own likeness in the catalog: "this is Pedro (my self)". The source is a procedural 3D sculpt
of him. It has no rig, no skinning and no morph targets. Its smile and raised brow are separate static meshes built by
running the same code with other numbers. Its mouth is modelled closed, with no interior, inside a goatee that is a
single printed sheet over the jaw. A static turnaround is not a port: he has to pick up a pose, speak, blink, move his
head with speech and change expression while he does it.

The picture is his own face, so it is not caricatured or improved past what the sculpt does, and only he can approve it.
What identifies him stays: shaved sides under a short top, a high forehead, substantial eyebrows, relaxed brown eyes, a
straight nose broad at the tip, a connected moustache and salt-and-pepper goatee, navy over a black T-shirt.

After the first cut he gave eight photographs of himself to correct the sculpt, from April, May and August. His verdict
on the correction that came out of the first seven was that the character looked fat. The eighth, from mid-August, became
the main reference for the face and the outfit.

## Decision

**Rebuild the sculpt as parameters, and shoot it on the plates of ADR 0068.** The port keeps the sculpt's numbers and
gives up its meshes.

- `srstudio.pedro_sculpt` holds the head as the profiles and fields of the sculpt, ray-cast from one centre onto a fixed
  grid of rows and columns. Every expression therefore has the same vertices in the same order, which is what a blend
  needs and what the sculpt's marching-cubes meshes cannot give.
- `srstudio.pedro` holds an expression as a typed record of numbers, `Mood`, and blends two of them with `towards`, so a
  change of expression under speech is a continuous change of one surface. A mouth shape is a second typed record,
  `Shape`. One function, `warp`, moves skin, lips, goatee and beard strokes, so the goatee cannot part from the jaw it
  covers.
- A speaking mouth drops the triangles across the lip seam and opens the jaw through that slit, with teeth, a tongue and
  a throat behind. At rest no triangle is dropped and nothing of the inside exists.
- A blink is a lid surface that comes down over a whole eye. An open eye is the sculpt's own eye: no lid surface exists
  until the eye starts to close.
- `srstudio.pedro_wardrobe` holds his clothes as implicit fields, taken by marching tetrahedra.
- `srstudio.pedro_host` shoots him. `srstudio.plate_host` holds the clockwork that is not his: the shelf of plates, the
  held poses, blinks, spoken frames and gates. `rafa_host` can adopt it when the two branches meet.

Plates are layered so a clip costs a fraction of its frames. A pose plate has him with a bare face, an eye plate adds
eyes and brows, and a mouth plate adds the lower face, patched into the head box. Two-frame poses, stepped turns and nods
and a quarter-step share of a blend bound how many plates exist.

Nothing of the pack ships. No mesh, no reference, no font and no script is vendored: the repository carries code only,
and each plate is rebuilt from code into `generated/`. His photographs are not read by anything here and are in no
commit, no proof page and no catalog page.

**The photographs correct numbers, and only numbers.** The render was viewed beside them and proportions and colours were
changed by eye. No texture, plate or pixel is sampled from one, no face-matching tool ran and no likeness score exists,
because a port that carried his picture could not be separated from his picture.

**A lean head comes from one number, not from moving every feature.** `pedro.LEAN` narrows the whole head at the point
it enters the scene, so eyes, mouth, brows, nose, ears, hair and beard go in together and the warp that moves them stays
in the sculpt's units. Only irises and highlights are drawn wide to compensate, so they stand round. The rest of the
correction is shape:

- The face tapers from the cheekbones to the chin, with flat temples, a hollow under the cheekbones and no jowl. The back
  of the head falls away towards the nape, so it is not a block from the side.
- A real neck shows above the tee, narrower than the jaw, and his head sits on it instead of on his shoulders.
- The eyes sit deep under a strong ridge. The forehead is smooth: its lines are gone.
- The nose is straight and longer, broad at the tip. The mouth is smaller, with fuller lips.
- The hair is a short textured crop, salt and pepper, low on the skull, with a soft peak on a high forehead. The sides
  are a close, greying shave, painted on the skin no expression moves.
- The beard is a goatee only: a moustache joined to a chin beard that runs past the chin to a soft point, grey towards
  the tip, leaving bare cheeks and a bare jawline. Past the jaw it leaves his skin and curls under the chin.
- The default outfit is a navy blazer with notched lapels over a black crew-neck tee, on a lean figure with sloping
  shoulders. The tee is cut from the same figure, so the blazer is one layer over it.

Options exist on the turntable only: `view(dress="tee")`, `view(dress="puffer")` and `view(glasses=True)`. Reels draw
none of them, so they add no plate to a clip. Glasses are the frames alone, because a material here has no glass.

No dependency is added. `contour` replaces scikit-image's marching cubes, a monotone cubic of about a dozen lines
replaces scipy's Pchip, and the goatee's picture is made in numpy. The proof ships no text, so the sculpt's font does not
ship and its licence needs no notice here.

## Rejected alternatives

- **The head motion of ADR 0050 on a flat picture of the sculpt.** A 2D rig moves parts of a drawing. A path-traced head
  shows its volume at every turn, the light moving across the forehead and the jaw, and a 2D rig cannot do that without
  losing the look the operator recognises.
- **Morph targets on the sculpt's own meshes.** The expressions are remeshed by marching cubes, so their vertices do not
  correspond. Correspondence would need registration first, and the closed mouth would still have no slit to open.
- **Swapping between the three static meshes.** It would snap between expressions, and it has no mouth at all.
- **A skeleton and skinning on the exported GLB.** Bones do not make a mouth interior or a lid, and the skin is a single
  closed sheet with the goatee printed on it.
- **A real-time rig instead of plates.** Plates give the same frame as the sculpt's own path-tracer, and ADR 0068 already
  pays for them by digest.
- **Vendoring the pack.** It is a large set of meshes that would be read by nothing once the numbers are ported.
- **Projecting a photograph on the head.** It would be the closest likeness and would put his photograph in the repository
  and in every plate, which the operator ruled out.
- **Moving each feature in to a narrower sculpt by hand.** It would repeat the same factor through dozens of numbers, and
  every warp would need retuning. One factor at the scene boundary keeps them all in proportion.
- **Thinning only the jacket.** The puffer was the biggest single cause after the head, but no cut of it stops being a
  wide mass under the jaw. The blazer is the outfit of the main reference.
- **Ear plugs.** Two photographs show dark objects at both ears, but the August lift mirror shows a bare lobe and no
  August view shows anything there. The latest photographs win on shape, so they are left out.
- **A second hairstyle, the maroon windbreaker, April's cheek stubble and grown-out sides.** Each describes a period, not
  the default, and none comes free with the sculpt. May and April were used to judge strand direction, grey and skin
  tone instead.

## Consequences

- **Only a head and chest.** The port has no trousers, shoes or hands: the frame does not show them. A standing or
  gesturing shot needs them added.
- **The iris is more matt than the sculpt's.** The sculpt's iris and pupil are smooth enough to mirror the key light, and
  on one eye at some poses that turned a brown iris grey. Raising their roughness keeps both eyes brown at every pose.
  This is the one number changed away from the sculpt to keep an identifying feature.
- **He moved away from the sculpt on purpose.** The head's width, the hair, beard, eyes and clothes are no longer the
  sculpt's. The sculpt stays the start of the numbers, and the photographs are the reason for each change.
- **The puffer stays as code.** It costs nothing to keep because it was already built, and no reel draws it.
- **Lapels and collar are thin meshes on a contoured shell.** At the reel's angles they are clean. At three-quarter a small
  jag remains where the collar meets the shoulder.
- **The first build is slow and a change of geometry rebuilds everything.** Plates are keyed by what they draw.
- **A second plate host exists until `rafa_host` adopts `plate_host`.**
- **Approval is his alone.** The part stays `proposed` until he has judged a moving clip, and no one else records it.
