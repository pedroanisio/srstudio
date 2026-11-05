"""What test_smallprint.py shares with other test modules: the penny show, a script that keeps the format."""

from __future__ import annotations

from srstudio.smallprint import Beat, Show, Stamp
from srstudio.social import InstagramPost

SMILE, BATTERY, MELTDOWN = "public-smile", "social-battery", "internal-meltdown"
TOWER = "smallprint-tower"
FOUND = Stamp("TOP SPEED 25 MPH", "Louis Bloomfield, Live Science, 2012")
BEATS = (
    Beat("hook", "Can a penny from up there kill you?", SMILE, TOWER, "top"),
    Beat("try", "Okay. One penny.", MELTDOWN, steps=((0.4, "fall-1"), (0.8, "fall-3"), (1.2, "landed")), hold=0.5),
    Beat("no", "Nope. It would sting.", BATTERY, framing="close"),
    Beat("why", "It is flat, so it tumbles. It tops out around 25 miles an hour.", BATTERY,
         panel="penny-fall", stamp=FOUND),
    Beat("busted", "MythBusters tried it in 2003. Busted.", BATTERY, panel="penny-fall",
         stamp=Stamp("BUSTED", "MythBusters, 2003")),
    Beat("check", "Please do not check.", BATTERY, TOWER, "landed", framing="tight", hold=0.6),
    Beat("bolt", "What does hit that building? Lightning. About 23 times a year.", SMILE, panel="lightning",
         stamp=Stamp("23 STRIKES A YEAR", "NASA Goddard, citing NOAA, 2017")),
    Beat("end", "So up there, the penny is the safe one.", SMILE, TOWER, "top"),
)  # fmt: skip
KEPT = (2.4, 1.4, 1.5, 4.6, 2.2, 1.2, 4.0, 2.2)
SHOW = Show(
    "penny", 1, "A penny", "Can a penny dropped from the Empire State Building kill you?", "Rafa and a penny.",
    "A clay man drops a penny off a model tower.", BEATS, KEPT, InstagramPost(title="Can a penny kill you?",
    description="d"),
)  # fmt: skip
