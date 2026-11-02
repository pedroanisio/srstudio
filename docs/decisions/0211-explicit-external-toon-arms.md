---
generated-by: OpenAI Codex (GPT-6)
---

# 0211: Declare externally drawn arms on candidate Toon clips

The shared candidate needs a spatial arm attached to a native split-head
character. Drawing that arm over the original two native arms creates a third
hand; suppressing arbitrary XML nodes loses anatomical ownership and depends on
generated IDs. The source's tablet gesture also owns a prop that conflicts with
the new carrying action.

Add an optional, immutable `external_arms` tuple to `ToonClip` and
`toon_head.figure`. Each entry is a distinct `left` or `right`. Validate the
complete bounded pose sequence before scene or anatomy-ledger mutation. Nonempty
delegation requires `rig.drawn_as=None` and separable shared arm poses. Reject
drawing-specific indivisible gestures, including overrides of shared pose names.
This is candidate authoring, not approval of a modified registered drawing.

The existing arm drawer and anatomy ledger receive the same omitted-side set.
Typing frames, under-head arms and over-head arms all honor it. Facial, gaze,
head and source-clock ownership stay with their existing paths. The caller owns
the external geometry, its attachment and complete composition proof; this
setting does not add replacement LimbTrack support to the split-head backend.

The default empty tuple preserves existing drawings and positional clip
arguments. Existing approved rig/specimen and clip tests remain applicable.
Malformed ownership and incompatible poses raise repairable HeadMotionError
diagnostics before mutation.

Rejected alternatives: drawing another arm leaves duplicates; making a native
arm transparent leaves incorrect ownership; removing nodes by generated IDs
couples anatomy to emission order; silently accepting named gestures can leave
pieces of their hands or props behind.
