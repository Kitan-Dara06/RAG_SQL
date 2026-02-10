"""
Unit tests for generator.py - Basic SQL generation functionality.
"""
import sqlite3
from unittest.mock import Mock, patch, MagicMock

import pytest

from test_utils import validate_sql_syntax


class TestExecuteSQL:
    """Test suite for execute_sql function."""
    
    def test_execute_simple_select(self, test_db):
        """Test execution of a simple SELECT query."""
        from generator import execute_sql
        
        # Temporarily patch DB_PATH
        with patch('generator.DB_PATH', test_db):
            result = execute_sql("SELECT * FROM users;")
        
        assert result["success"] is True, "Query should succeed"
        assert "columns" in result, "Should return columns"
        assert "data" in result, "Should return data"
        assert len(result["data"]) == 2, "Should return 2 users"
    
    def test_forbidden_drop_command(self, test_db):
        """Test that DROP commands are blocked."""
        from generator import execute_sql
        
        with patch('generator.DB_PATH', test_db):
            result = execute_sql("DROP TABLE users;")
        
        assert result["success"] is False, "DROP should be blocked"
        assert "Safety Alert" in result["error"], "Should return safety error"
    
    def test_forbidden_delete_command(self, test_db):
        """Test that DELETE commands are blocked."""
        from generator import execute_sql
        
        with patch('generator.DB_PATH', test_db):
            result = execute_sql("DELETE FROM users WHERE id = 1;")
        
        assert result["success"] is False, "DELETE should be blocked"
        assert "Safety Alert" in result["error"], "Should return safety error"
    
    def test_forbidden_update_command(self, test_db):
        """Test that UPDATE commands are blocked."""
        from generator import execute_sql
        
        with patch('generator.DB_PATH', test_db):
            result = execute_sql("UPDATE users SET name = 'Hacker' WHERE id = 1;")
        
        assert result["success"] is False, "UPDATE should be blocked"
        assert "Safety Alert" in result["error"], "Should return safety error"
    
    def test_forbidden_insert_command(self, test_db):
        """Test that INSERT commands are blocked."""
        from generator import execute_sql
        
        with patch('generator.DB_PATH', test_db):
            result = execute_sql("INSERT INTO users (name, email) VALUES ('Evil', 'evil@test.com');")
        
        assert result["success"] is False, "INSERT should be blocked"
        assert "Safety Alert" in result["error"], "Should return safety error"
    
    def test_sql_with_markdown_formatting(self, test_db):
        """Test that SQL with markdown formatting is cleaned."""
        from generator import execute_sql
        
        sql_with_markdown = "```sql\\nSELECT * FROM users;\\n```"
        
        with patch('generator.DB_PATH', test_db):
            result = execute_sql(sql_with_markdown)
        
        assert result["success"] is True, "Should clean markdown and execute"
    
    def test_invalid_sql_syntax(self, test_db):
        """Test handling of invalid SQL syntax."""
        from generator import execute_sql
        
        with patch('generator.DB_PATH', test_db):
            result = execute_sql("SELECT * FORM users;")  # Typo: FORM instead of FROM
        
        assert result["success"] is False, "Invalid SQL should fail"
        assert "error" in result, "Should return error message"
    
    def test_query_nonexistent_table(self, test_db):
        """Test querying a table that doesn't exist."""
        from generator import execute_sql
        
        with patch('generator.DB_PATH', test_db):
            result = execute_sql("SELECT * FROM nonexistent_table;")
        
        assert result["success"] is False, "Should fail for nonexistent table"
        assert "error" in result, "Should return error message"
    
    def test_column_names_returned(self, test_db):
        """Test that column names are correctly returned."""
        from generator import execute_sql
        
        with patch('generator.DB_PATH', test_db):
            result = execute_sql("SELECT name, email FROM users;")
        
        assert result["success"] is True
        assert "name" in result["columns"], "Should include 'name' column"
        assert "email" in result["columns"], "Should include 'email' column"
    
    def test_empty_result_set(self, test_db):
        """Test query that returns no rows."""
        from generator import execute_sql
        
        with patch('generator.DB_PATH', test_db):
            result = execute_sql("SELECT * FROM users WHERE id = 999;")
        
        assert result["success"] is True, "Query should succeed"
        assert len(result["data"]) == 0, "Should return empty result set"


class TestGetRelevantSchema:
    """Test suite for get_relevant_schema function."""
    
    @pytest.mark.skip(reason="Requires OpenAI API - tested in integration tests")
    def test_schema_retrieval(self, chroma_client, embedding_function):
        """Test basic schema retrieval from vector database."""
        pass


class TestGenerateSQL:
    """Test suite for generate_sql function with mocked OpenAI."""
    
    @pytest.mark.skip(reason="Requires OpenAI API - tested in integration tests")
    def test_sql_generation_basic(self, mock_env):
        """Test basic SQL generation."""
        pass
    
    @pytest.mark.skip(reason="Requires OpenAI API - tested in integration tests")
    def test_sql_generation_with_context(self, mock_env):
        """Test that schema context is used in generation."""
        pass


class TestRunAgent:
    """Test suite for run_agent function with retry logic."""
    
    @pytest.mark.skip(reason="Requires OpenAI API - tested in integration tests")
    def test_agent_success_first_try(self, test_db, chroma_client, embedding_function, mock_env):
        """Test agent succeeds on first attempt."""
        pass
    
    @pytest.mark.skip(reason="Requires OpenAI API - tested in integration tests")
    def test_agent_retry_on_error(self, test_db, chroma_client, embedding_function, mock_env):
        """Test agent retries on SQL error."""
        pass
    
    @pytest.mark.skip(reason="Requires OpenAI API - tested in integration tests")
    def test_agent_max_retries(self, test_db, chroma_client, embedding_function, mock_env):
        """Test agent stops after max retries."""
        pass
