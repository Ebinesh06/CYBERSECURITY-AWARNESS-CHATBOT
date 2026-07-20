from typing import Tuple, List
from Backend.vector_db import hybrid_search


def retrieve_context(query: str) -> Tuple[str, List[tuple]]:
    """Retrieve context using hybrid search and return combined context and raw results."""
    retrieved_results = hybrid_search(query)
    context = "\n\n".join(doc for doc, score in retrieved_results)
    return context, retrieved_results
