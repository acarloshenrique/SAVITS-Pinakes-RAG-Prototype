from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

import requests

from .local_dataset import extract_authors, load_sample_works

logger = logging.getLogger(__name__)

OASISBR_API_URL = os.environ.get("OASISBR_API_URL", "https://oasisbr.ibict.br/vufind/api/v1/search")


def _fallback_records(limit: int | None) -> List[Dict[str, Any]]:
    works = [w for w in load_sample_works() if (w.get("acesso") or "").lower() == "aberto"]
    records: List[Dict[str, Any]] = []
    for work in works:
        records.append(
            {
                "id": work.get("id"),
                "title": work.get("titulo"),
                "year": work.get("ano"),
                "authors": extract_authors(work),
                "doi": work.get("doi"),
                "abstract": work.get("resumo"),
                "keywords": work.get("palavras_chave"),
                "acesso": "aberto",
                "licenca": work.get("licenca"),
                "impact_area": work.get("areas_cnpq"),
                "maturity_level": "Oasisbr - fallback",
                "source": "oasisbr",
                "source_uri": "internal://raw_data.json#oasisbr",
            }
        )
    if limit:
        return records[:limit]
    return records


def _map_remote_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    metadata = entry.get("metadata") or entry
    return {
        "id": metadata.get("id") or metadata.get("identifier"),
        "title": metadata.get("title"),
        "year": metadata.get("publishDate") or metadata.get("year"),
        "authors": metadata.get("author") or [],
        "doi": metadata.get("doi"),
        "abstract": metadata.get("description"),
        "keywords": metadata.get("subject") or entry.get("keywords"),
        "acesso": "aberto",
        "licenca": metadata.get("rights") or "https://creativecommons.org/licenses/by/4.0/",
        "impact_area": metadata.get("subject") or [],
        "maturity_level": "Oasisbr",
        "source": "oasisbr",
        "source_uri": metadata.get("url") or metadata.get("link"),
    }


def _fetch_remote(limit: int | None) -> List[Dict[str, Any]]:
    params = {
        "lookfor": "dados pesquisa",
        "type": "AllFields",
        "limit": limit or 30,
        "sort": "relevance",
    }
    response = requests.get(OASISBR_API_URL, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    records = payload.get("records") or payload.get("result") or []
    return [_map_remote_entry(entry) for entry in records]


def harvest_oasisbr(limit: int | None = None, use_remote: bool | None = None) -> List[Dict[str, Any]]:
    env_flag = os.getenv("SAVITS_USE_REMOTE_SOURCES")
    if use_remote is None:
        use_remote = env_flag != "0"

    if use_remote:
        try:
            remote = _fetch_remote(limit)
            if remote:
                return remote[: limit or len(remote)]
        except Exception as exc:
            logger.warning("Oasisbr API unavailable, falling back to bundled dataset: %s", exc)

    return _fallback_records(limit)


if __name__ == "__main__":
    docs = harvest_oasisbr(use_remote=True)
    print("Oasisbr registros coletados:", len(docs))

