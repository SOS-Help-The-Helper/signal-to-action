# Utility re-calibration — retrieval λ for `signal_action/retrieval`

**Date:** 2026-10-05
**Corpus seed:** 20261005 (seeded shuffle of 40 hand-authored signals → IDs R-001..R-040)
**Corpus size:** 40 signals (20 requests / 12 resources / 6 noise / 2 unclear; lane/urgency/risk labels fixed at authoring)
**Judge model:** `@cf/cloudflare/clef-flash` via Cloudflare Workers AI (same judge pattern as phase 10: `build_state` + `build_questions`, 3 verdicts × 40 signals = 120 pairs per memory)
**Bank:** 79 L-bank memories (`mem_bank3`, read-only SELECT; row count unchanged; no writes anywhere)
**Embeddings:** none — utility calibration uses no retrieval, so zero embedding spend
**Total spend:** 3,200 judge calls (79×40 + 40 baseline), 0 failures, 0 retries → **upper-bound $0.48** (3,200 × $0.00015 list rate; Clef-flash actual is cheaper). Measured 2,115,080 input tokens (~661 tok/call).

## Anti-cheat verification (run before any judge call)

- Fresh texts ≠ phase-10 `calibration.json` (C-001..C-040): 0 verbatim overlaps
- Fresh texts ≠ phase-8 sealed holdout (`fixtures8.json`): 0 verbatim overlaps
- Fresh texts not present in any L-bank memory content: 0 verbatim overlaps
- 40 unique texts, 40 unique IDs

## Measured utility distribution (fresh corpus, pp over 120 verdict pairs, n=79)

| stat | value | phase-10 (same experiment, old corpus) |
|---|---|---|
| mean | **+0.253** | −3.049 |
| min | **−5.000** | −15.000 |
| max | **+6.667** | +4.167 |
| negative | **35/79 (44.3%)** | 61/79 (77.2%) |
| zero | 5 | — |

Histogram (2pp bins):

| bin | count |
|---|---|
| [−6, −4) | 2 |
| [−4, −2) | 17 |
| [−2, 0) | 16 |
| [0, +2) | 21 |
| [+2, +4) | 16 |
| [+4, +6) | 6 |
| [+6, +8) | 1 |

Kind split: exemplars (n=70) mean −0.083, 35/70 negative (50.0%); rules (n=9) mean +2.870, **0/9 negative**.

Worst: `608118fa` (−5.000, exemplar). Best: `ffdae534` (+6.667, exemplar).

## Replications and non-replications vs phase 10

- **Did not replicate:** the −15pp extreme. Fresh min is −5.000pp, close to the design doc's ±5pp assumption. The phase-10 −15pp was a corpus-specific outlier.
- **Did replicate:** `608118fa` (phase-10's worst, −15.0pp) is again the worst memory on the fresh corpus (−5.0pp). Direction of the harm replicates; magnitude does not.
- `db4aa968` (phase-10's best, +4.167pp) is +2.5pp here — still positive.
- The "downweighting prior" story is weaker on fresh data: exemplars split 50/50 (vs 77% negative in phase 10); all 9 rules are positive.

## λ verdict: KEEP λ_u=1.0

At λ_u=1.0 the utility term spans −0.050 to +0.067 (range **0.117**); the RRF term in `HybridBank` (1/(60+rank), two rankers, 70 retrievable memories) spans 0.0154–0.0328 (range **0.0174**). The utility term is ~7x the RRF spread — **yes, λ_u=1.0 still dominates ranking**, reproducing the phase-10 structural finding. But the phase-10 magnitude finding (measured −15pp *dwarfing* the assumed ±5pp) does **not** replicate: the fresh range matches the design assumption, so the case for retuning is weaker than it looked.

Why keep, not retune or magnitude-match:

1. λ_u=1.0 is the value already validated on the sealed 178-signal holdout (V2 bundle +4.87pp vs P9, p=0.0005; V2-U +2.06pp, p=0.10). Changing it on the strength of this calibration alone — without re-running the sealed-holdout ablation — would be post-hoc tuning, the exact thing the lab refused to do in phase 10.
2. The fresh corpus removes the motivation: the assumed ±5pp range now matches measurement. A magnitude-match (λ_u ≈ 0.15 to equalize the utility term with the RRF spread) would be fitting to this corpus's measured range, not to holdout evidence.
3. Utility-first ranking is a documented property of the shipped bundle, not a defect: the ablation's gain came from utility *downweighting* harmful exemplars, and the gain concentrated on urgency (+10.7pp vs P9).

**If λ is ever retuned:** magnitude-match against measured ranges on a *third* corpus, then re-validate the full ablation on the sealed holdout before changing the shipped `UTILITY_LAMBDA`.

## Honest status

Calibration complete on an honest fresh corpus: λ re-derived, verdict keep 1.0. The phase-10 −15pp magnitude extreme did not replicate (fresh min −5.0pp); the utility term still dominates ranking at 1.0 by a ~7x spread margin. This re-calibration is a weighting prior, not a significance-tested endpoint — no per-memory p-values are claimed.

## Provenance

- Corpus: `~/workspace/signal-action-distill/calibration/calibration_fresh.json`
- Generator: `~/workspace/signal-action-distill/calibration/gen_corpus_fresh.py`
- Harness: `~/workspace/signal-action-distill/calibration/run_utility_fresh.py` (judge pattern verbatim from `decide-work/phase10/run_utility.py`)
- Results: `~/workspace/signal-action-distill/calibration/utility_fresh.json`
- Run log: `~/workspace/signal-action-distill/calibration/utility_fresh_run.log`
- Package code this λ ships in: `~/workspace/signal-action-distill/signal_action/retrieval/__init__.py` (`UTILITY_LAMBDA = 1.0`)
