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

Semantic GraphRAG prototype for the Pinakes / BrCris ecosystem with FAIR/CARE/DEIA governance.

## Novidades principais

- **Coletores reais + fallback seguro** (`src/ingestion`)  
  Os conectores de BrCris, Oasisbr, BDTD e OpenAlex agora tentam consumir APIs oficiais (com suporte a `BRCRIS_API_TOKEN`, `OASISBR_API_URL`, etc.) e retrocedem para o dataset curado `data/raw_data.json` quando não houver rede, garantindo demos off-line.
- **Curadoria LGPD/DEIA completa** (`src/curation/metadata_normalizer.py`, `src/ontology/ontology_mapper.py`)  
  Todos os registros recebem `ark:/13030/savits-*`, `DCTERMS.source`, base legal LGPD inferida e tags DEIA automáticas, eliminando os avisos FAIR_FINDABLE/FAIR_REUSABLE.
- **Analytics e governança visuais** (`app.py`, `src/analytics`, `src/governance/provenance_tracker.py`)  
  A aba “Analytics LGPD/DEIA” exibe cobertura de acesso aberto, impacto social, fontes DCTERMS e lacunas DEIA, enquanto a aba de Governança mostra métricas PROV/DCTERMS e alertas detalhados.
- **Pipeline automatizado** (`build_all.cmd`, `.github/workflows/ci.yml`)  
  O comando único executa ingestão → grafo → validação FAIR → `pytest`, com `PYTHONIOENCODING` forçado para evitar problemas de encoding e com execução contínua no GitHub Actions (Node 24-ready).
- **Perguntas de avaliação prontas** (`docs/chat_eval_prompts.md`)  
  Roteiro oficial para a banca testar o chat e comprovar aderência ao edital SAVITS.

## Como executar localmente

1. **Gerar grafos e validar FAIR/CARE**  
   - Windows: `build_all.cmd` (configura `PYTHONIOENCODING`, recria TTLs, executa validações e testes).  
   - Multi-plataforma:  
     ```bash
     export PYTHONIOENCODING=utf-8
     python build_graph.py
     python -m src.governance.fair_validator pinakes_graph.ttl > reports/governance_report.json
     pytest
     ```
2. **Validar integrações das fontes e atualizar cache local**  
   ```bash
   python validate_sources.py
   ```
   - Gera `reports/source_validation_report.json` com status por fonte.
   - Salva amostras reais de payload em `reports/ingestion_samples/*.json`.
   - Persiste cache de coleta em `data/cache/ingestion/*.json` para reduzir dependência de rede.
   - Variáveis úteis:
     - `INGESTION_USE_CACHE_FIRST=1` (padrão: usar cache antes da rede)
     - `INGESTION_CACHE_TTL_HOURS=24`
     - `INGESTION_RETRIES=3`
     - `INGESTION_TIMEOUT_SECONDS=30`
     - `BRCRIS_API_URL` / `BRCRIS_API_TOKEN` para endpoint autenticado do BrCris
3. **Executar a interface Streamlit**  
   ```bash
   streamlit run app.py
   ```
4. **Reexecutar apenas o grafo sem Streamlit**  
   ```bash
   python src/semantic_integration.py --input data/raw_data.json --output pinakes_graph.ttl
   ```

## Testes

- Suite mínima em `tests/` cobrindo curadoria LGPD/DEIA e indicadores de governança (`pytest`).
- Relatório FAIR/CARE automatizado em `reports/governance_report.json`.

## Deploy contínuo

1. **GitHub**  
   - Configure o remote `origin` conforme o repo [`acarloshenrique/SAVITS-Pinakes-RAG-Prototype`](https://github.com/acarloshenrique/SAVITS-Pinakes-RAG-Prototype).  
   - `git add . && git commit -m "feat: governance analytics"`  
   - `git push origin main` (aciona o workflow `ci.yml`).
2. **Hugging Face Spaces**  
   - `huggingface-cli login`  
   - `huggingface-cli repo create acarloshenrique/SAVITS-Pinakes-RAG --type space --sdk streamlit` (uma vez).  
   - `huggingface-cli upload ./app.py` e dependências ou `git push` para o repo Space.  
   - Configure `GROQ_API_KEY` como Secret no Space.

## Roteiro de perguntas para a banca

Consulte `docs/chat_eval_prompts.md` para um conjunto de 7 prompts que cobrem FAIR, LGPD, impacto social e DEIA.
