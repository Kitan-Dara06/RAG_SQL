"""
Stress testing and performance benchmarking for SQL_RAG project.
"""
import time
import concurrent.futures
import threading
from unittest.mock import patch

import pytest


class TestConcurrentQueries:
    """Test suite for concurrent query handling."""
    
    def test_concurrent_schema_extraction(self, test_db):
        """Test concurrent schema extraction doesn't cause issues."""
        from sql_rag import get_database_schema
        
        def extract_schema():
            return get_database_schema(test_db)
        
        # Run 10 concurrent extractions
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(extract_schema) for _ in range(10)]
            results = [f.result() for f in futures]
        
        # All should succeed and return same results
        assert all(len(r) == 3 for r in results), "All should extract 3 tables"
        assert all(r == results[0] for r in results), "All results should be identical"
    
    def test_concurrent_sql_execution(self, test_db):
        """Test concurrent SQL execution."""
        from generator import execute_sql
        
        def run_query():
            with patch('generator.DB_PATH', test_db):
                return execute_sql("SELECT COUNT(*) FROM users;")
        
        # Run 20 concurrent queries
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(run_query) for _ in range(20)]
            results = [f.result() for f in futures]
        
        # All should succeed
        assert all(r["success"] for r in results), "All queries should succeed"
    
    def test_concurrent_vector_search(self, chroma_client, embedding_function):
        """Test concurrent vector database searches."""
        from generator import get_relevant_schema
        
        # Setup collection
        collection = chroma_client.get_or_create_collection(
            name="schema_index",
            embedding_function=embedding_function
        )
        collection.add(
            documents=["CREATE TABLE users (id INTEGER);"],
            ids=["users"]
        )
        
        def search():
            with patch('generator.collection', collection):
                return get_relevant_schema("users")
        
        # Run 15 concurrent searches
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(search) for _ in range(15)]
            results = [f.result() for f in futures]
        
        # All should return results
        assert all(len(r) > 0 for r in results), "All searches should return results"
    
    @pytest.mark.benchmark
    def test_high_concurrency_stress(self, test_db):
        """Stress test with 50 concurrent queries."""
        from generator import execute_sql
        
        queries = [
            "SELECT * FROM users;",
            "SELECT * FROM products;",
            "SELECT * FROM orders;",
            "SELECT COUNT(*) FROM users;",
            "SELECT COUNT(*) FROM products;",
        ]
        
        def run_random_query(query_idx):
            query = queries[query_idx % len(queries)]
            with patch('generator.DB_PATH', test_db):
                return execute_sql(query)
        
        start_time = time.time()
        
        # Run 50 concurrent queries
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(run_random_query, i) for i in range(50)]
            results = [f.result() for f in futures]
        
        end_time = time.time()
        duration = end_time - start_time
        
        # All should succeed
        success_count = sum(1 for r in results if r["success"])
        assert success_count >= 45, f"At least 45/50 should succeed, got {success_count}"
        
        # Should complete in reasonable time (< 10 seconds)
        assert duration < 10, f"Should complete in < 10s, took {duration:.2f}s"
    
    def test_connection_pool_exhaustion(self, test_db):
        """Test that connection pool doesn't get exhausted."""
        from generator import execute_sql
        
        # Run many sequential queries to test connection cleanup
        for i in range(100):
            with patch('generator.DB_PATH', test_db):
                result = execute_sql("SELECT * FROM users;")
            
            assert result["success"], f"Query {i} should succeed"


class TestLargeSchemaHandling:
    """Test suite for handling large database schemas."""
    
    def test_many_tables_schema_extraction(self):
        """Test extraction of schema with many tables."""
        import sqlite3
        import tempfile
        import os
        from sql_rag import get_database_schema
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create 50 tables
            for i in range(50):
                cursor.execute(f"""
                    CREATE TABLE table_{i} (
                        id INTEGER PRIMARY KEY,
                        name TEXT,
                        value REAL
                    );
                """)
            
            conn.commit()
            conn.close()
            
            # Extract schema
            start_time = time.time()
            schemas = get_database_schema(db_path)
            duration = time.time() - start_time
            
            assert len(schemas) == 50, "Should extract all 50 tables"
            assert duration < 2.0, f"Should extract quickly, took {duration:.2f}s"
        
        finally:
            os.unlink(db_path)
    
    def test_large_table_query(self, test_db):
        """Test querying tables with many rows."""
        import sqlite3
        from generator import execute_sql
        
        # Add many rows to test database
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        
        # Insert 1000 users
        for i in range(1000):
            cursor.execute(
                "INSERT INTO users (name, email) VALUES (?, ?)",
                (f"User{i}", f"user{i}@test.com")
            )
        
        conn.commit()
        conn.close()
        
        # Query all users
        start_time = time.time()
        with patch('generator.DB_PATH', test_db):
            result = execute_sql("SELECT * FROM users;")
        duration = time.time() - start_time
        
        assert result["success"], "Should handle large result set"
        assert len(result["data"]) >= 1000, "Should return all rows"
        assert duration < 1.0, f"Should query quickly, took {duration:.2f}s"


class TestComplexQueryPerformance:
    """Test suite for complex query performance."""
    
    def test_multi_join_query(self, test_db):
        """Test performance of multi-table JOIN queries."""
        from generator import execute_sql
        
        sql = """
        SELECT u.name, p.name, o.total
        FROM users u
        JOIN orders o ON u.id = o.user_id
        JOIN products p ON 1=1
        LIMIT 100;
        """
        
        start_time = time.time()
        with patch('generator.DB_PATH', test_db):
            result = execute_sql(sql)
        duration = time.time() - start_time
        
        assert result["success"], "Complex JOIN should succeed"
        assert duration < 0.5, f"Should execute quickly, took {duration:.2f}s"
    
    def test_aggregation_query(self, test_db):
        """Test performance of aggregation queries."""
        from generator import execute_sql
        
        sql = """
        SELECT user_id, COUNT(*) as order_count, SUM(total) as total_spent
        FROM orders
        GROUP BY user_id
        HAVING total_spent > 0
        ORDER BY total_spent DESC;
        """
        
        start_time = time.time()
        with patch('generator.DB_PATH', test_db):
            result = execute_sql(sql)
        duration = time.time() - start_time
        
        assert result["success"], "Aggregation should succeed"
        assert duration < 0.3, f"Should execute quickly, took {duration:.2f}s"
    
    def test_subquery_performance(self, test_db):
        """Test performance of queries with subqueries."""
        from generator import execute_sql
        
        sql = """
        SELECT name, email
        FROM users
        WHERE id IN (
            SELECT user_id FROM orders WHERE total > 100
        );
        """
        
        start_time = time.time()
        with patch('generator.DB_PATH', test_db):
            result = execute_sql(sql)
        duration = time.time() - start_time
        
        assert result["success"], "Subquery should succeed"
        assert duration < 0.3, f"Should execute quickly, took {duration:.2f}s"


class TestVectorDatabasePerformance:
    """Test suite for vector database performance."""
    
    def test_large_collection_search(self, chroma_client, embedding_function):
        """Test search performance with large collection."""
        from generator import get_relevant_schema
        
        # Create collection with 100 schemas
        collection = chroma_client.get_or_create_collection(
            name="schema_index",
            embedding_function=embedding_function
        )
        
        schemas = []
        ids = []
        for i in range(100):
            schema = f"CREATE TABLE table_{i} (id INTEGER, name TEXT, value REAL);"
            schemas.append(schema)
            ids.append(f"table_{i}")
        
        collection.add(documents=schemas, ids=ids)
        
        # Perform search
        start_time = time.time()
        with patch('generator.collection', collection):
            results = get_relevant_schema("Find tables with user data")
        duration = time.time() - start_time
        
        assert len(results) > 0, "Should return results"
        assert duration < 1.0, f"Search should be fast, took {duration:.2f}s"
    
    def test_repeated_searches(self, chroma_client, embedding_function):
        """Test performance of repeated searches."""
        from generator import get_relevant_schema
        
        collection = chroma_client.get_or_create_collection(
            name="schema_index",
            embedding_function=embedding_function
        )
        collection.add(
            documents=["CREATE TABLE users (id INTEGER);"],
            ids=["users"]
        )
        
        # Perform 50 searches
        start_time = time.time()
        with patch('generator.collection', collection):
            for _ in range(50):
                get_relevant_schema("users")
        duration = time.time() - start_time
        
        assert duration < 5.0, f"50 searches should complete quickly, took {duration:.2f}s"


class TestMemoryUsage:
    """Test suite for memory usage patterns."""
    
    def test_large_result_set_memory(self, test_db):
        """Test memory handling with large result sets."""
        import sqlite3
        from generator import execute_sql
        
        # Add many rows
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        for i in range(5000):
            cursor.execute(
                "INSERT INTO users (name, email) VALUES (?, ?)",
                (f"User{i}", f"user{i}@test.com")
            )
        conn.commit()
        conn.close()
        
        # Query all - should not crash
        with patch('generator.DB_PATH', test_db):
            result = execute_sql("SELECT * FROM users;")
        
        assert result["success"], "Should handle large result set"
        assert len(result["data"]) >= 5000, "Should return all rows"
    
    def test_repeated_operations_no_leak(self, test_db):
        """Test that repeated operations don't leak memory."""
        from generator import execute_sql
        
        # Run many operations
        for _ in range(200):
            with patch('generator.DB_PATH', test_db):
                execute_sql("SELECT * FROM users;")
        
        # If there's a memory leak, this would crash or slow down significantly
        # The fact that it completes is a basic check
        assert True, "Should complete without memory issues"


class TestEndToEndPerformance:
    """Test suite for end-to-end performance."""
    
    def test_full_rag_pipeline_performance(self, test_db, chroma_client, embedding_function, mock_env):
        """Test performance of complete RAG pipeline."""
        from generator import run_agent
        
        # Setup
        collection = chroma_client.get_or_create_collection(
            name="schema_index",
            embedding_function=embedding_function
        )
        collection.add(
            documents=["CREATE TABLE users (id INTEGER, name TEXT, email TEXT);"],
            ids=["users"]
        )
        
        mock_client = MockOpenAIClient(responses=["SELECT * FROM users;"])
        
        # Run full pipeline
        start_time = time.time()
        with patch('generator.collection', collection), \
             patch('generator.client', mock_client), \
             patch('generator.DB_PATH', test_db):
            result = run_agent("List all users")
        duration = time.time() - start_time
        
        assert result is not None, "Should return result"
        assert result["success"], "Should succeed"
        assert duration < 2.0, f"Full pipeline should be fast, took {duration:.2f}s"
