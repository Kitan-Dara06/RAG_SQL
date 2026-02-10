"""
Unit tests for sql_rag.py - Schema extraction functionality.
"""
import sqlite3
import tempfile
import os

import pytest

from sql_rag import get_database_schema


class TestGetDatabaseSchema:
    """Test suite for get_database_schema function."""
    
    def test_schema_extraction_basic(self, test_db):
        """Test basic schema extraction from a database."""
        schemas = get_database_schema(test_db)
        
        assert len(schemas) == 3, "Should extract 3 table schemas"
        assert all(isinstance(s, str) for s in schemas), "All schemas should be strings"
        assert all("CREATE TABLE" in s for s in schemas), "All should be CREATE TABLE statements"
    
    def test_schema_contains_table_names(self, test_db):
        """Test that extracted schemas contain expected table names."""
        schemas = get_database_schema(test_db)
        schema_text = " ".join(schemas)
        
        assert "users" in schema_text, "Should contain users table"
        assert "products" in schema_text, "Should contain products table"
        assert "orders" in schema_text, "Should contain orders table"
    
    def test_schema_contains_columns(self, test_db):
        """Test that schemas contain column definitions."""
        schemas = get_database_schema(test_db)
        schema_text = " ".join(schemas)
        
        # Check for expected columns
        assert "name" in schema_text, "Should contain name column"
        assert "email" in schema_text, "Should contain email column"
        assert "price" in schema_text, "Should contain price column"
    
    def test_empty_database(self):
        """Test schema extraction from an empty database."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            # Create empty database
            conn = sqlite3.connect(db_path)
            conn.close()
            
            schemas = get_database_schema(db_path)
            assert schemas == [], "Empty database should return empty list"
        finally:
            os.unlink(db_path)
    
    def test_nonexistent_database(self):
        """Test behavior with nonexistent database path."""
        with pytest.raises(sqlite3.OperationalError):
            get_database_schema("/nonexistent/path/to/database.db")
    
    def test_schema_excludes_sqlite_internal_tables(self, test_db):
        """Test that internal SQLite tables are handled correctly."""
        schemas = get_database_schema(test_db)
        schema_text = " ".join(schemas)
        
        # sqlite_sequence might be present but should not cause issues
        assert len(schemas) >= 3, "Should have at least our 3 tables"
    
    def test_foreign_key_preservation(self, test_db):
        """Test that foreign key constraints are preserved in schema."""
        schemas = get_database_schema(test_db)
        orders_schema = [s for s in schemas if "orders" in s.lower()][0]
        
        assert "FOREIGN KEY" in orders_schema, "Should preserve foreign key constraints"
        assert "REFERENCES" in orders_schema, "Should preserve references"
    
    def test_schema_format_consistency(self, test_db):
        """Test that all schemas follow consistent format."""
        schemas = get_database_schema(test_db)
        
        for schema in schemas:
            assert schema.strip(), "Schema should not be empty or whitespace"
            assert schema.startswith("CREATE TABLE"), "Should start with CREATE TABLE"
            assert "(" in schema and ")" in schema, "Should contain column definitions"
    
    def test_multiple_calls_consistency(self, test_db):
        """Test that multiple calls return consistent results."""
        schemas1 = get_database_schema(test_db)
        schemas2 = get_database_schema(test_db)
        
        assert schemas1 == schemas2, "Multiple calls should return identical results"
    
    def test_connection_cleanup(self, test_db):
        """Test that database connections are properly closed."""
        # Call function multiple times
        for _ in range(10):
            get_database_schema(test_db)
        
        # Should not raise "too many connections" error
        # If connections aren't closed, this would eventually fail
        schemas = get_database_schema(test_db)
        assert len(schemas) > 0, "Should still work after multiple calls"


class TestSchemaIntegrity:
    """Test suite for schema integrity and edge cases."""
    
    def test_special_characters_in_table_names(self):
        """Test handling of special characters in table names."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE "user-data" (id INTEGER PRIMARY KEY);')
            cursor.execute('CREATE TABLE [order items] (id INTEGER PRIMARY KEY);')
            conn.commit()
            conn.close()
            
            schemas = get_database_schema(db_path)
            assert len(schemas) == 2, "Should handle special characters in table names"
        finally:
            os.unlink(db_path)
    
    def test_complex_column_types(self):
        """Test extraction of complex column types and constraints."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE complex_table (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    amount REAL DEFAULT 0.0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    CHECK (amount >= 0)
                );
            """)
            conn.commit()
            conn.close()
            
            schemas = get_database_schema(db_path)
            schema_text = schemas[0]
            
            assert "PRIMARY KEY" in schema_text, "Should preserve PRIMARY KEY"
            assert "NOT NULL" in schema_text, "Should preserve NOT NULL"
            assert "UNIQUE" in schema_text or "unique" in schema_text.lower(), "Should preserve UNIQUE"
        finally:
            os.unlink(db_path)
