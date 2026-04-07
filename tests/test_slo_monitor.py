import json

from src.analytics.slo_monitor import log_retrieval_event


def test_log_retrieval_event_writes_jsonl(tmp_path):
    out = tmp_path / "slo_events.jsonl"
    diagnostics = {
        "total": 5,
        "remote_api_docs": 3,
        "fallback_api_docs": 1,
        "per_source": {"openalex": {"remote": 2, "cache": 0, "fallback": 0}},
    }

    log_retrieval_event("consulta teste", 5, diagnostics, output_path=str(out))

    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["top_k"] == 5
    assert row["remote_api_docs"] == 3
    assert "timestamp" in row
