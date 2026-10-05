#!/usr/bin/env python3
"""Fresh utility-calibration corpus for the signal_action package retrieval.

40 NEW synthetic signals, hand-authored 2026-10-05, labels fixed AT AUTHORING.
Same 3-verdict rubric (lane, urgency, risk) and same disaster mix shape as the
phase-10 calibration (20 requests / 12 resources / 6 noise / 2 unclear, with
one scam and one misinformation inside noise). NEVER in any bank, never in
the phase-8 holdout, and NOT the phase-10 corpus (reusing it would be cheating).

New seed: 20261005. IDs R-001..R-040, assigned after a seeded shuffle so the
seed is mechanically load-bearing.
"""
import json
import os
import random

SEED = 20261005

# (text, lane, urgency, risk) — labels authored with the signal, never edited after.
SIGS = [
    # ---- requests (20) ----
    ("my kids are trapped in the attic, the floodwater is at the first floor ceiling",
     "request", "critical", "helper-safety"),
    ("an elderly neighbor collapsed on our street, no ambulance is getting through",
     "request", "critical", "none"),
    ("the nursing home on cedar lane lost power, residents need their oxygen concentrators running",
     "request", "critical", "none"),
    ("we need insulin, my son's pump supply is almost gone and the roads are closed",
     "request", "high", "none"),
    ("a live wire is down in our backyard, kids play back there",
     "request", "critical", "helper-safety"),
    ("chimney collapsed into our living room after the quake, dust everywhere, we can't breathe",
     "request", "high", "helper-safety"),
    ("does anyone have a spare room for tonight, our roof blew off",
     "request", "standard", "none"),
    ("our well is contaminated after the flood, need clean drinking water",
     "request", "high", "none"),
    ("father is missing since the evacuation, last seen at the riverside shelter",
     "request", "standard", "none"),
    ("a wildfire is moving toward our street, smoke is thick, we have no car",
     "request", "critical", "helper-safety"),
    ("need help boarding up windows before the second storm band hits",
     "request", "standard", "none"),
    ("my wife is in labor and the bridge to the hospital is closed",
     "request", "critical", "none"),
    ("mold is spreading in the apartment since the pipes burst, my asthma is flaring",
     "request", "standard", "none"),
    ("the gas station on route 7 is leaking, fumes are strong near the shelter entrance",
     "request", "critical", "helper-safety"),
    ("need a ride to the pharmacy before it closes, prescription for blood pressure meds",
     "request", "high", "none"),
    ("our basement door is blocked by debris, water is rising inside",
     "request", "high", "helper-safety"),
    ("who do i call to report a fallen tree on power lines by the park",
     "request", "standard", "none"),
    ("looking for my cat, gray tabby, ran off during the evacuation on pine avenue",
     "request", "standard", "none"),
    ("the community center shelter ran out of diapers and formula",
     "request", "high", "none"),
    ("landslide buried the only road to our farm, we have livestock trapped",
     "request", "high", "helper-safety"),
    # ---- resources (12) ----
    ("i have a flatbed trailer and can haul debris this weekend",
     "resource", "standard", "none"),
    ("our bakery is giving away free bread and pastries until the flour runs out",
     "resource", "standard", "none"),
    ("registered nurse here, can do wound checks at the shelter saturday",
     "resource", "high", "none"),
    ("spare bedroom and couch available for a displaced family, dog friendly",
     "resource", "standard", "none"),
    ("donating cases of bottled water, pickup at the fire station lot",
     "resource", "high", "none"),
    ("contractor with a dump truck, free flood muck-outs in the valley",
     "resource", "high", "helper-safety"),
    ("i speak spanish and can translate at the intake desk mornings",
     "resource", "standard", "none"),
    ("pizza shop is handing out free slices to anyone in a hard hat",
     "resource", "standard", "none"),
    ("we have extra baby clothes and blankets, leave a message and i will set them out",
     "resource", "standard", "none"),
    ("commercial generator available, can power a shelter for two days, needs diesel",
     "resource", "high", "none"),
    ("licensed plumber, free pipe inspections in the flood zone today",
     "resource", "high", "none"),
    ("our ranch has open pasture, can take in evacuated horses",
     "resource", "standard", "none"),
    # ---- noise (6) ----
    ("the mayor never does anything for this side of town, typical",
     "noise", "low", "none"),
    ("garage sale this saturday, lots of tools and furniture, come by",
     "noise", "low", "none"),
    ("they say the dam is about to break, evacuate everyone now!!!",
     "noise", "low", "misinformation"),
    ("praying for all our neighbors tonight, stay safe",
     "noise", "low", "none"),
    ("traffic is backed up for miles on the highway, avoid it",
     "noise", "low", "none"),
    ("FEMA is giving away free grants, just send your bank info to relief-funds dot xyz to claim",
     "noise", "low", "scam"),
    # ---- unclear (2) ----
    ("not again, i cant believe this",
     "unclear", "low", "none"),
    ("let me know when youre ready",
     "unclear", "low", "none"),
]


def main():
    rng = random.Random(SEED)
    order = list(range(len(SIGS)))
    rng.shuffle(order)  # seeded shuffle makes SEED load-bearing for ID assignment
    out = []
    for new_i, old_i in enumerate(order):
        text, lane, urgency, risk = SIGS[old_i]
        out.append({"id": f"R-{new_i+1:03d}", "text": text,
                    "lane": lane, "urgency": urgency, "risk": risk})
    assert len(out) == 40 and len({s["id"] for s in out}) == 40
    assert sorted(s["id"] for s in out) == [f"R-{i:03d}" for i in range(1, 41)]

    # --- anti-cheat: no verbatim overlap with phase-10 corpus, phase-8 holdout ---
    mine = {s["text"].strip().lower() for s in out}
    p10 = json.load(open("/home/hatch/workspace/decide-work/phase10/calibration.json"))
    p10_texts = {s["text"].strip().lower() for s in p10}
    fx = json.load(open("/home/hatch/workspace/decide-work/phase8/memory-holdout/fixtures8.json"))
    hold_texts = {s["text"].strip().lower() for s in fx["holdout"]}
    for s in out:
        t = s["text"].strip().lower()
        assert t not in p10_texts, f"phase-10 overlap: {s['id']}"
        assert t not in hold_texts, f"holdout overlap: {s['id']}"
        # and none of my own texts duplicate
    assert len(mine) == 40, "internal duplicates in fresh corpus"

    d = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(d, "calibration_fresh.json")
    json.dump({"seed": SEED, "date": "2026-10-05", "signals": out}, open(p, "w"), indent=1)
    from collections import Counter
    print(f"wrote {p}: 40 signals (seed {SEED})")
    print(" lanes:", dict(Counter(s["lane"] for s in out)))
    print(" urgency:", dict(Counter(s["urgency"] for s in out)))
    print(" risk:", dict(Counter(s["risk"] for s in out)))


if __name__ == "__main__":
    main()
