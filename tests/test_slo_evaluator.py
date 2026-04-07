from src.analytics.slo_evaluator import SLOTargets, compute_metrics, evaluate_metrics


def test_slo_metrics_and_checks():
    events = [
        {
            "total_docs": 5,
            "remote_api_docs": 3,
            "retrieval_elapsed_seconds": 2.0,
            "blocked_by_reliability_gate": False,
            "per_source": {"openalex": {"remote": 2, "fallback": 0}},
        },
        {
            "total_docs": 4,
            "remote_api_docs": 1,
            "retrieval_elapsed_seconds": 7.0,
            "blocked_by_reliability_gate": False,
            "per_source": {"openalex": {"remote": 0, "fallback": 1}},
        },
    ]
    targets = SLOTargets(
        availability_min=0.9,
        latency_p95_max_seconds=8.0,
        remote_docs_min_n=2,
        remote_docs_ratio_min=0.4,
        fallback_ratio_max_default=0.6,
    )
    metrics = compute_metrics(events, targets)
    assert metrics["total_requests"] == 2
    assert metrics["availability_ratio"] == 1.0
    assert metrics["remote_docs_ratio"] == 0.5
    assert "openalex" in metrics["fallback_ratio_by_source"]

    report = evaluate_metrics(metrics, targets)
    assert report["pass"] is True
