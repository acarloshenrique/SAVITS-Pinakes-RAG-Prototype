from __future__ import annotations

import re
from typing import Iterable, List, Sequence

# Canonical LGPD legal bases referenced in the SAVITS edital
LGPD_BASES = {
    "consentimento": "Consentimento (Art. 7o, I)",
    "interesse publico": "Interesse publico em pesquisa (Art. 7o, III)",
    "politicas publicas": "Politicas publicas (Art. 7o, III)",
    "contrato": "Execucao de contrato (Art. 7o, V)",
    "anonimizado": "Dados anonimizados (Art. 12)",
}

# Impact taxonomy (Pinakes / CNPq mapping)
IMPACT_TAXONOMY = {
    "Cidadania e Informacao": {"ciencia da informacao", "dados abertos", "transparencia"},
    "Saude Publica": {"saude", "epidemiologia", "surtos"},
    "Educacao e Cultura": {"educacao", "inclusao digital", "alfabetizacao"},
    "Meio Ambiente": {"amazonia", "biodiversidade", "mudancas climaticas"},
    "Agricultura Familiar": {"agricultura familiar", "semiarido", "seguranca alimentar"},
}

# DEIA glossary to flag whether a record addresses diversity, equity, inclusion, accessibility
DEIA_GLOSSARY = {
    "Diversidade": {"mulheres", "indigena", "quilombola", "lgbt", "raca", "equidade"},
    "Equidade": {"justica social", "redistribuicao", "igualdade", "vulneravel"},
    "Inclusao": {"acessibilidade", "inclusao", "participacao social"},
    "Acessibilidade": {"acessivel", "libras", "assistiva", "barreiras"},
}


def _tokenize(values: Iterable[str]) -> str:
    return " ".join(value.lower() for value in values if value).strip()


def normalize_impact_labels(raw: Sequence[str] | str | None) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        items = [part.strip() for part in raw.split(",")]
    else:
        items = [str(item).strip() for item in raw]

    normalized: List[str] = []
    for item in items:
        if not item:
            continue
        needle = item.lower()
        match = next(
            (canonical for canonical, synonyms in IMPACT_TAXONOMY.items() if needle in synonyms or needle == canonical.lower()),
            None,
        )
        normalized.append(match or item)
    return sorted(dict.fromkeys(normalized))


def infer_lgpd_legal_basis(has_personal_data: bool, declared_basis: str | None) -> str:
    if declared_basis:
        normalized = re.sub(r"\s+", " ", declared_basis).strip().lower()
        return LGPD_BASES.get(normalized, declared_basis)
    if not has_personal_data:
        return LGPD_BASES["anonimizado"]
    return LGPD_BASES["consentimento"]


def derive_deia_tags(record: dict) -> List[str]:
    impact_values = record.get("impact_area")
    if isinstance(impact_values, str):
        impact_tokens = [impact_values]
    elif isinstance(impact_values, Iterable):
        impact_tokens = [str(value) for value in impact_values]
    else:
        impact_tokens = []

    haystack = _tokenize(
        [
            record.get("title", ""),
            record.get("abstract", ""),
            " ".join(record.get("keywords", [])),
            " ".join(impact_tokens),
        ]
    )
    tags = []
    for pillar, keywords in DEIA_GLOSSARY.items():
        if any(term in haystack for term in keywords):
            tags.append(pillar)
    return sorted(dict.fromkeys(tags))


def ensure_deia_annotation(record: dict) -> dict:
    record = dict(record)
    record["deia_tags"] = record.get("deia_tags") or derive_deia_tags(record)
    return record

