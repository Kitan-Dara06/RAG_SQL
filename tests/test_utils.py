"""
Shared test utilities and fixtures for SQL_RAG testing.
"""
import os
import sqlite3
import tempfile
from typing import Dict, List

import pytest


def create_test_database(db_path: str) -> None:
    """Create a test database with sample schema."""
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


@pytest.fixture
def test_db():
    """Fixture that creates a temporary test database."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    create_test_database(db_path)
    yield db_path
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def sample_questions():
    """Fixture providing sample test questions."""
    return [
        "How many users are there?",
        "What is the most expensive product?",
        "Who made the largest order?",
        "List all products",
        "What is the total revenue?",
    ]


@pytest.fixture
def expected_sql_patterns():
    """Fixture providing expected SQL patterns for validation."""
    return {
        "count_users": ["SELECT", "COUNT", "users"],
        "max_price": ["SELECT", "MAX", "price", "products"],
        "largest_order": ["SELECT", "MAX", "total", "orders"],
        "list_products": ["SELECT", "products"],
        "total_revenue": ["SELECT", "SUM", "total", "orders"],
    }


def validate_sql_syntax(sql: str) -> bool:
    """Validate basic SQL syntax."""
    sql_upper = sql.upper().strip()
    
    # Must start with SELECT for read-only queries
    if not sql_upper.startswith("SELECT"):
        return False
    
    # Should not contain forbidden operations
    forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "CREATE", "ALTER"]
    for word in forbidden:
        if word in sql_upper:
            return False
    
    return True


def measure_performance(func):
    """Decorator to measure function performance."""
    import time
    
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        return result, end - start
    
    return wrapper
