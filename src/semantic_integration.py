"""
semantic_integration.py
Geração automática do grafo RDF (pinakes_graph.ttl) a partir de data/raw_data.json.
Stack: RDFLib + ontologias BIBO / DC / FOAF / SCHEMA / custom Pinakes.
Uso: python src/semantic_integration.py [--input data/raw_data.json] [--output pinakes_graph.ttl]
"""

import json
import argparse
import hashlib
from pathlib import Path
from datetime import datetime

from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, OWL, XSD, DC, FOAF

# ─── Namespaces ───────────────────────────────────────────────────────────────
BIBO    = Namespace("http://purl.org/ontology/bibo/")
SCHEMA  = Namespace("https://schema.org/")
PINAKES = Namespace("https://pinakes.ibict.br/ontology/")
BRCRIS  = Namespace("https://brcris.ibict.br/resource/")
DCTERMS = Namespace("http://purl.org/dc/terms/")
VIVO    = Namespace("http://vivoweb.org/ontology/core#")
PROV    = Namespace("http://www.w3.org/ns/prov#")
DCAT    = Namespace("http://www.w3.org/ns/dcat#")

# ─── Tipo → classe RDF ────────────────────────────────────────────────────────
WORK_TYPE_MAP = {
    "artigo":        BIBO.AcademicArticle,
    "tese":          BIBO.Thesis,
    "dissertacao":   BIBO.Thesis,
    "dissertação":   BIBO.Thesis,
    "livro":         BIBO.Book,
    "capitulo":      BIBO.BookSection,
    "capítulo":      BIBO.BookSection,
    "relatorio":     BIBO.Report,
    "relatório":     BIBO.Report,
    "conferencia":   BIBO.Conference,
    "conferência":   BIBO.Conference,
    "default":       BIBO.Document,
}


def slugify(text: str) -> str:
    """Gera um slug URL-safe a partir de uma string."""
    import re
    text = text.lower().strip()
    text = re.sub(r"[áàãâä]", "a", text)
    text = re.sub(r"[éèêë]", "e", text)
    text = re.sub(r"[íìîï]", "i", text)
    text = re.sub(r"[óòõôö]", "o", text)
    text = re.sub(r"[úùûü]", "u", text)
    text = re.sub(r"[ç]", "c", text)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def mint_uri(namespace: Namespace, *parts: str) -> URIRef:
    """Cria uma URIRef limpa combinando namespace + partes slugificadas."""
    slug = "_".join(slugify(p) for p in parts if p)
    return namespace[slug]


def short_hash(text: str, length: int = 8) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:length]


# ─── Adicionar proveniência PROV-O ───────────────────────────────────────────
def add_provenance(g: Graph, source_file: str) -> URIRef:
    activity = BRCRIS[f"gen_{short_hash(source_file + datetime.utcnow().isoformat())}"]
    g.add((activity, RDF.type, PROV.Activity))
    g.add((activity, RDFS.label, Literal("Geração automática via semantic_integration.py")))
    g.add((activity, PROV.startedAtTime, Literal(datetime.utcnow().isoformat(), datatype=XSD.dateTime)))
    g.add((activity, PROV.wasAssociatedWith, URIRef("https://github.com/acarloshenrique/SAVITS-Pinakes-RAG-Prototype")))
    return activity


# ─── Mapear Author ────────────────────────────────────────────────────────────
def map_author(g: Graph, author_data: dict, work_uri: URIRef) -> URIRef:
    name   = author_data.get("nome") or author_data.get("name", "Autor Desconhecido")
    orcid  = author_data.get("orcid")
    lattes = author_data.get("lattes")
    affil  = author_data.get("afiliacao") or author_data.get("affiliation")

    if orcid:
        author_uri = URIRef(f"https://orcid.org/{orcid.lstrip('https://orcid.org/')}")
    else:
        author_uri = mint_uri(BRCRIS, "author", name, short_hash(name))

    g.add((author_uri, RDF.type, FOAF.Person))
    g.add((author_uri, RDF.type, VIVO.FacultyMember))
    g.add((author_uri, FOAF.name, Literal(name, lang="pt")))

    if orcid:
        g.add((author_uri, PINAKES.orcid, Literal(orcid)))
    if lattes:
        g.add((author_uri, PINAKES.lattesID, Literal(lattes)))
    if affil:
        inst_uri = map_institution(g, affil if isinstance(affil, dict) else {"nome": affil})
        g.add((author_uri, SCHEMA.affiliation, inst_uri))

    # Relação com a obra
    g.add((work_uri, DC.creator, author_uri))
    g.add((work_uri, BIBO.authorList, author_uri))

    return author_uri


# ─── Mapear Institution ───────────────────────────────────────────────────────
def map_institution(g: Graph, inst_data: dict) -> URIRef:
    name  = inst_data.get("nome") or inst_data.get("name", "Instituição Desconhecida")
    cnpj  = inst_data.get("cnpj")
    ror   = inst_data.get("ror")

    if ror:
        inst_uri = URIRef(f"https://ror.org/{ror.lstrip('https://ror.org/')}")
    else:
        inst_uri = mint_uri(BRCRIS, "institution", name)

    g.add((inst_uri, RDF.type, FOAF.Organization))
    g.add((inst_uri, RDF.type, VIVO.University))
    g.add((inst_uri, FOAF.name, Literal(name, lang="pt")))

    if cnpj:
        g.add((inst_uri, PINAKES.cnpj, Literal(cnpj)))
    if ror:
        g.add((inst_uri, PINAKES.rorID, Literal(ror)))
    country = inst_data.get("pais") or inst_data.get("country", "Brasil")
    g.add((inst_uri, SCHEMA.addressCountry, Literal(country)))

    return inst_uri


# ─── Mapear Subject / Keyword ─────────────────────────────────────────────────
def map_keyword(g: Graph, kw: str, work_uri: URIRef):
    kw = kw.strip()
    kw_uri = mint_uri(BRCRIS, "keyword", kw)
    g.add((kw_uri, RDF.type, SCHEMA.DefinedTerm))
    g.add((kw_uri, RDFS.label, Literal(kw, lang="pt")))
    g.add((work_uri, DCTERMS.subject, kw_uri))
    g.add((work_uri, SCHEMA.keywords, Literal(kw, lang="pt")))


# ─── Mapear Journal/Venue ─────────────────────────────────────────────────────
def map_venue(g: Graph, venue_data: dict, work_uri: URIRef):
    name  = venue_data.get("nome") or venue_data.get("name", "")
    issn  = venue_data.get("issn")
    if not name:
        return

    venue_uri = mint_uri(BRCRIS, "venue", name)
    g.add((venue_uri, RDF.type, BIBO.Periodical))
    g.add((venue_uri, DC.title, Literal(name, lang="pt")))
    if issn:
        g.add((venue_uri, BIBO.issn, Literal(issn)))
    g.add((work_uri, DCTERMS.isPartOf, venue_uri))


# ─── Mapear Work ──────────────────────────────────────────────────────────────
def map_work(g: Graph, item: dict, prov_activity: URIRef, source_label: str) -> URIRef:
    # Identidade
    work_id  = str(item.get("id") or item.get("doi") or short_hash(json.dumps(item)))
    doi      = item.get("doi")
    titulo   = item.get("titulo") or item.get("title", f"Trabalho {work_id}")
    tipo_str = (item.get("tipo") or item.get("type", "default")).lower()
    tipo_cls = WORK_TYPE_MAP.get(tipo_str, WORK_TYPE_MAP["default"])

    ark_identifier = None
    if doi:
        work_uri = URIRef(f"https://doi.org/{doi}")
    else:
        ark_identifier = item.get("ark") or f"ark:/13030/savits-{work_id}"
        work_uri = mint_uri(BRCRIS, "work", work_id)

    # Tipo
    g.add((work_uri, RDF.type, tipo_cls))
    g.add((work_uri, RDF.type, BIBO.Document))

    # Metadados básicos
    lang = item.get("idioma") or item.get("language", "pt")
    g.add((work_uri, DC.title,     Literal(titulo, lang=lang)))
    g.add((work_uri, DCTERMS.title, Literal(titulo, lang=lang)))

    if doi:
        g.add((work_uri, BIBO.doi, Literal(doi)))
    if ark_identifier:
        g.add((work_uri, DCTERMS.identifier, Literal(ark_identifier)))

    resumo = item.get("resumo") or item.get("abstract")
    if resumo:
        g.add((work_uri, DCTERMS.abstract, Literal(resumo, lang=lang)))
        g.add((work_uri, DC.description,   Literal(resumo, lang=lang)))

    ano = item.get("ano") or item.get("year")
    if ano:
        g.add((work_uri, DCTERMS.issued, Literal(str(ano), datatype=XSD.gYear)))
        g.add((work_uri, DC.date, Literal(str(ano))))

    # Acesso / FAIR
    access = item.get("acesso") or item.get("access", "restrito")
    g.add((work_uri, DCTERMS.accessRights, Literal(access)))
    license_url = item.get("licenca") or item.get("license")
    if license_url:
        g.add((work_uri, DCTERMS.license, URIRef(license_url)))

    # LGPD – dados sensíveis
    dados_pessoais = item.get("dados_pessoais", False)
    g.add((work_uri, PINAKES.contemDadosPessoais, Literal(dados_pessoais, datatype=XSD.boolean)))
    status_lgpd = item.get("status_lgpd") or ("Controlado" if dados_pessoais else "Anonimizado")
    g.add((work_uri, PINAKES.statusLGPD, Literal(status_lgpd)))
    base_legal = item.get("base_legal_lgpd") or ("Consentimento" if dados_pessoais else "Dados anonimizados (Art. 12)")
    g.add((work_uri, PINAKES.baseLegalLGPD, Literal(base_legal)))

    # Autores
    for author_data in item.get("autores") or item.get("authors") or []:
        if isinstance(author_data, str):
            author_data = {"nome": author_data}
        map_author(g, author_data, work_uri)

    # Palavras-chave
    for kw in item.get("palavras_chave") or item.get("keywords") or []:
        map_keyword(g, kw, work_uri)

    # Venue/periódico
    venue = item.get("periodico") or item.get("venue") or item.get("journal")
    if venue:
        if isinstance(venue, str):
            venue = {"nome": venue}
        map_venue(g, venue, work_uri)

    # Áreas de conhecimento (CNPQ)
    impact_areas = item.get("areas_cnpq") or item.get("impact_area") or []
    if isinstance(impact_areas, str):
        impact_areas = [impact_areas]
    if not impact_areas:
        impact_areas = ["Ciência da Informação"]
    for area in impact_areas:
        area_uri = mint_uri(BRCRIS, "area", area)
        g.add((area_uri, RDF.type, SCHEMA.CategoryCode))
        g.add((area_uri, RDFS.label, Literal(area, lang="pt")))
        g.add((work_uri, VIVO.hasResearchArea, area_uri))
        g.add((work_uri, PINAKES.temImpactoSocial, Literal(area, lang="pt")))

    # Proveniência
    source_ref = item.get("fonte") or item.get("source") or source_label
    g.add((work_uri, PROV.wasGeneratedBy, prov_activity))
    g.add((work_uri, DCTERMS.source, Literal(source_ref)))

    # Texto completo RAG – concatenado para embedding/SPARQL
    rag_text_parts = [titulo]
    if resumo:
        rag_text_parts.append(resumo)
    for kw in item.get("palavras_chave") or item.get("keywords") or []:
        rag_text_parts.append(kw)
    g.add((work_uri, PINAKES.ragText, Literal(" | ".join(rag_text_parts), lang=lang)))

    return work_uri


# ─── Pipeline principal ───────────────────────────────────────────────────────
def build_graph(raw_data: list, source_file: str = "raw_data.json") -> Graph:
    g = Graph()

    # Bind namespaces
    g.bind("bibo",    BIBO)
    g.bind("schema",  SCHEMA)
    g.bind("pinakes", PINAKES)
    g.bind("brcris",  BRCRIS)
    g.bind("dcterms", DCTERMS)
    g.bind("dc",      DC)
    g.bind("foaf",    FOAF)
    g.bind("vivo",    VIVO)
    g.bind("prov",    PROV)
    g.bind("dcat",    DCAT)

    # Ontologia inline
    onto = PINAKES["Ontology"]
    g.add((onto, RDF.type, OWL.Ontology))
    g.add((onto, RDFS.label,   Literal("Pinakes RAG Ontology", lang="en")))
    g.add((onto, RDFS.comment, Literal("Ontologia do protótipo SAVITS-Pinakes para RAG semântico (FAIR/LGPD)", lang="pt")))
    g.add((onto, DC.creator,   URIRef("https://github.com/acarloshenrique")))
    g.add((onto, DCTERMS.modified, Literal(datetime.utcnow().isoformat(), datatype=XSD.dateTime)))

    # Proveniência global
    prov_activity = add_provenance(g, source_file)

    # Processar itens
    items = raw_data if isinstance(raw_data, list) else raw_data.get("works") or raw_data.get("dados") or []
    for item in items:
        try:
            map_work(g, item, prov_activity, source_file)
        except Exception as exc:
            print(f"  [AVISO] Erro ao processar item {item.get('id','[build]')}: {exc}")

    print(f"  ✅ Grafo gerado: {len(g)} triplas | {len(items)} itens processados")
    return g


def generate_graph(input_path: str, output_path: str):
    input_file = Path(input_path)
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"📂 Lendo {input_file}...")
    with open(input_file, encoding="utf-8") as f:
        raw_data = json.load(f)

    print("🔨 Construindo grafo RDF...")
    g = build_graph(raw_data, source_file=input_file.name)

    print(f"💾 Serializando para {output_file}...")
    g.serialize(destination=str(output_file), format="turtle")
    print(f"✅ {output_file} gerado com sucesso!")


# ─── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera pinakes_graph.ttl a partir de raw_data.json")
    parser.add_argument("--input",  default="data/raw_data.json",  help="Caminho do JSON de entrada")
    parser.add_argument("--output", default="pinakes_graph.ttl",   help="Caminho do TTL de saída")
    args = parser.parse_args()
    generate_graph(args.input, args.output)
