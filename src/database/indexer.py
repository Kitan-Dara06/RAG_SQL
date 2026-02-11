"""
Schema indexing for SQL_RAG using ChromaDB.
Provides utilities for indexing database schemas into vector database.
"""
import chromadb
from chromadb.utils import embedding_functions
from src.utils.config import CHROMA_DB_PATH, EMBEDDING_MODEL
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Initialize sentence transformer embedding function (can be imported by other modules)
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL
)

logger.info("Indexer module loaded with embedding model: %s", EMBEDDING_MODEL)
