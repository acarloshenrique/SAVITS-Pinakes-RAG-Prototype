from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, RDF

from src.governance.provenance_tracker import governance_indicators

BIBO = Namespace("http://purl.org/ontology/bibo/")
PINAKES = Namespace("https://pinakes.ibict.br/ontology/")
PROV = Namespace("http://www.w3.org/ns/prov#")


def test_governance_indicator_flags_missing_metadata():
    graph = Graph()
    doc_ok = URIRef("https://example.org/doc/ok")
    graph.add((doc_ok, RDF.type, BIBO.Document))
    graph.add((doc_ok, DCTERMS.title, Literal("Doc OK")))
    graph.add((doc_ok, DCTERMS.source, Literal("brcris")))
    graph.add((doc_ok, PROV.wasGeneratedBy, URIRef("https://example.org/activity/ok")))
    graph.add((doc_ok, PINAKES.baseLegalLGPD, Literal("Consentimento")))

    doc_missing = URIRef("https://example.org/doc/missing")
    graph.add((doc_missing, RDF.type, BIBO.Document))
    graph.add((doc_missing, DCTERMS.title, Literal("Doc Missing")))

    report = governance_indicators(graph)

    assert 0 <= report["source_coverage"] <= 1
    assert 0 <= report["prov_coverage"] <= 1
    missing_sources = report["provenance"]["missing_source"]
    assert missing_sources
    assert any("Doc Missing" in entry for entry in missing_sources)
    assert report["provenance"]["missing_lgpd"], "Should flag documents sem base legal"
