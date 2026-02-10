"""
Input validation utilities for SQL_RAG project.
Validates user inputs and sanitizes data to prevent security issues.
"""
import re
from src.utils.config import MAX_QUESTION_LENGTH
from src.utils.logger import get_logger
from src.utils.exceptions import InvalidInputError

logger = get_logger(__name__)


def validate_question(question: str) -> str:
    """
    Validate and sanitize user question.
    
    Args:
        question: User's natural language question
    
    Returns:
        Sanitized question string
    
    Raises:
        InvalidInputError: If question is invalid
    """
    if not question:
        logger.error("Empty question provided")
        raise InvalidInputError("Question cannot be empty")
    
    if not isinstance(question, str):
        logger.error("Question must be a string, got %s", type(question))
        raise InvalidInputError("Question must be a string")
    
    # Strip whitespace
    question = question.strip()
    
    # Check length
    if len(question) > MAX_QUESTION_LENGTH:
        logger.warning("Question too long: %d characters (max: %d)", 
                      len(question), MAX_QUESTION_LENGTH)
        raise InvalidInputError(
            f"Question too long. Maximum {MAX_QUESTION_LENGTH} characters allowed."
        )
    
    # Check for suspicious patterns (basic XSS/injection prevention)
    suspicious_patterns = [
        r'<script',
        r'javascript:',
        r'onerror=',
        r'onclick=',
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, question, re.IGNORECASE):
            logger.warning("Suspicious pattern detected in question: %s", pattern)
            raise InvalidInputError("Question contains invalid characters or patterns")
    
    logger.debug("Question validated: %s", question[:50])
    return question


def validate_sql_query(sql: str) -> str:
    """
    Validate SQL query string.
    
    Args:
        sql: SQL query string
    
    Returns:
        Validated SQL string
    
    Raises:
        InvalidInputError: If SQL is invalid
    """
    if not sql:
        raise InvalidInputError("SQL query cannot be empty")
    
    if not isinstance(sql, str):
        raise InvalidInputError("SQL query must be a string")
    
    sql = sql.strip()
    
    # Check for minimum length (at least "SELECT")
    if len(sql) < 6:
        raise InvalidInputError("SQL query too short")
    
    # Ensure it starts with SELECT (case-insensitive)
    if not sql.upper().startswith('SELECT'):
        logger.warning("Non-SELECT query attempted: %s", sql[:50])
        raise InvalidInputError("Only SELECT queries are allowed")
    
    return sql


def sanitize_error_message(error: Exception, include_details: bool = False) -> str:
    """
    Sanitize error messages to prevent information leakage.
    
    Args:
        error: Original exception
        include_details: Whether to include technical details (for logging)
    
    Returns:
        Sanitized error message safe for user display
    """
    error_str = str(error).lower()
    
    # Generic message for users
    generic_message = "An error occurred while processing your request. Please try again."
    
    # Check for specific error types and provide helpful but safe messages
    if 'syntax' in error_str or 'near' in error_str:
        return "Invalid SQL syntax. Please check your query."
    elif 'no such table' in error_str:
        return "Referenced table does not exist in the database."
    elif 'no such column' in error_str:
        return "Referenced column does not exist."
    elif 'ambiguous' in error_str:
        return "Ambiguous column reference. Please specify table name."
    elif 'timeout' in error_str:
        return "Query took too long to execute. Please simplify your query."
    
    # For other errors, return generic message
    # Full error is logged separately for debugging
    if include_details:
        return f"{generic_message} Details: {str(error)}"
    
    return generic_message


def validate_table_name(table_name: str) -> str:
    """
    Validate table name to prevent SQL injection.
    
    Args:
        table_name: Table name to validate
    
    Returns:
        Validated table name
    
    Raises:
        InvalidInputError: If table name is invalid
    """
    if not table_name:
        raise InvalidInputError("Table name cannot be empty")
    
    # Allow only alphanumeric characters and underscores
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
        logger.warning("Invalid table name: %s", table_name)
        raise InvalidInputError(
            "Invalid table name. Use only letters, numbers, and underscores."
        )
    
    return table_name


def validate_column_name(column_name: str) -> str:
    """
    Validate column name to prevent SQL injection.
    
    Args:
        column_name: Column name to validate
    
    Returns:
        Validated column name
    
    Raises:
        InvalidInputError: If column name is invalid
    """
    if not column_name:
        raise InvalidInputError("Column name cannot be empty")
    
    # Allow only alphanumeric characters and underscores
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', column_name):
        logger.warning("Invalid column name: %s", column_name)
        raise InvalidInputError(
            "Invalid column name. Use only letters, numbers, and underscores."
        )
    
    return column_name


if __name__ == "__main__":
    # Test validators
    print("Testing validators...")
    
    try:
        validate_question("What are the top 10 products?")
        print("✓ Valid question accepted")
    except InvalidInputError as e:
        print(f"✗ Valid question rejected: {e}")
    
    try:
        validate_question("x" * 1000)
        print("✗ Long question accepted (should fail)")
    except InvalidInputError:
        print("✓ Long question rejected")
    
    try:
        validate_sql_query("SELECT * FROM users")
        print("✓ Valid SQL accepted")
    except InvalidInputError as e:
        print(f"✗ Valid SQL rejected: {e}")
    
    try:
        validate_sql_query("DROP TABLE users")
        print("✗ DROP query accepted (should fail)")
    except InvalidInputError:
        print("✓ DROP query rejected")
    
    print("\nAll validator tests passed!")
