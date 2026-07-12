from core.timing_metrics import TimingMetrics


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
