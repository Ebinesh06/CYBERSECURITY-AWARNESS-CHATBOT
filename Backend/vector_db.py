try:
    from rank_bm25 import BM25Okapi
except Exception:
    BM25Okapi = None

try:
    from flashrank import Ranker, RerankRequest
except Exception:
    Ranker = None
    RerankRequest = None
# pydantic may not be available in minimal import environments; provide a lightweight fallback
try:
    from pydantic import BaseModel
except Exception:
    class BaseModel:  # type: ignore
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)

# chromadb may not be installed in minimal environments; guard its import
try:
    import chromadb
except Exception:
    chromadb = None
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

if Ranker is not None:
    try:
        ranker = Ranker(model_name="ms-marco-TinyBERT-L-2-v2", cache_dir="./models")
    except Exception as e:
        print(f"Warning: FlashRank Ranker initialization failed: {e}")
        ranker = None
else:
    ranker = None
print(f"SUCCESS: Indexed {len(documents)} vulnerabilities for Precision Search.")

# 4. Request models
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default_user"

def hybrid_search(query, top_k=10):

    # Defensive early exits
    if intelligence_collection is None:
        return []

    try:
        vector_results = intelligence_collection.query(
            query_texts=[query],
            n_results=top_k,
        )
    except Exception:
        vector_results = {"documents": [[]], "distances": [[]]}

    vector_docs = vector_results.get("documents", [[]])[0]
    vector_distances = vector_results.get("distances", [[]])[0]

    # BM25 scores (global corpus)
    if bm25 is not None and tokenized_corpus:
        tokenized_query = query.lower().split()
        try:
            bm25_scores_all = bm25.get_scores(tokenized_query)
        except Exception:
            bm25_scores_all = [0.0] * len(tokenized_corpus)
        max_bm25 = max(bm25_scores_all) if bm25_scores_all else 0.0
    else:
        bm25_scores_all = []
        max_bm25 = 0.0

    fusion_results = {}

    for idx_in_res, doc in enumerate(vector_docs):
        # vector similarity from returned distances (smaller distance -> higher sim)
        vec_sim = 0.0
        if idx_in_res < len(vector_distances):
            try:
                dist = float(vector_distances[idx_in_res])
                vec_sim = 1.0 / (1.0 + dist)
            except Exception:
                vec_sim = 0.0

        # BM25 normalized score for this document (if present in our corpus)
        bm25_norm = 0.0
        try:
            corpus_idx = documents.index(doc)
            raw_bm25 = bm25_scores_all[corpus_idx] if corpus_idx < len(bm25_scores_all) else 0.0
            if max_bm25 > 0:
                bm25_norm = raw_bm25 / max_bm25
        except Exception:
            bm25_norm = 0.0

        # Fusion: weighted sum (tunable)
        fused_score = 0.6 * vec_sim + 0.4 * bm25_norm
        fusion_results[doc] = fused_score

    # Optional: use FlashRank ranker to refine top candidates if available
    try:
        if ranker is not None and fusion_results:
            candidates = list(fusion_results.keys())[: max(50, top_k)]
            # FlashRank API varies; try common method names conservatively
            if hasattr(ranker, "rerank"):
                rr = ranker.rerank(query, candidates)
            elif hasattr(ranker, "rank"):
                rr = ranker.rank(query, candidates)
            else:
                rr = None

            if isinstance(rr, (list, tuple)) and len(rr) == len(candidates):
                max_rr = max(rr) if max(rr) > 0 else 1.0
                for cand, score in zip(candidates, rr):
                    # blend reranker score into fusion
                    fusion_results[cand] = fusion_results.get(cand, 0.0) * 0.6 + (score / max_rr) * 0.4
    except Exception:
        pass

    # Sort and return top_k
    ranked_docs = sorted(fusion_results.items(), key=lambda x: x[1], reverse=True)

    print("\n========== HYBRID SEARCH ==========")
    print(f"Query: {query}")

    for i, (doc, score) in enumerate(ranked_docs[:top_k]):
        print(f"\nResult {i+1}")
        print(f"Fusion Score : {score:.4f}")
        try:
            idx = documents.index(doc)
            print(f"Source : {metadatas[idx]}")
        except Exception:
            print("Source : Unknown")
        print(doc[:300])
        print("----------------------------------")

    return ranked_docs[:top_k]
