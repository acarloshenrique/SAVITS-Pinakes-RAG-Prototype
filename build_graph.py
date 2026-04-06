from src.curation.pipeline import run_pipeline
from src.graph.graph_builder import build_graph

docs = run_pipeline()

g = build_graph(docs)

g.serialize("pinakes_graph.ttl")

print("Triplas no grafo:", len(g))