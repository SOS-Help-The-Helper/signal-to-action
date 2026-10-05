"""Per-stage latency instrumentation with caller-configured SLO budgets.

A LatencyTracker records named stages ("retrieve", "rerank", "total", or any
caller-defined name) via a context manager or explicit record() calls.
check_slo() reports p50/p95 per stage against budgets. Pure stdlib; tests
inject a fake clock (no real sleeps anywhere in this package).

Status: fixture-tested.
"""

import time
from contextlib import contextmanager

__all__ = [
    "DEFAULT_BUDGETS",
    "percentile",
    "LatencyTracker",
]

# ---------------------------------------------------------------------------
# Budgets: PLACEHOLDER DEFAULTS ONLY — not production SLO numbers.
# Every deployment configures its own budgets and passes them to check_slo().
# These exist so check_slo() works unconfigured in development and fixture
# tests. Do not treat them as recommended production values.
# ---------------------------------------------------------------------------
DEFAULT_BUDGETS = {
    "retrieve": 0.500,  # seconds; placeholder default, NOT a production SLO
    "rerank": 1.000,    # seconds; placeholder default, NOT a production SLO
    "total": 2.000,     # seconds; placeholder default, NOT a production SLO
}


def percentile(values, p):
    """Nearest-rank percentile of a non-empty sample list (p in [0, 100]).

    Sorts ascending; returns the value at rank ceil(p/100 * n) (1-indexed).
    p50 of [1,2,3,4,5] is 3; p95 of 1..100 is 95.
    """
    if not 0 <= p <= 100:
        raise ValueError(f"p must be in [0, 100], got {p!r}")
    vals = sorted(values)
    if not vals:
        raise ValueError("percentile of empty sample")
    import math
    n = len(vals)
    rank = max(1, min(n, math.ceil(p / 100.0 * n)))
    return vals[rank - 1]


class LatencyTracker:
    """Records per-stage latency samples and checks them against budgets.

    time_fn: clock source in seconds, injectable for deterministic tests;
        defaults to time.perf_counter.

    Budgets are caller-configured: pass {stage: seconds} to check_slo().
    Omit the argument to use DEFAULT_BUDGETS (placeholder defaults, not
    production SLOs — see note above).
    """

    def __init__(self, time_fn=None):
        self._time = time.perf_counter if time_fn is None else time_fn
        if not callable(self._time):
            raise ValueError("time_fn must be callable")
        self._samples = {}  # stage -> [seconds]

    def record(self, stage, seconds):
        """Record one latency sample for a stage (seconds >= 0)."""
        secs = float(seconds)
        if secs < 0:
            raise ValueError(f"seconds must be >= 0, got {seconds!r}")
        self._samples.setdefault(str(stage), []).append(secs)
        return secs

    @contextmanager
    def stage(self, name):
        """Context manager: time the enclosed block as stage `name`.

        with tracker.stage("retrieve"):
            ...work...
        """
        start = self._time()
        try:
            yield self
        finally:
            self.record(name, self._time() - start)

    def samples(self, stage):
        """Copy of the recorded samples for a stage ([] if none)."""
        return list(self._samples.get(str(stage), []))

    def stats(self, stage):
        """{n, min, max, p50, p95} for a stage, or None if no samples."""
        vals = self._samples.get(str(stage))
        if not vals:
            return None
        return {
            "n": len(vals),
            "min": min(vals),
            "max": max(vals),
            "p50": percentile(vals, 50),
            "p95": percentile(vals, 95),
        }

    def check_slo(self, budgets=None):
        """Report per-stage p50/p95 against budgets.

        budgets: {stage: seconds}; defaults to DEFAULT_BUDGETS (placeholder
        defaults — configure real budgets for production). Stages with no
        samples are omitted; stages with no configured budget report
        budget=None and breached=False.

        Returns {"stages": {name: {n, min, max, p50, p95, budget, breached}},
        "breached_any": bool}.
        """
        cfg = dict(DEFAULT_BUDGETS) if budgets is None else dict(budgets)
        stages = {}
        for name in self._samples:
            st = self.stats(name)
            budget = cfg.get(name)
            if budget is not None:
                budget = float(budget)
            stages[name] = dict(st, budget=budget,
                                breached=(budget is not None and st["p95"] > budget))
        return {"stages": stages,
                "breached_any": any(s["breached"] for s in stages.values())}
