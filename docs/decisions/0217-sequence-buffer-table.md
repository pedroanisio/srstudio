---
generated-by: Claude Code (claude-opus-5-5)
---

# 0217: Raster sequences carry each distinct mesh buffer once

A raster sequence is a list of held snapshots, and each snapshot is a complete
plate or proxy source. Static geometry, such as a prop that never moves or a
triangle list whose topology never changes, used to be serialized again in every
snapshot. The compiler's `worker.protocol` cap (8,388,608 bytes of combined
source buffers) counted every copy. The supported Bento candidate's 80 hand
snapshots carried 3,350,720 bytes. The two fixed cup rests accounted for
1,236,480 of them. The triangle lists, identical in every snapshot, accounted for
1,328,640, including the rests' share. The documented
12-fps complete scene measured 8,941,694 bytes and failed the cap before any
render.

The sequence payload is now a content-addressed table plus references:

- `RasterSequence` IPC carries `buffers`: a list of `{digest, data}` entries,
  one for each distinct mesh buffer (vertices, normals, triangles, UVs). The
  digest is the SHA-256 of the raw bytes. Snapshot meshes carry the digest in
  place of inline base64.
- Decoding verifies every entry against its digest. It refuses duplicate
  digests, references to missing entries, inline data, and entries that no
  snapshot uses. Snapshots resolve to one shared bytes object per entry.
- `validate_source` counts each distinct buffer once, which is exactly the table
  that crosses to the worker. The decoder recounts the table it received and
  refuses a sequence whose recount differs.

Plate and proxy sources outside a sequence keep inline buffers.

Sequence preparation had the same defect one step later. The prepare-sequence
reply inlined every content-named resource (`meshes/<sha256>.obj`) for every
pass of every snapshot, and the worker's bound counted each copy. For the
candidate's 12-fps hand this came to 8,843,680 bytes: 467,520 of prepared XML,
plus 8,376,160 of resources that are 2,267,126 bytes across 232 distinct files.
The light and ID passes of a snapshot share their meshes, and held snapshots
share the rests. The reply now carries a verified resource table in the same
form. Passes reference it, and the bound counts the prepared XML of each
snapshot plus each distinct resource once. The client refuses unused,
duplicate, mismatched or missing entries and inline data, and shares one bytes
object per entry. Prepared digests are unchanged; a test pins them.

The cap value is unchanged. Snapshot digests, `raster_sequence_digest` and
render-job keys hash the same source content as before, so cached renders stay
valid; a test pins the earlier identities. With the table, the candidate's hand
sequence measures 1,090,592 bytes and the complete scene 6,681,566.

Rejected alternatives:

- Counting distinct buffers while still sending a copy per snapshot would make a
  protocol cap report fewer bytes than cross the wire.
- Moving the rests into their own raster binding needs 13 more plate renders, so
  the scene's declared plate budget would have to rise (209 against 208). The
  cup–rest contact edge would then be composited from two layers instead of
  rendered once.
- Lowering the world cadence, or raising the cap, changes the candidate or the
  shared bound rather than removing the duplication.
