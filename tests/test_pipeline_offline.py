from __future__ import annotations

from src.curation.pipeline import run_pipeline
from src.graph.graph_builder import build_graph


def test_run_pipeline_offline_deduplicates_to_five_documents():
    docs = run_pipeline(use_remote=False)

    assert len(docs) == 5
    assert len({doc["title"] for doc in docs}) == 5


def test_run_pipeline_offline_prefers_domain_sources_over_openalex_fallback():
    docs = {doc["id"]: doc for doc in run_pipeline(use_remote=False)}

    assert docs["002"]["source"] == "brcris"
    assert docs["003"]["source"] == "bdtd"
    assert docs["004"]["source"] == "openalex-fallback"


def test_build_graph_from_offline_pipeline_contains_documents():
    docs = run_pipeline(use_remote=False)
    graph = build_graph(docs)

    document_count = sum(1 for _ in graph.subjects())

    assert len(graph) > 0
    assert document_count >= 5
