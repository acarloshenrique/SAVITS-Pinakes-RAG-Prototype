def run_graph_query(graph, query):

    results = graph.query(query)

    output = []

    for row in results:
        output.append([str(value) for value in row])

    return output