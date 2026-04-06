from rdflib import Graph

def load_graph(path="pinakes_graph.ttl"):

    graph = Graph()
    graph.parse(path, format="turtle")

    return graph