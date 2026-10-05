# Signal-to-Action

The open framework for turning scattered signals into coordinated action.

**The premise:** the community is there. The coordination isn't. Signals are everywhere — requests for help, offers of resources, reports from the ground. Action is nowhere, because nothing connects the two. Signal-to-Action is the loop that does.

## The loop

Seven stages, one outer loop:

**Signal → Judgment → Proposal → Human Decision → Action → Outcome → Learning**

Cheap, typed models sort (Judgment). Large models draft (Proposal). Humans own every irreversible call (Decision). Outcomes become versioned, checkable rules that sharpen future judgment (Learning). Nothing in the loop is a black box you can't audit.

## Loops within the loop

Four smaller loops spin inside the big one. Each maintains one artifact:

- **Coordination Loop** — *maintains the commitment record.* Match → Route → Commit → Track → Learn. Lives inside the Action stage. No referral is ever forgotten.
- **Memory Loop** — *maintains the decision rules.* Outcome → Memory → Judgment. Only validated, checkable rules compound.
- **Trust Loop** — *maintains the routing weights.* Evidence → Score → Routing weight. Routing optimization, never person-rating.
- **Evaluation Loop** — *maintains the calibration set.* Overrides become eval data; eval data recalibrates confidence.

One shared grammar: **Observe → Update persistent state → Steer future decisions.** Every update is gated, measured against a frozen-update counterfactual, and expires unless re-earned.

## What's open, what's not

This repo is the open framework: the loop, the stage contracts, the inner-loop grammar, the capture adapters. Build on it.

What stays private is the learning substrate — the tuned parameters, the utility calibration, the compounding memory banks. The mechanism is open; the accumulated learning is the moat. That's the open-core split, stated plainly.

## Status

Early. The reference implementation is [SOS](https://sosconnect.org), running the loop for community coordination. The paper — with the full test program, honest negatives included — is at the link below.

## The paper

**Signal-to-Action: The Framework** — the coordination problem and solution, with testing data, modeling, and the failures kept in the record.

---

*The generosity arrives on its own. What it needs is a loop.*
