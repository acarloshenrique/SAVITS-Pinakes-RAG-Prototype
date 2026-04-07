from src.ingestion.source_health import summarize_source_health


def test_source_health_summary_counts_remote_and_fallback():
    rows = [
        {"source": "openalex", "ok": True, "mode": "remote", "count": 30},
        {"source": "oasisbr", "ok": True, "mode": "cache", "count": 10},
        {"source": "bdtd", "ok": True, "mode": "fallback", "count": 3},
        {"source": "brcris", "ok": False, "mode": "error", "count": 0},
    ]
    summary = summarize_source_health(rows)

    assert summary["remote_ready_sources"] == 2
    assert summary["fallback_only_sources"] == 1
    assert summary["primary_remote_ready"] == 2
    assert summary["healthy"] is True
