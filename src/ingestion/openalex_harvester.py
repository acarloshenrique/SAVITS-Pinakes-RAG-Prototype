import logging

import requests

from .local_dataset import load_sample_works

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
        }
        for work in works
    ]


def harvest_openalex(query: str = "information science", per_page: int = 20):
    params = {"search": query, "per_page": per_page}
    try:
        response = requests.get(OPENALEX_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        logger.warning("OpenAlex API unavailable, using fallback dataset: %s", exc)
        return _fallback_records(per_page)

    results = []

    for work in data.get("results", []):
        impact_area = [concept["display_name"] for concept in work.get("concepts", [])[:3] if concept.get("display_name")]
        record = {
            "id": work.get("id"),
            "title": work.get("title"),
            "year": work.get("publication_year"),
            "authors": [a["author"]["display_name"] for a in work.get("authorships", []) if a.get("author")],
            "doi": work.get("doi"),
            "abstract": work.get("abstract_inverted_index"),
            "keywords": [
                concept["display_name"]
                for concept in work.get("concepts", [])
                if concept.get("display_name")
            ],
            "impact_area": impact_area,
            "source": "openalex",
            "source_uri": work.get("id"),
            "maturity_level": work.get("type"),
        }

        results.append(record)

    return results


if __name__ == "__main__":
    docs = harvest_openalex()
    print("Documentos coletados:", len(docs))
