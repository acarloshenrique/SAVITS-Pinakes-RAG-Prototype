from __future__ import annotations

import os
from typing import Any, Dict, List

import requests

from .local_dataset import extract_authors, load_sample_works

BRCRIS_API_URL = os.getenv("BRCRIS_API_URL", "https://brcris.ibict.br/api/works")
BRCRIS_API_TOKEN = os.getenv("BRCRIS_API_TOKEN")


def _fetch_remote_payload(limit: int | None) -> List[Dict[str, Any]]:
    """Fetch data from the BrCris API."""
    headers = {"Accept": "application/json"}
    if BRCRIS_API_TOKEN:
        headers["Authorization"] = f"Bearer {BRCRIS_API_TOKEN}"
    params = {"limit": limit or 20}
    response = requests.get(BRCRIS_API_URL, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    return payload.get("results") or payload.get("works") or payload


def harvest_brcris(limit: int | None = None, use_remote: bool | None = None) -> List[Dict[str, Any]]:
    """Harvest BrCris metadata, with HTTP fallback to the bundled dataset."""
    use_remote = use_remote if use_remote is not None else os.getenv("SAVITS_USE_REMOTE_SOURCES") == "1"
    records: List[Dict[str, Any]] = []

    if use_remote:
        try:
            for work in _fetch_remote_payload(limit):
                records.append(
                    {
                        "id": work.get("id") or work.get("identifier"),
                        "title": work.get("title"),
                        "year": work.get("year"),
                        "authors": [a.get("name") for a in work.get("authors", []) if isinstance(a, dict)],
                        "doi": work.get("doi"),
                        "abstract": work.get("abstract"),
                        "keywords": work.get("keywords"),
                        "acesso": work.get("access"),
                        "licenca": work.get("license"),
                        "impact_area": work.get("areas_cnpq"),
                        "maturity_level": work.get("maturity_level") or "Avaliado (BrCris)",
                        "source": "brcris",
                    }
                )
        except Exception as exc:
            print(f"[INGEST] Falha BrCris remoto ({exc}). Usando dataset local.")

    if not records:
        works = [w for w in load_sample_works() if (w.get("tipo") or "").startswith("artigo")]
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
                    "maturity_level": "Avaliado (BrCris)",
                    "source": "brcris",
                }
            )

    if limit:
        return records[:limit]
    return records


if __name__ == "__main__":
    docs = harvest_brcris(use_remote=True)
    print("BrCris registros simulados:", len(docs))
