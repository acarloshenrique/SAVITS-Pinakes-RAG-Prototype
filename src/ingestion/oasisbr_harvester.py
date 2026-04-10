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


def _extract_authors(value: Any) -> List[str]:
    if isinstance(value, list):
        return _listify(value)
    if isinstance(value, dict):
        names: List[str] = []
        for group in ("primary", "secondary", "corporate"):
            entries = value.get(group)
            if isinstance(entries, dict):
                names.extend([name.strip() for name in entries.keys() if name.strip()])
            elif isinstance(entries, list):
                names.extend(_listify(entries))
        return names
    return []


def _flatten_subjects(value: Any) -> List[str]:
    if not isinstance(value, list):
        return _listify(value)
    flattened: List[str] = []
    for row in value:
        if isinstance(row, list):
            flattened.extend(_listify(row))
        else:
            flattened.extend(_listify(row))
    return flattened


def _extract_url(value: Any) -> str | None:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                raw_url = item.get("url") or item.get("desc")
                if isinstance(raw_url, str) and raw_url.strip():
                    return raw_url.strip()
            elif isinstance(item, str) and item.strip():
                return item.strip()
        return None
    if isinstance(value, str):
        return value.strip() or None
    return None


def _map_remote_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    metadata = entry.get("metadata") or entry
    subjects = metadata.get("subjects") or metadata.get("subject") or metadata.get("topic") or entry.get("subjects")
    return {
        "id": _first_text(metadata.get("id") or metadata.get("identifier"), metadata.get("recordid")),
        "title": _first_text(metadata.get("title"), _first_text(entry.get("title"))),
        "year": _first_text(metadata.get("publishDate") or metadata.get("year") or metadata.get("date")),
        "authors": _extract_authors(metadata.get("authors") or metadata.get("author") or entry.get("authors") or entry.get("author")),
        "doi": metadata.get("doi"),
        "abstract": _first_text(metadata.get("description"), ""),
        "keywords": _flatten_subjects(subjects) or _listify(entry.get("keywords")),
        "acesso": "aberto",
        "licenca": _first_text(metadata.get("rights"), "https://creativecommons.org/licenses/by/4.0/"),
        "impact_area": _flatten_subjects(subjects),
        "maturity_level": "Oasisbr",
        "source": "oasisbr",
        "source_uri": _extract_url(metadata.get("urls"))
        or _first_text(metadata.get("url") or metadata.get("link"), metadata.get("id")),
        "ingestion_mode": "remote",
    }


def _fetch_remote(limit: int | None, query: str | None = None) -> List[Dict[str, Any]]:
    page = 1
    page_size = 30 if not limit else min(30, max(1, limit))
    collected: List[Dict[str, Any]] = []
    captured_sample = False
    max_pages_allowed = max_pages()

    while page <= max_pages_allowed:
        params = {
            "lookfor": query or "dados pesquisa",
            "type": "AllFields",
            "limit": page_size,
            "page": page,
            "sort": "relevance",
        }
        payload = request_json("oasisbr", OASISBR_API_URL, params=params, headers={"Accept": "application/json"})
        if not captured_sample:
            write_sample("oasisbr", payload)
            captured_sample = True

        records = extract_records(payload, ("records", "result", "results", "items"))
        if not records:
            break

        for entry in records:
            collected.append(_map_remote_entry(entry))

        if limit and len(collected) >= limit:
            break
        if len(records) < page_size:
            break
        page += 1

    deduped = unique_by(collected, "id", "doi", "title")
    if limit:
        return deduped[:limit]
    return deduped


def harvest_oasisbr(
    limit: int | None = None,
    force_refresh: bool = False,
    query: str | None = None,
    use_remote: bool = True,
) -> List[Dict[str, Any]]:
    if should_use_cache_first() and not force_refresh:
        cached = load_cache("oasisbr", limit=limit)
        if cached:
            return cached

    if not use_remote:
        stale_cache = load_cache("oasisbr", limit=limit, allow_stale=True)
        if stale_cache:
            return stale_cache
        return _fallback_records(limit)

    try:
        remote = _fetch_remote(limit, query=query)
        if remote:
            write_cache("oasisbr", remote, origin="remote")
            return remote[: limit or len(remote)]
    except Exception as exc:
        logger.warning("Oasisbr API unavailable, using cache/fallback: %s", exc)

    stale_cache = load_cache("oasisbr", limit=limit, allow_stale=True)
    if stale_cache:
        return stale_cache
    return _fallback_records(limit)


if __name__ == "__main__":
    docs = harvest_oasisbr(25)
    print("Oasisbr registros coletados:", len(docs))
