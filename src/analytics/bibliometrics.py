from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, List, Tuple

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import DCTERMS, FOAF, RDF

BIBO = Namespace("http://purl.org/ontology/bibo/")
SCHEMA = Namespace("https://schema.org/")
PINAKES = Namespace("https://pinakes.ibict.br/ontology/")


# Legacy dashboard helpers ----------------------------------------------------
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
        if str(access).lower().startswith("abert"):
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


# FAIR/LGPD analytics ---------------------------------------------------------
def _documents(graph: Graph) -> List[URIRef]:
    docs = {subject for subject in graph.subjects(RDF.type, BIBO.Document)}
    if not docs:
        docs = {subject for subject in graph.subjects(DCTERMS.title, None)}
    return list(docs)


def _counter_to_list(counter: Counter, limit: int = 5) -> List[Tuple[str, int]]:
    return [(item, count) for item, count in counter.most_common(limit)]


def compute_graph_kpis(graph: Graph) -> Dict[str, object]:
    documents = _documents(graph)
    total = len(documents)
    if total == 0:
        return {
            "total_documents": 0,
            "open_access_ratio": 0.0,
            "lgpd_compliance": 0.0,
            "impact_coverage": 0.0,
            "deia_coverage": 0.0,
            "sources": [],
            "top_keywords": [],
        }

    open_access = 0
    lgpd_ready = 0
    impact_ready = 0
    deia_ready = 0
    sources = Counter()
    keywords = Counter()

    for doc in documents:
        for source in graph.objects(doc, DCTERMS.source):
            sources[str(source)] += 1

        access = next(graph.objects(doc, DCTERMS.accessRights), None)
        if access and str(access).lower().startswith("abert"):
            open_access += 1

        if any(graph.objects(doc, PINAKES.baseLegalLGPD)):
            lgpd_ready += 1

        if any(graph.objects(doc, PINAKES.temImpactoSocial)):
            impact_ready += 1

        if any(graph.objects(doc, PINAKES.deiaTag)):
            deia_ready += 1

        for kw in graph.objects(doc, SCHEMA.keywords):
            keywords[str(kw)] += 1

    return {
        "total_documents": total,
        "open_access_ratio": round(open_access / total, 2),
        "lgpd_compliance": round(lgpd_ready / total, 2),
        "impact_coverage": round(impact_ready / total, 2),
        "deia_coverage": round(deia_ready / total, 2),
        "sources": _counter_to_list(sources),
        "top_keywords": _counter_to_list(keywords),
    }


def detect_deia_gaps(graph: Graph) -> List[str]:
    gaps: List[str] = []
    for doc in _documents(graph):
        if any(graph.objects(doc, PINAKES.deiaTag)):
            continue
        title = next(graph.objects(doc, DCTERMS.title), doc)
        gaps.append(str(title))
    return gaps

