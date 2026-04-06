from __future__ import annotations

from typing import List, Dict, Any

from .local_dataset import extract_authors, load_sample_works


def harvest_brcris(limit: int | None = None) -> List[Dict[str, Any]]:
    """Simulate integration with BrCris by leveraging curated sample data."""
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
                "maturity_level": "Avaliado (BrCris)",
                "source": "brcris",
            }
        )
    if limit:
        return records[:limit]
    return records


if __name__ == "__main__":
    docs = harvest_brcris()
    print("BrCris registros simulados:", len(docs))
