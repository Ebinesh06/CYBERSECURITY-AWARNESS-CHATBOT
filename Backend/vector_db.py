from rank_bm25 import BM25Okapi
from flashrank import Ranker
from pydantic import BaseModel
import chromadb
# 5. ChromaDB - Initialize with fallback
try:
    
    from chromadb.utils import embedding_functions

    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

    chroma_client = chromadb.PersistentClient(path="./chroma_db")

    intelligence_collection = chroma_client.get_collection(
        name="cyber_intelligence",
        embedding_function=sentence_transformer_ef
    )
    # --- PHASE 2 STARTUP: KEYWORD INDEXING ---
    all_data = intelligence_collection.get()
    documents = all_data['documents']
    metadatas = all_data['metadatas']
    
    tokenized_corpus = [doc.lower().split(" ") for doc in documents]
    bm25 = BM25Okapi(tokenized_corpus)
except Exception as e:
    print(f"Warning: ChromaDB initialization failed: {e}")
    print("Proceeding with authentication endpoints only")
    chroma_client = None
    intelligence_collection = None
    all_data = {'documents': [], 'metadatas': []}
    documents = []
    metadatas = []
    tokenized_corpus = []
    bm25 = None

ranker = Ranker(model_name="ms-marco-TinyBERT-L-2-v2", cache_dir="./models")

print(f"SUCCESS: Indexed {len(documents)} vulnerabilities for Precision Search.")

# 4. Request models
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default_user"

def hybrid_search(query, top_k=10):

    vector_results = intelligence_collection.query(
        query_texts=[query],
        n_results=top_k
    )

    ...

    ranked_docs = sorted(
        fusion_results.items(),
        key=lambda x: x[1],
        reverse=True
    )

    print("\n========== HYBRID SEARCH ==========")
    print(f"Query: {query}")

    for i, (doc, score) in enumerate(ranked_docs[:top_k]):

        print(f"\nResult {i+1}")
        print(f"Fusion Score : {score:.4f}")

        # Find metadata
        try:
            idx = documents.index(doc)
            print(f"Source : {metadatas[idx]}")
        except ValueError:
            print("Source : Unknown")

        print(doc[:300])
        print("----------------------------------")

    return ranked_docs[:top_k]
