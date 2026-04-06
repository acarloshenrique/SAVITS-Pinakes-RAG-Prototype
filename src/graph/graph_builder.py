from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, DCTERMS, FOAF

EX = Namespace("http://example.org/")

def build_graph(records):

    g = Graph()

    for r in records:

        doc = URIRef(EX + r["title"].replace(" ", "_"))

        g.add((doc, RDF.type, EX.Document))

        g.add((doc, DCTERMS.title, Literal(r["title"])))

        if r["year"]:
            g.add((doc, DCTERMS.issued, Literal(r["year"])))

        for author in r["authors"]:

            author_uri = URIRef(EX + author.replace(" ", "_"))

            g.add((author_uri, RDF.type, FOAF.Person))
            g.add((author_uri, FOAF.name, Literal(author)))

            g.add((doc, DCTERMS.creator, author_uri))

    return g