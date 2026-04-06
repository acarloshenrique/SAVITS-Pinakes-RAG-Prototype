\---

title: SAVITS Pinakes RAG

emoji: 🔍

colorFrom: blue

colorTo: indigo

sdk: streamlit

sdk\_version: "1.35.0"

python\_version: "3.10"

app\_file: app.py

pinned: false

license: mit

short\_description: Semantic GraphRAG for Pinakes research data

\------

# 🔍 SAVITS Pinakes RAG Prototype

> \\\\\\\*\\\\\\\*PoC de Arquitetura Semântica e RAG\\\\\\\*\\\\\\\* para o ecossistema Pinakes/BrCris (IBICT),  
> com foco em governança de dados \\\\\\\*\\\\\\\*FAIR\\\\\\\*\\\\\\\* e \\\\\\\*\\\\\\\*LGPD\\\\\\\*\\\\\\\*.

[!\[Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[!\[Streamlit](https://img.shields.io/badge/Streamlit-1.35-red?logo=streamlit)](https://streamlit.io)
[!\[Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-orange)](https://groq.com)
[!\[RDFLib](https://img.shields.io/badge/RDFLib-7.x-green)](https://rdflib.readthedocs.io)
[!\[License](https://img.shields.io/badge/License-MIT-lightgrey)](LICENSE)

\---

## 🧠 O que é este projeto?

Este protótipo implementa um pipeline **RAG (Retrieval-Augmented Generation) semântico** sobre dados de pesquisa científica brasileira, combinando:

|Componente|Tecnologia|Função|
|-|-|-|
|📊 Grafo de Conhecimento|RDFLib + Turtle (.ttl)|Representa obras, autores, instituições e metadados em triplas RDF|
|🔎 Recuperação|SPARQL|Consulta semântica no grafo local (sem banco de dados externo)|
|🤖 Geração|Groq · Llama 3.3 70B|Respostas em linguagem natural com base nos documentos recuperados|
|🖥️ Interface|Streamlit|Chat interativo com visualização dos documentos recuperados|
|🏛️ Ontologias|BIBO · DC · FOAF · VIVO · PROV-O|Interoperabilidade semântica e rastreabilidade|
|✅ Compliance|FAIR · LGPD|Anotações de acesso, licença e base legal diretamente no grafo|

\---

## 🚀 Como usar

### 1\. Configure a chave da API Groq

Neste Hugging Face Space, a chave é configurada como **Secret**:

```
Configurações do Space → Variables and Secrets → New Secret
Nome: GROQ\\\\\\\_API\\\\\\\_KEY
Valor: gsk\\\\\\\_xxxxxxxxxxxxxxxxxx
```

Obtenha sua chave gratuitamente em [console.groq.com](https://console.groq.com).

### 2\. Use o chat

Digite sua pergunta no campo de chat, como por exemplo:

* *"Quais artigos sobre aprendizado de máquina estão disponíveis em acesso aberto?"*
* *"Liste pesquisas sobre biodiversidade publicadas após 2020."*
* *"Quem são os principais autores na área de ciência da informação?"*

O sistema irá:

1. **Recuperar** documentos relevantes via SPARQL no grafo RDF local
2. **Gerar** uma resposta contextualizada com o Llama 3.3 70B via Groq
3. **Exibir** os documentos-fonte na aba "Documentos Recuperados"

\---

## 🏗️ Arquitetura

```
raw\\\\\\\_data.json
     │
     ▼ semantic\\\\\\\_integration.py (RDFLib)
     │
pinakes\\\\\\\_graph.ttl  ──► SPARQL Query ──► Contexto
                                             │
                                             ▼
                              Groq API (Llama 3.3 70B)
                                             │
                                             ▼
                              Streamlit Chat Interface
```

### Ontologias utilizadas

* **BIBO** (`http://purl.org/ontology/bibo/`) — tipos de publicação
* **DC / DCTERMS** — metadados bibliográficos
* **FOAF** — pessoas e organizações
* **VIVO** — pesquisadores e afiliações acadêmicas
* **PROV-O** — proveniência dos dados
* **SCHEMA.ORG** — termos complementares
* **PINAKES** (`https://pinakes.ibict.br/ontology/`) — extensão customizada (LGPD, Lattes, ORCID)

\---

## 📂 Estrutura do Repositório

```
SAVITS-Pinakes-RAG-Prototype/
├── app.py                      # Interface Streamlit (HF Spaces)
├── pinakes\\\\\\\_graph.ttl           # Grafo RDF gerado (versionado)
├── requirements.txt            # Dependências Python
├── README.md                   # Este arquivo
├── data/
│   └── raw\\\\\\\_data.json           # Dados brutos de entrada
└── src/
    ├── \\\\\\\_\\\\\\\_init\\\\\\\_\\\\\\\_.py
    └── semantic\\\\\\\_integration.py # Geração do grafo TTL
```

\---

## ⚙️ Rodando Localmente

```bash
# 1. Clone o repositório
git clone https://github.com/acarloshenrique/SAVITS-Pinakes-RAG-Prototype.git
cd SAVITS-Pinakes-RAG-Prototype

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Gere o grafo RDF a partir dos dados brutos
python src/semantic\\\\\\\_integration.py --input data/raw\\\\\\\_data.json --output pinakes\\\\\\\_graph.ttl

# 4. Configure a API Key (local)
export GROQ\\\\\\\_API\\\\\\\_KEY="gsk\\\\\\\_sua\\\\\\\_chave\\\\\\\_aqui"

# 5. Execute o app
streamlit run app.py
```

\---

## 🔐 Privacidade e Conformidade

Este protótipo foi desenvolvido com foco em **governança de dados**:

* **FAIR**: cada recurso possui URI estável, metadados ricos e links entre entidades
* **LGPD**: o grafo anota se uma obra contém dados pessoais (`pinakes:contemDadosPessoais`) e a base legal correspondente
* **PROV-O**: toda tripla gerada é rastreável à sua atividade de geração no grafo
* **Acesso**: o campo `dcterms:accessRights` registra o nível de acesso (aberto, restrito, embargado)

\---

## 🤝 Contribuindo

Contribuições são bem-vindas! Abra uma *issue* ou envie um *pull request* no [GitHub](https://github.com/acarloshenrique/SAVITS-Pinakes-RAG-Prototype).

\---

## 📜 Licença

MIT © [acarloshenrique](https://github.com/acarloshenrique)

\---

*Desenvolvido como PoC para o ecossistema* [*Pinakes*](https://pinakes.ibict.br) */* [*BrCris*](https://brcris.ibict.br) *do* [*IBICT*](https://www.ibict.br)*.*

