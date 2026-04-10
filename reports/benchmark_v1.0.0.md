# Benchmark v1.0.0

## Summary

- Generated at: `2026-04-10T01:46:08.918927+00:00`
- Offline documents: **5**
- Enriched graph triples: **155**
- Offline build time: **4.37 ms**
- Retrieval Top-1 accuracy: **100%**
- Retrieval Top-3 accuracy: **100%**
- Median retrieval latency: **0.054 ms**
- P95 retrieval latency: **0.098 ms**

## Source Mix

- `brcris`: 3 documents
- `bdtd`: 1 documents
- `openalex-fallback`: 1 documents

## Governance Coverage

- `FAIR_FINDABLE`: 100%
- `FAIR_ACCESSIBLE`: 100%
- `FAIR_INTEROPERABLE`: 100%
- `FAIR_REUSABLE`: 100%
- `CARE_COLLECTIVE`: 100%
- `CARE_AUTHORITY`: 100%
- `CARE_RESPONSIBILITY`: 100%

## Retrieval Cases

| Case | Expected | Top result | Top-3 | Latency (ms) |
| --- | --- | --- | --- | ---: |
| `fair-lgpd` | Governança de Dados de Pesquisa no Brasil: Desafios FAIR e LGPD | Governança de Dados de Pesquisa no Brasil: Desafios FAIR e LGPD | yes | 0.098 |
| `agricultura-familiar` | Impacto das Mudanças Climáticas na Agricultura Familiar do Semiárido Nordestino | Impacto das Mudanças Climáticas na Agricultura Familiar do Semiárido Nordestino | yes | 0.058 |
| `amazonia-biodiversidade` | Aplicação de Redes Neurais na Análise de Biodiversidade Amazônica | Aplicação de Redes Neurais na Análise de Biodiversidade Amazônica | yes | 0.054 |
| `sparql-rag` | Recuperação de Informação Semântica com SPARQL em Bases de Dados Científicas | Recuperação de Informação Semântica com SPARQL em Bases de Dados Científicas | yes | 0.045 |
| `interoperabilidade` | Interoperabilidade Semântica entre Repositórios de Dados de Pesquisa: Um Framework Baseado em Ontologias | Interoperabilidade Semântica entre Repositórios de Dados de Pesquisa: Um Framework Baseado em Ontologias | yes | 0.049 |

## Method

- `python -m src.evaluation.simple_benchmark`
- Offline mode using `run_pipeline(use_remote=False)`
- Retrieval scored over title, abstract, keywords, impact area, and source fields
- FAIR/CARE coverage computed with `src.governance.fair_validator.evaluate_graph`
