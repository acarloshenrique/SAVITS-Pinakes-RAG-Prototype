from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

from .local_dataset import extract_authors, load_sample_works
from .source_client import (
    extract_records,
    load_cache,
    max_pages,
    request_json,
    should_use_cache_first,
    unique_by,
    write_cache,
    write_sample,
)

logger = logging.getLogger(__name__)

BRCRIS_API_URL = os.environ.get("BRCRIS_API_URL", "https://dados.brcris.ibict.br/api/works")
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
                "ingestion_mode": "fallback",
            }
        )
    if limit:
        return records[:limit]
    return records


def _first_text(value: Any, default: str | None = None) -> str | None:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                return item.strip()
        return default
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or default
    return default


def _listify(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        if ";" in value:
            return [token.strip() for token in value.split(";") if token.strip()]
        if "," in value:
            return [token.strip() for token in value.split(",") if token.strip()]
        return [value.strip()] if value.strip() else []
    return [str(value)]


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
        "title": _first_text(work.get("titulo") or work.get("title"), work.get("name")),
        "year": _first_text(work.get("ano") or work.get("year") or work.get("publicationYear")),
        "authors": author_names,
        "doi": work.get("doi"),
        "abstract": work.get("resumo") or work.get("abstract"),
        "keywords": _listify(work.get("palavrasChave") or work.get("palavras_chave") or work.get("keywords")),
        "acesso": work.get("acesso") or work.get("accessRights"),
        "licenca": work.get("licenca") or work.get("license"),
        "impact_area": _listify(work.get("areasCnpq") or work.get("areas_cnpq")),
        "maturity_level": work.get("maturityLevel") or "Avaliado (BrCris)",
        "source": "brcris",
        "source_uri": work.get("handle") or work.get("url") or work.get("landingPage") or work.get("id"),
        "prov_generated_by": work.get("provenance") or work.get("prov"),
        "ingestion_mode": "remote",
    }


def _fetch_remote(limit: int | None, query: str | None = None) -> List[Dict[str, Any]]:
    headers = {"Accept": "application/json"}
    if BRCRIS_API_TOKEN:
        headers["Authorization"] = f"Bearer {BRCRIS_API_TOKEN}"
    page = 0
    page_size = 50 if not limit else min(50, max(1, limit))
    collected: List[Dict[str, Any]] = []
    captured_sample = False
    max_pages_allowed = max_pages()

    while page < max_pages_allowed:
        params = {"size": page_size, "page": page}
        if query:
            params["q"] = query
            params["search"] = query
        payload = request_json("brcris", BRCRIS_API_URL, params=params, headers=headers)
        if not captured_sample:
            write_sample("brcris", payload)
            captured_sample = True

        works = extract_records(payload, ("content", "results", "items", "data"))
        if not works:
            break

        for work in works:
            collected.append(_map_remote_work(work))

        if limit and len(collected) >= limit:
            break
        if len(works) < page_size:
            break
        page += 1

    deduped = unique_by(collected, "id", "doi", "title")
    if limit:
        return deduped[:limit]
    return deduped


def harvest_brcris(
    limit: int | None = None,
    force_refresh: bool = False,
    query: str | None = None,
    use_remote: bool = True,
) -> List[Dict[str, Any]]:
    if should_use_cache_first() and not force_refresh:
        cached = load_cache("brcris", limit=limit)
        if cached:
            return cached

    if not use_remote:
        stale_cache = load_cache("brcris", limit=limit, allow_stale=True)
        if stale_cache:
            return stale_cache
        return _fallback_records(limit)

    try:
        remote = _fetch_remote(limit, query=query)
        if remote:
            write_cache("brcris", remote, origin="remote")
            return remote[: limit or len(remote)]
    except Exception as exc:
        logger.warning("BrCris API unavailable, using cache/fallback: %s", exc)

    stale_cache = load_cache("brcris", limit=limit, allow_stale=True)
    if stale_cache:
        return stale_cache
    return _fallback_records(limit)


if __name__ == "__main__":
    docs = harvest_brcris(25)
    print("BrCris registros coletados:", len(docs))
