from __future__ import annotations

import logging
import os
from typing import Dict, List

import requests

from .local_dataset import extract_authors, load_sample_works

logger = logging.getLogger(__name__)

THESIS_TYPES = {"tese", "dissertacao"}
BDTD_API_URL = os.environ.get("BDTD_API_URL", "https://bdtd.ibict.br/vufind/api/v1/search")


def _fallback_records(limit: int | None) -> List[Dict[str, str]]:
    works = [w for w in load_sample_works() if (w.get("tipo") or "").lower() in THESIS_TYPES]
    records: List[Dict[str, str]] = []
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
                "acesso": work.get("acesso"),
                "licenca": work.get("licenca"),
                "impact_area": work.get("areas_cnpq"),
                "maturity_level": "BDTD - fallback",
                "source": "bdtd",
                "source_uri": "internal://raw_data.json#bdtd",
            }
        )
    if limit:
        return records[:limit]
    return records


def _map_remote_entry(entry: Dict[str, str]) -> Dict[str, str]:
    metadata = entry.get("metadata") or entry
    return {
        "id": metadata.get("id") or metadata.get("identifier"),
        "title": metadata.get("title"),
        "year": metadata.get("publishDate") or metadata.get("year"),
        "authors": metadata.get("author") or [],
        "doi": metadata.get("doi"),
        "abstract": metadata.get("description"),
        "keywords": metadata.get("subject") or [],
        "acesso": metadata.get("accessRights") or "restrito",
        "licenca": metadata.get("rights"),
        "impact_area": metadata.get("subject") or [],
        "maturity_level": "BDTD",
        "source": "bdtd",
        "source_uri": metadata.get("url") or metadata.get("link"),
    }


def _fetch_remote(limit: int | None) -> List[Dict[str, str]]:
    params = {
        "lookfor": "teses dados",
        "type": "AllFields",
        "limit": limit or 20,
        "sort": "year",
    }
    response = requests.get(BDTD_API_URL, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    records = payload.get("records") or payload.get("result") or []
    thesis_only = [entry for entry in records if "tese" in (entry.get("format", "") or "").lower()]
    return [_map_remote_entry(entry) for entry in thesis_only]


def harvest_bdtd(limit: int | None = None, use_remote: bool | None = None) -> List[Dict[str, str]]:
    env_flag = os.getenv("SAVITS_USE_REMOTE_SOURCES")
    if use_remote is None:
        use_remote = env_flag != "0"

    if use_remote:
        try:
            remote = _fetch_remote(limit)
            if remote:
                return remote[: limit or len(remote)]
        except Exception as exc:
            logger.warning("BDTD API unavailable, revert to embedded dataset: %s", exc)

    return _fallback_records(limit)


if __name__ == "__main__":
    docs = harvest_bdtd(use_remote=True)
    print("BDTD registros coletados:", len(docs))

