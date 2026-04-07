from __future__ import annotations

import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Sequence, Tuple

from src.ingestion.bdtd_harvester import harvest_bdtd
from src.ingestion.brcris_harvester import harvest_brcris
from src.ingestion.oasisbr_harvester import harvest_oasisbr
from src.ingestion.openalex_harvester import harvest_openalex

STOPWORDS_PT = {
    "como", "onde", "quando", "qual", "quais", "sobre", "para", "com", "sem", "dos",
    "das", "de", "do", "da", "e", "ou", "em", "um", "uma", "os", "as", "no", "na",
    "nos", "nas", "por", "que", "se", "ao", "aos", "a", "o", "tratam", "trata",
}
PRIORITY_TERMS = {
    "fair", "care", "lgpd", "deia", "governanca", "proveniencia",
    "dados", "pesquisa", "ciencia", "informacao", "ontologia", "interoperabilidade",
}
PRIMARY_REST_SOURCES = ("openalex", "oasisbr", "bdtd")
SECONDARY_API_SOURCES = ("brcris",)
API_SOURCE_NAMES = PRIMARY_REST_SOURCES + SECONDARY_API_SOURCES


def normalize_term(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    return normalized.lower().strip()


def query_tokens(query: str) -> List[str]:
    terms: List[str] = []
    seen = set()
    for raw in re.split(r"[^\w]+", query.strip()):
        if not raw:
            continue
        token = normalize_term(raw)
        if len(token) < 4 or token in STOPWORDS_PT:
            continue
        if token in seen:
            continue
        seen.add(token)
        terms.append(token)

    priority = [term for term in terms if term in PRIORITY_TERMS]
    regular = [term for term in terms if term not in PRIORITY_TERMS]
    return priority + regular


def result_score(result: Dict, tokens: Sequence[str]) -> Tuple[int, int]:
    text = " ".join(
        [
            str(result.get("titulo", "")),
            str(result.get("resumo", "")),
            str(result.get("keywords", "")),
            str(result.get("acesso", "")),
            str(result.get("tipo", "")),
        ]
    )
    normalized = normalize_term(text)
    token_hits = sum(1 for token in tokens if token in normalized)
    year_match = re.search(r"\d{4}", str(result.get("ano", "")))
    year_value = int(year_match.group(0)) if year_match else 0
    return token_hits, year_value


def _as_text_list(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items: List[str] = []
        for item in value:
            if isinstance(item, dict):
                items.extend(_as_text_list(item.get("name") or item.get("nome")))
            else:
                text = str(item).strip()
                if text:
                    items.append(text)
        return items
    text = str(value).strip()
    return [text] if text else []


def normalize_api_record(source: str, record: Dict) -> Dict | None:
    title = str(record.get("title") or record.get("titulo") or "").strip()
    if not title:
        return None

    raw_authors = record.get("authors") or record.get("autores")
    authors = ", ".join(_as_text_list(raw_authors)) or "Desconhecido"
    raw_keywords = record.get("keywords") or record.get("palavras_chave")
    keywords = ", ".join(_as_text_list(raw_keywords))

    uri = record.get("source_uri") or record.get("doi") or record.get("id") or f"{source}:{title}"
    uri_text = str(uri).strip()
    if uri_text and not uri_text.startswith("http"):
        uri_text = f"{source}:{uri_text}"

    return {
        "uri": uri_text or f"{source}:{title}",
        "titulo": title,
        "resumo": str(record.get("abstract") or record.get("resumo") or ""),
        "ano": str(record.get("year") or record.get("ano") or "s/d"),
        "tipo": str(record.get("maturity_level") or record.get("tipo") or "Document"),
        "autores": authors,
        "keywords": keywords,
        "acesso": str(record.get("acesso") or record.get("access") or "-"),
        "retrieval_channel": "api",
        "retrieval_source": source,
        "retrieval_mode": str(record.get("ingestion_mode") or "remote"),
    }


def _retrieve_api_source(source: str, user_query: str, limit: int) -> List[Dict]:
    try:
        if source == "openalex":
            records = harvest_openalex(query=user_query, per_page=limit, force_refresh=True)
        elif source == "brcris":
            records = harvest_brcris(limit=limit, force_refresh=True, query=user_query)
        elif source == "oasisbr":
            records = harvest_oasisbr(limit=limit, force_refresh=True, query=user_query)
        elif source == "bdtd":
            records = harvest_bdtd(limit=limit, force_refresh=True, query=user_query)
        else:
            return []
    except Exception:
        return []

    out: List[Dict] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        normalized = normalize_api_record(source, record)
        if normalized:
            out.append(normalized)
    return out


def retrieve_api_results(user_query: str, top_k: int) -> List[Dict]:
    tokens = query_tokens(user_query)
    api_query = " ".join(tokens[:6]) if tokens else user_query
    per_source_limit = max(8, top_k * 3)
    results: List[Dict] = []

    with ThreadPoolExecutor(max_workers=len(PRIMARY_REST_SOURCES)) as executor:
        future_map = {
            executor.submit(_retrieve_api_source, source, api_query, per_source_limit): source
            for source in PRIMARY_REST_SOURCES
        }
        for future in as_completed(future_map):
            try:
                source_results = future.result()
            except Exception:
                source_results = []
            results.extend(source_results)

    if len(results) < top_k * 2:
        for source in SECONDARY_API_SOURCES:
            results.extend(_retrieve_api_source(source, api_query, max(3, top_k)))

    unique: List[Dict] = []
    seen_uris = set()
    seen_titles = set()
    for item in results:
        uri_key = str(item.get("uri") or "").strip()
        title_key = normalize_term(item.get("titulo", ""))
        if (uri_key and uri_key in seen_uris) or (title_key and title_key in seen_titles):
            continue
        if uri_key:
            seen_uris.add(uri_key)
        if title_key:
            seen_titles.add(title_key)
        unique.append(item)

    unique.sort(key=lambda item: result_score(item, tokens), reverse=True)
    return unique


def _append_unique_result(
    sink: List[Dict],
    seen_uris: set[str],
    seen_titles: set[str],
    item: Dict,
) -> bool:
    uri_key = str(item.get("uri") or "").strip()
    title_key = normalize_term(item.get("titulo", ""))
    if (uri_key and uri_key in seen_uris) or (title_key and title_key in seen_titles):
        return False
    if uri_key:
        seen_uris.add(uri_key)
    if title_key:
        seen_titles.add(title_key)
    sink.append(item)
    return True


def merge_retrieval_results(
    user_query: str,
    sparql_results: List[Dict],
    api_results: List[Dict],
    top_k: int,
) -> List[Dict]:
    tokens = query_tokens(user_query)
    ranked_sparql = sorted(sparql_results, key=lambda item: result_score(item, tokens), reverse=True)
    ranked_api = sorted(api_results, key=lambda item: result_score(item, tokens), reverse=True)

    final: List[Dict] = []
    seen_uris: set[str] = set()
    seen_titles: set[str] = set()
    api_quota = min(len(ranked_api), max(1, top_k // 2)) if ranked_api else 0

    if api_quota:
        source_heads = {source: None for source in API_SOURCE_NAMES}
        for item in ranked_api:
            source = str(item.get("retrieval_source") or "")
            if source in source_heads and source_heads[source] is None:
                source_heads[source] = item
        for source in API_SOURCE_NAMES:
            if len(final) >= api_quota:
                break
            head = source_heads.get(source)
            if head is not None:
                _append_unique_result(final, seen_uris, seen_titles, head)

    if len(final) < api_quota:
        for item in ranked_api:
            if len(final) >= api_quota:
                break
            _append_unique_result(final, seen_uris, seen_titles, item)

    for item in ranked_sparql:
        if len(final) >= top_k:
            break
        _append_unique_result(final, seen_uris, seen_titles, item)

    for item in ranked_api:
        if len(final) >= top_k:
            break
        _append_unique_result(final, seen_uris, seen_titles, item)

    return final[:top_k]


def retrieval_diagnostics(results: List[Dict]) -> Dict[str, object]:
    remote_api = 0
    fallback_api = 0
    per_source: Dict[str, Dict[str, int]] = {}
    for row in results:
        if row.get("retrieval_channel") != "api":
            continue
        source = str(row.get("retrieval_source") or "api")
        mode = str(row.get("retrieval_mode") or "remote")
        per_source.setdefault(source, {"remote": 0, "cache": 0, "fallback": 0})
        if mode not in per_source[source]:
            per_source[source][mode] = 0
        per_source[source][mode] += 1
        if mode == "fallback":
            fallback_api += 1
        else:
            remote_api += 1

    return {
        "total": len(results),
        "remote_api_docs": remote_api,
        "fallback_api_docs": fallback_api,
        "per_source": per_source,
    }
