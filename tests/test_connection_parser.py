"""
Unit tests for parse_connection_string() utility.
"""
import pytest
from src.utils.config import parse_connection_string


class TestParseConnectionString:
    """Tests for connection string parsing."""

    def test_postgresql_with_asyncpg(self):
        """Parses postgresql+asyncpg:// and strips the driver."""
        url = "postgresql+asyncpg://myuser:mypass@localhost:5432/sentinel_lite"
        result = parse_connection_string(url)

        assert result["dialect"] == "postgresql"
        assert result["driver"] == "asyncpg"
        assert result["db_type"] == "PostgreSQL"
        assert result["user"] == "myuser"
        assert result["password"] == "mypass"
        assert result["host"] == "localhost"
        assert result["port"] == "5432"
        assert result["dbname"] == "sentinel_lite"
        assert result["clean_url"] == "postgresql://myuser:mypass@localhost:5432/sentinel_lite"

    def test_plain_postgresql(self):
        """Parses a standard postgresql:// URL with no driver suffix."""
        url = "postgresql://admin:secret@db.example.com:5432/production"
        result = parse_connection_string(url)

        assert result["dialect"] == "postgresql"
        assert result["driver"] is None
        assert result["db_type"] == "PostgreSQL"
        assert result["user"] == "admin"
        assert result["host"] == "db.example.com"
        assert result["dbname"] == "production"
        assert result["clean_url"] == "postgresql://admin:secret@db.example.com:5432/production"

    def test_postgres_shorthand(self):
        """Handles 'postgres://' as an alias for 'postgresql://'."""
        url = "postgres://user:pass@host:5432/db"
        result = parse_connection_string(url)

        assert result["dialect"] == "postgres"
        assert result["db_type"] == "PostgreSQL"
        assert result["clean_url"] == "postgresql://user:pass@host:5432/db"

    def test_mysql_with_pymysql(self):
        """Parses mysql+pymysql:// format."""
        url = "mysql+pymysql://root:password@127.0.0.1:3306/app_db"
        result = parse_connection_string(url)

        assert result["dialect"] == "mysql"
        assert result["driver"] == "pymysql"
        assert result["db_type"] == "MySQL"
        assert result["port"] == "3306"
        assert result["dbname"] == "app_db"
        assert result["clean_url"] == "mysql+pymysql://root:password@127.0.0.1:3306/app_db"

    def test_sqlite(self):
        """Parses sqlite:/// format."""
        url = "sqlite:///path/to/database.db"
        result = parse_connection_string(url)

        assert result["dialect"] == "sqlite"
        assert result["db_type"] == "SQLite"
        assert result["dbname"] == "path/to/database.db"
        assert result["clean_url"] == "sqlite:///path/to/database.db"

    def test_special_characters_in_password(self):
        """Handles URL-encoded special characters in password."""
        url = "postgresql://user:p%40ss%23word@localhost:5432/mydb"
        result = parse_connection_string(url)

        assert result["password"] == "p@ss#word"
        assert result["user"] == "user"

    def test_missing_port_defaults(self):
        """Uses default port when omitted."""
        url = "postgresql://user:pass@localhost/mydb"
        result = parse_connection_string(url)

        assert result["port"] == "5432"

    def test_mysql_missing_port_defaults(self):
        """Uses default MySQL port when omitted."""
        url = "mysql://user:pass@localhost/mydb"
        result = parse_connection_string(url)

        assert result["port"] == "3306"

    def test_empty_string_raises(self):
        """Empty string raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            parse_connection_string("")

    def test_whitespace_only_raises(self):
        """Whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            parse_connection_string("   ")

    def test_unsupported_dialect_raises(self):
        """Unsupported dialect raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported"):
            parse_connection_string("oracle://user:pass@host:1521/db")

    def test_strips_whitespace(self):
        """Leading/trailing whitespace is stripped before parsing."""
        url = "  postgresql://user:pass@localhost:5432/db  "
        result = parse_connection_string(url)

        assert result["dbname"] == "db"
        assert result["host"] == "localhost"
