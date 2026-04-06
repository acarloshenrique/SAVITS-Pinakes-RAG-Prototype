from __future__ import annotations

import os
from typing import Any, Dict, List

import requests

from .local_dataset import extract_authors, load_sample_works

OASISBR_API_URL = os.getenv("OASISBR_API_URL", "https://oasisbr.ibict.br/api/works")


def _fetch_remote(limit: int | None) -> List[Dict[str, Any]]:
    response = requests.get(OASISBR_API_URL, params={"limit": limit or 20}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    return payload.get("results") or payload


def harvest_oasisbr(limit: int | None = None, use_remote: bool | None = None) -> List[Dict[str, Any]]:
    """Harvest Oasisbr works, preferring the remote API when enabled."""
    use_remote = use_remote if use_remote is not None else os.getenv("SAVITS_USE_REMOTE_SOURCES") == "1"
    records: List[Dict[str, Any]] = []

    if use_remote:
        try:
            for work in _fetch_remote(limit):
                records.append(
                    {
                        "id": work.get("id"),
                        "title": work.get("title"),
                        "year": work.get("year"),
                        "authors": [a.get("name") for a in work.get("authors", []) if isinstance(a, dict)],
                        "doi": work.get("doi"),
                        "abstract": work.get("abstract"),
                        "keywords": work.get("keywords"),
                        "acesso": work.get("access") or "aberto",
                        "licenca": work.get("license"),
                        "impact_area": work.get("areas_cnpq"),
                        "maturity_level": work.get("maturity_level") or "Oasisbr",
                        "source": "oasisbr",
                    }
                )
        except Exception as exc:
            print(f"[INGEST] Falha Oasisbr remoto ({exc}). Usando dataset local.")

    if not records:
        works = [w for w in load_sample_works() if (w.get("acesso") or "").lower() == "aberto"]
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
                    "maturity_level": "Oasisbr",
                    "source": "oasisbr",
                }
            )

    if limit:
        return records[:limit]
    return records


if __name__ == "__main__":
    docs = harvest_oasisbr(use_remote=True)
    print("Oasisbr registros simulados:", len(docs))
