from core.timing_metrics import PreflightMetrics, TimingMetrics


def test_timing_metrics_reports_recent_percentiles() -> None:
    metrics = TimingMetrics(capacity=4)
    for value in (10, 20, 30, 40, 50):
        metrics.record(preflight_ms=value, guidance_ms=value * 10)
    assert metrics.snapshot() == {
        "preflight_p50_ms": 30,
        "preflight_p95_ms": 50,
        "guidance_p50_ms": 300,
        "guidance_p95_ms": 500,
        "sample_count": 4,
    }


def test_preflight_metrics_counts_blocked_outcomes() -> None:
    metrics = PreflightMetrics()
    metrics.record("detected", "face_confirmed", blocked=False)
    metrics.record("uncertain", "face_low_confidence", blocked=False)
    metrics.record("missing", "no_face", blocked=True)
    assert metrics.snapshot() == {
        "total": 3,
        "passed": 2,
        "blocked": 1,
        "block_rate": 0.3333,
        "states": {"detected": 1, "uncertain": 1, "missing": 1},
        "reasons": {"face_confirmed": 1, "face_low_confidence": 1, "no_face": 1},
    }
