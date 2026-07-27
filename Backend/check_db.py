import chromadb
from config import CHROMA_PATH

client = chromadb.PersistentClient(path=str(CHROMA_PATH))

print("Collections:")
for c in client.list_collections():
    print(c.name)