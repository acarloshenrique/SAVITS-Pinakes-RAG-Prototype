from __future__ import annotations

import json
import time
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

from rdflib import Graph
from rdflib.namespace import DCTERMS, RDF

from src.curation.pipeline import run_pipeline
from src.governance.fair_validator import evaluate_graph
from src.graph.graph_builder import BIBO, PINAKES, build_graph


ROOT_DIR = Path(__file__).resolve().parents[2]
REPORT_JSON = ROOT_DIR / "reports" / "benchmark_v1.0.0.json"
REPORT_MD = ROOT_DIR / "reports" / "benchmark_v1.0.0.md"
RELEASE_VERSION = "v1.0.0"
TOP_K = 3
BENCHMARK_CASES = [
    {
        "id": "fair-lgpd",
        "query": "Quais obras tratam especificamente de LGPD ou governanca de dados?",
        "expected_title": "Governança de Dados de Pesquisa no Brasil: Desafios FAIR e LGPD",
    },
    {
        "id": "agricultura-familiar",
        "query": "Liste tecnologias sociais focadas em agricultura familiar com impacto comprovado.",
        "expected_title": "Impacto das Mudanças Climáticas na Agricultura Familiar do Semiárido Nordestino",
    },
    {
        "id": "amazonia-biodiversidade",
        "query": "Existe alguma pesquisa que discuta biodiversidade na Amazonia? Cite autores e licencas.",
        "expected_title": "Aplicação de Redes Neurais na Análise de Biodiversidade Amazônica",
    },
    {
        "id": "sparql-rag",
        "query": "Recuperacao de informacao semantica com SPARQL em bases cientificas",
        "expected_title": "Recuperação de Informação Semântica com SPARQL em Bases de Dados Científicas",
    },
    {
        "id": "interoperabilidade",
        "query": "framework de interoperabilidade semantica entre repositorios de dados de pesquisa",
        "expected_title": "Interoperabilidade Semântica entre Repositórios de Dados de Pesquisa: Um Framework Baseado em Ontologias",
    },
]


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return text.encode("ascii", "ignore").decode("ascii").lower()


def _query_tokens(query: str) -> list[str]:
    tokens = [token for token in _normalize(query).split() if len(token) > 2]
    return tokens


def _doc_to_record(graph: Graph, subject) -> dict[str, Any]:
    def first(predicate, default: str = "") -> str:
        value = next(graph.objects(subject, predicate), None)
        return str(value) if value else default

    keywords = [str(value) for value in graph.objects(subject, DCTERMS.subject)]
    impact = [str(value) for value in graph.objects(subject, PINAKES.temImpactoSocial)]
    return {
        "uri": str(subject),
        "title": first(DCTERMS.title),
        "abstract": first(DCTERMS.abstract),
        "keywords": keywords,
        "impact_area": impact,
        "source": first(DCTERMS.source),
        "year": first(DCTERMS.issued, "0"),
    }


def _score(record: dict[str, Any], query: str) -> tuple[int, int]:
    haystack = " ".join(
        [
            record.get("title", ""),
            record.get("abstract", ""),
            " ".join(record.get("keywords", [])),
            " ".join(record.get("impact_area", [])),
            record.get("source", ""),
        ]
    )
    normalized = _normalize(haystack)
    token_hits = sum(1 for token in _query_tokens(query) if token in normalized)
    try:
        year = int(str(record.get("year", "0"))[:4])
    except ValueError:
        year = 0
    return token_hits, year


def _retrieve(records: list[dict[str, Any]], query: str, top_k: int = TOP_K) -> list[dict[str, Any]]:
    ranked = sorted(records, key=lambda record: _score(record, query), reverse=True)
    return ranked[:top_k]


def _percentile(latencies: list[float], percentile: float) -> float:
    if not latencies:
        return 0.0
    ordered = sorted(latencies)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * percentile)))
    return ordered[index]


def _build_report() -> dict[str, Any]:
    started_at = datetime.now(timezone.utc).isoformat()

    build_started = time.perf_counter()
    docs = run_pipeline(use_remote=False)
    graph = build_graph(docs)
    build_ms = round((time.perf_counter() - build_started) * 1000, 2)

    graph_records = [
        _doc_to_record(graph, subject)
        for subject in graph.subjects(RDF.type, BIBO.Document)
    ]

    latencies: list[float] = []
    retrieval_cases = []
    for case in BENCHMARK_CASES:
        query_started = time.perf_counter()
        results = _retrieve(graph_records, case["query"])
        latency_ms = round((time.perf_counter() - query_started) * 1000, 3)
        latencies.append(latency_ms)
        top_titles = [result["title"] for result in results]
        retrieval_cases.append(
            {
                "id": case["id"],
                "query": case["query"],
                "expected_title": case["expected_title"],
                "top_titles": top_titles,
                "top_1_match": bool(top_titles and top_titles[0] == case["expected_title"]),
                "top_3_match": case["expected_title"] in top_titles,
                "latency_ms": latency_ms,
            }
        )

    governance = evaluate_graph(graph)
    score_map = {score["pillar"]: score["coverage"] for score in governance["scores"]}
    source_mix = dict(Counter(doc["source"] for doc in docs))
    top_1_accuracy = round(
        sum(1 for case in retrieval_cases if case["top_1_match"]) / len(retrieval_cases),
        2,
    )
    top_3_accuracy = round(
        sum(1 for case in retrieval_cases if case["top_3_match"]) / len(retrieval_cases),
        2,
    )

    return {
        "release": RELEASE_VERSION,
        "generated_at": started_at,
        "documents": len(docs),
        "graph_triples": len(graph),
        "source_mix": source_mix,
        "build_time_ms": build_ms,
        "retrieval": {
            "top_k": TOP_K,
            "cases": len(retrieval_cases),
            "top_1_accuracy": top_1_accuracy,
            "top_3_accuracy": top_3_accuracy,
            "median_latency_ms": round(median(latencies), 3),
            "p95_latency_ms": round(_percentile(latencies, 0.95), 3),
            "cases_detail": retrieval_cases,
        },
        "governance": {
            "documents": governance["documents"],
            "scores": score_map,
            "issues": governance["issues"],
        },
    }


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Benchmark {report['release']}",
        "",
        "## Summary",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Offline documents: **{report['documents']}**",
        f"- Enriched graph triples: **{report['graph_triples']}**",
        f"- Offline build time: **{report['build_time_ms']} ms**",
        f"- Retrieval Top-1 accuracy: **{report['retrieval']['top_1_accuracy'] * 100:.0f}%**",
        f"- Retrieval Top-3 accuracy: **{report['retrieval']['top_3_accuracy'] * 100:.0f}%**",
        f"- Median retrieval latency: **{report['retrieval']['median_latency_ms']} ms**",
        f"- P95 retrieval latency: **{report['retrieval']['p95_latency_ms']} ms**",
        "",
        "## Source Mix",
        "",
    ]

    for source, count in report["source_mix"].items():
        lines.append(f"- `{source}`: {count} documents")

    lines.extend(
        [
            "",
            "## Governance Coverage",
            "",
        ]
    )
    for pillar, coverage in report["governance"]["scores"].items():
        lines.append(f"- `{pillar}`: {coverage * 100:.0f}%")

    lines.extend(
        [
            "",
            "## Retrieval Cases",
            "",
            "| Case | Expected | Top result | Top-3 | Latency (ms) |",
            "| --- | --- | --- | --- | ---: |",
        ]
    )

    for case in report["retrieval"]["cases_detail"]:
        top_result = case["top_titles"][0] if case["top_titles"] else "-"
        lines.append(
            f"| `{case['id']}` | {case['expected_title']} | {top_result} | "
            f"{'yes' if case['top_3_match'] else 'no'} | {case['latency_ms']} |"
        )

    lines.extend(
        [
            "",
            "## Method",
            "",
            "- `python -m src.evaluation.simple_benchmark`",
            "- Offline mode using `run_pipeline(use_remote=False)`",
            "- Retrieval scored over title, abstract, keywords, impact area, and source fields",
            "- FAIR/CARE coverage computed with `src.governance.fair_validator.evaluate_graph`",
        ]
    )
    return "\n".join(lines) + "\n"


def write_report() -> dict[str, Any]:
    report = _build_report()
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(report), encoding="utf-8")
    return report


if __name__ == "__main__":
    report = write_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
