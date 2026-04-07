from __future__ import annotations

from src.ingestion.openalex_harvester import _decode_abstract, _map_remote_work


def test_decode_abstract_from_inverted_index():
    inverted = {"dados": [2], "governanca": [1], "de": [3]}
    assert _decode_abstract(inverted) == "governanca dados de"


def test_map_remote_work_normalizes_fields():
    work = {
        "id": "https://openalex.org/W123",
        "display_name": "Paper",
        "publication_year": 2024,
        "doi": "https://doi.org/10.1234/abc",
        "type": "article",
        "abstract_inverted_index": {"Hello": [0], "World": [1]},
        "authorships": [{"author": {"display_name": "Ana"}}],
        "concepts": [{"display_name": "Data Governance"}],
    }

    mapped = _map_remote_work(work)

    assert mapped["title"] == "Paper"
    assert mapped["authors"] == ["Ana"]
    assert mapped["abstract"] == "Hello World"
    assert mapped["keywords"] == ["Data Governance"]
    assert mapped["ingestion_mode"] == "remote"
