"""
app.py — SAVITS Pinakes RAG Prototype
Sistema RAG Semântico: RDFLib + SPARQL + Groq (Llama 3.3 70B) + Streamlit
Deploy: Hugging Face Spaces (GROQ_API_KEY configurada como Secret)
"""

import os
import re
import time
import logging
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import streamlit as st
from rdflib import Graph
from groq import Groq

from src.analytics.bibliometrics import compute_graph_kpis, detect_deia_gaps
from src.analytics.slo_monitor import log_retrieval_event
from src.governance.fair_validator import evaluate_graph
from src.governance.provenance_tracker import governance_indicators
from src.ingestion.bdtd_harvester import harvest_bdtd
from src.ingestion.brcris_harvester import harvest_brcris
from src.ingestion.oasisbr_harvester import harvest_oasisbr
from src.ingestion.openalex_harvester import harvest_openalex
from src.retrieval.hybrid_service import (
    merge_retrieval_results as merge_retrieval_results_service,
    query_tokens as query_tokens_service,
    retrieve_api_results as retrieve_api_results_service,
    retrieval_diagnostics,
)
# ─── Configuração de logging ──────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Constantes ───────────────────────────────────────────────────────────────
DEFAULT_GRAPH_PATH        = Path("pinakes_graph_enriched.ttl")
FALLBACK_GRAPH_PATH       = Path("pinakes_graph.ttl")
GROQ_MODEL      = "llama-3.3-70b-versatile"
MAX_TOKENS      = 1024
TEMPERATURE     = 0.3
TOP_K_RESULTS   = 5
APP_TITLE       = "🔍 SAVITS Pinakes RAG"
APP_SUBTITLE    = "Sistema RAG Semântico para o ecossistema Pinakes/BrCris (IBICT)"
TOKEN_LIMIT     = 12
STOPWORDS_PT    = {
    "como", "onde", "quando", "qual", "quais", "sobre", "para", "com", "sem", "dos",
    "das", "de", "do", "da", "e", "ou", "em", "um", "uma", "os", "as", "no", "na",
    "nos", "nas", "por", "que", "se", "ao", "aos", "a", "o", "tratam", "trata",
}
PRIORITY_TERMS  = {
    "fair", "care", "lgpd", "deia", "governanca", "proveniencia",
    "dados", "pesquisa", "ciencia", "informacao", "ontologia", "interoperabilidade",
}
GOVERNANCE_QUERY_TERMS = {
    "fair", "care", "lgpd", "deia", "governanca", "proveniencia", "prov", "dcterms",
}
MIN_REMOTE_API_DOCS = int(os.environ.get("MIN_REMOTE_API_DOCS", "1"))


# ─── Carregamento do grafo RDF ─────────────────────────────────────────────────
@st.cache_resource(show_spinner="Carregando grafo RDF…")
def load_graph(graph_path: str, graph_mtime: float | None = None) -> Graph:
    """Carrega o grafo Turtle em cache na sessão do Streamlit."""
    path = Path(graph_path)
    if not path.exists():
        st.error(
            f"Arquivo `{path}` não encontrado. "
            "Execute `python build_graph.py` para gerar os TTLs."
        )
        st.stop()
    g = Graph()
    g.parse(str(path), format="turtle")
    logger.info(f"Grafo carregado: {len(g)} triplas de {path}")
    return g


def resolve_graph_path() -> Path:
    env_path = os.environ.get("PINAKES_GRAPH_PATH")
    if env_path:
        explicit = Path(env_path)
        if explicit.exists():
            return explicit
        logger.warning("PINAKES_GRAPH_PATH configurado, mas arquivo não existe: %s", explicit)

    if DEFAULT_GRAPH_PATH.exists():
        return DEFAULT_GRAPH_PATH
    return FALLBACK_GRAPH_PATH


def refresh_graph_from_sources(output_path: Path = DEFAULT_GRAPH_PATH) -> tuple[int, int]:
    """
    Atualiza o grafo enriquecido a partir dos coletores (APIs/cache/fallback).
    Retorna (documentos, triplas).
    """
    from src.curation.pipeline import run_pipeline
    from src.graph.graph_builder import build_graph as build_enriched_graph

    docs = run_pipeline()
    graph = build_enriched_graph(docs)
    graph.serialize(str(output_path), format="turtle")
    return len(docs), len(graph)


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
  ?work a bibo:Document .
  {{
    ?work dc:title ?titulo .
  }} UNION {{
    ?work dcterms:title ?titulo .
  }}
  OPTIONAL {{ ?work dcterms:abstract ?resumo . }}
  OPTIONAL {{
    {{
      ?work dc:date ?ano .
    }} UNION {{
      ?work dcterms:issued ?ano .
    }}
  }}
  OPTIONAL {{ ?work a               ?tipo . FILTER(?tipo != <http://www.w3.org/2002/07/owl#Thing>) }}
  OPTIONAL {{
    {{
      ?work dc:creator ?autor .
    }} UNION {{
      ?work dcterms:creator ?autor .
    }}
    OPTIONAL {{ ?autor foaf:name ?autorNome . }}
    BIND(COALESCE(?autorNome, ?autor) AS ?autores)
  }}
  OPTIONAL {{
    {{
      ?work schema:keywords ?keywords .
    }} UNION {{
      ?work dcterms:subject ?keywords .
    }}
  }}
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

SPARQL_BROWSE_TEMPLATE = """
PREFIX dc:      <http://purl.org/dc/elements/1.1/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX bibo:    <http://purl.org/ontology/bibo/>
PREFIX foaf:    <http://xmlns.com/foaf/0.1/>
PREFIX pinakes: <https://pinakes.ibict.br/ontology/>
PREFIX schema:  <https://schema.org/>
PREFIX rdfs:    <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?work ?titulo ?resumo ?ano ?tipo ?autores ?keywords ?acesso
WHERE {{
  ?work a bibo:Document .
  {{
    ?work dc:title ?titulo .
  }} UNION {{
    ?work dcterms:title ?titulo .
  }}
  OPTIONAL {{ ?work dcterms:abstract ?resumo . }}
  OPTIONAL {{
    {{
      ?work dc:date ?ano .
    }} UNION {{
      ?work dcterms:issued ?ano .
    }}
  }}
  OPTIONAL {{ ?work a               ?tipo . FILTER(?tipo != <http://www.w3.org/2002/07/owl#Thing>) }}
  OPTIONAL {{
    {{
      ?work dc:creator ?autor .
    }} UNION {{
      ?work dcterms:creator ?autor .
    }}
    OPTIONAL {{ ?autor foaf:name ?autorNome . }}
    BIND(COALESCE(?autorNome, ?autor) AS ?autores)
  }}
  OPTIONAL {{
    {{
      ?work schema:keywords ?keywords .
    }} UNION {{
      ?work dcterms:subject ?keywords .
    }}
  }}
  OPTIONAL {{ ?work dcterms:accessRights ?acesso . }}
  OPTIONAL {{ ?work pinakes:ragText ?ragText . }}
}}
LIMIT {limit}
"""

def _row_to_result(row) -> dict:
    return {
        "uri":      str(row.work),
        "titulo":   str(row.titulo)   if row.titulo   else "—",
        "resumo":   str(row.resumo)   if row.resumo   else "",
        "ano":      str(row.ano)      if row.ano      else "s/d",
        "tipo":     str(row.tipo)     if row.tipo     else "",
        "autores":  str(row.autores)  if row.autores  else "Desconhecido",
        "keywords": str(row.keywords) if row.keywords else "",
        "acesso":   str(row.acesso)   if row.acesso   else "—",
        "retrieval_channel": "sparql",
        "retrieval_source": "graph",
        "retrieval_mode": "local",
    }


def _result_score(result: dict, tokens: list[str]) -> tuple[int, int]:
    text = " ".join(
        [
            str(result.get("titulo", "")),
            str(result.get("resumo", "")),
            str(result.get("keywords", "")),
            str(result.get("acesso", "")),
            str(result.get("tipo", "")),
        ]
    )
    normalized = _normalize_term(text)
    token_hits = sum(1 for token in tokens if token in normalized)
    year_match = re.search(r"\d{4}", str(result.get("ano", "")))
    year_value = int(year_match.group(0)) if year_match else 0
    return token_hits, year_value


def _broaden_results(
    g: Graph,
    seen_uris: set[str],
    seen_titles: set[str],
    top_k: int,
    tokens: list[str],
) -> list[dict]:
    broaden_limit = max(30, top_k * 10)
    query = SPARQL_BROWSE_TEMPLATE.format(limit=broaden_limit)
    fallback_pool = []
    for row in g.query(query):
        item = _row_to_result(row)
        title_key = _normalize_term(item.get("titulo", ""))
        if item["uri"] in seen_uris or title_key in seen_titles:
            continue
        fallback_pool.append(item)

    fallback_pool.sort(key=lambda item: _result_score(item, tokens), reverse=True)
    return fallback_pool


def sparql_retrieve(g: Graph, query: str, top_k: int = TOP_K_RESULTS) -> list[dict]:
    """Executa busca SPARQL no grafo local e retorna lista de resultados."""
    tokens = _query_tokens(query)
    if not tokens:
        tokens = [query.strip()[:40]]

    seen_uris, seen_titles, results = set(), set(), []
    for token in tokens[:TOKEN_LIMIT]:
        sparql = SPARQL_TEMPLATE.format(
            query=token.replace('"', '').replace("'", ""),
            limit=top_k * 2,
        )
        try:
            for row in g.query(sparql):
                item = _row_to_result(row)
                work_uri = item["uri"]
                title_key = _normalize_term(item.get("titulo", ""))
                if work_uri in seen_uris or title_key in seen_titles:
                    continue
                seen_uris.add(work_uri)
                seen_titles.add(title_key)
                results.append(item)
        except Exception as exc:
            logger.warning(f"Erro SPARQL para token '{token}': {exc}")

    if len(results) < top_k:
        broadened = _broaden_results(g, seen_uris, seen_titles, top_k, tokens)
        for item in broadened:
            if len(results) >= top_k:
                break
            title_key = _normalize_term(item.get("titulo", ""))
            if item["uri"] in seen_uris or title_key in seen_titles:
                continue
            seen_uris.add(item["uri"])
            seen_titles.add(title_key)
            results.append(item)

    return results[:top_k]


def _normalize_term(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    return normalized.lower().strip()


def _query_tokens(query: str) -> list[str]:
    return query_tokens_service(query)


def _as_text_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = []
        for item in value:
            if isinstance(item, dict):
                items.extend(_as_text_list(item.get("name") or item.get("nome")))
            else:
                text = str(item).strip()
                if text:
                    items.append(text)
        return items
    text = str(value).strip()
    return [text] if text else []


def _normalize_api_record(source: str, record: dict) -> dict | None:
    title = str(record.get("title") or record.get("titulo") or "").strip()
    if not title:
        return None

    raw_authors = record.get("authors") or record.get("autores")
    authors = ", ".join(_as_text_list(raw_authors)) or "Desconhecido"

    raw_keywords = record.get("keywords") or record.get("palavras_chave")
    keywords = ", ".join(_as_text_list(raw_keywords))

    uri = record.get("source_uri") or record.get("doi") or record.get("id") or f"{source}:{title}"
    uri_text = str(uri).strip()
    if uri_text and not uri_text.startswith("http"):
        uri_text = f"{source}:{uri_text}"

    return {
        "uri": uri_text or f"{source}:{title}",
        "titulo": title,
        "resumo": str(record.get("abstract") or record.get("resumo") or ""),
        "ano": str(record.get("year") or record.get("ano") or "s/d"),
        "tipo": str(record.get("maturity_level") or record.get("tipo") or "Document"),
        "autores": authors,
        "keywords": keywords,
        "acesso": str(record.get("acesso") or record.get("access") or "—"),
        "retrieval_channel": "api",
        "retrieval_source": source,
        "retrieval_mode": str(record.get("ingestion_mode") or "remote"),
    }


def _retrieve_api_source(source: str, user_query: str, limit: int) -> list[dict]:
    try:
        if source == "openalex":
            records = harvest_openalex(query=user_query, per_page=limit, force_refresh=True)
        elif source == "brcris":
            records = harvest_brcris(limit=limit, force_refresh=True, query=user_query)
        elif source == "oasisbr":
            records = harvest_oasisbr(limit=limit, force_refresh=True, query=user_query)
        elif source == "bdtd":
            records = harvest_bdtd(limit=limit, force_refresh=True, query=user_query)
        else:
            return []
    except Exception as exc:
        logger.warning("Falha ao consultar fonte %s: %s", source, exc)
        return []

    out = []
    for record in records:
        if not isinstance(record, dict):
            continue
        normalized = _normalize_api_record(source, record)
        if normalized:
            out.append(normalized)
    return out


@st.cache_data(show_spinner=False, ttl=900)
def retrieve_api_results(user_query: str, top_k: int) -> list[dict]:
    return retrieve_api_results_service(user_query, top_k)


def _append_unique_result(
    sink: list[dict],
    seen_uris: set[str],
    seen_titles: set[str],
    item: dict,
) -> bool:
    uri_key = str(item.get("uri") or "").strip()
    title_key = _normalize_term(item.get("titulo", ""))
    if (uri_key and uri_key in seen_uris) or (title_key and title_key in seen_titles):
        return False
    if uri_key:
        seen_uris.add(uri_key)
    if title_key:
        seen_titles.add(title_key)
    sink.append(item)
    return True


def merge_retrieval_results(
    user_query: str,
    sparql_results: list[dict],
    api_results: list[dict],
    top_k: int,
) -> list[dict]:
    return merge_retrieval_results_service(user_query, sparql_results, api_results, top_k)


# ─── Groq: geração aumentada ──────────────────────────────────────────────────
def build_context(results: list[dict]) -> str:
    """Formata resultados combinados (SPARQL + APIs) como contexto para o LLM."""
    if not results:
        return "Nenhum documento relevante encontrado no grafo semântico."
    parts = []
    for i, r in enumerate(results, 1):
        parts.append(
            f"[{i}] Título: {r['titulo']}\n"
            f"    Fonte: {r.get('retrieval_source', 'graph')} | Canal: {r.get('retrieval_channel', 'sparql')}\n"
            f"    Autores: {r['autores']} | Ano: {r['ano']} | Acesso: {r['acesso']}\n"
            f"    Palavras-chave: {r['keywords']}\n"
            f"    Resumo: {r['resumo'][:400]}{'…' if len(r['resumo']) > 400 else ''}\n"
            f"    URI: {r['uri']}"
        )
    return "\n\n".join(parts)


SYSTEM_PROMPT = """Você é um assistente especializado em pesquisa científica brasileira,
com foco no ecossistema Pinakes/BrCris do IBICT. Responda **em português**, de forma
precisa, clara e acadêmica. Use exclusivamente o contexto consolidado fornecido
(SPARQL do grafo RDF + conectores BrCris/Oasisbr/BDTD/OpenAlex). Se a informação não
constar no contexto, diga explicitamente. Respeite as diretrizes FAIR e LGPD ao tratar
dados de pesquisa. Não invente DOI, URI, título ou percentual: use apenas os valores que
aparecem no contexto fornecido."""


def build_governance_context(compliance: dict, governance: dict, analytics: dict) -> str:
    lines = [f"Documentos avaliados: {compliance.get('documents', 0)}"]
    for score in compliance.get("scores", []):
        pct = int(float(score.get("coverage", 0)) * 100)
        lines.append(f"{score.get('pillar')}: {pct}%")
    lines.append(f"DCTERMS.source cobertura: {int(governance.get('source_coverage', 0) * 100)}%")
    lines.append(f"PROV.wasGeneratedBy cobertura: {int(governance.get('prov_coverage', 0) * 100)}%")
    lines.append(f"LGPD base legal cobertura: {int(governance.get('lgpd_coverage', 0) * 100)}%")
    lines.append(f"Acesso aberto: {int(analytics.get('open_access_ratio', 0) * 100)}%")
    return "\n".join(lines)


def is_governance_query(query: str) -> bool:
    tokens = _query_tokens(query)
    return any(token in GOVERNANCE_QUERY_TERMS for token in tokens)


def deterministic_governance_answer(
    compliance: dict,
    governance: dict,
    analytics: dict,
    results: list[dict],
) -> str:
    score_map = {
        score.get("pillar"): int(float(score.get("coverage", 0)) * 100)
        for score in compliance.get("scores", [])
    }
    fair_parts = [
        f"Findable {score_map.get('FAIR_FINDABLE', 0)}%",
        f"Accessible {score_map.get('FAIR_ACCESSIBLE', 0)}%",
        f"Interoperable {score_map.get('FAIR_INTEROPERABLE', 0)}%",
        f"Reusable {score_map.get('FAIR_REUSABLE', 0)}%",
    ]
    care_parts = [
        f"Collective {score_map.get('CARE_COLLECTIVE', 0)}%",
        f"Authority {score_map.get('CARE_AUTHORITY', 0)}%",
        f"Responsibility {score_map.get('CARE_RESPONSIBILITY', 0)}%",
    ]

    sources_cov = int(governance.get("source_coverage", 0) * 100)
    prov_cov = int(governance.get("prov_coverage", 0) * 100)
    lgpd_cov = int(governance.get("lgpd_coverage", 0) * 100)
    open_access = int(analytics.get("open_access_ratio", 0) * 100)
    deia_cov = int(analytics.get("deia_coverage", 0) * 100)
    total_docs = int(compliance.get("documents", 0))

    doc_titles = []
    for row in results:
        title = str(row.get("titulo") or "").strip()
        if title and title not in doc_titles:
            doc_titles.append(title)
    cited = "; ".join(doc_titles[:3]) if doc_titles else "Nenhum documento específico recuperado nesta consulta."

    return (
        f"O grafo Pinakes avalia {total_docs} documentos com cobertura FAIR de "
        f"{', '.join(fair_parts)}.\n\n"
        f"No bloco CARE implementado no validador atual, as coberturas são: {', '.join(care_parts)}. "
        "A dimensão CARE Ethics não aparece como pilar separado neste relatório.\n\n"
        f"Indicadores de governança/proveniência: DCTERMS.source {sources_cov}%, "
        f"PROV.wasGeneratedBy {prov_cov}%, base legal LGPD {lgpd_cov}%, acesso aberto {open_access}%.\n\n"
        f"Observação: a cobertura DEIA calculada está em {deia_cov}% no grafo atual.\n\n"
        f"Documentos recuperados nesta resposta: {cited}."
    )


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
def render_sidebar(graph: Graph, active_graph_path: Path) -> tuple[Groq | None, int]:
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

    if st.sidebar.button("🔄 Atualizar grafo via APIs/cache", use_container_width=True):
        with st.sidebar:
            with st.spinner("Atualizando fontes e regenerando grafo..."):
                try:
                    docs_count, triple_count = refresh_graph_from_sources(DEFAULT_GRAPH_PATH)
                    st.cache_resource.clear()
                    st.success(f"Grafo atualizado: {docs_count} registros, {triple_count} triplas.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Falha ao atualizar grafo: {exc}")

    # Info do grafo
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**📊 Grafo RDF**  \n`{len(graph)}` triplas carregadas")
    st.sidebar.markdown(f"**Arquivo ativo:** `{active_graph_path}`")
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


def render_results(results: list[dict], top_k: int):
    if not results:
        st.info("Nenhum documento encontrado no grafo para esta consulta.")
        return
    sparql_count = sum(1 for item in results if item.get("retrieval_channel") == "sparql")
    api_count = sum(1 for item in results if item.get("retrieval_channel") == "api")
    source_modes = {}
    for item in results:
        if item.get("retrieval_channel") != "api":
            continue
        source = str(item.get("retrieval_source") or "api")
        mode = str(item.get("retrieval_mode") or "remote")
        source_modes[source] = mode
    st.caption(f"Top-k configurado: {top_k}")
    st.markdown(
        f"**{len(results)} documento(s) recuperado(s): SPARQL {sparql_count} | APIs {api_count}**"
    )
    if source_modes:
        mode_text = ", ".join(f"{source} ({mode})" for source, mode in source_modes.items())
        st.caption(f"Fontes API consultadas: {mode_text}")
    for r in results:
        with st.expander(f"📄 {r['titulo']} ({r['ano']})", expanded=False):
            cols = st.columns([2, 1])
            with cols[0]:
                st.markdown(
                    f"**Canal/Fonte:** `{r.get('retrieval_channel', 'n/a')}` / "
                    f"`{r.get('retrieval_source', 'n/a')}`"
                )
                st.markdown(f"**Autores:** {r['autores']}")
                st.markdown(f"**Palavras-chave:** {r['keywords'] or '—'}")
                if r['resumo']:
                    st.markdown(f"**Resumo:** {r['resumo'][:500]}{'…' if len(r['resumo']) > 500 else ''}")
            with cols[1]:
                st.markdown(f"**Acesso:** `{r['acesso']}`")
                st.markdown(f"**Tipo:** `{r['tipo'].split('/')[-1]}`")
                if r['uri'].startswith("http"):
                    st.markdown(f"[🔗 URI]({r['uri']})")
                else:
                    st.markdown(f"**ID/URI:** `{r['uri']}`")


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
        "Este sistema recupera documentos por **SPARQL** no grafo RDF local e também por "
        "**APIs OpenAlex/Oasisbr/BDTD (prioridade REST) + BrCris (secundária)**. A geração de respostas é feita pelo "
        "**Llama 3.3 70B** via Groq, seguindo as diretrizes **FAIR** e **LGPD**."
    )
    st.divider()

    # Carrega o grafo e renderiza a sidebar
    graph_path = resolve_graph_path()
    graph_mtime = graph_path.stat().st_mtime if graph_path.exists() else None
    graph  = load_graph(str(graph_path), graph_mtime)
    client, top_k = render_sidebar(graph, graph_path)

    # Histórico de chat
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input: suporta campo com botão "Buscar" e chat_input.
    user_query = None
    with st.form("search_form", clear_on_submit=False):
        query_text = st.text_input(
            "🔎 Consulta",
            value="",
            placeholder="Faça uma pergunta sobre as pesquisas do Pinakes…",
        )
        submitted = st.form_submit_button("Buscar")

    if submitted:
        typed_query = (query_text or "").strip()
        if typed_query:
            user_query = typed_query
        else:
            st.warning("Digite uma pergunta antes de buscar.")

    if user_query is None:
        chat_query = st.chat_input("💬 Faça uma pergunta sobre as pesquisas do Pinakes…")
        if chat_query:
            user_query = chat_query.strip()

    if user_query:
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        with st.chat_message("assistant"):
            with st.spinner("🔎 Consultando SPARQL + APIs REST (OpenAlex/Oasisbr/BDTD) e BrCris secundária…"):
                sparql_results = sparql_retrieve(graph, user_query, top_k)
                api_results = retrieve_api_results(user_query, top_k)
                results = merge_retrieval_results(user_query, sparql_results, api_results, top_k)
                diagnostics = retrieval_diagnostics(results)
                log_retrieval_event(user_query, top_k, diagnostics)
                critical_query = is_governance_query(user_query)
                remote_gate_ok = diagnostics.get("remote_api_docs", 0) >= MIN_REMOTE_API_DOCS

            compliance = evaluate_graph(graph)
            governance = governance_indicators(graph)
            analytics = compute_graph_kpis(graph)
            deia_gaps = detect_deia_gaps(graph)
            tab_resp, tab_docs, tab_governance, tab_analytics = st.tabs(
                [
                    "💬 Resposta RAG",
                    "📚 Documentos Recuperados",
                    "⚖️ Governança FAIR/CARE",
                    "📈 Analytics LGPD/DEIA",
                ]
            )

            with tab_docs:
                if diagnostics.get("remote_api_docs", 0) < MIN_REMOTE_API_DOCS:
                    st.warning(
                        f"Cobertura remota abaixo do mínimo ({diagnostics.get('remote_api_docs', 0)}/"
                        f"{MIN_REMOTE_API_DOCS}). Parte dos resultados pode estar em cache/fallback."
                    )
                render_results(results, top_k)

            with tab_governance:
                st.markdown(f"**Documentos avaliados:** {compliance['documents']}")
                st.caption("Pontuações calculadas automaticamente conforme FAIR/CARE/DEIA do edital SAVITS.")
                cols = st.columns(2)
                for idx, score in enumerate(compliance["scores"]):
                    with cols[idx % 2]:
                        pct = score["coverage"]
                        st.metric(score["pillar"], f"{int(pct * 100)}%", delta=None)
                        st.progress(pct)
                prov_cols = st.columns(3)
                prov_cols[0].metric("DCTERMS.source", f"{int(governance['source_coverage'] * 100)}%")
                prov_cols[1].metric("PROV.wasGeneratedBy", f"{int(governance['prov_coverage'] * 100)}%")
                prov_cols[2].metric("LGPD base legal", f"{int(governance['lgpd_coverage'] * 100)}%")
                if compliance["issues"]:
                    st.divider()
                    for issue in compliance["issues"]:
                        st.warning(f"[{issue['pillar']}] {issue['resource']}: {issue['detail']}")
                else:
                    st.success("Nenhum alerta de governança encontrado no grafo atual.")
                missing = governance["provenance"]
                if any(missing.values()):
                    st.info(
                        "Recursos sem metadados: "
                        + ", ".join(
                            f"{label}: {len(entries)}"
                            for label, entries in missing.items()
                            if entries
                        )
                    )

            with tab_analytics:
                st.metric("Documentos no grafo", analytics["total_documents"])
                metrics_cols = st.columns(3)
                metrics_cols[0].metric("Acesso aberto", f"{int(analytics['open_access_ratio'] * 100)}%")
                metrics_cols[1].metric("Impacto social", f"{int(analytics['impact_coverage'] * 100)}%")
                metrics_cols[2].metric("Cobertura DEIA", f"{int(analytics['deia_coverage'] * 100)}%")
                lgpd_cols = st.columns(2)
                lgpd_cols[0].metric("LGPD pronto", f"{int(analytics['lgpd_compliance'] * 100)}%")
                lgpd_cols[1].metric("Fontes distintas", len(analytics["sources"]))
                st.subheader("Principais fontes (DCTERMS.source)")
                if analytics["sources"]:
                    st.table(analytics["sources"])
                else:
                    st.write("Sem fontes declaradas nas triplas.")
                st.subheader("Top keywords")
                if analytics["top_keywords"]:
                    st.table(analytics["top_keywords"])
                else:
                    st.write("Sem palavras-chave indexadas.")
                if deia_gaps:
                    st.warning(f"{len(deia_gaps)} registro(s) sem anotações DEIA. Exemplos: {', '.join(deia_gaps[:3])}")
                else:
                    st.success("Todos os registros contam com tags DEIA.")

            with tab_resp:
                if critical_query and not remote_gate_ok:
                    answer = (
                        "Consulta crítica sem cobertura remota suficiente nas APIs. "
                        "A resposta foi bloqueada para evitar fallback silencioso. "
                        "Atualize as fontes e repita a consulta."
                    )
                    st.error(answer)
                    st.caption("Gate de confiabilidade: MIN_REMOTE_API_DOCS.")
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                elif is_governance_query(user_query):
                    answer = deterministic_governance_answer(compliance, governance, analytics, results)
                    st.markdown(answer)
                    st.caption("Resposta calculada diretamente a partir dos indicadores do grafo local.")
                    st.session_state.messages.append(
                        {"role": "assistant", "content": answer}
                    )
                elif not client:
                    st.warning("Configure a Groq API Key na sidebar para gerar respostas.")
                else:
                    docs_context = build_context(results)
                    governance_context = build_governance_context(compliance, governance, analytics)
                    context = (
                        f"{docs_context}\n\n"
                        f"[Indicadores FAIR/CARE/LGPD do grafo]\n{governance_context}"
                    )
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
