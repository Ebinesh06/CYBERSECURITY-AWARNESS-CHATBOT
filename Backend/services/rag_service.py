from typing import List
from vector_db import hybrid_search


def retrieve_context(query: str) -> tuple[str, list[tuple[str, float]]]:
    """Retrieve context using hybrid search and return combined context and raw results."""
    retrieved_results = hybrid_search(query)
    context = "\n\n".join(doc for doc, score in retrieved_results)
    return context, retrieved_results
