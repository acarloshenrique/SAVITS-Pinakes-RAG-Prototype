from src.curation.pipeline import run_pipeline
from src.graph.graph_builder import build_graph
from src import semantic_integration

docs = run_pipeline()

g = build_graph(docs)

g.serialize("pinakes_graph_enriched.ttl")

semantic_integration.generate_graph("data/raw_data.json", "pinakes_graph.ttl")

print("Triplas no grafo enriquecido:", len(g))
