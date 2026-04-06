from __future__ import annotations

import os
from typing import Dict, List

import requests

from .local_dataset import extract_authors, load_sample_works

THESIS_TYPES = {"tese", "dissertacao", "dissertação"}
BDTD_API_URL = os.getenv("BDTD_API_URL", "https://bdtd.ibict.br/api/theses")


def _fetch_remote(limit: int | None) -> List[Dict[str, str]]:
    response = requests.get(BDTD_API_URL, params={"limit": limit or 20}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    return payload.get("results") or payload


def harvest_bdtd(limit: int | None = None, use_remote: bool | None = None) -> List[Dict[str, str]]:
    """Harvest thesis/dissertation metadata inspired by the BDTD portal."""
    use_remote = use_remote if use_remote is not None else os.getenv("SAVITS_USE_REMOTE_SOURCES") == "1"
    records: List[Dict[str, str]] = []

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
                        "acesso": work.get("access"),
                        "licenca": work.get("license"),
                        "impact_area": work.get("areas_cnpq"),
                        "maturity_level": "BDTD",
                        "source": "bdtd",
                    }
                )
        except Exception as exc:
            print(f"[INGEST] Falha BDTD remota ({exc}). Usando dataset local.")

    if not records:
        works = [w for w in load_sample_works() if (w.get("tipo") or "").lower() in THESIS_TYPES]
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
                    "maturity_level": "BDTD",
                    "source": "bdtd",
                }
            )

    if limit:
        return records[:limit]
    return records


if __name__ == "__main__":
    docs = harvest_bdtd(use_remote=True)
    print("BDTD registros simulados:", len(docs))
