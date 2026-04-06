from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict

from rdflib import Graph
from rdflib.namespace import DCTERMS, FOAF


def summarize_years(graph: Graph) -> Dict[str, int]:
    counter: Counter[str] = Counter()
    for _, _, year in graph.triples((None, DCTERMS.issued, None)):
        counter[str(year)] += 1
    return dict(counter)


def openness_share(graph: Graph) -> Dict[str, float]:
    total = 0
    open_count = 0
    for _, _, access in graph.triples((None, DCTERMS.accessRights, None)):
        total += 1
        if str(access).lower() == "aberto":
            open_count += 1
    if total == 0:
        return {"open": 0.0, "restricted": 0.0}
    return {
        "open": round(open_count / total, 2),
        "restricted": round((total - open_count) / total, 2),
    }


def top_authors(graph: Graph, top_k: int = 10) -> Dict[str, int]:
    counter: Counter[str] = Counter()
    for _, _, name in graph.triples((None, FOAF.name, None)):
        counter[str(name)] += 1
    return dict(counter.most_common(top_k))


def keywords_heatmap(graph: Graph, top_k: int = 10) -> Dict[str, int]:
    from rdflib.namespace import SCHEMA

    counter: Counter[str] = Counter()
    for _, _, keyword in graph.triples((None, SCHEMA.keywords, None)):
        counter[str(keyword).lower()] += 1
    return dict(counter.most_common(top_k))


def build_dashboard_metrics(graph: Graph) -> Dict[str, Dict[str, int]]:
    metrics = defaultdict(dict)
    metrics["years"] = summarize_years(graph)
    metrics["openness"] = openness_share(graph)
    metrics["authors"] = top_authors(graph)
    metrics["keywords"] = keywords_heatmap(graph)
    return metrics
