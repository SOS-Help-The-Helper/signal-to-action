"""The loops framework — design spec distilled from the canonical loops doc.

Status: design spec distilled from the canonical loops doc 2026-10-03/05.
Inner-loop publishability verdicts live in the paper, not here.

Structure (not prose):
  OUTER_STAGES         — the 7 Signal-to-Action stages in order; each Stage
                         carries a 1-2 line contract, a typed-handoff note,
                         and its lane (None where the doc assigns none)
  Lane                 — the four functional lanes: sorting, synthesis,
                         guarantee, decision
  INNER_LOOPS          — the four inner loops: name, subtitle, step sequence,
                         plus gating, decay/expiry, and the holdout claim the
                         falsifiable bar requires
  validate_loop        — structural validator: rejects loops with no gating
                         description or no decay/expiry
  NON_COLLAPSIBLE_RULES, language rules, naming constants

The shared inner-loop grammar is Observe -> Update persistent state ->
Steer future decisions. The falsifiable bar: the Update must be gated
(validation, attribution, expiry, anti-poison), must carry decay/expiry,
and must change a specified decision distribution by a measurable amount on
a sealed holdout versus a frozen-update counterfactual — otherwise the loop
is defective. A subsystem that writes and steers but is poisoned,
Sybil-captured, or oscillating is a *defective loop*, not a pass.
"""

from dataclasses import dataclass
from enum import Enum

# ---------------------------------------------------------------------------
# Lanes (functional names; no new proper nouns coined)
# ---------------------------------------------------------------------------


class Lane(Enum):
    SORTING = "sorting"      # decision models produce Judgment
    SYNTHESIS = "synthesis"  # LLMs produce Proposal and synthesis, after
                             # judgment, never instead of it
    GUARANTEE = "guarantee"  # deterministic systems: IDs, ledger, math,
                             # the SOS scorer
    DECISION = "decision"    # humans at the gate


# ---------------------------------------------------------------------------
# Outer loop: the 7 Signal-to-Action stages, in order
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Stage:
    """One outer-loop stage: its contract, its typed handoff, its lane."""

    name: str
    description: str
    handoff: str
    lane: "Lane | None" = None


OUTER_STAGES = (
    Stage(
        name="Signal",
        description="A request arrives. The phone number is the one required "
        "field: an intake without a reachable number is a dead end. "
        "PII isolation begins here.",
        handoff="Typed intake payload (request + reachable contact) written "
        "to the ledger; anonymized before any vendor sees the payload.",
    ),
    Stage(
        name="Judgment",
        description="A typed decision on the signal: relevance; lane (request "
        "vs resource); duplicate_of; urgency; risk; route_to. Produced by "
        "cheap typed decision models behind a vendor-neutral, eval-gated "
        "decide() seam. 'Unknown' is a valid output.",
        handoff="Evidence and interpretation travel in separate fields: only "
        "deterministic/typed tools write evidence fields; LLMs write "
        "interpretation fields.",
        lane=Lane.SORTING,
    ),
    Stage(
        name="Proposal",
        description="Scored options for fulfilling the request, synthesized "
        "(LLM lane) only after deterministic scorers narrow the tier. "
        "Nothing commits itself.",
        handoff="Scores only — never writes, never contacts anyone.",
        lane=Lane.SYNTHESIS,
    ),
    Stage(
        name="Human Decision",
        description="A person approves, rejects, or redirects. Humans own "
        "irreversible decisions; the gate is load-bearing.",
        handoff="Authorization handoff; the override is captured for the "
        "Evaluation Loop.",
        lane=Lane.DECISION,
    ),
    Stage(
        name="Action",
        description="The decision executes. A decision is not proof of "
        "execution.",
        handoff="The Coordination Loop runs inside this stage "
        "(Match -> Route -> Commit -> Track -> Learn).",
    ),
    Stage(
        name="Outcome",
        description="What actually happened, recorded honestly, win or lose.",
        handoff="Per-referral outcomes land in the append-only ledger first.",
    ),
    Stage(
        name="Learning",
        description="Every outcome feeds learning. Learnings are typed "
        "(defect / process / model / reliability / domain / operations) and "
        "must become checkable mechanisms — rules, thresholds, corrected "
        "exemplars — never prose advice.",
        handoff="Checkable memory writes (rules, exemplars, thresholds) into "
        "the memory store; prose advice is excluded by policy.",
    ),
)


# ---------------------------------------------------------------------------
# Non-collapsible rules
# ---------------------------------------------------------------------------

NON_COLLAPSIBLE_RULES = (
    "No stage is skipped or silently collapsed: any bypass (e.g. a life-safety "
    "fast path) is itself a logged ledger event requiring standing authorization.",
    "Evidence stays separate from interpretation (separate fields, separate writers).",
    "'Unknown' is a valid judgment output.",
    "A decision is not proof of execution.",
    "Humans own irreversible decisions; the gate is load-bearing.",
    "Every outcome feeds learning.",
    "Stage tools communicate through the append-only ledger — never hidden side "
    "channels.",
)


# ---------------------------------------------------------------------------
# Inner loops
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InnerLoop:
    """An inner loop: name, subtitle, step sequence, plus the three things
    the falsifiable bar requires — gating, decay/expiry, and the specified
    decision distribution its Update must move on a sealed holdout."""

    name: str
    subtitle: str
    steps: tuple
    description: str = ""
    gating: str = ""
    decay: str = ""
    holdout_claim: str = ""


COORDINATION_LOOP = InnerLoop(
    name="Coordination Loop",
    subtitle="maintains the commitment record",
    steps=("Match", "Route", "Commit", "Track", "Learn"),
    description="The fulfillment flywheel: once a decision authorizes action, "
    "this loop matches the request to resources, routes it, commits (a human "
    "commit step; the no-phantom-matches invariant), tracks it to completion, "
    "and records the referral's outcome into the ledger. Its Learn step is a "
    "feed into outer Outcome/Learning, not a second learning system.",
    gating="Human commit step before routing (no-phantom-matches invariant); "
    "cannot bypass the human gate — Commit sits before it structurally.",
    decay="Commitment records close on fulfillment or expire; stale "
    "commitments age out so routing reads the live record, not history.",
    holdout_claim="Changes the share of requests routed to live, available "
    "commitments versus stale/duplicate commitments.",
)

MEMORY_LOOP = InnerLoop(
    name="Memory Loop",
    subtitle="maintains the decision rules",
    steps=("Outcome", "Memory", "Judgment"),
    description="Outcomes become memories that sharpen future judgment. Only "
    "checkable memories compound: corrected exemplars, deterministic rules, "
    "calibrated thresholds. Prose advice is excluded by policy.",
    gating="Only checkable memories compound; prose advice excluded by policy; "
    "adversarial write gate against poisoned or Sybil-written memories.",
    decay="Memories carry expiry; contradictions and oscillating memories are "
    "retired rather than left to steer.",
    holdout_claim="Changes the judgment accuracy distribution on a sealed "
    "holdout (lab direction: corrected exemplars improved internal judgment "
    "accuracy; 'compound' is a convergence claim until the convergence test "
    "passes).",
)

TRUST_LOOP = InnerLoop(
    name="Trust Loop",
    subtitle="maintains the routing weights",
    steps=("Evidence", "Score", "Routing weight"),
    description="Evidence about helpers/resources becomes scores; scores "
    "become routing weight — the right helpers get the right requests. "
    "Always framed as routing optimization, not person-rating.",
    gating="Sybil-resistant gate before scores compound; trust propagation is "
    "scoped per-deployment over a disclosed seed set.",
    decay="Scores decay with age and refresh on new evidence; live "
    "availability/capacity feeds keep weights current (routing to a full "
    "shelter is referral theater).",
    holdout_claim="Changes the distribution of fulfillment outcomes for "
    "higher- versus lower-weighted helpers on a sealed holdout.",
)

EVALUATION_LOOP = InnerLoop(
    name="Evaluation Loop",
    subtitle="maintains the calibration set",
    steps=("Override", "Eval set", "Calibration"),
    description="Every human override is captured, labeled, and lands in the "
    "eval set; eval sets recalibrate per-model per-verdict thresholds. "
    "Global confidence floors are dead.",
    gating="Sealed holdout plus protected grader; two-window breaker on "
    "gaming; override-rate evidence is what moves the autonomy gate.",
    decay="Thresholds recalibrate on drift; stale calibrations expire; the "
    "eval set accumulates and recalibrates continuously rather than "
    "assuming ML stasis.",
    holdout_claim="Changes per-model per-verdict calibration error (ECE) on "
    "the sealed holdout versus a frozen-calibration counterfactual.",
)

INNER_LOOPS = (
    COORDINATION_LOOP,
    MEMORY_LOOP,
    TRUST_LOOP,
    EVALUATION_LOOP,
)


class LoopSpecError(ValueError):
    """Raised when a loop spec fails structural validation."""


def validate_loop(loop):
    """Structurally enforce the falsifiable bar.

    A loop is defective unless it has: a step sequence, a gating description
    (validation / attribution / expiry / anti-poison), and a decay/expiry
    description. Returns True for a well-formed loop; raises LoopSpecError
    otherwise.
    """
    name = getattr(loop, "name", None) or "<unnamed>"
    problems = []
    steps = getattr(loop, "steps", None) or ()
    if not steps:
        problems.append("no step sequence")
    gating = (getattr(loop, "gating", "") or "").strip()
    if not gating:
        problems.append("no gating description (validation/attribution/expiry/anti-poison)")
    decay = (getattr(loop, "decay", "") or "").strip()
    if not decay:
        problems.append("no decay/expiry description")
    if problems:
        raise LoopSpecError(
            f"loop {name!r} is structurally defective: {'; '.join(problems)}"
        )
    return True


# ---------------------------------------------------------------------------
# Language rules (hard, apply to everything)
# ---------------------------------------------------------------------------

REQUEST_NOUN = "requests"    # what people have — never "needs" as a noun
RESOURCE_NOUN = "resources"  # what helpers provide — never "offers" as a noun
HELPER_NOUN = "helpers"      # people who help — never "volunteers"
FORBIDDEN_LABEL = "survivor"  # never for people getting help
# Standing exception: the exact line "There are no survivors / Only helpers".

# ---------------------------------------------------------------------------
# Naming (settled)
# ---------------------------------------------------------------------------

FRAMEWORK = "Signal-to-Action"       # the framework
ENGINE = "Relay"                     # the engine that runs the framework
JUDGMENT = "Judgment"                # user-facing name of stage 2
VENDOR_DECISION_MODEL = "TypeSafe Jev"  # vendor model behind the decide() seam
INTERNAL_SCORER = "SOS scorer"       # internal deterministic match scorer;
                                     # never bare "Jev" for internal work


__all__ = [
    "Lane",
    "Stage",
    "OUTER_STAGES",
    "NON_COLLAPSIBLE_RULES",
    "InnerLoop",
    "COORDINATION_LOOP",
    "MEMORY_LOOP",
    "TRUST_LOOP",
    "EVALUATION_LOOP",
    "INNER_LOOPS",
    "LoopSpecError",
    "validate_loop",
    "REQUEST_NOUN",
    "RESOURCE_NOUN",
    "HELPER_NOUN",
    "FORBIDDEN_LABEL",
    "FRAMEWORK",
    "ENGINE",
    "JUDGMENT",
    "VENDOR_DECISION_MODEL",
    "INTERNAL_SCORER",
]
