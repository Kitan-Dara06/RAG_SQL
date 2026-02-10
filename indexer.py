"""
Schema indexer for SQL_RAG.
Extracts database schema and indexes it into ChromaDB for vector search.
"""
import re

import chromadb
from chromadb.utils import embedding_functions

from sql_rag import get_database_schema
from config import CHROMA_DB_PATH, EMBEDDING_MODEL, DB_TYPE
from logger import get_logger

logger = get_logger(__name__)

# Extract schemas from database
logger.info("Extracting schemas from %s database", DB_TYPE)
schemas = get_database_schema()

# Generate IDs from table names
ids = []
for sql in schemas:
    pattern = r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([^\s\(]+)"
    match = re.search(pattern, sql, re.IGNORECASE)
    
    if match:
        table_name = match.group(1).strip('"')
        ids.append(table_name)
    else:
        ids.append(f"table_{len(ids)}")

logger.info("Generated IDs: %s", ids)

# Initialize ChromaDB
client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# Delete old collection to avoid conflicts
try:
    client.delete_collection(name="schema_index")
    logger.info("Deleted old 'schema_index' collection")
except ValueError:
    logger.info("No existing 'schema_index' collection to delete")

# Create new collection with embeddings
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL
)
collection = client.get_or_create_collection(
    name="schema_index", embedding_function=sentence_transformer_ef
)

# Index schemas
collection.add(documents=schemas, ids=ids)
logger.info("Indexed %d tables into 'schema_index'", len(schemas))

print(f" Successfully indexed {len(schemas)} tables from {DB_TYPE} database")
print(f"Tables: {ids}")
