from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from src.ontology.ontology_mapper import (
    ensure_deia_annotation,
    infer_lgpd_legal_basis,
    normalize_impact_labels,
)

DEFAULT_LICENSE = "https://creativecommons.org/licenses/by/4.0/"
DEFAULT_ACCESS_RIGHTS = "aberto"
DEFAULT_IMPACT = ["Ciencia da Informacao"]


def _slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def _mint_dark_id(source_id: Optional[str], title: str) -> str:
    base = source_id or _slugify(title) or uuid4().hex[:8]
    return f"ark:/13030/savits-{base}"


def _coerce_year(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_authors(raw_authors: Any) -> List[Dict[str, Optional[str]]]:
    authors = []
    if not raw_authors:
        return authors
    for raw in raw_authors:
        if isinstance(raw, dict):
            name = raw.get("name") or raw.get("nome") or ""
            orcid = raw.get("orcid")
            affiliation = raw.get("affiliation") or raw.get("afiliacao")
        else:
            name = str(raw)
            orcid = None
            affiliation = None
        authors.append(
            {
                "name": name.strip(),
                "orcid": _sanitize_orcid(orcid),
                "affiliation": affiliation.strip() if isinstance(affiliation, str) else affiliation,
            }
        )
    return authors


def _sanitize_orcid(orcid: Optional[str]) -> Optional[str]:
    if not orcid:
        return None
    digits = re.sub(r"[^0-9Xx]", "", orcid)
    if len(digits) != 16:
        return None
    parts = [digits[i : i + 4] for i in range(0, 16, 4)]
    return "-".join(parts)


def _normalize_abstract(raw_abstract: Any) -> str:
    if not raw_abstract:
        return ""
    if isinstance(raw_abstract, dict):
        tokens = []
        for word, positions in raw_abstract.items():
            first_position = positions[0] if positions else 0
            tokens.append((first_position, word))
        tokens.sort()
        return " ".join(word for _, word in tokens)
    return str(raw_abstract).strip()


def _ensure_keywords(record: Dict[str, Any]) -> List[str]:
    keywords = record.get("keywords") or record.get("palavras_chave") or []
    if isinstance(keywords, str):
        keywords = [kw.strip() for kw in keywords.split(",")]
    return [kw for kw in (k.strip() for k in keywords) if kw]


def normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Clean and enrich a raw record according to FAIR/CARE guardrails."""
    title = (record.get("title") or record.get("titulo") or "").strip()
    normalized: Dict[str, Any] = {"title": title}
    normalized["id"] = record.get("id") or record.get("identifier") or _slugify(title)
    normalized["ark_id"] = _mint_dark_id(record.get("id"), title)
    normalized["year"] = _coerce_year(record.get("year") or record.get("ano"))
    normalized["authors"] = _normalize_authors(record.get("authors") or record.get("autores"))
    normalized["doi"] = record.get("doi")
    normalized["abstract"] = _normalize_abstract(record.get("abstract") or record.get("resumo"))
    normalized["keywords"] = _ensure_keywords(record)
    normalized["access"] = record.get("acesso") or DEFAULT_ACCESS_RIGHTS
    normalized["license"] = record.get("licenca") or DEFAULT_LICENSE
    normalized["impact_area"] = normalize_impact_labels(record.get("impact_area") or record.get("areas_cnpq") or DEFAULT_IMPACT)
    normalized["maturity_level"] = record.get("maturity_level") or "Pesquisa exploratoria"
    has_personal_data = bool(record.get("dados_pessoais"))
    normalized["lgpd_status"] = "Controlado" if has_personal_data else "Anonimizado"
    normalized["lgpd_legal_basis"] = infer_lgpd_legal_basis(has_personal_data, record.get("base_legal_lgpd"))
    normalized["processed_at"] = datetime.utcnow().isoformat()
    normalized["source"] = record.get("source") or "openalex"
    normalized["source_reference"] = record.get("source_uri") or record.get("fonte") or record.get("url") or normalized["source"]
    normalized["provenance_uri"] = record.get("prov_generated_by") or f"https://pinakes.ibict.br/activity/{normalized['id']}"
    return ensure_deia_annotation(normalized)

