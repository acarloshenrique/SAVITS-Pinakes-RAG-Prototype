"""
app.py — SAVITS Pinakes RAG Prototype
Sistema RAG Semântico: RDFLib + SPARQL + Groq (Llama 3.3 70B) + Streamlit
Deploy: Hugging Face Spaces (GROQ_API_KEY configurada como Secret)
"""

import os
import re
import time
import logging
from pathlib import Path

import streamlit as st
from rdflib import Graph
from groq import Groq

# ─── Configuração de logging ──────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Constantes ───────────────────────────────────────────────────────────────
TTL_PATH        = Path("pinakes_graph.ttl")
GROQ_MODEL      = "llama-3.3-70b-versatile"
MAX_TOKENS      = 1024
TEMPERATURE     = 0.3
TOP_K_RESULTS   = 5
APP_TITLE       = "🔍 SAVITS Pinakes RAG"
APP_SUBTITLE    = "Sistema RAG Semântico para o ecossistema Pinakes/BrCris (IBICT)"


# ─── Carregamento do grafo RDF ─────────────────────────────────────────────────
@st.cache_resource(show_spinner="Carregando grafo RDF…")
def load_graph() -> Graph:
    """Carrega o grafo Turtle em cache na sessão do Streamlit."""
    if not TTL_PATH.exists():
        st.error(
            f"Arquivo `{TTL_PATH}` não encontrado. "
            "Execute `python src/semantic_integration.py` para gerá-lo."
        )
        st.stop()
    g = Graph()
    g.parse(str(TTL_PATH), format="turtle")
    logger.info(f"Grafo carregado: {len(g)} triplas")
    return g


# ─── SPARQL: recuperação semântica ────────────────────────────────────────────
SPARQL_TEMPLATE = """
PREFIX dc:      <http://purl.org/dc/elements/1.1/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX bibo:    <http://purl.org/ontology/bibo/>
PREFIX foaf:    <http://xmlns.com/foaf/0.1/>
PREFIX pinakes: <https://pinakes.ibict.br/ontology/>
PREFIX schema:  <https://schema.org/>
PREFIX rdfs:    <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?work ?titulo ?resumo ?ano ?tipo ?autores ?keywords ?acesso
WHERE {{
  ?work dc:title ?titulo .
  OPTIONAL {{ ?work dcterms:abstract ?resumo . }}
  OPTIONAL {{ ?work dc:date         ?ano . }}
  OPTIONAL {{ ?work a               ?tipo . FILTER(?tipo != <http://www.w3.org/2002/07/owl#Thing>) }}
  OPTIONAL {{ ?work dc:creator      ?autor .
              ?autor foaf:name      ?autores . }}
  OPTIONAL {{ ?work schema:keywords ?keywords . }}
  OPTIONAL {{ ?work dcterms:accessRights ?acesso . }}
  OPTIONAL {{ ?work pinakes:ragText ?ragText . }}

  FILTER(
    CONTAINS(LCASE(STR(?titulo)), LCASE("{query}")) ||
    CONTAINS(LCASE(STR(?resumo)), LCASE("{query}")) ||
    CONTAINS(LCASE(STR(?keywords)), LCASE("{query}")) ||
    CONTAINS(LCASE(STR(?ragText)), LCASE("{query}"))
  )
}}
LIMIT {limit}
"""

def sparql_retrieve(g: Graph, query: str, top_k: int = TOP_K_RESULTS) -> list[dict]:
    """Executa busca SPARQL no grafo local e retorna lista de resultados."""
    # Tokenização básica: busca por cada palavra com ≥ 4 chars
    tokens = [t for t in re.split(r"\s+", query.strip()) if len(t) >= 4]
    if not tokens:
        tokens = [query.strip()[:40]]

    seen, results = set(), []
    for token in tokens[:4]:   # limita para não explodir a query
        sparql = SPARQL_TEMPLATE.format(
            query=token.replace('"', '').replace("'", ""),
            limit=top_k * 2,
        )
        try:
            for row in g.query(sparql):
                work_uri = str(row.work)
                if work_uri not in seen:
                    seen.add(work_uri)
                    results.append({
                        "uri":      work_uri,
                        "titulo":   str(row.titulo)   if row.titulo   else "—",
                        "resumo":   str(row.resumo)   if row.resumo   else "",
                        "ano":      str(row.ano)       if row.ano      else "s/d",
                        "tipo":     str(row.tipo)      if row.tipo     else "",
                        "autores":  str(row.autores)   if row.autores  else "Desconhecido",
                        "keywords": str(row.keywords)  if row.keywords else "",
                        "acesso":   str(row.acesso)    if row.acesso   else "—",
                    })
        except Exception as exc:
            logger.warning(f"Erro SPARQL para token '{token}': {exc}")

    return results[:top_k]


# ─── Groq: geração aumentada ──────────────────────────────────────────────────
def build_context(results: list[dict]) -> str:
    """Formata os resultados SPARQL como contexto para o LLM."""
    if not results:
        return "Nenhum documento relevante encontrado no grafo semântico."
    parts = []
    for i, r in enumerate(results, 1):
        parts.append(
            f"[{i}] Título: {r['titulo']}\n"
            f"    Autores: {r['autores']} | Ano: {r['ano']} | Acesso: {r['acesso']}\n"
            f"    Palavras-chave: {r['keywords']}\n"
            f"    Resumo: {r['resumo'][:400]}{'…' if len(r['resumo']) > 400 else ''}\n"
            f"    URI: {r['uri']}"
        )
    return "\n\n".join(parts)


SYSTEM_PROMPT = """Você é um assistente especializado em pesquisa científica brasileira,
com foco no ecossistema Pinakes/BrCris do IBICT. Responda **em português**, de forma
precisa, clara e acadêmica. Use exclusivamente o contexto semântico fornecido (recuperado
por SPARQL de um grafo RDF Turtle com ontologias BIBO/DC/FOAF/VIVO). Se a informação não
constar no contexto, diga explicitamente. Respeite as diretrizes FAIR e LGPD ao tratar
dados de pesquisa. Cite os documentos recuperados pelos seus títulos."""


def groq_generate(client: Groq, user_query: str, context: str) -> str:
    """Chama a API Groq e retorna a resposta gerada."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"**Pergunta:** {user_query}\n\n"
                f"**Contexto semântico recuperado do grafo Pinakes:**\n{context}"
            ),
        },
    ]
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
    )
    return response.choices[0].message.content


# ─── Credenciais: HF Spaces Secret ou st.secrets ──────────────────────────────
def get_groq_api_key() -> str:
    """
    Resolve a chave Groq na seguinte ordem:
    1. Variável de ambiente GROQ_API_KEY  (HF Spaces Secret)
    2. st.secrets["GROQ_API_KEY"]         (secrets.toml local)
    3. Input do usuário via sidebar       (fallback interativo)
    """
    key = os.environ.get("GROQ_API_KEY") or os.environ.get("GROQ_APIKEY")
    if key:
        return key
    try:
        key = st.secrets["GROQ_API_KEY"]
        if key:
            return key
    except Exception:
        pass
    return ""


# ─── UI ───────────────────────────────────────────────────────────────────────
def render_sidebar(graph: Graph) -> tuple[Groq | None, int]:
    st.sidebar.image(
        "https://www.ibict.br/images/ibict-logo.png",
        width=120,
        caption="IBICT – Pinakes/BrCris",
    )
    st.sidebar.title("⚙️ Configurações")

    # API Key
    api_key = get_groq_api_key()
    if not api_key:
        api_key = st.sidebar.text_input(
            "🔑 Groq API Key",
            type="password",
            help="Obtenha em https://console.groq.com",
        )

    client = None
    if api_key:
        try:
            client = Groq(api_key=api_key)
            st.sidebar.success("✅ Groq conectado")
        except Exception as e:
            st.sidebar.error(f"Erro ao conectar Groq: {e}")
    else:
        st.sidebar.warning("⚠️ Insira a Groq API Key para usar o RAG.")

    # Top-K
    top_k = st.sidebar.slider("🎯 Documentos recuperados (top-k)", 1, 10, TOP_K_RESULTS)

    # Info do grafo
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**📊 Grafo RDF**  \n`{len(graph)}` triplas carregadas")
    st.sidebar.markdown(
        "**Stack:** RDFLib · SPARQL · Groq Llama 3.3 70B · Streamlit  \n"
        "**Ontologias:** BIBO · DC · FOAF · VIVO · PROV-O  \n"
        "**Compliance:** FAIR · LGPD"
    )
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "[📂 GitHub](https://github.com/acarloshenrique/SAVITS-Pinakes-RAG-Prototype) | "
        "[🤗 HF Spaces](https://huggingface.co/spaces)"
    )
    return client, top_k


def render_results(results: list[dict]):
    if not results:
        st.info("Nenhum documento encontrado no grafo para esta consulta.")
        return
    st.markdown(f"**{len(results)} documento(s) recuperado(s) via SPARQL:**")
    for r in results:
        with st.expander(f"📄 {r['titulo']} ({r['ano']})", expanded=False):
            cols = st.columns([2, 1])
            with cols[0]:
                st.markdown(f"**Autores:** {r['autores']}")
                st.markdown(f"**Palavras-chave:** {r['keywords'] or '—'}")
                if r['resumo']:
                    st.markdown(f"**Resumo:** {r['resumo'][:500]}{'…' if len(r['resumo']) > 500 else ''}")
            with cols[1]:
                st.markdown(f"**Acesso:** `{r['acesso']}`")
                st.markdown(f"**Tipo:** `{r['tipo'].split('/')[-1]}`")
                if r['uri'].startswith("http"):
                    st.markdown(f"[🔗 URI]({r['uri']})")


def main():
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title(APP_TITLE)
    st.caption(APP_SUBTITLE)
    st.markdown(
        "Este sistema usa um grafo RDF construído com **RDFLib** e consultado via **SPARQL** "
        "para recuperar documentos científicos brasileiros. A geração de respostas é feita pelo "
        "**Llama 3.3 70B** via Groq, seguindo as diretrizes **FAIR** e **LGPD**."
    )
    st.divider()

    # Carrega o grafo e renderiza a sidebar
    graph  = load_graph()
    client, top_k = render_sidebar(graph)

    # Histórico de chat
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input
    user_query = st.chat_input("💬 Faça uma pergunta sobre as pesquisas do Pinakes…")

    if user_query:
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        with st.chat_message("assistant"):
            with st.spinner("🔎 Consultando grafo SPARQL…"):
                results = sparql_retrieve(graph, user_query, top_k)

            tab_resp, tab_docs = st.tabs(["💬 Resposta RAG", "📚 Documentos Recuperados"])

            with tab_docs:
                render_results(results)

            with tab_resp:
                if not client:
                    st.warning("Configure a Groq API Key na sidebar para gerar respostas.")
                else:
                    context = build_context(results)
                    with st.spinner("🤖 Gerando resposta com Llama 3.3 70B…"):
                        try:
                            t0 = time.time()
                            answer = groq_generate(client, user_query, context)
                            elapsed = time.time() - t0
                            st.markdown(answer)
                            st.caption(f"⏱ Gerado em {elapsed:.1f}s | Modelo: {GROQ_MODEL}")
                            st.session_state.messages.append(
                                {"role": "assistant", "content": answer}
                            )
                        except Exception as e:
                            st.error(f"Erro na API Groq: {e}")


if __name__ == "__main__":
    main()
