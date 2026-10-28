---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
source: scripts.json
---

# Backlog: three scripts, each funnier than the last

Back to the [library README](../../README.md). The beats, cast and parts are kept in [scripts.json](scripts.json).

| # | Title | Style | Duration | Engine of the joke |
|---|---|---|---|---|
| 1 | Day Off | Soft (1080×1920, 30 fps) | 18 s | one premise, one twist |
| 2 | Not a Robot | Ink (1080×1080, 24 fps) | 32 s | rule of three turning existential, then a callback |
| 3 | The Cactus | Cutout (1080×1920, 30 fps) | 42 s | a crossover that pays off a gag hidden since *Five Years* |

The catalog so far leans on the office: six job interviews, most closing on a result card, three remote-work
sketches, two talking appliances and two songs where Pip dances instead of working. None of these scripts is an interview or a
meeting, none ends on a scorecard, and the one appliance is a cameo.

## 1. Day Off — Soft, 18 s

Pip finally has a Saturday on the sofa, but his body is still at work. It types on nothing and agrees with the
lamp, and he can only relax once relaxing is a meeting. This is *Focus Mode* turned around: there the groove
beat the work, here the work beats the rest.

| Time | Picture | Pip sings | Sound |
|---|---|---|---|
| 0.0–2.5 | Home wide. Pip lounges, eyes closed, smiling. | "Saturday. No work. Just me." | |
| 2.5–5.0 | On the beat his hands lift off his lap and type on the air; he looks down at them. | "My hands are typing… on nothing." | keyboard clicks, no keyboard |
| 5.0–7.5 | He nods on the beat at the floor lamp. | "Yes, totally. Great point, lamp." | |
| 7.5–10.0 | He stands, hands clasped, very calm, sits back down, and the hands drift up and type again. | "I can stop. I can stop any time." | |
| 10.0–13.5 | A badge pops: *Relax · 15 min*, then *Accepted*. He lounges; the groove melts; nothing moves. | "Booked a meeting… with the sofa." | calendar ping |
| 13.5–16.0 | *Meeting ended*. He snaps upright, typing on the air. | "Running over! Sorry, sofa!" | chime |
| 16.0–18.0 | *Extend 15 min?* He taps it, lounges, hard out. | | ping |

## 2. Not a Robot — Ink, 32 s

One form before lunch. The captcha's questions get more personal until it decides the human is a robot, and the
router from *The Router* welcomes him home.

| Time | Shot | Line | Sound |
|---|---|---|---|
| 0.0–3.0 | Desk | HUMAN: One form. Then lunch. | click |
| 3.0–6.0 | Screen | *☐ I'm not a robot* → tick → *Select all images with traffic lights.* | click |
| 6.0–8.5 | Close | HUMAN: Easy. | three clicks |
| 8.5–11.5 | Screen | *Select all traffic lights that are sad.* | |
| 11.5–14.0 | Close, squinting | HUMAN: …That one's having a day. | click |
| 14.0–17.0 | Screen | *Select every moment you felt truly alive.* Nine identical pictures of the laptop. | |
| 17.0–20.0 | Close, long silence | HUMAN: …Skip? | |
| 20.0–23.5 | Screen | *Verification failed. You hesitated like a human, but you clicked like a robot.* | error buzz |
| 23.5–26.5 | Router on its shelf, LEDs chasing | ROUTER: Welcome, brother. | LED chirp |
| 26.5–29.0 | Close | HUMAN: I'm not a… Do robots get lunch? | |
| 29.0–32.0 | Router, close | ROUTER: Only after a reboot. | |

## 3. The Cactus — Cutout, 42 s

The cast finally notices the potted cactus that has been in every original video since *Five Years*. It follows them from the office to the
café to the park, and in the end it is in the executive chair. The payoff lands on five videos of setup nobody
noticed (*Five Years*, *The Router*, *Focus Mode*, *Camera Off*, *Screen Share*). The script turns our most repeated format around, so the interviewer becomes the applicant, and
it calls back to *Five Years* twice (the chair, the squeak).

| Time | Location | Picture | Line | Sound |
|---|---|---|---|---|
| 0–6 | Office, wide | The interviewer stops reading a CV and stares at the cactus on his desk. | INTERVIEWER: Has this always been here? CANDIDATE: It came with the chair. | |
| 6–14 | Café | Ava sets a coffee down; the cactus sits by the tip jar. Its flower turns toward them. | BEANIE: Is that yours? AVA: I thought it was yours. | cup |
| 14–22 | Park | The beanie guy flees to the bench. The cactus is already there. The pigeon leaves. | BEANIE: I bought a coffee! I did everything right! | flutter |
| 22–30 | Office, reverse | The interviewer shuts the door, exhales, turns: the cactus is in the executive chair, turning slowly. | INTERVIEWER: …No. | the squeaky chair |
| 30–36 | Push-in | The code SR-1028 on the pot fills the frame. | INTERVIEWER: S-R… one-oh-two-eight? CANDIDATE: That's its employee number. | |
| 36–42 | Office, reverse | The interviewer sits in the applicant's chair, facing the cactus. | INTERVIEWER: So… where do you see yourself in five years? *The flower blooms. Hard cut.* | pop |

## What each needs to be built

| Script | Already in srstudio | New part |
|---|---|---|
| Day Off | `blob.home(on_sofa=)`, the `lounge`, `type-a/b`, `nod`, `step` and `clasp` poses, the `sing` mouth, `srstudio.song` | a Soft calendar badge, after *Camera Off*'s call badge |
| Not a Robot | the Ink human, `router_shot` and `talking-router`, `desk_shot`, `closeup`, the takes pipeline | `ink-captcha`: a screen shot with a 3×3 grid, a checkbox and a prompt line |
| The Cactus | the Cutout cast, the four locations and their slots, `signature.cactus` and `signature.code`, the executive chair | the cactus as a keyed prop (flower turn, bloom, placed on the bench and in the chair) |

The push-in in *The Cactus* must use the inline drawing, not instanced symbols. Engines 0.8.0 and 0.9.0 both
soften a magnified instance.
