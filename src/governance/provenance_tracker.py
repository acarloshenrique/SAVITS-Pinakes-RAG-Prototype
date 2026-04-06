from __future__ import annotations

from typing import Dict, List

from rdflib import Graph
from rdflib.namespace import DCTERMS

from .fair_validator import evaluate_graph


def list_missing_provenance(graph: Graph) -> List[str]:
    """Return URIs that do not cite prov:wasGeneratedBy."""
    from rdflib.namespace import PROV

    missing: List[str] = []
    for subject in graph.subjects(DCTERMS.title, None):
        has_prov = any(graph.objects(subject, PROV.wasGeneratedBy))
        if not has_prov:
            missing.append(str(subject))
    return missing


def governance_dashboard(graph: Graph) -> Dict[str, object]:
    """Combine FAIR/CARE evaluation with provenance-specific diagnostics."""
    report = evaluate_graph(graph)
    report["missingProvenance"] = list_missing_provenance(graph)
    return report
