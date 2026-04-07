from __future__ import annotations

from typing import Dict, List

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import DCTERMS, RDF

BIBO = Namespace("http://purl.org/ontology/bibo/")
PINAKES = Namespace("https://pinakes.ibict.br/ontology/")
PROV = Namespace("http://www.w3.org/ns/prov#")


def _documents(graph: Graph) -> List[URIRef]:
    docs = {subject for subject in graph.subjects(RDF.type, BIBO.Document)}
    if not docs:
        docs = {subject for subject in graph.subjects(DCTERMS.title, None)}
    return list(docs)


def summarize_provenance(graph: Graph) -> Dict[str, List[str]]:
    missing_source: List[str] = []
    missing_prov: List[str] = []
    missing_lgpd: List[str] = []

    for doc in _documents(graph):
        title = next(graph.objects(doc, DCTERMS.title), doc)
        has_source = any(graph.objects(doc, DCTERMS.source))
        has_prov = any(graph.objects(doc, PROV.wasGeneratedBy))
        has_lgpd = any(graph.objects(doc, PINAKES.baseLegalLGPD))

        if not has_source:
            missing_source.append(str(title))
        if not has_prov:
            missing_prov.append(str(title))
        if not has_lgpd:
            missing_lgpd.append(str(title))

    return {
        "missing_source": missing_source,
        "missing_provenance": missing_prov,
        "missing_lgpd": missing_lgpd,
    }


def governance_indicators(graph: Graph) -> Dict[str, object]:
    provenance = summarize_provenance(graph)
    documents = _documents(graph)
    total = len(documents) or 1
    return {
        "provenance": provenance,
        "source_coverage": round(1 - len(provenance["missing_source"]) / total, 2),
        "prov_coverage": round(1 - len(provenance["missing_provenance"]) / total, 2),
        "lgpd_coverage": round(1 - len(provenance["missing_lgpd"]) / total, 2),
    }

