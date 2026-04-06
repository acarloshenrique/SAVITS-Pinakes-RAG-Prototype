from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

import requests

from .local_dataset import extract_authors, load_sample_works

logger = logging.getLogger(__name__)

BRCRIS_API_URL = os.environ.get("BRCRIS_API_URL", "https://brcris.ibict.br/api/works")
BRCRIS_API_TOKEN = os.environ.get("BRCRIS_API_TOKEN")


def _fallback_records(limit: int | None) -> List[Dict[str, Any]]:
    works = [w for w in load_sample_works() if (w.get("tipo") or "").startswith("artigo")]
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
                "acesso": work.get("acesso"),
                "licenca": work.get("licenca"),
                "impact_area": work.get("areas_cnpq"),
                "maturity_level": "Avaliado (BrCris - fallback)",
                "source": "brcris",
                "source_uri": "internal://raw_data.json#brcris",
            }
        )
    if limit:
        return records[:limit]
    return records


def _map_remote_work(work: Dict[str, Any]) -> Dict[str, Any]:
    authors = work.get("autores") or work.get("authors") or []
    author_names = []
    for author in authors:
        if isinstance(author, dict):
            author_names.append(author.get("name") or author.get("nome"))
        else:
            author_names.append(str(author))
    return {
        "id": work.get("id") or work.get("identifier"),
        "title": work.get("titulo") or work.get("title"),
        "year": work.get("ano") or work.get("year"),
        "authors": author_names,
        "doi": work.get("doi"),
        "abstract": work.get("resumo") or work.get("abstract"),
        "keywords": work.get("palavrasChave") or work.get("palavras_chave") or work.get("keywords"),
        "acesso": work.get("acesso") or work.get("accessRights"),
        "licenca": work.get("licenca") or work.get("license"),
        "impact_area": work.get("areasCnpq") or work.get("areas_cnpq"),
        "maturity_level": work.get("maturityLevel") or "Avaliado (BrCris)",
        "source": "brcris",
        "source_uri": work.get("handle") or work.get("url") or work.get("landingPage"),
        "prov_generated_by": work.get("provenance") or work.get("prov"),
    }


def _fetch_remote(limit: int | None) -> List[Dict[str, Any]]:
    params = {"limit": limit or 20}
    headers = {"Accept": "application/json"}
    if BRCRIS_API_TOKEN:
        headers["Authorization"] = f"Bearer {BRCRIS_API_TOKEN}"
    response = requests.get(BRCRIS_API_URL, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    payload = response.json()
    works = payload.get("content") or payload.get("results") or payload.get("works") or payload
    if not isinstance(works, list):
        return []
    return [_map_remote_work(work) for work in works]


def harvest_brcris(limit: int | None = None, use_remote: bool | None = None) -> List[Dict[str, Any]]:
    env_flag = os.getenv("SAVITS_USE_REMOTE_SOURCES")
    if use_remote is None:
        use_remote = env_flag != "0"

    if use_remote:
        try:
            remote = _fetch_remote(limit)
            if remote:
                return remote[: limit or len(remote)]
        except Exception as exc:
            logger.warning("BrCris API unavailable, using curated fallback: %s", exc)

    return _fallback_records(limit)


if __name__ == "__main__":
    docs = harvest_brcris(use_remote=True)
    print("BrCris registros coletados:", len(docs))

