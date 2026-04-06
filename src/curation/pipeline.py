from __future__ import annotations

import os
from typing import List

from src.curation.metadata_normalizer import normalize_record
from src.ingestion.bdtd_harvester import harvest_bdtd
from src.ingestion.brcris_harvester import harvest_brcris
from src.ingestion.oasisbr_harvester import harvest_oasisbr
from src.ingestion.openalex_harvester import harvest_openalex
from src.pinakes_mapper import create_pinakes_graph, process_social_technology_record


def _map_to_social_record(record: dict) -> dict:
    authors = record.get("authors") or []
    primary_author = authors[0]["name"] if authors else "Equipe SAVITS"
    impact_area = record.get("impact_area")
    if isinstance(impact_area, list):
        impact_area = ", ".join(impact_area)
    return {
        "id": record.get("id"),
        "title": record.get("title"),
        "author": primary_author,
        "impact_area": impact_area or "Cidadania e Informação",
        "maturity_level": record.get("maturity_level"),
    }


def run_pipeline(return_pinakes_graph: bool = False):
    """
    Harvest raw records, normalize them for FAIR/CARE compliance and optionally
    materialize a Pinakes-ready RDF graph with dARK identifiers.
    """
    use_remote = os.getenv("SAVITS_USE_REMOTE_SOURCES") == "1"
    harvested: List[dict] = []
    harvesters = [
        lambda: harvest_openalex(),
        lambda: harvest_brcris(use_remote=use_remote),
        lambda: harvest_oasisbr(use_remote=use_remote),
        lambda: harvest_bdtd(use_remote=use_remote),
    ]
    for getter in harvesters:
        try:
            harvested.extend(getter())
        except Exception as exc:
            print(f"[INGEST] Falha ao coletar dados ({exc}).")

    seen = set()
    cleaned: List[dict] = []
    for record in harvested:
        dedup_key = record.get("doi") or record.get("id") or record.get("title")
        if not dedup_key or dedup_key not in seen:
            seen.add(dedup_key)
            cleaned.append(normalize_record(record))

    if not return_pinakes_graph:
        return cleaned

    graph = create_pinakes_graph()
    for normalized in cleaned:
        process_social_technology_record(graph, _map_to_social_record(normalized))
    return cleaned, graph


if __name__ == "__main__":
    docs, _graph = run_pipeline(return_pinakes_graph=True)
    print("Documentos processados:", len(docs))
