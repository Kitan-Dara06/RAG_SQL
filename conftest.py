"""
Pytest configuration and shared fixtures.
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path

import pytest
import chromadb
from chromadb.utils import embedding_functions

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session")
def test_chroma_path():
    """Create a temporary ChromaDB directory for testing."""
    temp_dir = tempfile.mkdtemp(prefix="test_chroma_")
    yield temp_dir
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def chroma_client(test_chroma_path):
    """Provide a ChromaDB client with test collection."""
    client = chromadb.PersistentClient(path=test_chroma_path)
    
    # Clean up any existing test collections
    try:
        client.delete_collection("test_schema_index")
    except:
        pass
    
    yield client
    
    # Cleanup
    try:
        client.delete_collection("test_schema_index")
    except:
        pass


@pytest.fixture
def embedding_function():
    """Provide the sentence transformer embedding function."""
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )


@pytest.fixture
def mock_env(monkeypatch):
    """Mock environment variables without reading .env file."""
    monkeypatch.setenv("OPENAI_KEY", "test-key-12345")
    return {"OPENAI_KEY": "test-key-12345"}


@pytest.fixture(autouse=True)
def reset_modules():
    """Reset imported modules between tests to avoid state pollution."""
    yield
    # Remove project modules from sys.modules to force reimport
    modules_to_remove = [
        mod for mod in sys.modules.keys() 
        if mod.startswith(('sql_rag', 'generator', 'indexer', 'setup_db'))
    ]
    for mod in modules_to_remove:
        del sys.modules[mod]


@pytest.fixture
def test_db():
    """Fixture that creates a temporary test database."""
    import sqlite3
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    # Create test database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL
        );
    """)
    
    cursor.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL NOT NULL
        );
    """)
    
    cursor.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            total REAL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    
    # Insert test data
    cursor.execute("INSERT INTO users (name, email) VALUES ('Alice', 'alice@test.com');")
    cursor.execute("INSERT INTO users (name, email) VALUES ('Bob', 'bob@test.com');")
    cursor.execute("INSERT INTO products (name, price) VALUES ('Laptop', 1000.00);")
    cursor.execute("INSERT INTO products (name, price) VALUES ('Mouse', 25.00);")
    cursor.execute("INSERT INTO orders (user_id, total) VALUES (1, 1025.00);")
    cursor.execute("INSERT INTO orders (user_id, total) VALUES (2, 25.00);")
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)

