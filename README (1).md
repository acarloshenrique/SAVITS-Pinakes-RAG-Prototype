---
title: SAVITS Pinakes RAG Prototype
emoji: 🔍
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: "1.35.0"
app_file: app.py
pinned: false
license: mit
tags:
  - rag
  - semantic-web
  - rdflib
  - sparql
  - groq
  - llama
  - knowledge-graph
  - fair-data
  - lgpd
  - ibict
  - pinakes
  - brcris
  - python
short_description: RAG semântico com RDFLib + SPARQL + Groq Llama 3.3 70B para o ecossistema Pinakes/BrCris (IBICT)
---

# 🔍 SAVITS Pinakes RAG Prototype

> **PoC de Arquitetura Semântica e RAG** para o ecossistema Pinakes/BrCris (IBICT),  
> com foco em governança de dados **FAIR** e **LGPD**.

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35-red?logo=streamlit)](https://streamlit.io)
[![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-orange)](https://groq.com)
[![RDFLib](https://img.shields.io/badge/RDFLib-7.x-green)](https://rdflib.readthedocs.io)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](LICENSE)

---

## 🧠 O que é este projeto?

Este protótipo implementa um pipeline **RAG (Retrieval-Augmented Generation) semântico** sobre dados de pesquisa científica brasileira, combinando:

| Componente | Tecnologia | Função |
|---|---|---|
| 📊 Grafo de Conhecimento | RDFLib + Turtle (.ttl) | Representa obras, autores, instituições e metadados em triplas RDF |
| 🔎 Recuperação | SPARQL | Consulta semântica no grafo local (sem banco de dados externo) |
| 🤖 Geração | Groq · Llama 3.3 70B | Respostas em linguagem natural com base nos documentos recuperados |
| 🖥️ Interface | Streamlit | Chat interativo com visualização dos documentos recuperados |
| 🏛️ Ontologias | BIBO · DC · FOAF · VIVO · PROV-O | Interoperabilidade semântica e rastreabilidade |
| ✅ Compliance | FAIR · LGPD | Anotações de acesso, licença e base legal diretamente no grafo |

---

## 🚀 Como usar

### 1. Configure a chave da API Groq

Neste Hugging Face Space, a chave é configurada como **Secret**:

```
Configurações do Space → Variables and Secrets → New Secret
Nome: GROQ_API_KEY
Valor: gsk_xxxxxxxxxxxxxxxxxx
```

Obtenha sua chave gratuitamente em [console.groq.com](https://console.groq.com).

### 2. Use o chat

Digite sua pergunta no campo de chat, como por exemplo:

- *"Quais artigos sobre aprendizado de máquina estão disponíveis em acesso aberto?"*
- *"Liste pesquisas sobre biodiversidade publicadas após 2020."*
- *"Quem são os principais autores na área de ciência da informação?"*

O sistema irá:
1. **Recuperar** documentos relevantes via SPARQL no grafo RDF local
2. **Gerar** uma resposta contextualizada com o Llama 3.3 70B via Groq
3. **Exibir** os documentos-fonte na aba "Documentos Recuperados"

---

## 🏗️ Arquitetura

```
raw_data.json
     │
     ▼ semantic_integration.py (RDFLib)
     │
pinakes_graph.ttl  ──► SPARQL Query ──► Contexto
                                             │
                                             ▼
                              Groq API (Llama 3.3 70B)
                                             │
                                             ▼
                              Streamlit Chat Interface
```

### Ontologias utilizadas

- **BIBO** (`http://purl.org/ontology/bibo/`) — tipos de publicação
- **DC / DCTERMS** — metadados bibliográficos
- **FOAF** — pessoas e organizações
- **VIVO** — pesquisadores e afiliações acadêmicas
- **PROV-O** — proveniência dos dados
- **SCHEMA.ORG** — termos complementares
- **PINAKES** (`https://pinakes.ibict.br/ontology/`) — extensão customizada (LGPD, Lattes, ORCID)

---

## 📂 Estrutura do Repositório

```
SAVITS-Pinakes-RAG-Prototype/
├── app.py                      # Interface Streamlit (HF Spaces)
├── pinakes_graph.ttl           # Grafo RDF gerado (versionado)
├── requirements.txt            # Dependências Python
├── README.md                   # Este arquivo
├── data/
│   └── raw_data.json           # Dados brutos de entrada
└── src/
    ├── __init__.py
    └── semantic_integration.py # Geração do grafo TTL
```

---

## ⚙️ Rodando Localmente

```bash
# 1. Clone o repositório
git clone https://github.com/acarloshenrique/SAVITS-Pinakes-RAG-Prototype.git
cd SAVITS-Pinakes-RAG-Prototype

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Gere o grafo RDF a partir dos dados brutos
python src/semantic_integration.py --input data/raw_data.json --output pinakes_graph.ttl

# 4. Configure a API Key (local)
export GROQ_API_KEY="gsk_sua_chave_aqui"

# 5. Execute o app
streamlit run app.py
```

---

## 🔐 Privacidade e Conformidade

Este protótipo foi desenvolvido com foco em **governança de dados**:

- **FAIR**: cada recurso possui URI estável, metadados ricos e links entre entidades
- **LGPD**: o grafo anota se uma obra contém dados pessoais (`pinakes:contemDadosPessoais`) e a base legal correspondente
- **PROV-O**: toda tripla gerada é rastreável à sua atividade de geração no grafo
- **Acesso**: o campo `dcterms:accessRights` registra o nível de acesso (aberto, restrito, embargado)

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Abra uma *issue* ou envie um *pull request* no [GitHub](https://github.com/acarloshenrique/SAVITS-Pinakes-RAG-Prototype).

---

## 📜 Licença

MIT © [acarloshenrique](https://github.com/acarloshenrique)

---

*Desenvolvido como PoC para o ecossistema [Pinakes](https://pinakes.ibict.br) / [BrCris](https://brcris.ibict.br) do [IBICT](https://www.ibict.br).*
