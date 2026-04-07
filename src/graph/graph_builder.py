from __future__ import annotations

from urllib.parse import quote

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, FOAF, RDF

SCHEMA = Namespace("https://schema.org/")
PINAKES = Namespace("https://pinakes.ibict.br/ontology/")
BIBO = Namespace("http://purl.org/ontology/bibo/")
PROV = Namespace("http://www.w3.org/ns/prov#")
EX = Namespace("http://example.org/")


def _encode_http_uri(uri: str) -> str:
    if "://" not in uri:
        return quote(uri, safe="@/?#&=:+-._~")
    scheme, rest = uri.split("://", 1)
    return f"{scheme}://{quote(rest, safe='@/?#&=:+-._~')}"


def _document_uri(record: dict) -> URIRef:
    doi = record.get("doi")
    if doi:
        doi = doi.strip()
        if doi.startswith("http"):
            uri = doi
        else:
            uri = f"https://doi.org/{doi}"
        return URIRef(_encode_http_uri(uri))
    if record.get("ark_id"):
        uri = f"https://pinakes.ibict.br/resource/{record['ark_id'].replace(':', '/')}"
        return URIRef(_encode_http_uri(uri))
    return URIRef(_encode_http_uri(EX + record["title"].replace(" ", "_")))


def build_graph(records):
    """
    Build an enriched RDFLib graph honoring FAIR/CARE commitments.
    """
    g = Graph()
    g.bind("dcterms", DCTERMS)
    g.bind("foaf", FOAF)
    g.bind("pinakes", PINAKES)
    g.bind("schema", SCHEMA)
    g.bind("bibo", BIBO)

    for record in records:
        doc = _document_uri(record)
        g.add((doc, RDF.type, BIBO.Document))
        g.add((doc, DCTERMS.title, Literal(record["title"], lang="pt")))
        if record.get("year"):
            g.add((doc, DCTERMS.issued, Literal(record["year"])))
        if record.get("doi"):
            g.add((doc, BIBO.doi, Literal(record["doi"])))
        if record.get("ark_id"):
            g.add((doc, DCTERMS.identifier, Literal(record["ark_id"])))
        if abstract := record.get("abstract"):
            g.add((doc, DCTERMS.abstract, Literal(abstract, lang="pt")))
        if record.get("access"):
            g.add((doc, DCTERMS.accessRights, Literal(record["access"])))
        if record.get("license"):
            g.add((doc, DCTERMS.license, URIRef(record["license"])))
        if record.get("source_reference"):
            g.add((doc, DCTERMS.source, Literal(record["source_reference"])))

        for keyword in record.get("keywords", []):
            g.add((doc, DCTERMS.subject, Literal(keyword, lang="pt")))
            g.add((doc, SCHEMA.keywords, Literal(keyword, lang="pt")))

        impact_area = record.get("impact_area")
        if isinstance(impact_area, list):
            impact_labels = impact_area
        else:
            impact_labels = [impact_area] if impact_area else []
        for area in impact_labels:
            g.add((doc, PINAKES.temImpactoSocial, Literal(area, lang="pt")))

        g.add((doc, PINAKES.statusLGPD, Literal(record.get("lgpd_status", "Desconhecido"))))
        g.add((doc, PINAKES.baseLegalLGPD, Literal(record.get("lgpd_legal_basis", "N/A"))))
        g.add((doc, PINAKES.dataProcessamento, Literal(record.get("processed_at"))))
        for tag in record.get("deia_tags", []):
            g.add((doc, PINAKES.deiaTag, Literal(tag)))

        activity_uri = URIRef(
            _encode_http_uri(record.get("provenance_uri") or f"https://pinakes.ibict.br/activity/{record['id']}")
        )
        g.add((activity_uri, RDF.type, PROV.Activity))
        g.add((doc, PROV.wasGeneratedBy, activity_uri))
        if record.get("source_reference"):
            g.add((activity_uri, DCTERMS.source, Literal(record["source_reference"])))

        for author in record.get("authors", []):
            name = author.get("name", "").replace(" ", "_") or "autor_desconhecido"
            author_uri = URIRef(EX + name)
            g.add((author_uri, RDF.type, FOAF.Person))
            g.add((author_uri, FOAF.name, Literal(author.get("name", "Autor Desconhecido"))))
            if author.get("orcid"):
                g.add((author_uri, PINAKES.orcid, Literal(author["orcid"])))
            if affiliation := author.get("affiliation"):
                g.add((author_uri, SCHEMA.affiliation, Literal(affiliation)))
            g.add((doc, DCTERMS.creator, author_uri))

    return g
