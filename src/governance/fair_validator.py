"""
Governance helpers to score the SAVITS knowledge graph against FAIR/CARE guardrails.
The heuristics are intentionally lightweight so they can run inside Streamlit or CI
without extra dependencies while still surfacing concrete issues for bibliotecários.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List

from rdflib import Graph, URIRef
from rdflib.namespace import DC, DCTERMS, FOAF, RDF


# Custom namespaces reused across the project
PINAKES = URIRef("https://pinakes.ibict.br/ontology/")
SCHEMA = URIRef("https://schema.org/")
BIBO = URIRef("http://purl.org/ontology/bibo/")
PROV = URIRef("http://www.w3.org/ns/prov#")


@dataclass
class PillarScore:
    name: str
    compliant: int = 0
    total: int = 0

    def to_dict(self) -> Dict[str, float]:
        coverage = self.compliant / self.total if self.total else 0.0
        return {"pillar": self.name, "compliant": self.compliant, "total": self.total, "coverage": round(coverage, 2)}


@dataclass
class ComplianceIssue:
    pillar: str
    severity: str
    resource: str
    detail: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


def _first(graph: Graph, subject: URIRef, predicates: Iterable[URIRef]) -> bool:
    for predicate in predicates:
        if any(graph.objects(subject, predicate)):
            return True
    return False


def _qname(graph: Graph, subject: URIRef) -> str:
    try:
        return graph.qname(subject)
    except Exception:
        return str(subject)


def evaluate_graph(graph: Graph) -> Dict[str, List[Dict[str, str]]]:
    """Return coverage metrics plus detailed findings for FAIR/CARE pillars."""
    documents = {s for s in graph.subjects(RDF.type, URIRef(f"{BIBO}Document"))}
    if not documents:
        documents = {s for s in graph.subjects(DCTERMS.title, None)}

    scores: Dict[str, PillarScore] = {
        "FAIR_FINDABLE": PillarScore("FAIR_FINDABLE"),
        "FAIR_ACCESSIBLE": PillarScore("FAIR_ACCESSIBLE"),
        "FAIR_INTEROPERABLE": PillarScore("FAIR_INTEROPERABLE"),
        "FAIR_REUSABLE": PillarScore("FAIR_REUSABLE"),
        "CARE_COLLECTIVE": PillarScore("CARE_COLLECTIVE"),
        "CARE_AUTHORITY": PillarScore("CARE_AUTHORITY"),
        "CARE_RESPONSIBILITY": PillarScore("CARE_RESPONSIBILITY"),
    }
    issues: List[ComplianceIssue] = []

    for doc in documents:
        label = _qname(graph, doc)

        def record(pillar: str, condition: bool, detail: str, severity: str = "WARN"):
            score = scores[pillar]
            score.total += 1
            if condition:
                score.compliant += 1
            else:
                issues.append(ComplianceIssue(pillar=pillar, severity=severity, resource=label, detail=detail))

        record(
            "FAIR_FINDABLE",
            _first(graph, doc, [DCTERMS.identifier, DC.identifier, URIRef(f"{BIBO}doi")]),
            "Documento sem identificador persistente (DOI, ARK ou dc:identifier).",
        )
        record(
            "FAIR_ACCESSIBLE",
            _first(graph, doc, [DCTERMS.accessRights, DCTERMS.license]),
            "Informe direitos de acesso/licença para reutilização controlada.",
        )
        record(
            "FAIR_INTEROPERABLE",
            _first(graph, doc, [DCTERMS.subject, URIRef(f"{SCHEMA}keywords"), FOAF.name]),
            "Inclua assuntos/keywords interoperáveis com ontologias públicas.",
        )
        record(
            "FAIR_REUSABLE",
            _first(graph, doc, [DCTERMS.abstract, DC.description]) and _first(graph, doc, [DCTERMS.source, URIRef(f"{PROV}wasGeneratedBy")]),
            "Faltam resumo/contexto ou vínculos PROV-O para rastreabilidade.",
        )
        record(
            "CARE_COLLECTIVE",
            _first(graph, doc, [URIRef(f"{PINAKES}temImpactoSocial"), URIRef(f"{PINAKES}areasCnpq")]),
            "Informe impacto social/área CNPq para demonstrar benefício coletivo.",
        )
        record(
            "CARE_AUTHORITY",
            _first(graph, doc, [URIRef(f"{PINAKES}statusLGPD"), URIRef(f"{PINAKES}baseLegalLGPD")]),
            "Registre status/base legal LGPD para garantir agência dos titulares.",
        )
        record(
            "CARE_RESPONSIBILITY",
            _first(graph, doc, [URIRef(f"{PINAKES}dataProcessamento"), URIRef(f"{PROV}wasGeneratedBy")]),
            "Faltam marcas de processamento/proveniência para responsabilização.",
        )

    return {
        "documents": len(documents),
        "scores": [score.to_dict() for score in scores.values()],
        "issues": [issue.to_dict() for issue in issues],
    }


def validate_graph(path: Path) -> Dict[str, List[Dict[str, str]]]:
    graph = Graph()
    graph.parse(path, format="turtle")
    return evaluate_graph(graph)


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Run FAIR/CARE compliance validation on a Turtle graph.")
    parser.add_argument("graph_path", help="Path to pinakes_graph.ttl", type=Path)
    args = parser.parse_args()
    report = validate_graph(args.graph_path)
    print(json.dumps(report, indent=2, ensure_ascii=False))
