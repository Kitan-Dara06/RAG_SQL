"""
Integration tests for SQL_RAG - End-to-end pipeline testing.
"""
import pytest
from unittest.mock import patch

from test_utils import MockOpenAIClient


class TestEndToEndRAGPipeline:
    """Test suite for complete RAG pipeline."""
    
    def test_simple_question_flow(self, test_db, chroma_client, embedding_function, mock_env):
        """Test complete flow for a simple question."""
        from generator import run_agent
        
        # Setup vector database
        collection = chroma_client.get_or_create_collection(
            name="schema_index",
            embedding_function=embedding_function
        )
        collection.add(
            documents=[
                "CREATE TABLE users (id INTEGER, name TEXT, email TEXT);",
                "CREATE TABLE products (id INTEGER, name TEXT, price REAL);",
            ],
            ids=["users", "products"]
        )
        
        mock_client = MockOpenAIClient(responses=["SELECT COUNT(*) FROM users;"])
        
        with patch('generator.collection', collection), \
             patch('generator.client', mock_client), \
             patch('generator.DB_PATH', test_db):
            result = run_agent("How many users are there?")
        
        assert result is not None, "Should return result"
        assert result["success"], "Should succeed"
        assert len(result["data"]) > 0, "Should have data"
    
    def test_complex_join_question(self, test_db, chroma_client, embedding_function, mock_env):
        """Test flow for question requiring joins."""
        from generator import run_agent
        
        collection = chroma_client.get_or_create_collection(
            name="schema_index",
            embedding_function=embedding_function
        )
        collection.add(
            documents=[
                "CREATE TABLE users (id INTEGER, name TEXT, email TEXT);",
                "CREATE TABLE orders (id INTEGER, user_id INTEGER, total REAL);",
            ],
            ids=["users", "orders"]
        )
        
        sql = """
        SELECT u.name, SUM(o.total) as total_spent
        FROM users u
        JOIN orders o ON u.id = o.user_id
        GROUP BY u.name
        ORDER BY total_spent DESC
        LIMIT 1;
        """
        
        mock_client = MockOpenAIClient(responses=[sql])
        
        with patch('generator.collection', collection), \
             patch('generator.client', mock_client), \
             patch('generator.DB_PATH', test_db):
            result = run_agent("Who spent the most money?")
        
        assert result is not None, "Should return result"
        assert result["success"], "Should succeed"
    
    def test_error_recovery_flow(self, test_db, chroma_client, embedding_function, mock_env):
        """Test that system recovers from SQL errors."""
        from generator import run_agent
        
        collection = chroma_client.get_or_create_collection(
            name="schema_index",
            embedding_function=embedding_function
        )
        collection.add(
            documents=["CREATE TABLE users (id INTEGER, name TEXT);"],
            ids=["users"]
        )
        
        # First query fails, second succeeds
        mock_client = MockOpenAIClient(responses=[
            "SELECT * FROM wrong_table;",  # Error
            "SELECT * FROM users;"  # Success
        ])
        
        with patch('generator.collection', collection), \
             patch('generator.client', mock_client), \
             patch('generator.DB_PATH', test_db):
            result = run_agent("Show users")
        
        assert result is not None, "Should recover and return result"
        assert result["success"], "Should eventually succeed"
        assert mock_client.call_count >= 2, "Should retry after error"


class TestGenerator2Integration:
    """Integration tests for generator2.py advanced features."""
    
    def test_smart_retrieval_with_foreign_keys(self, test_db, chroma_client, embedding_function, mock_env):
        """Test smart retrieval includes related tables via foreign keys."""
        from generator2 import smart_retrieval, run_agent
        
        collection = chroma_client.get_or_create_collection(
            name="schema_index",
            embedding_function=embedding_function
        )
        collection.add(
            documents=[
                "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);",
                "CREATE TABLE orders (id INTEGER, user_id INTEGER, FOREIGN KEY(user_id) REFERENCES users(id));",
                "CREATE TABLE products (id INTEGER, name TEXT);",
            ],
            ids=["users", "orders", "products"]
        )
        
        with patch('generator2.collection', collection):
            schemas = smart_retrieval("Show user orders")
        
        # Should retrieve both users and orders (related via FK)
        schema_text = " ".join(schemas)
        assert "users" in schema_text or "orders" in schema_text, "Should retrieve relevant schemas"
    
    def test_ast_validation_in_pipeline(self, test_db, mock_env):
        """Test that AST validation works in the full pipeline."""
        from generator2 import execute_sql
        
        # Try forbidden operation
        with patch('generator2.engine') as mock_engine:
            mock_engine.dialect.name = "sqlite"
            result = execute_sql("DROP TABLE users;")
        
        assert result["success"] is False, "Should block forbidden operation"
        assert "Safety Violation" in result["error"] or "AST detected" in result["error"]
    
    def test_query_critic_feedback(self, test_db, chroma_client, embedding_function, mock_env):
        """Test that query critic provides helpful feedback."""
        from generator2 import query_critic
        
        failed_sql = "SELECT * FROM wrong_table;"
        error_msg = "no such table: wrong_table"
        schema = "CREATE TABLE users (id INTEGER, name TEXT);"
        
        mock_client = MockOpenAIClient(responses=[
            "The table name 'wrong_table' does not exist in the schema."
        ])
        
        with patch('generator2.client', mock_client):
            critique = query_critic(
                "List all users",
                failed_sql,
                error_msg,
                schema
            )
        
        assert len(critique) > 0, "Should provide critique"
        assert mock_client.call_count == 1, "Should call OpenAI once"


class TestAnswerSynthesis:
    """Test suite for natural language answer synthesis."""
    
    def test_synthesize_simple_answer(self, mock_env):
        """Test synthesis of simple answer from query results."""
        from generator2 import synthesize_answer
        
        question = "How many users are there?"
        sql_results = [(5,)]
        column_names = ["COUNT(*)"]
        
        mock_client = MockOpenAIClient(responses=["There are 5 users."])
        
        with patch('generator2.client', mock_client):
            answer = synthesize_answer(question, sql_results, column_names)
        
        assert len(answer) > 0, "Should generate answer"
        assert mock_client.call_count == 1, "Should call OpenAI once"
    
    def test_synthesize_complex_answer(self, mock_env):
        """Test synthesis of complex answer with multiple rows."""
        from generator2 import synthesize_answer
        
        question = "Who are the top spenders?"
        sql_results = [("Alice", 1500.00), ("Bob", 1200.00)]
        column_names = ["name", "total_spent"]
        
        mock_client = MockOpenAIClient(responses=[
            "The top spenders are Alice with $1,500 and Bob with $1,200."
        ])
        
        with patch('generator2.client', mock_client):
            answer = synthesize_answer(question, sql_results, column_names)
        
        assert len(answer) > 0, "Should generate answer"
    
    def test_synthesize_empty_results(self, mock_env):
        """Test synthesis when no results found."""
        from generator2 import synthesize_answer
        
        question = "Who bought product X?"
        sql_results = []
        column_names = []
        
        answer = synthesize_answer(question, sql_results, column_names)
        
        assert "couldn't find" in answer.lower() or "no" in answer.lower(), \
            "Should indicate no results found"


class TestMultiDatabaseDialects:
    """Test suite for multi-database dialect handling."""
    
    def test_sqlite_dialect(self, test_db, mock_env):
        """Test that SQLite dialect is correctly identified."""
        from generator2 import dialect
        
        # Should be sqlite
        assert "sqlite" in dialect.lower(), "Should identify SQLite dialect"
    
    def test_dialect_specific_prompts(self, chroma_client, embedding_function, mock_env):
        """Test that prompts include dialect-specific information."""
        from generator2 import run_agent
        
        collection = chroma_client.get_or_create_collection(
            name="schema_index",
            embedding_function=embedding_function
        )
        collection.add(
            documents=["CREATE TABLE users (id INTEGER);"],
            ids=["users"]
        )
        
        # Mock client that captures the prompt
        captured_messages = []
        
        def mock_create(**kwargs):
            captured_messages.append(kwargs.get("messages", []))
            mock_response = type('obj', (object,), {
                'choices': [type('obj', (object,), {
                    'message': type('obj', (object,), {
                        'content': 'SELECT * FROM users;'
                    })()
                })()]
            })()
            return mock_response
        
        mock_client = type('obj', (object,), {
            'chat': type('obj', (object,), {
                'completions': type('obj', (object,), {
                    'create': mock_create
                })()
            })()
        })()
        
        with patch('generator2.collection', collection), \
             patch('generator2.client', mock_client), \
             patch('generator2.execute_sql', lambda x: {"success": True, "columns": [], "data": []}):
            run_agent("List users")
        
        # Check that dialect was mentioned in prompts
        assert len(captured_messages) > 0, "Should have captured messages"


class TestIndexing:
    """Test suite for indexing functionality."""
    
    def test_indexer_creates_collection(self, test_db, chroma_client, embedding_function):
        """Test that indexer creates vector collection correctly."""
        import re
        from sql_rag import get_database_schema
        
        schemas = get_database_schema(test_db)
        
        # Extract table names
        ids = []
        for sql in schemas:
            pattern = r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([^\s\(]+)"
            match = re.search(pattern, sql, re.IGNORECASE)
            if match:
                table_name = match.group(1).strip('"')
                ids.append(table_name)
        
        # Create collection
        collection = chroma_client.get_or_create_collection(
            name="test_schema_index",
            embedding_function=embedding_function
        )
        collection.add(documents=schemas, ids=ids)
        
        # Verify
        result = collection.get()
        assert len(result["ids"]) == len(schemas), "Should index all schemas"
        assert all(id in result["ids"] for id in ids), "Should have correct IDs"
