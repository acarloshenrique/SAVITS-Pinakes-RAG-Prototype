from __future__ import annotations

from src.ingestion.source_client import extract_records, load_cache, write_cache


def test_extract_records_from_multiple_payload_shapes():
    assert extract_records({"content": [{"id": "1"}]}, ("content", "items")) == [{"id": "1"}]
    assert extract_records({"result": {"records": [{"id": "2"}]}}, ("records", "items")) == [{"id": "2"}]
    assert extract_records({"items": [{"id": "3"}]}, ("content", "items")) == [{"id": "3"}]


def test_cache_roundtrip_uses_cache_mode():
    source = "test-source-client"
    records = [{"id": "abc", "title": "Pinakes"}]
    write_cache(source, records, origin="remote")

    cached = load_cache(source, limit=1)

    assert cached == records
