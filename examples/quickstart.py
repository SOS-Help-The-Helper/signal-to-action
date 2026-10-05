"""5-minute quickstart: Signal -> Judgment -> Proposal -> Human Decision ->
Action -> Outcome -> Learning, on synthetic data.

Run from the repo root (the directory containing `signal_action/`):

    python examples/quickstart.py

Zero dependencies beyond the package. Finishes in seconds.

What this is: a walkthrough of the 7 outer-loop stage contracts on three
synthetic signals. The Judgment step uses a tiny keyword heuristic as a
STAND-IN for the typed decision models behind the decide() seam — it is a
demo prop, not a judgment engine. Scrubbing is real: every record passes
through the production scrubber before anything else sees it.

What this is not: a claim about accuracy, a production pipeline, or a
substitute for the test program. See the paper for measured results.
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signal_action.capture.adapters.base import NormalizedRecord
from signal_action.capture.feed import prepare_record
from signal_action.loops import OUTER_STAGES

# Synthetic signals only. The second one carries planted PII to show the
# scrubber working; the third is noise the judgment stand-in should ignore.
SIGNALS = [
    {
        "id": "sig-001",
        "text": ("Maria's porch steps washed out in the storm. She needs a "
                 "ride to the shelter on 5th street before dark. "
                 "Reachable at the number on file."),
        "expect": "request",
    },
    {
        "id": "sig-002",
        "text": ("I can drive a truck Saturday. Email me at "
                 "driver.jane@example.com or call +1-555-014-8890 to "
                 "coordinate pickup of donated supplies."),
        "expect": "resource",
    },
    {
        "id": "sig-003",
        "text": "Anyone know a good taco place near the fairgrounds?",
        "expect": "none",
    },
]

REQUEST_WORDS = {"need", "needs", "ride", "shelter", "help", "stranded",
                 "urgent", "request"}
RESOURCE_WORDS = {"offer", "drive", "truck", "donate", "volunteer",
                  "supplies", "available", "coordinate"}


def toy_judgment(text: str) -> dict:
    """Keyword-heuristic STAND-IN for the decide() seam. Demo prop only."""
    toks = set(text.lower().replace("'", "").split())
    req = len(toks & REQUEST_WORDS)
    res = len(toks & RESOURCE_WORDS)
    if req > res:
        return {"lane": "request", "route_to": "coordination",
                "confidence": 0.6, "verdict": "confirm"}
    if res > req:
        return {"lane": "resource", "route_to": "coordination",
                "confidence": 0.6, "verdict": "confirm"}
    return {"lane": "none", "route_to": "ignore",
            "confidence": 0.8, "verdict": "reject"}


def run_signal(sig: dict) -> dict:
    print(f"\n=== {sig['id']} ===")
    trace = {"signal_id": sig["id"], "stages": {}}

    # 1. Signal — normalize, then scrub before anything downstream sees it.
    rec = NormalizedRecord(
        platform="quickstart", agent_id="", session_id="demo",
        ts="2026-10-05T00:00:00+00:00", role="user", content=sig["text"],
        message_id=sig["id"],
    )
    scrubbed = prepare_record(rec)
    leaked = ("example.com" in scrubbed.content or "555-014" in scrubbed.content)
    print(f"[1] Signal:    captured + scrubbed "
          f"({'PII redacted' if sig['id'] == 'sig-002' else 'clean'}"
          f"{'; LEAK!' if leaked else ''})")
    trace["stages"]["Signal"] = "captured+scrubbed"

    # 2. Judgment — toy heuristic stands in for the typed decision model.
    j = toy_judgment(scrubbed.content)
    match = "MATCH" if j["lane"] == sig["expect"] else "MISS"
    print(f"[2] Judgment:  lane={j['lane']} route={j['route_to']} "
          f"verdict={j['verdict']} conf={j['confidence']} [{match} vs expected]")
    trace["stages"]["Judgment"] = j

    # 3-7. Walk the remaining stage contracts with the judgment's output.
    proposal = (f"propose {j['lane']} -> {j['route_to']}"
                if j["verdict"] == "confirm" else "no proposal (rejected)")
    print(f"[3] Proposal:  {proposal}")
    decision = ("human confirms" if j["verdict"] == "confirm"
                else "human agrees: ignore")
    print(f"[4] Human Decision: {decision} (human at the gate, always)")
    action = ("routed to coordination queue" if j["verdict"] == "confirm"
              else "no action taken")
    print(f"[5] Action:    {action}")
    outcome = ("pending in this demo (no real world attached)"
               if j["verdict"] == "confirm" else "n/a")
    print(f"[6] Outcome:   {outcome}")
    learning = ("would record: judgment {v} on lane={lane}".format(
        v=j["verdict"], lane=j["lane"]))
    print(f"[7] Learning:  {learning}")
    trace["stages"]["Proposal"] = proposal
    trace["stages"]["Human Decision"] = decision
    trace["stages"]["Action"] = action
    trace["stages"]["Outcome"] = outcome
    trace["stages"]["Learning"] = learning
    trace["expected"] = sig["expect"]
    return trace


def main() -> int:
    print("Signal-to-Action quickstart — synthetic demo, seconds to run.")
    print("Judgment below is a KEYWORD HEURISTIC stand-in, not the decide() seam.")
    traces = [run_signal(s) for s in SIGNALS]

    confirmed = sum(1 for t in traces
                    if t["stages"]["Judgment"]["verdict"] == "confirm")
    hits = sum(1 for t in traces
               if t["stages"]["Judgment"]["lane"] == t["expected"])
    print("\n--- learning summary ---")
    print(f"signals processed: {len(traces)}")
    print(f"confirmed: {confirmed}, rejected: {len(traces) - confirmed}")
    print(f"toy-judgment lane hits: {hits}/{len(traces)}")
    print("learning recorded: 3 judgment traces (lane, verdict, confidence) "
          "ready for the memory bank")
    print("\nNext: point it at your own data — "
          "python examples/chatgpt_export.py /path/to/conversations.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
