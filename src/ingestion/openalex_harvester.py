import logging

from .local_dataset import load_sample_works
from .source_client import (
    load_cache,
    request_json,
    should_use_cache_first,
    unique_by,
    write_cache,
    write_sample,
)

logger = logging.getLogger(__name__)

OPENALEX_URL = "https://api.openalex.org/works"


def _fallback_records(limit: int | None) -> list[dict]:
    works = load_sample_works()
    if limit:
        works = works[:limit]
    return [
        {
            "id": work.get("id"),
            "title": work.get("titulo"),
            "year": work.get("ano"),
            "authors": [a.get("nome") if isinstance(a, dict) else a for a in work.get("autores", [])],
            "doi": work.get("doi"),
            "abstract": work.get("resumo"),
            "keywords": work.get("palavras_chave"),
            "impact_area": work.get("areas_cnpq"),
            "source": "openalex-fallback",
            "source_uri": "internal://raw_data.json#openalex",
            "ingestion_mode": "fallback",
        }
        for work in works
    ]


def _decode_abstract(inverted_index) -> str:
    if not isinstance(inverted_index, dict):
        return ""
    indexed_tokens = []
    for token, positions in inverted_index.items():
        if not isinstance(positions, list):
            continue
        for pos in positions:
            indexed_tokens.append((pos, token))
    indexed_tokens.sort(key=lambda item: item[0])
    return " ".join(token for _, token in indexed_tokens)


def _map_remote_work(work: dict) -> dict:
    concepts = work.get("concepts") or []
    impact_area = [concept.get("display_name") for concept in concepts[:3] if concept.get("display_name")]
    authorships = work.get("authorships") or []
    return {
        "id": work.get("id"),
        "title": work.get("display_name") or work.get("title"),
        "year": work.get("publication_year"),
        "authors": [
            authorship.get("author", {}).get("display_name")
            for authorship in authorships
            if isinstance(authorship, dict) and authorship.get("author")
        ],
        "doi": work.get("doi"),
        "abstract": _decode_abstract(work.get("abstract_inverted_index")),
        "keywords": [concept.get("display_name") for concept in concepts if concept.get("display_name")],
        "impact_area": impact_area,
        "source": "openalex",
        "source_uri": work.get("id"),
        "maturity_level": work.get("type"),
        "ingestion_mode": "remote",
    }


def _fetch_remote(query: str, limit: int) -> list[dict]:
    cursor = "*"
    remaining = max(1, limit)
    records: list[dict] = []
    captured_sample = False

    while remaining > 0:
        page_size = 200 if remaining > 200 else remaining
        params = {
            "search": query,
            "per_page": page_size,
            "cursor": cursor,
            "select": "id,display_name,title,publication_year,doi,authorships,concepts,abstract_inverted_index,type",
        }
        payload = request_json("openalex", OPENALEX_URL, params=params, headers={"Accept": "application/json"})
        if not captured_sample:
            write_sample("openalex", payload)
            captured_sample = True

        page_items = payload.get("results") or []
        if not isinstance(page_items, list) or not page_items:
            break

        for item in page_items:
            if not isinstance(item, dict):
                continue
            records.append(_map_remote_work(item))

        remaining = limit - len(records)
        next_cursor = (payload.get("meta") or {}).get("next_cursor")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor

    deduped = unique_by(records, "id", "doi", "title")
    return deduped[:limit]


def harvest_openalex(query: str = "information science", per_page: int = 20, force_refresh: bool = False) -> list[dict]:
    if should_use_cache_first() and not force_refresh:
        cached = load_cache("openalex", limit=per_page)
        if cached:
            return cached

    try:
        remote = _fetch_remote(query=query, limit=per_page)
        if remote:
            write_cache("openalex", remote, origin="remote")
            return remote
    except Exception as exc:
        logger.warning("OpenAlex API unavailable, using cache/fallback: %s", exc)

    stale_cache = load_cache("openalex", limit=per_page, allow_stale=True)
    if stale_cache:
        return stale_cache
    return _fallback_records(per_page)


if __name__ == "__main__":
    docs = harvest_openalex()
    print("Documentos coletados:", len(docs))
