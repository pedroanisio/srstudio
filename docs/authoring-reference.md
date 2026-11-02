---
updated-by: OpenAI Codex (GPT-6)
---

# Authoring task index

<a id="authoring-and-episode-reference"></a>

Start with the [library README](../README.md) for installation and a first working episode.
Choose a focused guide below; each keeps the relevant inputs, clocks, runtime bindings and failure paths together.
Run commands from the srstudio repository root.

## Agent authoring entry points

Start from the task, inspect the selected rig's capabilities, then use its typed API. JSON contracts describe
arguments; objects such as `Canvas` and scene parents remain runtime bindings. Do not infer a capability from
a similar character or pass contract JSON directly to a builder.

| Task | Entry point | Clock and capability checks |
| --- | --- | --- |
| Discover a character, prop or location | `srstudio inspect KIND NAME --json`; [agent contracts](authoring-discovery.md#agent-contracts) | Read declared units, vocabularies, versions and runtime bindings; unknown fields remain unknown. |
| Place different character families | [Character clips](authoring-clips.md#character-clips-one-placement-and-timing-boundary) | One local performance clock and an explicit project interval; adapters enforce family capabilities. |
| Coordinate emotion, speech and listening | `parse_score`, `compile_performance`; [acting](authoring-acting.md#coordinated-acting-and-continuity) | Strict score schema, supported emotion maps and explicit channel ownership. |
| Add anticipation and staggered arrivals | [Transition policies](authoring-acting.md#opt-in-acting-transition-policies) | Opt-in score 1.1.0; declared phases must fit and respect contacts. Faces remain held drawings. |
| Blend authored facial expressions | [`bento_blends()` and `blend=True`](authoring-acting.md#authored-emotional-blends) | Score 1.2.0; declared face pairs, bounded geometry samples and one performance clock. |
| Carry state through a cut | [Listening](authoring-acting.md#sustained-listening-and-repairable-capability-failures) and [carrying](authoring-acting.md#carrying-a-prop-across-a-cut) recipes | Window one source performance; preserve contact, expression and texture clocks. |
| Author constrained arm motion | [Limbs guide](catalog/limbs.md) | Declare anatomy, reference units, projection and contacts; canonical-arm limits do not certify whole-body motion. |
| Coordinate pelvis, torso, feet and steps | [`body.compile_body`](authoring-body.md) | World sole anchors, explicit joint envelopes and a sampled static support proxy; source-clock cuts. |
| Choose a continuity guarantee | [Continuity discovery](catalog/limbs.md#inspect-continuity-before-choosing-a-transition) | Inspect source key derivatives, estimated joins, endpoint holds and rendered sampling separately. |
| Repair invalid authoring input | [Diagnostic recipe](authoring-diagnostics.md#repairing-authoring-input) | Match `code` and `path`, validate corrected input, and bound retries in ordinary code. |
| Evaluate motion quality | [Quality study](../examples/limbs_quality.py) | Keep numeric limits, strict rendering and human temporal ratings separate. |
| Measure authoring cost | [Authoring benchmark](authoring-benchmark.md) | Separate cold/warm phases, compare output hashes, and bound plate renderer invocations. |
| Compile a bounded composition | [Composition preflight and emission](composition-preflight.md) | Validate manifests and vector/plate/proxy payloads, preserve clocks, and publish supported scenes or portable bundles. |
| Keep a spatial hand/prop registered to plates | `composition.spatial_camera`, `scene_motion.spatial_cameras`; [spatial registration](composition-preflight.md#register-a-spatial-camera) | Fold world parents once, preserve the scene camera clock, and compose baked vectors in screen space. |
| Build a hybrid drawing review candidate | [Candidate and measured review](drawing-proof.md) | Keep new geometry unapproved, bound render work, and distinguish measured gates from remaining acceptance work. |
| Animate a shared camera, lights and parents | `scene_motion.plan_scene`, `emit_timeline`; [timeline emission](composition-preflight.md#emit-a-scene-timeline) | Bound the complete clip, preserve source clocks through held view cuts, and share verified raw renders. |


| More authoring tasks | Guide |
| --- | --- |
| Record, verify and place audio | [Audio workflow](authoring-audio.md) |
| Load dialogue, take audio or timed captions | [Timeline inputs](authoring-timelines.md) |
| Choose frame, palette, lip sync and effects | [Styles and scene finishing](authoring-styles.md) |
| Find a drawing family and pin its version | [Parts and versions](authoring-parts.md) |
| Register a builder and define failure behavior | [Drawing extensions](authoring-extensions.md) |
| Sign a scene, prepare covers and package releases | [Delivery](authoring-delivery.md) |
| Select the relevant SDK, render and delivery checks | [Verification](authoring-verification.md) |

## Episode history

[Episode and package records](episode-history.md) retain the detailed production history.
Reusable discovery, acting, timing, drawing and delivery workflows live in the task guides above.

## Existing section bookmarks

Earlier links to this reference still resolve below. Follow the named section to its guide.

- <a id="repairing-authoring-input"></a> [Repairing authoring input](authoring-diagnostics.md#repairing-authoring-input)
- <a id="timeline-input-formats"></a> [Timeline input formats](authoring-timelines.md#timeline-input-formats)
- <a id="coordinated-acting-and-continuity"></a> [Coordinated acting and continuity](authoring-acting.md#coordinated-acting-and-continuity)
- <a id="opt-in-acting-transition-policies"></a> [Opt-in acting transition policies](authoring-acting.md#opt-in-acting-transition-policies)
- <a id="sustained-listening-and-repairable-capability-failures"></a> [Sustained listening and repairable capability failures](authoring-acting.md#sustained-listening-and-repairable-capability-failures)
- <a id="carrying-a-prop-across-a-cut"></a> [Carrying a prop across a cut](authoring-acting.md#carrying-a-prop-across-a-cut)
- <a id="styles"></a> [Styles](authoring-styles.md#styles)
- <a id="lip-sync"></a> [Lip sync](authoring-styles.md#lip-sync)
- <a id="engine-native-captions-transitions-effects-and-text-animators"></a> [Engine-native captions, transitions, effects and text animators](authoring-styles.md#engine-native-captions-transitions-effects-and-text-animators)
- <a id="the-parts"></a> [The parts](authoring-parts.md#the-parts)
- <a id="extending"></a> [Extending](authoring-discovery.md#extending)
- <a id="agent-contracts"></a> [Agent contracts](authoring-discovery.md#agent-contracts)
- <a id="non-character-discovery-and-drawing-anchors"></a> [Non-character discovery and drawing anchors](authoring-discovery.md#non-character-discovery-and-drawing-anchors)
- <a id="character-clips-one-placement-and-timing-boundary"></a> [Character clips: one placement and timing boundary](authoring-clips.md#character-clips-one-placement-and-timing-boundary)
- <a id="plate-cache-ownership"></a> [Plate cache ownership](authoring-clips.md#plate-cache-ownership)
- <a id="extending-drawing-calls"></a> [Extending drawing calls](authoring-extensions.md#extending-drawing-calls)
- <a id="finishing-a-style-srstudiolook"></a> [Finishing a style: `srstudio.look`](authoring-styles.md#finishing-a-style-srstudiolook)
- <a id="staging-and-series-srstudiostaging-srstudioseries"></a> [Staging and series: `srstudio.staging`, `srstudio.series`](authoring-styles.md#staging-and-series-srstudiostaging-srstudioseries)
- <a id="google-fonts"></a> [Google Fonts](authoring-styles.md#google-fonts)
- <a id="cast-cards-srstudiocast_card"></a> [Cast cards: `srstudio.cast_card`](authoring-styles.md#cast-cards-srstudiocast_card)
- <a id="new-episodes-with-generated-audio-five-years-06"></a> [New episodes with generated audio: *Five Years* (06)](episode-history.md#new-episodes-with-generated-audio-five-years-06)
- <a id="cutout-episode-with-generated-audio-tip-screen-12"></a> [Cutout episode with generated audio: *Tip Screen* (12)](episode-history.md#cutout-episode-with-generated-audio-tip-screen-12)
- <a id="cutout-crossover-in-the-park-culture-fit-14"></a> [Cutout crossover in the park: *Culture Fit* (14)](episode-history.md#cutout-crossover-in-the-park-culture-fit-14)
- <a id="cutout-episode-in-the-conference-room-market-rate-16"></a> [Cutout episode in the conference room: *Market Rate* (16)](episode-history.md#cutout-episode-in-the-conference-room-market-rate-16)
- <a id="cutout-episode-in-the-elevator-elevator-pitch-18"></a> [Cutout episode in the elevator: *Elevator Pitch* (18)](episode-history.md#cutout-episode-in-the-elevator-elevator-pitch-18)
- <a id="cutout-crossover-finale-going-down-20"></a> [Cutout crossover finale: *Going Down* (20)](episode-history.md#cutout-crossover-finale-going-down-20)
- <a id="cutout-episode-at-the-café-counter-cup-fee-22"></a> [Cutout episode at the café counter: *Cup Fee* (22)](episode-history.md#cutout-episode-at-the-café-counter-cup-fee-22)
- <a id="cutout-episode-on-the-park-bench-storage-full-23"></a> [Cutout episode on the park bench: *Storage Full* (23)](episode-history.md#cutout-episode-on-the-park-bench-storage-full-23)
- <a id="cutout-episode-across-the-interview-desk-name-a-number-24"></a> [Cutout episode across the interview desk: *Name a Number* (24)](episode-history.md#cutout-episode-across-the-interview-desk-name-a-number-24)
- <a id="interview-episodes-with-a-google-caption-face"></a> [Interview episodes with a Google caption face](episode-history.md#interview-episodes-with-a-google-caption-face)
- <a id="cutout-episode-in-the-elevator-neighbor-names-25"></a> [Cutout episode in the elevator: *Neighbor Names* (25)](episode-history.md#cutout-episode-in-the-elevator-neighbor-names-25)
- <a id="cutout-episode-at-the-home-printer-out-of-cyan-26"></a> [Cutout episode at the home printer: *Out of Cyan* (26)](episode-history.md#cutout-episode-at-the-home-printer-out-of-cyan-26)
- <a id="cutout-episode-in-the-break-room-im-quitting-27"></a> [Cutout episode in the break room: *I'm Quitting* (27)](episode-history.md#cutout-episode-in-the-break-room-im-quitting-27)
- <a id="cutout-episode-in-the-hiring-office-entry-level-28"></a> [Cutout episode in the hiring office: *Entry Level* (28)](episode-history.md#cutout-episode-in-the-hiring-office-entry-level-28)
- <a id="cutout-episode-at-the-barbers-just-a-trim-29"></a> [Cutout episode at the barber's: *Just a Trim* (29)](episode-history.md#cutout-episode-at-the-barbers-just-a-trim-29)
- <a id="cutout-episode-at-the-store-just-one-thing-30"></a> [Cutout episode at the store: *Just One Thing* (30)](episode-history.md#cutout-episode-at-the-store-just-one-thing-30)
- <a id="ink-episode-the-router-ink-02"></a> [Ink episode: *The Router* (Ink 02)](episode-history.md#ink-episode-the-router-ink-02)
- <a id="ink-episode-not-a-robot-ink-03"></a> [Ink episode: *Not a Robot* (Ink 03)](episode-history.md#ink-episode-not-a-robot-ink-03)
- <a id="ink-episode-message-failed-ink-04"></a> [Ink episode: *Message Failed* (Ink 04)](episode-history.md#ink-episode-message-failed-ink-04)
- <a id="ink-episode-u-up-ink-05"></a> [Ink episode: *U Up?* (Ink 05)](episode-history.md#ink-episode-u-up-ink-05)
- <a id="ink-episode-premium-suction-ink-06"></a> [Ink episode: *Premium Suction* (Ink 06)](episode-history.md#ink-episode-premium-suction-ink-06)
- <a id="ink-episode-home-sick-ink-07"></a> [Ink episode: *Home Sick* (Ink 07)](episode-history.md#ink-episode-home-sick-ink-07)
- <a id="ink-episode-pay-to-park-ink-08"></a> [Ink episode: *Pay to Park* (Ink 08)](episode-history.md#ink-episode-pay-to-park-ink-08)
- <a id="soft-style-episode-focus-mode-07"></a> [Soft style episode: *Focus Mode* (07)](episode-history.md#soft-style-episode-focus-mode-07)
- <a id="soft-style-episode-camera-off-08"></a> [Soft style episode: *Camera Off* (08)](episode-history.md#soft-style-episode-camera-off-08)
- <a id="soft-style-episode-day-off-11"></a> [Soft style episode: *Day Off* (11)](episode-history.md#soft-style-episode-day-off-11)
- <a id="soft-style-episode-unlimited-pto-13"></a> [Soft style episode: *Unlimited PTO* (13)](episode-history.md#soft-style-episode-unlimited-pto-13)
- <a id="soft-style-episode-return-to-office-15"></a> [Soft style episode: *Return to Office* (15)](episode-history.md#soft-style-episode-return-to-office-15)
- <a id="soft-style-episode-smart-lamp-17"></a> [Soft style episode: *Smart Lamp* (17)](episode-history.md#soft-style-episode-smart-lamp-17)
- <a id="soft-style-episode-the-cake-19"></a> [Soft style episode: *The Cake* (19)](episode-history.md#soft-style-episode-the-cake-19)
- <a id="soft-style-episode-hang-out"></a> [Soft style episode: *Hang Out*](episode-history.md#soft-style-episode-hang-out)
- <a id="soft-style-episode-early-night"></a> [Soft style episode: *Early Night*](episode-history.md#soft-style-episode-early-night)
- <a id="soft-style-episode-why"></a> [Soft style episode: *Why*](episode-history.md#soft-style-episode-why)
- <a id="cel-style-package-work-training-be-like"></a> [Cel style package: *Work Training Be Like*](episode-history.md#cel-style-package-work-training-be-like)
- <a id="narrated-master"></a> [Narrated master](episode-history.md#narrated-master)
- <a id="stick-style-package-check-with-my-team"></a> [Stick style package: *Check With My Team*](episode-history.md#stick-style-package-check-with-my-team)
- <a id="an-original-stick-episode-screen-share-r2"></a> [An original Stick episode: *Screen Share* (R2)](episode-history.md#an-original-stick-episode-screen-share-r2)
- <a id="an-original-stick-episode-in-a-car-repeat-after-me-r3"></a> [An original Stick episode in a car: *Repeat After Me* (R3)](episode-history.md#an-original-stick-episode-in-a-car-repeat-after-me-r3)
- <a id="an-original-stick-episode-at-the-store-unexpected-item-r4"></a> [An original Stick episode at the store: *Unexpected Item* (R4)](episode-history.md#an-original-stick-episode-at-the-store-unexpected-item-r4)
- <a id="an-original-stick-episode-in-a-flat-for-rent-the-viewing-r5"></a> [An original Stick episode in a flat for rent: *The Viewing* (R5)](episode-history.md#an-original-stick-episode-in-a-flat-for-rent-the-viewing-r5)
- <a id="an-original-stick-episode-at-the-gym-cancel-anytime-r6"></a> [An original Stick episode at the gym: *Cancel Anytime* (R6)](episode-history.md#an-original-stick-episode-at-the-gym-cancel-anytime-r6)
- <a id="an-original-stick-episode-at-school-what-my-dad-does-r7"></a> [An original Stick episode at school: *What My Dad Does* (R7)](episode-history.md#an-original-stick-episode-at-school-what-my-dad-does-r7)
- <a id="an-original-stick-episode-at-the-airport-group-9-r8"></a> [An original Stick episode at the airport: *Group 9* (R8)](episode-history.md#an-original-stick-episode-at-the-airport-group-9-r8)
- <a id="an-original-stick-episode-in-the-car-the-exit-r9"></a> [An original Stick episode in the car: *The Exit* (R9)](episode-history.md#an-original-stick-episode-in-the-car-the-exit-r9)
- <a id="an-original-stick-episode-at-a-door-hold-the-door-r10"></a> [An original Stick episode at a door: *Hold the Door* (R10)](episode-history.md#an-original-stick-episode-at-a-door-hold-the-door-r10)
- <a id="an-original-stick-episode-in-a-kitchen-take-my-phone-r11"></a> [An original Stick episode in a kitchen: *Take My Phone* (R11)](episode-history.md#an-original-stick-episode-in-a-kitchen-take-my-phone-r11)
- <a id="an-original-stick-episode-at-the-coffee-machine-good-you-r12"></a> [An original Stick episode at the coffee machine: *Good, You* (R12)](episode-history.md#an-original-stick-episode-at-the-coffee-machine-good-you-r12)
- <a id="an-original-stick-episode-on-the-road-the-stove-r13"></a> [An original Stick episode on the road: *The Stove* (R13)](episode-history.md#an-original-stick-episode-on-the-road-the-stove-r13)
- <a id="toon-style-package-anonymous-employee-survey"></a> [Toon style package: *Anonymous Employee Survey*](episode-history.md#toon-style-package-anonymous-employee-survey)
- <a id="narrated-master-1"></a> [Narrated master](episode-history.md#narrated-master-1)
- <a id="toon-coworkers-brush-drawn-characters"></a> [Toon coworkers: brush-drawn characters](authoring-parts.md#toon-coworkers-brush-drawn-characters)
- <a id="part-versions"></a> [Part versions](authoring-parts.md#part-versions)
- <a id="toon-sketches-the-report-t3-logo-bigger-t4-and-quick-question-t5"></a> [Toon sketches: *The Report* (T3), *Logo Bigger* (T4) and *Quick Question* (T5)](episode-history.md#toon-sketches-the-report-t3-logo-bigger-t4-and-quick-question-t5)
- <a id="toon-dinner-the-restaurant-the-table-the-dishes-and-the-card-reader"></a> [Toon dinner: the restaurant, the table, the dishes and the card reader](episode-history.md#toon-dinner-the-restaurant-the-table-the-dishes-and-the-card-reader)
- <a id="toon-sets-the-office-kitchen-and-the-home-office-at-night"></a> [Toon sets: the office kitchen and the home office at night](episode-history.md#toon-sets-the-office-kitchen-and-the-home-office-at-night)
- <a id="toon-rooms-a-living-room-at-night-and-a-service-counter-lit-over-time"></a> [Toon rooms: a living room at night and a service counter, lit over time](episode-history.md#toon-rooms-a-living-room-at-night-and-a-service-counter-lit-over-time)
- <a id="toon-everyday-props-the-phone-the-speaker-the-receipt-the-queue-and-the-form"></a> [Toon everyday props: the phone, the speaker, the receipt, the queue and the form](episode-history.md#toon-everyday-props-the-phone-the-speaker-the-receipt-the-queue-and-the-form)
- <a id="saga-style-a-space-opera-parody-in-seven-episodes-s1s7"></a> [Saga style: a space-opera parody in seven episodes (S1–S7)](episode-history.md#saga-style-a-space-opera-parody-in-seven-episodes-s1s7)
- <a id="gloss-style-a-cheerful-forever-plaza-in-nine-episodes-g1g9"></a> [Gloss style: a cheerful forever-plaza in nine episodes (G1–G9)](episode-history.md#gloss-style-a-cheerful-forever-plaza-in-nine-episodes-g1g9)
- <a id="collage-style-grown-ups-losing-to-brainrot"></a> [Collage style: grown-ups losing to brainrot](episode-history.md#collage-style-grown-ups-losing-to-brainrot)
- <a id="signature"></a> [Signature](authoring-delivery.md#signature)
- <a id="instagram-captions"></a> [Instagram captions](authoring-delivery.md#instagram-captions)
- <a id="the-okayville-show-signature"></a> [The Okayville show signature](authoring-delivery.md#the-okayville-show-signature)
- <a id="strict-findings-at-first-delivery"></a> [Strict findings at first delivery](authoring-delivery.md#strict-findings-at-first-delivery)
- <a id="verification"></a> [Verification](authoring-verification.md#verification)
