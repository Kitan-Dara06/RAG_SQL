"""
Configuration management for SQL_RAG.
Loads settings from environment variables with sensible defaults.
"""
import os
from pathlib import Path
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def parse_connection_string(url: str) -> dict:
    """
    Parse a database connection string into its components.
    
    Handles formats like:
      - postgresql+asyncpg://user:password@localhost:5432/dbname
      - postgresql://user:password@localhost:5432/dbname
      - mysql+pymysql://user:pass@host:3306/db
      - sqlite:///path/to/db.sqlite
    
    Returns a dict with keys:
      dialect, driver, user, password, host, port, dbname, clean_url
    """
    url = url.strip()
    if not url:
        raise ValueError("Connection string cannot be empty")
    
    parsed = urlparse(url)
    
    # Split scheme into dialect and optional driver (e.g. "postgresql+asyncpg")
    scheme = parsed.scheme  # e.g. "postgresql+asyncpg"
    if "+" in scheme:
        dialect, driver = scheme.split("+", 1)
    else:
        dialect, driver = scheme, None
    
    # Normalize dialect name
    dialect_lower = dialect.lower()
    if dialect_lower in ("postgres", "postgresql"):
        db_type = "PostgreSQL"
        default_port = "5432"
        clean_dialect = "postgresql"
    elif dialect_lower == "mysql":
        db_type = "MySQL"
        default_port = "3306"
        clean_dialect = "mysql+pymysql"
    elif dialect_lower == "sqlite":
        db_type = "SQLite"
        default_port = ""
        clean_dialect = "sqlite"
    else:
        raise ValueError(f"Unsupported database dialect: {dialect}")
    
    # Extract components
    user = unquote(parsed.username or "")
    password = unquote(parsed.password or "")
    host = parsed.hostname or "localhost"
    port = str(parsed.port) if parsed.port else default_port
    dbname = parsed.path.lstrip("/") if parsed.path else ""
    
    # Build a clean SQLAlchemy-compatible URL (no asyncpg driver etc.)
    if dialect_lower == "sqlite":
        clean_url = f"sqlite:///{dbname}" if dbname else "sqlite://"
    else:
        clean_url = f"{clean_dialect}://{user}:{password}@{host}:{port}/{dbname}"
    
    return {
        "dialect": dialect_lower,
        "driver": driver,
        "db_type": db_type,
        "user": user,
        "password": password,
        "host": host,
        "port": port,
        "dbname": dbname,
        "clean_url": clean_url,
    }

# Try to import streamlit for cloud deployment
try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

# OpenAI Configuration
# Try Streamlit secrets first (for cloud deployment), then environment variables
if HAS_STREAMLIT:
    try:
        OPENAI_KEY = st.secrets.get("OPENAI_KEY", os.getenv("OPENAI_KEY", ""))
        OPENAI_MODEL = st.secrets.get("OPENAI_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    except:
        OPENAI_KEY = os.getenv("OPENAI_KEY", "")
        OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
else:
    OPENAI_KEY = os.getenv("OPENAI_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Database Configuration
DB_TYPE = os.getenv("DB_TYPE", "sqlite")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "enterprise")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Construct connection string based on DB_TYPE
if DB_TYPE == "sqlite":
    DB_CONNECTION_STRING = f"sqlite:///{os.getenv('DB_PATH', 'enterprise.db')}"
elif DB_TYPE == "postgresql":
    DB_CONNECTION_STRING = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
elif DB_TYPE == "mysql":
    DB_CONNECTION_STRING = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    raise ValueError(f"Unsupported database type: {DB_TYPE}")

# ChromaDB Configuration
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./repo_db")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "sql_rag.log")

# Rate Limiting Configuration
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

# Query Configuration
MAX_QUESTION_LENGTH = int(os.getenv("MAX_QUESTION_LENGTH", "500"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
