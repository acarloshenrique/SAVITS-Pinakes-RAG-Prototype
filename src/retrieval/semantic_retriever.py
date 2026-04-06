from rdflib import Graph
from rdflib.namespace import FOAF, DCTERMS

GRAPH_PATH = "pinakes_graph.ttl"


def load_graph():
    """
    Carrega o grafo RDF.
    """
    g = Graph()
    g.parse(GRAPH_PATH)
    return g


def get_all_authors(graph, limit=50):
    """
    Retorna autores do grafo.
    """

    query = f"""
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>

    SELECT DISTINCT ?name
    WHERE {{
        ?a a foaf:Person .
        ?a foaf:name ?name .
    }}
    LIMIT {limit}
    """

    results = graph.query(query)

    authors = [str(r.name) for r in results]

    return authors


def get_documents(graph, limit=20):
    """
    Retorna títulos de documentos.
    """

    query = f"""
    PREFIX dcterms: <http://purl.org/dc/terms/>

    SELECT ?title
    WHERE {{
        ?doc dcterms:title ?title .
    }}
    LIMIT {limit}
    """

    results = graph.query(query)

    docs = [str(r.title) for r in results]

    return docs


def get_author_documents(graph, limit=20):
    """
    Retorna pares autor-documento.
    """

    query = f"""
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX dcterms: <http://purl.org/dc/terms/>

    SELECT ?author ?title
    WHERE {{
        ?doc dcterms:creator ?a .
        ?doc dcterms:title ?title .
        ?a foaf:name ?author .
    }}
    LIMIT {limit}
    """

    results = graph.query(query)

    pairs = [(str(r.author), str(r.title)) for r in results]

    return pairs


if __name__ == "__main__":

    g = load_graph()

    print("Triplas no grafo:", len(g))

    authors = get_all_authors(g)

    print("\nAutores encontrados:")
    for a in authors:
        print("-", a)

    docs = get_documents(g)

    print("\nDocumentos encontrados:")
    for d in docs:
        print("-", d)

    pairs = get_author_documents(g)

    print("\nAutor → Documento:")
    for a, d in pairs:
        print(a, "→", d)