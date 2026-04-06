def build_context(results):

    context = ""

    for row in results:
        context += " | ".join(row) + "\n"

    return context