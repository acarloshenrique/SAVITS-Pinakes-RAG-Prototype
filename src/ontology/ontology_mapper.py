from __future__ import annotations

from typing import Dict, List, Tuple

SKOS_MAP: Dict[str, Tuple[str, str]] = {
    "fair": ("http://www.w3.org/2004/02/skos/core#FAIR", "Princípios FAIR"),
    "lgpd": ("https://www.gov.br/lgpd", "Lei Geral de Proteção de Dados"),
    "ontologias": ("http://www.w3.org/2002/07/owl#", "Ontologias OWL"),
    "oai-pmh": ("http://www.openarchives.org/OAI/2.0/", "OAI-PMH"),
    "linked data": ("https://www.w3.org/standards/semanticweb/data", "Linked Data"),
}


def map_keywords_to_skos(keywords: List[str]) -> List[Dict[str, str]]:
    mapped: List[Dict[str, str]] = []
    for keyword in keywords:
        normalized = keyword.lower()
        uri, label = SKOS_MAP.get(normalized, (None, None))
        if uri:
            mapped.append({"keyword": keyword, "uri": uri, "label": label})
    return mapped


def enrich_record_with_skos(record: Dict[str, object]) -> Dict[str, object]:
    keywords = record.get("keywords") or record.get("palavras_chave") or []
    if isinstance(keywords, str):
        keywords = [keywords]
    record["skos_mappings"] = map_keywords_to_skos(keywords)
    return record
