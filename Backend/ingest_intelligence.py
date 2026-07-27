import logging
from pathlib import Path

import chromadb
import requests
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import CHROMA_PATH, MODEL_NAME

logger = logging.getLogger(__name__)
DATA_DIR = Path("./data")
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=MODEL_NAME)
client = chromadb.PersistentClient(path=str(CHROMA_PATH))
collection = client.get_or_create_collection(name="cyber_intelligence", embedding_function=sentence_transformer_ef)
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200, separators=["\n\n", "\n", " ", ""])


def ingest_local_files() -> None:
    """Read local text files and add their chunks to ChromaDB."""
    logger.info("Fetching local knowledge base")
    if not DATA_DIR.exists():
        logger.warning("Data folder not found: %s", DATA_DIR)
        return
    for file in DATA_DIR.glob("*.txt"):
        chunks = text_splitter.split_text(file.read_text(encoding="utf-8"))
        logger.info("Processing %s (%d chunks)", file.name, len(chunks))
        for index, chunk in enumerate(chunks):
            collection.add(documents=[chunk], metadatas=[{"source": "Local File", "filename": file.name}], ids=[f"local_{file.name}_{index}"])
    logger.info("Local files ingested successfully")


def ingest_cisa_kev() -> None:
    """Fetch CISA KEV data and add the first 100 vulnerabilities to ChromaDB."""
    logger.info("Fetching live data from CISA")
    response = requests.get("https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json")
    response.raise_for_status()
    vulnerabilities = response.json().get("vulnerabilities", [])
    logger.info("Processing %d vulnerabilities", len(vulnerabilities))
    for vulnerability in vulnerabilities[:100]:
        content = f"CVE ID: {vulnerability['cveID']}\nVendor: {vulnerability['vendorProject']}\nProduct: {vulnerability['product']}\nDescription: {vulnerability['shortDescription']}\nRemediation: {vulnerability['requiredAction']}"
        metadata = {"source": "CISA KEV", "cve_id": vulnerability["cveID"], "vendor": vulnerability["vendorProject"]}
        for index, chunk in enumerate(text_splitter.split_text(content)):
            collection.add(documents=[chunk], metadatas=[metadata], ids=[f"{vulnerability['cveID']}_{index}"])
    logger.info("CISA data ingested successfully")


if __name__ == "__main__":
    print("Starting ingestion...")

    CHROMA_PATH.mkdir(parents=True, exist_ok=True)

    ingest_local_files()
    print("Local ingestion finished")

    ingest_cisa_kev()
    print("CISA ingestion finished")

    print("Collections:")
    for c in client.list_collections():
        print(c.name)

    print("Done")
print(CHROMA_PATH)