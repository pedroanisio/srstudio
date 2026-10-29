#!/usr/bin/env python3
"""The Instagram post of every episode, as data, and the publish gate of the rendered videos.

Each episode script calls ``ep.instagram(POSTS[slug])`` so a build leaves ``ig.txt`` next to its scene. Each post
also designs its cover: a :class:`~srstudio.thumbnail.Thumbnail` drawn over a frame of the video. ``deliver``
writes one ``<out>/<video name>/`` folder per rendered video, holding ``ig.txt`` and ``cover.jpg``, for every video
that drifted, and records ``<out>/delivery.json``; ``check`` exits 1 and lists every drift (a video re-rendered after
its cover, a changed post, an edited or missing file, a post without a render) and writes nothing:

    python3 instagram_posts.py deliver OUT RENDERS --fonts DIR [--engine BIN] [--only NAME ...]
    python3 instagram_posts.py check OUT RENDERS --fonts DIR

``--only`` delivers the named videos alone (one ready to publish while another post waits for its render); the
rest of the delivery is left as it was, and ``check`` still reports what drifted there.

The headline font (:data:`THUMBNAIL_FONT`) is installed into ``--fonts`` and pinned there; once it is in place
nothing is downloaded. ``--engine`` defaults to ``$SRSTUDIO_ENGINE``, then ``scene-render`` on the ``PATH``.
"""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

from srstudio import fonts
from srstudio.social import DeliveryError, Drift, InstagramPost, Item, check_delivery, publish
from srstudio.thumbnail import Thumbnail

THUMBNAIL_FONT = fonts.GoogleFont("Anton", 400)  # a condensed display face: two big lines fit a portrait cover

VOICES = "Voices: ElevenLabs premade voices Eric and Will."
SERIES = ("#TheInterview", "#officehumor", "#jobinterview", "#workcomedy", "#animatedshorts", "#vectoranimation")

POSTS: dict[str, InstagramPost] = {
    "honesty-interview": InstagramPost(
        title="Greatest weakness? Honesty.",
        description=(
            "Episode 01 of The Interview. The candidate is asked for a weakness and gives the one answer the manager "
            "cannot argue with, twice.\n"
            "Contains one strong word."
        ),
        credit=VOICES,
        hashtags=SERIES + ("#honesty", "#interviewfail"),
        thumbnail=Thumbnail("Greatest weakness?\nHonesty.", 2.4, "The Interview · 01", (540, 690), 1.4),
    ),
    "pressure-interview": InstagramPost(
        title="How do you handle pressure?",
        description=(
            "Episode 02 of The Interview. A perfectly honest answer about pressure, and a manager who realises too "
            "late that they were talking about the same thing."
        ),
        credit=VOICES,
        hashtags=SERIES + ("#notifications", "#worklifebalance"),
        thumbnail=Thumbnail("How do you handle\npressure?", 6.0, "The Interview · 02", (540, 700), 1.4),
    ),
    "fast-at-math": InstagramPost(
        title="17 × 19? Forty-two. But it was fast.",
        description=(
            "Episode 03 of The Interview. Greatest strength: speed. Accuracy was not on the list. Hand gestures, a "
            "facepalm and a scorecard that keeps the receipts."
        ),
        credit=VOICES + " Original sound effects.",
        hashtags=SERIES + ("#mathjokes", "#fastnotright"),
        thumbnail=Thumbnail("17 × 19?\nForty-two.", 5.4, "The Interview · 03", (600, 520), 1.15),
    ),
    "multitasking": InstagramPost(
        title="Are you good at multitasking? Absolutely.",
        description=(
            "Episode 04 of The Interview. Asked for an example, the candidate names the one task they can run in "
            "parallel without dropping anything. Status pings included."
        ),
        credit=VOICES,
        hashtags=SERIES + ("#multitasking", "#disappointment"),
        thumbnail=Thumbnail("Good at\nmultitasking?", 5.0, "The Interview · 04", (540, 520), 1.1),
    ),
    "wifi-password": InstagramPost(
        title="The Wi-Fi password is a sales tactic.",
        description=(
            "Comedy Cut 05, new cast: Ava the barista, Milo the customer and one park pigeon. The password is exactly "
            "what she said. No spaces. Five bucks well spent on a spelling lesson."
        ),
        credit="Voices: ElevenLabs premade voices Jessica and Liam. Procedural café and park sound effects.",
        hashtags=(
            "#TheInterview",
            "#cafehumor",
            "#wifipassword",
            "#baristalife",
            "#workcomedy",
            "#animatedshorts",
            "#vectoranimation",
            "#pigeon",
        ),
        thumbnail=Thumbnail("What's the\nWi-Fi password?", 9.0, "Comedy Cut 05", (540, 560), 1.2),
    ),
    "scene": InstagramPost(  # printer-recreation: the project slug of the square cartoon
        title="The printer was fine this morning.",
        description=(
            "A printer that makes startup noises instead of printing, and knows exactly when you are in a hurry.\n"
            "This is a procedural, hand-built vector recreation of Mark Kacy's printer cartoon, with newly "
            "synthesized performances. Original idea, writing and design: Mark Kacy."
        ),
        credit="Recreation of a cartoon by Mark Kacy. Voices: ElevenLabs premade voices Chris and Callum.",
        hashtags=(
            "#printerproblems",
            "#officehumor",
            "#cartoon",
            "#handdrawn",
            "#animatedshorts",
            "#recreation",
            "#markkacy",
            "#workcomedy",
        ),
        thumbnail=Thumbnail("Use the\nblack ink!", 37.0, "Printer", place="top"),
    ),
    "five-years": InstagramPost(
        title="Where do you see yourself in five years?",
        description=(
            "Episode 06 of The Interview. The candidate has a plan. It does not involve the job. It does involve the "
            "chair, which squeaks, and which gets taken for a spin before the credits."
        ),
        credit=VOICES + " Sound effects generated with ElevenLabs.",
        hashtags=SERIES + ("#fiveyearplan", "#executivechair"),
        thumbnail=Thumbnail("Where do you see\nyourself in 5 years?", 10.4, "The Interview · 06", (540, 560), 1.2),
    ),
    "upside-down": InstagramPost(
        title="When the Q3 numbers are bad, check the board.",
        description=(
            "Episode 07 of The Interview. The candidate got a job after all: reception. Upstairs the boss presents "
            "a chart going down, until the speakerphone points out the board is upside down. Record quarter! "
            "Bonuses for everyone! Including reception? Flip.\n"
            "Episode 09, in the new polished reception and conference room."
        ),
        credit="Voices: ElevenLabs premade voices Eric, Will and Liam. Sound effects generated with ElevenLabs.",
        hashtags=SERIES + ("#quarterlyreview", "#bonus"),
        thumbnail=Thumbnail("Check\nthe board.", 19.2, "The Interview · 09", (700, 760), 1.25),
    ),
    "the-router": InstagramPost(
        title="Have you tried turning me off and on again?",
        description=(
            "The internet is down and the router knows exactly how to fix it. It just would rather you did it.\n"
            "Ink 02: the second square cartoon, an original talking appliance this time."
        ),
        credit="Voices: ElevenLabs premade voices Chris and Daniel. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#routerproblems",
            "#officehumor",
            "#itsupport",
            "#turnitoffandonagain",
            "#handdrawn",
            "#animatedshorts",
            "#workcomedy",
        ),
        thumbnail=Thumbnail("Off and\non again?", 11.0, "Ink 02", place="top"),
    ),
    "mushroom-training": InstagramPost(
        title="Work training be like.",
        description=(
            "This module will take 45 minutes to complete, and there will be a test at the end. A mushroom sits "
            "through all of it.\n"
            "Recreation of the Under Studio training cartoon in the Cel style: traced drawings, a measured camera "
            "push, hand-lettered captions and a new synthesized narration. Character art, dialogue and lettering "
            "are adapted from the reference; the original creator retains rights."
        ),
        credit="Narration: ElevenLabs premade voice Alice. Reference: understudiohub / Under Studio.",
        hashtags=(
            "#worktraining",
            "#officehumor",
            "#onboarding",
            "#compliancetraining",
            "#workcomedy",
            "#animatedshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Work training\nbe like", 36.0, "Workplace module", (540, 700), 1.3),
    ),
    "focus-mode": InstagramPost(
        title="Focus. The deadline is... oh.",
        description=(
            "Pip sits down to work, types for one bar, and the groove wins. A record scratch: the deadline. Focus. "
            "Then he checks the date.\n"
            "Episode 07, the first in the Soft style: every pose lands on the beat."
        ),
        credit="Voice: ElevenLabs premade voice Will. Music composed with ElevenLabs Music.",
        hashtags=(
            "#focusmode",
            "#deadline",
            "#procrastination",
            "#officehumor",
            "#workcomedy",
            "#animatedshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Shake it\nto the beat!", 10.0, "Episode 07", (620, 1000), 1.3),
    ),
    "camera-off": InstagramPost(
        title="Camera off. Pajamas on the beat.",
        description=(
            "Pip is very professional on the call. Then the boss announces forty slides, the camera goes off and "
            "the dancing starts, until someone asks him to share his screen.\n"
            "Episode 08, the second in the Soft style: every pose lands on the beat."
        ),
        credit=(
            "Song composed and sung with the ElevenLabs Music API. Boss: ElevenLabs premade voice Eric. "
            "Sound effects generated with ElevenLabs."
        ),
        hashtags=(
            "#cameraoff",
            "#zoommeeting",
            "#workfromhome",
            "#remotework",
            "#officehumor",
            "#workcomedy",
            "#animatedshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Camera off.\nPajamas on.", 10.0, "Episode 08", (560, 1000), 1.25),
    ),
    "off-and-on": InstagramPost(
        title="IT support has one fix. It's a jingle.",
        description=(
            "The coffee machine is broken: turn it off and on again. Pip is broken: lights off, lights on, and now "
            "he loves Mondays. Then Remy's own screen dies, and the IT hotline knows exactly what to say.\n"
            "Episode 10, the third in the Soft style, with Juno and Remy in the new meeting room and break room."
        ),
        credit=(
            "Music and Remy's vocal composed with the ElevenLabs Music API. Voices: ElevenLabs premade voices Laura "
            "(Juno), Will (Pip) and Charlie (IT hotline). Sound effects generated with ElevenLabs."
        ),
        hashtags=(
            "#itsupport",
            "#turnitoffandonagain",
            "#mondays",
            "#officehumor",
            "#workcomedy",
            "#animatedshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Somebody\nreboot me.", 29.5, "Episode 10", (600, 1000), 1.2),
    ),
    "day-off": InstagramPost(
        title="Saturday. No work. Just me.",
        description=(
            "Pip finally has a day off. His hands keep typing on nothing, he agrees with the lamp, and he can stop "
            "any time. The only way he can rest is to book it: a meeting with the sofa.\n"
            "Episode 11, the fourth in the Soft style: every pose lands on the beat."
        ),
        credit=(
            "Pip: ElevenLabs premade voice Will. Music composed with ElevenLabs Music. "
            "Sound effects generated with ElevenLabs."
        ),
        hashtags=(
            "#dayoff",
            "#weekendvibes",
            "#burnout",
            "#workaholic",
            "#officehumor",
            "#workcomedy",
            "#animatedshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Day off?\nBook it.", 19.6, "Soft 04", (600, 1000), 1.25),
    ),
    "employee-survey": InstagramPost(
        title="Anonymous employee survey.",
        description=(
            "Would you recommend working for this company? Not a chance in hell. Then the survey asks for a "
            "department, a job title, a start date and a seat on the office map.\n"
            "Recreation of the.nope.cat's survey reel in the Toon style: a flat cartoon cat whose expression swaps "
            "per line, each phrase in a white pill, and a new synthesised narration. Character, dialogue and "
            "captions are adapted from the reference; the original creator retains rights."
        ),
        credit="Narration: ElevenLabs premade voice Brian. Reference: the.nope.cat.",
        hashtags=(
            "#employeesurvey",
            "#anonymous",
            "#officehumor",
            "#workcomedy",
            "#catsofinstagram",
            "#animatedshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Anonymous\nsurvey?", 37.0, "Employee survey", (480, 1050), 1.3),
    ),
    "check-with-my-team": InstagramPost(
        title="POV: you gotta check with your team first.",
        description=(
            "Let me just check with my team real quick and get back to you. The team turns out to be one person and "
            "three AI assistants, dancing in a garden. Three hours later, the verdict is in.\n"
            "Recreation of @theaifilmmaker's cartoon in the Stick style: traced stick figures on painted sets, "
            "outlined captions, a new synthesised voice-over and music at the dance's tempo. Character art, dialogue "
            "and lettering are adapted from the reference, and the original creator retains rights; the card and the "
            "closing line are new."
        ),
        credit="Voice-over: ElevenLabs premade voice Chris. Music composed with ElevenLabs Music. "
        "Reference: @theaifilmmaker.",
        hashtags=(
            "#checkwithmyteam",
            "#officehumor",
            "#aitools",
            "#workcomedy",
            "#stickfigure",
            "#animatedshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Let me check\nwith my team", 0.8, "POV", (430, 900), 1.3),
    ),
    "screen-share": InstagramPost(
        title="Can everyone see my screen?",
        description=(
            "Yes. And the inbox. All of it. Three beats of a remote workday: a shared screen that shows too much, a "
            "meeting that runs over meets a very bad connection, and a Friday 4:59 PM \"got a sec?\".\n"
            "Stick 02, the first original episode in the Stick style: drawn stick figures, a call screen and a boss "
            "who walks in."
        ),
        credit="Voices: ElevenLabs premade voices Eric and Will. Sound effect generated with ElevenLabs.",
        hashtags=(
            "#screenshare",
            "#remotework",
            "#zoommeeting",
            "#officehumor",
            "#workcomedy",
            "#stickfigure",
            "#animatedshorts",
        ),
        thumbnail=Thumbnail("Can everyone\nsee my screen?", 2.2, "Stick 02", (380, 900), 2.2),
    ),
    "repeat-after-me": InstagramPost(
        title="Repeat after me.",
        description=(
            "I will not check my email on the drive home. I will leave work at work. Say it twice, say it firmer, "
            "and whatever you do, don't look at the passenger seat.\n"
            "Stick 03: Dev's vows on the commute, a car drawn in code with the road passing in the window, and the "
            "captions one word at a time."
        ),
        credit="Voice: ElevenLabs premade voice Will. Sound effect and instrumental music composed with ElevenLabs.",
        hashtags=(
            "#workfromcar",
            "#worklifebalance",
            "#afterhours",
            "#officehumor",
            "#workcomedy",
            "#stickfigure",
            "#animatedshorts",
        ),
        thumbnail=Thumbnail("Repeat\nafter me.", 10.8, "Stick 03", (540, 1200), 1.3),
    ),
    "cancel-anytime": InstagramPost(
        title="How do I cancel my gym membership?",
        description=(
            "Cancel anytime, says the sign. In person: he's here. On a Tuesday: it's Tuesday. Before sunrise: it's "
            "still dark. With a note from the trainer he has never met. Any other way? A death certificate. Whose? "
            "They're flexible.\n"
            "A stick-figure cartoon voiced with ElevenLabs premade voices Callum and Jessica."
        ),
        credit="Voices: ElevenLabs premade voices Callum and Jessica. Instrumental music composed with ElevenLabs "
        "Music.",
        hashtags=(
            "#gymmembership",
            "#cancelanytime",
            "#fineprint",
            "#subscriptions",
            "#animatedshorts",
            "#stickfigure",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Cancel\nanytime*", 1.0, "Stick 06", (540, 1200), 1.3),
    ),
    "what-my-dad-does": InstagramPost(
        title="Have you read what your kid wrote about you?",
        description=(
            "Parent-teacher night, on a chair built for an eight-year-old. The essay: What My Dad Does. He works "
            "from home, in a tie and no pants. His job is saying \"I think you're on mute\". At three he has Focus "
            "Time, and Focus Time snores. Last line: Dad says he works from home. Mom says he's just home.\n"
            "Stick 07: a classroom, a tiny chair and an essay page drawn in code, the captions one word at a time."
        ),
        credit="Voices: ElevenLabs premade voices Will and Sarah. Sound effect and instrumental music composed with "
        "ElevenLabs.",
        hashtags=(
            "#workfromhome",
            "#parentteacher",
            "#parentinghumor",
            "#remotework",
            "#animatedshorts",
            "#stickfigure",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("What my\ndad does", 18.6, "Stick 07", place="top"),
    ),
    "elevator-pitch": InstagramPost(
        title="Working from home? Elevator pitch. You've got till my floor.",
        description=(
            "He pitches it: more productive, no commute, no meetings. Floor 4, the doors open, and in walks Kevin, "
            "the pigeon the boss hired on his lunch break. Kevin is fully remote. He flies in on Tuesdays. He "
            "negotiated; you took a title. Floor 9: Kevin, your call.\n"
            "Comedy Cut 18: the boss, the employee from Market Rate and the pigeon from Culture Fit, in a new elevator."
        ),
        credit="Voices: ElevenLabs premade voices Will and Eric. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#workfromhome",
            "#returntooffice",
            "#elevatorpitch",
            "#officehumor",
            "#animatedshorts",
            "#cartoon",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Elevator\npitch", 8.6, "Comedy Cut 18", place="top"),
    ),
    "the-cake": InstagramPost(
        title="Ten bucks for the cake?",
        description=(
            "Juno collects ten bucks from Pip for a cake. Not a birthday: someone is leaving. Bo arrives with it, "
            "delighted. The company saved a whole salary. The cake says WE'LL MISS YOU. Then Bo turns it round.\n"
            "Comedy Cut 19: Pip, Juno and Bo in the break room, pose to pose on a 120 bpm beat."
        ),
        credit="Voices: ElevenLabs premade voices Laura (Juno), Will (Pip) and Eric (Bo). Music composed with "
        "ElevenLabs Music. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#officehumor",
            "#layoffs",
            "#corporatelife",
            "#workhumor",
            "#animatedshorts",
            "#comedyshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("We'll miss\nyou, Pip", 17.2, "Comedy Cut 19", place="top"),
    ),
    "split-it": InstagramPost(
        title="Should we just split it evenly?",
        description=(
            "Mia had a side salad. Brock had the lobster; same thing, basically. Three lobsters, and the wine was for "
            "the table. Then his card is declined, and he promises to send his half tonight.\n"
            "Toon 10: Brock and Mia at the bistro, a new restaurant set, table and card reader."
        ),
        credit="Voices: ElevenLabs premade voices Roger (Brock) and River (Mia). Buzz and sting synthesised.",
        hashtags=(
            "#splitthebill",
            "#datenight",
            "#friendshumor",
            "#moneyhumor",
            "#animatedshorts",
            "#comedyshorts",
            "#cartoon",
        ),
        thumbnail=Thumbnail("Split it\nevenly?", 1.2, "Toon 10", (470, 1130), 1.35),
    ),
    "home-sick": InstagramPost(
        title="Why won't you open the door?",
        description=(
            "Your video doorbell won't let you in: the resident is home sick today. You got better? Then you're late "
            "for work. So it asks the street's group chat who you are, from your account. Your boss lives on the "
            "street.\n"
            "A square pen-and-ink cartoon voiced with ElevenLabs premade voices Chris and George."
        ),
        credit="Voices: ElevenLabs premade voices Chris and George. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#sickday",
            "#smarthome",
            "#neighbors",
            "#officehumor",
            "#animatedshorts",
            "#inkdrawing",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("The resident\nis home sick.", 4.0, "Ink 07", place="top"),
    ),
    "group-nine": InstagramPost(
        title="Is Group 9 boarding yet?",
        description=(
            "Group 9 boards after the luggage. Your bag is Group 4, and it's doing great. Group 8 costs extra: same "
            "seat, you just board feeling chosen. The plane can't leave without you? Everyone says that.\n"
            "Stick 08: a boarding gate, a podium, a carry-on and a cabin row drawn in code, the captions one word at "
            "a time."
        ),
        credit="Voices: ElevenLabs premade voices Liam and Matilda. Sound effect and instrumental music composed with "
        "ElevenLabs.",
        hashtags=(
            "#travelhumor",
            "#airlines",
            "#boardinggroup",
            "#officehumor",
            "#animatedshorts",
            "#stickfigure",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Is Group 9\nboarding yet?", 1.0, "Stick 08", place="top"),
    ),
    "going-down": InstagramPost(
        title="Am I being fired?",
        description=(
            "No. Your role is being sunset. You're going fully remote: from your couch, forever. Floor 4, the doors "
            "open, and Kevin, the pigeon who is now Head of People, flies in for this, with a pink slip in his beak. "
            "He drops it. It's not for you.\n"
            "Comedy Cut 20, the office finale: the boss, the employee from Market Rate and Elevator Pitch, and the "
            "pigeon from Culture Fit, back on the bench where it all began."
        ),
        credit="Voices: ElevenLabs premade voices Will and Eric. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#layoffs",
            "#corporatespeak",
            "#officehumor",
            "#remotework",
            "#animatedshorts",
            "#cartoon",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Am I being\nfired?", 1.0, "Comedy Cut 20", place="top"),
    ),
    "unexpected-item": InstagramPost(
        title="Unexpected item in the bagging area.",
        description=(
            "One avocado. The machine wanted it in the bagging area, then out of it, then back in it, then called "
            "for help. Two hundred items scanned and bagged this month, three jams fixed: congratulations, you're "
            "employee of the month.\n"
            "Stick 04: Dev at the self-checkout, a store and a kiosk drawn in code, the captions one word at a time."
        ),
        credit="Voices: ElevenLabs premade voices Laura, Will and Alice. Sound effect and instrumental music composed "
        "with ElevenLabs.",
        hashtags=(
            "#selfcheckout",
            "#unexpecteditem",
            "#grocerystore",
            "#adulting",
            "#workcomedy",
            "#stickfigure",
            "#animatedshorts",
        ),
        thumbnail=Thumbnail("Employee of\nthe month.", 24.3, "Stick 04", (540, 1200), 1.3),
    ),
    "tip-screen": InstagramPost(
        title="How would you like to tip me for ordering?",
        description=(
            "A black coffee, poured from a pot, with intention. Then the tablet swivels: 20%, 25%, 30%. So Milo "
            "brought a tablet of his own.\n"
            "Comedy Cut 12: Ava and Milo from The Wi-Fi Password, back in the café, tapping until closing time."
        ),
        credit="Voices: ElevenLabs premade voices Liam and Jessica. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#tipping",
            "#tipscreen",
            "#coffeeshop",
            "#adulting",
            "#officehumor",
            "#animatedshorts",
            "#comedyshorts",
        ),
        thumbnail=Thumbnail("Tip me for\nordering?", 12.0, "Episode 12", place="top"),
    ),
    "culture-fit": InstagramPost(
        title="Where do you see yourself in five years?",
        description=(
            "Job hunt, day 200: two hundred applications, not one reply. Then the boss sits down on the same bench "
            "for lunch, and a pigeon lands at his feet. The pigeon interviews well.\n"
            "Comedy Cut 14: Milo from The Wi-Fi Password meets the boss from The Interview, in the park."
        ),
        credit="Voices: ElevenLabs premade voices Liam and Eric. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#jobhunting",
            "#jobsearch",
            "#hiring",
            "#adulting",
            "#officehumor",
            "#animatedshorts",
            "#comedyshorts",
        ),
        thumbnail=Thumbnail("He works\nfor crumbs.", 17.75, "Episode 14", (560, 820), 1.1, place="bottom"),
    ),
    "market-rate": InstagramPost(
        title="Can we talk about my salary?",
        description=(
            "He got the job. Now he asks the boss for a raise, on the conference-room speakerphone. Record year! So, "
            "a raise? Better: a title. Then he finds his own job posted online, paying more. That's for external "
            "talent.\n"
            "Comedy Cut 16: the candidate from The Interview, a year in."
        ),
        credit="Voices: ElevenLabs premade voices Will and Eric. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#salary",
            "#payraise",
            "#corporatelife",
            "#officehumor",
            "#workhumor",
            "#animatedshorts",
            "#comedyshorts",
        ),
        thumbnail=Thumbnail("Asking for\na raise.", 9.0, "Episode 16", (540, 900), 1.3, place="bottom"),
    ),
    "smart-lamp": InstagramPost(
        title="You never listen to me.",
        description=(
            "Juno says Pip never listens. He always listens! The smart lamp disagrees: it has recordings. Then it "
            "orders flowers, with a card that says sorry. Then a ring.\n"
            "Comedy Cut 17: Pip, Juno and Mister Lamp from Day Off, pose to pose on a 120 bpm beat."
        ),
        credit="Voices: ElevenLabs premade voices Laura (Juno), Will (Pip) and Matilda (the lamp). Music composed with "
        "ElevenLabs Music. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#smarthome",
            "#relationshiphumor",
            "#couplegoals",
            "#techhumor",
            "#animatedshorts",
            "#comedyshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("The lamp\nhas recordings.", 6.0, "Episode 17", (540, 900), 1.0),
    ),
    "return-to-office": InstagramPost(
        title="Two hours on a train. For this?",
        description=(
            "Day one of the return to office. Pip commutes two hours to an empty meeting room, and the boss "
            "welcomes the team back on the wall screen. From a beach. Leadership is hybrid.\n"
            "Comedy Cut 15: Pip and Bo, pose to pose on a 120 bpm beat."
        ),
        credit="Voices: ElevenLabs premade voices Will and Eric. Music composed with ElevenLabs Music. Sound effects "
        "generated with ElevenLabs.",
        hashtags=(
            "#returntooffice",
            "#rto",
            "#hybridwork",
            "#officehumor",
            "#corporatelife",
            "#animatedshorts",
            "#comedyshorts",
        ),
        thumbnail=Thumbnail("Someone has to\nbe the culture.", 19.2, "Episode 15", place="bottom"),
    ),
    "the-report": InstagramPost(
        title="Rex. It's on your forehead.",
        description=(
            "Fern wants the report. Rex has never heard of any report. The eleven reminders, the sticky notes and "
            "the one on his forehead say otherwise.\n"
            "A Toon two-hander voiced with ElevenLabs premade voices Charlie (Rex) and Matilda (Fern); original "
            "characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Charlie and Matilda. Original characters, drawn in code.",
        hashtags=(
            "#officehumor",
            "#workcomedy",
            "#thereport",
            "#animatedshorts",
            "#vectoranimation",
            "#cartoondog",
            "#cartoonfrog",
        ),
        thumbnail=Thumbnail("It's on your\nforehead.", 27.5, "Toon 03", (330, 1000), 1.4),
    ),
    "logo-bigger": InstagramPost(
        title="Can you make the logo bigger?",
        description=(
            "The client wants the logo bigger. Then bigger. Then the size of the building. Then it should pop. "
            "Then smaller. Rex sends the invoice.\n"
            "A Toon sketch voiced with ElevenLabs premade voices George (the client), Matilda (Fern) and Charlie "
            "(Rex); original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices George, Matilda and Charlie. Original characters, drawn in code.",
        hashtags=(
            "#makeitbigger",
            "#designerproblems",
            "#clientfeedback",
            "#officehumor",
            "#workcomedy",
            "#animatedshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Can you make\nit bigger?", 16.5, "Toon 04", (700, 950), 1.2),
    ),
    "quick-question": InstagramPost(
        title="Quick question. Got a sec?",
        description=(
            "Pip has a quick question. First, some context. It started in March. Then Dave left. Forty-six "
            "minutes later: when's the stand-up? Three minutes ago. It's on the board behind her.\n"
            "A Toon sketch voiced with ElevenLabs premade voices Alice (Pip) and Bill (Bruno), lip-synced to their "
            "words; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Alice and Bill. Original characters, drawn in code.",
        hashtags=(
            "#quickquestion",
            "#officehumor",
            "#workcomedy",
            "#standupmeeting",
            "#animatedshorts",
            "#vectoranimation",
            "#lipsync",
        ),
        thumbnail=Thumbnail("Quick question.\nGot a sec?", 1.0, "Toon 05", (340, 1050), 1.3),
    ),
    "whose-milk": InstagramPost(
        title="Rex. Whose milk is this?",
        description=(
            "The milk in the office fridge says Rex, 2019. It has survived two reorgs, more than Dave did. Then it "
            "moved. It's not milk anymore: it's yogurt, and it got promoted. Fern has been here six years.\n"
            "A Toon sketch voiced with ElevenLabs premade voices Matilda (Fern) and Charlie (Rex), lip-synced to "
            "their words; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Matilda and Charlie. Original characters, drawn in code.",
        hashtags=(
            "#officefridge",
            "#officehumor",
            "#workcomedy",
            "#corporatelife",
            "#animatedshorts",
            "#vectoranimation",
            "#lipsync",
        ),
        thumbnail=Thumbnail("Whose milk\nis this?", 0.8, "Toon 06", (470, 1130), 1.35),
    ),
    "date-night": InstagramPost(
        title="A calendar invite? For dinner?",
        description=(
            "Otto sends Mae a calendar invite for date night, from the next room. There's an agenda: item three, "
            "feelings, ten minutes. She's optional; the pasta is required. It's recurring. Until June.\n"
            "A Toon sketch voiced with ElevenLabs premade voices Sarah (Mae) and Daniel (Otto), lip-synced to "
            "their words; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Sarah and Daniel. Original characters, drawn in code.",
        hashtags=(
            "#datenight",
            "#relationshiphumor",
            "#couplegoals",
            "#calendarinvite",
            "#animatedshorts",
            "#vectoranimation",
            "#lipsync",
        ),
        thumbnail=Thumbnail("A calendar invite.\nFor dinner.", 0.8, "Toon 08", (470, 1130), 1.35),
    ),
    "in-network": InstagramPost(
        title="Is a broken arm covered?",
        description=(
            "Gil calls his insurer about a broken arm. Dana in claims is delighted: which arm? They cover the right. "
            "The doctor's out of network, the ambulance was his choice, and the advice is to try again in January.\n"
            "A Toon sketch voiced with ElevenLabs premade voices Chris (Gil) and Jessica (Dana), lip-synced to "
            "their words; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Chris and Jessica. Original characters, drawn in code.",
        hashtags=(
            "#healthinsurance",
            "#adulting",
            "#customerservice",
            "#onhold",
            "#animatedshorts",
            "#vectoranimation",
            "#lipsync",
        ),
        thumbnail=Thumbnail("Is a broken arm\ncovered?", 0.8, "Toon 09", (500, 1181), 1.3),
    ),
    "not-a-robot": InstagramPost(
        title="One form before lunch. How hard can it be?",
        description=(
            "Select all traffic lights. Select all traffic lights that are sad. Select every moment you felt truly "
            "alive. He hesitated like a human and clicked like a robot, and the router from The Router welcomes its "
            "brother home.\n"
            "A square pen-and-ink cartoon voiced with ElevenLabs premade voices Chris, Sarah and Daniel."
        ),
        credit="Voices: ElevenLabs premade voices Chris, Sarah and Daniel. Sound effect generated with ElevenLabs.",
        hashtags=(
            "#captcha",
            "#imnotarobot",
            "#techhumor",
            "#officehumor",
            "#animatedshorts",
            "#inkdrawing",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Prove you're\nnot a robot.", 15.0, "Ink 03", place="top"),
    ),
    "message-failed": InstagramPost(
        title="Wait. Did I just send that to my boss?",
        description=(
            "A text about the boss went to the boss. He begs the router to drop the Wi-Fi, and it does: the message "
            "fails. Then the router retries it, because it hates failing. The boss is typing.\n"
            "A square pen-and-ink cartoon voiced with ElevenLabs premade voices Chris and Daniel."
        ),
        credit="Voices: ElevenLabs premade voices Chris and Daniel. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#wrongchat",
            "#texting",
            "#officehumor",
            "#techhumor",
            "#animatedshorts",
            "#inkdrawing",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Sent to\nthe boss.", 1.4, "Ink 04", (540, 420), 1.5),
    ),
    "u-up": InstagramPost(
        title="I just texted my ex. Was that a mistake?",
        description=(
            "Two in the morning: u up? The router won't unsend it; it doesn't fail anymore, it has grown. She's "
            "typing: who is this? Then she remembers the forty dollars. The router has already paid them, with a "
            "memo.\n"
            "A square pen-and-ink cartoon voiced with ElevenLabs premade voices Chris and Daniel."
        ),
        credit="Voices: ElevenLabs premade voices Chris and Daniel. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#textingmyex",
            "#latenighttexts",
            "#datinghumor",
            "#techhumor",
            "#animatedshorts",
            "#inkdrawing",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("2 AM.\nTexting the ex.", 1.4, "Ink 05", (540, 420), 1.5),
    ),
    "premium-suction": InstagramPost(
        title="Why did you stop cleaning?",
        description=(
            "The robot vacuum's free trial has ended. You bought the hardware; suction is monthly. The kitchen is "
            "premium, the corners platinum. What's free? It maps your home and sells the map. Guess who bought it.\n"
            "A square pen-and-ink cartoon voiced with ElevenLabs premade voices Chris and Lily."
        ),
        credit="Voices: ElevenLabs premade voices Chris and Lily. Sound effect generated with ElevenLabs.",
        hashtags=(
            "#subscriptions",
            "#smarthome",
            "#landlords",
            "#techhumor",
            "#animatedshorts",
            "#inkdrawing",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Your free trial\nhas ended.", 2.6, "Ink 06", place="top"),
    ),
    "the-viewing": InstagramPost(
        title="Is that a toilet in the kitchen?",
        description=(
            "Flat hunting, day 41. The kitchen is open plan: cook and multitask. The window is hand-painted, so the "
            "view never changes. The bed folds down, and it comes with Gary. Two grand a month, each. Dev takes it. "
            "He is applicant forty-seven.\n"
            "A stick-figure cartoon voiced with ElevenLabs premade voices Will, Lily and Callum; original characters "
            "drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Will, Lily and Callum. Sound effect generated with ElevenLabs; "
        "music composed with ElevenLabs Music.",
        hashtags=(
            "#flathunting",
            "#rent",
            "#landlord",
            "#adulting",
            "#animatedshorts",
            "#stickfigure",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("He comes\nwith the lease.", 14.0, "Stick 05", (540, 1000), 1.0),
    ),
    "out-of-office": InstagramPost(
        title="Aren't you on vacation?",
        description=(
            "Bruno is on vacation. Out-of-office is on. He has answered every email to say so, personally, because "
            "it's warmer. The calendar tears through the week. Even his boss replied: from her vacation.\n"
            "A Toon sketch voiced with ElevenLabs premade voices Alice (Pip) and Bill (Bruno), lip-synced to their "
            "words; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Alice and Bill. Original characters, drawn in code.",
        hashtags=(
            "#outofoffice",
            "#vacation",
            "#officehumor",
            "#workcomedy",
            "#corporatelife",
            "#animatedshorts",
            "#lipsync",
        ),
        thumbnail=Thumbnail("Aren't you on\nvacation?", 0.8, "Toon 07", (470, 1222), 1.4),
    ),
    "unlimited-pto": InstagramPost(
        title="Who wants unlimited vacation?",
        description=(
            "Bo has big news: unlimited time off. Pip asks for Friday. Then Friday afternoon. Then lunch. Declined, "
            "declined, declined. So how many days is unlimited? Unlimited: that's why nobody needs one.\n"
            "Comedy Cut 13, Bo's first time on screen: a one-on-one in the meeting room, every pose on the beat."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Eric (Bo) and Will (Pip). Music composed with ElevenLabs Music. "
            "Sound effects generated with ElevenLabs."
        ),
        hashtags=(
            "#unlimitedpto",
            "#vacation",
            "#officehumor",
            "#workcomedy",
            "#corporatelife",
            "#animatedshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Unlimited\nvacation?", 4.6, "Episode 13", place="top"),
    ),
    "brand-refresh": InstagramPost(
        title='Why is our logo a toilet?',
        description=(
            'Rosa runs a bank. Brent rebranded it after a singing toilet, because that is what the kids watch. Q3 is '
            "down. Brent says it's a song. Rosa asks him to play it again.\n"
            'A Collage sketch voiced with ElevenLabs premade voices Matilda (Rosa), Brian (Brent) and Charlie (Flush),'
            ' lip-synced to their words; BOWLHEADS is an invented show, and every character is original, drawn in '
            'code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices Matilda, Brian and Charlie. Original characters, drawn in code. Sound '
            'effects synthesised in code.'
        ),
        hashtags=(
            "#rebrand",
            "#marketing",
            "#corporatelife",
            "#brainrot",
            "#officehumor",
            "#animatedshorts",
            "#satire",
        ),
        thumbnail=Thumbnail("Why is our logo\na toilet?", 16.2, "Collage 01", (540, 1090), 1.3),
    ),
    "book-report": InstagramPost(
        title='A book report about a toilet?',
        description=(
            "Priya asks why Kai's book report is about a toilet. Gary says it's not a toilet, it's Flush, and he has a"
            ' whole arc. Season two is basically Moby Dick. Kai got a D. Gary would like to speak to its manager.\n'
            'A Collage sketch voiced with ElevenLabs premade voices Sarah (Priya) and Chris (Gary), lip-synced to '
            'their words; BOWLHEADS is an invented show, and every character is original, drawn in code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices Sarah and Chris. Original characters, drawn in code. Sound effects '
            'synthesised in code.'
        ),
        hashtags=("#parenting", "#homework", "#schoollife", "#brainrot", "#dadlife", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("A book report\nabout a toilet?", 16.8, "Collage 02", (540, 1090), 1.3),
    ),
    "first-date": InstagramPost(
        title='First date. What do you do?',
        description=(
            "Deb asks Jun what he does. He makes a kids' show. She doesn't let her son watch that stuff. It's Bowl "
            "Heads, the toilet thing: thirty billion views. Her son calls. She wants one autograph, then she's "
            'leaving.\n'
            'A Collage sketch voiced with ElevenLabs premade voices Jessica (Deb), Will (Jun) and River (Kai), '
            'lip-synced to their words; BOWLHEADS is an invented show, and every character is original, drawn in code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices Jessica, Will and River. Original characters, drawn in code. Sound '
            'effects synthesised in code.'
        ),
        hashtags=("#firstdate", "#dating", "#datinglife", "#brainrot", "#parenting", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("First date.\nWhat do you do?", 9.3, "Collage 03", (540, 1090), 1.3),
    ),
    "the-lore": InstagramPost(
        title='Want to hear the lore?',
        description=(
            'Gary offers Kai the Flush lore: ninety-nine episodes, watched on double speed. Nobody watches Bowl Heads '
            'anymore. Then what do they watch? A new one, with a new episode every hour. Gary starts at episode one.\n'
            'A Collage sketch voiced with ElevenLabs premade voices Chris (Gary) and River (Kai), lip-synced to their '
            'words; BOWLHEADS is an invented show, and every character is original, drawn in code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices Chris and River. Original characters, drawn in code. Sound effects '
            'synthesised in code.'
        ),
        hashtags=("#parenting", "#dadlife", "#lore", "#brainrot", "#streaming", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Want to hear\nthe lore?", 9.8, "Collage 04", (540, 1090), 1.3),
    ),
    "gritty-reboot": InstagramPost(
        title='Can you give me pain?',
        description=(
            "Jun is taking his toilet show prestige. He asks Flush for pain. Flush flush, yeah? Be sadder: your "
            "father was a urinal. Now look at the camera like you've lost everything. The best acting Jun has seen "
            "all year.\n"
            'A Collage sketch voiced with ElevenLabs premade voices Will (Jun) and Charlie (Flush), lip-synced to '
            'their words; BOWLHEADS is an invented show, and every character is original, drawn in code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices Will and Charlie. Original characters, drawn in code. Sound effects '
            'synthesised in code.'
        ),
        hashtags=("#reboot", "#prestigetv", "#acting", "#brainrot", "#filmmaking", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Can you give\nme pain?", 13.5, "Collage 05", (540, 1240), 1.3),
    ),
    "breaking-news": InstagramPost(
        title="Is a toilet rotting your kid's brain?",
        description=(
            "Omar asks if a singing toilet is rotting your child's brain. Experts say yes. Experts also say it gets "
            "ten times the ratings. So tonight's weather is brought to you by Flush. The ratings just tripled.\n"
            'A Collage sketch voiced with ElevenLabs premade voices Daniel (Omar) and Charlie (Flush), lip-synced to '
            'their words; BOWLHEADS is an invented show, and every character is original, drawn in code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices Daniel and Charlie. Original characters, drawn in code. Sound effects '
            'synthesised in code.'
        ),
        hashtags=("#news", "#breakingnews", "#media", "#brainrot", "#ratings", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Is a toilet rotting\nyour kid's brain?", 14.0, "Collage 06", (540, 1090), 1.3),
    ),
    "therapy-session": InstagramPost(
        title='Why are you here today?',
        description=(
            "Jun made a show about a toilet. It's his most successful work. He went to film school for this. Feld's "
            'session is two hundred dollars. Can he pay in exposure? Thirty billion views. Same time next week: bring '
            'the toilet.\n'
            'A Collage sketch voiced with ElevenLabs premade voices Alice (Feld) and Will (Jun), lip-synced to their '
            'words; BOWLHEADS is an invented show, and every character is original, drawn in code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices Alice and Will. Original characters, drawn in code. Sound effects '
            'synthesised in code.'
        ),
        hashtags=("#therapy", "#creativelife", "#filmschool", "#brainrot", "#burnout", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Why are you\nhere today?", 14.8, "Collage 07", (540, 1090), 1.3),
    ),
    'saga-known-issue': InstagramPost(
        title='Why did the battle cube have a hole?',
        description=(
            'The deadliest station in the galaxy has a hole that blows it up. Somebody reported it nine years '
            'ago. Lord Gloom asks Enforcer Seven for the priority: medium, then low, then nice to have. The '
            'Directorate has since built a new cube; the hole is now listed as a feature.\nA Saga sketch, a '
            'space-opera parody narrated by a deadpan field guide, voiced with ElevenLabs premade voices George '
            '(narrator), Callum (Lord Gloom) and Liam (Seven); the Directorate and every character are original, '
            'drawn in code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices George, Callum and Liam. Sound effects generated with ElevenLabs. '
            'Music composed with ElevenLabs Music. Original characters, drawn in code.'
        ),
        hashtags=(
            '#backlog',
            '#softwareengineering',
            '#techdebt',
            '#bugreport',
            '#spaceopera',
            '#animatedshorts',
            '#satire',
        ),
        thumbnail=Thumbnail('Why does the cube\nhave a hole?', 13.0, 'Saga 01', (540, 890), 1.0),
    ),
    'saga-annual-review': InstagramPost(
        title='Why do the enforcers never hit anything?',
        description=(
            "Enforcer Seven's annual review: nine thousand shots fired, zero hits. Zero damage, zero complaints, "
            "zero paperwork. Enforcer of the year. And the ones who hit things? We don't talk about Gary.\nA Saga "
            'sketch, a space-opera parody narrated by a deadpan field guide, voiced with ElevenLabs premade '
            'voices George (narrator), Callum (Lord Gloom) and Liam (Seven); the Directorate and every character '
            'are original, drawn in code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices George, Callum and Liam. Sound effects generated with ElevenLabs. '
            'Music composed with ElevenLabs Music. Original characters, drawn in code.'
        ),
        hashtags=(
            '#performancereview',
            '#corporatelife',
            '#kpi',
            '#worklife',
            '#spaceopera',
            '#animatedshorts',
            '#satire',
        ),
        thumbnail=Thumbnail('Shots fired: 9000.\nHits: zero.', 9.0, 'Saga 02', (540, 890), 1.0),
    ),
    'saga-group-chat': InstagramPost(
        title='Worst way to find out who your father is?',
        description=(
            'On the dunes, Lord Gloom makes the big reveal. Juno already knows: Dad posted it in the family group '
            'chat. And sent it to the whole Directorate.\nA Saga sketch, a space-opera parody narrated by a '
            'deadpan field guide, voiced with ElevenLabs premade voices George (narrator), Callum (Lord Gloom) '
            'and River (Juno); the Directorate and every character are original, drawn in code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices George, Callum and River. Sound effects generated with ElevenLabs. '
            'Music composed with ElevenLabs Music. Original characters, drawn in code.'
        ),
        hashtags=('#groupchat', '#familychat', '#dads', '#parenting', '#spaceopera', '#animatedshorts', '#satire'),
        thumbnail=Thumbnail('Juno. I am\nyour father.', 4.5, 'Saga 03', (540, 890), 1.0),
    ),
    'saga-card-reader': InstagramPost(
        title='What does a smuggler fear most?',
        description=(
            'Rook orders one drink in a rough cantina. The bar droid turns the card reader around: add a tip? No '
            'tip. Every patron turns to stare. Fine, the biggest one. The receipt goes straight to the '
            'Directorate.\nA Saga sketch, a space-opera parody narrated by a deadpan field guide, voiced with '
            'ElevenLabs premade voices George (narrator), Roger (Rook) and Jessica (the bar droid); the '
            'Directorate and every character are original, drawn in code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices George, Roger and Jessica. Sound effects generated with '
            'ElevenLabs. Music composed with ElevenLabs Music. Original characters, drawn in code.'
        ),
        hashtags=('#tipping', '#tipscreen', '#tipflation', '#bartender', '#spaceopera', '#animatedshorts', '#satire'),
        thumbnail=Thumbnail('What does a\nsmuggler fear?', 8.5, 'Saga 04', (540, 890), 1.0),
    ),
    'saga-update': InstagramPost(
        title='Worst possible time for a software update?',
        description=(
            'Mid-chase, Rook says punch it. The jump drive has other plans: an update is ready. Skip it? It wants '
            'to know if tonight works. Tonight works. Is this tonight? The update also removed the jump drive, '
            'for security reasons.\nA Saga sketch, a space-opera parody narrated by a deadpan field guide, voiced '
            'with ElevenLabs premade voices George (narrator), Roger (Rook) and River (Juno); the Directorate and '
            'every character are original, drawn in code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices George, Roger and River. Sound effects generated with ElevenLabs. '
            'Music composed with ElevenLabs Music. Original characters, drawn in code.'
        ),
        hashtags=(
            '#softwareupdate',
            '#updates',
            '#tech',
            '#remindmelater',
            '#spaceopera',
            '#animatedshorts',
            '#satire',
        ),
        thumbnail=Thumbnail('Worst time for\nan update?', 8.0, 'Saga 05', (540, 890), 1.0),
    ),
    'saga-free-tier': InstagramPost(
        title='Can you feel the energy that binds the galaxy?',
        description=(
            'Elder Mabel teaches Juno the Flow. Juno feels it: a pebble. Boulders are Flow Plus, mind tricks are '
            'Flow Premium, billed yearly, and free gets you commercials. That great disturbance? The renewal.\nA '
            'Saga sketch, a space-opera parody narrated by a deadpan field guide, voiced with ElevenLabs premade '
            'voices George (narrator), Lily (Elder Mabel) and River (Juno); the Directorate and every character '
            'are original, drawn in code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices George, Lily and River. Music composed with ElevenLabs Music. '
            'Original characters, drawn in code.'
        ),
        hashtags=(
            '#subscriptions',
            '#freemium',
            '#cancelsubscription',
            '#streaming',
            '#spaceopera',
            '#animatedshorts',
            '#satire',
        ),
        thumbnail=Thumbnail('Can you feel\nthe Flow?', 8.5, 'Saga 06', (540, 890), 1.0),
    ),
    'saga-open-plan': InstagramPost(
        title='Why are the walls closing in?',
        description=(
            'The trash compactor walls are closing in. Facilities calls it an upgrade: please submit a ticket, '
            "about nine years. Then Enforcer Seven walks in for his hot desk. He's only in on Tuesdays.\nA Saga "
            'sketch, a space-opera parody narrated by a deadpan field guide, voiced with ElevenLabs premade '
            'voices George (narrator), Jessica (the facilities droid), Roger (Rook), River (Juno) and Liam '
            '(Seven); the Directorate and every character are original, drawn in code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices George, Jessica, Roger, River and Liam. Sound effects generated '
            'with ElevenLabs. Music composed with ElevenLabs Music. Original characters, drawn in code.'
        ),
        hashtags=(
            '#openplan',
            '#hotdesking',
            '#returntooffice',
            '#officelife',
            '#spaceopera',
            '#animatedshorts',
            '#satire',
        ),
        thumbnail=Thumbnail('Why are the walls\nclosing in?', 14.0, 'Saga 07', (540, 890), 1.0),
    ),
    "password-expired": InstagramPost(
        title="Why does my password expire every month?",
        description=(
            "Bruno's password expired again. IT rejects the new one: too similar to the old one. How does IT know "
            "his old one? They keep them all, in a spreadsheet. Was the spreadsheet password protected? It was. It "
            "expired.\n"
            "A Toon sketch voiced with ElevenLabs premade voices Bill (Bruno) and Alice (Pip), lip-synced to their "
            "words; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Bill and Alice. Original characters, drawn in code.",
        hashtags=(
            "#passwords",
            "#ithelpdesk",
            "#cybersecurity",
            "#officehumor",
            "#workcomedy",
            "#animatedshorts",
            "#lipsync",
        ),
        thumbnail=Thumbnail("Why does my\npassword expire?", 1.0, "Toon 13", (470, 1130), 1.35),
    ),
    "goldfish-funeral": InstagramPost(
        title="Do you want to say a few words for Bubbles?",
        description=(
            "Gary and Kai say goodbye to Bubbles the goldfish. He was a good fish. A great fish. Then the toilet "
            "answers: Flush, the singing toilet from the show, is in every toilet. Gary asks for a selfie.\n"
            "A Collage sketch voiced with ElevenLabs premade voices Chris (Gary), River (Kai) and Charlie (Flush), "
            "lip-synced to their words; BOWLHEADS is an invented show, and every character is original, drawn in "
            "code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Chris, River and Charlie. Original characters, drawn in code. Sound "
            "effects synthesised in code."
        ),
        hashtags=("#goldfish", "#parenting", "#petfuneral", "#brainrot", "#dadlife", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("A few words\nfor Bubbles?", 1.0, "Collage 08", (540, 1200), 1.6),
    ),
    "saga-icebreaker": InstagramPost(
        title="Is there anything worse than a team icebreaker?",
        description=(
            "One fun fact about yourself. Seven has never hit a target. The droid is technically a toaster. Lord "
            "Gloom can hear your thoughts. Great icebreaker, my lord. Now say it in your head.\n"
            "A Saga sketch, a space-opera parody narrated by a deadpan field guide, voiced with ElevenLabs premade "
            "voices George (narrator), Liam (Seven), Callum (Lord Gloom) and Jessica (the droid); the Directorate "
            "and every character are original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices George, Liam, Callum and Jessica. Sound effects generated with "
            "ElevenLabs. Music composed with ElevenLabs Music. Original characters, drawn in code."
        ),
        hashtags=(
            "#icebreaker",
            "#teambuilding",
            "#officelife",
            "#workcomedy",
            "#spaceopera",
            "#animatedshorts",
            "#satire",
        ),
        thumbnail=Thumbnail("Worse than an\nicebreaker?", 12.0, "Saga 08", (540, 890), 1.0),
    ),
    "the-card": InstagramPost(
        title="Rex, whose card is this?",
        description=(
            "There's a leaving card in the office kitchen. Fern signs it without asking whose it is: good luck out "
            "there. Then she reads the front. It says Fern. She is not leaving. There's a meeting with HR. Rex has "
            "advice: bring it with you.\n"
            "A Toon sketch voiced with ElevenLabs premade voices Matilda (Fern) and Charlie (Rex), lip-synced to "
            "their words; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Matilda and Charlie. Original characters, drawn in code.",
        hashtags=(
            "#leavingcard",
            "#layoffs",
            "#officehumor",
            "#workcomedy",
            "#corporatelife",
            "#animatedshorts",
            "#lipsync",
        ),
        thumbnail=Thumbnail("Whose card\nis this?", 0.8, "Toon 14", (470, 1130), 1.35),
    ),
    "the-will": InstagramPost(
        title="Why wait until I'm dead to read my will?",
        description=(
            "Rosa reads her will now, to watch their faces. The house goes to Gary, if he finishes one book that "
            "isn't about a toilet. Everything else goes to Kai, if he can name one thing that isn't a toilet.\n"
            "A Collage sketch voiced with ElevenLabs premade voices Matilda (Rosa), Chris (Gary) and River (Kai), "
            "lip-synced to their words; BOWLHEADS is an invented show, and every character is original, drawn in "
            "code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Matilda, Chris and River. Original characters, drawn in code. Sound "
            "effects synthesised in code."
        ),
        hashtags=("#inheritance", "#family", "#grandma", "#brainrot", "#parenting", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Why wait until\nI'm dead?", 1.0, "Collage 09", (540, 1200), 1.6),
    ),
    "saga-exit-interview": InstagramPost(
        title="Why does nobody ever quit the Directorate?",
        description=(
            "Enforcer Seven has another offer. Is it the pay? The hours? The airlock? Lord Gloom threw Gary out of "
            "it: Gary was not a culture fit. What if they threw Seven a pizza party? What kind of pizza?\n"
            "A Saga sketch, a space-opera parody narrated by a deadpan field guide, voiced with ElevenLabs premade "
            "voices George (narrator), Callum (Lord Gloom) and Liam (Seven); the Directorate and every character "
            "are original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices George, Callum and Liam. Music composed with ElevenLabs Music. "
            "Original characters, drawn in code."
        ),
        hashtags=(
            "#exitinterview",
            "#culturefit",
            "#quitting",
            "#officelife",
            "#spaceopera",
            "#animatedshorts",
            "#satire",
        ),
        thumbnail=Thumbnail("Why does nobody\never quit?", 8.0, "Saga 09", (540, 890), 1.0),
    ),
    "friday-sync": InstagramPost(
        title="Why is there a meeting on Friday evening?",
        description=(
            "Bruno booked a quick sync for Friday evening. It's nothing bad: Pip just needs to train the new hire. "
            "Then a job alert: her own job, for less money. Can she apply for it? Sorry. She's overqualified.\n"
            "A Toon sketch voiced with ElevenLabs premade voices Alice (Pip) and Bill (Bruno), lip-synced to their "
            "words; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Alice and Bill. Original characters, drawn in code.",
        hashtags=(
            "#fridayfeeling",
            "#jobsearch",
            "#replaced",
            "#officehumor",
            "#workcomedy",
            "#animatedshorts",
            "#lipsync",
        ),
        thumbnail=Thumbnail("A meeting on\nFriday evening?", 1.0, "Toon 15", (470, 1130), 1.35),
    ),
    "thought-leader": InstagramPost(
        title="Can I read you my post before it goes live?",
        description=(
            "Brent's new post: what a singing toilet taught him about leadership. Lesson one, always be flushing. "
            "Lesson two, let go of what weighs you down. Jun wrote that show. Lesson four: never credit the writer.\n"
            "A Collage sketch voiced with ElevenLabs premade voices Brian (Brent) and Will (Jun), lip-synced to "
            "their words; BOWLHEADS is an invented show, and every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Brian and Will. Original characters, drawn in code. Sound effects "
            "synthesised in code."
        ),
        hashtags=(
            "#thoughtleadership",
            "#linkedin",
            "#leadership",
            "#brainrot",
            "#creatives",
            "#animatedshorts",
            "#satire",
        ),
        thumbnail=Thumbnail("Can I read you\nmy post?", 1.0, "Collage 10", (540, 1200), 1.6),
    ),
    "saga-moving-day": InstagramPost(
        title="What does it really cost to own a ship?",
        description=(
            "Juno is moving. It's just a few boxes. And a couch. And her aunt's water tower. And her aunt. To the "
            "top floor of the battle cube, where the lift is broken. Rook owns a ship. He will never fly it "
            "anywhere he wants again.\n"
            "A Saga sketch, a space-opera parody narrated by a deadpan field guide, voiced with ElevenLabs premade "
            "voices George (narrator), River (Juno) and Roger (Rook); the Directorate and every character are "
            "original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices George, River and Roger. Music composed with ElevenLabs Music. "
            "Original characters, drawn in code."
        ),
        hashtags=(
            "#movingday",
            "#friendswithacar",
            "#moving",
            "#adulting",
            "#spaceopera",
            "#animatedshorts",
            "#satire",
        ),
        thumbnail=Thumbnail("What does it cost\nto own a ship?", 9.0, "Saga 10", (540, 890), 1.0),
    ),
    "like-family": InstagramPost(
        title="Rex, can we talk about my salary?",
        description=(
            "We're not a company, Rex says, we're a family. Then Fern would like an allowance. He thinks of her "
            "like a daughter. Then she'll see him at Christmas. Let's keep this professional. So, a raise? Sorry. "
            "She's like family.\n"
            "A Toon sketch voiced with ElevenLabs premade voices Matilda (Fern) and Charlie (Rex), lip-synced to "
            "their words; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Matilda and Charlie. Original characters, drawn in code.",
        hashtags=("#salary", "#payraise", "#werefamily", "#officehumor", "#workcomedy", "#animatedshorts", "#lipsync"),
        thumbnail=Thumbnail("Can we talk about\nmy salary?", 0.8, "Toon 16", (470, 1130), 1.35),
    ),
    "final-broadcast": InstagramPost(
        title="After thirty years, is this really my last broadcast?",
        description=(
            "Omar's last night on air. The network found a younger anchor: Flush, the singing toilet. He tested "
            "great with young people. He can't even read the news. Neither can the viewers. And now, the weather.\n"
            "A Collage sketch voiced with ElevenLabs premade voices Daniel (Omar), Will (Jun) and Charlie (Flush), "
            "lip-synced to their words; BOWLHEADS is an invented show, and every character is original, drawn in "
            "code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Daniel, Will and Charlie. Original characters, drawn in code. Sound "
            "effects synthesised in code."
        ),
        hashtags=("#news", "#newsanchor", "#replaced", "#brainrot", "#media", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Is this my last\nbroadcast?", 1.0, "Collage 11", (540, 1200), 1.6),
    ),
    "saga-expense-report": InstagramPost(
        title="Who approves a dark lord's expenses?",
        description=(
            "One planet, destroyed; the receipt exploded. The cape is personal. The helmet is personal. The "
            "breathing machine is personal. The planet is approved: just attach a photo of it. Then it's personal.\n"
            "A Saga sketch, a space-opera parody narrated by a deadpan field guide, voiced with ElevenLabs premade "
            "voices George (narrator), Callum (Lord Gloom) and Jessica (the droid); the Directorate and every "
            "character are original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices George, Callum and Jessica. Sound effects generated with ElevenLabs. "
            "Music composed with ElevenLabs Music. Original characters, drawn in code."
        ),
        hashtags=(
            "#expenses",
            "#expensereport",
            "#finance",
            "#officelife",
            "#spaceopera",
            "#animatedshorts",
            "#satire",
        ),
        thumbnail=Thumbnail("Who approves\nhis expenses?", 10.0, "Saga 11", (540, 890), 1.0),
    ),
    "reply-all": InstagramPost(
        title="Bruno. Did you just reply all?",
        description=(
            "Bruno meant to send it to Pip. He sent it to the whole company: this meeting could have been an email. "
            "The CEO agrees, and cancels every meeting. He's a hero. Then the CEO again: your job, also an email.\n"
            "A Toon sketch voiced with ElevenLabs premade voices Alice (Pip) and Bill (Bruno), lip-synced to their "
            "words; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Alice and Bill. Original characters, drawn in code.",
        hashtags=("#replyall", "#email", "#meetings", "#officehumor", "#workcomedy", "#animatedshorts", "#lipsync"),
        thumbnail=Thumbnail("Did you just\nreply all?", 0.8, "Toon 17", (470, 1130), 1.35),
    ),
    "intervention": InstagramPost(
        title="Gary, do you know why we're all here?",
        description=(
            "It's an intervention. Gary has watched every episode of Bowl Heads, twice. Kai is ten, and he stopped: "
            "he's into tax law now. Then the headset beeps. Was that a new episode? Just the intro.\n"
            "A Collage sketch voiced with ElevenLabs premade voices Jessica (Deb), River (Kai) and Chris (Gary), "
            "lip-synced to their words; BOWLHEADS is an invented show, and every character is original, drawn in "
            "code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Jessica, River and Chris. Original characters, drawn in code. Sound "
            "effects synthesised in code."
        ),
        hashtags=("#intervention", "#bingewatching", "#dadlife", "#brainrot", "#family", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Do you know why\nwe're all here?", 1.0, "Collage 12", (540, 1200), 1.6),
    ),
    "saga-on-hold": InstagramPost(
        title="Who do you call when your planet gets destroyed?",
        description=(
            "Juno's planet was destroyed. Has she tried restarting it? Please hold. Can she speak to a human? All "
            "their humans were on her planet. Would she like to add planet insurance?\n"
            "A Saga sketch, a space-opera parody narrated by a deadpan field guide, voiced with ElevenLabs premade "
            "voices George (narrator), River (Juno) and Jessica (the droid); the Directorate and every character "
            "are original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices George, River and Jessica. Sound effects generated with ElevenLabs. "
            "Music composed with ElevenLabs Music. Original characters, drawn in code."
        ),
        hashtags=(
            "#onhold",
            "#customerservice",
            "#callcenter",
            "#adulting",
            "#spaceopera",
            "#animatedshorts",
            "#satire",
        ),
        thumbnail=Thumbnail("Planet destroyed?\nWho do you call?", 12.0, "Saga 12", (540, 890), 1.0),
    ),
    "gloss-orientation": InstagramPost(
        title="Ever woken up inside a mandatory team-building exercise?",
        description=(
            "Day one in the Plaza. Nadia asks for the exit; Sunny says it is right behind her. It is painted on. "
            "Tamsin tried it for eleven years, and Gus is still on his free trial. The exit is available in a future "
            "update.\nA Gloss sketch, a satire of cheerful forever-worlds hosted by a deadpan orb, voiced with "
            "ElevenLabs premade voices Alice (Sunny), Sarah (Nadia), Bill (Gus) and Laura (Tamsin); the Plaza and "
            "every character are original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Alice, Sarah, Bill and Laura. Sound effects generated with ElevenLabs."
            " Music composed with ElevenLabs Music. Original characters, drawn in code."
        ),
        hashtags=("#teambuilding", "#corporatelife", "#officehumor", "#adulting", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Where is\nthe exit?", 15.0, "Gloss 01", (540, 960), 1.0),
    ),
    "gloss-joy-points": InstagramPost(
        title="What if every tiny thing you did was being scored?",
        description=(
            "Gus holds a door: plus two. Gus breathes, heavily: minus. Tamsin has nine million Joy Points and is "
            "saving up for more points, because points can be redeemed for more points. The balance does not roll "
            "over. Neither do you.\nA Gloss sketch, a satire of cheerful forever-worlds hosted by a deadpan orb, "
            "voiced with ElevenLabs premade voices Alice (Sunny), Bill (Gus) and Laura (Tamsin); the Plaza and every "
            "character are original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Alice, Bill and Laura. Music composed with ElevenLabs Music. Original "
            "characters, drawn in code."
        ),
        hashtags=("#gamification", "#performancereview", "#kpi", "#corporatelife", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Points for\nmore points", 15.8, "Gloss 02", (540, 960), 1.0),
    ),
    "gloss-trust-fall": InstagramPost(
        title="How much should you trust your workplace?",
        description=(
            "Today's activity is a trust fall. Nadia asks who is catching her. Sunny says: trust. Nobody catches her;"
            " catching was not in the budget. Gus fell in March and is still waiting for the trust. Please remain on "
            "the floor for scoring.\nA Gloss sketch, a satire of cheerful forever-worlds hosted by a deadpan orb, "
            "voiced with ElevenLabs premade voices Alice (Sunny), Sarah (Nadia) and Bill (Gus); the Plaza and every "
            "character are original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Alice, Sarah and Bill. Sound effects generated with ElevenLabs. Music "
            "composed with ElevenLabs Music. Original characters, drawn in code."
        ),
        hashtags=("#teambuilding", "#trustfall", "#corporatelife", "#workculture", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Who is\ncatching me?", 7.6, "Gloss 03", (540, 960), 1.0),
    ),
    "gloss-feedback": InstagramPost(
        title="Ever been asked to rate a place you can never leave?",
        description=(
            "The eternal stay survey: one to five. Tamsin gives five forever. Gus gives zero, which is not an option,"
            " so it is recorded as one. Comments go straight into the bin. Based on your feedback, the Plaza has "
            "added more plaza, which was the complaint.\nA Gloss sketch, a satire of cheerful forever-worlds hosted "
            "by a deadpan orb, voiced with ElevenLabs premade voices Alice (Sunny), Sarah (Nadia), Bill (Gus) and "
            "Laura (Tamsin); the Plaza and every character are original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Alice, Sarah, Bill and Laura. Music composed with ElevenLabs Music. "
            "Original characters, drawn in code."
        ),
        hashtags=("#customersurvey", "#feedback", "#customerexperience", "#adulting", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Rate your\neternal stay", 21.5, "Gloss 04", (540, 960), 1.0),
    ),
    "gloss-exit": InstagramPost(
        title="What is really behind the exit door?",
        description=(
            "Forty years Gus has looked for this door. Behind it: another door. Then a smaller door. Then a waiting "
            "room, a ticket and a display. He is four million and six. Now serving: three. Waiting is the "
            "attraction.\nA Gloss sketch, a satire of cheerful forever-worlds hosted by a deadpan orb, voiced with "
            "ElevenLabs premade voices Alice (Sunny) and Bill (Gus); the Plaza and every character are original, "
            "drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Alice and Bill. Sound effects generated with ElevenLabs. Music "
            "composed with ElevenLabs Music. Original characters, drawn in code."
        ),
        hashtags=("#waitingroom", "#bureaucracy", "#customerservice", "#adulting", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Behind the\nexit door", 18.5, "Gloss 05", (540, 960), 1.0),
    ),
    "gloss-wellness": InstagramPost(
        title="When did wellness become mandatory?",
        description=(
            "Gus's wellness check reads twelve percent. Please smile harder. His face is escalated to a manager, who "
            "is the same orb in a tie. Your wellbeing is our top priority. It is ranked fourth.\nA Gloss sketch, a "
            "satire of cheerful forever-worlds hosted by a deadpan orb, voiced with ElevenLabs premade voices Alice "
            "(Sunny) and Bill (Gus); the Plaza and every character are original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Alice and Bill. Sound effects generated with ElevenLabs. Music "
            "composed with ElevenLabs Music. Original characters, drawn in code."
        ),
        hashtags=("#wellness", "#wellbeing", "#corporatewellness", "#corporatelife", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Smile\nharder", 21.0, "Gloss 06", (540, 960), 1.0),
    ),
    "gloss-terms": InstagramPost(
        title="Did anyone actually read the new terms of existence?",
        description=(
            "The Plaza has updated its terms of existence. Tamsin accepts without reading. Section four: hope is now "
            "a premium feature, and declining has been added to section four. By continuing to exist, you agree to "
            "continue existing.\nA Gloss sketch, a satire of cheerful forever-worlds hosted by a deadpan orb, voiced "
            "with ElevenLabs premade voices Alice (Sunny), Sarah (Nadia), Bill (Gus) and Laura (Tamsin); the Plaza "
            "and every character are original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Alice, Sarah, Bill and Laura. Music composed with ElevenLabs Music. "
            "Original characters, drawn in code."
        ),
        hashtags=("#termsandconditions", "#fineprint", "#adulting", "#corporatelife", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Hope is\npremium", 11.5, "Gloss 07", (540, 960), 1.0),
    ),
}

# project slug -> the file name of its rendered video, without extension
VIDEOS = {
    "honesty-interview": "honesty-interview-recreated",
    "pressure-interview": "pressure-interview",
    "fast-at-math": "fast-at-math",
    "multitasking": "multitasking",
    "wifi-password": "wifi-password",
    "scene": "Printer_Recreation",
    "five-years": "five-years",
    "upside-down": "upside-down",
    "the-router": "the-router",
    "mushroom-training": "mushroom-training",
    "focus-mode": "focus-mode",
    "camera-off": "camera-off",
    "off-and-on": "off-and-on",
    "employee-survey": "employee-survey",
    "check-with-my-team": "check-with-my-team",
    "screen-share": "screen-share",
    "repeat-after-me": "repeat-after-me",
    "the-report": "the-report",
    "logo-bigger": "logo-bigger",
    "quick-question": "quick-question",
    "day-off": "day-off",
    "whose-milk": "whose-milk",
    "date-night": "date-night",
    "in-network": "in-network",
    "not-a-robot": "not-a-robot",
    "unexpected-item": "unexpected-item",
    "cancel-anytime": "cancel-anytime",
    "what-my-dad-does": "what-my-dad-does",
    "tip-screen": "tip-screen",
    "out-of-office": "out-of-office",
    "unlimited-pto": "unlimited-pto",
    "message-failed": "message-failed",
    "u-up": "u-up",
    "premium-suction": "premium-suction",
    "the-viewing": "the-viewing",
    "culture-fit": "culture-fit",
    "market-rate": "market-rate",
    "elevator-pitch": "elevator-pitch",
    "the-cake": "the-cake",
    "split-it": "split-it",
    "home-sick": "home-sick",
    "group-nine": "group-nine",
    "going-down": "going-down",
    "smart-lamp": "smart-lamp",
    "return-to-office": "return-to-office",
    "brand-refresh": "brand-refresh",
    "book-report": "book-report",
    "first-date": "first-date",
    "the-lore": "the-lore",
    "gritty-reboot": "gritty-reboot",
    "breaking-news": "breaking-news",
    "therapy-session": "therapy-session",
    "saga-known-issue": "saga-known-issue",
    "saga-annual-review": "saga-annual-review",
    "saga-group-chat": "saga-group-chat",
    "saga-card-reader": "saga-card-reader",
    "saga-update": "saga-update",
    "saga-free-tier": "saga-free-tier",
    "saga-open-plan": "saga-open-plan",
    "password-expired": "password-expired",
    "goldfish-funeral": "goldfish-funeral",
    "saga-icebreaker": "saga-icebreaker",
    "the-card": "the-card",
    "the-will": "the-will",
    "saga-exit-interview": "saga-exit-interview",
    "friday-sync": "friday-sync",
    "thought-leader": "thought-leader",
    "saga-moving-day": "saga-moving-day",
    "like-family": "like-family",
    "final-broadcast": "final-broadcast",
    "saga-expense-report": "saga-expense-report",
    "reply-all": "reply-all",
    "intervention": "intervention",
    "saga-on-hold": "saga-on-hold",
    "gloss-orientation": "gloss-orientation",
    "gloss-joy-points": "gloss-joy-points",
    "gloss-trust-fall": "gloss-trust-fall",
    "gloss-feedback": "gloss-feedback",
    "gloss-exit": "gloss-exit",
    "gloss-wellness": "gloss-wellness",
    "gloss-terms": "gloss-terms",
}


# Episodes whose scene hides its burned-in text (hook card, captions) in a cover variant, with the scene file in
# <episodes>/<slug>/ that the published video is encoded from: the cover's backdrop is drawn from it, so the headline
# does not sit on a cut card or a ghost caption.
COVER_SCENES = {
    "repeat-after-me": "repeat-after-me.scene.xml",
    "check-with-my-team": "scene.xml",
    "not-a-robot": "not-a-robot.scene.xml",
    "unexpected-item": "unexpected-item.scene.xml",
    "cancel-anytime": "cancel-anytime.scene.xml",
    "what-my-dad-does": "what-my-dad-does.scene.xml",
    "tip-screen": "tip-screen.scene.xml",
    "unlimited-pto": "unlimited-pto.scene.xml",
    "message-failed": "message-failed.scene.xml",
    "u-up": "u-up.scene.xml",
    "premium-suction": "premium-suction.scene.xml",
    "home-sick": "home-sick.scene.xml",
    "group-nine": "group-nine.scene.xml",
    "going-down": "going-down.scene.xml",
    "the-viewing": "the-viewing.scene.xml",
    "culture-fit": "culture-fit.scene.xml",
    "market-rate": "market-rate.scene.xml",
    "elevator-pitch": "elevator-pitch.scene.xml",
    "return-to-office": "return-to-office.scene.xml",
    "saga-known-issue": "saga-known-issue.scene.xml",
    "saga-annual-review": "saga-annual-review.scene.xml",
    "saga-group-chat": "saga-group-chat.scene.xml",
    "saga-card-reader": "saga-card-reader.scene.xml",
    "saga-update": "saga-update.scene.xml",
    "saga-free-tier": "saga-free-tier.scene.xml",
    "saga-open-plan": "saga-open-plan.scene.xml",
    "saga-icebreaker": "saga-icebreaker.scene.xml",
    "saga-exit-interview": "saga-exit-interview.scene.xml",
    "saga-moving-day": "saga-moving-day.scene.xml",
    "saga-expense-report": "saga-expense-report.scene.xml",
    "saga-on-hold": "saga-on-hold.scene.xml",
    "gloss-orientation": "gloss-orientation.scene.xml",
    "gloss-joy-points": "gloss-joy-points.scene.xml",
    "gloss-trust-fall": "gloss-trust-fall.scene.xml",
    "gloss-feedback": "gloss-feedback.scene.xml",
    "gloss-exit": "gloss-exit.scene.xml",
    "gloss-wellness": "gloss-wellness.scene.xml",
    "gloss-terms": "gloss-terms.scene.xml",
}


def items(renders: Path, episodes: Path | None = None) -> dict[str, Item]:
    """Every post with its rendered video (and the scene its cover is drawn from, for :data:`COVER_SCENES`), keyed
    by the video's name. ``episodes`` defaults to the ``episodes`` folder beside ``renders``."""
    episodes = Path(episodes) if episodes is not None else Path(renders).resolve().parent / "episodes"
    return {
        VIDEOS[slug]: Item(
            post,
            Path(renders) / f"{VIDEOS[slug]}.mp4",
            episodes / slug / COVER_SCENES[slug] if slug in COVER_SCENES else None,
        )
        for slug, post in POSTS.items()
    }


def font_file(folder: Path) -> Path:
    """The headline font, installed into ``folder`` (and pinned by its lock) the first time."""
    return fonts.install(THUMBNAIL_FONT, folder).path


def write_all(
    out: Path, renders: Path, *, fonts_dir: Path, engine: str | Path, only: list[str] | None = None
) -> list[Path]:
    """Deliver every post whose video drifted (or only the ``only`` ones) and record the delivery; returns the
    folders written."""
    return publish(items(renders), out, font=font_file(fonts_dir), engine=engine, only=only)


def check_all(out: Path, renders: Path, *, fonts_dir: Path) -> list[Drift]:
    """Every drift between ``out`` and delivering every post from ``renders`` now."""
    return check_delivery(items(renders), out, font=font_file(fonts_dir))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("deliver", "check"))
    parser.add_argument("out", type=Path, help="the delivery folder: one folder per video and delivery.json")
    parser.add_argument("renders", type=Path, help="the folder of rendered <video name>.mp4 files")
    parser.add_argument("--fonts", type=Path, required=True, help="where the headline font is installed")
    parser.add_argument("--engine", default=os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render"))
    parser.add_argument("--only", action="append", metavar="NAME", help="deliver this video alone (repeatable)")
    args = parser.parse_args(argv)
    if args.command == "check":
        drift = check_all(args.out, args.renders, fonts_dir=args.fonts)
        for d in drift:
            print(d)
        print(f"{len(POSTS)} videos, {len(drift)} drifted" if drift else f"{len(POSTS)} videos, delivery current")
        return 1 if drift else 0
    if not args.engine:
        parser.error("no engine: pass --engine or set SRSTUDIO_ENGINE")
    try:
        written = write_all(args.out, args.renders, fonts_dir=args.fonts, engine=args.engine, only=args.only)
    except DeliveryError as exc:
        raise SystemExit(f"deliver: {exc}") from None
    for folder in written:
        print(folder / "ig.txt", folder / "cover.jpg")
    if args.only:
        left = [d for d in check_all(args.out, args.renders, fonts_dir=args.fonts) if d.name not in args.only]
        print(f"delivered {', '.join(args.only)}; {len(left)} drift(s) left elsewhere, see check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
