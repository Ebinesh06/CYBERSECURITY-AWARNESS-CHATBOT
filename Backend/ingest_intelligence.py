import os
from pathlib import Path
import requests
import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 1. Define Paths
DATA_DIR = "./data"
DB_DIR = "./chroma_db" # Use the unified chroma_db folder

# 2. Set a Unified Embedding Model
# We explicitly define the embedding function so both local files and API data 
# are mathematically mapped the exact same way.
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

# 3. Connect to the unified ChromaDB
client = chromadb.PersistentClient(path=DB_DIR)
collection = client.get_or_create_collection(
    name="cyber_intelligence",
    embedding_function=sentence_transformer_ef # Apply unified embeddings
)

# Initialize standard text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", " ", ""]
)

def ingest_local_files():
    """Reads local .txt files and adds them to ChromaDB"""
    print("Fetching local knowledge base...")
    path = Path(DATA_DIR)
    
    if not path.exists():
        print("❌ data folder not found")
        return

    for file in path.glob("*.txt"):
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        metadata = {
            "source": "Local File",
            "filename": file.name
        }
        
        chunks = text_splitter.split_text(content)
        print(f"Processing {file.name} ({len(chunks)} chunks)...")
        
        # Add to the unified collection
        for i, chunk in enumerate(chunks):
            collection.add(
                documents=[chunk],
                metadatas=[metadata],
                ids=[f"local_{file.name}_{i}"]
            )
    print("✅ Local files ingested successfully.")

def ingest_cisa_kev():
    """Fetches live CVE data and adds it to ChromaDB"""
    print("Fetching live data from CISA...")
    url = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
    response = requests.get(url)
    data = response.json()
    
    vulnerabilities = data.get("vulnerabilities", [])
    print(f"Processing {len(vulnerabilities)} vulnerabilities...")
    
    # Process only top 100 for speed, just like the original script
    for vuln in vulnerabilities[:100]: 
        content = f"CVE ID: {vuln['cveID']}\nVendor: {vuln['vendorProject']}\nProduct: {vuln['product']}\nDescription: {vuln['shortDescription']}\nRemediation: {vuln['requiredAction']}"
        
        metadata = {
            "source": "CISA KEV",
            "cve_id": vuln['cveID'],
            "vendor": vuln['vendorProject']
        }
        
        chunks = text_splitter.split_text(content)
        
        for i, chunk in enumerate(chunks):
            collection.add(
                documents=[chunk],
                metadatas=[metadata],
                ids=[f"{vuln['cveID']}_{i}"]
            )
    print("✅ CISA data ingested successfully.")

if __name__ == "__main__":
    os.makedirs(DB_DIR, exist_ok=True)
    
    # Run both ingestion pipelines
    print("--- Starting Unified Intelligence Ingestion ---")
    ingest_local_files()
    ingest_cisa_kev()
    print("--- Ingestion Complete ---")