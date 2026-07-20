import logging

import chromadb

from config import CHROMA_PATH

logger = logging.getLogger(__name__)
client = chromadb.PersistentClient(path=str(CHROMA_PATH))
collection = client.get_collection(name="cyber_intelligence")
logger.info("Total items in database: %d", collection.count())
