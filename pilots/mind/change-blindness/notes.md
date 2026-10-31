---
pilot: change-blindness
main-trigger: challenge
to: whoever they want to try it on, or the neighbour who sees everything
generated-by: claude-opus-5-5 in Claude Code
date: 2026-10-31
---

# Notes: Change Blindness

## Main trigger

Challenge. The viewer takes part: "One thing in this room is changing. You have until she shuts up." The observation
came first: the neighbour who notices everything, and tells you. Her confidence is the joke and the trap at once, so the
talking scene is the whole reel and the reveal is its last third. The hook is a dare with a clock on it, and the clock
is the fox's mouth.

A fox gossips to a sloth in her hall. Number six, number nine and his shampoo go onto a pad headed "Noticed", and she
ends on "Nothing gets past me." Behind them the front door has turned from teal to red. It runs back and forward again,
sped up, and she says it has been red for years, which goes on the pad too. Then two neighbours carry a teal door
through, and the sloth is a bear when it has passed. She looks at him and takes the credit: "There. You changed it back. Much better."

It ends on a hard cut to the first frame, door teal and sloth back, so the second watch starts on a viewer who knows
where to look. It is one shot with no cut until the reveal, because a cut would be an interruption, and the claim is
about changes with none. Only a slow push moves the frame in those 12 s.

The name is not a card. It sits on the first stamp, over the picture, for about 2 s.

## What is claimed, and what is comedy

- "Large, slow changes can go unnoticed. Simons et al., 2000" is the source file's stamp. Status: abstract-level (rows 1
  and 2).
- "A stranger swapped mid-chat. Only half noticed. Simons & Levin, 1998" is the source file's other stamp. Status:
  abstract-level (row 11). Neither paper was read in full.
- "In one study, a stranger was swapped mid-chat. Only half noticed." keeps "in one study", so it says nothing of
  everyone.
- "Researchers found the same with photographs." is the file's safe wording. It sits next to the first stamp so that the
  stamp does not read as a result about this hall. No line says a study tested a door, a drawing, a hall or a talking
  character, and no line says how many viewers miss this door.
- The door carried past is the setup in row 14, which is a secondary source. The reel only acts it out; no line
  describes the setup, and the two carriers are neighbours, not the study's "construction workers".
- The swap of a sloth for a bear is comedy. The study's two people were alike in gender and age (row 14), which is
  nothing like a sloth and a bear.
- Her "Much better." is a joke, not a finding, though it leans on row 6: viewers realised something was different
  without having seen it change.
- The change takes 12 s, the only duration documented (rows 5 and 8). It is colour, the best-supported change (row 8),
  and not a fade: two opaque doors of the same shapes, so no frame shows anything through anything (David et al., p.
  255, on transparent artefacts). No flashes and no flicker.
- The door is about 10% of the frame in its drawn size, partly behind the sloth. That is more than the 1.9% of row 7, so
  the reel makes no claim about how hard this one is.

## Parts reused

Fox, sloth, bear, rabbit and raccoon from the Toon cast at their approved versions; the hallway set and its door; the
oak ledge; the mind kit's captions, grade, key light and sting; the signature cactus and code.

## Parts new (all proposed)

None. The repainted door, the carried door, the pad and the stamps are the pilot's own dressing, drawn in
`episodes/pilots/change_blindness_data.py`. No library or kit file changed.

## What I would change

- The reel runs 27.8 s, over the 25 s target. The 12 s change sets the floor, and the last 1.5 s are the first frame held
  for the replay, the least a sketch runs after its last beat.
- The change starts at 1.9 s and ends on "The door." at 13.9 s, so its first second falls under the hook. I cut a fourth
  neighbour ("Number four has two bins now.") to bring the length down, and the three that are left are stronger.
- There is no music. Two voices, the sting and the whoosh carry the sound.
- The sloth only blinks. That is right for him, but the fox's head, the pad and the push carry the motion of those 12 s.
- The door keeps its brightness while its hue moves, so the middle of the change is a dull mauve. I can't tell yet
  whether that reads as a colour or as a shadow.
- The fox's crossed arms run long across her chest at 9.5 to 15 s. It is her stock pose, and it looks stretched.
- The raccoon's snout crosses the fox's cheek and mouth corner for part of the carry. Her eyes stay clear, and the door
  hides the sloth on purpose: that is the swap.
- The fox's head tilts a little differently on the last frame than on the first, because the head's motion is still
  settling. The set, door, sloth, pad and caption match.
- The fox's head springs restart from rest every 8 keys, in `rest_springs`. On one long shot the engine's time for a
  frame grows very fast with each carried key. The pilot deals with that itself; the library is unchanged.

## Watch gate

- At 2 seconds, did you want to keep watching?
- Who would you send this to, if anyone?
- Did the first-time viewer spot the change before the reveal?
