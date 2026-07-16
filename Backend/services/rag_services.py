from vector_db import hybrid_search


def retrieve_context(query: str):

    retrieved_results = hybrid_search(query)

    context = "\n\n".join(
        doc for doc, score in retrieved_results
    )

    return context, retrieved_results