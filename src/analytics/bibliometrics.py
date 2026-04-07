from __future__ import annotations

from collections import Counter
from typing import Dict, List, Tuple

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import DCTERMS, RDF

BIBO = Namespace("http://purl.org/ontology/bibo/")
SCHEMA = Namespace("https://schema.org/")
PINAKES = Namespace("https://pinakes.ibict.br/ontology/")


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

