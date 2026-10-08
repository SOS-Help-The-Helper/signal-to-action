# Signal-to-Action: The Canonical Guide

**STA — Signal-to-Action.** The framework for turning a flood of messy incoming signals into reliable, human-approved action that learns from every outcome.

This document is the single canonical reference. It subsumes and replaces `signal-to-action-brief-for-fresh-agent.md`. Any agent with no prior context must be able to load this guide and deeply understand STA: what it is, what it is not, how its seven stages and four inner loops fit together, where the code lives, what has been proven, what has failed, and what is still missing.

Every claim about a decision carries its date. Uncertain items are labeled as such. Verbatim Jonathan quotes are included only where verified, with provenance — the guide names the verbatim deficit explicitly instead of filling it.

---

## 1. BOOTSTRAP — Load this first

**What STA is, in 30 lines:**

1. STA is a framework, not a product and not a prompt. It defines how any stream of incoming signals becomes coordinated action.
2. The outer loop has seven stages, in fixed order: **Signal → Judgment → Proposal → Human Decision → Action → Outcome → Learning**.
3. No stage is skipped or silently collapsed. A life-safety fast path, if one exists, is itself a logged ledger event requiring standing authorization.
4. Judgment comes before proposal. Cheap typed decision models sort; expensive LLMs draft. Never the reverse.
5. `decide()` is only a socket inside Judgment — a vendor-neutral, eval-gated seam where TypeSafe Jev, Clef, deterministic providers, or another model can sit. It is not the framework.
6. Humans own irreversible decisions. The Human Decision gate is load-bearing and does not collapse under load.
7. A decision is not proof of execution. Action must be tracked to an Outcome.
8. Every outcome feeds Learning. Learnings are checkable mechanisms — rules, thresholds, corrected exemplars — never prose advice.
9. Four lanes divide the work: **SORTING** (decision models produce Judgment), **SYNTHESIS** (LLMs produce Proposal, after judgment, never instead of it), **GUARANTEE** (deterministic systems: IDs, ledger, math, the SOS scorer — no AI in the record-keeping path, ever), **DECISION** (humans at the gate).
10. Four inner loops spin inside the outer loop: **Coordination** (Match → Route → Commit → Track → Learn, lives inside Action), **Memory** (Outcome → Memory → Judgment), **Trust** (Evidence → Score → Routing weight), **Evaluation** (Override → Eval set → Calibration).
11. A loop without gating, decay/expiry, and a measurable holdout claim is defective. Those three are the falsifiable bar.
12. All stage communication goes through an append-only, hash-chained ledger. No hidden side channels. "Prove it" is a feature: any decision must be replayable from the ledger alone.
13. Evidence and interpretation travel in separate fields, written by separate writers. Deterministic/typed tools write evidence; LLMs write interpretation.
14. "Unknown" is a valid Judgment output.
15. The model cascade is gated by confidence: decision model (~$0.0001, ~100ms) → workhorse LLM (~$0.01, 2–5s) → frontier LLM (~$0.10+, 10s+). The cheap model is the bouncer.
16. **Relay** is the engine that runs the complete machine side of all seven stages, the four inner loops, gates, ledger, and state. STA is the framework (what/why); Relay is the engine (how it runs). Humans retain the Decision lane — Relay routes, enforces, and records; it never replaces the human gate.
17. Relay is hosted. Every implementation is a thin tenant: persona + domain + `loop-config.yaml`. Core loop logic, ledger, and learning live in one Relay — tenants clone the connection, not the code.
18. Cross-tenant learning is allowed only with consent: per-tenant `share_learning` toggle, default ON, contribution only when consented (decided 2026-10-06).
19. One engine rule: build the loop once, in Relay, and point every tenant at it. Do not fork the loop per project.
20. SOS, Impacted, Wingman, and Jerry are implementations/tenants of STA — each at a different stage of conformance (see §13). SOS production today runs bespoke STA-like code; the canonical `signal_action` package exists with tests but is not yet imported into SOS production (verified 2026-10-07).
21. Language is settled and non-negotiable: what people have are **requests**, what helpers provide are **resources**, people who help are **helpers**. Never "needs"/"offers" as domain nouns, never "volunteers," never the forbidden label for people getting help (see §2).
22. If you remember nothing else: **sort cheap, draft expensive, gate irreversible decisions with a human, record everything in the ledger, and turn every outcome into a checkable rule.**

---

## 2. Glossary and non-negotiable terminology

These terms are settled. Use them exactly. The machine-readable source is `signal_action/loops/__init__.py` (`FRAMEWORK`, `ENGINE`, `JUDGMENT`, `VENDOR_DECISION_MODEL`, `INTERNAL_SCORER`, `REQUEST_NOUN`, `RESOURCE_NOUN`, `HELPER_NOUN`, `FORBIDDEN_LABEL`).

| Term | Exact meaning |
|---|---|
| **Signal-to-Action (STA)** | The framework. What the system does and why: the seven-stage outer loop, four inner loops, four lanes, ledger spine, cascade economics, and the rules that bind them. Settled name; "STA" is the shorthand in use from 2026-10-06 onward (see §14). |
| **Relay** | The engine. The hosted system that runs the complete machine side of all seven stages, the four inner loops, gates, ledger, and state. STA is the framework; Relay is the engine that runs it. Settled 2026-10-03 (naming review) and 2026-10-05 (three-layer model). |
| **Signal** | Stage 1. Raw incoming material: a text, a ticket, a sensor ping, a lead form, a disaster report. In SOS intake, the phone number is the one required field — an intake without a reachable number is a dead end. PII isolation begins here. |
| **Judgment** | Stage 2. A typed decision on the signal: relevance; lane (request vs resource); `duplicate_of`; urgency; risk; `route_to`. Produced by cheap typed decision models behind the `decide()` seam. User-facing name of stage 2 is "Judgment." |
| **decide()** | The vendor-neutral, eval-gated seam inside Judgment. A socket, not the framework. TypeSafe Jev, Clef, deterministic providers, or another decision model swap through this seam after passing the eval gate. Originally built to swap benchmark judges. |
| **TypeSafe Jev** | The vendor decision model behind the `decide()` seam (`VENDOR_DECISION_MODEL`). External/vendor judgment engine. |
| **SOS scorer** | The internal deterministic match scorer (`INTERNAL_SCORER`). Score → Propose → Commit. Never call internal scoring work bare "Jev" — that name belongs to the vendor model. |
| **Proposal** | Stage 3. Scored options for fulfilling the request, synthesized by the LLM lane only after deterministic scorers narrow the tier. A proposal never writes, never contacts anyone, never commits itself. |
| **Human Decision** | Stage 4. A person approves, rejects, or redirects. Humans own irreversible decisions. The override is captured for the Evaluation Loop. |
| **Action** | Stage 5. The authorized decision executes. The Coordination Loop runs inside this stage. |
| **Outcome** | Stage 6. What actually happened, recorded honestly, win or lose. Per-referral outcomes land in the append-only ledger first. |
| **Learning** | Stage 7. Every outcome feeds learning. Learnings are typed — defect / process / model / reliability / domain / operations — and must become checkable mechanisms. Prose advice is excluded by policy. |
| **Coordination Loop** | Inner loop inside Action: Match → Route → Commit → Track → Learn. Maintains the commitment record. Its Learn step feeds outer Outcome/Learning; it is not a second learning system. |
| **Memory Loop** | Inner loop: Outcome → Memory → Judgment. Maintains the decision rules. Only checkable memories compound. |
| **Trust Loop** | Inner loop: Evidence → Score → Routing weight. Maintains the routing weights. Framed as routing optimization, not person-rating. In SOS product language the score is XP with autonomy tiers (see §12/§13); the loop mechanism is the same: evidence becomes a score, the score becomes routing weight. |
| **Evaluation Loop** | Inner loop: Override → Eval set → Calibration. Maintains the calibration set. Every human override is captured, labeled, and used to recalibrate per-model per-verdict thresholds. Global confidence floors are dead. |
| **Ledger** | The append-only, hash-chained, replayable record every stage writes to. The spine. See §8. |
| **Lane** | One of four functional divisions of labor: SORTING, SYNTHESIS, GUARANTEE, DECISION. See §5. No new proper nouns are coined for lanes. |
| **Tenant** | A thin Relay implementation: persona + domain + `loop-config.yaml` pointing at Relay. Core loop logic, ledger, and learning live in Relay, not in the tenant. Settled 2026-10-06. |
| **share_learning** | Per-tenant toggle controlling whether a tenant contributes to cross-tenant learning. Default ON for current projects; contribution only when consented. Decided 2026-10-06. |
| **Checkable memory** | A learning expressed as a corrected exemplar, a deterministic rule, or a calibrated threshold — something the system can verify on the next pass. The only kind of memory that compounds. |
| **Holdout claim** | The specified decision distribution an inner loop's Update must move, measured on a sealed holdout versus a frozen-update counterfactual. Part of the falsifiable bar (§6). |

### Language rules (hard, apply to everything)

From the loops spec, verbatim in intent:

- **requests** — what people have. Never "needs" as a domain noun.
- **resources** — what helpers provide. Never "offers" as a domain noun.
- **helpers** — people who help. Never "volunteers."
- The forbidden label for people getting help is never used. Standing exception: the exact line "There are no survivors / Only helpers".

Ordinary English verb use ("communities need coordination") is fine. The rule governs domain nouns in copy, product UI, specs, and replies.

---

## 3. What STA is NOT

These negations are as load-bearing as the definitions. Each one corrects a real misreading that has occurred in this project's history.

- **STA is not an LLM prompt.** There is no prompt that "is" STA. The framework is stages, typed handoffs, lanes, gates, and a ledger. A prompt lives inside at most two lanes (SORTING support and SYNTHESIS); it cannot be the framework.
- **STA is not just `decide()`.** `decide()` is only a socket inside Judgment — one seam in stage 2 of 7. Treating the seam as the framework collapses the loop and loses Proposal, the human gate, Action tracking, Outcome, and Learning. The seam is built; the framework around it is the larger thing.
- **The outer loop is NOT called "coordination."** Coordination is the name of one inner loop (Match → Route → Commit → Track → Learn) that lives inside Action. Calling the whole outer loop "coordination" was killed in the 2026-10-05 naming audit, which also killed the paper title "The Coordination Paper" in favor of "Signal-to-Action: The Framework" (see §14).
- **STA is not an LLM wrapper.** The GUARANTEE lane — IDs, ledger, math, the SOS scorer — contains no AI at all, by design. A system that routes its record-keeping through an LLM is not STA; the fault-injection test in §14 exists precisely to prove this spine is load-bearing.
- **STA is not a chatbot pattern.** Wingman is a full STA implementation, not a chatbot using the pattern (Jonathan, 2026-10-06). A conversational surface may be the front door (SOS/Impacted intake), but the loop behind it — judgment, proposal, gate, tracked action, outcome, learning — is the product. A bot that answers and forgets is not running STA.
- **STA is not a funnel.** The structure is loops within a loop — flywheels within flywheels — because Learning feeds Judgment and Trust feeds routing. A funnel ends; STA compounds.
- **A score is not a match, and a proposal is not an actioned match.** From the SOS scorer contract: SCORE ranks, PROPOSE persists a shortlist for a human, COMMIT is the only step that connects anyone. The no-phantom-matches invariant (§6) holds across every tenant.

---

## 4. The seven-stage outer loop

The machine-readable source is `~/workspace/signal-action-distill/signal_action/loops/__init__.py`, `OUTER_STAGES`. The contracts below quote that spec faithfully. Each stage lists: contract, typed handoff, lane (where the spec assigns one; `None` in the spec means the stage is not lane-bound in the same way — do not invent an assignment).

### Stage 1 — Signal

- **Contract:** "A request arrives. The phone number is the one required field: an intake without a reachable number is a dead end. PII isolation begins here."
- **Typed handoff:** "Typed intake payload (request + reachable contact) written to the ledger; anonymized before any vendor sees the payload."
- **Lane:** None assigned in the spec.

### Stage 2 — Judgment

- **Contract:** "A typed decision on the signal: relevance; lane (request vs resource); duplicate_of; urgency; risk; route_to. Produced by cheap typed decision models behind a vendor-neutral, eval-gated decide() seam. 'Unknown' is a valid output."
- **Typed handoff:** "Evidence and interpretation travel in separate fields: only deterministic/typed tools write evidence fields; LLMs write interpretation fields."
- **Lane:** SORTING.

### Stage 3 — Proposal

- **Contract:** "Scored options for fulfilling the request, synthesized (LLM lane) only after deterministic scorers narrow the tier. Nothing commits itself."
- **Typed handoff:** "Scores only — never writes, never contacts anyone."
- **Lane:** SYNTHESIS.

### Stage 4 — Human Decision

- **Contract:** "A person approves, rejects, or redirects. Humans own irreversible decisions; the gate is load-bearing."
- **Typed handoff:** "Authorization handoff; the override is captured for the Evaluation Loop."
- **Lane:** DECISION.

### Stage 5 — Action

- **Contract:** "The decision executes. A decision is not proof of execution."
- **Typed handoff:** "The Coordination Loop runs inside this stage (Match -> Route -> Commit -> Track -> Learn)."
- **Lane:** None assigned in the spec.

### Stage 6 — Outcome

- **Contract:** "What actually happened, recorded honestly, win or lose."
- **Typed handoff:** "Per-referral outcomes land in the append-only ledger first."
- **Lane:** None assigned in the spec.

### Stage 7 — Learning

- **Contract:** "Every outcome feeds learning. Learnings are typed (defect / process / model / reliability / domain / operations) and must become checkable mechanisms — rules, thresholds, corrected exemplars — never prose advice."
- **Typed handoff:** "Checkable memory writes (rules, exemplars, thresholds) into the memory store; prose advice is excluded by policy."
- **Lane:** None assigned in the spec.

---

## 5. The four lanes

Lanes divide labor by kind of work, not by vendor or team. Source: `Lane` enum in the loops spec. "Functional names; no new proper nouns coined."

### SORTING — decision models produce Judgment

Cheap, fast, typed. This lane runs stage 2. The tools here are small decision models behind the `decide()` seam — TypeSafe Jev, Clef, deterministic providers — evaluated and swapped through the eval gate (§11, HAR-47). The lane's output is typed fields: relevance, lane, `duplicate_of`, urgency, risk, `route_to`. "Unknown" is a valid output of this lane.

### SYNTHESIS — LLMs produce Proposal

LLMs produce Proposal and synthesis, **after judgment, never instead of it** (spec comment, verbatim in intent). This lane runs stage 3. Given a Judgment and a deterministically narrowed tier, the LLM drafts the plan, the message, the outreach. It never sorts raw signals as a substitute for Judgment, and its output commits nothing.

### GUARANTEE — deterministic systems

IDs, ledger, math, the SOS scorer. No AI in the record-keeping path, ever. This lane owns identity assignment, the append-only ledger (§8), deterministic scoring (§11, HAR-48), and every computation whose result must be reproducible bit-for-bit. If a result cannot be recomputed deterministically, it does not belong in this lane.

### DECISION — humans at the gate

People approve, reject, or redirect (stage 4). Irreversible calls stay human. Every override in this lane is captured and fed to the Evaluation Loop (§6). Relay and every tenant route work to this lane; they never absorb it.

---

## 6. The four inner loops

Source: `INNER_LOOPS` in the loops spec. Shared grammar for every inner loop: **Observe → Update persistent state → Steer future decisions.**

### The falsifiable bar (applies to all four)

> The Update must be gated (validation, attribution, expiry, anti-poison), must carry decay/expiry, and must change a specified decision distribution by a measurable amount on a sealed holdout versus a frozen-update counterfactual — otherwise the loop is defective. A subsystem that writes and steers but is poisoned, Sybil-captured, or oscillating is a *defective loop*, not a pass.

`validate_loop()` enforces the structural part of this bar in code: a loop spec with no step sequence, no gating description, or no decay/expiry description raises `LoopSpecError`. **A loop without gating, decay, and a measurable holdout claim is defective.** That sentence is the test every future loop proposal must pass before it is written up as a loop.

### 6.1 Coordination Loop — maintains the commitment record

- **Steps:** Match → Route → Commit → Track → Learn
- **Where it lives:** Inside Action (stage 5).
- **Description (spec):** "The fulfillment flywheel: once a decision authorizes action, this loop matches the request to resources, routes it, commits (a human commit step; the no-phantom-matches invariant), tracks it to completion, and records the referral's outcome into the ledger. Its Learn step is a feed into outer Outcome/Learning, not a second learning system."
- **Gating:** "Human commit step before routing (no-phantom-matches invariant); cannot bypass the human gate — Commit sits before it structurally."
- **Decay/expiry:** "Commitment records close on fulfillment or expire; stale commitments age out so routing reads the live record, not history."
- **Holdout claim:** "Changes the share of requests routed to live, available commitments versus stale/duplicate commitments."

### 6.2 Memory Loop — maintains the decision rules

- **Steps:** Outcome → Memory → Judgment
- **Description (spec):** "Outcomes become memories that sharpen future judgment. Only checkable memories compound: corrected exemplars, deterministic rules, calibrated thresholds. Prose advice is excluded by policy."
- **Gating:** "Only checkable memories compound; prose advice excluded by policy; adversarial write gate against poisoned or Sybil-written memories."
- **Decay/expiry:** "Memories carry expiry; contradictions and oscillating memories are retired rather than left to steer."
- **Holdout claim:** "Changes the judgment accuracy distribution on a sealed holdout (lab direction: corrected exemplars improved internal judgment accuracy; 'compound' is a convergence claim until the convergence test passes)."

### 6.3 Trust Loop — maintains the routing weights

- **Steps:** Evidence → Score → Routing weight
- **Description (spec):** "Evidence about helpers/resources becomes scores; scores become routing weight — the right helpers get the right requests. Always framed as routing optimization, not person-rating."
- **Gating:** "Sybil-resistant gate before scores compound; trust propagation is scoped per-deployment over a disclosed seed set."
- **Decay/expiry:** "Scores decay with age and refresh on new evidence; live availability/capacity feeds keep weights current (routing to a full shelter is referral theater)."
- **Holdout claim:** "Changes the distribution of fulfillment outcomes for higher- versus lower-weighted helpers on a sealed holdout."

In SOS product terms, the score in this loop is XP: everyone starts at a baseline, XP compounds through verified actions with no ceiling, network attribution shares XP with the inviter, and score gates are autonomy tiers — lower score means more human oversight, never exclusion (decided 2026-10-07). The loop mechanics (evidence → score → routing weight, with decay and a Sybil gate) are unchanged; the product framing keeps low XP from ever feeling like denied opportunity.

### 6.4 Evaluation Loop — maintains the calibration set

- **Steps:** Override → Eval set → Calibration
- **Description (spec):** "Every human override is captured, labeled, and lands in the eval set; eval sets recalibrate per-model per-verdict thresholds. Global confidence floors are dead."
- **Gating:** "Sealed holdout plus protected grader; two-window breaker on gaming; override-rate evidence is what moves the autonomy gate."
- **Decay/expiry:** "Thresholds recalibrate on drift; stale calibrations expire; the eval set accumulates and recalibrates continuously rather than assuming ML stasis."
- **Holdout claim:** "Changes per-model per-verdict calibration error (ECE) on the sealed holdout versus a frozen-calibration counterfactual."

---

## 7. Non-collapsible rules

Source: `NON_COLLAPSIBLE_RULES` in the loops spec. These seven rules are quoted from the spec; they bind every stage, every tenant, and every fast path.

1. **No stage is skipped or silently collapsed:** any bypass (e.g. a life-safety fast path) is itself a logged ledger event requiring standing authorization.
2. **Evidence stays separate from interpretation** (separate fields, separate writers).
3. **'Unknown' is a valid judgment output.**
4. **A decision is not proof of execution.**
5. **Humans own irreversible decisions; the gate is load-bearing.**
6. **Every outcome feeds learning.**
7. **Stage tools communicate through the append-only ledger — never hidden side channels.**

If a design needs to break one of these, the design is wrong. The correct move is to log the bypass as its own ledger event under standing authorization (rule 1) — never to quietly collapse a stage.

---

## 8. The ledger spine

Every stage writes to an **append-only, hash-chained ledger**. No hidden side channels (rule 7). Because the ledger is complete, any decision can be **replayed purely from the ledger** — and a replay that cannot reconstruct a decision is a test the ledger can fail. That is the accountability claim: "prove it" is a feature, not a slogan.

Properties, as established in the lab:

- **Append-only.** Records are added, never edited in place. Corrections are new entries.
- **Hash-chained.** Each entry binds to the previous entry's hash; tampering breaks the chain and is detectable.
- **Replayable.** The ledger alone must suffice to reconstruct why a signal was judged, proposed, approved, and actioned. The ledger replay + dispute exercise (§14, §15) is the distinctive test of this property and has not yet been run.
- **Dedicated writer, shared access revoked.** Hardened on the test environment: hash chain verified, append-only verified, dedicated writer credential, shared access revoked. Security tests SEC-1/2/3 green (2026-10-03, `~/workspace/decide-work/sec-123-results-2026-10-03.md`).
- **Regulatory mapping.** This shape maps to EU AI Act Article 12 auditability (record-keeping for high-risk AI systems). The mapping is a design claim from the program, stated here as such.

What the ledger is not: it is not a log file nobody reads, and it is not a database table that application code can quietly update. Henry Brain's `signal_traces` is the organism-level memory sink fed by this pattern (see §17); the per-tenant ledger in Relay is the system of record for that tenant's loop.

---

## 9. The cascade economics

Three tiers, gated by confidence. The cheap model is the bouncer deciding what deserves expensive-model time.

| Tier | Cost (approx.) | Latency (approx.) | Role |
|---|---|---|---|
| Decision model | ~$0.0001 | ~100ms | Handles everything it is confident about. This is the SORTING lane: typed Judgment on every signal. |
| Workhorse LLM | ~$0.01 | ~2–5s | Uncertain cases plus Proposals (SYNTHESIS lane). |
| Frontier LLM | ~$0.10+ | ~10s+ | Hardest cases only. Rare by design. |

Confidence gates the escalation. A signal the decision model judges confidently never touches an LLM. A low-confidence judgment escalates to the workhorse; still-uncertain or high-stakes cases escalate to the frontier tier. Threshold data lives in `~/workspace/decide-work/cascade-thresholds.json`.

Two honest qualifications from the test record (see §14): the "hybrid" appeal tier (LLM double-checks the cheap model on hard cases) has shown **no measurable gain** over Clef alone on the current corpus — 92.2% / 91.7% vs 92.8% — so the cascade's middle tier earns its place for Proposal synthesis, not (yet) for judgment appeals. And the economics are not the constraint on rigorous evaluation: the full 7-system comparison costs ~$1.13 in API spend; the scarce resource is human labeling (100 signals = 600 human judgments).

The pattern itself is industry-validated (the same shape as Sonnet→Opus routing, extended one tier down). What STA adds is the gate discipline: escalation is a ledger event, thresholds are per-model per-verdict (calibrated by the Evaluation Loop), and global confidence floors are dead.

---

## 10. Relay relationship

Settled in three layers on 2026-10-05, with the hosted-tenant model decided 2026-10-06:

1. **Signal-to-Action is the framework** — the what and the why. Seven stages, four inner loops, four lanes, ledger, cascade, rules. This guide.
2. **Relay is the engine** that runs the complete machine side of all seven stages, the four inner loops, the gates, the ledger, and the state.
3. **The guarantees/test harness is the portable proof layer** — the eval gates, holdouts, and security tests that let any tenant (or auditor) verify a Relay deployment actually behaves as the framework requires.

**Humans retain the Decision lane.** Relay routes work to the gate, enforces that the gate happened, and records the outcome. It never replaces the human at the gate. A Relay feature that approves its own proposals is a framework violation, not an optimization.

### The hosted Relay model (decided 2026-10-06)

- Relay is hosted. Every implementation — Impacted, Wingman, SOS, Jerry, future coaches and companies — is a **thin tenant**: persona + domain + `loop-config.yaml` pointing at Relay.
- Core loop logic, ledger, and learning live in one Relay. Tenants clone the connection, not the code. ("Clone the connection, not the code.")
- Swapping a tenant from a local loop implementation to Relay calls is a config change, not a rewrite — this is the formalization target for the local `loop.js`-style code against the stage spec.
- Impacted is the reference implementation. Post-webinar work: build Relay out, formalize the local loop against the STA stage spec so the swap is configuration.

### Cross-tenant learning (decided 2026-10-06)

- Cross-tenant learning is allowed **only if the client agrees** — per-tenant `share_learning` toggle, on/off.
- All current projects default to learning ON.
- Contribution is consent-scoped: a tenant contributes learnings to the shared pool only when its toggle is on. Tenants with the toggle off still benefit from their own Memory Loop; they do not contribute.

### Canonical tenant DB core

**Uncertain — labeled as such.** A canonical tenant database core (the shared schema every tenant's Relay deployment carries: signals, judgments, proposals, decisions, commitments, outcomes, ledger, scores) is implied by the hosted model and by the tenant template repo (`s2a-tenant-template`, with `domain/`, `ledger/`, `persona/`). The coverage audit did not verify a single named schema document for the tenant core. Treat "canonical tenant DB core" as an architectural commitment of the hosted model whose schema artifact still needs to be pinned down and versioned (§15).

### Build state

- Relay is **built but not production-deployed** (as of 2026-10-07): repo `Signal-To-Action/signal-relay`, 7/7 tests passing, with an **in-memory store; Postgres persistence pending**.
- Do not describe Relay as the production engine for any live tenant today. SOS and the Impacted bridge run bespoke loop code (§13); Relay is the convergence target.

---

## 11. Interfaces/seams HAR-44 through HAR-50

The STA seams are tracked as HAR-44 through HAR-50. Each seam is a boundary where a vendor, a model, or a subsystem can be swapped without re-architecting — provided it passes the eval gate. Where the code mapping is known, it is named. Where it is missing, this section says so plainly (full gap list in §15).

### HAR-44 — Parent production port

The seam between the lab/distill code and production. This is the port that carries the canonical `signal_action` package (and, eventually, Relay) into the production SOS codebase.

- **Code mapping: missing/partial.** The canonical package lives at `~/workspace/signal-action-distill/signal_action/` and in the public repo `SOS-Help-The-Helper/signal-to-action` (129KB, last push 2026-10-05 — may be stale versus the local distill). As of 2026-10-07 the package is **not imported into SOS production**; SOS runs bespoke STA-like equivalents. HAR-44 is the migration path (§13) and remains open.

### HAR-45 — Capture adapter

The seam where raw platform material becomes normalized Signals: per-platform adapters → one format → mandatory PII/secret scrubber → Henry Brain `signal_traces` sink, with provenance (`source_trace_ids`) and verbatim rehydration on demand.

- **Code mapping: exists.** `~/workspace/signal-action-distill/signal_action/capture/` (adapters for OpenClaw, Claude Code, Muse DB, ChatGPT; `scrubber.py`, `feed.py`, `sinks.py`) and `~/workspace/transcript-capture/` (built 2026-10-05/06). Two streams: messages (all agents) and reasoning. Instinct is blocked (no export API). The zero-leak scrubber bar applies before anything reaches the sink. See also §12 for the failed PII backstop audit — capture working is not the same claim as PII-safe at scale.

### HAR-46 — Dedupe strategy

The seam that decides `duplicate_of` in Judgment: is this signal a duplicate of one already in flight?

- **Code mapping: partial.** The Judgment contract carries the `duplicate_of` field. The lab result — dedup F1 1.000 — was measured on **n=15 signals, too small to trust** (§14). A production dedupe strategy (thresholds, matching keys, merge behavior) behind a named interface is not yet pinned to a code location. **Mapping missing.**

### HAR-47 — decide/Clef adapter (the Judgment socket)

`decide()` is the vendor-neutral Judgment socket. TypeSafe Jev, Clef, deterministic providers, or another decision model swap through this eval-gated seam. A vendor earns the socket by passing the eval harness, not by integration effort.

- **Code mapping: exists.** `~/workspace/decide-work/` — Clef adapter, TypeSafe adapter, calibration data, `cascade-thresholds.json`, compounding-learnings tooling, eval harness. In production, the SOS gateway runs a `decide()` `person-identity` judgment (identity resolution on intake approval, deterministic-v1 active; confidence ≥ 0.8 auto-applies, below that it falls back to legacy phone matching; the decision is flushed to `signal_traces` as `identity_decision`).
- **Proof point:** Cloudflare's Clef was swapped in and benchmarked within 24 hours through the same eval harness, with no re-architecture (2026-10-02/03 test program).

### HAR-48 — Scorer interface/policy (SOS scorer)

The deterministic match scorer: **Score → Propose → Commit.**

- **SCORE** — pure, deterministic scoring of one request against candidate resources. No I/O, no persistence. Weights (SOS default): category 40% · distance 20% · urgency 15% · capability/availability 10% · SOS score 10% · recency 5%. Vetting is a bounded ±10 re-rank adjustment, never an exclusion. Unknown values are neutral (0.5, benefit of the doubt) — a new helper is never punished for being unscored.
- **PROPOSE** — persist the top shortlist as `matches` rows at status `proposed`, for a human to review. Lives in the SOS app (`proposeMatchesForRequest` in `lib/matches.ts`).
- **COMMIT** — a human accepts a proposal → `accepted`. Only this step connects anyone. **No phantom matches:** a score is not a match; a proposal is not an actioned match.

- **Code mapping: exists.** Skill at `~/workspace/skills/sos-scorer/` (`bin/score.mjs`, self-contained Node scorer; canonical core ported from the SOS repo's `lib/jev-core.js` / `lib/matches.ts` + `lib/match-rules.ts`). Tenant weighting profiles are supported (e.g. the Impacted job-matching profile raises category to 0.50 and recency to 0.20). The scorer is read-only: it never proposes, commits, contacts anyone, or writes to a database.
- **Naming discipline:** the SOS scorer is the internal deterministic scorer. "Jev" is TypeSafe's vendor decision model behind HAR-47. Never bare "Jev" for internal scoring work.

### HAR-49 — Calibration/proposal seam

The boundary where the Evaluation Loop's recalibrated thresholds (per-model, per-verdict) meet Proposal generation: which model drafts, with what confidence handling, under which calibrated thresholds.

- **Code mapping: partial.** Calibration artifacts exist (`~/workspace/decide-work/calibration-2026-10-03/`, `cascade-thresholds.json`; human proposal rankings 8 of 24 done at last record). A single named seam interface in production code, where calibrated thresholds are consumed by the proposal path, is **not yet mapped**.

### HAR-50 — Learning/policy-update seam

The boundary where typed learnings (defect / process / model / reliability / domain / operations) become checkable mechanisms in the memory store — and where policy updates (thresholds, rules, autonomy tiers) are written back.

- **Code mapping: partial.** The compounding-learnings tooling in `~/workspace/decide-work/` (corrected exemplars, retrieval-v2 hybrid keyword+embedding with utility weighting — 83.33% at ~872 tok/judgment vs 82.21% full-dump at ~3,589) demonstrates the mechanism in the lab. pgvector is the chosen vector store, with the retrieval interface kept backend-swappable. The production write path from Outcome → typed learning → Judgment steering, as one named seam, is **not yet mapped**.

### Seam summary

| Seam | What it is | Code mapped? |
|---|---|---|
| HAR-44 | Parent production port | No — migration open; package not in SOS prod (2026-10-07) |
| HAR-45 | Capture adapter | Yes — `signal_action/capture/`, `transcript-capture/` |
| HAR-46 | Dedupe strategy | No — field exists; strategy unmapped; evidence n=15 |
| HAR-47 | decide/Clef adapter | Yes — `~/workspace/decide-work/`; SOS gateway `person-identity` |
| HAR-48 | Scorer interface/policy | Yes — `~/workspace/skills/sos-scorer/` |
| HAR-49 | Calibration/proposal seam | Partial — calibration data exists; production seam unmapped |
| HAR-50 | Learning/policy-update seam | Partial — lab tooling exists; production seam unmapped |

In the live bridge, STA judgment appears in `~/workspace/impacted/sms-bridge/src/sta-gate.mjs` (the STA intake gate) and `sta-react.mjs` (judgment-driven emoji reactions), with `sta-context.mjs` alongside. These are bespoke implementations, not the canonical package.

---

## 12. Safety/privacy posture

STA's safety posture in SOS deployments is not a compliance appendix; it is part of the concept (Jonathan, 2026-10-07).

### The safe confidant

SOS is the safe confidant: people can talk about their worst moments with no fear those moments are captured by big data. The agent helps people going through a lot — encourages, inspires, and amplifies the scientifically-proven human desire to help others and coexist peacefully in community. Sad or lonely moments never touch big data. This is a design constraint on Signal and Judgment: PII isolation begins at Signal (§4), payloads are anonymized before any vendor sees them, and the capture layer (§11, HAR-45) scrubs PII/secrets to a zero-leak bar before anything reaches Henry Brain.

### The sheepdog

The agent is a sheepdog. It protects the flock from wolves — fraud awareness, bad actors — and defends itself from bad actors, including prompt-injection defense (the Wingman build carries the same posture). The sheepdog does not pretend to be a sheep: the agent is **obviously an AI, never a creepy human-imitator**. What it offers instead is what an AI actually has: total recall, instant pattern-matching across thousands of cases, always available, never tired, no judgment.

### Constrained capabilities + free conversation

The core tension: too loose and the agent goes wild (uncontrolled writes, off-track); too tight and it feels like scripted questions. The settled answer is **constrained capabilities + free conversation**:

- Closed write surface. The citizen agent's six boundary requirements are the model: only a closed intake body shape, identity from transport, rate limits at the boundary, every refusal logged loudly.
- Natural LLM conversation inside those bounds. The agent talks like a person; it writes like a form.
- Identity from transport, never from the conversation. The system does not learn who you are by asking you to claim it.
- Every refusal is logged. A refusal that disappears is a defect.

### The failed PII backstop audit (honest)

The PII backstop audit **failed**. Three blockers stand before any real data touches a model: (1) domestic phone-number detection, (2) an unguarded full-LLM route, and (3) a privacy review with explicit sign-off. Until all three are fixed and re-audited, STA's privacy claims are design claims, not audited facts. This failure is recorded in the paper's honest-results chapter and stays open in §15.

### Brevity and aliveness defaults

- Brevity by default: nobody likes long texts. Long only when it earns it.
- "Uniquely alive": use native platform features (typing indicators, reactions, formatting) so it never feels like a generic bot. In the Impacted bridge, emoji reactions are judgment-driven (`sta-react.mjs`), not regex-triggered.
- Acknowledgments must reflect the person's actual words. Canned warmth that ignores what someone said is a product defect, not polish.

---

## 13. Project patterns

How STA appears in each project today. The pattern differs per project; the framework doesn't.

### SOS — bespoke STA-like code, canonical package not imported

SOS is the origin case study (community coordination; disaster relief was the case study, not the frame). Production state, verified 2026-10-07:

- The canonical `signal_action` package (`~/workspace/signal-action-distill/`) **exists with tests but is NOT imported into SOS production.** SOS runs bespoke code that implements STA-like behavior stage by stage: gateway intake with a `decide()` `person-identity` judgment (HAR-47), the deterministic SOS scorer (HAR-48, Score → Propose → Commit), intake lifecycle RPCs with idempotency and identity resolution, and `signal_traces` audit flushes.
- **Both are documented here deliberately:** the canonical package is the spec; the bespoke code is the running system. Conflating them is how "STA is live in SOS" becomes a false claim.
- **Migration path:** HAR-44 (parent production port). Port the production loop onto the canonical package's stage contracts — Signal/Judgment/Proposal handoffs first, then inner-loop validate_loop checks — seam by seam (HAR-45→50), with the eval gate deciding each swap. The 2026-10-07 directives "Wire SOS into STA" and "I want the cure now" (§16) are the standing authorization and urgency for this migration.
- SOS Score in the Trust Loop is XP: baseline start, compounding through verified actions, no ceiling, network attribution to inviters, verification boost-only (only claimed-but-contradicted affiliations get flagged), and autonomy-tier gating — lower score means more human oversight, never exclusion (2026-10-07).

### Impacted — the reference implementation

Impacted (the layoff-talent network, now an SOS product under the SOS PBC once formed; decided 2026-10-07) is the **reference implementation** of STA: the tenant whose local loop gets formalized against the stage spec first, so swapping local loop → Relay calls is a config change.

- **STA intake gate replacing keyword menus.** The bridge classifies every incoming message and routes the right path (2026-10-08 build). A general helper intro leads — the assistant introduces itself as the SOS assistant, an AI, free to use — before branching to disaster help or jobs. Job intake is inspiration-first: remote/hybrid/onsite is decided before location, no city question up front.
- **`sta-react.mjs` judgment-driven emoji.** Reactions are chosen by STA judgment, not keyword/regex triggers — emoji land in key moments only, never a heart on bad news.
- **Credential-cure judgment.** When LinkedIn OAuth credentials were the blocker, the fix was framed and executed as a judgment problem: classify the credential state, propose the cure, gate the irreversible step. (LinkedIn OAuth staged, not deployed, at last record.)
- Live state at last record: bridge live and responding, typing indicators and message-specific reactions live, WhatsApp reply path confirmed. Completed intakes emit to the SOS gateway as `source='impacted'` with idempotency key `impacted:<session>`, fenced by `exercise_id='impacted-pilot'`; going live is a one-line `exercise_id` change.

### Wingman — a full STA implementation

Wingman (Jay Robinson's agent; repo `Signal-To-Action/wingman`, private, created 2026-10-06) is positioned by Jonathan as **an implementation of the Signal-to-Action concept, not just a chatbot using the pattern** — and as the flagship proof for a coach network: other coaches get their own Wingman instances (lead pipeline + coordination), with multi-tenant schema already in place (tenant column on all tables; Jay is tenant #1). Coach onboarding is voice interview → generated persona → live agent. Wingman is the clearest existing example of the thin-tenant shape before Relay hosts it.

### Jerry — the full-loop backtest harness

Jerry's harness (`~/workspace/jerry/signal-to-action-backtest/`, 109MB) runs 25 plays through the **complete STA loop** with strict no-lookahead discipline: flat $100 paper units, win rate / ROI / CLV / binomial p-values with Holm-Bonferroni correction. Jonathan called it "a beautiful testing ground" (2026-10-06). Jerry must have **zero code entanglement with SOS repos** (decided 2026-10-05): Jerry runs on the public STA framework as a dependency, never as a drifting copy inside the SOS repo.

The 25-play backtest also produced the **Demand Lab methodology fix**, now the standing process for all Demand Lab experiments:

- **Phase 0 — data foundation:** split by league always, enrich with real factors (injuries/transfers/coaching), validate quality first.
- **Phase 1 — discovery:** mine the data for patterns; the data generates hypotheses.
- **Phase 2 — validation:** held-out data only, proper multiple-comparison correction.
- **Phase 3 — paper trade → live,** with explicit per-play approval.

The flaw it fixed: the original program tested 25 preconceived hypotheses (from Reddit/X/a friend's ideas) instead of discovering patterns from data — confirmatory before exploratory, backwards. CFB and NFL are different markets and are never pooled.

---

## 14. Experiments, wins, failures, changed decisions

Per standing rule (2026-10-05): every test stage updates the paper, and results — pass and fail — land in the honest-results chapter as each cluster completes. v1 and the live artifact stay read-only until Jonathan approves v2.

### Proven results (from the fresh-agent brief's test record)

1. **Sorting works.** On 6 classification verdicts against blind human rubrics: Cloudflare Clef scores 92.8%. Gemini 3 Flash and Grok 4.5 beat it significantly (proper paired statistics); GPT-5-mini ties it; Claude trends above but not significantly. TypeSafe Jev trails Clef by 12 points (significant).
2. **The hybrid appeal tier shows no gain — honest negative.** LLM double-checking the cheap model on hard cases: 92.2% / 91.7% vs 92.8% for Clef alone. On this corpus the appeal tier adds cost without measurable quality. It needs a corpus enriched for low-confidence cases, not more uniform signals.
3. **Memory compounds only when it is checkable.** Pasting prose advice into the prompt made things worse (78.3% → 73.3%). Corrected past cases as exemplars jumped accuracy 81.7% → 96.7%. A deterministic rule derived from a learning eliminated a whole error class. Thesis: "Checkable memories can compound." Prose doesn't.
4. **The full loop beats the alternatives.** End-to-end simulation, 9 arms: full loop vs no-AI manual vs human-only vs collapsed single-call AI vs five ablations (one piece removed at a time). The full loop wins, and every piece earned its keep — including the human gate.
5. **It survives load.** 500 signals/hour spike: pass. Adversarial noise: pass with caveats. Total sim cost: $0.62, production untouched.
6. **Vendor neutrality is real.** Cloudflare's Clef was swapped in and benchmarked within 24 hours through the same eval harness. No re-architecture. Any vendor swaps through the eval-gated seam.
7. **The ledger is hardened (test environment).** Hash chain verified, append-only verified, dedicated writer credential, shared access revoked. SEC-1/2/3 green.
8. **The statistics are real.** 100 signals is the properly powered sample size for build-vs-buy decisions; the full 7-system comparison costs ~$1.13 in API spend. Human labeling is the constraint (100 signals = 600 human judgments). Test sizing is by statistical significance, not dollars (standing rule, 2026-10-05).
9. **The system dogfoods itself.** Every learning from testing is written into the system's own learning engine, typed (defect / process / model / reliability / domain / operations).

### Honest failures and weak results

- **Conflicting signals break the loop (designed failure).** Two signals contradicting each other is a designed failure today, queued as its own conflict-detection design test. **The conflict-detection test is not built** (§15).
- **PII backstop audit failed.** Three blockers: domestic phone-number detection, an unguarded full-LLM route, and a privacy review with explicit sign-off (§12).
- **Dedup F1 1.000 on n=15.** Too small to trust. Quoted here only with its sample size attached.
- **Hybrid appeal tier: no proven gain** (above). Recorded as a negative result, not buried.

### Changed decisions (with dates)

| Date | Decision |
|---|---|
| 2026-10-05 | **ONE PAPER, not multiple assets.** Signal-to-Action (framework) + Relay (engine) + loops + testing data/modeling live in a single paper, SOS as the example/case study. This overrides the earlier separate-Relay-deep-dive direction; Relay content folds into the one paper as a chapter. The separate `relay-whitepaper` artifact folds in and is not deleted without Jonathan's explicit say-so. |
| 2026-10-05 | **v2 title: "Signal-to-Action: The Framework."** The naming audit killed "The Coordination Paper" (the outer loop is not called coordination, §3). |
| 2026-10-05 | **Relay folds into the one paper** as the engine chapter (consequence of ONE PAPER). |
| 2026-10-06 | **Relay hosted thin-tenant model.** Every implementation is a thin tenant (persona + domain + `loop-config.yaml`); core loop logic/ledger/learning live in one Relay. |
| 2026-10-06 | **Cross-tenant learning consent toggle.** Per-tenant `share_learning`, default ON for current projects, contribution only when consented. |
| 2026-10-05 | **Jerry zero code entanglement with SOS.** Jerry runs on the public STA framework as a dependency, not a drifting copy. (A Jerry build had been started inside the SOS repo; it must be fully extracted.) |
| 2026-10-07 | **"Wire SOS into STA" / "I want the cure now."** Directives to migrate SOS production onto the canonical framework (§13, §16). |
| 2026-10-06 → | **Terminology shift: full name → "STA" shorthand.** Verified by grep across daily memories (Oct 1–8): 195 matches for hyphenated "Signal-to-Action" vs 130 whole-word "STA" matches, with **all whole-word "STA" hits in Oct 6–8 files and zero before Oct 6**. ("Signal to Action" with spaces: 6; "S2A": 16; `signal_action` package name: 5.) Jonathan wrote it out in full until Oct 6, then switched to the shorthand. |

---

## 15. Outstanding gaps (honest)

These are open as of 2026-10-08. Nothing in this section is softened.

1. **`signal_action` package not imported into SOS production.** The canonical package exists (local distill, 580KB, with `capture`, `provenance`, `retrieval`, `loops`, `tests`) and tests pass in the lab (8/8 end-to-end, 10/10 reasoning-stream; one provenance test skipped because it touched the production DB). SOS production runs bespoke STA-like equivalents. HAR-44 is the open migration port.
2. **HAR-44–50 lack complete per-seam code mapping.** HAR-45, HAR-47, HAR-48 are mapped. HAR-44, HAR-46, HAR-49, HAR-50 are partial or missing (§11). There is no consolidated map of which SOS/Impacted code paths implement which STA stage.
3. **Verbatim deficit.** The Sept 26 – Oct 3 definitional conversations — where STA was actually hammered out — survive only as summaries in daily memories. The Fireflies pull (16 meetings) is STA-empty: all IES × Harmony commercial calls. Instinct is blocked (no export API). OpenClaw/Grokbot/Claude Code local sessions have not yet had an STA-targeted pull. Section 16 therefore contains five verified quotes and an explicit admission, not a reconstructed voice.
4. **Conflicting-signals conflict-detection test not built.** The failure is designed and understood; the fix (a conflict-detection stage behavior) has a queued design test that does not exist yet.
5. **Ledger replay/dispute exercise not run.** Two coordinators disagree; the ledger alone settles it. This is the most distinctive claim in the program ("prove it") and it has never been exercised end-to-end.
6. **Relay not production-deployed.** Built (`Signal-To-Action/signal-relay`, 7/7 tests) with an in-memory store; Postgres persistence pending. No live tenant runs on Relay today.
7. **PII backstop blockers open.** Phone-number detection, the unguarded full-LLM route, and privacy sign-off (§12). Re-audit pending the three fixes.
8. **Human calibration incomplete.** Human proposal rankings were 8 of 24 done at last record; the human gate trap session (20 adversarial scenarios) had not been run. Two sim assumptions remain provisional until then: unweighted proposal generators and a simulated (not human) gate policy.
9. **Remaining tests from the brief, not yet run:** Sybil-adversarial trust simulation; fault injection (an LLM deliberately placed in the record-keeping path to watch the record corrupt — proving the deterministic spine is load-bearing); final build-vs-buy evaluation per component (runs last); production ledger rollout (needs explicit approval, not started).
10. **Public repo may be stale.** `SOS-Help-The-Helper/signal-to-action` was last pushed 2026-10-05; the local distill is ahead. Which one is canonical must be settled when HAR-44 is worked.

---

## 16. Verbatim Jonathan quotes with provenance

**Only** the following quotes are verified verbatim. No other Jonathan quotes are asserted in this guide. This shortness is the verbatim deficit (§15, gap 3) made visible: the definitional STA conversations of Sept 26 – Oct 3 were compacted into summaries, and this guide refuses to reconstruct wording that was not captured.

1. **"Wire SOS into STA"**
   — 2026-10-07, 13:23–13:47 MST window, daily memory (`~/memory/2026-10-07.md`). Directive: migrate SOS production onto the canonical STA framework (§13).

2. **"I want the cure now"**
   — Same 2026-10-07 window, daily memory. Paired with the directive above; "the cure" is the STA migration, not another bespoke patch.

3. **"Agent should be able to route told you to set up STA as intake gate"**
   — 2026-10-08, daily memory (`~/memory/2026-10-08.md`). The directive behind the STA intake gate in the Impacted bridge (§13): the agent routes; the gate is STA classification, not keyword menus.

4. **"I'm honestly shocked that you dont know what STA is and I've been referring to it in instructions, talking about it all day etc"**
   — 2026-10-08, live session. Wording as received, including "dont". This message is the reason this guide exists: the knowledge was in instructions and conversation all day, and the agent's compaction had dropped it. The BOOTSTRAP (§1) is the direct fix.

5. **"How do we audit our verbatim transcripts to put together a ultra detailed guide that survives your compaction and also draw from learnings we've gathered together"**
   — 2026-10-08, live session. Wording as received, including "a ultra". This is the commissioning instruction for the coverage audit (`~/workspace/sta-audit/COVERAGE-REPORT.md`, approved 2026-10-08) and for this guide.

---

## 17. Code/repo map

Where STA actually lives, as of 2026-10-08. Local paths are on this machine; GitHub repos are named with their org.

### Framework and engine repos

| Location | What it is |
|---|---|
| `SOS-Help-The-Helper/signal-to-action` (public GitHub) | The public framework repo: `signal_action/` package, `calibration/`, `docs/`, `examples/`, README, LICENSE. 129KB. Created 2026-10-05; last push 2026-10-05 — **may be stale** versus the local distill. |
| `Signal-To-Action/signal-relay` (GitHub) | Relay, the hosted engine: `db/`, `src/`, `tests/`. Built, 7/7 tests, in-memory store; Postgres persistence pending. Not production-deployed. |
| `Signal-To-Action/s2a-tenant-template` (GitHub) | Cloneable thin-tenant template: `domain/`, `ledger/`, `persona/`, `loop-config.example.yaml`. |
| `Signal-To-Action/wingman` (GitHub, private) | Wingman — Jay's agent. A full STA implementation; tenant #1 of the coach network. Created 2026-10-06. |

### Local canonical code

| Location | What it is |
|---|---|
| `~/workspace/signal-action-distill/signal_action/` | The distilled canonical package. `loops/` (the machine-readable spec: `OUTER_STAGES`, `Lane`, `INNER_LOOPS`, `NON_COLLAPSIBLE_RULES`, `validate_loop`), `capture/` (adapters, scrubber, feed, sinks), `provenance/` (attach/rehydrate/verify), `retrieval/` (hybrid BM25+embedding RRF retrieval, utility-weighted), `tests/` (8/8 end-to-end, 10/10 reasoning-stream in lab baseline). Production backends stripped; persistence is an injectable interface. |
| `~/workspace/decide-work/` | The HAR-47 seam: `decide()` vendor adapters (Clef, TypeSafe), calibration data (`calibration-2026-10-03/`), `cascade-thresholds.json`, compounding-learnings tooling, eval harness, and the explainer docs (`loops-framework-llm-context.md`, `system-explainer-full.md`, `sos-explainer-plain-english.md`, `signal-to-action-test-plan.md`). |
| `~/workspace/skills/sos-scorer/` | HAR-48: the deterministic SOS scorer (Score → Propose → Commit). `bin/score.mjs` + references. Read-only; never writes to a database. |
| `~/workspace/transcript-capture/` | HAR-45 infrastructure as built 2026-10-05/06: platform adapters, PII/secret scrubber, provenance, feed. The capture layer is itself an STA project by Jonathan's 2026-10-05 directive. |

### STA in running systems (bespoke, not the canonical package)

| Location | STA role |
|---|---|
| SOS gateway (`SOS-Help-The-Helper/help-the-helper`) | Intake lifecycle, identity resolution, and a production `decide()` judgment: `person-identity` (deterministic-v1; ≥0.8 confidence auto-applies, below falls back to legacy phone matching; decisions flushed to `signal_traces` as `identity_decision`). Matching via the SOS scorer core (`lib/matches.ts`, `lib/match-rules.ts`, `lib/jev-core.js`). |
| `~/workspace/impacted/sms-bridge/src/sta-gate.mjs` | The STA intake gate: classify every incoming message, route the right path. Replaced keyword menus. |
| `~/workspace/impacted/sms-bridge/src/sta-react.mjs` | Judgment-driven emoji reactions (STA judgment, not regex). `sta-context.mjs` sits alongside. |
| Henry Brain (Supabase `vqudlavumxwslfejqupy`) | The organism-level memory sink: `signal_traces`, `system_learnings`, `agent_briefings`, `jev_analysis`. Memories carry `source_trace_ids` with verbatim rehydration on demand. This is where STA's Learning stage lands at organism scale. Note: this is the organism DB, distinct from THE SOS production DB (Supabase `rtduqguwhkczexnoawej`). |
| `~/workspace/jerry/signal-to-action-backtest/` | Jerry's 25-play full-loop backtest harness (109MB). Strict no-lookahead; the Demand Lab methodology fix came out of this work. Zero code entanglement with SOS repos. |

### Documents

| Location | What it is |
|---|---|
| This guide (`sta-canonical-guide`) | The canonical STA reference. Subsumes the brief below. |
| `~/workspace/your_files/signal-to-action-brief-for-fresh-agent.md` | The prior compaction-survival brief (135 lines). **Superseded by this guide**; kept for provenance. |
| `~/workspace/sta-audit/COVERAGE-REPORT.md` | The Phase 1 audit this guide was synthesized from. Approved by Jonathan 2026-10-08. |
| `~/workspace/your_files/signal-to-action-whitepaper-v2-draft.md` | The ONE PAPER draft: "Signal-to-Action: The Framework" — framework + Relay + loops + testing, SOS as case study. Every test stage updates its honest-results chapter. |

---

*End of guide. If you are a fresh agent session: you now hold the STA framework. Load §1, honor §2 and §7, route work through §11's seams, and check §15 before claiming anything is live.*
