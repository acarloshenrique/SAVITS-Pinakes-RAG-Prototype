from __future__ import annotations

from typing import Any, Dict, List

from .local_dataset import extract_authors, load_sample_works


def harvest_oasisbr(limit: int | None = None) -> List[Dict[str, Any]]:
    """Harvest open-access works, emulating the Oasisbr API contract."""
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
                "maturity_level": "Oasisbr",
                "source": "oasisbr",
            }
        )
    if limit:
        return records[:limit]
    return records


if __name__ == "__main__":
    docs = harvest_oasisbr()
    print("Oasisbr registros simulados:", len(docs))
