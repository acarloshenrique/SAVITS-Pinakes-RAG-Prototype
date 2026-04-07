from __future__ import annotations

from src.ingestion.source_client import extract_records, load_cache, write_cache


def test_extract_records_from_multiple_payload_shapes():
    payload = {"results": [{"id": "A"}]}
    records = extract_records(payload, ("content", "results"))
    assert records == [{"id": "A"}]

    payload = {"content": [{"id": "B"}]}
    records = extract_records(payload, ("content", "results"))
    assert records == [{"id": "B"}]

    payload = [{"id": "C"}]
    records = extract_records(payload, ("content", "results"))
    assert records == [{"id": "C"}]


def test_cache_roundtrip_uses_cache_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("INGESTION_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("INGESTION_CACHE_TTL_HOURS", "24")

    write_cache("openalex", [{"id": "001", "title": "Doc 1"}], origin="remote")
    cached = load_cache("openalex")

    assert cached is not None
    assert cached[0]["id"] == "001"
    assert cached[0]["ingestion_mode"] == "cache"
