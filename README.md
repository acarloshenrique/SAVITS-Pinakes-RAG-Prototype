---
title: SAVITS Pinakes RAG
emoji: 🔎
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: "1.35.0"
python_version: "3.10"
app_file: app.py
pinned: false
license: mit
short_description: Semantic GraphRAG for Pinakes research data
---

# SAVITS Pinakes RAG

Semantic GraphRAG prototype for the Pinakes / BrCris ecosystem.

## Destaques recentes

- **Governança FAIR/CARE integrada**: o app Streamlit agora executa validações automáticas (Findable, Accessible, Interoperable, Reusable + CARE) via `src/governance/fair_validator.py`, exibindo alertas diretamente na aba “Governança” e permitindo que a equipe corrija metadados antes das respostas RAG.
- **Curadoria bibliotecária reforçada**: o pipeline (`src/curation`) normaliza autores, ORCID, licenças, direitos de acesso e gera identificadores dARK para cada obra, alinhado às exigências do edital SAVITS para o perfil de bibliotecário de dados.
- **Grafos enriquecidos**: `src/graph/graph_builder.py` escreve triplas com licenças, LGPD, impactos sociais e afiliações FOAF/Schema.org, garantindo interoperabilidade com Pinakes/BrCris.

## Fluxo de trabalho recomendado

1. `python build_graph.py` – executa o pipeline de ingestão/curadoria (OpenAlex → metadados FAIR/CARE) e gera `pinakes_graph.ttl` enriquecido.
2. `streamlit run app.py` – carrega o grafo, disponibiliza busca SPARQL + Groq e apresenta o painel de governança.
3. Opcional: `python -m src.governance.fair_validator pinakes_graph.ttl` – produz relatório JSON utilizável em CI para comprovar aderência ao edital.

## Próximos passos sugeridos

- Conectar coletores adicionais (BrCris, Oasisbr, BDTD) via `src/ingestion`.
- Completar os módulos `analytics/`, `governance/` e `ontology/` com métricas e validadores específicos de LGPD/DEIA.
