"""The reels stopped before their first delivery, each with the ruling behind it (ADR 0140). A held reel owes no
delivery, so the publish gate reads on, and it cannot be delivered until its line leaves this map. It stays listed as
held back on every Drive push. A ruling that releases a reel removes its line in the commit that delivers it.
"""

STOPPED = "batch A stopped: arc4d3, Slack 1793546229.202829"

HELD = {
    "best-day": STOPPED,
    "bin-day": STOPPED,
    "did-you-pack": STOPPED,
    "eye-chart": STOPPED,
    "first-sip": STOPPED,
    "fitted-sheet": STOPPED,
    "headphones": STOPPED,
    "how-is-everything": STOPPED,
    "mosquito": STOPPED,
    "one-more-taste": STOPPED,
    "one-symptom": STOPPED,
    "quiet-please": STOPPED,
    "seat-belt-sign": STOPPED,
    "sensor": STOPPED,
    "shortest-line": STOPPED,
    "sinking-chair": STOPPED,
    "slept-wrong": STOPPED,
    "some-assembly": STOPPED,
    "the-last-guy": STOPPED,
    "the-scale": STOPPED,
    "the-tongs": STOPPED,
    "warranty": STOPPED,
    "wave-back": STOPPED,
    "you-have-it": STOPPED,
}
