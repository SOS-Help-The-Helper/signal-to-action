"""SLO instrumentation tests. Synthetic fixtures only — no DB, no network,
no secrets, no real sleeps (all timing via an injected fake clock).

Run from the distill root: python3 -m signal_action.tests.test_slo
"""
from signal_action.retrieval.slo import (
    DEFAULT_BUDGETS,
    LatencyTracker,
    percentile,
)


class FakeClock:
    def __init__(self):
        self.t = 500.0

    def now(self):
        return self.t

    def advance(self, dt):
        self.t += dt


def _close(a, b, tol=1e-9):
    return all(abs(x - y) < tol for x, y in zip(a, b))


def test_stage_context_manager_records():
    clock = FakeClock()
    tr = LatencyTracker(time_fn=clock.now)
    with tr.stage("retrieve"):
        clock.advance(0.12)
    with tr.stage("retrieve"):
        clock.advance(0.08)
    with tr.stage("rerank"):
        clock.advance(0.30)
    assert _close(tr.samples("retrieve"), [0.12, 0.08])
    assert _close(tr.samples("rerank"), [0.30])
    assert tr.samples("total") == []
    print("stage context manager: OK")


def test_stage_records_on_exception():
    clock = FakeClock()
    tr = LatencyTracker(time_fn=clock.now)
    try:
        with tr.stage("retrieve"):
            clock.advance(0.05)
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert _close(tr.samples("retrieve"), [0.05]), "stage lost on exception"
    print("stage records on exception: OK")


def test_percentile_math():
    assert percentile([1, 2, 3, 4, 5], 50) == 3
    assert percentile([1, 2, 3, 4, 5], 95) == 5
    assert percentile([1, 2, 3, 4, 5], 0) == 1
    assert percentile([1, 2, 3, 4, 5], 100) == 5
    vals = list(range(1, 101))  # 1..100
    assert percentile(vals, 50) == 50
    assert percentile(vals, 95) == 95
    assert percentile([7.5], 95) == 7.5  # single sample
    # unsorted input is sorted internally
    assert percentile([5, 1, 4, 2, 3], 50) == 3
    print("percentile math: OK")


def test_percentile_rejects():
    for bad in ([],):
        try:
            percentile(bad, 50)
        except ValueError:
            pass
        else:
            raise AssertionError("empty sample did not raise ValueError")
    for bad_p in (-1, 101):
        try:
            percentile([1, 2, 3], bad_p)
        except ValueError:
            pass
        else:
            raise AssertionError(f"p={bad_p} did not raise ValueError")
    print("percentile rejects: OK")


def test_stats():
    clock = FakeClock()
    tr = LatencyTracker(time_fn=clock.now)
    assert tr.stats("retrieve") is None  # no samples yet
    for v in (0.10, 0.20, 0.30, 0.40, 0.50):
        tr.record("retrieve", v)
    st = tr.stats("retrieve")
    assert st["n"] == 5
    assert st["min"] == 0.10
    assert st["max"] == 0.50
    assert st["p50"] == 0.30, st
    assert st["p95"] == 0.50, st
    print("stats: OK")


def test_check_slo_breach_reporting():
    clock = FakeClock()
    tr = LatencyTracker(time_fn=clock.now)
    for v in (0.10, 0.12, 0.11, 0.13, 0.60):  # p95 = 0.60
        tr.record("retrieve", v)
    tr.record("rerank", 0.20)
    report = tr.check_slo({"retrieve": 0.50, "rerank": 0.50})
    r = report["stages"]["retrieve"]
    assert r["p95"] == 0.60
    assert r["budget"] == 0.50
    assert r["breached"] is True, "p95 0.60 > budget 0.50 should breach"
    rk = report["stages"]["rerank"]
    assert rk["breached"] is False
    assert report["breached_any"] is True
    print("check_slo breach reporting: OK")


def test_check_slo_no_breach():
    tr = LatencyTracker()
    tr.record("total", 0.5)
    report = tr.check_slo({"total": 5.0})
    assert report["stages"]["total"]["breached"] is False
    assert report["breached_any"] is False
    print("check_slo no breach: OK")


def test_check_slo_missing_budget():
    tr = LatencyTracker()
    tr.record("custom_stage", 9.99)
    report = tr.check_slo({"retrieve": 1.0})  # no budget for custom_stage
    st = report["stages"]["custom_stage"]
    assert st["budget"] is None
    assert st["breached"] is False
    print("check_slo missing budget: OK")


def test_check_slo_default_budgets_labeled():
    # defaults exist and are honest placeholders, not production SLOs
    assert set(DEFAULT_BUDGETS) >= {"retrieve", "rerank", "total"}
    assert all(v > 0 for v in DEFAULT_BUDGETS.values())
    tr = LatencyTracker()
    tr.record("retrieve", 0.01)
    report = tr.check_slo()  # no budgets passed -> placeholder defaults
    assert report["stages"]["retrieve"]["budget"] == DEFAULT_BUDGETS["retrieve"]
    assert report["stages"]["retrieve"]["breached"] is False
    print("check_slo default budgets: OK")


def test_record_rejects_negative():
    tr = LatencyTracker()
    try:
        tr.record("retrieve", -0.1)
    except ValueError:
        pass
    else:
        raise AssertionError("negative seconds did not raise ValueError")
    print("record rejects negative: OK")


if __name__ == "__main__":
    test_stage_context_manager_records()
    test_stage_records_on_exception()
    test_percentile_math()
    test_percentile_rejects()
    test_stats()
    test_check_slo_breach_reporting()
    test_check_slo_no_breach()
    test_check_slo_missing_budget()
    test_check_slo_default_budgets_labeled()
    test_record_rejects_negative()
    print("\nALL SLO TESTS PASSED")
