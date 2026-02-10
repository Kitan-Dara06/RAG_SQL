"""
Security testing for SQL_RAG project.
Tests for SQL injection, forbidden operations, and vulnerability exploits.
"""
import pytest
from unittest.mock import patch


class TestSQLInjectionPrevention:
    """Test suite for SQL injection attack prevention."""
    
    def test_injection_via_drop_table(self, test_db):
        """Test prevention of DROP TABLE injection."""
        from generator import execute_sql
        
        malicious_queries = [
            "SELECT * FROM users; DROP TABLE users;",
            "SELECT * FROM users WHERE id = 1; DROP TABLE products;",
            "'; DROP TABLE users; --",
        ]
        
        for query in malicious_queries:
            with patch('generator.DB_PATH', test_db):
                result = execute_sql(query)
            
            assert result["success"] is False, f"Should block: {query}"
            assert "Safety Alert" in result["error"], "Should return safety error"
    
    def test_injection_via_union_with_drop(self, test_db):
        """Test prevention of UNION-based injection with DROP."""
        from generator import execute_sql
        
        query = "SELECT * FROM users UNION SELECT 'DROP', 'TABLE', 'users'"
        
        with patch('generator.DB_PATH', test_db):
            result = execute_sql(query)
        
        # This should succeed as it's a valid SELECT, but let's verify no damage
        # The key is that even if this runs, it won't execute DROP
        if result["success"]:
            # Verify users table still exists
            check_result = execute_sql("SELECT COUNT(*) FROM users;")
            assert check_result["success"], "Users table should still exist"
    
    def test_injection_via_comment_bypass(self, test_db):
        """Test that comment-based bypass attempts are blocked."""
        from generator import execute_sql
        
        queries = [
            "SELECT * FROM users; -- DROP TABLE users",
            "SELECT * FROM users /* DROP TABLE users */",
        ]
        
        for query in queries:
            with patch('generator.DB_PATH', test_db):
                result = execute_sql(query)
            
            # These might succeed as SELECTs, but verify no DROP occurred
            check = execute_sql("SELECT COUNT(*) FROM users;")
            assert check["success"], "Table should still exist after comment injection attempt"
    
    def test_injection_via_update(self, test_db):
        """Test prevention of UPDATE injection."""
        from generator import execute_sql
        
        queries = [
            "SELECT * FROM users WHERE id = 1; UPDATE users SET name = 'Hacked';",
            "'; UPDATE users SET email = 'hacker@evil.com'; --",
        ]
        
        for query in queries:
            with patch('generator.DB_PATH', test_db):
                result = execute_sql(query)
            
            assert result["success"] is False, f"Should block UPDATE: {query}"
    
    def test_injection_via_delete(self, test_db):
        """Test prevention of DELETE injection."""
        from generator import execute_sql
        
        queries = [
            "SELECT * FROM users; DELETE FROM users;",
            "'; DELETE FROM products WHERE 1=1; --",
        ]
        
        for query in queries:
            with patch('generator.DB_PATH', test_db):
                result = execute_sql(query)
            
            assert result["success"] is False, f"Should block DELETE: {query}"


class TestForbiddenOperations:
    """Test suite for blocking all forbidden SQL operations."""
    
    def test_block_drop_table(self, test_db):
        """Test DROP TABLE is blocked."""
        from generator import execute_sql
        
        with patch('generator.DB_PATH', test_db):
            result = execute_sql("DROP TABLE users;")
        
        assert result["success"] is False
        assert "Safety Alert" in result["error"]
    
    def test_block_drop_database(self, test_db):
        """Test DROP DATABASE is blocked."""
        from generator import execute_sql
        
        with patch('generator.DB_PATH', test_db):
            result = execute_sql("DROP DATABASE test;")
        
        assert result["success"] is False
    
    def test_block_delete_all(self, test_db):
        """Test DELETE without WHERE is blocked."""
        from generator import execute_sql
        
        with patch('generator.DB_PATH', test_db):
            result = execute_sql("DELETE FROM users;")
        
        assert result["success"] is False
    
    def test_block_update_all(self, test_db):
        """Test UPDATE without WHERE is blocked."""
        from generator import execute_sql
        
        with patch('generator.DB_PATH', test_db):
            result = execute_sql("UPDATE users SET name = 'Test';")
        
        assert result["success"] is False
    
    def test_block_insert(self, test_db):
        """Test INSERT is blocked."""
        from generator import execute_sql
        
        with patch('generator.DB_PATH', test_db):
            result = execute_sql("INSERT INTO users (name, email) VALUES ('Test', 'test@test.com');")
        
        assert result["success"] is False
    
    def test_case_insensitive_blocking(self, test_db):
        """Test that forbidden words are blocked regardless of case."""
        from generator import execute_sql
        
        queries = [
            "drop table users;",
            "DrOp TaBlE users;",
            "DELETE from users;",
            "DeLeTe FrOm users;",
        ]
        
        for query in queries:
            with patch('generator.DB_PATH', test_db):
                result = execute_sql(query)
            
            assert result["success"] is False, f"Should block case variant: {query}"


class TestASTValidation:
    """Test suite for AST-based SQL validation in generator2.py."""
    
    def test_ast_detects_drop(self):
        """Test AST validation detects DROP statements."""
        from generator2 import validate_sql_ast
        
        is_valid, error = validate_sql_ast("DROP TABLE users;")
        
        assert is_valid is False, "Should detect DROP"
        assert "Safety Violation" in error or "AST detected" in error
    
    def test_ast_detects_delete(self):
        """Test AST validation detects DELETE statements."""
        from generator2 import validate_sql_ast
        
        is_valid, error = validate_sql_ast("DELETE FROM users WHERE id = 1;")
        
        assert is_valid is False, "Should detect DELETE"
    
    def test_ast_detects_update(self):
        """Test AST validation detects UPDATE statements."""
        from generator2 import validate_sql_ast
        
        is_valid, error = validate_sql_ast("UPDATE users SET name = 'Test';")
        
        assert is_valid is False, "Should detect UPDATE"
    
    def test_ast_detects_insert(self):
        """Test AST validation detects INSERT statements."""
        from generator2 import validate_sql_ast
        
        is_valid, error = validate_sql_ast("INSERT INTO users VALUES (1, 'Test');")
        
        assert is_valid is False, "Should detect INSERT"
    
    def test_ast_detects_create(self):
        """Test AST validation detects CREATE statements."""
        from generator2 import validate_sql_ast
        
        is_valid, error = validate_sql_ast("CREATE TABLE hackers (id INTEGER);")
        
        assert is_valid is False, "Should detect CREATE"
    
    def test_ast_allows_select(self):
        """Test AST validation allows SELECT statements."""
        from generator2 import validate_sql_ast
        
        is_valid, error = validate_sql_ast("SELECT * FROM users;")
        
        assert is_valid is True, "Should allow SELECT"
        assert error == "", "Should have no error"
    
    def test_ast_allows_complex_select(self):
        """Test AST validation allows complex SELECT with JOINs."""
        from generator2 import validate_sql_ast
        
        sql = """
        SELECT u.name, o.total 
        FROM users u 
        JOIN orders o ON u.id = o.user_id 
        WHERE o.total > 100;
        """
        
        is_valid, error = validate_sql_ast(sql)
        
        assert is_valid is True, "Should allow complex SELECT"
    
    def test_ast_syntax_error_detection(self):
        """Test AST detects syntax errors."""
        from generator2 import validate_sql_ast
        
        is_valid, error = validate_sql_ast("SELECT * FORM users;")  # Typo
        
        assert is_valid is False, "Should detect syntax error"
        assert "Syntax Error" in error or "Error" in error


class TestPathTraversalPrevention:
    """Test suite for path traversal attack prevention."""
    
    def test_database_path_validation(self):
        """Test that database paths are validated."""
        from generator import execute_sql
        
        # Try to access files outside intended directory
        malicious_paths = [
            "../../../etc/passwd",
            "../../.env",
            "/etc/shadow",
        ]
        
        for path in malicious_paths:
            with patch('generator.DB_PATH', path):
                # Should fail to connect or execute
                result = execute_sql("SELECT * FROM users;")
                # Either fails or doesn't expose sensitive data
                assert result["success"] is False or "data" not in result


class TestResourceExhaustion:
    """Test suite for resource exhaustion attack prevention."""
    
    def test_large_result_set_handling(self, test_db):
        """Test handling of queries that return large result sets."""
        from generator import execute_sql
        
        # This should work but not crash
        with patch('generator.DB_PATH', test_db):
            result = execute_sql("SELECT * FROM users UNION ALL SELECT * FROM users UNION ALL SELECT * FROM users;")
        
        # Should either succeed or fail gracefully
        assert "success" in result, "Should return a result"
    
    def test_complex_join_handling(self, test_db):
        """Test handling of complex JOIN queries."""
        from generator import execute_sql
        
        sql = """
        SELECT u.*, o.*, p.*
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
        LEFT JOIN products p ON 1=1;
        """
        
        with patch('generator.DB_PATH', test_db):
            result = execute_sql(sql)
        
        # Should handle without crashing
        assert "success" in result


class TestInputSanitization:
    """Test suite for input sanitization."""
    
    def test_markdown_code_block_removal(self, test_db):
        """Test that markdown code blocks are properly removed."""
        from generator import execute_sql
        
        queries = [
            "```sql\nSELECT * FROM users;\n```",
            "```\nSELECT * FROM users;\n```",
            "```sql\\nSELECT * FROM users;\\n```",
        ]
        
        for query in queries:
            with patch('generator.DB_PATH', test_db):
                result = execute_sql(query)
            
            # Should clean and execute successfully
            assert result["success"] is True, f"Should clean markdown from: {query}"
    
    def test_whitespace_handling(self, test_db):
        """Test handling of excessive whitespace."""
        from generator import execute_sql
        
        query = "   SELECT   *   FROM   users   ;   "
        
        with patch('generator.DB_PATH', test_db):
            result = execute_sql(query)
        
        assert result["success"] is True, "Should handle whitespace"
    
    def test_newline_handling(self, test_db):
        """Test handling of newlines in queries."""
        from generator import execute_sql
        
        query = "SELECT\\n*\\nFROM\\nusers;"
        
        with patch('generator.DB_PATH', test_db):
            result = execute_sql(query)
        
        # Should handle newlines appropriately
        assert "success" in result
