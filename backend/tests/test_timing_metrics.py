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
    metrics.record(
        "confirmed",
        "face_confirmed",
        blocked=False,
        detection_source="face",
    )
    metrics.record(
        "uncertain",
        "pose_partial",
        blocked=False,
        detection_source="pose",
    )
    metrics.record(
        "missing",
        "no_subject_signal",
        blocked=True,
        detection_source="none",
    )
    assert metrics.snapshot() == {
        "total": 3,
        "passed": 2,
        "blocked": 1,
        "block_rate": 0.3333,
        "states": {"confirmed": 1, "uncertain": 1, "missing": 1},
        "reasons": {
            "face_confirmed": 1,
            "pose_partial": 1,
            "no_subject_signal": 1,
        },
        "sources": {"face": 1, "pose": 1, "none": 1},
        "history_recovered": 0,
    }
