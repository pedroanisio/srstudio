---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0064: A floor under the comedy

- Status: accepted (2026-10-31), from the operator's words: "we should not ship bellow the comedy target for the comedy
  chanel"; and, on the first scope, "no, Maps is not comedy."
- Deciders: the operator (pedroanisio), recorded by Claude Opus 5.5 in Claude Code
- Follows [ADR 0015](0015-toon-sketches.md) and [ADR 0056](0056-auto-enhance.md)
- Back to the [library README](../../README.md)

## Context

The funny-reels skill has a rubric of ten criteria at 0 to 2 points, and 14/20 was what an author aimed for. An aim
stops nothing: the author scored their own script, and no command read the number.

ADR 0015 rejected a model-scored funny gate. This is not that gate. No model is called, the gate certifies nothing
funny, and the operator keeps the last word on any video. It holds a recorded judgement to a number.

## Decision

1. `srstudio.comedy_floor` holds the floor: `FLOOR` is 14 and `TOP` is 20. A video has two scores, the author's and the
   reviewer's, each a whole number from 0 to 20. The reviewer is a different session from the author, and scores
   independently. The lower counts.
2. A News pilot carries `comedy-author` and `comedy-reviewer` in the frontmatter of its `notes.md`, the file every pilot
   already ships.
3. A @tuxmeme reel carries `comedy=Scores(author, reviewer)` on its `Release`, because a reel has no `notes.md` and its
   release is the typed file the gates already read. `Tags` is the wrong home: it holds what the analytics count, from
   closed sets, and many releases have none.
4. Missing, malformed, off the scale or under the floor is a typed `ComedyError` naming the slug and the reason, before
   anything is staged or written.
5. `publish_pilots.py` holds the floor for every series outside `NOT_COMEDY`, which is Mind and Maps. Mind is an
   explainer channel, and the operator ruled that Maps is not comedy, so of today's series only News owes it. A series
   added later owes the floor until someone lists it, so forgetting fails closed. An unknown series is refused as before.
6. `instagram_posts.py deliver` holds it on a reel's first delivery, using the same test as auto-enhance: a video in the
   delivery manifest owes nothing, and a pilot already on Drive owes nothing. So published reels need no list and no
   score, and `check` asks for none.
7. The gate has no mode. Turning auto-enhance off does not lift it.

`--series` and the `news` series reach this branch with the gate: the option was written for the Maps channel and had
not merged, and refusing a series needs a command that knows one.

The scores are agents' judgements, so they are model output and get the five controls of the project rules: a typed
parse into `Scores` that refuses unknown `comedy-` fields, range and floor checks, a typed refusal, failing-input tests
in `tests/test_comedy_floor.py`, and no loop a model can steer.

## Alternatives rejected

- **A model scoring the reel.** ADR 0015 rejected it: it would measure a model's taste, not the audience's.
- **Averaging the two scores.** A generous author would carry a reviewer's low score. The lower counts.
- **Gating `check` as well.** `check` runs in the Drive unit and over all published reels, which are frozen. A reel that
  skipped the floor is already refused by `check` as never delivered.
- **A closed list of exempt reels.** The manifest already says what has been delivered, as in ADR 0056.
- **Refusing a short pilot already on Drive.** Staging takes the whole set, so one old pilot would hold back a new one.
- **A list of comedy series.** A new series would pass by default. The list that exists is of series that are not comedy.
- **A field naming the reviewer's session.** The same hand can write it, so it would look like proof without being any.

## Consequences

- The honest limit: the scores are judgements, and the gate proves two numbers were recorded and that the lower reached
  14. It does not prove that a reel is funny. It does not prove a second reader scored it either: it cannot see who
  wrote the numbers, so one session writing both passes. Independence is a rule of the process, stated in the skill, and
  it holds only as far as agents keep it.
- A score can be raised to clear the floor. Nothing mechanical stops that, but the number sits in the diff, in the
  release file or in the pilot's notes, beside the session that wrote it.
- The floor is a judgement call on a rubric, so it can refuse a funny reel and pass a dull one. The account's numbers,
  not this gate, say which reels worked.
- Reels and News pilots still on a branch owe scores at first delivery, and a reviewer session is now part of the cost
  of each new one.
