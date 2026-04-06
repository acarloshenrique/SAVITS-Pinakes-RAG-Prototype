from src.agents.graph_agent import run_graph_query
from src.rag.context_builder import build_context
from src.agents.reasoning_agent import generate_answer

def answer_query(graph, user_query):

    sparql = """
    SELECT ?title ?author
    WHERE {
        ?paper <http://purl.org/dc/terms/title> ?title .
        ?paper <http://purl.org/dc/terms/creator> ?author .
    }
    LIMIT 5
    """

    results = run_graph_query(graph, sparql)

    context = build_context(results)

    answer = generate_answer(context, user_query)

    return answer, results