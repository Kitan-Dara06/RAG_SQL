"""
Custom exception types for SQL_RAG project.
Provides specific exception classes for better error handling and debugging.
"""


class SQLRAGException(Exception):
    """Base exception for all SQL_RAG errors."""
    pass


class InvalidInputError(SQLRAGException):
    """Raised when user input is invalid (e.g., too long, malformed)."""
    pass


class SQLExecutionError(SQLRAGException):
    """Raised when SQL execution fails."""
    
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.original_error = original_error


class RateLimitError(SQLRAGException):
    """Raised when API rate limit is exceeded."""
    pass


class DatabaseConnectionError(SQLRAGException):
    """Raised when database connection fails."""
    
    def __init__(self, message: str, db_type: str = None):
        super().__init__(message)
        self.db_type = db_type


class SchemaExtractionError(SQLRAGException):
    """Raised when schema extraction fails."""
    pass


class VectorSearchError(SQLRAGException):
    """Raised when vector database search fails."""
    pass


class ConfigurationError(SQLRAGException):
    """Raised when configuration is invalid or missing."""
    pass
